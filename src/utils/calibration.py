import sys
import time
import cv2
import numpy as np
from src.utils.config import CALIBRATION_ITEMS, RESOURCES, ROI_COLORS
from src.vision.capture import capture_frame
from src.vision.detection import preprocess_for_ocr, point_in_rect
from src.utils.roi_manager import save_rois

C_BG         = (10,  14,  20)
C_PANEL      = (16,  22,  30)
C_BORDER     = (35,  50,  65)
C_BORDER_LIT = (60,  90, 115)
C_WHITE      = (235, 240, 245)
C_DIM        = (80, 100, 120)
C_CONFIRM    = (55, 180,  80)
C_CONFIRM_DK = (20,  60,  28)
C_CANCEL     = (65,  65, 190)
C_CANCEL_DK  = (25,  25,  75)
C_BACK       = (140, 140, 140)
C_BACK_DK    = (50,  50,  50)

CALIBRATION_DESCRIPTIONS = {
    "gold": "Box the NUMBERS of your HOME Gold (top right)",
    "elixir": "Box the NUMBERS of your HOME Elixir (top right)",
    "dark_elixir": "Box the NUMBERS of your HOME Dark Elixir",
    "enemy_gold": "Box the NUMBERS of the ENEMY Gold (top left)",
    "enemy_elixir": "Box the NUMBERS of the ENEMY Elixir",
    "enemy_dark_elixir": "Box the NUMBERS of the ENEMY Dark Elixir",
    "main_screen_i": "Box the BLUE [ i ] BUTTON (e.g. next to shield or builders)",
    "upgrades_menu": "Box the scrollable LIST AREA of the Upgrades tab",
    "builders_icon": "Box the FRACTION (e.g., 5/5) of your available Builders"
}

RES_ACCENT = {
    "gold":              (40,  185, 245),
    "elixir":            (205,  75, 175),
    "dark_elixir":       (195, 115,  35),
    "enemy_gold":        (40,  185, 245),
    "enemy_elixir":      (205,  75, 175),
    "enemy_dark_elixir": (195, 115,  35),
    "main_screen_i":     (255, 255, 255), 
    "upgrades_menu":     (100, 255, 100),
    "builders_icon":     (100, 200, 255),
}

WIN_NAME = "CoC [CALIBRATION]"
WIN_W, WIN_H = 1280, 720
def alpha_fill(img, x1, y1, x2, y2, color, a=0.7):
    x1,y1 = max(0,x1), max(0,y1)
    x2,y2 = min(img.shape[1],x2), min(img.shape[0],y2)
    if x2<=x1 or y2<=y1: return
    roi   = img[y1:y2, x1:x2]
    block = np.full(roi.shape, color, dtype=np.uint8)
    cv2.addWeighted(block, a, roi, 1-a, 0, roi)
    img[y1:y2, x1:x2] = roi


def rr(img, x1, y1, x2, y2, r, color, t=1):
    cv2.line(img,(x1+r,y1),(x2-r,y1),color,t)
    cv2.line(img,(x1+r,y2),(x2-r,y2),color,t)
    cv2.line(img,(x1,y1+r),(x1,y2-r),color,t)
    cv2.line(img,(x2,y1+r),(x2,y2-r),color,t)
    cv2.ellipse(img,(x1+r,y1+r),(r,r),180,0,90,color,t)
    cv2.ellipse(img,(x2-r,y1+r),(r,r),270,0,90,color,t)
    cv2.ellipse(img,(x1+r,y2-r),(r,r), 90,0,90,color,t)
    cv2.ellipse(img,(x2-r,y2-r),(r,r),  0,0,90,color,t)


def txt(img, s, x, y, scale=0.42, color=C_DIM, bold=False):
    font = cv2.FONT_HERSHEY_DUPLEX if bold else cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, s, (x,y), font, scale, color, 2 if bold else 1, cv2.LINE_AA)


def panel(img, x1, y1, x2, y2, a=0.90, border=C_BORDER):
    alpha_fill(img, x1, y1, x2, y2, C_PANEL, a)
    rr(img, x1, y1, x2, y2, 5, border)


