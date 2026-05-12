import time
import base64
import cv2
import numpy as np
import requests
import pytesseract
import datetime
import os

from src.vision.capture import click_relative_roi, zoom_camera, pan_camera, scroll_roi
from src.vision.detection import crop_roi, preprocess_for_ocr
from src.vision.ocr import OLLAMA_MODEL, OLLAMA_URL, rapid_engine


class UpgradeManager:
    CORNER_TOP_RIGHT = {"x": 0.95, "y": 0.05, "w": 0, "h": 0}
    
    WALL_VERIFY_CENTER_X = 0.520
    WALL_VERIFY_CENTER_Y = 0.790
    
    WALL_ADD_MORE = {"x": 0.500, "y": 0.800, "w": 0.0, "h": 0.0}
    UPGRADE_BUTTON_GOLD = {"x": 0.600, "y": 0.800, "w": 0.0, "h": 0.0}
    UPGRADE_BUTTON_ELIXIR = {"x": 0.650, "y": 0.800, "w": 0.0, "h": 0.0}
    
    CONFIRM_BUTTON_SINGLE = {"x": 0.700, "y": 0.850, "w": 0.0, "h": 0.0}
    CONFIRM_BUTTON_MULTI = {"x": 0.620, "y": 0.620, "w": 0.0, "h": 0.0}
    
    CLOSE_MENU = {"x": 0.1, "y": 0.5, "w": 0, "h": 0}
    
    ELIXIR_COST_THRESHOLD = 500000
    
    def __init__(self, hwnd, rois, ocr_engine_getter, bot_running_check, latest_data_getter, state_cache, log_callback, ui_update_callbacks, config_getters=None):
        self.hwnd = hwnd
        self.rois = rois
        self.get_ocr_engine = ocr_engine_getter if callable(ocr_engine_getter) else (lambda: ocr_engine_getter)
        self.bot_running_check = bot_running_check
        self.get_latest_data = latest_data_getter if callable(latest_data_getter) else (lambda: latest_data_getter)
        self.state_cache = state_cache
        self.log_callback = log_callback
        self.ui_update_callbacks = ui_update_callbacks
        self.config_getters = config_getters or {}

    def _debug_click(self, roi, capture_callback, label="click"):
        
        save_screenshots = self.config_getters.get("get_debug_screenshots", lambda: True)()
        
        if save_screenshots:
            frame = capture_callback()
            if frame is not None:
                os.makedirs("response", exist_ok=True)
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                
                h, w = frame.shape[:2]
                rw = roi.get("w", 0.0)
                rh = roi.get("h", 0.0)
                cx = int((roi["x"] + rw / 2.0) * w)
                cy = int((roi["y"] + rh / 2.0) * h)
                
                debug_img = frame.copy()
                cv2.circle(debug_img, (cx, cy), 6, (0, 0, 255), -1)
                cv2.circle(debug_img, (cx, cy), 12, (0, 255, 255), 2)
                cv2.putText(debug_img, label, (cx + 15, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                filename = f"response/debug_{label}_{ts}.png"
                cv2.imwrite(filename, debug_img)
                self.log_callback(f"[DEBUG] Saved click visualization to {filename}", "sys")
            
        click_relative_roi(self.hwnd, roi)
        
    def is_auto_wall_enabled(self):
        getter = self.config_getters.get("auto_wall_var")
        if getter:
            return bool(getter())
        return False
        
    def reset_builder_view(self, capture_callback):
        self.log_callback("[BOT] Running deselector sequence to reset view...", "sys")
        
        zoom_camera(self.hwnd, ticks=15, direction="out")
        time.sleep(0.5)
        
        self._debug_click(self.CORNER_TOP_RIGHT, capture_callback, "reset_corner_1")
        time.sleep(0.5)
        
        self._debug_click(self.rois["builders_icon"], capture_callback, "reset_open_builders")
        time.sleep(0.5)
        
        menu_x = self.rois["upgrades_menu"]["x"] + (self.rois["upgrades_menu"]["w"] / 2.0)
        menu_y = self.rois["upgrades_menu"]["y"]
        menu_h = self.rois["upgrades_menu"]["h"]
        pan_camera(self.hwnd, start_rel=(menu_x, menu_y + menu_h * 0.3), end_rel=(menu_x, menu_y + menu_h * 0.8), drag_speed=15)
        time.sleep(0.5)
        
        self._debug_click(self.CORNER_TOP_RIGHT, capture_callback, "reset_corner_2")
        time.sleep(0.5)
        
    def upgrade_walls(self, walls_to_do, capture_callback):
        if not self.bot_running_check():
            return False
        
        # Sort from cheapest to most expensive so we ALWAYS exhaust resources on cheap walls first
        def safe_cost(w):
            try: return int(w.get("cost", float('inf')))
            except: return float('inf')
        walls_to_do.sort(key=safe_cost)
        
        self.log_callback(f"[BOT] Starting Wall Upgrade Sequence for {len(walls_to_do)} wall types...", "bot")
        
        engine_type = self.get_ocr_engine().upper()
        self.log_callback(f"[BOT] Using {engine_type} engine for wall OCR...", "sys")
        
        for wall in walls_to_do:
            target_cost = wall.get("cost", 0)
            qty_available = wall.get("qty", 1)
            
            while qty_available > 0:
                if not self.bot_running_check():
                    return False
                
                latest_data = self.get_latest_data()
                curr_gold = latest_data.get("gold", 0)
                curr_elixir = latest_data.get("elixir", 0)
                
                self.log_callback(f"[DEBUG] Reading resources: Gold={curr_gold:,}, Elixir={curr_elixir:,}", "sys")
                
                can_use_elixir = target_cost >= self.ELIXIR_COST_THRESHOLD
                
                # Keep 100,000 gold in reserve to allow searching for matches
                available_gold = max(0, curr_gold - 100000)
                available_elixir = curr_elixir
                
                afford_gold = available_gold // target_cost
                afford_elixir = available_elixir // target_cost if can_use_elixir else 0
                
                if afford_gold == 0 and afford_elixir == 0:
                    self.log_callback(f"[BOT] Cannot afford more walls of cost {target_cost:,}.", "sys")
                    break
                    
                if afford_gold >= afford_elixir and afford_gold > 0:
                    use_resource = "gold"
                    qty_to_do = min(qty_available, afford_gold)
                else:
                    use_resource = "elixir"
                    qty_to_do = min(qty_available, afford_elixir)
                    
                self.log_callback(f"[BOT] Attempting to upgrade {qty_to_do}x Wall (Cost: {target_cost:,}) with {use_resource.upper()}...", "bot")
                
                self.reset_builder_view(capture_callback)
                
                self.log_callback("[BOT] Opening Builder Menu...", "sys")
                self._debug_click(self.rois["builders_icon"], capture_callback, "open_builders_menu")
                time.sleep(2.0)
                
                if hasattr(self, "ui_update_callbacks") and "set_scanning_upgrades" in self.ui_update_callbacks:
                    self.ui_update_callbacks["set_scanning_upgrades"](True)
                
                wall_found = False
                wall_coords = None
                
                for _ in range(10):
                    if not self.bot_running_check():
                        return False
                    time.sleep(0.5)
                    frame = capture_callback()
                    if frame is None:
                        return False
                    
                    roi = self.rois["upgrades_menu"]
                    crop = crop_roi(frame, roi)
                    
                    if hasattr(self, "ui_update_callbacks") and "update_upgrade_preview" in self.ui_update_callbacks:
                        self.ui_update_callbacks["update_upgrade_preview"](preprocess_for_ocr(crop, "upgrades_menu"))
                    
                    self.log_callback(f"[BOT] Scanning menu with {engine_type}...", "sys")
                    
                    h, w = crop.shape[:2]
                    
                    if engine_type == "TESSERACT":
                        # --- Full-image approach with positional word data ---
                        processed_crop = preprocess_for_ocr(crop, "upgrades_menu")
                        
                        # Save debug images
                        save_screenshots = self.config_getters.get("get_debug_screenshots", lambda: True)()
                        if save_screenshots:
                            os.makedirs("response", exist_ok=True)
                            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                            cv2.imwrite(f"response/debug_menu_raw_{ts}.png", crop)
                            cv2.imwrite(f"response/debug_menu_proc_{ts}.png", processed_crop)
                        
                        data = pytesseract.image_to_data(
                            processed_crop, config='--psm 6',
                            output_type=pytesseract.Output.DICT
                        )
                        
                        # Group words into lines by Y-proximity
                        lines_map = {}
                        for idx in range(len(data['text'])):
                            txt = data['text'][idx].strip()
                            conf = int(data['conf'][idx])
                            if not txt or conf < 1:
                                continue
                            top = data['top'][idx]
                            # Find an existing line within 20px
                            placed = False
                            for key in lines_map:
                                if abs(top - key) < 20:
                                    lines_map[key]['words'].append(txt)
                                    lines_map[key]['min_top'] = min(lines_map[key]['min_top'], top)
                                    placed = True
                                    break
                            if not placed:
                                lines_map[top] = {'words': [txt], 'min_top': top}
                        
                        # Check each detected line for wall match
                        for key in sorted(lines_map.keys()):
                            line_data = lines_map[key]
                            r_text = ' '.join(line_data['words']).lower()
                            
                            r_text_clean = r_text.replace("s", "5").replace("o", "0").replace("l", "1").replace("i", "1")
                            clean_for_cost = r_text_clean
                            for ww in ["wa11", "wa1", "vva11", "wall", "wal"]:
                                clean_for_cost = clean_for_cost.replace(ww, "")
                            c_text = clean_for_cost.replace(" ", "").replace(",", "").replace(".", "")
                            
                            has_wall = "wall" in r_text or "wal" in r_text or "wa11" in r_text_clean or "wa1" in r_text_clean
                            
                            str_cost = str(target_cost)
                            is_match = False
                            if has_wall:
                                if str_cost in c_text:
                                    is_match = True
                                else:
                                    import re
                                    text_no_qty = re.sub(r'x\s*\d+', '', clean_for_cost)
                                    digits = re.sub(r'\D', '', text_no_qty)
                                    if digits:
                                        try:
                                            read_cost = int(digits)
                                            if abs(read_cost - target_cost) / max(target_cost, 1) <= 0.25:
                                                is_match = True
                                        except:
                                            pass
                            
                            if is_match:
                                # Divide by 2 because preprocess upscales 2x
                                found_y = line_data['min_top'] / 2.0
                                rel_y = roi["y"] + (found_y / frame.shape[0])
                                rel_x = roi["x"] + (roi["w"] / 2.0)
                                wall_coords = {"x": rel_x, "y": rel_y, "w": 0.0, "h": 0.0}
                                wall_found = True
                                break
                    
                    else:
                        # --- Row-by-row approach for GLM / RAPID ---
                        num_rows = 6
                        row_h = h // num_rows
                        
                        for i in range(num_rows):
                            if not self.bot_running_check():
                                return False
                            row_img = crop[i*row_h : (i+1)*row_h, :]
                            
                            r_text = ""
                            if engine_type == "GLM":
                                try:
                                    _, r_buf = cv2.imencode('.png', row_img)
                                    r_b64 = base64.b64encode(r_buf).decode('utf-8')
                                    r_payload = {
                                        "model": OLLAMA_MODEL,
                                        "prompt": "Extract text.",
                                        "images": [r_b64],
                                        "stream": False,
                                        "options": {"temperature": 0.0}
                                    }
                                    r_res = requests.post(OLLAMA_URL, json=r_payload, timeout=10)
                                    r_text = r_res.json().get("response", "").lower()
                                except:
                                    pass
                            elif engine_type == "RAPID" and rapid_engine:
                                r_res, _ = rapid_engine(row_img)
                                if r_res:
                                    r_text = " ".join([item[1] for item in r_res]).lower()
                            
                            r_text_clean = r_text.replace("s", "5").replace("o", "0").replace("l", "1").replace("i", "1")
                            clean_for_cost = r_text_clean
                            for ww in ["wa11", "wa1", "vva11", "wall", "wal"]:
                                clean_for_cost = clean_for_cost.replace(ww, "")
                            c_text = clean_for_cost.replace(" ", "").replace(",", "").replace(".", "")
                            
                            str_cost = str(target_cost)
                            
                            is_match = False
                            if "wall" in r_text or "wal" in r_text or "wa11" in r_text_clean or "wa1" in r_text_clean:
                                if str_cost in c_text:
                                    is_match = True
                                else:
                                    import re
                                    text_no_qty = re.sub(r'x\s*\d+', '', clean_for_cost)
                                    digits = re.sub(r'\D', '', text_no_qty)
                                    if digits:
                                        try:
                                            read_cost = int(digits)
                                            if abs(read_cost - target_cost) / max(target_cost, 1) <= 0.25:
                                                is_match = True
                                        except:
                                            pass
                            
                            if is_match:
                                found_y = i * row_h + (row_h * 0.2)
                                rel_y = roi["y"] + (found_y / frame.shape[0])
                                rel_x = roi["x"] + (roi["w"] / 2.0)
                                wall_coords = {"x": rel_x, "y": rel_y, "w": 0.0, "h": 0.0}
                                wall_found = True
                                break
                            
                    if wall_found:
                        break
                    else:
                        self.log_callback(f"[BOT] Target Wall ({target_cost}) not found, scrolling...", "sys")
                        scroll_roi(self.hwnd, roi)
                        time.sleep(2.0)
                        
                if hasattr(self, "ui_update_callbacks") and "set_scanning_upgrades" in self.ui_update_callbacks:
                    self.ui_update_callbacks["set_scanning_upgrades"](False)
                        
                if not wall_found or not wall_coords:
                    self.log_callback(f"[BOT] Could not locate Wall ({target_cost}) in menu. Skipping.", "sys")
                    self._debug_click(self.CLOSE_MENU, capture_callback, "close_menu_not_found")
                    time.sleep(1.0)
                    qty_available = 0
                    break
                    
                self.log_callback("[BOT] Wall found! Clicking it...", "bot")
                self._debug_click(wall_coords, capture_callback, f"select_wall_{target_cost}")
                time.sleep(2.0)
                
                frame = capture_callback()
                wall_selected_verified = False
                if frame is not None:
                    img_h, img_w = frame.shape[:2]
                    cx = int(self.WALL_VERIFY_CENTER_X * img_w)
                    cy = int(self.WALL_VERIFY_CENTER_Y * img_h)
                    y1, y2 = max(0, cy-5), min(img_h, cy+5)
                    x1, x2 = max(0, cx-5), min(img_w, cx+5)
                    region = frame[y1:y2, x1:x2]
                    
                    # ⚡ CHANGED HERE: Lowered threshold from 240 to 210 to include #E0E0E0 (224, 224, 224)
                    white_mask = cv2.inRange(region, np.array([210, 210, 210]), np.array([255, 255, 255]))
                    if cv2.countNonZero(white_mask) > 0:
                        wall_selected_verified = True
                        
                if not wall_selected_verified:
                    self.log_callback("[BOT] Failed to confirm wall selection (No white pixel). Retrying...", "sys")
                    self._debug_click(self.CORNER_TOP_RIGHT, capture_callback, "retry_unselect")
                    time.sleep(1.0)
                    continue
                else:
                    self.log_callback("[BOT] Wall selection confirmed.", "sys")
                
                if qty_to_do > 1:
                    self.log_callback(f"[BOT] Adding {qty_to_do - 1} more walls to selection...", "sys")

                    for _ in range(qty_to_do):
                        self._debug_click(self.WALL_ADD_MORE, capture_callback, "add_wall")
                        time.sleep(0.5)
                
                self.log_callback(f"[BOT] Using {use_resource.capitalize()} for Wall Upgrade...", "sys")
                if use_resource == "elixir":
                    self._debug_click(self.UPGRADE_BUTTON_ELIXIR, capture_callback, "upgrade_elixir")
                else:
                    self._debug_click(self.UPGRADE_BUTTON_GOLD, capture_callback, "upgrade_gold")
                time.sleep(1.0)
                
                self.log_callback("[BOT] Confirming upgrade...", "sys")
                if qty_to_do > 1:
                    self._debug_click(self.CONFIRM_BUTTON_MULTI, capture_callback, "confirm_multi")
                else:
                    self._debug_click(self.CONFIRM_BUTTON_SINGLE, capture_callback, "confirm_single")
                time.sleep(1.0)
                
                self.log_callback("[BOT] Zooming out after wall upgrade...", "sys")
                zoom_camera(self.hwnd, ticks=15, direction="out")
                time.sleep(1.0)
                
                latest_data = self.get_latest_data()
                if use_resource == "gold":
                    latest_data["gold"] -= (target_cost * qty_to_do)
                    if "update_gold" in self.ui_update_callbacks:
                        self.ui_update_callbacks["update_gold"](latest_data["gold"])
                else:
                    latest_data["elixir"] -= (target_cost * qty_to_do)
                    if "update_elixir" in self.ui_update_callbacks:
                        self.ui_update_callbacks["update_elixir"](latest_data["elixir"])
                    
                qty_available -= qty_to_do
                wall["qty"] = qty_available
                
                if "upgrades_info" in self.state_cache:
                    self.state_cache["upgrades_info"]["upgrades"] =[
                        w for w in self.state_cache["upgrades_info"]["upgrades"] if w.get("qty", 1) > 0
                    ]
                    latest_data["upgrades_info"] = self.state_cache["upgrades_info"]
                    if "apply_update" in self.ui_update_callbacks:
                        ts = datetime.datetime.now().strftime("%H:%M:%S")
                        self.ui_update_callbacks["apply_update"](latest_data, ts, 0.0, "CACHE")

                self.log_callback(f"[BOT] Upgraded {qty_to_do} walls. {qty_available} left of this cost.", "bot")
                
                if "upgrades_info" in self.state_cache:
                    total_walls_left = sum(w.get("qty", 1) for w in self.state_cache["upgrades_info"]["upgrades"] if "wall" in w.get("name", "").lower())
                    if total_walls_left <= 0:
                        self.log_callback("[BOT] Reached 0 walls available to upgrade. Stopping bot.", "bot_off")
                        if "stop_bot" in self.ui_update_callbacks:
                            self.ui_update_callbacks["stop_bot"]()
                        return True
                
        self.log_callback("[BOT] Wall Upgrade sequence complete.", "bot")
        return True