from collections import Counter
from dataclasses import dataclass
import math
import random
import time

NON_PART_CLASSES = frozenset({"hand", "hands", "mano", "mani", "palm", "person"})
INVENTORY_STABLE_FRAMES = 6
RIGHT_CLEAR_FRAMES = 8
RIGHT_CLEAR_SECONDS = 0.8
MAX_OBSERVATION_GAP_SECONDS = 5.0
RETURN_PARTS_MESSAGE = "RIPORTARE I PEZZI NEL PIANO DI PARTENZA"


def is_hand(code):
    return str(code).strip().casefold() in NON_PART_CLASSES


def box_iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = ((a[2] - a[0]) * (a[3] - a[1]) +
             (b[2] - b[0]) * (b[3] - b[1]) - intersection)
    return intersection / union if union > 0 else 0.0


def format_counts(counts):
    return ", ".join(f"{code} x{n}" for code, n in sorted(counts.items()) if n > 0) or "nessuno"


def left_position(part, split_x, height):

    horizontal = ("vicino al bordo sinistro" if part["cx"] < split_x / 3 else
                  "vicino alla linea centrale" if part["cx"] > 2 * split_x / 3 else
                  "nella fascia centrale")
    vertical = ("in alto" if part["cy"] < height / 3 else
                "in basso" if part["cy"] > 2 * height / 3 else "a mezza altezza")
    return f"{vertical}, {horizontal}"


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    message: str


class EmptyAreaGuard:

    def __init__(self, min_frames=RIGHT_CLEAR_FRAMES, min_seconds=RIGHT_CLEAR_SECONDS,
                 max_gap=MAX_OBSERVATION_GAP_SECONDS):
        if min_frames < 1 or min_seconds < 0 or max_gap <= 0:
            raise ValueError("Parametri del controllo di area vuota non validi.")
        self.min_frames = min_frames
        self.min_seconds = min_seconds
        self.max_gap = max_gap
        self.count = 0
        self.since = None
        self.last = None
        self.valid = False
        self.occupied = True

    def observe(self, occupied, now, valid=True):
        gap = self.last is None or now < self.last or now - self.last > self.max_gap
        self.last = now
        self.valid = bool(valid)
        self.occupied = bool(occupied)
        if not valid or occupied:
            self.count = 0
            self.since = None
        else:
            if gap or self.since is None:
                self.count = 0
                self.since = now
            self.count += 1

    def ready(self, now):
        return bool(self.valid and not self.occupied and self.last is not None and
                    0 <= now - self.last <= self.max_gap and self.since is not None and
                    self.count >= self.min_frames and now - self.since >= self.min_seconds)


