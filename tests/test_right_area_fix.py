import copy
import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from test_composition import Fixture, part, raw_from
import test_new_workflow as workflow
from composition_controller import CompositionController, EmptyAreaGuard, RETURN_PARTS_MESSAGE
from composition_ui import (CompositionUI, draw_workspace_blockers, workspace_status,
                            workspace_rows)
import meccano_tracker as tracker

NAMES = {0: "A003", 1: "A045", 2: "C658", 3: "Hand"}


def tracked(p, *, confidence=0.9, locked=True):
    inverse = {name: i for i, name in NAMES.items()}
    cls = inverse[p["class_name"]]
    return {"bbox": p["bbox"], "tid": p["tid"], "stable_cls": cls,
            "raw_cls": cls, "conf": confidence, "locked": locked}


def observation(box, code="A003", confidence=0.9):
    return {"bbox": box, "class_name": code, "conf": confidence}


def filtered(raw, tracks=(), width=1280, height=720):
    return tracker.workspace_observations(raw, tracks, NAMES, width, height)


class ObservationFilterTests(unittest.TestCase):
    def test_background_box_rejected_by_same_geometry_as_tracking(self):
        huge = observation((400, 10, 1270, 700))
        self.assertFalse(tracker.box_plausibile(*huge["bbox"], 1280, 720)[0])
        accepted, rejected = filtered([huge])
        self.assertEqual(accepted, [])
        self.assertEqual(len(rejected), 1)
        self.assertIn("troppo largo", rejected[0]["reason"])

    def test_weak_raw_only_detection_rejected_without_changing_tracking_confidence(self):
        accepted, rejected = filtered([observation((800, 100, 830, 130), confidence=.12)])
        self.assertEqual(accepted, [])
        self.assertEqual(rejected[0]["reason"], "confidenza bassa")
        self.assertEqual(tracker.INFER_CONF, .10)
        self.assertEqual(tracker.WORKSPACE_MIN_RAW_CONF, .35)

    def test_current_track_even_weak_and_not_locked_is_preserved(self):
        p = part(cx=900)
        t = tracked(p, confidence=.12, locked=False)
        accepted, rejected = filtered([observation(p["bbox"], confidence=.12)], [t])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["source"], "tracking")
        self.assertEqual(accepted[0]["tid"], p["tid"])
        self.assertFalse(accepted[0]["locked"])
        self.assertEqual(accepted[0]["bbox"], p["bbox"])

    def test_reliable_candidate_without_id_kept_before_lock(self):
        for confidence in (.35, .5, .9):
            with self.subTest(confidence=confidence):
                accepted, rejected = filtered([observation((800, 100, 830, 130), confidence=confidence)])
                self.assertEqual(len(accepted), 1)
                self.assertNotIn("tid", accepted[0])
                self.assertEqual(rejected, [])

    def test_tiny_huge_flat_degenerate_off_frame_boxes_rejected(self):
        cases = [(-100, 10, -10, 50), (1280, 10, 1300, 50), (900, -80, 950, 0),
                 (900, 720, 950, 760), (900, 10, 902, 30), (900, 10, 890, 40),
                 (900, 10, 1220, 28), (700, 5, 900, 715),
                 (600, 5, 1040, 300)]
        for box in cases:
            with self.subTest(box=box):
                accepted, rejected = filtered([observation(box)])
                self.assertEqual(accepted, [])
                self.assertEqual(len(rejected), 1)

    def test_oversized_box_cannot_be_made_plausible_by_clipping(self):
        accepted, rejected = filtered([observation((1250, 10, 2500, 50))])
        self.assertEqual(accepted, [])
        self.assertIn("troppo largo", rejected[0]["reason"])

    def test_partially_visible_valid_piece_is_clipped(self):
        accepted, _ = filtered([observation((1250, 10, 1290, 50))])
        self.assertEqual(accepted[0]["bbox"], (1250, 10, 1280, 50))

    def test_invalid_coordinates_or_confidence_do_not_crash(self):
        cases = [observation(None), observation((900, 10, float("nan"), 50)),
                 observation((900, 10, float("inf"), 50)), observation((900, 20)),
                 observation((900, 10, "oops", 50)),
                 observation((900, 10, 950, 50), confidence=float("nan")),
                 observation((900, 10, 950, 50), confidence=None),
                 observation((900, 10, 950, 50), confidence=1.1)]
        for value in cases:
            with self.subTest(value=value):
                accepted, rejected = filtered([value])
                self.assertEqual(accepted, [])
                self.assertEqual(len(rejected), 1)

    def test_large_hand_is_not_filtered_as_impossible_meccano_part(self):
        accepted, rejected = filtered([observation((500, 10, 1200, 700), "Hand")])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(rejected, [])

    def test_unavailable_snapshot_stays_none_even_with_tracks(self):
        accepted, rejected = filtered(None, [tracked(part())])
        self.assertIsNone(accepted)
        self.assertEqual(rejected, [])

    def test_inputs_are_not_mutated_and_no_ghost_history_is_read(self):
        raw = raw_from([part()])
        tracks = [tracked(part())]
        before = copy.deepcopy((raw, tracks))
        filtered(raw, tracks)
        self.assertEqual((raw, tracks), before)
        self.assertEqual(filtered([], [])[0], [])

    def test_all_part_geometry_thresholds_agree_with_drawn_tracking(self):
        rng = np.random.default_rng(10)
        for _ in range(200):
            x1, y1 = rng.uniform((0, 0), (1000, 500))
            width, height = rng.uniform((1, 1), (650, 450))
            x2, y2 = min(1279., x1+width), min(719., y1+height)
            box = (x1, y1, x2, y2)
            expected = tracker.box_plausibile(*box, 1280, 720)[0]
            self.assertEqual(bool(filtered([observation(box)])[0]), expected)


