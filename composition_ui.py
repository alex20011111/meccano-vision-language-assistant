from collections import deque
import cv2
import numpy as np
from composition_controller import format_counts, is_hand
from parts_catalog import PARTS_CATALOG

FONT = cv2.FONT_HERSHEY_SIMPLEX


def put_text(img, text, xy, scale=0.48, colour=(225, 225, 225), thickness=1):

    text = str(text).translate(str.maketrans("àèéìòù", "aeeiou"))
    cv2.putText(img, text, xy, FONT, scale, colour, thickness, cv2.LINE_AA)


def wrap_text(text, width, scale=0.46):
    lines, line = [], ""
    for word in str(text).split():
        candidate = (line + " " + word).strip()
        if line and cv2.getTextSize(candidate, FONT, scale, 1)[0][0] > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def draw_left_highlights(image, parts, split_x):

    left = image[:, :split_x]
    h, w = left.shape[:2]
    for index, part in enumerate(parts, start=1):
        x1, y1, x2, y2 = map(int, part["bbox"])
        x1, x2 = max(0, x1-6), min(w-1, x2+6)
        y1, y2 = max(0, y1-6), min(h-1, y2+6)
        cv2.rectangle(left, (x1,y1), (x2,y2), (0,255,255), 5)
        label = f"#{index} {part['class_name']}"
        (tw, th), _ = cv2.getTextSize(label, FONT, 0.70, 2)

        ty = min(h-7, y2+th+12)
        tx = max(0, min(x1, w-tw-8))
        cv2.rectangle(left, (tx, ty-th-6), (min(w-1,tx+tw+8),ty+6), (0,0,0), -1)
        put_text(left, label, (tx+4,ty), 0.70, (0,255,255), 2)


def draw_workspace_blockers(image, blockers, split_x):


    height, width = image.shape[:2]
    split = max(0, min(width, int(split_x)))
    right = image[:, split:]
    if right.size == 0:
        return
    for detection in blockers:
        if detection.get("source") == "tracking":
            continue
        x1, y1, x2, y2 = detection["bbox"]
        x1 = max(0, min(width - split - 1, int(x1) - split))
        x2 = max(0, min(width - split - 1, int(x2) - split))
        y1 = max(0, min(height - 1, int(y1)))
        y2 = max(0, min(height - 1, int(y2)))
        colour = (70, 140, 255)
        cv2.rectangle(right, (x1, y1), (x2, y2), colour, 2)
        code = detection.get("class_name", "?")
        label = "MANO: LIBERA IL PIANO" if is_hand(code) else f"CONTROLLO DX {code} (senza ID)"
        confidence = detection.get("conf")
        if confidence is not None:
            label += f" {float(confidence):.2f}"
        scale = min(0.58, max(1, right.shape[1]-12) /
                    max(1, cv2.getTextSize(label, FONT, 1, 1)[0][0]))
        (tw, th), _ = cv2.getTextSize(label, FONT, scale, 1)
        tx = max(0, min(x1, right.shape[1]-tw-8))
        ty = min(height-5, max(th+7, y1-7))
        cv2.rectangle(right, (tx, ty-th-4), (min(right.shape[1]-1,tx+tw+8),ty+4),
                      (20,20,20), -1)
        put_text(right, label, (tx+3,ty), scale, colour)


def workspace_status(controller):

    if not controller.frame_valid:
        return "DESTRO: CONTROLLO NON DISPONIBILE"
    if controller.guard.occupied:
        count = sum(not is_hand(d.get("class_name")) for d in controller.right_blockers)
        return f"DESTRO OCCUPATO ({count})" if count else "DESTRO: MANO PRESENTE"
    if controller.guard.ready(controller._now):
        return "DESTRO LIBERO"
    return "DESTRO: VERIFICA IN CORSO"


