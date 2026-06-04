import time
import numpy as np
import cv2
import tkinter as tk

from src.core.bot import ReloadGameException
from src.vision.capture import capture_frame, get_relative_mouse_pos, zoom_camera, pan_camera, send_esc_key, click_relative_roi
from src.vision.detection import crop_roi, preprocess_for_ocr, is_main_screen

def update_mouse_coords(ui):
    try:
        rel_x, rel_y = get_relative_mouse_pos(ui.hwnd)
        if rel_x >= 0 and rel_y >= 0 and rel_x <= 1 and rel_y <= 1:
            ui.mouse_coords_lbl.config(text=f"X: {rel_x:.3f}  Y: {rel_y:.3f}", fg="#eab308")
        else:
            ui.mouse_coords_lbl.config(text="X: ---  Y: ---", fg="#737373")
    except Exception:
        pass
    ui.root.after(100, lambda: update_mouse_coords(ui))

def anti_afk_loop(ui):
    while True:
        if getattr(ui, 'anti_afk_var', None) and ui.anti_afk_var.get() and not ui.bot_running:
            try:
                zoom_camera(ui.hwnd, ticks=5, direction="in")
                time.sleep(1.0)
                
                pan_camera(ui.hwnd, start_rel=(0.6, 0.5), end_rel=(0.4, 0.5))
                time.sleep(1.0)
                
                pan_camera(ui.hwnd, start_rel=(0.4, 0.5), end_rel=(0.6, 0.5))
                time.sleep(1.0)

                zoom_camera(ui.hwnd, ticks=5, direction="out")
                
                for _ in range(150):
                    if not ui.anti_afk_var.get() or ui.bot_running:
                        break
                    time.sleep(0.1)
            except Exception as e:
                print(f"[WARN] Anti-AFK error: {e}")
                time.sleep(2.0)
        else:
            time.sleep(1.0)

def safe_capture(ui):
    with ui.capture_lock:
        frame = capture_frame(ui.hwnd)
        
        if frame is not None and getattr(ui, "bot_running", False):
            h, w = frame.shape[:2]
            
            star_check_1_x, star_check_1_y = int(0.870 * w), int(0.445 * h)
            star_check_2_x, star_check_2_y = int(0.170 * w), int(0.540 * h)
            
            star_color_1 = np.mean(frame[max(0, star_check_1_y-2):star_check_1_y+3, 
                                         max(0, star_check_1_x-2):star_check_1_x+3])
            star_color_2 = np.mean(frame[max(0, star_check_2_y-2):star_check_2_y+3, 
                                         max(0, star_check_2_x-2):star_check_2_x+3])
            
            if star_color_1 < 10 and star_color_2 < 10:
                return frame
            
            p1_x, p1_y = int(0.442 * w), int(0.438 * h)
            p2_x, p2_y = int(0.323 * w), int(0.529 * h)
            
            color1 = frame[p1_y, p1_x].astype(np.int32)
            color2 = frame[p2_y, p2_x].astype(np.int32)
            
            target_bgr = np.array([30, 28, 25])
            if np.all(np.abs(color1 - target_bgr) <= 15) and np.all(np.abs(color2 - target_bgr) <= 15):
                ui.log_terminal("[WARN] Reload Game popup detected! Pressing ESC after 1s...", "sys")
                time.sleep(1.0)
                send_esc_key(ui.hwnd)
                time.sleep(5.0)
                
                while getattr(ui, "bot_running", False):
                    f = capture_frame(ui.hwnd)
                    if f is not None:
                        if is_main_screen(f, ui.rois["main_screen_i"]):
                            ui.log_terminal("[BOT] Main village detected after reload! Initiating restart...", "sys")
                            raise ReloadGameException("Game was reloaded. Restarting loop.")
                        
                        fh, fw = f.shape[:2]
                        
                        # Check for Match End screen (stars)
                        s1_x, s1_y = int(0.870 * fw), int(0.445 * fh)
                        s2_x, s2_y = int(0.170 * fw), int(0.540 * fh)
                        s_col1 = np.mean(f[max(0, s1_y-2):s1_y+3, max(0, s1_x-2):s1_x+3])
                        s_col2 = np.mean(f[max(0, s2_y-2):s2_y+3, max(0, s2_x-2):s2_x+3])
                        
                        if s_col1 < 10 and s_col2 < 10:
                            ui.log_terminal("[BOT] Match End Detected after reload! Clicking 'Return Home'...", "bot")
                            click_relative_roi(ui.hwnd, {"x": 0.505, "y": 0.850, "w": 0, "h": 0})
                            time.sleep(2.0)
                            continue
                            
                        # Check for Star Bonus popup
                        px, py = int(0.659 * fw), int(0.120 * fh)
                        color = f[py, px]
                        target_color = np.array([204, 255, 255])
                        if np.all(np.abs(color.astype(int) - target_color.astype(int)) <= 15):
                            ui.log_terminal("[BOT] Star Bonus popup detected after reload! Clicking Okay...", "bot")
                            click_relative_roi(ui.hwnd, {"x": 0.50, "y": 0.83, "w": 0, "h": 0})
                            time.sleep(2.0)
                            continue

                    time.sleep(1.0)
                raise ReloadGameException("Game was reloaded. Restarting loop.")
                
        return frame