class RightGuardFixTests(Fixture):
    def feed(self, c, left, raw, tracks=(), right=(), now=None):
        accepted, rejected = filtered(raw, tracks, c.guide.W, c.guide.H)
        c.observe(left, right, accepted, .6, now=c._now+.2 if now is None else now,
                  rejected_detections=rejected)
        return c

    def test_eight_left_pieces_and_continuous_background_noise_can_start(self):

        left = [part("A045", tid=i+1, cx=70+i*60) for i in range(8)]
        c = self.ready_controller(left)
        noise = [observation((400, 0, 1279, 710)),
                 observation((900, 400, 950, 450), confidence=.12)]
        for _ in range(15):
            self.feed(c, left, raw_from(left)+noise, [tracked(p) for p in left])
            self.assertFalse(c.guard.occupied)
            self.assertFalse(c.right_has_parts)
            self.assertEqual(c.right_blockers, [])
        with contextlib.redirect_stdout(io.StringIO()):
            result = c.generate(now=c._now)
        self.assertTrue(result.ok, result.message)
        self.assertEqual(len(c.guide.slots), 8)
        self.assertEqual(len(c.rejected_detections), 2)

    def test_noise_after_x_never_triggers_return_speech(self):
        c = self.ready_controller()
        left = c.left_parts
        for _ in range(10):
            self.feed(c, left, raw_from(left)+[observation((400, 5, 1279, 710))])
            c.finish()
            self.assertFalse(c.return_warning_visible)
            self.assertIsNone(c.take_return_announcement())

    def test_reliable_raw_only_right_piece_still_blocks_start_and_warns_on_x(self):
        c = self.ready_controller()
        self.feed(c, c.left_parts, raw_from(c.left_parts+[part(cx=900)]))
        self.assertFalse(c.generate(now=c._now).ok)
        c.finish()
        self.assertEqual(c.take_return_announcement(), RETURN_PARTS_MESSAGE)
        self.assertEqual(c.right_blockers[0]["source"], "detector")

    def test_weak_current_unlocked_track_still_blocks(self):
        c = self.ready_controller()
        p = part(cx=900)
        self.feed(c, c.left_parts, raw_from(c.left_parts), [tracked(p, confidence=.12, locked=False)])
        self.assertTrue(c.guard.occupied)
        self.assertFalse(c.generate(now=c._now).ok)

    def test_piece_touching_line_without_crossing_is_left_not_right(self):
        c = self.ready_controller()
        p = part(cx=c.guide.split_x-12)
        for _ in range(3):
            self.feed(c, [p], raw_from([p]), [tracked(p)])
        self.assertFalse(c.guard.occupied)
        self.assertFalse(c.unresolved_left)
        self.assertTrue(c.inventory_ready)

    def test_one_pixel_of_bbox_over_line_still_blocks(self):
        c = self.ready_controller()
        p = part(cx=c.guide.split_x-11)
        self.feed(c, [p], raw_from([p]))
        self.assertTrue(c.guard.occupied)
        self.assertTrue(c.right_has_parts)

    def test_real_raw_crossing_not_lost_when_corresponding_track_still_left(self):
        c = self.ready_controller()
        p = part(cx=c.guide.split_x-12)
        raw = raw_from([p])
        raw[0]["bbox"] = (p["bbox"][0]+3, p["bbox"][1], p["bbox"][2]+3, p["bbox"][3])
        self.feed(c, [p], raw, [tracked(p)])
        self.assertTrue(c.guard.occupied)
        self.assertEqual(c.right_blockers[0]["source"], "detector")

    def test_label_beyond_line_does_not_count_as_piece(self):
        c = self.ready_controller()
        p = part("C658", cx=c.guide.split_x-32)
        t = tracked(p)
        img = np.zeros((c.guide.H, c.guide.W, 3), np.uint8)
        with patch.object(tracker, "class_names", NAMES):
            tracker.draw_detection(img, t)

        self.assertTrue(np.any(img[:, c.guide.split_x:]))
        self.feed(c, [p], raw_from([p]), [t])
        self.assertFalse(c.guard.occupied)

    def test_right_blocker_list_deduplicates_raw_and_current_track(self):
        c = self.ready_controller()
        p = part(cx=900)
        self.feed(c, [], raw_from([p]), [tracked(p)], [p])
        self.assertEqual(len(c.right_blockers), 1)
        self.assertEqual(c.right_blockers[0]["tid"], p["tid"])
        self.assertEqual(c.right_blockers[0]["source"], "tracking")

    def test_manually_wrong_left_right_list_cannot_override_box_geometry(self):
        c = self.ready_controller()
        p = part(cx=120)
        self.feed(c, [], raw_from([p]), right=[p])
        self.assertFalse(c.guard.occupied)

    def test_return_warning_clears_after_real_piece_removed_despite_raw_noise(self):
        c = self.ready_controller()
        self.feed(c, [], raw_from([part(cx=900)]))
        c.finish(); c.take_return_announcement()
        noise = [observation((400, 0, 1279, 710)), observation((900, 30, 930, 60), confidence=.1)]
        self.feed(c, [], noise)
        self.assertTrue(c.return_warning_visible)
        self.feed(c, [], noise)
        self.assertFalse(c.return_warning_visible)
        self.assertTrue(c.guard.ready(c._now))

    def test_rejected_command_message_updates_when_area_clears(self):
        c = self.ready_controller()
        left = c.left_parts
        self.feed(c, left, raw_from(left+[part(cx=900)]))
        self.assertFalse(c.generate(now=c._now).ok)
        self.assertIn("occupato", c.message)
        self.feed(c, left, raw_from(left))
        self.assertIn("Attendo", c.message)
        self.feed(c, left, raw_from(left))
        self.assertIn("Piano destro libero", c.message)
        self.assertNotIn("occupato", c.message)

    def test_refresh_never_overwrites_new_stop_message(self):
        c = self.ready_controller()
        left = c.left_parts
        self.feed(c, left, raw_from(left+[part(cx=900)]))
        c.generate(now=c._now)
        c.message = "Voce interrotta."
        self.feed(c, left, raw_from(left))
        self.feed(c, left, raw_from(left))
        self.assertEqual(c.message, "Voce interrotta.")

    def test_large_right_hand_blocks_but_does_not_claim_returnable_parts(self):
        c = self.ready_controller()
        self.feed(c, c.left_parts, [observation((500, 5, 1200, 715), "Hand")])
        c.finish()
        self.assertTrue(c.guard.occupied)
        self.assertFalse(c.right_has_parts)
        self.assertIsNone(c.take_return_announcement())
        self.assertIn("MANO", workspace_status(c))
        self.assertIn("Mano", c.readiness_reason(c._now))

    def test_invalid_snapshot_is_reported_unknown_not_occupied(self):
        c = self.ready_controller()
        self.feed(c, [], None)
        self.assertFalse(c.generate(now=c._now).ok)
        self.assertIn("NON DISPONIBILE", workspace_status(c))

    def test_source_coordinates_do_not_depend_on_ui_scale_or_offset(self):
        c = self.ready_controller()
        p = part(cx=620)
        self.feed(c, [p], raw_from([p]))
        for width, height in ((1280,720), (1600,900), (1024,768)):
            ui = CompositionUI("test", max_width=width, max_height=height)
            ui.draw(np.zeros((720,1280,3), np.uint8), c)
            self.assertEqual(c.guide.split_x, 640)
            self.assertFalse(c.guard.occupied)

    def test_fresh_observation_drops_blockers_without_clearing_track_history(self):
        c = self.ready_controller()
        self.feed(c, [], raw_from([part(cx=900)]))
        self.assertTrue(c.right_blockers)
        self.feed(c, [], [])
        self.assertEqual(c.right_blockers, [])
        self.assertFalse(c.guard.occupied)
        self.assertFalse(c.guard.ready(c._now))

    def test_bad_direct_controller_coordinates_mark_invalid_without_crashing(self):
        c = self.ready_controller()
        c.observe([], [], [observation(("oops", 1, 9, 10))], now=.4)
        self.assertFalse(c.frame_valid)
        self.assertFalse(c.generate(now=.4).ok)