def workspace_rows(controller):

    rows = [("", (0,0,0)), ("CONTROLLO PIANO DESTRO", (190,210,220))]
    status_colour = ((150,150,180) if not controller.frame_valid else
                     (120,195,255) if controller.guard.occupied else
                     (150,220,150) if controller.guard.ready(controller._now) else (180,180,180))
    rows.append((workspace_status(controller), status_colour))
    for detection in controller.right_blockers:
        code = detection.get("class_name", "?")
        tid = detection.get("tid")
        source = f"ID{tid}" if detection.get("source") == "tracking" and tid is not None else "senza ID"
        label = f"{code} - {source}"
        if detection.get("conf") is not None:
            label += f" - {float(detection['conf']):.2f}"
        rows.append((label, (120,195,255)))
        rows.append((f"  x2={detection['bbox'][2]:.1f}; linea={controller.guide.split_x}",
                     (155,155,155)))
    rejected = controller.rejected_detections
    if rejected:
        rows.append((f"Candidati grezzi scartati: {len(rejected)}", (150,150,150)))
        if any(d["reason"] == "confidenza bassa" for d in rejected):
            rows.append(("  Confidenza insufficiente.", (150,150,150)))
        if any(d["reason"] != "confidenza bassa" for d in rejected):
            rows.append(("  Box/coordinate non plausibili.", (150,150,150)))
    return rows