class CompositionController:
    def __init__(self, guide, stable_frames=INVENTORY_STABLE_FRAMES, guard=None):
        if stable_frames < 1:
            raise ValueError("stable_frames deve essere positivo.")
        self.guide = guide
        self.guard = guard if guard is not None else EmptyAreaGuard()
        self.stable_frames = stable_frames
        self.left_parts = []
        self.right_parts = []
        self.plane_z_m = None
        self.inventory_frames = 0
        self._inventory_signature = None
        self.frame_valid = False
        self.hand_visible = False
        self.unresolved_left = False
        self.verification_visible = False
        self.generation = 0
        self.right_has_parts = False
        self.right_blockers = []
        self.rejected_detections = []
        self._readiness_message = None
        self.return_check_active = False
        self.return_warning_visible = False
        self._return_announcement_pending = False
        self._completion_seen = False
        self.message = "Metti tutti i pezzi a sinistra e lascia libero il piano destro."
        self._now = 0.0
        self._rng = random.SystemRandom()

    @staticmethod
    def _normalise(parts):
        clean, seen = [], set()
        for index, part in enumerate(parts):
            p = dict(part)
            p["class_name"] = str(p.get("class_name", "")).strip().upper()
            if not p["class_name"] or is_hand(p["class_name"]):
                continue
            key = ("tid", p["tid"]) if p.get("tid") is not None else ("row", index)
            if key not in seen:
                clean.append(p)
                seen.add(key)
        return clean

    def observe(self, left_parts, right_parts, raw_detections, plane_z_m=None,
                now=None, frame_valid=True, rejected_detections=None):


        now = time.monotonic() if now is None else now
        self._now = now
        self.left_parts = self._normalise(left_parts)
        self.right_parts = self._normalise(right_parts)
        self.plane_z_m = plane_z_m
        self.frame_valid = bool(frame_valid and raw_detections is not None)
        raw = raw_detections or []
        self.rejected_detections = list(rejected_detections or [])
        self.hand_visible = any(is_hand(p.get("class_name")) for p in raw)
        self.right_blockers = []
        valid_raw = []
        for detection in raw:
            box = self._valid_box(detection.get("bbox"))
            if box is None:
                self.frame_valid = False
                continue
            d = dict(detection, bbox=box)
            valid_raw.append(d)
            self._add_right_blocker(d)


        for part in self.left_parts + self.right_parts:
            box = self._valid_box(part.get("bbox"))
            if box is None:
                self.frame_valid = False
                continue
            self._add_right_blocker(dict(part, bbox=box, source="tracking"))
        occupied = bool(self.right_blockers)
        self.right_has_parts = any(not is_hand(p.get("class_name"))
                                   for p in self.right_blockers)
        self.guard.observe(occupied, now, valid=self.frame_valid)
        self._update_return_warning()


        raw_left = [d for d in valid_raw if not is_hand(d.get("class_name")) and
                    d["bbox"][2] <= self.guide.split_x]
        self.unresolved_left = any(not any(
            p.get("bbox") is not None and box_iou(d["bbox"], p["bbox"]) >= 0.5
            for p in self.left_parts) for d in raw_left)
        signature = tuple(sorted((str(p.get("tid", index)), p["class_name"])
                                 for index, p in enumerate(self.left_parts)))
        if not self.frame_valid or self.hand_visible or self.unresolved_left:
            self.inventory_frames = 0
            self._inventory_signature = None
        elif signature == self._inventory_signature:
            self.inventory_frames += 1
        else:
            self._inventory_signature = signature
            self.inventory_frames = 1

        self._refresh_readiness_message(now)

    @staticmethod
    def _valid_box(value):
        try:
            box = tuple(float(v) for v in value)
        except (TypeError, ValueError, OverflowError):
            return None
        if (len(box) != 4 or not all(math.isfinite(v) for v in box) or
                box[2] <= box[0] or box[3] <= box[1]):
            return None
        return box

    def _add_right_blocker(self, detection):
        box = detection["bbox"]


        if not (min(box[2], self.guide.W) > max(box[0], self.guide.split_x) and
                min(box[3], self.guide.H) > max(box[1], 0)):
            return
        for index, previous in enumerate(self.right_blockers):
            same_type = is_hand(previous.get("class_name")) == is_hand(detection.get("class_name"))
            if same_type and box_iou(previous["bbox"], box) > 0.6:
                if detection.get("source") == "tracking" and previous.get("source") != "tracking":
                    self.right_blockers[index] = dict(detection)
                return
        self.right_blockers.append(dict(detection))

    def _refresh_readiness_message(self, now):


        if self._readiness_message is None:
            return
        if self.message != self._readiness_message:
            self._readiness_message = None
            return
        reason = self.readiness_reason(now)
        if reason:
            self.message = self._readiness_message = reason
        else:
            command = "[N] per cambiare composizione" if self.guide.generated else "[G] per avviare"
            self.message = "Piano destro libero. Premi " + command + "."
            self._readiness_message = None

    @property
    def inventory_ready(self):
        return bool(self.frame_valid and self.left_parts and not self.hand_visible and
                    not self.unresolved_left and self.inventory_frames >= self.stable_frames)

    def readiness_reason(self, now=None):
        now = time.monotonic() if now is None else now
        if not self.frame_valid:
            return "Controllo visivo non disponibile: avvio e cambio bloccati."
        if self.guard.occupied:
            if not self.right_has_parts:
                return "Mano nella zona di costruzione: allontanala per verificare il piano destro."
            return "Piano destro occupato: togli tutti i pezzi, anche quelli fuori sagoma."
        if not self.guard.ready(now):
            return "Attendo conferma stabile che il piano destro sia libero."
        if self.hand_visible:
            return "Allontana le mani dal piano prima di generare la composizione."
        if not self.left_parts:
            return "Nessun pezzo riconosciuto a sinistra."
        if not self.inventory_ready:
            return "Attendo che tutti i pezzi a sinistra siano riconosciuti e stabili."
        return ""

    def generate(self, change=False, now=None):

        now = time.monotonic() if now is None else now
        if self.guide.generated and not change:
            return self._result(False, "Composizione gia' attiva: usa Cambia composizione [N].")
        if change and not self.guide.generated:
            return self._result(False, "Prima avvia una composizione con [G].")
        reason = self.readiness_reason(now)
        if reason:
            result = self._result(False, reason)
            self._readiness_message = reason
            return result
        codes = [p["class_name"] for p in self.left_parts]

        success = self.guide.generate_from_parts(
            codes, self.plane_z_m, seed=self._rng.randrange(2 ** 31),
            ensure_different=change)
        if not success:
            return self._result(False, self.guide.last_error or "Composizione non generata.")
        self.generation += 1
        self.verification_visible = False
        self.return_check_active = False
        self.return_warning_visible = False
        self._return_announcement_pending = False
        self._completion_seen = False
        return self._result(True, f"Composizione {self.generation}: {len(codes)} sagome per "
                           f"{len(codes)} pezzi riconosciuti a sinistra.")

    def finish(self):


        self.guide.clear()
        self.verification_visible = False
        self._completion_seen = False
        self.return_check_active = True
        self._update_return_warning()
        return self._result(True, "Composizione conclusa. Tracking ancora attivo. "
                            "Riporta i pezzi a sinistra prima del prossimo avvio [G].")

    def check_completion(self):

        if self.guide.generated and self.guide.completed and not self._completion_seen:
            self._completion_seen = True
            self.return_check_active = True
            self.message = "Composizione completata. [X] concludi; il tracking continua."
        self._update_return_warning()

    def _update_return_warning(self):
        if not self.return_check_active:
            return
        if self.frame_valid and self.right_has_parts:
            if not self.return_warning_visible:
                self._return_announcement_pending = True
            self.return_warning_visible = True
        elif self.frame_valid and self.guard.ready(self._now):
            self.return_warning_visible = False
            self._return_announcement_pending = False


    @property
    def return_warning(self):
        return RETURN_PARTS_MESSAGE if self.return_warning_visible else ""

    def take_return_announcement(self):

        if not self._return_announcement_pending:
            return None
        self._return_announcement_pending = False
        return self.return_warning or None

    def silence_return_announcement(self):

        self._return_announcement_pending = False

    def _result(self, ok, message):
        self._readiness_message = None
        self.message = message
        return ActionResult(ok, message)

    def toggle_verification(self):
        if not self.guide.generated:
            self.message = "Prima avvia una composizione con [G]."
            return None
        self.verification_visible = not self.verification_visible
        if not self.verification_visible:
            self.message = "Verifica nascosta."
            return None
        self.message = "Evidenziati SOLO i pezzi da prendere sul piano sinistro."
        return self.verification_text()

    def report(self):
        required = Counter(s.code for s in self.guide.slots)
        completed = Counter(s.code for s in self.guide.slots if s.completed)
        remaining = required - completed
        right_present = Counter(p["class_name"] for p in self.right_parts)
        confirmed_ids = {p.get("tid") for s in self.guide.slots if s.completed
                         for p in [self.guide.last_matches.get(s.id)] if p is not None
                         and p.get("tid") is not None}

        pending_right = [p for p in self.right_parts if p.get("tid") not in confirmed_ids]
        raw_pending_counts = Counter(p["class_name"] for p in pending_right)
        right_pending = Counter({c: min(n, raw_pending_counts[c]) for c, n in remaining.items()
                                 if raw_pending_counts[c] > 0})
        to_pick = remaining - right_pending
        candidates = sorted(self.left_parts, key=lambda p: (p["class_name"], p["cy"],
                                                             p["cx"], str(p.get("tid", ""))))
        selected = []
        for part in candidates:
            code = part["class_name"]
            if to_pick[code] > 0:
                selected.append(part)
                to_pick[code] -= 1
        return {"required": required, "completed": completed, "remaining": remaining,
                "right_present": right_present, "right_pending": right_pending,
                "left_matches": selected, "unlocated": +to_pick,
                "unexpected_right": right_present - required,
                "done": sum(completed.values()), "total": sum(required.values())}

    def verification_text(self):
        report = self.report()
        if not report["total"]:
            return "Non c'e' una composizione attiva."
        lines = ["Pezzi della composizione: " + format_counts(report["required"]) + ".",
                 f"Completati {report['done']} su {report['total']}."]
        if not report["remaining"]:
            lines.append("La composizione e' completa. Nessun pezzo da cercare a sinistra.")
            return " ".join(lines)
        for part in report["left_matches"]:
            code = part["class_name"]
            lines.append(f"{code}, sul piano sinistro: " +
                         left_position(part, self.guide.split_x, self.guide.H) + ".")
        if report["right_pending"]:
            lines.append("Gia' a destra ma ancora da sistemare: " +
                         format_counts(report["right_pending"]) + ".")
        if report["unlocated"]:
            lines.append("Non localizzati fra i pezzi riconosciuti: " +
                         format_counts(report["unlocated"]) + ".")
        return " ".join(lines)
