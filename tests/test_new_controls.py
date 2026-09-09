import ast
import hashlib
import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

import cv2
import numpy as np
from test_composition import Fixture, part, raw_from
from composition_controller import RETURN_PARTS_MESSAGE
from composition_ui import CompositionUI
import meccano_tracker as tracker


class ReturnNoticeTests(Fixture):
    def controller_with_figure(self):
        c = self.ready_controller()
        self.assertTrue(self.make(c.guide, ["A003"]))
        return c

    def occupy(self, c, *, raw_only=False, code="A003", cx=900, valid=True):
        p = part(code, cx=cx)
        c.observe([], [] if raw_only else [p], raw_from([p]), 0.6,
                  now=c._now+0.2, frame_valid=valid)

    def test_no_warning_during_normal_build(self):
        c = self.controller_with_figure(); self.occupy(c)
        c.check_completion()
        self.assertFalse(c.return_warning_visible)
        self.assertIsNone(c.take_return_announcement())

    def test_x_clears_only_composition_and_warns_exact_text(self):
        c = self.controller_with_figure(); self.occupy(c)
        before = list(c.right_parts)
        self.assertTrue(c.finish().ok)
        self.assertFalse(c.guide.generated)
        self.assertEqual(c.guide.slots, [])
        self.assertEqual(c.right_parts, before)
        self.assertEqual(c.return_warning, RETURN_PARTS_MESSAGE)
        self.assertEqual(c.take_return_announcement(), "RIPORTARE I PEZZI NEL PIANO DI PARTENZA")

    def test_x_without_right_parts_does_not_warn(self):
        c = self.controller_with_figure(); c.finish()
        self.assertFalse(c.return_warning_visible)
        self.assertIsNone(c.take_return_announcement())

    def test_raw_without_id_and_piece_outside_silhouettes_warn(self):
        c = self.controller_with_figure(); self.occupy(c, raw_only=True, cx=1100)
        c.finish()
        self.assertEqual(c.return_warning, RETURN_PARTS_MESSAGE)

    def test_crossing_line_with_centre_still_left_warns(self):
        c = self.controller_with_figure(); self.occupy(c, raw_only=True, cx=635)
        c.finish()
        self.assertEqual(c.return_warning, RETURN_PARTS_MESSAGE)

    def test_hand_alone_is_not_reported_as_a_piece(self):
        c = self.controller_with_figure(); self.occupy(c, raw_only=True, code="Hand")
        c.finish()
        self.assertTrue(c.guard.occupied)
        self.assertFalse(c.return_warning_visible)

    def test_completion_warns_but_keeps_silhouettes(self):
        c = self.controller_with_figure(); self.occupy(c)
        c.guide.completed = True
        c.check_completion()
        self.assertTrue(c.guide.generated)
        self.assertTrue(c.guide.slots)
        self.assertEqual(c.take_return_announcement(), RETURN_PARTS_MESSAGE)
        c.check_completion()
        self.assertIsNone(c.take_return_announcement())

    def test_x_after_auto_completion_does_not_duplicate_announcement(self):
        c = self.controller_with_figure(); self.occupy(c)
        c.guide.completed = True; c.check_completion(); c.take_return_announcement()
        c.finish()
        self.assertIsNone(c.take_return_announcement())
        self.assertTrue(c.return_warning_visible)

    def test_notice_survives_invalid_frame_and_single_empty_frame(self):
        c = self.controller_with_figure(); self.occupy(c); c.finish()
        c.observe([], [], None, now=0.6, frame_valid=False)
        self.assertTrue(c.return_warning_visible)
        c.observe([], [], [], now=0.8)
        self.assertTrue(c.return_warning_visible)
        c.observe([], [], [], now=1.1)
        self.assertFalse(c.return_warning_visible)
        self.assertIsNone(c.take_return_announcement())

    def test_x_with_invalid_frame_checks_as_soon_as_camera_returns(self):
        c = self.controller_with_figure()
        c.observe([], [], None, frame_valid=False, now=0.4)
        c.finish()
        self.assertFalse(c.return_warning_visible)
        self.occupy(c, raw_only=True)
        self.assertEqual(c.take_return_announcement(), RETURN_PARTS_MESSAGE)

    def test_repeated_frames_and_x_do_not_loop_speech(self):
        c = self.controller_with_figure(); self.occupy(c); c.finish()
        self.assertIsNotNone(c.take_return_announcement())
        for _ in range(25):
            self.occupy(c); c.finish(); c.check_completion()
            self.assertIsNone(c.take_return_announcement())

    def test_stop_silences_pending_not_written_warning(self):
        c = self.controller_with_figure(); self.occupy(c); c.finish()
        c.silence_return_announcement()
        self.occupy(c)
        self.assertIsNone(c.take_return_announcement())
        self.assertEqual(c.return_warning, RETURN_PARTS_MESSAGE)

    def test_start_after_x_cannot_bypass_occupied_guard(self):
        c = self.controller_with_figure(); self.occupy(c); c.finish()
        self.assertFalse(c.generate(now=c._now).ok)
        self.assertFalse(c.guide.generated)

    def test_new_generation_clears_return_monitor(self):
        c = self.controller_with_figure(); self.occupy(c); c.finish()
        left = [part()]
        for now in (1.0,1.3):
            c.observe(left,[],raw_from(left),0.6,now=now)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(c.generate(now=1.3).ok)
        self.occupy(c)
        self.assertFalse(c.return_warning_visible)

    def test_new_occupancy_episode_gets_one_new_announcement(self):
        c = self.controller_with_figure(); self.occupy(c); c.finish()
        c.take_return_announcement()
        c.observe([],[],[],now=1.0); c.observe([],[],[],now=1.3)
        self.occupy(c)
        self.assertEqual(c.take_return_announcement(), RETURN_PARTS_MESSAGE)

    def test_warning_interrupts_busy_voice_and_clear_cancels_only_its_tag(self):
        c = self.controller_with_figure(); self.occupy(c); c.finish()
        from unittest.mock import Mock
        voice = Mock()
        with contextlib.redirect_stdout(io.StringIO()):
            tracker.dispatch_return_notice(c, voice)
        voice.say_async.assert_called_once_with(RETURN_PARTS_MESSAGE, interrupt=True, tag="return_parts")
        tracker.dispatch_return_notice(c, voice)
        voice.say_async.assert_called_once()
        c.observe([],[],[],now=1.0); c.observe([],[],[],now=1.3)
        tracker.dispatch_return_notice(c, voice)
        voice.cancel_tag.assert_called_once_with("return_parts")


