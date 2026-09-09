import threading
import time
import traceback
import re
from voice_runtime import VoiceRuntime, VoiceCancelled


from parts_catalog import PARTS_CATALOG, build_catalog_text


OLLAMA_URL   = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.1:8b"                                                      

WHISPER_MODEL_SIZE = "base"
WHISPER_LANGUAGE   = "it"

RECORD_SECONDS = 5
SAMPLE_RATE    = 16000

TTS_RATE = 175


USE_LLAMA_FOR_PARSING = True


class SceneState:


    def __init__(self):
        self._lock = threading.Lock()
        self._parts = {}
        self._frame_shape = (1080, 1920)

    def update_part(self, tid, class_name, pixel_xy, bbox, world_xyz):
        with self._lock:
            self._parts[tid] = {
                "class_name": class_name,
                "pixel_xy": pixel_xy,
                "bbox": bbox,
                "world_xyz": world_xyz,
            }

    def sync_with_active(self, active_locked_ids):
        with self._lock:
            for tid in list(self._parts.keys()):
                if tid not in active_locked_ids:
                    self._parts.pop(tid, None)

    def snapshot(self):
        with self._lock:
            return {tid: dict(p) for tid, p in self._parts.items()}

    def known_classes(self):

        with self._lock:
            return {p["class_name"] for p in self._parts.values()}

    def set_frame_shape(self, h, w):
        self._frame_shape = (h, w)

    def get_frame_shape(self):
        return self._frame_shape


def _cm_to_words(value_cm):


    return str(int(round(abs(value_cm))))


def describe_position(world_xyz):


    X, Y, Z = world_xyz
    x_cm = X * 100.0
    y_cm = Y * 100.0
    z_cm = Z * 100.0


    if abs(x_cm) < 2:
        x_part = "circa al centro orizzontalmente"
    else:
        side = "a destra" if x_cm > 0 else "a sinistra"
        x_part = f"a {_cm_to_words(x_cm)} centimetri {side}"


    if abs(y_cm) < 2:
        y_part = "circa al centro verticalmente"
    else:
        vert = "in basso" if y_cm > 0 else "in alto"
        y_part = f"{_cm_to_words(y_cm)} centimetri {vert}"


    z_part = f"a una profondita' di {_cm_to_words(z_cm)} centimetri"

    return f"{x_part}, {y_part}, {z_part}"


_WORD_DIGITS = {
    "zero": "0", "uno": "1", "due": "2", "tre": "3", "quattro": "4",
    "cinque": "5", "sei": "6", "sette": "7", "otto": "8", "nove": "9",
}


_WORD_NUMBERS = {
    "cento": 100, "duecento": 200, "trecento": 300, "quattrocento": 400,
    "cinquecento": 500, "seicento": 600, "settecento": 700,
    "ottocento": 800, "novecento": 900,
    "venti": 20, "ventuno": 21, "ventidue": 22, "ventitre": 23, "ventitré": 23,
    "ventiquattro": 24, "venticinque": 25, "ventisei": 26, "ventisette": 27,
    "ventotto": 28, "ventinove": 29,
    "trenta": 30, "quaranta": 40, "cinquanta": 50, "sessanta": 60,
    "settanta": 70, "ottanta": 80, "novanta": 90,
    "dieci": 10, "undici": 11, "dodici": 12, "tredici": 13, "quattordici": 14,
    "quindici": 15, "sedici": 16, "diciassette": 17, "diciotto": 18,
    "diciannove": 19,
    "uno": 1, "due": 2, "tre": 3, "quattro": 4, "cinque": 5, "sei": 6,
    "sette": 7, "otto": 8, "nove": 9,
}


_WORD_LETTERS = {
    "a": "A", "ah": "A", " a ": "A",
    "bi": "B", "be": "B", "b": "B",
    "ci": "C", "ce": "C", "c": "C",
    "di": "D", "de": "D", "d": "D",
}


def _words_to_number(text):


    tokens = text.split()


    digit_seq = ""
    for t in tokens:
        if t in _WORD_DIGITS:
            digit_seq += _WORD_DIGITS[t]
    if len(digit_seq) >= 2:
        return digit_seq


    total = 0
    found = False
    for t in tokens:
        if t in _WORD_NUMBERS:
            val = _WORD_NUMBERS[t]
            found = True
            if val >= 100:
                total += val
            else:
                total += val
    if found and total > 0:
        return str(total)

    return ""


