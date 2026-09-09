"""Meccano: riconoscimento, composizione e assistenza senza raccolta dati.

G / SPAZIO = avvia; V = verifica; N = cambia (solo a destra libero);
R = domanda vocale; S = stop voce; X = concludi/azzera; Q / ESC = esci.
Tracking visibile su tutti i pezzi in ogni fase, anche durante la verifica.
Fix piano destro: filtro dei candidati grezzi, diagnostica visibile, messaggi attuali.
"""
import argparse
import os
import time
from collections import defaultdict, deque, Counter
from pathlib import Path

import cv2
import numpy as np

from assembly_guide_cad import CadAssemblyGuide
from composition_controller import CompositionController, is_hand
from composition_ui import CompositionUI, draw_left_highlights, draw_workspace_blockers
from part_orientation import estimate_angle_deg, AngleSmoother

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = r"C:\Users\Tirocinio\Desktop\Yolo_Project\progetto_con_lllm\progetto_llm_con_montaggio\progetto_annidato\Progetto_annidato_annidato\runs\detect\train\weights\best.pt"
DEFAULT_SILHOUETTES_DIR = r"C:\Users\Tirocinio\Desktop\Yolo_Project\progetto_con_lllm\progetto_llm_con_montaggio\silhouettes"
DEFAULT_TRACKER_CFG = r"C:\Users\Tirocinio\Desktop\Yolo_Project\progetto_con_lllm\meccano_bytetrack.yaml"
class_names = {}

depth_scale = 1.0


INFER_CONF  = 0.10


BOX_MAX_W_FRAC   = 0.35
BOX_MAX_H_FRAC   = 0.50
BOX_MAX_AREA_FRAC = 0.12
BOX_MIN_SIDE_PX  = 18
BOX_MAX_ASPECT   = 12.0
SHOW_BOX_FILTER_LOG = True


INFER_IMGSZ = 1280


INFER_AUGMENT = True


INFER_IOU = 0.7


DEDUP_IOU = 0.6


WORKSPACE_MIN_RAW_CONF = 0.35


HISTORY_SIZE      = 20
LOCK_AFTER_FRAMES = 15
LOCK_DOMINANCE    = 0.70
MIN_CONF_TO_VOTE  = 0.35
HARD_LOCK         = True


GHOST_TTL        = 35

GHOST_MAX_DIST   = 80


GHOST_EXCLUDE_CLASSES = {"Hand"}


COLOR_WIDTH, COLOR_HEIGHT = 1920, 1080
DEPTH_WIDTH, DEPTH_HEIGHT = 1280, 720
FPS = 30


WINDOW_NAME = "Meccano Tracker"
DISPLAY_MAX_W = 1280
DISPLAY_MAX_H = 720


