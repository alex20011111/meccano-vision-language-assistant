import cv2
import numpy as np


def estimate_angle_deg(bgr_image, bbox, method="saturation"):


    x1, y1, x2, y2 = [int(v) for v in bbox]
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(bgr_image.shape[1], x2); y2 = min(bgr_image.shape[0], y2)
    if x2 - x1 < 5 or y2 - y1 < 5:
        return None, None

    roi = bgr_image[y1:y2, x1:x2]

    if method == "saturation":
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        s = hsv[..., 1]

        _, mask = cv2.threshold(s, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 0, 255,
                                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)


    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None


    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < 30:
        return None, None


    rect = cv2.minAreaRect(c)
    (rw, rh) = rect[1]
    angle = rect[2]


    if rw < rh:
        angle = angle + 90.0
    angle = angle % 180.0


    long_side = max(rw, rh)
    short_side = min(rw, rh) if min(rw, rh) > 0 else 1.0
    aspect = long_side / short_side

    return angle, aspect


class AngleSmoother:


    def __init__(self, window=7):
        from collections import defaultdict, deque
        self.window = window
        self._buf = defaultdict(lambda: deque(maxlen=window))

    def update(self, obj_id, angle_deg):

        import math
        if angle_deg is None:
            return self.get(obj_id)
        self._buf[obj_id].append(float(angle_deg))
        return self.get(obj_id)

    def get(self, obj_id):
        import math
        buf = self._buf.get(obj_id)
        if not buf:
            return None

        sx = sum(math.cos(math.radians(2 * a)) for a in buf)
        sy = sum(math.sin(math.radians(2 * a)) for a in buf)
        if sx == 0 and sy == 0:
            return buf[-1]
        mean = math.degrees(math.atan2(sy, sx)) / 2.0
        return mean % 180.0

    def cleanup(self, active_ids):

        for k in list(self._buf.keys()):
            if k not in active_ids:
                del self._buf[k]