class VoiceAssistant:

    def __init__(self, scene_state: SceneState, all_class_names=None):

        import importlib.util
        if importlib.util.find_spec("pyttsx3") is None:
            raise ImportError("pyttsx3 assente: installa requirements_voice.txt")
        self.scene = scene_state
        self.all_class_names = set(all_class_names or [])
        self._runtime = VoiceRuntime(scene_state, self.all_class_names, _voice_worker)

    @property
    def state(self):
        return self._runtime.state

    @property
    def last_error(self):
        return self._runtime.last_error

    def _set_state(self, state):

        self._connection.send(("state", self._job_id, state))

    def is_busy(self):
        return self._runtime.is_busy()

    def trigger(self):
        return self._runtime.submit("query")

    def say_async(self, text, *, interrupt=False, tag=None):
        return self._runtime.submit("say", text, interrupt=interrupt, tag=tag)

    def stop(self):
        return self._runtime.stop()

    def cancel_tag(self, tag):
        return self._runtime.cancel_tag(tag)

    def close(self):
        self._runtime.close()

    def _check_cancelled(self):
        if self._cancel_event.is_set():
            raise VoiceCancelled()

    def _ensure_whisper(self):
        self._check_cancelled()
        if self.whisper is None:
            self._set_state("STARTING")
            from faster_whisper import WhisperModel
            print(f"[VOICE] Carico Whisper '{WHISPER_MODEL_SIZE}' nel processo vocale...")
            self.whisper = WhisperModel(WHISPER_MODEL_SIZE, device="auto", compute_type="auto")
        self._check_cancelled()


    def _run_pipeline(self):
        try:
            self._ensure_whisper()
            self._set_state("LISTENING")
            audio = self._record_audio()
            self._check_cancelled()
            self._set_state("THINKING")
            query = self._transcribe(audio).strip()
            self._check_cancelled()
            if not query:
                self._set_state("SPEAKING")
                self._speak("Non ho capito, riprova.")
                return
            print(f"[VOICE] Query: {query!r}")


            scene = self.scene.snapshot()
            scene_classes = {p["class_name"] for p in scene.values()}
            print(f"[VOICE] Classi in scena: {scene_classes or '(nessuna)'}")


            target_class = self._extract_class(query, scene_classes=scene_classes)
            self._check_cancelled()
            print(f"[VOICE] Classe individuata: {target_class!r}")

            if target_class is None:
                self._set_state("SPEAKING")
                self._speak("Non ho capito di quale pezzo stai parlando. "
                            "Puoi ripetere il codice o descriverlo meglio?")
                return


            scene = self.scene.snapshot()
            self._check_cancelled()

            matching = [(tid, p) for tid, p in scene.items()
                        if p["class_name"].upper() == target_class.upper()]


            answer = self._build_answer(target_class, matching)
            print(f"[VOICE] Risposta: {answer!r}")

            self._set_state("SPEAKING")
            self._speak(answer)

        except VoiceCancelled:
            return
        except Exception as e:
            self._connection.send(("error", self._job_id, str(e)))
            print(f"[VOICE] ERRORE pipeline: {e}")
            traceback.print_exc()
            try:
                self._check_cancelled()
                self._set_state("SPEAKING")
                self._speak("Si e' verificato un errore.")
            except Exception:
                pass
        finally:
            self._set_state("IDLE")


    def _build_answer(self, target_class, matching):


        hint = self._short_hint(target_class)
        spelled = self._spell_class(target_class)
        name = f"{spelled}{hint}"

        if not matching:
            return (f"Il pezzo {name} non e' presente nella scena al momento.")

        if len(matching) == 1:
            _, p = matching[0]
            pos = self._describe_part_position(p)
            return (f"Il pezzo {name} si trova {pos}.")


        parts = []
        for i, (_, p) in enumerate(matching, start=1):
            pos = self._describe_part_position(p)
            parts.append(f"il {_ordinal_it(i)} {pos}")
        joined = "; ".join(parts)
        return (f"Ci sono {len(matching)} pezzi {name}: {joined}.")

    def _describe_part_position(self, part):
        world = part.get("world_xyz")
        if world is not None and len(world) == 3 and all(x is not None for x in world):
            return describe_position(world)
        h, w = self.scene.get_frame_shape()
        x, y = part["pixel_xy"]
        side = "sul piano sinistro" if x < w / 2 else "sul piano destro"
        level = "in alto" if y < h / 3 else ("in basso" if y > 2 * h / 3 else "al centro")
        return f"{side}, {level}; la profondita' non e' disponibile"

    def _short_hint(self, code):

        info = PARTS_CATALOG.get(code)
        if not info:
            return ""

        common = info["sinonimi"][0] if info.get("sinonimi") else None
        if common:
            return f", cioe' il {common},"
        return ""


    def _spell_class(self, cls):


        m = re.match(r"^([A-Za-z]+)(\d+)$", cls)
        if m:
            return f"{m.group(1).upper()} {m.group(2)}"
        return cls


    def _extract_class(self, query, scene_classes=None):


        q = query.lower()


        num_to_classes = {}
        for known in self.all_class_names:
            kn = re.sub(r"[^0-9]", "", known)
            num_to_classes.setdefault(kn, []).append(known)


        for letter, number in re.findall(r"([a-zA-Z])\s*[-_]?\s*(\d{2,4})", q):
            cand = f"{letter.upper()}{number}"
            for known in self.all_class_names:
                if known.upper() == cand:
                    print(f"[VOICE] match strategia 1 (codice formato): {known}")
                    return known


        for number in re.findall(r"\b(\d{2,4})\b", q):
            if number in num_to_classes:

                cands = num_to_classes[number]
                if len(cands) == 1:
                    print(f"[VOICE] match strategia 2 (numero formato): {cands[0]}")
                    return cands[0]

                disamb = self._disambiguate_by_letter(q, cands)
                if disamb:
                    print(f"[VOICE] match strategia 2+lettera: {disamb}")
                    return disamb


        number_words = _words_to_number(q)
        if number_words and number_words in num_to_classes:
            cands = num_to_classes[number_words]
            print(f"[VOICE] numero da parole: {number_words!r} -> candidati {cands}")
            if len(cands) == 1:
                return cands[0]
            disamb = self._disambiguate_by_letter(q, cands)
            if disamb:
                return disamb

            print(f"[VOICE] piu' classi con numero {number_words}, scelgo {cands[0]}")
            return cands[0]


        if USE_LLAMA_FOR_PARSING:
            try:

                if scene_classes:
                    res = self._extract_class_llama(query, restrict_to=scene_classes)
                    if res:
                        print(f"[VOICE] match strategia 5 (descrizione, in scena): {res}")
                        return res

                res = self._extract_class_llama(query, restrict_to=None)
                if res:
                    print(f"[VOICE] match strategia 5 (descrizione, catalogo): {res}")
                    return res
            except VoiceCancelled:
                raise
            except Exception as e:
                print(f"[VOICE] Strategia 5 (LLM) fallita: {e}")

        print("[VOICE] Nessuna strategia di parsing ha funzionato.")
        return None

    def _disambiguate_by_letter(self, query_lower, candidates):


        heard_letters = set()

        for w in query_lower.split():
            if w in _WORD_LETTERS:
                heard_letters.add(_WORD_LETTERS[w])

        for letter in re.findall(r"\b([a-zA-Z])\b", query_lower):
            heard_letters.add(letter.upper())

        for cand in candidates:
            cand_letter = cand[0].upper()
            if cand_letter in heard_letters:
                return cand
        return None

    def _extract_class_llama(self, query, restrict_to=None):


        import requests
        self._check_cancelled()

        catalog_text = build_catalog_text(only_classes=restrict_to)


        if restrict_to:
            valid_codes = sorted(restrict_to)
        else:
            valid_codes = sorted(c for c in PARTS_CATALOG.keys()
                                 if c in self.all_class_names)
        codes_str = ", ".join(valid_codes)

        system = (
            "Sei un assistente che identifica pezzi di un kit Meccano a partire "
            "dalla descrizione a voce di un operatore. Di seguito il CATALOGO "
            "dei pezzi con descrizione e modi alternativi di chiamarli:\n\n"
            f"{catalog_text}\n\n"
            "L'operatore ti dara' una descrizione qualitativa di UN pezzo "
            "(colore, forma, numero di buchi, tipo). Il tuo compito e' capire "
            "di quale pezzo si tratta e rispondere SOLO con il suo codice, "
            f"scelto ESATTAMENTE da questa lista: {codes_str}. "
            "Presta attenzione ai dettagli distintivi: colore (rosso, grigio, "
            "bianco, nero), numero di buchi, forma (dritto, a gomito/L, storto), "
            "e presenza o assenza di scanalature. "
            "Rispondi con il solo codice, senza spiegazioni. Se la descrizione "
            "non corrisponde a nessun pezzo del catalogo, rispondi: NESSUNO."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f'Descrizione dell\'operatore: "{query}"'},
        ]
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "messages": messages,
                  "stream": False, "options": {"temperature": 0.0}},
            timeout=45,
        )
        self._check_cancelled()
        r.raise_for_status()
        out = r.json()["message"]["content"].strip().upper()
        out = re.sub(r"[^A-Z0-9]", "", out)                                     
        print(f"[VOICE] LLM ha proposto il codice: {out!r}")

        for code in valid_codes:
            if code.upper() == out:
                return code
        return None


    def _record_audio(self):
        import sounddevice as sd
        self._check_cancelled()
        print(f"[VOICE] Registro {RECORD_SECONDS}s. Parla...")
        try:
            audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                           channels=1, dtype="float32", blocking=False)
            while sd.get_stream().active:
                if self._cancel_event.wait(0.02):
                    raise VoiceCancelled()
            self._check_cancelled()
            sd.wait()
            return audio.flatten()
        finally:
            sd.stop()

    def _transcribe(self, audio):
        self._check_cancelled()
        print("[VOICE] Trascrivo...")
        segments, _ = self.whisper.transcribe(
            audio, language=WHISPER_LANGUAGE, beam_size=5, vad_filter=True)
        words = []
        for segment in segments:
            self._check_cancelled()
            words.append(segment.text)
        self._check_cancelled()
        return " ".join(words)

    def _speak(self, text):
        import pyttsx3
        self._check_cancelled()

        if self._tts is None:
            self._tts = pyttsx3.init()
            self._tts.setProperty("rate", TTS_RATE)
            for voice in self._tts.getProperty("voices"):
                name = (str(voice.name)+" "+str(voice.id or "")).lower()
                if any(token in name for token in ("italian", "italia", "it_", "it-")):
                    self._tts.setProperty("voice", voice.id)
                    break
        engine = self._tts
        loop_started = False
        errors = []
        error_token = engine.connect("error", lambda name, exception: errors.append(exception))
        try:
            self._check_cancelled()
            print(f"[VOICE] Parlo: {text!r}")
            engine.say(text)
            engine.startLoop(False)
            loop_started = True

            while True:
                self._check_cancelled()
                engine.iterate()
                if errors:
                    raise RuntimeError(str(errors[0]))
                if not engine.isBusy():
                    break
                self._cancel_event.wait(0.01)
        finally:
            engine.stop()
            if loop_started:
                engine.endLoop()
            engine.disconnect(error_token)