class ClassStabilizer:


    def __init__(self, history_size=20, lock_after=15, dominance=0.7,
                 min_conf=0.35, hard_lock=True,
                 ghost_ttl=90, ghost_max_dist=80,
                 exclude_class_ids=None):
        self.history   = defaultdict(lambda: deque(maxlen=history_size))
        self.locked    = {}
        self.last_bbox = {}
        self.ghosts    = {}

        self.history_size = history_size
        self.lock_after   = lock_after
        self.dominance    = dominance
        self.min_conf     = min_conf
        self.hard_lock    = hard_lock
        self.ghost_ttl     = ghost_ttl
        self.ghost_max_dist = ghost_max_dist

        self.exclude_class_ids = set(exclude_class_ids) if exclude_class_ids else set()


    def update(self, tid, cls, conf, bbox):

        x1, y1, x2, y2 = bbox
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        self.last_bbox[tid] = (cx, cy)

        inherited = False

        if tid not in self.history and tid not in self.locked:
            inherited = self._try_inherit_from_ghost(tid, cx, cy)


        if self.hard_lock and tid in self.locked:
            return self.locked[tid], inherited


        if conf >= self.min_conf:
            self.history[tid].append((int(cls), float(conf)))

        if not self.history[tid]:
            return int(cls), inherited

        dominant = self._weighted_majority(tid)


        buf = self.history[tid]
        if len(buf) >= self.lock_after and tid not in self.locked:
            counts = Counter(c for c, _ in buf)
            top_cls, top_count = counts.most_common(1)[0]
            if top_count / len(buf) >= self.dominance:
                self.locked[tid] = top_cls
                print(f"[LOCK] tid={tid} -> {class_names[top_cls]} "
                      f"({top_count}/{len(buf)} = {top_count/len(buf):.0%})")
                return top_cls, inherited

        return dominant, inherited


    def _try_inherit_from_ghost(self, new_tid, cx, cy):


        best = None
        best_d = float("inf")
        for gid, g in self.ghosts.items():
            d = ((cx - g["cx"]) ** 2 + (cy - g["cy"]) ** 2) ** 0.5
            if d <= self.ghost_max_dist and d < best_d:
                best_d = d
                best = gid

        if best is None:
            return False

        g = self.ghosts.pop(best)
        if g["locked_class"] is not None:
            self.locked[new_tid] = g["locked_class"]
            print(f"[INHERIT] new_tid={new_tid} eredita lock "
                  f"{class_names[g['locked_class']]} da ghost tid={best} "
                  f"(dist={best_d:.0f}px, age={g['age']})")
            return True

        return False


    def _weighted_majority(self, tid):
        scores = defaultdict(float)
        for c, conf in self.history[tid]:
            scores[c] += conf
        return max(scores.items(), key=lambda x: x[1])[0]

    def is_locked(self, tid):
        return tid in self.locked


    def forget(self, tid):


        self.history.pop(tid, None)
        self.locked.pop(tid, None)
        if hasattr(self, "ghosts"):
            self.ghosts.pop(tid, None)
        if hasattr(self, "last_bbox"):
            self.last_bbox.pop(tid, None)


    def cleanup(self, active_ids):


        gone = set(self.history.keys()) - active_ids
        gone |= (set(self.locked.keys()) - active_ids)
        for tid in gone:
            locked_cls = self.locked.get(tid)


            is_excluded = locked_cls in self.exclude_class_ids
            if tid in self.last_bbox and not is_excluded:
                cx, cy = self.last_bbox[tid]
                self.ghosts[tid] = {
                    "age": 0,
                    "cx": cx, "cy": cy,
                    "locked_class": locked_cls,
                    "history": self.history.get(tid, deque(maxlen=self.history_size)),
                }
            self.history.pop(tid, None)
            self.locked.pop(tid, None)
            self.last_bbox.pop(tid, None)


        for gid in list(self.ghosts.keys()):
            self.ghosts[gid]["age"] += 1
            if self.ghosts[gid]["age"] > self.ghost_ttl:
                self.ghosts.pop(gid, None)


def depth_at_bbox_center(depth_img, x1, y1, x2, y2, half=4):
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    h, w = depth_img.shape
    cx = max(0, min(cx, w - 1))
    cy = max(0, min(cy, h - 1))
    xa = max(0, cx - half); xb = min(w, cx + half + 1)
    ya = max(0, cy - half); yb = min(h, cy + half + 1)
    patch = depth_img[ya:yb, xa:xb]
    valid = patch[patch > 0]
    if valid.size == 0:
        return 0.0
    return float(np.median(valid)) * depth_scale


def box_plausibile(x1, y1, x2, y2, frame_w, frame_h):


    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return False, "degenere"
    if w < BOX_MIN_SIDE_PX or h < BOX_MIN_SIDE_PX:
        return False, f"troppo piccolo ({w}x{h}px)"
    if w > frame_w * BOX_MAX_W_FRAC:
        return False, f"troppo largo ({w}px > {frame_w*BOX_MAX_W_FRAC:.0f})"
    if h > frame_h * BOX_MAX_H_FRAC:
        return False, f"troppo alto ({h}px > {frame_h*BOX_MAX_H_FRAC:.0f})"
    if (w * h) > (frame_w * frame_h * BOX_MAX_AREA_FRAC):
        return False, f"area eccessiva ({w*h}px2)"
    lato_lungo, lato_corto = max(w, h), min(w, h)
    if lato_corto > 0 and lato_lungo / lato_corto > BOX_MAX_ASPECT:
        return False, f"proporzioni impossibili ({lato_lungo/lato_corto:.1f}:1)"
    return True, ""


def iou_xyxy(a, b):

    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def deduplicate_detections(dets, iou_thresh):


    def sort_key(d):
        return (
            0 if d["locked"] else 1,                  
            d["tid"],                                   
            -d["conf"],                                 
        )
    ordered = sorted(dets, key=sort_key)

    kept = []
    for d in ordered:

        is_dup = any(iou_xyxy(d["bbox"], k["bbox"]) > iou_thresh for k in kept)
        if not is_dup:
            kept.append(d)
    return kept


