import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assembly_guide_cad import CadAssemblyGuide, CadSlot
from composition_controller import CompositionController, EmptyAreaGuard
from composition_ui import CompositionUI, draw_left_highlights
from meccano_tracker import RawDetectionSnapshot, estimate_plane_z
from voice_assistant import SceneState, VoiceAssistant


def part(code="A003", tid=1, cx=120, cy=150, angle=0, half=12):
    return {"class_name": code, "tid": tid, "cx": cx, "cy": cy,
            "bbox": (cx-half,cy-half,cx+half,cy+half), "angle_deg": angle, "z": 0.6}


def raw_from(parts):
    return [{"class_name": p["class_name"], "bbox": p["bbox"], "conf": 0.9} for p in parts]


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name)
        entries = {}
        for code, (w,h) in {"A003":(80,15), "A004":(60,15),
                           "A045":(25,25), "C658":(12,12), "B577":(35,25)}.items():
            image = np.zeros((h+4,w+4,4), np.uint8)
            image[2:h+2,2:w+2,:] = 255
            cv2.imwrite(str(cls.directory/f"{code}.png"), image)
            entries[code] = {"png":f"{code}.png", "size_mm":[w,h], "mm_per_px":1.0}
        (cls.directory/"silhouettes_meta.json").write_text(json.dumps({"parts":entries}))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def guide(self, w=1280, h=720):
        with contextlib.redirect_stdout(io.StringIO()):
            return CadAssemblyGuide(w,h,str(self.directory),600,stability_frames=2)

    def make(self, guide, codes, seed=42, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return guide.generate_from_parts(codes,0.6,seed=seed,**kwargs)

    def ready_controller(self, left=None):
        g = self.guide()
        c = CompositionController(g,stable_frames=2,
                                  guard=EmptyAreaGuard(min_frames=2,min_seconds=0.1))
        left = [part()] if left is None else left
        c.observe(left,[],raw_from(left),0.6,now=0.0)
        c.observe(left,[],raw_from(left),0.6,now=0.2)
        return c


class LayoutTests(Fixture):
    def test_exact_count_preserves_duplicate_classes(self):
        g=self.guide(); codes=["A003","A003","A045","C658","C658","A004"]
        self.assertTrue(self.make(g,codes),g.last_error)
        self.assertEqual(Counter(s.code for s in g.slots),Counter(codes))
        self.assertEqual(g._count_overlaps(),0)
        x1,y1,x2,y2=g._figure_bbox()
        self.assertGreaterEqual(x1,g.split_x+25)
        self.assertLessEqual(x2,g.W-25)
        self.assertGreaterEqual(y1,25)
        self.assertLessEqual(y2,g.H-25)

    def test_more_than_seven_parts(self):
        g=self.guide(); codes=["A045"]*11
        self.assertTrue(self.make(g,codes),g.last_error)
        self.assertEqual(len(g.slots),11)

    def test_single_part_and_reproducible_seed(self):
        g1,g2=self.guide(),self.guide()
        self.assertTrue(self.make(g1,["A045"]))
        self.assertTrue(self.make(g2,["A045"]))
        self.assertEqual(g1._layout_signature(),g2._layout_signature())

    def test_missing_silhouette_keeps_previous_figure(self):
        g=self.guide(); self.assertTrue(self.make(g,["A003"]))
        old=g.slots
        self.assertFalse(self.make(g,["A003","UNKNOWN"]))
        self.assertIs(g.slots,old)
        self.assertIn("UNKNOWN",g.last_error)

    def test_empty_inventory_does_not_create_empty_success(self):
        g=self.guide()
        self.assertFalse(self.make(g,[]))
        self.assertFalse(g.generated)

    def test_missing_png_is_not_silently_ignored(self):
        g=self.guide()
        g.lib.meta["parts"]["BAD"]={"png":"absent.png","size_mm":[10,10],"mm_per_px":1}
        self.assertFalse(self.make(g,["BAD"]))
        self.assertEqual(g.slots,[])

    def test_invalid_metadata_and_scale(self):
        g=self.guide()
        g.lib.meta["parts"]["BAD"]={"png":"A045.png","size_mm":[0,10],"mm_per_px":1}
        self.assertFalse(g.can_render("BAD"))
        for depth in [None,0,-1,float("nan"),float("inf")]:
            self.assertFalse(g.generate_from_parts(["A045"],depth))

    def test_no_space_does_not_drop_parts_or_commit_invalid_layout(self):
        g=self.guide(w=160,h=120)
        self.assertFalse(self.make(g,["A003"]*3))
        self.assertFalse(g.generated)
        self.assertEqual(g.slots,[])

    def test_generation_exception_is_atomic(self):
        g=self.guide(); self.assertTrue(self.make(g,["A045"]))
        previous=g.slots
        with patch.object(g,"_build_figure",side_effect=ValueError("errore simulato")):
            self.assertFalse(self.make(g,["A045"]))
        self.assertIs(g.slots,previous)
        self.assertTrue(g.generated)

    def test_changed_depth_changes_mask_scale(self):
        g=self.guide(); self.assertTrue(self.make(g,["A045"]))
        first=g._scaled_rotated_silhouette("A045",0).shape
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(g.generate_from_parts(["A045"],1.2,seed=42))
        second=g._scaled_rotated_silhouette("A045",0).shape
        self.assertLess(second[0],first[0])

    def test_change_single_round_part_is_visibly_different(self):
        g=self.guide(); self.assertTrue(self.make(g,["A045"],seed=1))
        signature=g._layout_signature()
        self.assertTrue(self.make(g,["A045"],seed=2,ensure_different=True))
        self.assertNotEqual(signature,g._layout_signature())


class MatchingTests(Fixture):
    def slots_guide(self):
        g=self.guide(); g.generated=True; g.missing_frames=2
        g.slots=[CadSlot(0,"A003",800,300),CadSlot(1,"A003",850,300)]
        return g

    def test_one_part_cannot_complete_two_identical_slots(self):
        g=self.slots_guide(); pieces=[part(cx=810,cy=300)]
        g.update(pieces); g.update(pieces)
        self.assertEqual(g.progress(),(1,2))
        self.assertEqual(len(g.last_matches),1)

    def test_two_physical_parts_can_complete_two_slots(self):
        g=self.slots_guide(); pieces=[part(cx=800,cy=300),part(tid=2,cx=850,cy=300)]
        g.update(pieces); g.update(pieces)
        self.assertEqual(g.progress(),(2,2))
        self.assertTrue(g.completed)

    def test_repeated_tracking_id_counts_once(self):
        g=self.slots_guide(); p1=part(cx=800,cy=300); p2=part(cx=850,cy=300)
        g.update([p1,p2]);g.update([p1,p2])
        self.assertEqual(g.progress(),(1,2))

    def test_removal_reopens_slot_but_one_missing_frame_does_not(self):
        g=self.slots_guide(); pieces=[part(cx=800,cy=300),part(tid=2,cx=850,cy=300)]
        g.update(pieces);g.update(pieces)
        g.update([]);self.assertTrue(g.completed)
        g.update([]);self.assertEqual(g.progress(),(0,2));self.assertFalse(g.completed)

    def test_wrong_class_position_and_rotation_do_not_complete(self):
        g=self.slots_guide()
        for bad in [part("A004",cx=800,cy=300),part(cx=1200,cy=600),
                    part(cx=800,cy=300,angle=90)]:
            g.update([bad]);g.update([bad])
            self.assertEqual(g.progress(),(0,2))

    def test_unknown_angle_keeps_original_position_only_fallback(self):
        g=self.slots_guide()
        g.update([part(cx=800,cy=300,angle=None)])
        g.update([part(cx=800,cy=300,angle=None)])
        self.assertEqual(g.progress(),(1,2))

    def test_unknown_angle_does_not_block_round_part(self):
        g=self.guide();g.generated=True;g.slots=[CadSlot(0,"A045",800,300)]
        p=part("A045",cx=800,cy=300,angle=None)
        g.update([p]);g.update([p])
        self.assertTrue(g.completed)

    def test_maximum_matching_avoids_greedy_under_count(self):
        g=self.slots_guide()

        g.slots[0].cx=800;g.slots[1].cx=900
        pieces=[part(cx=820,cy=300),part(tid=2,cx=730,cy=300)]
        g.update(pieces);g.update(pieces)
        self.assertEqual(g.progress(),(2,2))

    def test_invalid_coordinates_are_not_a_match(self):
        g=self.slots_guide()
        self.assertEqual(g.update([part(cx=float("nan"),cy=300)]),[])
        self.assertEqual(g.progress(),(0,2))


class ControlTests(Fixture):
    def generate_ok(self,c,change=False):
        with contextlib.redirect_stdout(io.StringIO()):
            result=c.generate(change=change,now=c._now)
        self.assertTrue(result.ok,result.message)

    def test_start_snapshots_all_left_parts(self):
        c=self.ready_controller([part(tid=i,cx=50+i*35) for i in range(8)])
        self.generate_ok(c)
        self.assertEqual(len(c.guide.slots),8)

    def test_start_cannot_reset_existing_composition(self):
        c=self.ready_controller();self.generate_ok(c)
        previous=c.guide.slots
        self.assertFalse(c.generate(now=0.2).ok)
        self.assertIs(c.guide.slots,previous)

    def test_change_requires_existing_figure(self):
        c=self.ready_controller()
        self.assertFalse(c.generate(change=True,now=0.2).ok)

    def test_raw_unlocked_piece_blocks_change_and_preserves_progress(self):
        c=self.ready_controller();self.generate_ok(c)
        old=c.guide.slots;c.guide.slots[0].completed=True
        c.observe(c.left_parts,[],raw_from(c.left_parts+[part("C658",tid=50,cx=900)]),0.6,now=0.4)
        result=c.generate(change=True,now=0.4)
        self.assertFalse(result.ok)
        self.assertIs(c.guide.slots,old)
        self.assertTrue(c.guide.slots[0].completed)

    def test_piece_straddling_boundary_blocks_even_with_left_centre(self):
        c=self.ready_controller();self.generate_ok(c)
        crossing=part(cx=c.guide.split_x-4,half=12)
        c.observe(c.left_parts,[],raw_from(c.left_parts+[crossing]),0.6,now=0.4)
        self.assertFalse(c.generate(change=True,now=0.4).ok)

    def test_hands_never_become_silhouettes_and_block_occluded_inventory(self):
        c=self.ready_controller()
        hand=part("Hand",tid=9,cx=200)
        c.observe(c.left_parts+[hand],[],raw_from(c.left_parts+[hand]),0.6,now=0.4)
        self.assertEqual(len(c.left_parts),1)
        self.assertFalse(c.generate(now=0.4).ok)

    def test_unknown_raw_snapshot_never_means_empty_area(self):
        c=self.ready_controller();self.generate_ok(c)
        c.observe(c.left_parts,[],None,0.6,now=0.4)
        self.assertFalse(c.generate(change=True,now=0.4).ok)

    def test_one_empty_frame_does_not_unlock_after_occupancy(self):
        c=self.ready_controller();self.generate_ok(c)
        left=c.left_parts
        c.observe(left,[],raw_from(left+[part(cx=900)]),0.6,now=0.4)
        c.observe(left,[],raw_from(left),0.6,now=0.6)
        self.assertFalse(c.generate(change=True,now=0.6).ok)
        c.observe(left,[],raw_from(left),0.6,now=0.8)
        self.generate_ok(c,change=True)

    def test_unlocked_left_piece_does_not_get_silently_omitted(self):
        c=self.ready_controller();left=c.left_parts
        c.observe(left,[],raw_from(left+[part(tid=3,cx=350)]),0.6,now=0.4)
        self.assertFalse(c.generate(now=0.4).ok)

    def test_change_rebuilds_from_current_left_count(self):
        c=self.ready_controller();self.generate_ok(c)
        left=[part("A045",tid=2,cx=300),part("A045",tid=3,cx=400)]
        c.observe(left,[],raw_from(left),0.6,now=0.4)
        c.observe(left,[],raw_from(left),0.6,now=0.6)
        self.generate_ok(c,change=True)
        self.assertEqual(Counter(s.code for s in c.guide.slots),Counter({"A045":2}))

    def test_total_stays_frozen_as_parts_move_to_the_right(self):
        c=self.ready_controller([part(),part("A045",tid=2,cx=300)])
        self.generate_ok(c)
        c.observe([], [part(cx=900),part("A045",tid=2,cx=1000)],[],0.6,now=0.4)
        self.assertEqual(c.report()["total"],2)

    def test_old_frames_cannot_authorise_change(self):
        c=self.ready_controller();self.generate_ok(c)
        self.assertFalse(c.generate(change=True,now=100).ok)

    def test_verification_does_not_generate_a_composition(self):
        c=self.ready_controller()
        self.assertIsNone(c.toggle_verification())
        self.assertFalse(c.guide.generated)


class ReportTests(Fixture):
    def test_missing_identical_parts_use_quantities_not_just_class_sets(self):
        c=self.ready_controller()
        c.guide.generated=True
        c.guide.slots=[CadSlot(0,"A003",800,300),CadSlot(1,"A003",850,300)]
        c.guide.slots[0].completed=True
        c.left_parts=[part(),part(tid=2,cx=200)]
        report=c.report()
        self.assertEqual(report["remaining"],Counter({"A003":1}))
        self.assertEqual(len(report["left_matches"]),1)

    def test_completed_classes_and_extras_not_highlighted(self):
        c=self.ready_controller();self.assertTrue(self.make(c.guide,["A003"]))
        c.guide.slots[0].completed=True
        c.left_parts=[part(),part("A004",tid=2,cx=300)]
        self.assertEqual(c.report()["left_matches"],[])

    def test_misplaced_right_piece_not_claimed_as_completed_or_left_target(self):
        c=self.ready_controller();self.assertTrue(self.make(c.guide,["A003","A003"]))
        c.right_parts=[part(tid=4,cx=1000)]
        c.left_parts=[part(),part(tid=2,cx=200)]
        r=c.report()
        self.assertEqual(r["done"],0)
        self.assertEqual(r["right_pending"],Counter({"A003":1}))
        self.assertEqual(len(r["left_matches"]),1)

    def test_unlocated_piece_reported_without_inventing_location(self):
        c=self.ready_controller();self.assertTrue(self.make(c.guide,["A003","A004"]))
        r=c.report()
        self.assertEqual(r["unlocated"],Counter({"A004":1}))
        self.assertIn("Non localizzati",c.verification_text())

    def test_toggle_reports_and_hides_without_microphone(self):
        c=self.ready_controller();self.assertTrue(self.make(c.guide,["A003"]))
        text=c.toggle_verification()
        self.assertIn("sul piano sinistro",text)
        self.assertTrue(c.verification_visible)
        self.assertIsNone(c.toggle_verification())
        self.assertFalse(c.verification_visible)


class GuardTests(unittest.TestCase):
    def test_both_frame_count_and_duration_required(self):
        guard=EmptyAreaGuard(min_frames=2,min_seconds=1)
        guard.observe(False,0);guard.observe(False,0.1)
        self.assertFalse(guard.ready(0.1))
        guard.observe(False,1.1)
        self.assertTrue(guard.ready(1.1))

    def test_gap_or_failed_frame_resets_clearance(self):
        guard=EmptyAreaGuard(min_frames=2,min_seconds=0,max_gap=1)
        guard.observe(False,0);guard.observe(False,0.1)
        self.assertTrue(guard.ready(0.1))
        guard.observe(False,3)
        self.assertFalse(guard.ready(3))
        guard.observe(False,3.2,valid=False)
        self.assertFalse(guard.ready(3.2))


class UIAndAdapterTests(Fixture):
    def test_highlights_never_draw_in_right_half(self):
        image=np.zeros((200,400,3),np.uint8)
        draw_left_highlights(image,[part(cx=185,cy=100)],200)
        self.assertTrue(np.any(image[:,:200]))
        self.assertFalse(np.any(image[:,200:]))

    def test_mouse_and_keyboard_use_same_action_names(self):
        c=self.ready_controller();ui=CompositionUI("test")
        view=ui.draw(np.zeros((720,1280,3),np.uint8),c)
        self.assertEqual(view.shape,(720,1280,3))
        for action,(x1,y1,x2,y2) in ui.buttons:
            ui.mouse_callback(cv2.EVENT_LBUTTONDOWN,(x1+x2)//2,(y1+y2)//2,0)
            self.assertEqual(ui.pop_actions(),[action])

    def test_snapshot_includes_no_id_detections_and_reset_invalidates(self):
        class Tensor:
            def __init__(self,x): self.x=np.array(x)
            def cpu(self): return self
            def numpy(self): return self.x
        boxes=SimpleNamespace(xyxy=Tensor([[700,100,720,120]]),cls=Tensor([0]),
                              conf=Tensor([0.15]),is_track=False)
        adapter=RawDetectionSnapshot({0:"A045"})
        adapter(SimpleNamespace(results=[SimpleNamespace(boxes=boxes)]))
        self.assertEqual(len(adapter.detections),1)
        self.assertNotIn("tid",adapter.detections[0])
        adapter.reset();self.assertIsNone(adapter.detections)
        boxes.is_track=True
        adapter(SimpleNamespace(results=[SimpleNamespace(boxes=boxes)]))
        self.assertIsNone(adapter.detections)

    def test_plane_depth_zero_holes_excluded(self):
        depth=np.full((200,400),600,np.uint16);depth[:,0:200]=1000;depth[80:100,220:240]=0
        self.assertAlmostEqual(estimate_plane_z(depth,0.001,200),0.6)
        self.assertIsNone(estimate_plane_z(np.zeros_like(depth),0.001,200))

    def test_scene_updates_even_with_missing_depth_and_removes_old_ids(self):
        scene=SceneState();scene.update_part(1,"A003",(10,20),(0,0,20,40),(None,None,None))
        self.assertEqual(scene.snapshot()[1]["pixel_xy"],(10,20))
        scene.sync_with_active(set());self.assertEqual(scene.snapshot(),{})

    def test_voice_claim_rejects_double_trigger_without_audio(self):
        import threading
        from voice_runtime import VoiceRuntime

        runtime=VoiceRuntime.__new__(VoiceRuntime)
        runtime._lock=threading.RLock();runtime._wake=threading.Event()
        runtime._state="IDLE";runtime._closed=False;runtime._sequence=0
        runtime._pending=None;runtime._cancel_at=None;runtime._last_error=""
        self.assertTrue(runtime.submit("say", "riepilogo"))
        self.assertFalse(runtime.submit("query"))

    def test_runtime_has_no_session_logging_or_video_saving(self):
        root=Path(__file__).resolve().parents[1]
        for filename in ["meccano_tracker.py","assembly_guide_cad.py","composition_controller.py"]:
            source=(root/filename).read_text(encoding="utf-8")
            for token in ["SessionLogger","SessionDirector","TlxCollector","VideoWriter", "logger."]:
                self.assertNotIn(token,source,filename)


if __name__ == "__main__":
    unittest.main()