class CompositionUI:
    def __init__(self, window_name, max_width=1280, max_height=720):
        self.window_name = window_name
        self.width, self.height = max_width, max_height
        self.toolbar_h, self.footer_h, self.panel_w = 54, 110, 300
        self.pending = deque()
        self.buttons = []
        self.scroll = 0

    def open(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

    def mouse_callback(self, event, x, y, flags, param=None):
        if event == cv2.EVENT_LBUTTONDOWN:
            for action, (x1,y1,x2,y2) in self.buttons:
                if x1 <= x < x2 and y1 <= y < y2:


                    self.pending.append(action)
                    return
        elif event == cv2.EVENT_MOUSEWHEEL and x >= self.width-self.panel_w:
            delta = flags >> 16
            self.scroll = max(0, self.scroll + (-3 if delta > 0 else 3))

    def pop_actions(self):
        actions = list(self.pending)
        self.pending.clear()
        return actions

    def draw(self, camera, controller, voice=None):
        canvas = np.full((self.height, self.width, 3), 23, dtype=np.uint8)
        content_h = self.height-self.toolbar_h-self.footer_h
        content_w = self.width-self.panel_w
        ch, cw = camera.shape[:2]
        scale = min(content_w/cw, content_h/ch, 1.0)
        vw, vh = max(1,int(cw*scale)), max(1,int(ch*scale))
        ox = (content_w-vw)//2
        oy = self.toolbar_h+(content_h-vh)//2
        canvas[oy:oy+vh,ox:ox+vw] = cv2.resize(camera,(vw,vh), interpolation=cv2.INTER_AREA)
        ready = not controller.readiness_reason(controller._now)
        states = [
            ("start", "[G] Avvia composizione", not controller.guide.generated and ready),
            ("verify", "[V] Nascondi verifica" if controller.verification_visible else "[V] Verifica pezzi",
             controller.guide.generated),
            ("change", "[N] Cambia composizione", controller.guide.generated and ready),
            ("voice", "[R] Domanda vocale", voice is not None and not voice.is_busy()),
            ("stop_voice", "[S] Stop voce", voice is not None),
            ("finish", "[X] Concludi / azzera", True)]
        gap = 8
        bw = (self.width-gap*(len(states)+1))//len(states)
        self.buttons = []
        for i, (action,label,enabled) in enumerate(states):
            x1, y1 = gap+i*(bw+gap), 8
            x2, y2 = x1+bw, self.toolbar_h-7
            active = action == "verify" and controller.verification_visible
            bg = (72,75,36) if active else ((57,67,61) if enabled else (39,39,39))
            cv2.rectangle(canvas,(x1,y1),(x2,y2),bg,-1)
            cv2.rectangle(canvas,(x1,y1),(x2,y2),(95,110,99) if enabled else (66,66,66),1)
            button_scale = min(0.46, (bw-12)/max(1,cv2.getTextSize(label,FONT,1,1)[0][0]))
            tw = cv2.getTextSize(label,FONT,button_scale,1)[0][0]
            put_text(canvas,label,(x1+(bw-tw)//2, y1+24),button_scale,
                     (235,235,235) if enabled else (145,145,145))
            self.buttons.append((action,(x1,y1,x2,y2)))
        self._draw_panel(canvas, controller)
        report = controller.report()
        fy = self.height-self.footer_h
        cv2.line(canvas,(0,fy),(self.width,fy),(74,74,74),1)
        right_status = workspace_status(controller)
        voice_state = voice.state if voice is not None else "non disponibile"
        first = (f"Sinistra: {len(controller.left_parts)} riconosciuti | "
                 f"Completati: {report['done']}/{report['total']} | {right_status} | Voce: {voice_state}")
        put_text(canvas,first,(10,fy+20),0.45)
        message_y = fy+44
        if controller.return_warning:

            cv2.rectangle(canvas,(6,fy+28),(self.width-7,fy+60),(36,36,104),-1)
            scale = min(0.62, (self.width-30)/max(1,cv2.getTextSize(
                controller.return_warning,FONT,1,2)[0][0]))
            put_text(canvas,controller.return_warning,(14,fy+51),scale,(255,255,255),2)
            message_y = fy+79
        voice_error = getattr(voice, "last_error", "") if voice is not None else ""
        message = ("Errore voce: " + voice_error) if voice_error else controller.message
        lines = wrap_text(message,self.width-24,0.43)
        for i,line in enumerate(lines[:2]):
            put_text(canvas,line,(10,message_y+17*i),0.43,(170,225,235))
        put_text(canvas,"Q / ESC: esci",(self.width-116,self.height-5),0.35,(140,140,140))
        return canvas

    def _draw_panel(self, canvas, controller):
        x = self.width-self.panel_w
        bottom = self.height-self.footer_h
        cv2.rectangle(canvas,(x,self.toolbar_h),(self.width-1,bottom),(29,29,29),-1)
        put_text(canvas,"PEZZI DELLA COMPOSIZIONE",(x+12,self.toolbar_h+25),0.49)
        report = controller.report()
        if not report["total"]:
            lines = ["1. Tutti i pezzi a sinistra.", "2. Piano destro libero.",
                     "3. Attendi il riconoscimento.", "4. Premi Avvia [G].", "",
                     "Una sagoma per ogni pezzo,", "incluse le copie uguali."]
            rows = [(line, (225,225,225)) for line in lines] + workspace_rows(controller)
            self._draw_rows(canvas, rows, x, self.toolbar_h+60, bottom)
            return

        complete = controller.guide.completed
        summary = f"{report['done']} / {report['total']} completati"
        if complete:
            summary += " - OK"
        put_text(canvas,summary,(x+12,self.toolbar_h+49),0.49,
                 (110,230,110) if complete else (220,220,220))
        put_text(canvas,"Codice       OK/Tot   A destra",(x+12,self.toolbar_h+73),0.43)

        rows = []
        for code in sorted(set(report["required"]) | set(report["right_present"])):
            done, total = report["completed"][code], report["required"][code]
            right = report["right_present"][code]
            rows.append((f"{code:<10} {done:>2}/{total:<3}     {right}", (220,220,220)))
            synonyms = PARTS_CATALOG.get(code,{}).get("sinonimi",[])
            if synonyms and "[" not in synonyms[0]:
                rows.append(("  "+synonyms[0],(145,145,145)))
        if controller.verification_visible:
            rows.append(("",(0,0,0)))
            rows.append(("DA PRENDERE A SINISTRA",(0,230,230)))
            if not report["left_matches"]:
                rows.append(("Nessun pezzo da evidenziare.",(190,190,190)))
            for i,part in enumerate(report["left_matches"],1):
                rows.append((f"#{i} {part['class_name']}  (riquadro giallo)",(0,230,230)))
            for title,key in (("Gia' a destra, da sistemare:","right_pending"),
                              ("Non localizzati:","unlocated"),
                              ("Pezzi in piu' a destra:","unexpected_right")):
                if report[key]:
                    rows.append((title,(170,205,240)))
                    for line in wrap_text(format_counts(report[key]),self.panel_w-26,0.43):
                        rows.append((line,(195,195,195)))
        else:
            rows += [("",(0,0,0)),("[V] individua i pezzi mancanti",(0,225,225))]
        rows += workspace_rows(controller)
        self._draw_rows(canvas, rows, x, self.toolbar_h+99, bottom)

    def _draw_rows(self, canvas, rows, x, y0, bottom):
        row_h = 21
        capacity = max(1,(bottom-y0-24)//row_h)
        self.scroll = min(self.scroll,max(0,len(rows)-capacity))
        for i,(text,colour) in enumerate(rows[self.scroll:self.scroll+capacity]):
            put_text(canvas,text,(x+12,y0+i*row_h),0.43,colour)
        if len(rows) > capacity:
            put_text(canvas,"Rotella qui: scorri tutti i pezzi",(x+10,bottom-10),0.4,(160,160,160))
