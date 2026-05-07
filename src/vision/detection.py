import cv2
import numpy as np

def abs_roi(frame: np.ndarray, rel: dict) -> tuple[int, int, int, int]:
    h, w = frame.shape[:2]
    return (int(rel["x"]*w), int(rel["y"]*h),
            int(rel["w"]*w), int(rel["h"]*h))

def crop_roi(frame: np.ndarray, rel: dict) -> np.ndarray:
    x, y, rw, rh = abs_roi(frame, rel)
    return frame[y:y+rh, x:x+rw]

def preprocess_for_ocr(img, resource_name):
    if img is None or img.size == 0:
        return img

    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)

    tol = 30 

    if resource_name == "enemy_gold":
        lower1 = np.array([max(0, 204-tol), max(0, 251-tol), max(0, 255-tol)])
        upper1 = np.array([min(255, 204+tol), min(255, 251+tol), min(255, 255+tol)])
        lower2 = np.array([max(0, 179-tol), max(0, 220-tol), max(0, 224-tol)])
        upper2 = np.array([min(255, 179+tol), min(255, 220+tol), min(255, 224+tol)])
        
        mask1 = cv2.inRange(img, lower1, upper1)
        mask2 = cv2.inRange(img, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)

    elif resource_name == "enemy_elixir":
        lower1 = np.array([max(0, 253-tol), max(0, 232-tol), max(0, 255-tol)])
        upper1 = np.array([min(255, 253+tol), min(255, 232+tol), min(255, 255+tol)])
        lower2 = np.array([max(0, 222-tol), max(0, 204-tol), max(0, 224-tol)])
        upper2 = np.array([min(255, 222+tol), min(255, 204+tol), min(255, 224+tol)])
        
        mask1 = cv2.inRange(img, lower1, upper1)
        mask2 = cv2.inRange(img, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)

    elif resource_name == "enemy_dark_elixir":
        lower = np.array([max(0, 213-tol), max(0, 213-tol), max(0, 213-tol)])
        upper = np.array([min(255, 213+tol), min(255, 213+tol), min(255, 213+tol)])
        mask = cv2.inRange(img, lower, upper)

    elif resource_name == "upgrades_menu":
        lower_white = np.array([170, 170, 170])
        upper_white = np.array([255, 255, 255])
        mask_white = cv2.inRange(img, lower_white, upper_white)
        
        red_tol = 45
        lower_red = np.array([max(0, 112-red_tol), max(0, 119-red_tol), max(0, 224-red_tol)])
        upper_red = np.array([min(255, 112+red_tol), min(255, 119+red_tol), min(255, 255)])
        mask_red = cv2.inRange(img, lower_red, upper_red)
        
        lower_green = np.array([0, 150, 0])
        upper_green = np.array([120, 255, 120])
        mask_green = cv2.inRange(img, lower_green, upper_green)
        
        mask = cv2.bitwise_or(mask_white, mask_red)
        mask = cv2.bitwise_or(mask, mask_green)
        
        kernel = np.ones((2,2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        processed = cv2.bitwise_not(mask)
        return processed

    else:
        target_tol = 23
        lower1 = np.array([max(0, 224-target_tol), max(0, 224-target_tol), max(0, 224-target_tol)])
        upper1 = np.array([min(255, 224+target_tol), min(255, 224+target_tol), min(255, 224+target_tol)])
        mask1 = cv2.inRange(img, lower1, upper1)
        
        white_tol = 10
        lower2 = np.array([max(0, 255-white_tol), max(0, 255-white_tol), max(0, 255-white_tol)])
        upper2 = np.array([255, 255, 255])
        mask2 = cv2.inRange(img, lower2, upper2)
        
        mask = cv2.bitwise_or(mask1, mask2)

    kernel = np.ones((2,2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    processed = cv2.bitwise_not(mask)
    
    return processed

def draw_button(img: np.ndarray, label: str, x: int, y: int,
                w: int, h: int, color: tuple, mx: int, my: int) -> tuple:
    hover = (x <= mx <= x+w and y <= my <= y+h)
    bg    = tuple(min(c+40, 255) for c in color) if hover else color
    cv2.rectangle(img, (x, y), (x+w, y+h), bg, -1)
    cv2.rectangle(img, (x, y), (x+w, y+h), (255,255,255), 2)
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(label, font, 0.65, 2)
    cv2.putText(img, label, (x+(w-tw)//2, y+(h+th)//2), font, 0.65, (255,255,255), 2)
    return (x, y, x+w, y+h)

def point_in_rect(px: int, py: int, rect: tuple) -> bool:
    return rect[0] <= px <= rect[2] and rect[1] <= py <= rect[3]

def is_main_screen(frame: np.ndarray, i_roi: dict) -> bool:
    roi_img = crop_roi(frame, i_roi)
    proc = preprocess_for_ocr(roi_img, "main_screen_i")
    total_pixels = proc.shape[0] * proc.shape[1]
    white_pixels = cv2.countNonZero(proc)
    black_pixels = total_pixels - white_pixels
    return black_pixels > 20

def check_match_found(frame: np.ndarray, next_button_roi: dict) -> bool:
    if frame is None or frame.size == 0:
        return False
        
    roi_img = crop_roi(frame, next_button_roi)
    if roi_img.size == 0:
        return False
        
    tol = 30
    lower = np.array([max(0, 47-tol), max(0, 168-tol), max(0, 221-tol)])
    upper = np.array([min(255, 47+tol), min(255, 168+tol), min(255, 221+tol)])
    
    mask = cv2.inRange(roi_img, lower, upper)
    white_pixels = cv2.countNonZero(mask)
    
    return white_pixels > 50