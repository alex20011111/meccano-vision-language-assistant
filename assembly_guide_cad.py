import os
import json
import math
from collections import Counter
import numpy as np
import cv2


AREA_SPLIT_X_FRAC = 0.5
POLYGON_RADIUS_PX = 240


ASSEMBLY_LAYOUT = "random"                                                     


STRUCTURAL_ASPECT_MIN = 2.0


CONTACT_GAP_MM = 0.0


CHAIN_TURN_MIN_DEG = 20.0
CHAIN_TURN_MAX_DEG = 55.0

STABILITY_FRAMES  = 12
POS_TOL_MM        = 40.0
POS_TOL_PX        = 90


ROT_TOL_DEG       = 30.0
CHECK_ROTATION    = True
SILHOUETTE_ALPHA  = 0.45


ANGLE_SIGN = -1.0


ALLOW_MIRRORED_ANGLE = False
MISSING_FRAMES = 12

ROUND_PARTS = {
    "A045",               
    "A046",                     
    "A053",                                
    "A057",                                       
    "A077",                              
    "C658",                                                      
}


class SilhouetteLibrary:


    def __init__(self, silhouettes_dir):
        self.dir = silhouettes_dir
        self.meta = {}
        self.images = {}
        self._load_meta()

    def _load_meta(self):
        meta_path = os.path.join(self.dir, "silhouettes_meta.json")
        if not os.path.exists(meta_path):
            print(f"[SIL] ATTENZIONE: {meta_path} non trovato. "
                  "Genera prima le silhouette con generate_silhouettes.py.")
            return
        try:
            with open(meta_path, encoding="utf-8") as fp:
                self.meta = json.load(fp)
            parts = self.meta.get("parts", {})
            if not isinstance(parts, dict):
                raise ValueError("La voce 'parts' deve essere un oggetto JSON.")
            self.meta["parts"] = {str(k).upper(): v for k, v in parts.items()}
        except (OSError, ValueError, AttributeError) as exc:
            self.meta = {}
            print(f"[SIL] Metadati non validi: {exc}")
        print(f"[SIL] Meta caricato: {len(self.meta.get('parts', {}))} silhouette disponibili.")

    def has(self, code):
        return code in self.meta.get("parts", {})

    def get_image(self, code):

        if code in self.images:
            return self.images[code]
        info = self.meta.get("parts", {}).get(code)
        if info is None:
            return None
        if not isinstance(info, dict) or not isinstance(info.get("png"), str):
            return None
        path = os.path.join(self.dir, info["png"])
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"[SIL] impossibile leggere {path}")
            return None
        if img.ndim != 3 or img.shape[2] != 4 or not np.any(img[..., 3]):
            print(f"[SIL] PNG senza una sagoma BGRA valida: {path}")
            return None
        img = self._crop_transparent_border(img)
        self.images[code] = img
        return img

    @staticmethod
    def _crop_transparent_border(img):


        if img is None or img.shape[2] < 4:
            return img
        ys, xs = np.where(img[..., 3] > 0)
        if len(xs) == 0:
            return img
        return img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

    def mm_per_px_native(self, code):

        info = self.meta.get("parts", {}).get(code)
        if info is None:
            return None
        return info["mm_per_px"]


class CadSlot:


    def __init__(self, slot_id, code, cx, cy, angle_deg=0.0):
        self.id = slot_id
        self.code = code
        self.cx = cx
        self.cy = cy
        self.angle = angle_deg
        self.completed = False
        self.stable_count = 0
        self.missing_count = 0
        self.matched_tid = None

    def reset_progress(self):
        self.stable_count = 0