class RawDetectionSnapshot:


    def __init__(self, names):
        self.names = names
        self.detections = None

    def reset(self):
        self.detections = None

    def __call__(self, predictor):
        self.detections = None
        try:
            if not predictor.results:
                self.detections = []
                return
            boxes = predictor.results[0].boxes
            if boxes is None:
                self.detections = []
                return
            if getattr(boxes, "is_track", False):
                return
            xyxy = boxes.xyxy.cpu().numpy().copy()
            classes = boxes.cls.cpu().numpy().astype(int)
            confs = boxes.conf.cpu().numpy()
            self.detections = [
                {"bbox": tuple(float(x) for x in box),
                 "class_name": str(self.names[int(code)]), "conf": float(conf)}
                for box, code, conf in zip(xyxy, classes, confs)]
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            self.detections = None


def workspace_observations(raw_detections, tracked_detections, names,
                           frame_w, frame_h, min_raw_conf=None):


    if min_raw_conf is None:
        min_raw_conf = WORKSPACE_MIN_RAW_CONF
    if not 0 <= min_raw_conf <= 1:
        raise ValueError("Confidenza del controllo area non valida.")
    if raw_detections is None:
        return None, []
    if frame_w <= 0 or frame_h <= 0:
        return None, []
    observations, rejected = [], []

    def reject(detection, reason):
        rejected.append({"class_name": str(detection.get("class_name", "?")),
                         "bbox": detection.get("bbox"), "reason": reason})

    def geometry(detection):
        try:
            box = tuple(float(v) for v in detection["bbox"])
            if len(box) != 4 or not all(np.isfinite(v) for v in box):
                raise ValueError("box non finito")
            x1, y1, x2, y2 = box
        except (KeyError, TypeError, ValueError, OverflowError):
            reject(detection, "coordinate non valide")
            return None
        if x2 <= x1 or y2 <= y1:
            reject(detection, "riquadro degenere")
            return None
        if x2 <= 0 or y2 <= 0 or x1 >= frame_w or y1 >= frame_h:
            reject(detection, "fuori immagine")
            return None
        clipped = (max(0.0, x1), max(0.0, y1),
                   min(float(frame_w), x2), min(float(frame_h), y2))
        if not is_hand(detection.get("class_name")):


            ok, reason = box_plausibile(*box, frame_w, frame_h)
            if ok:
                ok, reason = box_plausibile(*clipped, frame_w, frame_h)
            if not ok:
                reject(detection, reason)
                return None
        return clipped

    for track in tracked_detections:
        try:
            code = str(names[int(track["stable_cls"])]).strip()
        except (KeyError, IndexError, TypeError, ValueError, OverflowError):
            continue
        detection = {"bbox": track.get("bbox"), "class_name": code,
                     "conf": track.get("conf"), "tid": track.get("tid"),
                     "locked": bool(track.get("locked")), "source": "tracking"}
        box = geometry(detection)
        if box is not None and code:
            detection["bbox"] = box
            observations.append(detection)

    for raw in raw_detections:
        detection = dict(raw)
        code = str(detection.get("class_name", "")).strip()
        detection["class_name"] = code
        if not code:
            reject(detection, "classe assente")
            continue
        box = geometry(detection)
        if box is None:
            continue
        try:
            confidence = float(detection["conf"])
            if not np.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError("confidenza non valida")
        except (KeyError, TypeError, ValueError, OverflowError):
            reject(detection, "confidenza non valida")
            continue
        if confidence < min_raw_conf:

            reject(detection, "confidenza bassa")
            continue
        detection.update(bbox=box, conf=confidence, source="detector")
        detection.pop("tid", None)
        observations.append(detection)


    return observations, rejected


def estimate_plane_z(depth_image, scale, split_x):

    h, w = depth_image.shape[:2]
    margin = max(4, int(min(h, w) * 0.025))
    patch = depth_image[margin:h-margin, split_x+margin:w-margin:6]
    valid = patch[patch > 0]
    if valid.size < 30:
        return None
    z = float(np.median(valid)) * scale
    return z if np.isfinite(z) and z > 0 else None