def preview_loop(ui):
    window_name = "OCR LIVE PREVIEW"
    window_created = False
    while True:
        if ui.preview_enabled:
            if not window_created:
                cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
                cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
                window_created = True

            display_img = None
            if ui.is_scanning_upgrades:
                if ui.current_upgrade_preview is not None:
                    display_img = ui.current_upgrade_preview.copy()
                    if len(display_img.shape) == 2:
                        display_img = cv2.cvtColor(display_img, cv2.COLOR_GRAY2BGR)
                    if display_img.shape[0] > 700:
                        sf = 700.0 / display_img.shape[0]
                        display_img = cv2.resize(display_img, (0, 0), fx=sf, fy=sf)
            else:
                try:
                    frame = safe_capture(ui)
                except ReloadGameException:
                    frame = None
                except Exception as e:
                    print(f"[PREVIEW] Capture error: {e}")
                    frame = None

                if frame is not None:
                    on_main = is_main_screen(frame, ui.rois["main_screen_i"])
                    keys =["gold", "elixir", "dark_elixir"] if on_main \
                              else["enemy_gold", "enemy_elixir", "enemy_dark_elixir"]
                    
                    crops =[]
                    for k in keys:
                        crops.append(preprocess_for_ocr(crop_roi(frame, ui.rois[k]), k))
                    
                    if on_main:
                        crops.append(preprocess_for_ocr(
                            crop_roi(frame, ui.rois["builders_icon"]), "builders_icon"))
                    
                    max_w = max(img.shape[1] for img in crops)
                    uniform =[]
                    for img in crops:
                        if len(img.shape) == 2:
                            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                        
                        w_diff = max_w - img.shape[1]
                        if w_diff > 0:
                            left_pad = w_diff // 2
                            right_pad = w_diff - left_pad
                            img = cv2.copyMakeBorder(img, 0, 0, left_pad, right_pad,
                                                     cv2.BORDER_CONSTANT, value=[255, 255, 255])
                        
                        img = cv2.copyMakeBorder(img, 5, 5, 5, 5,
                                                 cv2.BORDER_CONSTANT, value=[255, 255, 255])
                        uniform.append(img)
                    
                    display_img = np.vstack(uniform)

            if display_img is not None:
                cv2.imshow(window_name, display_img)
            cv2.waitKey(200)

            if window_created:
                try:
                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                        ui.preview_enabled = False
                        ui.root.after(0, lambda: ui.preview_var.set(False))
                        window_created = False
                except Exception:
                    ui.preview_enabled = False
                    ui.root.after(0, lambda: ui.preview_var.set(False))
                    window_created = False
        else:
            if window_created:
                cv2.destroyWindow(window_name)
                window_created = False
            time.sleep(0.2)