class TrackingAndUIRegressionTests(Fixture):
    def test_boxes_drawn_during_verification_and_after_completion_and_x(self):
        c=self.ready_controller(); self.assertTrue(self.make(c.guide,["A003"]))
        d={"bbox":(880,210,960,240),"tid":42,"locked":True,"raw_cls":0,"stable_cls":0}
        c.guide.slots[0].completed=True
        c.guide.last_matches[c.guide.slots[0].id] = {"tid":42}
        for verify in (False,True):
            c.verification_visible=verify
            with patch.object(tracker,'class_names',{0:"A003"}), patch.object(tracker,'draw_detection',wraps=tracker.draw_detection) as draw:
                image=tracker.draw_tracked_scene(np.zeros((720,1280,3),np.uint8),[d],c.guide,c)
            draw.assert_called_once()
            self.assertTrue(np.any(image[210:241,880:961]))
        c.finish()
        with patch.object(tracker,'class_names',{0:"A003"}), patch.object(tracker,'draw_detection') as draw:
            tracker.draw_tracked_scene(np.zeros((720,1280,3),np.uint8),[d],c.guide,c)
        draw.assert_called_once()

    def test_tracking_labels_include_original_raw_class_feedback(self):
        d={"bbox":(80,100,160,140),"tid":3,"locked":True,"raw_cls":1,"stable_cls":0}
        with patch.object(tracker,'class_names',{0:"A003",1:"A004"}), patch.object(tracker.cv2,'putText') as put:
            tracker.draw_detection(np.zeros((300,400,3),np.uint8),d)
        self.assertEqual(put.call_args.args[1],"ID3 A003 [LOCK]  (raw:A004)")

    def test_stop_and_finish_are_clickable_and_have_uppercase_shortcuts(self):
        c=self.ready_controller(); ui=CompositionUI("test")
        ui.draw(np.zeros((720,1280,3),np.uint8),c)
        actions={a for a,_ in ui.buttons}
        self.assertEqual(actions,{"start","change","verify","voice","stop_voice","finish"})
        for key,action in [('s','stop_voice'),('S','stop_voice'),('x','finish'),('X','finish')]:
            self.assertEqual(tracker.KEY_ACTIONS[ord(key)],action)

    def test_written_banner_survives_stop_and_other_status_messages(self):
        c=self.ready_controller(); c.return_warning_visible=True
        c.message="Voce interrotta."
        ui=CompositionUI("test")
        with patch('composition_ui.put_text') as put:
            ui.draw(np.zeros((720,1280,3),np.uint8),c)
        self.assertIn(RETURN_PARTS_MESSAGE,[call.args[1] for call in put.call_args_list])

    def test_original_tracking_parameters_are_unchanged(self):
        for name,value in {"INFER_CONF":0.1,"INFER_IMGSZ":1280,"INFER_AUGMENT":True,
                           "INFER_IOU":0.7,"DEDUP_IOU":0.6,"HISTORY_SIZE":20,
                           "LOCK_AFTER_FRAMES":15,"LOCK_DOMINANCE":0.7,"MIN_CONF_TO_VOTE":0.35,
                           "HARD_LOCK":True,"GHOST_TTL":35,"GHOST_MAX_DIST":80}.items():
            self.assertEqual(getattr(tracker,name),value,name)

    def test_original_class_stabilizer_is_unchanged(self):
        source=Path(tracker.__file__).read_text(encoding='utf-8')
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='ClassStabilizer')
        digest=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()
        self.assertEqual(digest, '20594ba114848abf39d24b79519bc1c25452904888cb58f11d11606f34955268')


if __name__=='__main__': unittest.main()