class _RemoteScene:

    def __init__(self, connection, cancel, job):
        self.connection, self.cancel, self.job = connection, cancel, job
        self.shape = (1080, 1920)

    def snapshot(self):
        self.connection.send(("scene", self.job))
        while not self.cancel.is_set():
            if self.connection.poll(0.02):
                kind, job, shape, parts = self.connection.recv()
                if kind == "scene" and job == self.job:
                    self.shape = shape
                    return parts
        raise VoiceCancelled()

    def get_frame_shape(self):
        return self.shape


def _voice_worker(connection, cancel, class_names):

    assistant = VoiceAssistant.__new__(VoiceAssistant)
    assistant.all_class_names = set(class_names)
    assistant.whisper = None
    assistant._tts = None
    assistant._connection = connection
    assistant._cancel_event = cancel
    try:
        while not cancel.is_set():
            if not connection.poll(0.02):
                continue
            job, kind, text = connection.recv()
            assistant._job_id = job
            assistant.scene = _RemoteScene(connection, cancel, job)
            try:
                assistant._check_cancelled()
                if kind == "query":
                    assistant._run_pipeline()
                else:
                    assistant._set_state("SPEAKING")
                    assistant._speak(text)
            except VoiceCancelled:
                break
            except Exception as exc:
                connection.send(("error", job, str(exc)))
            if not cancel.is_set():
                connection.send(("done", job))
    except (EOFError, BrokenPipeError, OSError):
        pass
    finally:
        if assistant._tts is not None:
            try:
                assistant._tts.stop()
            except Exception:
                pass
        connection.close()


def _ordinal_it(n):
    ordinals = {1: "primo", 2: "secondo", 3: "terzo", 4: "quarto",
                5: "quinto", 6: "sesto", 7: "settimo", 8: "ottavo",
                9: "nono", 10: "decimo"}
    return ordinals.get(n, f"numero {n}")