class DiagnosticsTests(Fixture):
    def test_raw_only_blocker_is_visible_and_never_draws_left(self):
        img = np.zeros((200,400,3), np.uint8)
        blockers = [dict(observation((190,60,235,100)), source="detector")]
        with patch("composition_ui.put_text", wraps=__import__("composition_ui").put_text) as put:
            draw_workspace_blockers(img, blockers, 200)
        self.assertFalse(np.any(img[:,:200]))
        self.assertTrue(np.any(img[:,200:]))
        self.assertTrue(any("CONTROLLO DX" in call.args[1] for call in put.call_args_list))

    def test_existing_tracking_box_does_not_get_duplicate_diagnostic_rectangle(self):
        img = np.zeros((200,400,3), np.uint8)
        draw_workspace_blockers(img, [dict(observation((240,60,280,100)), source="tracking")], 200)
        self.assertFalse(np.any(img))

    def test_right_panel_lists_actual_blocker_and_rejection_count(self):
        c = self.ready_controller()
        raw = [observation((900,50,940,90)), observation((400,0,1270,710))]
        obs, rejected = filtered(raw)
        c.observe([],[],obs,now=.4,rejected_detections=rejected)
        lines = [text for text, _ in workspace_rows(c)]
        self.assertTrue(any("A003 - senza ID" in line for line in lines))
        self.assertTrue(any("x2=940.0; linea=640" in line for line in lines))
        self.assertIn("Candidati grezzi scartati: 1", lines)


