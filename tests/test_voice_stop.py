import threading
import time
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch
import numpy as np

from voice_assistant import SceneState, VoiceAssistant
from voice_runtime import VoiceRuntime, VoiceCancelled


def simulated_worker(connection, cancel, class_names):

    try:
        while not cancel.is_set():
            if not connection.poll(0.01):
                continue
            job, kind, text = connection.recv()
            if text == "instant":
                connection.send(("state",job,"SPEAKING"))
                connection.send(("done",job))
            elif text == "scene":
                connection.send(("scene",job))
                result=connection.recv()
                if result[3][9]["class_name"] != "A003":
                    connection.send(("error",job,"snapshot non aggiornato"))
                connection.send(("done",job))
            elif text == "fail":
                connection.send(("error",job,"errore simulato"))
                connection.send(("done",job))
            elif text == "crash":
                import os
                os._exit(7)
            elif text.startswith("block:"):
                connection.send(("state",job,text.split(":")[1]))
                while True:
                    time.sleep(0.01)
            else:
                connection.send(("state",job,"LISTENING" if kind=="query" else "SPEAKING"))
                cancel.wait(15)

                connection.send(("state",job,"SPEAKING"))
    except (EOFError,BrokenPipeError,OSError):
        pass
    finally:
        connection.close()