def draw_detection(image, d):

    x1, y1, x2, y2 = d["bbox"]
    colour = (0, 200, 0) if d["locked"] else (0, 165, 255)
    cv2.rectangle(image, (x1, y1), (x2, y2), colour, 2)
    code = class_names[d["stable_cls"]]
    label = f"ID{d['tid']} {code}" + (" [LOCK]" if d["locked"] else "")
    if d["raw_cls"] != d["stable_cls"]:
        label += f"  (raw:{class_names[d['raw_cls']]})"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    y_top = max(0, y1-th-8)
    cv2.rectangle(image, (x1, y_top), (min(image.shape[1]-1, x1+tw+6), y1), colour, -1)
    cv2.putText(image, label, (x1+3, max(th+2, y1-5)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2, cv2.LINE_AA)


def draw_tracked_scene(colour_image, detections, guide, controller):

    annotated = colour_image.copy()
    guide.draw(annotated, show_progress=False,
               show_labels=not controller.verification_visible)
    if controller.verification_visible:
        draw_left_highlights(annotated, controller.report()["left_matches"], guide.split_x)


    draw_workspace_blockers(annotated, controller.right_blockers, guide.split_x)
    for detection in detections:
        draw_detection(annotated, detection)
    return annotated


KEY_ACTIONS = {ord("g"): "start", ord(" "): "start", ord("n"): "change",
               ord("v"): "verify", ord("i"): "verify", ord("r"): "voice",
               ord("s"): "stop_voice", ord("x"): "finish", ord("q"): "quit", 27: "quit"}

KEY_ACTIONS.update({ord(chr(key).upper()): value for key, value in list(KEY_ACTIONS.items())
                    if ord("a") <= key <= ord("z")})


def stop_voice(voice, controller):
    controller.silence_return_announcement()
    if voice is not None:
        voice.stop()
        controller.message = "Voce interrotta. Tracking e avviso scritto restano attivi."
    else:
        controller.message = "Voce non disponibile. Tracking e avviso scritto restano attivi."


def dispatch_return_notice(controller, voice):
    speech = controller.take_return_announcement()
    if speech:
        print("[AVVISO] " + speech)
        if voice is not None:

            voice.say_async(speech, interrupt=True, tag="return_parts")
    elif not controller.return_warning_visible and voice is not None:

        voice.cancel_tag("return_parts")


def _arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    local_model = BASE_DIR / "best.pt"
    local_sil = BASE_DIR / "silhouettes"
    parser.add_argument("--model", default=os.environ.get(
        "MECCANO_MODEL_PATH", str(local_model) if local_model.is_file() else DEFAULT_MODEL_PATH))
    parser.add_argument("--silhouettes", default=os.environ.get(
        "MECCANO_SILHOUETTES_DIR", str(local_sil) if local_sil.is_dir() else DEFAULT_SILHOUETTES_DIR))
    parser.add_argument("--tracker", default=os.environ.get("MECCANO_TRACKER_CFG", DEFAULT_TRACKER_CFG))
    parser.add_argument("--no-voice", action="store_true", help="avvio senza componenti audio")
    return parser.parse_args()


def main():
    global class_names, depth_scale
    args = _arguments()
    if not Path(args.model).is_file():
        raise SystemExit(f"Modello non trovato: {args.model}\nUsa --model con il percorso del tuo best.pt.")
    if not Path(args.silhouettes).is_dir():
        raise SystemExit(f"Cartella silhouette non trovata: {args.silhouettes}\nUsa --silhouettes.")
    try:
        import pyrealsense2 as rs
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(f"Dipendenza mancante: {exc}. Usa l'ambiente Python del progetto.") from exc

    model = YOLO(args.model)
    names = model.names
    class_names = dict(names) if isinstance(names, dict) else dict(enumerate(names))
    raw_snapshot = RawDetectionSnapshot(class_names)

    model.add_callback("on_predict_postprocess_end", raw_snapshot)
    tracker_cfg = args.tracker if Path(args.tracker).is_file() else "bytetrack.yaml"
    excluded_ids = {idx for idx, name in class_names.items() if is_hand(name)}
    stabilizer = ClassStabilizer(
        history_size=HISTORY_SIZE, lock_after=LOCK_AFTER_FRAMES, dominance=LOCK_DOMINANCE,
        min_conf=MIN_CONF_TO_VOTE, hard_lock=HARD_LOCK, ghost_ttl=GHOST_TTL,
        ghost_max_dist=GHOST_MAX_DIST, exclude_class_ids=excluded_ids)
    angle_smoother = AngleSmoother(window=7)
    pipeline = rs.pipeline()
    camera_started = False
    voice = None
    scene = None
    try:
        config = rs.config()
        config.enable_stream(rs.stream.depth, DEPTH_WIDTH, DEPTH_HEIGHT, rs.format.z16, FPS)
        config.enable_stream(rs.stream.color, COLOR_WIDTH, COLOR_HEIGHT, rs.format.bgr8, FPS)
        profile = pipeline.start(config)
        camera_started = True
        depth_scale = profile.get_device().first_depth_sensor().get_depth_scale()
        intrinsics = profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()
        align = rs.align(rs.stream.color)
        spatial = rs.spatial_filter()
        spatial.set_option(rs.option.filter_magnitude, 2)
        spatial.set_option(rs.option.filter_smooth_alpha, 0.5)
        spatial.set_option(rs.option.filter_smooth_delta, 20)
        temporal = rs.temporal_filter()
        temporal.set_option(rs.option.filter_smooth_alpha, 0.4)
        temporal.set_option(rs.option.filter_smooth_delta, 20)
        hole_filling = rs.hole_filling_filter()
        hole_filling.set_option(rs.option.holes_fill, 1)
        guide = CadAssemblyGuide(COLOR_WIDTH, COLOR_HEIGHT, args.silhouettes, intrinsics.fx)
        controller = CompositionController(guide)
        ui = CompositionUI(WINDOW_NAME, DISPLAY_MAX_W, DISPLAY_MAX_H)

        if not args.no_voice:
            try:
                from voice_assistant import SceneState, VoiceAssistant
                scene = SceneState()
                scene.set_frame_shape(COLOR_HEIGHT, COLOR_WIDTH)
                voice = VoiceAssistant(scene, all_class_names=list(class_names.values()))
            except Exception as exc:
                voice = None
                print(f"[VOCE] Non disponibile: {exc}. I comandi visivi restano utilizzabili.")
        print("\nG / SPAZIO: avvia | V: verifica | N: cambia | R: voce | S: stop voce | X: concludi | Q: esci")
        print("[FIX PIANO DESTRO v1] Controllo area filtrato; tracking originale invariato.")
        print("Il cambio e' consentito solo dopo conferma stabile del piano destro libero.")
        print("Nessuna registrazione video, CSV, questionario o misura delle prestazioni.\n")
        ui.open()
        actions = deque()
        last_camera = np.zeros((COLOR_HEIGHT, COLOR_WIDTH, 3), dtype=np.uint8)
        while True:
            frames = pipeline.wait_for_frames()
            aligned = align.process(frames)
            depth_frame, colour_frame = aligned.get_depth_frame(), aligned.get_color_frame()
            if not depth_frame or not colour_frame:
                controller.observe([], [], None, frame_valid=False)

                actions.extend(ui.pop_actions())
                queued = list(actions)
                actions.clear()
                if "quit" in queued:
                    break
                if "finish" in queued:
                    controller.finish()
                if "stop_voice" in queued:
                    stop_voice(voice, controller)
                controller.message = "Camera non disponibile: avvio/cambio bloccati. Tracking in attesa di immagini."
                if scene is not None:
                    scene.sync_with_active(set())
                cv2.imshow(WINDOW_NAME, ui.draw(last_camera, controller, voice))
                action = KEY_ACTIONS.get(cv2.waitKey(1) & 0xFF)
                if action == "quit":
                    break
                if action == "stop_voice":
                    stop_voice(voice, controller)
                elif action == "finish":
                    controller.finish()
                continue
            filtered = hole_filling.process(temporal.process(spatial.process(depth_frame)))
            depth_image = np.asanyarray(filtered.get_data())
            colour_image = np.asanyarray(colour_frame.get_data())
            raw_snapshot.reset()
            results = model.track(source=colour_image, persist=True, tracker=tracker_cfg,
                                  imgsz=INFER_IMGSZ, conf=INFER_CONF, iou=INFER_IOU,
                                  augment=INFER_AUGMENT, verbose=False, show=False,
                                  save=False, save_txt=False, save_crop=False)[0]
            detections, active_ids = [], set()
            if results.boxes is not None and results.boxes.id is not None:
                boxes = results.boxes.xyxy.cpu().numpy()
                ids = results.boxes.id.cpu().numpy().astype(int)
                classes = results.boxes.cls.cpu().numpy().astype(int)
                confidences = results.boxes.conf.cpu().numpy()
                for box, tid, raw_cls, conf in zip(boxes, ids, classes, confidences):
                    x1, y1, x2, y2 = map(int, box)
                    x1, x2 = max(0, x1), min(COLOR_WIDTH - 1, x2)
                    y1, y2 = max(0, y1), min(COLOR_HEIGHT - 1, y2)
                    ok, _ = box_plausibile(x1, y1, x2, y2, COLOR_WIDTH, COLOR_HEIGHT)
                    if not ok or is_hand(class_names[int(raw_cls)]):
                        stabilizer.forget(int(tid))
                        continue
                    active_ids.add(int(tid))
                    stable, _ = stabilizer.update(int(tid), int(raw_cls), float(conf), (x1,y1,x2,y2))
                    detections.append({"bbox": (x1,y1,x2,y2), "tid": int(tid),
                                       "raw_cls": int(raw_cls), "stable_cls": int(stable),
                                       "conf": float(conf), "locked": stabilizer.is_locked(int(tid))})
            detections = deduplicate_detections(detections, DEDUP_IOU)
            left_parts, right_parts = [], []
            for d in detections:
                if not d["locked"]:
                    continue
                x1, y1, x2, y2 = d["bbox"]
                cx, cy = (x1+x2)//2, (y1+y2)//2
                distance = depth_at_bbox_center(depth_image, x1,y1,x2,y2)
                world = (None, None, None)
                if distance > 0:
                    world = tuple(rs.rs2_deproject_pixel_to_point(intrinsics, [float(cx),float(cy)], distance))
                code = str(class_names[d["stable_cls"]]).upper()

                if scene is not None:
                    scene.update_part(d["tid"], code, (cx,cy), d["bbox"], world)
                angle, aspect = estimate_angle_deg(colour_image, d["bbox"])
                if angle is not None and aspect is not None and aspect >= 1.25:
                    angle = angle_smoother.update(d["tid"], angle)
                else:

                    angle = None
                part = {"tid": d["tid"], "class_name": code, "bbox": d["bbox"],
                        "cx": cx, "cy": cy, "z": distance if distance > 0 else None,
                        "angle_deg": angle, "X_mm": world[0]*1000 if world[0] is not None else None,
                        "Y_mm": world[1]*1000 if world[1] is not None else None}
                (left_parts if guide.is_in_start_area(cx,cy) else right_parts).append(part)
            stabilizer.cleanup(active_ids)
            angle_smoother.cleanup(active_ids)
            if scene is not None:
                scene.sync_with_active({d["tid"] for d in detections if d["locked"]})
            now = time.monotonic()
            plane_z = estimate_plane_z(depth_image, depth_scale, guide.split_x)
            frame_h, frame_w = colour_image.shape[:2]
            workspace, rejected = workspace_observations(
                raw_snapshot.detections, detections, class_names, frame_w, frame_h)

            geometry_valid = (frame_w == guide.W and frame_h == guide.H)
            controller.observe(left_parts, right_parts, workspace, plane_z, now=now,
                               frame_valid=geometry_valid, rejected_detections=rejected)

            if controller.frame_valid:
                guide.update(right_parts)
            controller.check_completion()


            actions.extend(ui.pop_actions())
            quit_requested = False
            while actions:
                action = actions.popleft()
                if action == "quit":
                    quit_requested = True
                    break
                if action in ("start", "change"):
                    result = controller.generate(change=action == "change")
                    print("[COMPOSIZIONE] " + result.message)
                    if result.ok:
                        ui.scroll = 0
                elif action == "finish":
                    result = controller.finish()
                    ui.scroll = 0
                    print("[COMPOSIZIONE] " + result.message)
                elif action == "stop_voice":
                    stop_voice(voice, controller)
                elif action == "verify":
                    speech = controller.toggle_verification()
                    if speech:
                        print("[VERIFICA] " + speech)
                        if voice is not None:
                            voice.say_async(speech)
                elif action == "voice":
                    if voice is None:
                        controller.message = "Voce non disponibile. La verifica visiva [V] resta attiva."
                    elif not voice.trigger():
                        controller.message = "Assistente vocale gia' occupato."
            if quit_requested:
                break
            dispatch_return_notice(controller, voice)
            annotated = draw_tracked_scene(colour_image, detections, guide, controller)
            last_camera = annotated
            view = ui.draw(annotated, controller, voice)
            cv2.imshow(WINDOW_NAME, view)
            key = cv2.waitKey(1) & 0xFF
            action = KEY_ACTIONS.get(key)

            mouse_actions = ui.pop_actions()
            if action == "stop_voice" or "stop_voice" in mouse_actions:
                stop_voice(voice, controller)
                if action == "stop_voice":
                    action = None
                mouse_actions = [a for a in mouse_actions if a != "stop_voice"]
            actions.extend(mouse_actions)
            if action == "quit":
                break
            if action:
                actions.append(action)
            try:
                if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                    break
            except cv2.error:
                break
    finally:
        if voice is not None:
            voice.close()
        if camera_started:
            pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