class RawNoiseMainLoopTests(Fixture):
    def test_real_main_all_features_work_with_persistent_raw_false_positives(self):
        original = tracker.RawDetectionSnapshot
        class NoisySnapshot(original):
            def __call__(self, predictor):
                super().__call__(predictor)
                if self.detections is not None:
                    self.detections.extend([
                        observation((350, 5, 1279, 715)),
                        observation((1050, 500, 1080, 530), confidence=.12),
                        observation((1100, 300, 1105, 305)),
                    ])


        with patch.object(tracker, "RawDetectionSnapshot", NoisySnapshot):
            result = workflow.NewWorkflowTests.execute(self)
        self.assertEqual(result.controllers[0].generation, 2)
        self.assertTrue(result.pipeline.stopped)
        self.assertEqual(len(result.stabilizers), 1)
        self.assertEqual(result.stabilizers[0].locked, {1:1, 2:2})
        notices = [row for row in result.voices[0].spoken if row[1] == RETURN_PARTS_MESSAGE]
        self.assertEqual(len(notices), 1)
        self.assertIn(6, result.voices[0].stops)
        self.assertFalse(result.controllers[0].guard.occupied)
        self.assertFalse(result.controllers[0].return_warning_visible)
        self.assertEqual(len(result.controllers[0].rejected_detections), 3)


if __name__ == "__main__":
    unittest.main()