class RuntimeStopTests(unittest.TestCase):
    def setUp(self):
        self.scene=SceneState()
        self.runtime=VoiceRuntime(self.scene,["A003"],simulated_worker,stop_grace=0.05)

    def tearDown(self):
        self.runtime.close()
        self.assertFalse(self.runtime._thread.is_alive())
        self.assertIsNone(self.runtime._process)

    def wait_for(self,predicate,timeout=8):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if predicate(): return
            time.sleep(0.01)
        self.fail(f"Condizione non raggiunta; stato={self.runtime.state}; errore={self.runtime.last_error}")

    def test_worker_is_lazy_no_process_before_first_request(self):
        self.assertIsNone(self.runtime._process)
        self.assertFalse(self.runtime.is_busy())
        self.assertFalse(self.runtime.stop())

    def test_stop_listening_exits_process_and_rejects_late_state(self):
        self.assertTrue(self.runtime.submit("query"))
        self.wait_for(lambda:self.runtime.state=="LISTENING")
        started=time.monotonic();self.runtime.stop()
        self.assertLess(time.monotonic()-started,0.2)
        self.wait_for(lambda:self.runtime._process is None)
        self.assertEqual(self.runtime.state,"IDLE")
        self.assertFalse(self.runtime.last_error)

    def test_stop_forces_exit_of_blocked_transcription(self):
        self.runtime.submit("say","block:THINKING")
        self.wait_for(lambda:self.runtime.state=="THINKING")
        self.runtime.stop()
        self.wait_for(lambda:self.runtime._process is None)
        self.assertEqual(self.runtime.state,"IDLE")

    def test_stop_forces_exit_of_blocked_tts(self):
        self.runtime.submit("say","block:SPEAKING")
        self.wait_for(lambda:self.runtime.state=="SPEAKING")
        self.runtime.stop()
        self.wait_for(lambda:self.runtime._process is None)
        self.assertEqual(self.runtime.state,"IDLE")

    def test_stop_during_startup_cancels_queued_work(self):
        self.runtime.submit("query")
        self.runtime.stop()
        self.wait_for(lambda:self.runtime._process is None and not self.runtime.is_busy())
        self.assertIsNone(self.runtime._pending)

    def test_priority_warning_replaces_busy_job_then_stop_cancels_it(self):
        self.runtime.submit("query")
        self.wait_for(lambda:self.runtime.state=="LISTENING")
        with self.runtime._lock:
            self.assertTrue(self.runtime.submit("say","warning",interrupt=True,tag="return_parts"))
            self.runtime.stop()
        self.wait_for(lambda:self.runtime._process is None)
        self.assertIsNone(self.runtime._pending)
        self.assertEqual(self.runtime.state,"IDLE")

    def test_priority_warning_runs_after_old_process_is_reaped(self):
        self.runtime.submit("say","block:THINKING")
        self.wait_for(lambda:self.runtime.state=="THINKING")
        pid=self.runtime._process.pid
        self.runtime.submit("say","warning",interrupt=True,tag="return_parts")
        self.wait_for(lambda:self.runtime.state=="SPEAKING" and self.runtime._process.pid!=pid)
        self.assertEqual(self.runtime._current[3],"return_parts")

    def test_cancel_return_tag_does_not_stop_unrelated_query(self):
        self.runtime.submit("query")
        self.wait_for(lambda:self.runtime.state=="LISTENING")
        self.assertFalse(self.runtime.cancel_tag("return_parts"))
        self.assertEqual(self.runtime.state,"LISTENING")

    def test_cancel_tag_stops_own_warning(self):
        self.runtime.submit("say","warning",tag="return_parts")
        self.wait_for(lambda:self.runtime.state=="SPEAKING")
        self.assertTrue(self.runtime.cancel_tag("return_parts"))
        self.wait_for(lambda:self.runtime._process is None)

    def test_new_query_works_after_stop(self):
        self.runtime.submit("say","block:THINKING")
        self.wait_for(lambda:self.runtime.state=="THINKING")
        self.runtime.stop();self.wait_for(lambda:self.runtime._process is None)
        self.assertTrue(self.runtime.submit("query"))
        self.wait_for(lambda:self.runtime.state=="LISTENING")

    def test_concurrent_clicks_claim_only_one_request(self):
        results=[]
        threads=[threading.Thread(target=lambda:results.append(self.runtime.submit("query"))) for _ in range(8)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(sum(results),1)

    def test_worker_reads_current_scene_from_parent(self):
        self.scene.update_part(9,"A003",(10,20),(0,0,20,40),(None,None,None))
        self.runtime.submit("say","scene")
        self.wait_for(lambda:not self.runtime.is_busy())
        self.assertEqual(self.runtime.last_error,"")

    def test_runtime_error_is_reported_and_next_request_can_recover(self):
        self.runtime.submit("say","fail")
        self.wait_for(lambda:not self.runtime.is_busy())
        self.assertEqual(self.runtime.last_error,"errore simulato")
        self.assertTrue(self.runtime.submit("say","instant"))
        self.wait_for(lambda:not self.runtime.is_busy())
        self.assertEqual(self.runtime.last_error,"")

    def test_crash_does_not_block_subsequent_voice_or_tracker(self):
        self.runtime.submit("say","crash")
        self.wait_for(lambda:not self.runtime.is_busy())
        self.assertTrue(self.runtime.last_error)
        self.assertTrue(self.runtime.submit("query"))
        self.wait_for(lambda:self.runtime.state=="LISTENING")


class AudioAdapterStopTests(unittest.TestCase):
    def worker(self):
        v=VoiceAssistant.__new__(VoiceAssistant)
        v._cancel_event=threading.Event()
        v._tts=None
        v._connection=SimpleNamespace(send=lambda x:None)
        v._job_id=1
        return v

    def test_mic_stop_releases_stream_and_discards_partial_recording(self):
        v=self.worker();calls=[]
        def record(*args,**kwargs):
            v._cancel_event.set()
            return np.zeros((10,1),np.float32)
        fake=SimpleNamespace(rec=record,get_stream=lambda:SimpleNamespace(active=True),
                             wait=lambda: calls.append("wait"),stop=lambda:calls.append("stop"))
        with patch.dict(sys.modules,{"sounddevice":fake}):
            with self.assertRaises(VoiceCancelled):v._record_audio()
        self.assertEqual(calls,["stop"])

    def test_stop_before_microphone_never_opens_it(self):
        v=self.worker();v._cancel_event.set()
        from unittest.mock import Mock
        fake=Mock()
        with patch.dict(sys.modules,{"sounddevice":fake}):
            with self.assertRaises(VoiceCancelled):v._record_audio()
        fake.rec.assert_not_called()

    def test_tts_stop_runs_in_worker_loop_and_purges_queue(self):
        v=self.worker();calls=[]
        class Engine:
            def setProperty(self,*a):pass
            def getProperty(self,*a):return []
            def connect(self,*a):return 5
            def say(self,text):calls.append("say")
            def startLoop(self,own):calls.append(("loop",own))
            def iterate(self):v._cancel_event.set()
            def isBusy(self):return True
            def stop(self):calls.append("stop")
            def endLoop(self):calls.append("end")
            def disconnect(self,token):calls.append(("disconnect",token))
        with patch.dict(sys.modules,{"pyttsx3":SimpleNamespace(init=lambda:Engine())}):
            with self.assertRaises(VoiceCancelled):v._speak("frase di prova")
        self.assertIn(("loop",False),calls)
        self.assertEqual(calls[-3:],["stop","end",("disconnect",5)])

    def test_transcription_checks_cancel_between_segments(self):
        v=self.worker()
        def segments():
            yield SimpleNamespace(text="A")
            v._cancel_event.set()
            yield SimpleNamespace(text="003")
        v.whisper=SimpleNamespace(transcribe=lambda *a,**k:(segments(),None))
        with self.assertRaises(VoiceCancelled):v._transcribe(np.zeros(100,np.float32))


if __name__=='__main__':unittest.main()
