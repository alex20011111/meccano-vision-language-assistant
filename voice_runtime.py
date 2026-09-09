import multiprocessing as mp
import threading
import time


class VoiceCancelled(Exception):
    pass


class VoiceRuntime:
    def __init__(self, scene, class_names, worker_target, *, stop_grace=0.25):
        self.scene = scene
        self.class_names = list(class_names)
        self._target = worker_target
        self._context = mp.get_context("spawn")
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._closed = False
        self._state = "IDLE"
        self._last_error = ""
        self._sequence = 0
        self._pending = None
        self._current = None
        self._process = None
        self._connection = None
        self._cancel = None
        self._cancel_at = None
        self._terminate_at = None
        self._stop_grace = max(0.0, float(stop_grace))
        self._thread = threading.Thread(target=self._supervise,
                                        name="meccano-voice-supervisor", daemon=True)
        self._thread.start()

    @property
    def state(self):
        with self._lock:
            return self._state

    @property
    def last_error(self):
        with self._lock:
            return self._last_error

    def is_busy(self):
        return self.state != "IDLE"

    def submit(self, kind, text="", *, interrupt=False, tag=None):
        if kind not in {"query", "say"}:
            raise ValueError("Comando vocale non valido.")
        if kind == "say" and not str(text).strip():
            return False
        with self._lock:
            if self._closed:
                return False
            if self._state != "IDLE":
                if not interrupt:
                    return False
                self._request_stop_locked()
            self._sequence += 1
            self._pending = (self._sequence, kind, str(text), tag)
            self._last_error = ""
            if self._cancel_at is None:
                self._state = "STARTING"
            self._wake.set()
            return True

    def _request_stop_locked(self):
        self._pending = None

        self._current = None
        if self._process is not None:
            if self._cancel_at is None:
                self._cancel.set()
                self._cancel_at = time.monotonic()
            self._state = "STOPPING"
        else:
            self._state = "IDLE"

    def stop(self):

        with self._lock:
            was_busy = self._state != "IDLE"
            self._request_stop_locked()
            self._last_error = ""
            self._wake.set()
            return was_busy

    def cancel_tag(self, tag):

        with self._lock:
            pending_matches = self._pending is not None and self._pending[3] == tag
            current_matches = self._current is not None and self._current[3] == tag
            if current_matches:
                self._request_stop_locked()
                self._wake.set()
                return True
            if pending_matches:
                self._pending = None
                if self._current is None and self._cancel_at is None:
                    self._state = "IDLE"
                return True
            return False

    def _spawn_locked(self):
        parent, child = self._context.Pipe(duplex=True)
        cancel = self._context.Event()
        process = self._context.Process(target=self._target,
                                        args=(child, cancel, self.class_names),
                                        name="MeccanoVoice", daemon=True)
        try:
            process.start()
        except Exception:
            parent.close()
            child.close()
            process.close()
            raise
        child.close()
        self._process, self._connection, self._cancel = process, parent, cancel

    def _dispose_locked(self):
        process, connection = self._process, self._connection
        if connection is not None:
            connection.close()
        if process is not None:
            process.join(timeout=0)
            process.close()
        self._process = self._connection = self._cancel = None
        self._cancel_at = self._terminate_at = None
        self._current = None
        self._state = "STARTING" if self._pending else "IDLE"

    def _tick_locked(self):
        if self._process is not None:
            if not self._process.is_alive():
                if self._current is not None and self._cancel_at is None:
                    self._last_error = ("Il processo vocale si e' chiuso in modo inatteso "
                                        f"(codice {self._process.exitcode}). Premi R per riprovare.")
                self._dispose_locked()
            elif self._cancel_at is not None:
                now = time.monotonic()
                if self._terminate_at is None and now-self._cancel_at >= self._stop_grace:
                    self._process.terminate()
                    self._terminate_at = now
                elif self._terminate_at is not None and now-self._terminate_at >= 0.5:
                    self._process.kill()
                    self._terminate_at = now
                return
            else:

                while self._connection.poll():
                    message = self._connection.recv()
                    kind, job = message[:2]
                    if self._current is None or job != self._current[0]:
                        continue
                    if kind == "state" and message[2] != "IDLE":
                        self._state = message[2]
                    elif kind == "scene":
                        self._connection.send(("scene", job, self.scene.get_frame_shape(),
                                               self.scene.snapshot()))
                    elif kind == "error":
                        self._last_error = str(message[2])
                    elif kind == "done":
                        self._current = None
                        self._state = "IDLE"
        if self._pending is not None and self._current is None and not self._closed:
            if self._process is None:
                self._spawn_locked()
            self._current, self._pending = self._pending, None
            job, kind, text, _tag = self._current
            self._connection.send((job, kind, text))
            self._state = "STARTING"

    def _supervise(self):
        while True:
            self._wake.wait(0.02)
            self._wake.clear()
            with self._lock:
                try:
                    self._tick_locked()
                except (EOFError, OSError, BrokenPipeError) as exc:
                    self._last_error = f"Comunicazione vocale interrotta: {exc}"
                    self._request_stop_locked()
                except Exception as exc:
                    self._last_error = f"Errore del processo vocale: {exc}"
                    self._request_stop_locked()
                if self._closed and self._process is None:
                    return

    def close(self):

        with self._lock:
            if not self._closed:
                self._closed = True
                self._request_stop_locked()
                self._wake.set()
        self._thread.join(timeout=3.0)
        if self._thread.is_alive():

            with self._lock:
                if self._process is not None and self._process.is_alive():
                    self._process.kill()
            self._thread.join(timeout=1.0)