class CadAssemblyGuide:


    def __init__(self, frame_w, frame_h, silhouettes_dir,
                 intrinsics_fx,
                 split_x_frac=AREA_SPLIT_X_FRAC,
                 polygon_radius_px=POLYGON_RADIUS_PX,
                 stability_frames=STABILITY_FRAMES,
                 pos_tol_mm=POS_TOL_MM,
                 rot_tol_deg=ROT_TOL_DEG,
                 check_rotation=CHECK_ROTATION,
                 layout=ASSEMBLY_LAYOUT):
        self.W = frame_w
        self.H = frame_h
        self.split_x = int(frame_w * split_x_frac)
        self.lib = SilhouetteLibrary(silhouettes_dir)
        self.fx = intrinsics_fx
        self.polygon_radius = polygon_radius_px
        self.stability_frames = stability_frames
        self.pos_tol_mm = pos_tol_mm
        self.rot_tol_deg = rot_tol_deg
        self.check_rotation = check_rotation
        self.layout = layout

        self.slots = []
        self.generated = False
        self.completed = False
        self.plane_z_mm = None
        self.debug = False
        self._mask_cache = {}
        self._silhouette_cache = {}
        self.last_matches = {}
        self.last_error = ""
        self.missing_frames = MISSING_FRAMES


    def is_in_start_area(self, cx, cy):
        return cx < self.split_x

    def is_in_assembly_area(self, cx, cy):
        return cx >= self.split_x

    def is_on_completed_slot(self, class_name, cx, cy):


        if not self.generated:
            return False
        for slot in self.slots:
            if not slot.completed:
                continue
            if slot.code.upper() != str(class_name).upper():
                continue
            if math.hypot(cx - slot.cx, cy - slot.cy) <= POS_TOL_PX:
                return True
        return False


    def mm_to_px(self, mm, z_mm):


        if z_mm is None or z_mm <= 0:
            return None
        return mm * self.fx / z_mm


    def part_size_mm(self, code):

        info = self.lib.meta.get("parts", {}).get(code)
        if not info or "size_mm" not in info:
            return None, None
        w, h = info["size_mm"]
        return max(w, h), min(w, h)

    def is_structural(self, code):

        lng, srt = self.part_size_mm(code)
        if not lng or not srt or srt <= 0:
            return False
        return (lng / srt) >= STRUCTURAL_ASPECT_MIN


    @staticmethod
    def _obb_corners(cx, cy, length, width, angle_deg, margin=0.0):


        a = math.radians(angle_deg)
        ca, sa = math.cos(a), math.sin(a)
        hl = length / 2.0 + margin
        hw = width / 2.0 + margin
        pts = []
        for sx, sy in ((+1, +1), (+1, -1), (-1, -1), (-1, +1)):
            dx, dy = sx * hl, sy * hw

            pts.append((cx + dx * ca + dy * sa,
                        cy - dx * sa + dy * ca))
        return pts

    @staticmethod
    def _obb_overlap(poly_a, poly_b):


        for poly in (poly_a, poly_b):
            n = len(poly)
            for i in range(n):
                x1, y1 = poly[i]
                x2, y2 = poly[(i + 1) % n]

                ax, ay = -(y2 - y1), (x2 - x1)
                norm = math.hypot(ax, ay)
                if norm == 0:
                    continue
                ax, ay = ax / norm, ay / norm
                pa = [x * ax + y * ay for x, y in poly_a]
                pb = [x * ax + y * ay for x, y in poly_b]
                if max(pa) < min(pb) or max(pb) < min(pa):
                    return False
        return True

    def _slot_obb(self, slot, px_per_mm, margin_mm=0.0):

        L, W = self.part_size_mm(slot.code)
        if not L:
            L = W = 20.0
        return self._obb_corners(slot.cx, slot.cy,
                                 L * px_per_mm, W * px_per_mm,
                                 slot.angle, margin_mm * px_per_mm)

    def _slot_mask(self, slot):


        key = (slot.code, round(slot.angle, 1))
        cached = self._mask_cache.get(key)
        if cached is None:
            sil = self._scaled_rotated_silhouette(slot.code, slot.angle)
            if sil is None:
                return None
            m = (sil[..., 3] > 0).astype(np.uint8)


            m = cv2.dilate(m, np.ones((3, 3), np.uint8))
            cached = m.astype(bool)
            self._mask_cache[key] = cached
        m = cached
        h, w = m.shape[:2]
        x0 = int(slot.cx - w / 2)
        y0 = int(slot.cy - h / 2)
        return m, x0, y0

    @staticmethod
    def _masks_overlap(a, b):

        if a is None or b is None:
            return False
        ma, ax, ay = a
        mb, bx, by = b
        ha, wa = ma.shape
        hb, wb = mb.shape

        x1, y1 = max(ax, bx), max(ay, by)
        x2, y2 = min(ax + wa, bx + wb), min(ay + ha, by + hb)
        if x1 >= x2 or y1 >= y2:
            return False
        sub_a = ma[y1 - ay:y2 - ay, x1 - ax:x2 - ax]
        sub_b = mb[y1 - by:y2 - by, x1 - bx:x2 - bx]
        return bool(np.any(sub_a & sub_b))

    def _snap_to_contact(self, px_per_mm, max_pull_px=400):


        structural = [s for s in self.slots if self.is_structural(s.code)]
        if not structural:
            return

        step = 1
        placed = list(structural)
        masks = {id(s): self._slot_mask(s) for s in structural}

        for f in self.slots:
            if self.is_structural(f.code):
                continue
            target = min(structural,
                         key=lambda s: math.hypot(s.cx - f.cx, s.cy - f.cy))
            dx, dy = target.cx - f.cx, target.cy - f.cy
            d = math.hypot(dx, dy)
            if d < 1e-6:
                placed.append(f); masks[id(f)] = self._slot_mask(f)
                continue
            dx, dy = dx / d, dy / d


            guard = 0
            while guard < max_pull_px and any(
                    self._masks_overlap(self._slot_mask(f), masks[id(o)])
                    for o in placed):
                f.cx -= int(round(dx * step)); f.cy -= int(round(dy * step))
                guard += step

            pulled = 0
            while pulled < max_pull_px:
                f.cx += int(round(dx * step))
                f.cy += int(round(dy * step))
                pulled += step
                mf = self._slot_mask(f)
                if any(self._masks_overlap(mf, masks[id(o)]) for o in placed):
                    f.cx -= int(round(dx * step))
                    f.cy -= int(round(dy * step))
                    break
            placed.append(f)
            masks[id(f)] = self._slot_mask(f)

    def _separate_overlaps(self, px_per_mm, margin_mm, max_iter=120):


        step = 2
        max_shift = 250.0
        shifted = {id(s): 0.0 for s in self.slots}

        for _ in range(max_iter):
            moved = False
            for i in range(len(self.slots)):
                for j in range(i + 1, len(self.slots)):
                    s1, s2 = self.slots[i], self.slots[j]
                    if not self._masks_overlap(self._slot_mask(s1),
                                               self._slot_mask(s2)):
                        continue
                    dx, dy = s2.cx - s1.cx, s2.cy - s1.cy
                    d = math.hypot(dx, dy)
                    if d < 1e-6:
                        dx, dy, d = 1.0, 0.0, 1.0
                    dx, dy = dx / d, dy / d
                    target = s2 if not self.is_structural(s2.code) else (
                        s1 if not self.is_structural(s1.code) else s2)
                    if shifted[id(target)] >= max_shift:
                        continue
                    sign = 1.0 if target is s2 else -1.0
                    target.cx += int(round(dx * step * sign))
                    target.cy += int(round(dy * step * sign))
                    shifted[id(target)] += step
                    moved = True
            if not moved:
                return self._count_overlaps()
        left = 0
        for i in range(len(self.slots)):
            for j in range(i + 1, len(self.slots)):
                if self._masks_overlap(self._slot_mask(self.slots[i]),
                                       self._slot_mask(self.slots[j])):
                    left += 1
        return left


    def _figure_bbox(self):

        xs1, ys1, xs2, ys2 = [], [], [], []
        for s in self.slots:
            m = self._slot_mask(s)
            if m is None:
                continue
            mask, x0, y0 = m
            h, w = mask.shape
            xs1.append(x0); ys1.append(y0)
            xs2.append(x0 + w); ys2.append(y0 + h)
        if not xs1:
            return None
        return min(xs1), min(ys1), max(xs2), max(ys2)

    def _fit_into_assembly_area(self, margin=25):


        bb = self._figure_bbox()
        if bb is None:
            return True
        x1, y1, x2, y2 = bb
        ax1, ax2 = self.split_x + margin, self.W - margin
        ay1, ay2 = margin, self.H - margin
        if (x2 - x1) > (ax2 - ax1) or (y2 - y1) > (ay2 - ay1):
            return False
        dx = dy = 0
        if x1 < ax1:
            dx = ax1 - x1
        elif x2 > ax2:
            dx = ax2 - x2
        if y1 < ay1:
            dy = ay1 - y1
        elif y2 > ay2:
            dy = ay2 - y2
        if dx or dy:
            for s in self.slots:
                s.cx += int(dx); s.cy += int(dy)
        return True

    def generate_from_parts(self, part_classes, plane_z_m, seed=None,
                            ensure_different=False):


        import random
        codes = [str(c).strip().upper() for c in part_classes]
        self.last_error = ""
        if not codes:
            self.last_error = "Nessun pezzo riconosciuto nel piano sinistro."
            return False
        missing = sorted({c for c in codes if not self.can_render(c)})
        if missing:
            self.last_error = "Silhouette assenti o non valide: " + ", ".join(missing)
            return False
        try:
            z = float(plane_z_m)
            if not math.isfinite(z) or z <= 0 or not math.isfinite(self.fx) or self.fx <= 0:
                raise ValueError
        except (TypeError, ValueError):
            self.last_error = "Profondita' del piano non valida: impossibile scalare le sagome."
            return False

        fields = ("slots", "generated", "completed", "plane_z_mm", "_mask_cache",
                  "_silhouette_cache", "last_matches", "_fig_info", "_fig_usable")
        previous = {name: getattr(self, name, None) for name in fields}
        previous_signature = self._layout_signature()
        rng = random.Random(seed)
        base = rng.randrange(10 ** 9)
        reason = "Non riesco a disporre tutti i pezzi a destra senza sovrapposizioni."
        try:
            for attempt in range(22):
                self._mask_cache = {}
                self._silhouette_cache = {}
                self._build_figure(codes, z, seed=base + attempt,
                                   compact=min(1.0, attempt / 6.0),
                                   layout_override="parallel" if attempt >= 4 else None)
                if Counter(s.code for s in self.slots) != Counter(codes):
                    reason = "Numero o tipo delle sagome non corrispondente ai pezzi a sinistra."
                    break
                if not self._fit_into_assembly_area() or self._count_overlaps():
                    continue


                self._jitter_figure(rng)
                if ensure_different and self._layout_signature() == previous_signature:
                    reason = "Non e' stata trovata una disposizione diversa valida."
                    continue
                self.generated = True
                self.completed = False
                self.last_matches = {}
                self._print_final_report()
                return True
        except Exception as exc:
            reason = f"Generazione non riuscita: {exc}"

        for name, value in previous.items():
            setattr(self, name, value)
        self.last_error = reason
        return False

    def _layout_signature(self):
        return tuple(sorted((s.code, s.cx, s.cy,
                             0 if s.code in ROUND_PARTS else round(s.angle % 180, 2))
                            for s in self.slots))

    def _jitter_figure(self, rng, margin=25):
        bb = self._figure_bbox()
        if bb is None:
            return
        x1, y1, x2, y2 = bb
        dx = rng.randint(max(-40, self.split_x + margin - x1),
                         min(40, self.W - margin - x2))
        dy = rng.randint(max(-40, margin - y1), min(40, self.H - margin - y2))
        for slot in self.slots:
            slot.cx += dx
            slot.cy += dy

    def _count_overlaps(self):

        c = 0
        for i in range(len(self.slots)):
            for j in range(i + 1, len(self.slots)):
                if self._masks_overlap(self._slot_mask(self.slots[i]),
                                       self._slot_mask(self.slots[j])):
                    c += 1
        return c

    def _print_final_report(self):

        info = getattr(self, "_fig_info", None)
        print("[ASSEMBLY-CAD] --- modulo v7 (figura finale) ---")
        if info:
            print(f"[ASSEMBLY-CAD] Figura CONNESSA '{info['layout']}': "
                  f"{info['n_struct']} piastre + {info['n_fast']} fissaggi.")
        for s in self.slots:
            print(f"  - slot {s.id}: {s.code} @ ({s.cx},{s.cy}) ang={s.angle:.0f}")
        sovrapposte = []
        for i in range(len(self.slots)):
            for j in range(i + 1, len(self.slots)):
                if self._masks_overlap(self._slot_mask(self.slots[i]),
                                       self._slot_mask(self.slots[j])):
                    sovrapposte.append(
                        f"{self.slots[i].code}+{self.slots[j].code}")
        if sovrapposte:
            print(f"[ASSEMBLY-CAD] SOVRAPPOSTE ({len(sovrapposte)}): "
                  f"{', '.join(sovrapposte)}")
        else:
            print("[ASSEMBLY-CAD] Nessuna sovrapposizione.")
        for c in getattr(self, "_fig_usable", []):
            L, W = self.part_size_mm(c)
            if L and W:
                tipo = "PIASTRA " if self.is_structural(c) else "fissaggio"
                print(f"     {c}: {tipo} {L:.0f}x{W:.0f}mm (rapporto {L/W:.1f})")

    def _build_figure(self, part_classes, plane_z_m, seed=None, compact=0.0,
                      layout_override=None):


        import random
        rng = random.Random(seed)

        self.plane_z_mm = plane_z_m * 1000.0 if plane_z_m else None


        usable = list(part_classes)


        if self.plane_z_mm and self.plane_z_mm > 0:
            px_per_mm = self.fx / self.plane_z_mm
        else:
            px_per_mm = 2.0


        structural = [c for c in usable if self.is_structural(c)]
        fasteners = [c for c in usable if not self.is_structural(c)]
        rng.shuffle(structural)
        rng.shuffle(fasteners)
        if not structural:
            structural, fasteners = usable, []


        layout = layout_override or self.layout
        if layout == "random":
            if n_hint := len(structural):
                if n_hint >= 3:
                    layout = rng.choice(["polygon", "parallel"])
                elif n_hint == 2:
                    layout = rng.choice(["elle", "parallel"])
                else:
                    layout = "parallel"


        gap_mm = CONTACT_GAP_MM


        placements = []
        anchors = []
        n = len(structural)
        theta0 = rng.uniform(0, 360)

        def add_anchors(cx, cy, L, W, theta, cos_t, sin_t):

            nx, ny = -sin_t, cos_t
            off = W / 2.0 + gap_mm
            for t in (-0.32, 0.0, 0.32):
                for side in (1.0, -1.0):
                    anchors.append((cx + cos_t * (t * L) + side * nx * off,
                                    cy + sin_t * (t * L) + side * ny * off,
                                    theta, side))

        if layout == "parallel":


            rad0 = math.radians(theta0)
            cos_t, sin_t = math.cos(rad0), -math.sin(rad0)
            nx, ny = -sin_t, cos_t
            offset = 0.0
            for i, code in enumerate(structural):
                L, W = self.part_size_mm(code)
                cx = nx * offset
                cy = ny * offset
                placements.append((code, cx, cy, theta0))
                add_anchors(cx, cy, L, W, theta0, cos_t, sin_t)
                nextW = (self.part_size_mm(structural[i + 1])[1]
                         if i + 1 < n else 0.0) or 0.0
                offset += W / 2.0 + gap_mm + nextW / 2.0
        else:


            verso = rng.choice((1.0, -1.0))
            x = y = 0.0
            theta = theta0
            for i, code in enumerate(structural):
                L, W = self.part_size_mm(code)
                rad = math.radians(theta)
                cos_t, sin_t = math.cos(rad), -math.sin(rad)
                cx = x + (L / 2.0) * cos_t
                cy = y + (L / 2.0) * sin_t
                placements.append((code, cx, cy, theta))
                add_anchors(cx, cy, L, W, theta, cos_t, sin_t)
                if i + 1 < n:
                    Wn = (self.part_size_mm(structural[i + 1])[1] or W)
                    ex = x + L * cos_t
                    ey = y + L * sin_t
                    theta += verso * 90.0
                    rad2 = math.radians(theta)
                    cos_v, sin_v = math.cos(rad2), -math.sin(rad2)


                    x = ex - cos_t * (Wn / 2.0) + cos_v * (W / 2.0 + gap_mm)
                    y = ey - sin_t * (Wn / 2.0) + sin_v * (W / 2.0 + gap_mm)


        rng.shuffle(anchors)
        for k, code in enumerate(fasteners):
            Lf, _ = self.part_size_mm(code)
            Lf = Lf or 10.0
            if anchors:
                ax, ay, ath, side = anchors[k % len(anchors)]
                rad = math.radians(ath)


                nx, ny = math.sin(rad), math.cos(rad)
                gx = ax + side * nx * (Lf / 2.0)
                gy = ay + side * ny * (Lf / 2.0)
            else:
                gx, gy = k * (Lf + gap_mm), 0.0
            placements.append((code, gx, gy, rng.uniform(0, 180)))


        xs = [p[1] for p in placements]
        ys = [p[2] for p in placements]
        mid_x = (min(xs) + max(xs)) / 2.0
        mid_y = (min(ys) + max(ys)) / 2.0
        area_cx = self.split_x + (self.W - self.split_x) // 2
        area_cy = self.H // 2

        self.slots = []
        for i, (code, xmm, ymm, ang) in enumerate(placements):
            px = int(area_cx + (xmm - mid_x) * px_per_mm)
            py = int(area_cy + (ymm - mid_y) * px_per_mm)
            self.slots.append(CadSlot(i, code, px, py, ang))

        self.generated = True
        self.completed = False


        self._snap_to_contact(px_per_mm)


        self._separate_overlaps(px_per_mm, -0.3)


        self._snap_to_contact(px_per_mm)
        self._separate_overlaps(px_per_mm, -0.3)


        self._fig_info = {"layout": layout, "n_struct": len(structural),
                          "n_fast": len(fasteners)}
        self._fig_usable = sorted(set(usable))


    def _scaled_rotated_silhouette(self, code, angle_deg):


        key = (code, round(angle_deg % 360, 6), self.plane_z_mm)
        if key in self._silhouette_cache:
            return self._silhouette_cache[key]
        img = self.lib.get_image(code)
        if img is None:
            return None
        mm_per_px_native = self.lib.mm_per_px_native(code)
        if mm_per_px_native is None:
            return None


        if self.plane_z_mm and self.plane_z_mm > 0:
            px_screen_per_mm = self.fx / self.plane_z_mm
        else:

            px_screen_per_mm = 2.0
        scale = mm_per_px_native * px_screen_per_mm

        new_w = max(1, int(img.shape[1] * scale))
        new_h = max(1, int(img.shape[0] * scale))
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)


        M = cv2.getRotationMatrix2D((new_w / 2, new_h / 2), angle_deg, 1.0)
        cos = abs(M[0, 0]); sin = abs(M[0, 1])
        bound_w = max(1, int(math.ceil(new_h * sin + new_w * cos)))
        bound_h = max(1, int(math.ceil(new_h * cos + new_w * sin)))
        M[0, 2] += bound_w / 2 - new_w / 2
        M[1, 2] += bound_h / 2 - new_h / 2
        rotated = cv2.warpAffine(resized, M, (bound_w, bound_h),
                                 flags=cv2.INTER_NEAREST,
                                 borderValue=(0, 0, 0, 0))
        self._silhouette_cache[key] = rotated
        return rotated


    def _overlay_bgra(self, base_bgr, overlay_bgra, cx, cy, tint, alpha_mul=1.0):


        oh, ow = overlay_bgra.shape[:2]
        x1 = int(cx - ow / 2); y1 = int(cy - oh / 2)
        x2 = x1 + ow; y2 = y1 + oh


        bx1, by1 = max(0, x1), max(0, y1)
        bx2, by2 = min(base_bgr.shape[1], x2), min(base_bgr.shape[0], y2)
        if bx1 >= bx2 or by1 >= by2:
            return
        ox1, oy1 = bx1 - x1, by1 - y1
        ox2, oy2 = ox1 + (bx2 - bx1), oy1 + (by2 - by1)

        roi = base_bgr[by1:by2, bx1:bx2]
        ov = overlay_bgra[oy1:oy2, ox1:ox2]
        alpha = (ov[..., 3].astype(np.float32) / 255.0) * alpha_mul
        alpha = alpha[..., None]


        tint_arr = np.zeros_like(roi, dtype=np.float32)
        tint_arr[:] = tint
        base_bgr[by1:by2, bx1:bx2] = (roi * (1 - alpha) + tint_arr * alpha).astype(np.uint8)


    def update(self, placed_parts):


        if not self.generated:
            self.last_matches = {}
            return []
        self.last_matches = self._assign_parts(placed_parts)
        newly = []
        for slot in self.slots:
            match = self.last_matches.get(slot.id)
            if match is not None:
                slot.missing_count = 0
                slot.matched_tid = match.get("tid")
                slot.stable_count = min(self.stability_frames, slot.stable_count + 1)
                if not slot.completed and slot.stable_count >= self.stability_frames:
                    slot.completed = True
                    newly.append({"slot_id": slot.id, "class": slot.code})
            else:
                slot.stable_count = 0
                slot.missing_count += 1
                if slot.missing_count >= self.missing_frames:
                    slot.completed = False
                    slot.matched_tid = None
        self.completed = bool(self.slots) and all(s.completed for s in self.slots)
        return newly

    def _match_distance(self, slot, part):
        if str(part.get("class_name", "")).upper() != slot.code.upper():
            return None
        try:
            cx, cy = float(part["cx"]), float(part["cy"])
            if not (math.isfinite(cx) and math.isfinite(cy)):
                return None
            if not self.is_in_assembly_area(cx, cy):
                return None
            distance = math.hypot(cx - slot.cx, cy - slot.cy)
            if distance > POS_TOL_PX:
                return None
            if self.check_rotation and slot.code.upper() not in ROUND_PARTS:
                angle = part.get("angle_deg")


                if angle is not None:
                    if not math.isfinite(float(angle)):
                        return None
                    if self._angle_diff(float(angle), slot.angle) > self.rot_tol_deg:
                        return None
            return distance
        except (KeyError, TypeError, ValueError):
            return None

    def _assign_parts(self, placed_parts):


        parts, seen = [], set()
        for index, part in enumerate(placed_parts):
            key = ("tid", part["tid"]) if part.get("tid") is not None else ("row", index)
            if key not in seen:
                seen.add(key)
                parts.append(part)
        edges = {}
        for i, slot in enumerate(self.slots):
            candidates = []
            for j, part in enumerate(parts):
                distance = self._match_distance(slot, part)
                if distance is not None:
                    same_id = (slot.matched_tid is not None and
                               slot.matched_tid == part.get("tid"))
                    candidates.append((distance - (0.01 if same_id else 0), j))
            edges[i] = [j for _, j in sorted(candidates)]
        owners = {}

        def assign(i, visited):
            for j in edges[i]:
                if j not in visited and j not in owners:
                    visited.add(j)
                    owners[j] = i
                    return True
            for j in edges[i]:
                if j in visited:
                    continue
                visited.add(j)
                if assign(owners[j], visited):
                    owners[j] = i
                    return True
            return False

        for i in sorted(edges, key=lambda k: (len(edges[k]),
                                              not self.slots[k].completed,
                                              self.slots[k].id)):
            assign(i, set())
        return {self.slots[i].id: parts[j] for j, i in owners.items()}

    def _find_match(self, slot, placed_parts):

        valid = [(self._match_distance(slot, p), index, p)
                 for index, p in enumerate(placed_parts)]
        valid = [item for item in valid if item[0] is not None]
        return min(valid, key=lambda item: (item[0], item[1]))[2] if valid else None

    @staticmethod
    def _angle_diff(a, b):


        def diff_mod180(x, y):
            d = abs((x - y) % 180.0)
            return min(d, 180.0 - d)

        d = diff_mod180(ANGLE_SIGN * a, b)
        if ALLOW_MIRRORED_ANGLE:
            d = min(d, diff_mod180(-ANGLE_SIGN * a, b))
        return d

    @staticmethod
    def _angle_diff_both(a, b):

        def dm(x, y):
            d = abs((x - y) % 180.0)
            return min(d, 180.0 - d)
        return dm(a, b), dm(-a, b)


    def can_render(self, code):

        code = str(code).upper()
        info = self.lib.meta.get("parts", {}).get(code)
        if not isinstance(info, dict):
            return False
        try:
            values = [float(info["mm_per_px"]), *map(float, info["size_mm"])]
            if len(values) != 3 or any(not math.isfinite(v) or v <= 0 for v in values):
                return False
            return self.lib.get_image(code) is not None
        except (KeyError, TypeError, ValueError, OSError):
            return False

    def renderable(self, codes):

        return [c for c in codes if self.can_render(c)]

    def clear(self):

        self.slots = []
        self.generated = False
        self.completed = False
        self._fig_info = None
        self._fig_usable = []
        self._mask_cache = {}
        self._silhouette_cache = {}
        self.last_matches = {}
        self.last_error = ""


    def progress(self):
        done = sum(1 for s in self.slots if s.completed)
        return done, len(self.slots)


    def draw(self, img, show_progress=True, show_labels=True):

        H, W = img.shape[:2]


        cv2.line(img, (self.split_x, 0), (self.split_x, H), (200, 200, 200), 2)

        _y = H - 18
        cv2.putText(img, "PARTENZA", (24, _y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (175, 175, 175), 1,
                    cv2.LINE_AA)
        cv2.putText(img, "MONTAGGIO", (self.split_x + 24, _y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (175, 175, 175), 1,
                    cv2.LINE_AA)

        for slot in self.slots:
            sil = self._scaled_rotated_silhouette(slot.code, slot.angle)

            if slot.completed:
                tint = (0, 200, 0)
            elif slot.stable_count > 0:
                tint = (0, 220, 255)
            else:
                tint = (255, 180, 0)

            if sil is not None:
                a = SILHOUETTE_ALPHA * (1.0 if not slot.completed else 0.8)
                self._overlay_bgra(img, sil, slot.cx, slot.cy, tint, alpha_mul=a)
            else:

                cv2.circle(img, (slot.cx, slot.cy), 40, tint, 2)

            if show_labels:

                cv2.putText(img, slot.code, (slot.cx - 30, slot.cy - 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                if slot.completed:
                    cv2.putText(img, "OK", (slot.cx - 20, slot.cy + 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                elif slot.stable_count > 0:
                    frac = min(1.0, slot.stable_count / self.stability_frames)
                    cv2.putText(img, f"{int(frac*100)}%",
                                (slot.cx - 20, slot.cy + 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)


        done, total = self.progress()
        if total > 0 and show_progress:
            txt = f"Montaggio: {done}/{total}"
            if self.completed:
                txt += "  COMPLETATO!"
            cv2.putText(img, txt, (self.split_x + 20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                        (0, 255, 0) if self.completed else (255, 255, 255), 2)
