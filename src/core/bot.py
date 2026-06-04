# --- START OF FILE bot.py ---


import time
import threading
import datetime
import json
import cv2
import numpy as np

from src.vision.capture import capture_frame, click_relative_roi, scroll_roi, zoom_camera, pan_camera, send_esc_key
from src.vision.detection import crop_roi, is_main_screen, check_match_found
from src.core.recovery import attempt_recovery
from src.utils.config import STATIC_ATTACK_FILE


class ReloadGameException(Exception):
    pass


class BotOrchestrator:
    def __init__(self, hwnd, rois, state_manager, attack_manager, upgrade_manager, builder_scanner, ui_callbacks):
        self.hwnd = hwnd
        self.rois = rois
        self.state_manager = state_manager
        self.attack_manager = attack_manager
        self.upgrade_manager = upgrade_manager
        self.builder_scanner = builder_scanner
        self.ui_callbacks = ui_callbacks
        
        self.bot_running = False
        self.bot_thread = None
        self.capture_lock = threading.Lock()
        
    def start_bot(self):
        if self.bot_running:
            return False
        self.bot_running = True
        self.bot_thread = threading.Thread(target=self._pipeline_worker, daemon=True)
        self.bot_thread.start()
        return True
        
    def stop_bot(self):
        self.bot_running = False
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=2.0)
        return True
        
    def is_running(self):
        return self.bot_running
        
    def _safe_capture(self):
        with self.capture_lock:
            frame = capture_frame(self.hwnd)
            
            if frame is not None and self.bot_running:
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
                    self.ui_callbacks["log_terminal"]("[WARN] Reload Game popup detected! Pressing ESC...", "sys")
                    time.sleep(1.0)
                    send_esc_key(self.hwnd)
                    time.sleep(5.0)
                    
                    while self.bot_running:
                        f = capture_frame(self.hwnd)
                        if f is not None:
                            if is_main_screen(f, self.rois["main_screen_i"]):
                                self.ui_callbacks["log_terminal"]("[BOT] Main village detected after reload! Initiating restart...", "sys")
                                raise ReloadGameException("Game was reloaded. Restarting loop.")
                            
                            fh, fw = f.shape[:2]
                            
                            # Check for Match End screen (stars)
                            s1_x, s1_y = int(0.870 * fw), int(0.445 * fh)
                            s2_x, s2_y = int(0.170 * fw), int(0.540 * fh)
                            s_col1 = np.mean(f[max(0, s1_y-2):s1_y+3, max(0, s1_x-2):s1_x+3])
                            s_col2 = np.mean(f[max(0, s2_y-2):s2_y+3, max(0, s2_x-2):s2_x+3])
                            
                            if s_col1 < 10 and s_col2 < 10:
                                self.ui_callbacks["log_terminal"]("[BOT] Match End Detected after reload! Clicking 'Return Home'...", "bot")
                                click_relative_roi(self.hwnd, {"x": 0.505, "y": 0.850, "w": 0, "h": 0})
                                time.sleep(2.0)
                                continue
                                
                            # Check for Star Bonus popup
                            px, py = int(0.659 * fw), int(0.120 * fh)
                            color = f[py, px]
                            target_color = np.array([204, 255, 255])
                            if np.all(np.abs(color.astype(int) - target_color.astype(int)) <= 15):
                                self.ui_callbacks["log_terminal"]("[BOT] Star Bonus popup detected after reload! Clicking Okay...", "bot")
                                click_relative_roi(self.hwnd, {"x": 0.50, "y": 0.83, "w": 0, "h": 0})
                                time.sleep(2.0)
                                continue

                        time.sleep(1.0)
                    raise ReloadGameException("Game was reloaded. Restarting loop.")
            return frame
            
    def _monitor_battle_end(self):
        self.ui_callbacks["log_terminal"]("[BOT] Watching battle for end conditions...", "sys")
        
        star_roi_1 = {"x": 0.870, "y": 0.445}
        star_roi_2 = {"x": 0.170, "y": 0.540}
        return_home_btn = {"x": 0.505, "y": 0.850, "w": 0, "h": 0}
        
        def is_pitch_black(frame, roi):
            img_h, img_w = frame.shape[:2]
            x1, y1 = int(roi["x"] * img_w), int(roi["y"] * img_h)
            
            x2 = min(x1 + 5, img_w)
            y2 = min(y1 + 5, img_h)
            
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                return False
            
            avg_color = np.mean(crop, axis=(0, 1))
            return np.all(avg_color < 20)

        timeout = time.time() + 180
        
        while self.bot_running and time.time() < timeout:
            frame = self._safe_capture()
            if frame is not None:
                if is_pitch_black(frame, star_roi_1) and is_pitch_black(frame, star_roi_2):
                    self.ui_callbacks["log_terminal"]("[BOT] Match End Detected (Victory Stars found).", "bot")
                    time.sleep(3)
                    
                    self.ui_callbacks["log_terminal"]("[BOT] Clicking 'Return Home'...", "bot")
                    click_relative_roi(self.hwnd, return_home_btn)
                    
                    self.ui_callbacks["log_terminal"]("[BOT] Waiting for Home Village to load...", "sys")
                    load_timeout = time.time() + 30.0
                    while self.bot_running and time.time() < load_timeout:
                        time.sleep(1.0)
                        check_frame = self._safe_capture()
                        if check_frame is not None:
                            # Check for Star Bonus popup (#FFFFCC -> BGR: 204, 255, 255) at x=0.659, y=0.120
                            h, w = check_frame.shape[:2]
                            px, py = int(0.659 * w), int(0.120 * h)
                            color = check_frame[py, px]
                            target_color = np.array([204, 255, 255])
                            
                            if np.all(np.abs(color.astype(int) - target_color.astype(int)) <= 15):
                                self.ui_callbacks["log_terminal"]("[BOT] Star Bonus popup detected! Clicking Okay...", "bot")
                                click_relative_roi(self.hwnd, {"x": 0.50, "y": 0.83, "w": 0, "h": 0})
                                time.sleep(2.0)
                                continue

                            if is_main_screen(check_frame, self.rois["main_screen_i"]):
                                self.ui_callbacks["log_terminal"]("[BOT] Main village detected!", "bot")
                                return True
                            
                    self.ui_callbacks["log_terminal"]("[WARN] Timed out waiting for Home Village to load.", "sys")
                    return False
            time.sleep(1.0)
            
        if self.bot_running:
            self.ui_callbacks["log_terminal"]("[BOT] Battle monitoring timed out or ended.", "sys")
        return False
        
    def _pipeline_worker(self):
        attack_count = 0
        consecutive_failures = 0
        while self.bot_running:
            try:
                self.ui_callbacks["log_terminal"]("[BOT] Step 1: Retrieving Home Resources...", "bot")
                self.state_manager.scan_home_resources()
                
                if not self.bot_running:
                    break
                
                already_in_battle = False
                check_frame = self._safe_capture()
                if check_frame is not None and not is_main_screen(check_frame, self.rois['main_screen_i']):
                    result = attempt_recovery(
                        self.hwnd, self.rois,
                        self._safe_capture,
                        self.ui_callbacks['log_terminal']
                    )
                    
                    if result == "battle":
                        already_in_battle = True
                    elif result == "failed":
                        consecutive_failures += 1
                        if consecutive_failures >= 2:
                            self.ui_callbacks['log_terminal']('[WARN] Recovery failed 2 times. Sending ESC key...', 'sys')
                            send_esc_key(self.hwnd)
                            consecutive_failures = 0
                        time.sleep(2.0)
                        continue
                            
                consecutive_failures = 0

                if not already_in_battle:
                    time.sleep(1.0)

                    current_time = time.time()
                    last_scan = self.state_manager.get_last_upgrades_scan_time()

                    if self.upgrade_manager.is_auto_wall_enabled():
                        if current_time - last_scan > 1800 or not self.state_manager.has_upgrades_cache():
                            self.ui_callbacks["log_terminal"]("[BOT] Step 2: Upgrades info older than 30m. Updating...", "bot")
    
                            self.ui_callbacks["scan_upgrades"](is_bot=True)
    
                            if self.bot_running:
                                new_upg = self.state_manager.get_latest_upgrades()
                                if new_upg.get("total_items_found", 0) > 0:
                                    self.state_manager.update_upgrades_cache(new_upg)
                                    self.ui_callbacks["log_terminal"]("[BOT] Upgrades cache updated successfully.", "bot")
                                else:
                                    self.ui_callbacks["log_terminal"]("[WARN] Upgrades scan found 0 items! Keeping previous cache to be safe.", "sys")
                                    self.state_manager.restore_upgrades_from_cache()
                        else:
                            self.ui_callbacks["log_terminal"]("[BOT] Step 2: Upgrades info is recent (< 30m). Loading from cache.", "bot")
                            self.state_manager.load_upgrades_from_cache()
                            self.ui_callbacks["trigger_cache_update"]()
                    else:
                        self.ui_callbacks["log_terminal"]("[BOT] Step 2: Auto-Walls DISABLED. Skipping Upgrades scan.", "bot")

                    if not self.bot_running:
                        break

                    self.ui_callbacks["log_terminal"]("[BOT] Step 3: Entering Attack Phase...", "bot")

                    targets_info = self.attack_manager.get_active_targets()
                    if targets_info:
                        self.ui_callbacks["log_terminal"](f"[BOT] Minimum Loot: [ {targets_info} ]", "bot")

                    self.ui_callbacks["log_terminal"]("[BOT] Navigating to Multiplayer Search...", "bot")

                    if not self.bot_running:
                        break

                    click_relative_roi(self.hwnd, {"x": 0.06, "y": 0.88, "w": 0.08, "h": 0.08})
                    time.sleep(1.0)
                    if not self.bot_running:
                        break

                    click_relative_roi(self.hwnd, {"x": 0.14, "y": 0.70, "w": 0.15, "h": 0.06})
                    time.sleep(1.0)
                    if not self.bot_running:
                        break

                    if self.attack_manager.is_auto_reinforce_enabled():
                        self.ui_callbacks["log_terminal"]("[BOT] Auto-Reinforce ENABLED. Buying with medals...", "bot")
                        time.sleep(0.3)
                        click_relative_roi(self.hwnd, {"x": 0.802, "y": 0.774, "w": 0.0, "h": 0.0})
                        time.sleep(0.3)
                        click_relative_roi(self.hwnd, {"x": 0.675, "y": 0.666, "w": 0.00, "h": 0.0})
                        time.sleep(0.3)
                        click_relative_roi(self.hwnd, {"x": 0.850, "y": 0.850, "w": 0.0, "h": 0.0})
                    else:
                        self.ui_callbacks["log_terminal"]("[BOT] Auto-Reinforce DISABLED. Only attacking...", "bot")
                        click_relative_roi(self.hwnd, {"x": 0.85, "y": 0.85, "w": 0.0, "h": 0.0})

                    time.sleep(2.0)

                    self.ui_callbacks["log_terminal"]("[BOT] Searching for match...", "bot")
                    next_btn_roi = {"x": 0.870, "y": 0.743, "w": 0.10, "h": 0.06}
                    restart_cycle = False
                    search_start_time = time.time()

                    while self.bot_running:
                        if time.time() - search_start_time > 60.0:
                            self.ui_callbacks["log_terminal"]("[WARN] Search timed out (60s). Clicking return home...", "sys")
                            click_relative_roi(self.hwnd, {"x": 0.058, "y": 0.892, "w": 0.0, "h": 0.0})
                            time.sleep(2.0)
                            restart_cycle = True
                            break

                        frame = self._safe_capture()

                        if frame is not None and is_main_screen(frame, self.rois["main_screen_i"]):
                            self.ui_callbacks["log_terminal"]("[WARN] Main screen detected during search! Restarting cycle...", "bot_off")
                            restart_cycle = True
                            break

                        if frame is not None and check_match_found(frame, next_btn_roi):
                            self.ui_callbacks["log_terminal"]("[BOT] Match Found! Validating criteria...", "bot")

                            time.sleep(1.5)

                            enemy_loot = self.state_manager.scan_enemy_loot()

                            if not self.bot_running:
                                break

                            enemy_gold = enemy_loot.get("gold", 0)
                            enemy_elx = enemy_loot.get("elixir", 0)
                            enemy_dark = enemy_loot.get("dark_elixir", 0)

                            try:
                                enemy_gold = int(enemy_gold)
                            except:
                                enemy_gold = 0
                            try:
                                enemy_elx = int(enemy_elx)
                            except:
                                enemy_elx = 0
                            try:
                                enemy_dark = int(enemy_dark)
                            except:
                                enemy_dark = 0

                            if self.attack_manager.validate_loot(enemy_gold, enemy_elx, enemy_dark):
                                self.ui_callbacks["log_terminal"](f"[BOT] Loot criteria MET![G:{enemy_gold} E:{enemy_elx} D:{enemy_dark}]", "bot")
                                self.ui_callbacks["log_terminal"]("[BOT] Executing zoom sequence (out -> in -> out)...", "bot")
                                zoom_camera(self.hwnd, ticks=15, direction="out")
                                time.sleep(1.0)
                                zoom_camera(self.hwnd, ticks=15, direction="in")
                                time.sleep(1.0)
                                zoom_camera(self.hwnd, ticks=15, direction="out")
                                time.sleep(1.0)
                                break
                            else:
                                self.ui_callbacks["log_terminal"](f"[BOT] Loot insufficient[G:{enemy_gold} E:{enemy_elx} D:{enemy_dark}]. Clicking Next...", "bot")
                                click_relative_roi(self.hwnd, next_btn_roi)
                                time.sleep(3.5)
                                search_start_time = time.time()
                        else:
                            time.sleep(0.5)

                    if restart_cycle:
                        continue

                if self.bot_running:
                    self.ui_callbacks["log_terminal"]("[BOT] System Ready. Awaiting Battle Loop deployment logic implementation.", "sys")

                    ai_mode = self.attack_manager.get_ai_mode()
                    if ai_mode == "DYNAMIC AI":
                        self.ui_callbacks["log_terminal"]("[AI] Dynamic AI enabled. Taking screenshot...", "sys")
                        time.sleep(0.5)
                        frame = self._safe_capture()
                        if frame is not None:
                            ai_data = self.attack_manager.detect_and_plan_attack(frame)
                            if not ai_data:
                                ai_data = {}
                            self.attack_manager.execute_deployment_plan(ai_data, False)
                        else:
                            self.ui_callbacks["log_terminal"]("[ERROR] Failed to capture frame for DYNAMIC AI. Executing fallback...", "sys")
                            self.attack_manager.execute_deployment_plan({}, False)
                            
                    elif ai_mode == "STATIC":
                        self.ui_callbacks["log_terminal"]("[AI] Static AI Mode. Loading config/static_attack.json...", "sys")
                        ai_data = {}
                        try:
                            with open(STATIC_ATTACK_FILE, "r") as f:
                                ai_data = json.load(f)
                        except Exception as e:
                            self.ui_callbacks["log_terminal"](f"[WARN] Failed to load/parse config/static_attack.json: {e}. Defaulting to fallback.", "sys")
                            
                        # Automatically detect coordinates using vision
                        self.ui_callbacks["log_terminal"]("[BOT] Automatically mapping deployment bar...", "bot")
                        frame = self._safe_capture()
                        if frame is not None:
                            detected_data = self.attack_manager.detect_and_plan_attack(frame)
                            if detected_data and "available_troops" in detected_data:
                                detected_troops = detected_data["available_troops"]
                                
                                # Map detected coordinates to our static troops
                                for category in ["available_troops", "available_spells", "available_heros"]:
                                    for static_troop in ai_data.get(category, []):
                                        t_name = static_troop.get("name", "").lower()
                                        for dt in detected_troops:
                                            if dt.get("name", "").lower() == t_name:
                                                static_troop["xmin"] = dt.get("xmin")
                                                static_troop["ymin"] = dt.get("ymin")
                                                static_troop["xmax"] = dt.get("xmax")
                                                static_troop["ymax"] = dt.get("ymax")
                                                # Remove pos/x/y so it strictly uses the detected bounding box
                                                static_troop.pop("pos", None)
                                                static_troop.pop("x", None)
                                                static_troop.pop("y", None)
                                                break
                        
                        self.attack_manager.execute_deployment_plan(ai_data, False)
                            
                    self._monitor_battle_end()
                    
                    if not self.bot_running:
                        break

                    attack_count += 1

                    # Auto-Donation check BEFORE walls
                    if self.bot_running and self.attack_manager.is_clan_donate_enabled():
                        self.ui_callbacks["log_terminal"]("[BOT] Checking for donation requests...", "bot")
                        from src.core.donation import run_donation_cycle
                        save_ss = self.attack_manager.config_getters.get("get_debug_screenshots", lambda: True)()
                        run_donation_cycle(
                            self.hwnd,
                            self._safe_capture,
                            self.ui_callbacks["log_terminal"],
                            save_screenshots=save_ss
                        )

                    if self.bot_running and self.upgrade_manager.is_auto_wall_enabled():
                        wall_freq = self.ui_callbacks.get("get_wall_check_freq", lambda: 1)()
                        if attack_count % wall_freq == 0:
                            self.ui_callbacks["log_terminal"](f"[BOT] Post-Match ({attack_count}/{wall_freq}): Evaluating Wall Upgrades...", "bot")
                            
                            self.state_manager.scan_home_resources()
                            
                            walls_to_do = self.state_manager.get_wall_upgrades()
                            
                            if walls_to_do:
                                self.upgrade_manager.upgrade_walls(walls_to_do, self._safe_capture)
                            else:
                                self.ui_callbacks["log_terminal"]("[BOT] No walls found in Upgrades cache. Skipping.", "sys")
                        else:
                            self.ui_callbacks["log_terminal"](f"[BOT] Wall check skipped ({attack_count}/{wall_freq}). Next check in {wall_freq - (attack_count % wall_freq)} attacks.", "sys")
                    else:
                        self.ui_callbacks["log_terminal"]("[BOT] Auto Wall Upgrade is disabled. Skipping.", "sys")
                        
                    self.ui_callbacks["log_terminal"]("[BOT] Ready for next match cycle.", "bot")

            except ReloadGameException as e:
                self.ui_callbacks["log_terminal"](f"[WARN] Sequence interrupted: {e}", "sys")
                time.sleep(2.0)
                continue
            except Exception as e:
                self.ui_callbacks["log_terminal"](f"[ERROR] Pipeline error: {e}", "bot_off")
                time.sleep(2.0)

            continue

        self.ui_callbacks["reset_ui"]()