def crosshair(img, x, y, w, h, color):
    L = max(8, min(w, h, 24))
    segs =[
        ((x,y),(x+L,y)),((x,y),(x,y+L)),
        ((x+w,y),(x+w-L,y)),((x+w,y),(x+w,y+L)),
        ((x,y+h),(x+L,y+h)),((x,y+h),(x,y+h-L)),
        ((x+w,y+h),(x+w-L,y+h)),((x+w,y+h),(x+w,y+h-L)),
    ]
    for p1,p2 in segs:
        cv2.line(img,p1,p2,color,2,cv2.LINE_AA)
    cv2.drawMarker(img,(x+w//2,y+h//2),color,cv2.MARKER_CROSS,14,1,cv2.LINE_AA)


def hud_button(img, label, x, y, w, h, mx, my, bg_dk, border, bg_hot):
    hot = point_in_rect(mx, my, (x,y,x+w,y+h))
    alpha_fill(img, x, y, x+w, y+h, bg_hot if hot else bg_dk, 0.88)
    rr(img, x, y, x+w, y+h, 5, C_WHITE if hot else border)
    (tw,th),_ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
    cv2.putText(img, label, (x+(w-tw)//2, y+(h+th)//2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                C_WHITE if hot else C_DIM, 2 if hot else 1, cv2.LINE_AA)
    return (x, y, x+w, y+h)


def progress_dots(img, cx, y, total, current, accent):
    sp = 22
    sx = cx - (total*sp)//2
    for i in range(total):
        c = accent if i<current else (C_BORDER_LIT if i==current else C_BORDER)
        r = 5 if i==current else 3
        cv2.circle(img,(sx+i*sp,y),r,c,-1,cv2.LINE_AA)
        if i<total-1:
            cv2.line(img,(sx+i*sp+r+2,y),(sx+(i+1)*sp-r-2,y),
                     accent if i<current else C_BORDER, 1)


# ─────────────────────────────────────────────────────────
#  CUSTOM MOUSE-DRIVEN SLIDER
# ─────────────────────────────────────────────────────────
BTN_SZ    = 16
FINE_STEP = 0.001

class Slider:
    def __init__(self, key, label, value):
        self.key      = key
        self.label    = label
        self.value    = float(value)
        self.dragging = False
        self.bx = self.by = self.bw = self.bh = 0
        self._rect_minus = None
        self._rect_plus  = None

    def layout(self, bx, by, bw, bh=10):
        self.bx, self.by, self.bw, self.bh = bx, by, bw, bh
        val_end = bx + bw + 56
        mid_y   = by + bh // 2
        self._rect_minus = (val_end,            mid_y - BTN_SZ//2,
                            val_end + BTN_SZ,   mid_y + BTN_SZ//2)
        self._rect_plus  = (val_end + BTN_SZ + 3, mid_y - BTN_SZ//2,
                            val_end + BTN_SZ*2+3,  mid_y + BTN_SZ//2)

    def _clamp(self, v):
        return round(max(0.0, min(1.0, v)), 4)

    def on_mouse(self, event, mx, my):
        hit_track = (self.bx-8 <= mx <= self.bx+self.bw+8 and
                     self.by-8 <= my <= self.by+self.bh+8)
        if event == cv2.EVENT_LBUTTONDOWN:
            if hit_track:
                self.dragging = True
            if self._rect_minus and point_in_rect(mx, my, self._rect_minus):
                self.value = self._clamp(self.value - FINE_STEP)
            if self._rect_plus  and point_in_rect(mx, my, self._rect_plus):
                self.value = self._clamp(self.value + FINE_STEP)
        if event == cv2.EVENT_LBUTTONUP:
            self.dragging = False
        if self.dragging:
            self.value = self._clamp((mx - self.bx) / max(self.bw, 1))

    def draw(self, img, accent, mx, my):
        bx, by, bw, bh = self.bx, self.by, self.bw, self.bh
        filled = int(self.value * bw)
        alpha_fill(img, bx,        by, bx+bw,    by+bh, C_BORDER, 0.9)
        if filled > 0:
            alpha_fill(img, bx,    by, bx+filled, by+bh, accent,  0.75)
        tx = bx + filled
        cv2.circle(img, (tx, by+bh//2), 7, accent, -1, cv2.LINE_AA)
        cv2.circle(img, (tx, by+bh//2), 7, C_WHITE,  1, cv2.LINE_AA)
        txt(img, self.label,           bx-22,     by+bh//2+4, 0.42, C_DIM)
        txt(img, f"{self.value:.4f}",  bx+bw+10,  by+bh//2+4, 0.40, C_WHITE)

        # − button
        x1,y1,x2,y2 = self._rect_minus
        hot_m = point_in_rect(mx, my, self._rect_minus)
        alpha_fill(img, x1, y1, x2, y2, accent if hot_m else C_BORDER, 0.85)
        rr(img, x1, y1, x2, y2, 2, C_WHITE if hot_m else C_BORDER_LIT)
        cv2.putText(img, "-", (x1+4, y2-3),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, C_WHITE, 1, cv2.LINE_AA)

        # + button
        x1,y1,x2,y2 = self._rect_plus
        hot_p = point_in_rect(mx, my, self._rect_plus)
        alpha_fill(img, x1, y1, x2, y2, accent if hot_p else C_BORDER, 0.85)
        rr(img, x1, y1, x2, y2, 2, C_WHITE if hot_p else C_BORDER_LIT)
        cv2.putText(img, "+", (x1+3, y2-3),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, C_WHITE, 1, cv2.LINE_AA)


# ─────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────
def calibrate(hwnd: int, existing_rois: dict = None) -> dict:
    rois  = existing_rois.copy() if existing_rois else {}
    mouse = {"x":0, "y":0, "event":-1}

    defaults = {
        "gold":              {"x": 0.8700, "y": 0.0367, "w": 0.0840, "h": 0.0237},
        "elixir":            {"x": 0.8700, "y": 0.1157, "w": 0.0840, "h": 0.0237},
        "dark_elixir":       {"x": 0.8907, "y": 0.1927, "w": 0.0653, "h": 0.0257},
        "enemy_gold":        {"x": 0.0427, "y": 0.1123, "w": 0.0667, "h": 0.0350},
        "enemy_elixir":      {"x": 0.0387, "y": 0.1583, "w": 0.0737, "h": 0.0350},
        "enemy_dark_elixir": {"x": 0.0367, "y": 0.2000, "w": 0.0500, "h": 0.0350},
        "main_screen_i":     {"x": 0.0367, "y": 0.2000, "w": 0.0500, "h": 0.0350}, 
        "upgrades_menu":     {"x": 0.4040, "y": 0.1187, "w": 0.2170, "h": 0.5270},
        "builders_icon":     {"x": 0.4937, "y": 0.0320, "w": 0.0407, "h": 0.0327},
    }

    items_to_calibrate =[r for r in CALIBRATION_ITEMS if r not in rois]
    total = len(items_to_calibrate)

    if total == 0:
        return rois  # Safety check in case it was called when fully calibrated

    cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN_NAME, WIN_W, WIN_H)

    step = 0
    last_roi = None

    while step < total:
        resource = items_to_calibrate[step]
        accent = RES_ACCENT.get(resource, (180,180,60))
        
        # 1. If we already visited this step (e.g. went back), load it.
        # 2. If not, but we just calibrated the previous item, spawn the box with the EXACT same X, Y, W, H
        # 3. Otherwise, use defaults.
        if resource in rois:
            d = rois[resource]
        else:
            d = defaults.get(resource, {"x":0.5, "y":0.5, "w":0.2, "h":0.2})

        sliders =[
            Slider("x","X", d["x"]),
            Slider("y","Y", d["y"]),
            Slider("w","W", d["w"]),
            Slider("h","H", d["h"]),
        ]

        # Bottom-left slider panel geometry
        BAR_H_CONST = 68
        PNL_H_CONST = 44 + len(sliders)*36 + 14
        PNL_W  = 290
        PNL_X  = 10
        PNL_Y  = WIN_H - BAR_H_CONST - PNL_H_CONST - 10
        SL_BX  = PNL_X + 34
        SL_BW  = 120
        for i, sl in enumerate(sliders):
            sl.layout(SL_BX, PNL_Y + 44 + i*36, SL_BW, 10)

        def on_mouse(event, mx, my, flags, param):
            mouse["x"] = mx
            mouse["y"] = my
            mouse["event"] = event
            for sl in sliders:
                sl.on_mouse(event, mx, my)

        cv2.setMouseCallback(WIN_NAME, on_mouse)

        while True:
            frame = capture_frame(hwnd)
            if frame is None:
                time.sleep(0.05)
                continue

            h_f, w_f = frame.shape[:2]
            mx_m, my_m = mouse["x"], mouse["y"]
            x_r = sliders[0].value
            y_r = sliders[1].value
            w_r = sliders[2].value
            h_r = sliders[3].value

            rx = int(x_r * w_f);  ry = int(y_r * h_f)
            rw = int(w_r * w_f);  rh = int(h_r * h_f)

            vis = cv2.resize(frame, (WIN_W, WIN_H))
            sx  = WIN_W / w_f;  sy = WIN_H / h_f

            crx = max(0, min(WIN_W-1, int(rx*sx)))
            cry = max(0, min(WIN_H-1, int(ry*sy)))
            crw = max(4, min(WIN_W - crx - 1, int(rw*sx)))
            crh = max(4, min(WIN_H - cry - 1, int(rh*sy)))

            # Dim outside ROI
            mask = np.full(vis.shape, 35, dtype=np.uint8)
            mask[cry:cry+crh, crx:crx+crw] = 0
            cv2.addWeighted(mask, 0.62, vis, 1.0, 0, vis)

            # ROI crosshair
            crosshair(vis, crx, cry, crw, crh, accent)

            # Name tag
            tag = resource.upper().replace("_", " ")
            (tw,_),_ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            tag_y1 = max(0, cry - 26)
            tag_y2 = max(20, cry - 5)
            alpha_fill(vis, crx, tag_y1, crx+tw+14, tag_y2, C_PANEL, 0.90)
            txt(vis, tag, crx+7, max(14, cry-10), 0.45, accent)

            desc_text = CALIBRATION_DESCRIPTIONS.get(resource, "Adjust sliders to box the target area.")
            (tw_d, th_d), _ = cv2.getTextSize(desc_text, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1)
            
            tx = (WIN_W - tw_d) // 2
            ty = 45
            panel(vis, tx - 25, ty - 30, tx + tw_d + 25, ty + 15, 0.95, border=accent)
            txt(vis, desc_text, tx, ty, 0.6, C_WHITE, bold=True)
            panel(vis, PNL_X-4, PNL_Y, PNL_X+PNL_W, PNL_Y+PNL_H_CONST, 0.93)
            txt(vis, "ROI PARAMETERS", PNL_X+8, PNL_Y+16, 0.38, C_DIM)
            cv2.line(vis,(PNL_X+4,PNL_Y+22),(PNL_X+PNL_W-4,PNL_Y+22),C_BORDER,1)
            for sl in sliders:
                sl.draw(vis, accent, mx_m, my_m)

            PREV_PW, PREV_PH = 400, 140
            PREV_PX = (WIN_W - PREV_PW) // 2
            PREV_PY = (WIN_H - PREV_PH) // 2
            
            panel(vis, PREV_PX, PREV_PY,
                  PREV_PX+PREV_PW, PREV_PY+PREV_PH, 0.96)
            txt(vis, "OCR PREVIEW", PREV_PX+10, PREV_PY+18, 0.45, C_DIM)
            cv2.line(vis,(PREV_PX+6,PREV_PY+26),(PREV_PX+PREV_PW-6,PREV_PY+26), C_BORDER, 1)

            if rw > 4 and rh > 4:
                try:
                    crop = frame[ry:ry+rh, rx:rx+rw]
                    proc = preprocess_for_ocr(crop, resource) 
                    pbgr = cv2.cvtColor(proc, cv2.COLOR_GRAY2BGR)
                    
                    # Fit inside preview box, keeping aspect ratio
                    max_thumb_w = PREV_PW - 20
                    max_thumb_h = PREV_PH - 40
                    scale_p = min(max_thumb_w / max(pbgr.shape[1], 1),
                                  max_thumb_h / max(pbgr.shape[0], 1))
                    
                    nw = max(1, int(pbgr.shape[1] * scale_p))
                    nh = max(1, int(pbgr.shape[0] * scale_p))
                    thumb = cv2.resize(pbgr, (nw, nh))
                    
                    # Center the thumbnail inside the preview panel
                    py0 = PREV_PY + 30 + (max_thumb_h - nh) // 2
                    px0 = PREV_PX + 10 + (max_thumb_w - nw) // 2
                    
                    vis[py0:py0+nh, px0:px0+nw] = thumb
                except Exception:
                    pass

            BAR_H = 68
            alpha_fill(vis, 0, WIN_H-BAR_H, WIN_W, WIN_H, C_BG, 0.93)
            cv2.line(vis,(0,WIN_H-BAR_H),(WIN_W,WIN_H-BAR_H),C_BORDER_LIT,1)

            txt(vis, f"STEP {step+1}/{total}  ·  {tag}",
                14, WIN_H-BAR_H+22, 0.55, accent, bold=True)
            txt(vis, "Drag sliders  ·  SPACE to Lock  ·  B to Go Back",
                14, WIN_H-BAR_H+42, 0.38, C_DIM)

            progress_dots(vis, WIN_W//2, WIN_H-BAR_H+34, total, step, accent)

            mx_m, my_m = mouse["x"], mouse["y"]
            BTN_W, BTN_H = 160, 40
            bty = WIN_H - BAR_H + (BAR_H-BTN_H)//2

            rect_confirm = hud_button(
                vis,"CONFIRM  [SPACE]",
                WIN_W-BTN_W-12, bty, BTN_W, BTN_H, mx_m, my_m,
                C_CONFIRM_DK, C_CONFIRM, C_CONFIRM)

            rect_back = hud_button(
                vis,"BACK  [B]",
                WIN_W-BTN_W*2-24, bty, BTN_W, BTN_H, mx_m, my_m,
                C_BACK_DK, C_BACK, C_BACK)

            rect_cancel = hud_button(
                vis,"CANCEL  [ESC]",
                WIN_W-BTN_W*3-36, bty, BTN_W, BTN_H, mx_m, my_m,
                C_CANCEL_DK, C_CANCEL, C_CANCEL)

            cv2.imshow(WIN_NAME, vis)

            key   = cv2.waitKey(16) & 0xFF
            ev    = mouse["event"]
            mouse["event"] = -1
            click = (ev == cv2.EVENT_LBUTTONDOWN)

            if key == 32 or (click and point_in_rect(mx_m, my_m, rect_confirm)):
                rois[resource] = {"x":x_r,"y":y_r,"w":w_r,"h":h_r}
                
                print(f"  {resource}: x={x_r:.4f} y={y_r:.4f} w={w_r:.4f} h={h_r:.4f}")
                save_rois(rois)
                step += 1
                break
                
            elif key == ord('b') or key == ord('B') or (click and point_in_rect(mx_m, my_m, rect_back)):
                if step > 0:
                    rois[resource] = {"x":x_r,"y":y_r,"w":w_r,"h":h_r}
                    step -= 1
                    break
                    
            elif key == 27 or (click and point_in_rect(mx_m, my_m, rect_cancel)):
                print("[WARN] Calibration cancelled.")
                cv2.destroyAllWindows()
                sys.exit(0)

    cv2.destroyAllWindows()
    return rois