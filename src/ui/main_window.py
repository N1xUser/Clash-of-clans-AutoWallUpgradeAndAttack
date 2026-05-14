import time
import tkinter as tk
import webbrowser
from tkinter import scrolledtext
import threading
import datetime
import json
import cv2
import numpy as np

from src.utils.config import STATUS_FILE
from src.vision.capture import capture_frame, click_relative_roi, focus_sea_background, scroll_roi, zoom_camera, pan_camera, get_relative_mouse_pos
from src.vision.detection import crop_roi, preprocess_for_ocr, is_main_screen, check_match_found
from src.vision.ocr import (
    extract_all_tesseract, extract_all_glm, extract_all_rapid,
    extract_upgrades_tesseract, extract_upgrades_glm, extract_upgrades_rapid,
    extract_builders_tesseract, extract_builders_glm, extract_builders_rapid
)

from src.ui.widgets import (
    BG_DEEP, BG_PANEL, BG_CARD, BG_CARD2, BORDER, BORDER_BRIGHT,
    ACCENT_GOLD, ACCENT_ELX, ACCENT_DARK, ACCENT_UPG, ACCENT_RED,
    FG_PRIMARY, FG_SECONDARY, FG_DIM, FG_GREEN,
    WINDOW_W, WINDOW_H, MIN_W, MIN_H,
    make_btn, PulseDot, Badge, ScrollableFrame, StatBadge
)

from src.core.bot import BotOrchestrator, ReloadGameException
from src.core.attack import AttackManager
from src.core.upgrade import UpgradeManager
from src.core.builder import BuilderScanner
from src.core.state_manager import BotState
from src.core.coordinates import AttackCoordinates, UpgradeCoordinates, MenuCoordinates


class AutoWallsUI:
    def __init__(self, root, hwnd, rois):
        self.root = root
        self.hwnd = hwnd
        self.rois = rois

        self.root.title("AutoWalls · Engine by N1xUser")
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.configure(bg=BG_DEEP)
        self.root.resizable(True, True)
        self.root.minsize(MIN_W, MIN_H)

        self.bot_running = False
        self.latest_data = {
            "gold": 0, "elixir": 0, "dark_elixir": 0,
            "enemy_gold": 0, "enemy_elixir": 0, "enemy_dark_elixir": 0,
            "builders": "?/?",
            "upgrades_info": {"status": "Pending Scan..."},
        }
        self.capture_lock = threading.Lock()
        self.preview_enabled = False
        self.is_scanning_upgrades = False
        self.current_upgrade_preview = None

        self.state_cache = {}
        self.config_widgets =[]
        
        ai_config = {
            "api_key": "",
            "model": "gemini-2.0-flash-exp"
        }
        
        config_getters = {
            "get_target_info": self._get_target_info_string,
            "get_auto_donate": lambda: self.auto_donate_var.get() if hasattr(self, 'auto_donate_var') else False,
            "validate_loot": self._validate_loot,
            "get_ai_mode": lambda: self.ai_mode_var.get() if hasattr(self, 'ai_mode_var') else "none",
            "auto_wall_var": lambda: self.auto_wall_var.get() if hasattr(self, 'auto_wall_var') else False,
            "get_debug_screenshots": lambda: self.debug_ss_var.get() if hasattr(self, 'debug_ss_var') else True,
        }
        
        self.attack_manager = AttackManager(
            hwnd, 
            rois, 
            ai_config,
            log_callback=self.log_terminal,
            capture_callback=self._safe_capture,
            bot_running_callback=lambda: self.bot_running,
            config_getters=config_getters
        )
        
        self.builder_scanner = BuilderScanner(hwnd, rois)
        
        # >> ADDED MISSING CALLBACKS
        ui_callbacks = {
            "log_terminal": self.log_terminal,
            "log_rich": self.log_rich,
            "apply_update": self.apply_update,
            "reset_buttons": self.reset_buttons,
            "safe_capture": self._safe_capture,
            "get_bot_running": lambda: self.bot_running,
            "set_bot_running": self._set_bot_running,
            "reset_ui": self.reset_buttons,
            "trigger_cache_update": lambda: None,
            "run_ocr_once": self.run_ocr_once,
            "scan_upgrades": lambda is_bot=False: self.run_detect_builders(self.engine_upg_var.get(), is_bot=is_bot),
            "refresh_upgrades_ui": self._refresh_upgrades_display,
            "set_scanning_upgrades": lambda val: setattr(self, "is_scanning_upgrades", val),
            "update_upgrade_preview": lambda proc: setattr(self, "current_upgrade_preview", proc),
            "update_gold": lambda val: self.card_gold.set_value(val) if hasattr(self, 'card_gold') else None,
            "update_elixir": lambda val: self.card_elixir.set_value(val) if hasattr(self, 'card_elixir') else None,
            "stop_bot": lambda: self.root.after(0, self.on_start_bot) if self.bot_running else None,
            "get_wall_check_freq": lambda: self.wall_check_freq_var.get() if hasattr(self, 'wall_check_freq_var') else 1,
        }
        
        self.upgrade_manager = UpgradeManager(
            hwnd,
            rois,
            ocr_engine_getter=lambda: self.engine_wall_var.get() if hasattr(self, 'engine_wall_var') else "RAPID",
            bot_running_check=lambda: self.bot_running,
            latest_data_getter=lambda: self.latest_data,
            state_cache=self.state_cache,
            log_callback=self.log_terminal,
            ui_update_callbacks=ui_callbacks,
            config_getters=config_getters
        )
        
        class SimpleStateManager:
            def __init__(self, ui):
                self.ui = ui
            
            def get_state(self):
                return self.ui.latest_data
            
            def deduct_gold(self, amount):
                self.ui.latest_data["gold"] -= amount
                
            def deduct_elixir(self, amount):
                self.ui.latest_data["elixir"] -= amount
                
            def get_gold(self):
                return self.ui.latest_data.get("gold", 0)
                
            def get_elixir(self):
                return self.ui.latest_data.get("elixir", 0)
                
            def remove_zero_qty_walls(self):
                pass
                
            def count_remaining_walls(self):
                upg_info = self.ui.latest_data.get("upgrades_info", {})
                walls = [u for u in upg_info.get("upgrades", []) if "wall" in u.get("name", "").lower()]
                return sum(w.get("qty", 0) for w in walls)
                
            def scan_home_resources(self):
                import time
                engine = self.ui.engine_home_var.get().lower()
                
                self.ui.root.after(0, self.ui.log_terminal, f"  - Using {engine.upper()} engine for home scan...", "sys")
                
                frame = self.ui._safe_capture()
                if frame is None:
                    self.ui.root.after(0, self.ui.log_terminal, "[ERROR] Failed to capture frame for home scan.", "bot_off")
                    return
                
                from src.vision.detection import crop_roi, preprocess_for_ocr, is_main_screen
                from src.vision.ocr import extract_builders_tesseract, extract_builders_glm, extract_builders_rapid
                from src.vision.ocr import extract_all_tesseract, extract_all_glm, extract_all_rapid
                
                if not is_main_screen(frame, self.ui.rois["main_screen_i"]):
                    self.ui.root.after(0, self.ui.log_terminal, "[ERROR] Not on home screen. Cannot scan resources.", "bot_off")
                    return
                
                self.ui.root.after(0, self.ui.log_terminal, "  - Home Screen detected. Waiting for UI to stabilize...", "sys")
                
                # Poll for village stability instead of fixed sleep
                stable_timeout = time.time() + 10.0
                while time.time() < stable_timeout:
                    time.sleep(0.5)
                    f2 = self.ui._safe_capture()
                    if f2 is not None and is_main_screen(f2, self.ui.rois["main_screen_i"]):
                        self.ui.root.after(0, self.ui.log_terminal, "  - Village UI stable.", "sys")
                        break
                
                frame = self.ui._safe_capture()
                if frame is None:
                    self.ui.root.after(0, self.ui.log_terminal, "[ERROR] Failed to capture frame after wait.", "bot_off")
                    return
                
                raw = self.ui.latest_data.copy()
                
                builders_proc = preprocess_for_ocr(crop_roi(frame, self.ui.rois["builders_icon"]), "builders_icon")
                if engine == "tesseract":
                    raw["builders"] = extract_builders_tesseract(builders_proc)
                elif engine == "glm":
                    raw["builders"] = extract_builders_glm(builders_proc)
                elif engine == "rapid":
                    raw["builders"] = extract_builders_rapid(builders_proc)
                else:
                    raw["builders"] = extract_builders_rapid(builders_proc)
                
                scan_keys = ["gold", "elixir", "dark_elixir"]
                crops =[preprocess_for_ocr(crop_roi(frame, self.ui.rois[k]), k) for k in scan_keys]
                
                if engine == "tesseract":
                    res = extract_all_tesseract(crops)
                    for i, k in enumerate(scan_keys):
                        raw[k] = res[i] if i < len(res) else 0
                elif engine == "glm":
                    res = extract_all_glm(crops)
                    for i, k in enumerate(scan_keys):
                        raw[k] = res[i] if i < len(res) else 0
                elif engine == "rapid":
                    res = extract_all_rapid(crops)
                    for i, k in enumerate(scan_keys):
                        raw[k] = res[i] if i < len(res) else 0
                else:
                    res = extract_all_rapid(crops)
                    for i, k in enumerate(scan_keys):
                        raw[k] = res[i] if i < len(res) else 0
                
                self.ui.latest_data = raw.copy()
                
                import datetime
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self.ui.root.after(0, self.ui.log_terminal, f"  - Scanned: G={raw['gold']:,} E={raw['elixir']:,} D={raw['dark_elixir']:,}", "gold")
                self.ui.root.after(0, self.ui.apply_update, raw, ts, 0.0, engine)
            
            def get_last_upgrades_scan_time(self):
                return self.ui.state_cache.get("last_upgrade_scan", 0)
                
            def has_upgrades_cache(self):
                return "upgrades_info" in self.ui.state_cache
                
            def get_latest_upgrades(self):
                return self.ui.latest_data.get("upgrades_info", {})
                
            def update_upgrades_cache(self, data):
                self.ui.state_cache["upgrades_info"] = data
                
            def restore_upgrades_from_cache(self):
                if "upgrades_info" in self.ui.state_cache:
                    self.ui.latest_data["upgrades_info"] = self.ui.state_cache["upgrades_info"]
                    
            def load_upgrades_from_cache(self):
                self.restore_upgrades_from_cache()
                
            def scan_enemy_loot(self):
                engine = self.ui.engine_enemy_var.get().lower()
                frame = self.ui._safe_capture()
                if frame is None:
                    return {
                        "gold": 0,
                        "elixir": 0,
                        "dark_elixir": 0
                    }
                
                from src.vision.detection import crop_roi, preprocess_for_ocr
                from src.vision.ocr import extract_all_tesseract, extract_all_glm, extract_all_rapid
                
                scan_keys =["enemy_gold", "enemy_elixir", "enemy_dark_elixir"]
                crops =[preprocess_for_ocr(crop_roi(frame, self.ui.rois[k]), k) for k in scan_keys]
                
                if engine == "tesseract":
                    res = extract_all_tesseract(crops)
                    for i, k in enumerate(scan_keys):
                        self.ui.latest_data[k] = res[i] if i < len(res) else 0
                elif engine == "glm":
                    res = extract_all_glm(crops)
                    for i, k in enumerate(scan_keys):
                        self.ui.latest_data[k] = res[i] if i < len(res) else 0
                elif engine == "rapid":
                    res = extract_all_rapid(crops)
                    for i, k in enumerate(scan_keys):
                        self.ui.latest_data[k] = res[i] if i < len(res) else 0
                
                import datetime
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self.ui.root.after(0, self.ui.apply_update, self.ui.latest_data.copy(), ts, 0.0, engine)
                
                return {
                    "gold": self.ui.latest_data.get("enemy_gold", 0),
                    "elixir": self.ui.latest_data.get("enemy_elixir", 0),
                    "dark_elixir": self.ui.latest_data.get("enemy_dark_elixir", 0)
                }
                
            def get_wall_upgrades(self):
                upg_info = self.ui.latest_data.get("upgrades_info", {})
                return[u for u in upg_info.get("upgrades", []) if "wall" in u.get("name", "").lower()]
        
        state_wrapper = SimpleStateManager(self)
        
        self.bot_orchestrator = BotOrchestrator(
            hwnd,
            rois,
            state_wrapper,
            self.attack_manager,
            self.upgrade_manager,
            self.builder_scanner,
            ui_callbacks
        )

        self._build_ui()
        self.load_state()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        threading.Thread(target=self._preview_loop, daemon=True).start()
        threading.Thread(target=self._anti_afk_loop, daemon=True).start()
        self._update_mouse_coords()
        self.log_terminal("  ▸ Ready. Select an engine to scan or Start Bot.", "sys")

    def _get_config_getters(self):
        getters = {}
        def make_getter(attr):
            return lambda: getattr(self, attr, tk.StringVar()).get()
        
        for attr in['engine_home_var', 'engine_upg_var', 'engine_enemy_var', 'engine_wall_var',
                     'use_tgt_gold', 'use_tgt_elx', 'use_tgt_goel', 'use_tgt_dark',
                     'tgt_gold_var', 'tgt_elx_var', 'tgt_goel_var', 'tgt_dark_var',
                     'ai_mode_var', 'ai_model_var', 'gemini_api_var',
                     'auto_donate_var', 'anti_afk_var', 'auto_wall_var']:
            getters[attr] = make_getter(attr)
        return getters

    def _set_bot_running(self, value):
        self.bot_running = value

    def load_state(self):
        from src.utils.config import STATUS_FILE
        import json
        
        if not STATUS_FILE.exists():
            return
            
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            
            self.state_cache = loaded
            cfg = loaded.get("config", {})
            
            if "engine_home" in cfg: self.engine_home_var.set(cfg["engine_home"])
            if "engine_upg" in cfg: self.engine_upg_var.set(cfg["engine_upg"])
            if "engine_enemy" in cfg: self.engine_enemy_var.set(cfg["engine_enemy"])
            if "engine_wall" in cfg: self.engine_wall_var.set(cfg["engine_wall"])
            if "use_tgt_gold" in cfg: self.use_tgt_gold.set(cfg["use_tgt_gold"])
            if "use_tgt_elx" in cfg: self.use_tgt_elx.set(cfg["use_tgt_elx"])
            if "use_tgt_goel" in cfg: self.use_tgt_goel.set(cfg["use_tgt_goel"])
            if "use_tgt_dark" in cfg: self.use_tgt_dark.set(cfg["use_tgt_dark"])
            if "tgt_gold" in cfg: self.tgt_gold_var.set(cfg["tgt_gold"])
            if "tgt_elx" in cfg: self.tgt_elx_var.set(cfg["tgt_elx"])
            if "tgt_goel" in cfg: self.tgt_goel_var.set(cfg["tgt_goel"])
            if "tgt_dark" in cfg: self.tgt_dark_var.set(cfg["tgt_dark"])
            if "ai_mode" in cfg: self.ai_mode_var.set(cfg["ai_mode"])
            if "ai_model" in cfg: self.ai_model_var.set(cfg["ai_model"])
            if "api_key" in cfg: self.gemini_api_var.set(cfg["api_key"])
            if "auto_donate" in cfg: self.auto_donate_var.set(cfg["auto_donate"])
            if "anti_afk" in cfg: self.anti_afk_var.set(cfg["anti_afk"])
            if "auto_wall" in cfg: self.auto_wall_var.set(cfg["auto_wall"])
            if "wall_check_freq" in cfg: self.wall_check_freq_var.set(cfg["wall_check_freq"])
            if "debug_ss" in cfg: self.debug_ss_var.set(cfg["debug_ss"])
            if "opacity" in cfg and hasattr(self, 'transparency_var'):
                self.transparency_var.set(cfg["opacity"])
                self._on_transparency_change(cfg["opacity"])
            
            cached_upg = self.state_cache.get("upgrades_info")
            if cached_upg:
                self.latest_data["upgrades_info"] = cached_upg
                
                walls = sum(item.get("qty", 1) for item in cached_upg.get("upgrades",[])
                            if "wall" in item.get("name", "").lower())
                self.badge_walls.set(str(walls))
                
                self.root.after(100, self._render_walls_ui)
            
            if hasattr(self, 'global_validate_and_update'):
                self.global_validate_and_update()
        except Exception:
            pass

    def save_state(self):
        from src.utils.config import STATUS_FILE
        import json
        
        self.state_cache["config"] = {
            "engine_home": self.engine_home_var.get(),
            "engine_upg": self.engine_upg_var.get(),
            "engine_enemy": self.engine_enemy_var.get(),
            "engine_wall": self.engine_wall_var.get(),
            "use_tgt_gold": self.use_tgt_gold.get(),
            "use_tgt_elx": self.use_tgt_elx.get(),
            "use_tgt_goel": self.use_tgt_goel.get(),
            "use_tgt_dark": self.use_tgt_dark.get(),
            "tgt_gold": self.tgt_gold_var.get(),
            "tgt_elx": self.tgt_elx_var.get(),
            "tgt_goel": self.tgt_goel_var.get(),
            "tgt_dark": self.tgt_dark_var.get(),
            "ai_mode": self.ai_mode_var.get(),
            "ai_model": self.ai_model_var.get(),
            "api_key": self.gemini_api_var.get(),
            "auto_donate": self.auto_donate_var.get(),
            "anti_afk": self.anti_afk_var.get(),
            "auto_wall": self.auto_wall_var.get(),
            "wall_check_freq": self.wall_check_freq_var.get(),
            "debug_ss": self.debug_ss_var.get() if hasattr(self, 'debug_ss_var') else True,
            "opacity": self.transparency_var.get() if hasattr(self, 'transparency_var') else 100
        }
        
        try:
            with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.state_cache, f, indent=4)
        except Exception:
            pass

    def _update_mouse_coords(self):
        try:
            rel_x, rel_y = get_relative_mouse_pos(self.hwnd)
            if rel_x >= 0 and rel_y >= 0 and rel_x <= 1 and rel_y <= 1:
                self.mouse_coords_lbl.config(text=f"X: {rel_x:.3f}  Y: {rel_y:.3f}", fg="#eab308")
            else:
                self.mouse_coords_lbl.config(text="X: ---  Y: ---", fg="#737373")
        except Exception:
            pass
        self.root.after(100, self._update_mouse_coords)

    def _anti_afk_loop(self):
        while True:
            if getattr(self, 'anti_afk_var', None) and self.anti_afk_var.get() and not self.bot_running:
                try:
                    zoom_camera(self.hwnd, ticks=5, direction="in")
                    time.sleep(1.0)
                    
                    pan_camera(self.hwnd, start_rel=(0.6, 0.5), end_rel=(0.4, 0.5))
                    time.sleep(1.0)
                    
                    pan_camera(self.hwnd, start_rel=(0.4, 0.5), end_rel=(0.6, 0.5))
                    time.sleep(1.0)

                    zoom_camera(self.hwnd, ticks=5, direction="out")
                    
                    for _ in range(150):
                        if not self.anti_afk_var.get() or self.bot_running:
                            break
                        time.sleep(0.1)
                except Exception as e:
                    print(f"[WARN] Anti-AFK error: {e}")
                    time.sleep(2.0)
            else:
                time.sleep(1.0)

    def _style_dropdown(self, opt, width=8):
        opt.config(
            bg=BG_CARD2, fg=FG_PRIMARY,
            activebackground=BORDER_BRIGHT, activeforeground=FG_PRIMARY,
            highlightthickness=1, highlightbackground=BORDER,
            relief="flat", font=("Courier", 8), width=width, cursor="hand2",
        )
        opt["menu"].config(
            bg=BG_CARD2, fg=FG_PRIMARY, font=("Courier", 8),
            relief="flat", activebackground=BORDER_BRIGHT,
        )

    def _safe_capture(self):
        with self.capture_lock:
            frame = capture_frame(self.hwnd)
            
            if frame is not None and getattr(self, "bot_running", False):
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
                    self.log_terminal("[WARN] Reload Game popup detected! Clicking Reload...", "sys")
                    click_relative_roi(self.hwnd, {"x": 0.320, "y": 0.566, "w": 0, "h": 0})
                    time.sleep(5.0)
                    
                    while getattr(self, "bot_running", False):
                        f = capture_frame(self.hwnd)
                        if f is not None:
                            if is_main_screen(f, self.rois["main_screen_i"]):
                                self.log_terminal("[BOT] Main village detected after reload! Initiating restart...", "sys")
                                raise ReloadGameException("Game was reloaded. Restarting loop.")
                            
                            fh, fw = f.shape[:2]
                            
                            # Check for Match End screen (stars)
                            s1_x, s1_y = int(0.870 * fw), int(0.445 * fh)
                            s2_x, s2_y = int(0.170 * fw), int(0.540 * fh)
                            s_col1 = np.mean(f[max(0, s1_y-2):s1_y+3, max(0, s1_x-2):s1_x+3])
                            s_col2 = np.mean(f[max(0, s2_y-2):s2_y+3, max(0, s2_x-2):s2_x+3])
                            
                            if s_col1 < 10 and s_col2 < 10:
                                self.log_terminal("[BOT] Match End Detected after reload! Clicking 'Return Home'...", "bot")
                                click_relative_roi(self.hwnd, {"x": 0.505, "y": 0.850, "w": 0, "h": 0})
                                time.sleep(2.0)
                                continue
                                
                            # Check for Star Bonus popup
                            px, py = int(0.659 * fw), int(0.120 * fh)
                            color = f[py, px]
                            target_color = np.array([204, 255, 255])
                            if np.all(np.abs(color.astype(int) - target_color.astype(int)) <= 15):
                                self.log_terminal("[BOT] Star Bonus popup detected after reload! Clicking Okay...", "bot")
                                click_relative_roi(self.hwnd, {"x": 0.50, "y": 0.83, "w": 0, "h": 0})
                                time.sleep(2.0)
                                continue

                        time.sleep(1.0)
                    raise ReloadGameException("Game was reloaded. Restarting loop.")
                    
            return frame

    def _hsep(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=6)

    def _col_label(self, parent, text, color=FG_DIM):
        tk.Label(parent, text=text, font=("Courier", 8, "bold"),
                 bg=BG_DEEP, fg=color).pack(anchor="w", pady=(0, 5))

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)

        self._build_header()
        self._build_scrollable_body()
        self._build_terminal()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG_DEEP)
        hdr.grid(row=0, column=0, sticky="ew")

        top = tk.Frame(hdr, bg=BG_DEEP)
        top.pack(fill="x", padx=16, pady=(10, 0))

        logo = tk.Frame(top, bg=BG_DEEP)
        logo.pack(side="left")
        tk.Label(logo, text="⬡ ", font=("Courier", 15, "bold"),
                 bg=BG_DEEP, fg=ACCENT_GOLD).pack(side="left")
        tk.Label(logo, text="AUTO", font=("Courier", 15, "bold"),
                 bg=BG_DEEP, fg=FG_PRIMARY).pack(side="left")
        tk.Label(logo, text="WALLS", font=("Courier", 15, "bold"),
                 bg=BG_DEEP, fg=ACCENT_GOLD).pack(side="left")
        tk.Label(logo, text="  ·  https://github.com/N1xUser", font=("Courier", 9),
                 bg=BG_DEEP, fg=FG_DIM, cursor="hand2").pack(side="left")
        
        # Link the label to GitHub
        for slave in logo.pack_slaves():
            if slave.cget("text") == "  ·  Tri-Engine OCR by N1xUser":
                slave.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/N1xUser"))

        right = tk.Frame(top, bg=BG_DEEP)
        right.pack(side="right")

        self.mouse_coords_lbl = tk.Label(right, text="X: ---  Y: ---", font=("Courier", 8, "bold"), bg=BG_DEEP, fg="#737373")
        self.mouse_coords_lbl.pack(side="left", padx=(0, 15))

        self.preview_var = tk.BooleanVar(value=False)
        self.anti_afk_var = tk.BooleanVar(value=False)
        self.auto_wall_var = tk.BooleanVar(value=False)
        
        cb_auto_wall = tk.Checkbutton(
            right, text="AUTO WALLS", variable=self.auto_wall_var,
            bg=BG_DEEP, fg=FG_SECONDARY, selectcolor=BG_PANEL,
            activebackground=BG_DEEP, activeforeground=FG_PRIMARY,
            font=("Courier", 8, "bold"), cursor="hand2",
            command=self.save_state,
        )
        cb_auto_wall.pack(side="left", padx=(0, 4))
        self.config_widgets.append(cb_auto_wall)

        self.wall_check_freq_var = tk.IntVar(value=1)
        freq_frame = tk.Frame(right, bg=BG_DEEP)
        freq_frame.pack(side="left", padx=(0, 8))
        tk.Label(freq_frame, text="EVERY", font=("Courier", 7, "bold"),
                 bg=BG_DEEP, fg=FG_DIM).pack(side="left")
        freq_spin = tk.Spinbox(
            freq_frame, from_=1, to=20, width=3,
            textvariable=self.wall_check_freq_var,
            font=("Courier", 8, "bold"),
            bg=BG_CARD2, fg=FG_PRIMARY, buttonbackground=BG_CARD2,
            relief="flat", highlightthickness=1, highlightbackground=BORDER,
            command=self.save_state,
        )
        freq_spin.pack(side="left", padx=2)
        self.config_widgets.append(freq_spin)
        tk.Label(freq_frame, text="ATK", font=("Courier", 7, "bold"),
                 bg=BG_DEEP, fg=FG_DIM).pack(side="left")
        
        cb_anti_afk = tk.Checkbutton(
            right, text="ANTI AFK", variable=self.anti_afk_var,
            bg=BG_DEEP, fg=FG_SECONDARY, selectcolor=BG_PANEL,
            activebackground=BG_DEEP, activeforeground=FG_PRIMARY,
            font=("Courier", 8, "bold"), cursor="hand2",
            command=self.save_state,
        )
        cb_anti_afk.pack(side="left", padx=(0, 8))
        self.config_widgets.append(cb_anti_afk)
        tk.Checkbutton(
            right, text="PREVIEW", variable=self.preview_var,
            bg=BG_DEEP, fg=FG_SECONDARY, selectcolor=BG_PANEL,
            activebackground=BG_DEEP, activeforeground=FG_PRIMARY,
            font=("Courier", 8, "bold"), cursor="hand2",
            command=self._on_preview_toggle,
        ).pack(side="left", padx=(0, 12))

        trans_frame = tk.Frame(right, bg=BG_DEEP)
        trans_frame.pack(side="left", padx=(0, 12))
        tk.Label(trans_frame, text="OPACITY", font=("Courier", 7, "bold"), bg=BG_DEEP, fg=FG_DIM).pack(side="left")
        
        self.transparency_var = tk.IntVar(value=100)
        self.trans_scale = tk.Scale(
            trans_frame, from_=20, to=100, orient="horizontal",
            variable=self.transparency_var, command=self._on_transparency_change,
            bg=BG_DEEP, fg=FG_PRIMARY, troughcolor=BG_PANEL,
            highlightthickness=0, bd=0, activebackground=BG_DEEP,
            font=("Courier", 7), sliderlength=10, length=60, showvalue=0
        )
        self.trans_scale.pack(side="left", padx=2)
        self.trans_scale.bind("<ButtonRelease-1>", lambda e: self.save_state())
        
        self.trans_lbl = tk.Label(trans_frame, text="100%", font=("Courier", 7, "bold"), bg=BG_DEEP, fg=FG_PRIMARY)
        self.trans_lbl.pack(side="left")

        tk.Frame(right, bg=BORDER, width=1).pack(
            side="left", fill="y", pady=4, padx=(0, 12))

        tk.Label(right, text="SCAN", font=("Courier", 7, "bold"),
                 bg=BG_DEEP, fg=FG_DIM).pack(side="left", padx=(0, 8))

        self.btn_tess = make_btn(right, "TESS",
                                  lambda: self.on_update_click("tesseract"), ACCENT_GOLD)
        self.btn_glm = make_btn(right, "GLM",
                                  lambda: self.on_update_click("glm"), ACCENT_ELX)
        self.btn_rapid = make_btn(right, "RAPID",
                                  lambda: self.on_update_click("rapid"), ACCENT_DARK)
        for b in (self.btn_tess, self.btn_glm, self.btn_rapid):
            b.pack(side="left", padx=3)

        strip = tk.Frame(hdr, bg=BG_DEEP)
        strip.pack(fill="x", padx=16, pady=(8, 0))

        self.badge_builders = StatBadge(strip, "BUILDERS", "?/?", FG_PRIMARY)
        self.badge_builders.pack(side="left", padx=(0, 4))

        self.badge_walls = StatBadge(strip, "WALLS", "0", ACCENT_UPG)
        self.badge_walls.pack(side="left", padx=(0, 4))

        self.bot_status_lbl = tk.Label(
            strip, text="● BOT IDLE", font=("Courier", 8, "bold"),
            bg=BG_DEEP, fg=FG_DIM,
        )
        self.bot_status_lbl.pack(side="left", padx=(10, 0))

        self.btn_bot = tk.Button(
            strip, text="▶  START BOT", font=("Courier", 9, "bold"),
            bg="#22c55e", fg=BG_DEEP,
            activebackground="#16a34a", activeforeground=BG_DEEP,
            relief="flat", padx=14, pady=4, cursor="hand2",
            command=self.on_start_bot,
        )
        self.btn_bot.pack(side="right")

        tk.Frame(hdr, bg=BORDER, height=1).pack(fill="x", pady=(8, 0))

    def _build_scrollable_body(self):
        self._scroll_body = ScrollableFrame(self.root, bg=BG_DEEP)
        self._scroll_body.grid(row=1, column=0, sticky="nsew")

        body = self._scroll_body.inner
        body.columnconfigure(0, weight=1, uniform="col")
        body.columnconfigure(1, weight=1, uniform="col")
        body.columnconfigure(2, weight=1, uniform="col")

        self._build_home_col(body)
        self._build_enemy_col(body)
        self._build_config_col(body)

    def _build_home_col(self, parent):
        col = tk.Frame(parent, bg=BG_DEEP)
        col.grid(row=0, column=0, sticky="nsew", padx=(16, 6), pady=14)

        self._col_label(col, "HOME RESOURCES", ACCENT_GOLD)

        self.card_gold = Badge(col, "Gold", "⚡", ACCENT_GOLD)
        self.card_elixir = Badge(col, "Elixir", "✦", ACCENT_ELX)
        self.card_dark = Badge(col, "Dark Elixir", "◈", ACCENT_DARK)
        for card in (self.card_gold, self.card_elixir, self.card_dark):
            card.pack(fill="x", pady=3)
            card.configure(highlightthickness=1, highlightbackground=BORDER)

        self._hsep(col)
        self._col_label(col, "SCAN UPGRADES", ACCENT_UPG)

        upg_row = tk.Frame(col, bg=BG_DEEP)
        upg_row.pack(fill="x", pady=(0, 4))
        self.btn_upg_tess = make_btn(upg_row, "TESS",
                                      lambda: self.on_detect_builders("tesseract"),
                                      ACCENT_GOLD, small=True)
        self.btn_upg_glm = make_btn(upg_row, "GLM",
                                      lambda: self.on_detect_builders("glm"),
                                      ACCENT_ELX, small=True)
        self.btn_upg_rapid = make_btn(upg_row, "RAPID",
                                      lambda: self.on_detect_builders("rapid"),
                                      ACCENT_DARK, small=True)
        for b in (self.btn_upg_tess, self.btn_upg_glm, self.btn_upg_rapid):
            b.pack(side="left", padx=(0, 4))
            
        self.btn_save_upg = make_btn(upg_row, "SAVE EDITS",
                                      self._save_upgrades_json,
                                      ACCENT_RED, small=True)
        self.btn_save_upg.pack(side="right", padx=(0, 4))

        text_container = tk.Frame(col, bg=BG_DEEP, height=175)
        text_container.pack(fill="x", pady=(0, 5))
        text_container.pack_propagate(False)

        self.upgrades_text = scrolledtext.ScrolledText(
            text_container, bg=BG_CARD, fg=FG_SECONDARY, font=("Courier", 8),
            relief="flat", bd=0, padx=8, pady=6,
            highlightthickness=1, highlightbackground=BORDER,
        )
        
        self.upgrades_text.pack(fill="both", expand=True)
        
        self.upgrades_text.insert(tk.END, "Waiting for Home Screen scan...")

        self._hsep(col)
        self._col_label(col, "WALL TARGETS", ACCENT_GOLD)

        self.walls_container = tk.Frame(col, bg=BG_DEEP)
        self.walls_container.pack(fill="x", pady=(0, 5))

    def _build_enemy_col(self, parent):
        col = tk.Frame(parent, bg=BG_DEEP)
        col.grid(row=0, column=1, sticky="nsew", padx=6, pady=14)

        self._col_label(col, "ENEMY LOOT", ACCENT_RED)

        self.card_enemy_gold = Badge(col, "Enemy Gold", "⚡", ACCENT_GOLD)
        self.card_enemy_elixir = Badge(col, "Enemy Elixir", "✦", ACCENT_ELX)
        self.card_enemy_dark = Badge(col, "Enemy Dark", "◈", ACCENT_DARK)
        for card in (self.card_enemy_gold, self.card_enemy_elixir, self.card_enemy_dark):
            card.pack(fill="x", pady=3)
            card.configure(highlightthickness=1, highlightbackground=BORDER)

        self._hsep(col)

        self._col_label(col, "AI INTEGRATION", ACCENT_ELX)
        
        api_card = tk.Frame(col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER, height=210)
        api_card.pack_propagate(False)
        api_card.pack(fill="x", pady=(0, 6))
        
        api_inner = tk.Frame(api_card, bg=BG_CARD)
        api_inner.pack(fill="both", expand=True, padx=12, pady=10)

        btn_debug = tk.Button(
            api_inner, text="DEBUG JSON", command=self.open_debug_json_window,
            font=("Courier", 8, "bold"), bg=BG_DEEP, fg=ACCENT_ELX, cursor="hand2"
        )
        btn_debug.pack(anchor="w", pady=(0, 8))

        def ai_cfg_row(label_text, var_obj, options_list):
            row = tk.Frame(api_inner, bg=BG_CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label_text, font=("Courier", 8), 
                     bg=BG_CARD, fg=FG_SECONDARY).pack(side="left")
            opt = tk.OptionMenu(row, var_obj, *options_list)
            self._style_dropdown(opt, width=17)
            opt.pack(side="right")
            self.config_widgets.append(opt)

        self.ai_mode_var = tk.StringVar(value="STATIC")
        ai_cfg_row("ATTACK MODE", self.ai_mode_var, ["STATIC", "DYNAMIC AI"])

        self.ai_model_var = tk.StringVar(value="GEMINI FLASH LITE")
        ai_cfg_row("MODEL", self.ai_model_var,["GEMINI FLASH LITE", "GEMINI 1.5 PRO", "GPT-4O MINI", "GEMINI 3 FLASH PREVIEW", "GEMINI 3.1 PRO PREVIEW"])

        tk.Frame(api_inner, bg=BORDER, height=1).pack(fill="x", pady=10)

        tk.Label(api_inner, text="API KEY", font=("Courier", 8, "bold"), 
                 bg=BG_CARD, fg=FG_SECONDARY).pack(anchor="w", pady=(0, 5))
        
        self.gemini_api_var = tk.StringVar()
        api_entry = tk.Entry(
            api_inner, textvariable=self.gemini_api_var, font=("Courier", 8),
            bg=BG_PANEL, fg=FG_PRIMARY, insertbackground=FG_PRIMARY,
            relief="flat", show="*", highlightthickness=1, 
            highlightbackground=BORDER, highlightcolor=ACCENT_ELX
        )
        api_entry.pack(fill="x", ipady=4, padx=1)
        self.config_widgets.append(api_entry)

    def _build_config_col(self, parent):
        col = tk.Frame(parent, bg=BG_DEEP)
        col.grid(row=0, column=2, sticky="nsew", padx=(6, 16), pady=14)

        self._col_label(col, "PIPELINE CONFIG", FG_DIM)

        card = tk.Frame(col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x")

        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="both", expand=True, padx=14, pady=12)
        inner.columnconfigure(0, weight=0)
        inner.columnconfigure(1, weight=1)

        self.engine_home_var = tk.StringVar(value="RAPID")
        self.engine_upg_var = tk.StringVar(value="RAPID")
        self.engine_enemy_var = tk.StringVar(value="RAPID")
        self.engine_wall_var = tk.StringVar(value="GLM")
        self.use_tgt_gold = tk.IntVar(value=1)
        self.use_tgt_elx = tk.IntVar(value=1)
        self.use_tgt_goel = tk.IntVar(value=0)
        self.use_tgt_dark = tk.IntVar(value=0)
        
        self.tgt_gold_var = tk.IntVar(value=500000)
        self.tgt_elx_var = tk.IntVar(value=500000)
        self.tgt_goel_var = tk.IntVar(value=1000000)
        self.tgt_dark_var = tk.IntVar(value=3000)

        engines = ["TESSERACT", "GLM", "RAPID"]
        r = [0]
        self.ui_updaters =[]

        def global_validate_and_update(triggered_by=None):
            if triggered_by == "GO&EL" and self.use_tgt_goel.get() > 0:
                self.use_tgt_gold.set(0)
                self.use_tgt_elx.set(0)
            elif triggered_by in ["GOLD", "ELIXIR"] and (self.use_tgt_gold.get() > 0 or self.use_tgt_elx.get() > 0):
                self.use_tgt_goel.set(0)

            active_vars =[v for v in (self.use_tgt_gold, self.use_tgt_elx, self.use_tgt_dark, self.use_tgt_goel) if v.get() > 0]
            if len(active_vars) == 1 and active_vars[0].get() == 2:
                active_vars[0].set(1)
                
            for update_fn in self.ui_updaters:
                update_fn()
                
        self.global_validate_and_update = global_validate_and_update

        def section_lbl(text, color):
            tk.Label(inner, text=text, font=("Courier", 8, "bold"),
                     bg=BG_CARD, fg=color).grid(
                row=r[0], column=0, columnspan=2, sticky="w", pady=(8, 3))
            r[0] += 1

        def cfg_row(label, var):
            tk.Label(inner, text=label, font=("Courier", 8),
                     bg=BG_CARD, fg=FG_SECONDARY).grid(
                row=r[0], column=0, sticky="w", pady=2)
            opt = tk.OptionMenu(inner, var, *engines)
            self._style_dropdown(opt, width=7)
            opt.grid(row=r[0], column=1, sticky="e", pady=2)
            self.config_widgets.append(opt)
            r[0] += 1

        def divider():
            tk.Frame(inner, bg=BORDER, height=1).grid(
                row=r[0], column=0, columnspan=2, sticky="ew", pady=6)
            r[0] += 1

        def target_row(label_text, toggle_var, scale_var, max_val, step, color, name_id):
            def toggle():
                current = toggle_var.get()
                active_count = sum(1 for v in (self.use_tgt_gold, self.use_tgt_elx, self.use_tgt_dark, self.use_tgt_goel) if v.get() > 0)
                
                if active_count <= 1 and current > 0:
                    toggle_var.set(0)
                elif active_count == 0 and current == 0:
                    toggle_var.set(1)
                else:
                    toggle_var.set((current + 1) % 3)
                
                self.global_validate_and_update(name_id)

            def update_ui():
                st = toggle_var.get()
                if st == 1:   sym, c = "✓", color
                elif st == 2: sym, c = "•", color
                else:         sym, c = " ", FG_DIM
                
                chk_btn.config(text=f"[{sym}] {label_text}", fg=c, activeforeground=c)
                scale.config(fg=c)

            chk_btn = tk.Button(
                inner, command=toggle, bg=BG_CARD, activebackground=BG_CARD,
                relief="flat", bd=0, highlightthickness=0,
                font=("Courier", 8, "bold"), cursor="hand2", anchor="w", width=10, padx=0, pady=0
            )
            chk_btn.grid(row=r[0], column=0, sticky="w", pady=2)
            self.config_widgets.append(chk_btn)

            scale = tk.Scale(
                inner, variable=scale_var, from_=0, to=max_val, resolution=step,
                orient="horizontal", bg=BG_CARD, fg=color, troughcolor=BG_PANEL,
                highlightthickness=0, bd=0, activebackground=BORDER_BRIGHT,
                font=("Courier", 7), sliderlength=12,
            )
            scale.grid(row=r[0], column=1, sticky="ew", padx=(8, 0), pady=2)
            self.config_widgets.append(scale)
            
            self.ui_updaters.append(update_ui)
            update_ui()
            r[0] += 1

        section_lbl("HOME PIPELINE", ACCENT_UPG)
        cfg_row("1. RESOURCES", self.engine_home_var)
        cfg_row("2. UPGRADES", self.engine_upg_var)
        divider()

        section_lbl("ATTACK CONFIG", ACCENT_RED)
        cfg_row("ENEMY LOOT", self.engine_enemy_var)
        cfg_row("WALL OCR", self.engine_wall_var)
        divider()

        section_lbl("MIN TARGETS  (✓=AND, •=OR)", FG_DIM)
        target_row("GOLD", self.use_tgt_gold, self.tgt_gold_var, 1500000, 50000, ACCENT_GOLD, "GOLD")
        target_row("ELIXIR", self.use_tgt_elx, self.tgt_elx_var, 1500000, 50000, ACCENT_ELX, "ELIXIR")
        target_row("GO&EL", self.use_tgt_goel, self.tgt_goel_var, 2500000, 50000, "#10b981", "GO&EL")
        target_row("DARK", self.use_tgt_dark, self.tgt_dark_var, 15000, 500, ACCENT_DARK, "DARK")

        tk.Frame(inner, bg=BG_CARD, height=8).grid(row=r[0], column=0, columnspan=2, sticky="ew")
        self._hsep(col)

        self._col_label(col, "ATTACK SETTINGS", ACCENT_DARK)
        
        atk_card = tk.Frame(col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        atk_card.pack(fill="x")
        
        atk_inner = tk.Frame(atk_card, bg=BG_CARD)
        atk_inner.pack(fill="both", expand=True, padx=12, pady=20)
        
        self.auto_donate_var = tk.BooleanVar(value=False)
        cb_auto_donate = tk.Checkbutton(
            atk_inner, text="AUTO-DONATE (WIP)", variable=self.auto_donate_var,
            bg=BG_CARD, fg=FG_PRIMARY, selectcolor=BG_DEEP,
            activebackground=BG_CARD, activeforeground=FG_PRIMARY,
            font=("Courier", 8, "bold"), cursor="hand2"
        )
        cb_auto_donate.pack(anchor="w", pady=(0, 8))
        self.config_widgets.append(cb_auto_donate)

        self.debug_ss_var = tk.BooleanVar(value=True)
        cb_debug_ss = tk.Checkbutton(
            atk_inner, text="SAVE DEBUG SCREENSHOTS", variable=self.debug_ss_var,
            bg=BG_CARD, fg=FG_PRIMARY, selectcolor=BG_DEEP,
            activebackground=BG_CARD, activeforeground=FG_PRIMARY,
            font=("Courier", 8, "bold"), cursor="hand2"
        )
        cb_debug_ss.pack(anchor="w", pady=(0, 8))
        self.config_widgets.append(cb_debug_ss)


        tk.Frame(atk_inner, bg=BORDER, height=1).pack(fill="x", pady=10)
        
        tk.Label(atk_inner, text="WALL UPGRADE TEST", font=("Courier", 7, "bold"), 
                 bg=BG_CARD, fg=FG_DIM).pack(anchor="w", pady=(0, 8))
        
        self.btn_test_wall = tk.Button(
            atk_inner, text="TEST AUTOWALL", font=("Courier", 9, "bold"),
            bg=ACCENT_UPG, fg=BG_DEEP,
            activebackground="#7c3aed", activeforeground=BG_DEEP,
            relief="flat", padx=12, pady=6, cursor="hand2",
            command=self.on_test_autowall,
        )
        self.btn_test_wall.pack(fill="x", pady=(0, 10))
        
        tk.Frame(atk_inner, bg=BORDER, height=1).pack(fill="x", pady=10)
        
        tk.Label(atk_inner, text="PRIMARY DEPLOYMENT", font=("Courier", 7, "bold"), 
                 bg=BG_CARD, fg=FG_DIM).pack(anchor="w")
        
        troop_frame = tk.Frame(atk_inner, bg=BG_CARD)
        troop_frame.pack(anchor="w", pady=(3, 0))
        tk.Label(troop_frame, text="⚡", font=("Segoe UI Emoji", 10), 
                 bg=BG_CARD, fg=ACCENT_DARK).pack(side="left")
        tk.Label(troop_frame, text="ELECTRIC DRAGONS", font=("Courier", 9, "bold"), 
                 bg=BG_CARD, fg=ACCENT_DARK).pack(side="left", padx=(4, 0))

    def _build_terminal(self):
        TERM_H = 200

        outer = tk.Frame(self.root, bg=BG_DEEP, height=TERM_H)
        outer.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        outer.pack_propagate(False)

        hdr = tk.Frame(outer, bg=BG_DEEP)
        hdr.pack(fill="x")
        tk.Label(hdr, text="▸ TERMINAL", font=("Courier", 8, "bold"),
                 bg=BG_DEEP, fg=FG_DIM).pack(side="left", pady=(4, 3))
        tk.Button(
            hdr, text="CLEAR", font=("Courier", 7, "bold"),
            bg=BG_CARD2, fg=FG_DIM,
            activebackground=BORDER, activeforeground=FG_PRIMARY,
            relief="flat", padx=6, pady=1, cursor="hand2",
            command=self._clear_terminal,
        ).pack(side="right", pady=(4, 3))

        wrap = tk.Frame(outer, bg=BORDER, bd=0)
        wrap.pack(fill="both", expand=True)

        self.terminal = scrolledtext.ScrolledText(
            wrap, bg=BG_PANEL, fg=FG_GREEN, font=("Courier", 8),
            insertbackground=FG_PRIMARY, relief="flat", bd=0,
            padx=10, pady=8, wrap="word",
        )
        self.terminal.pack(fill="both", expand=True, padx=1, pady=1)
        self.terminal.tag_config("sys", foreground=FG_DIM)
        self.terminal.tag_config("time", foreground="#475569")
        self.terminal.tag_config("bot", foreground="#22c55e")
        self.terminal.tag_config("bot_off", foreground=ACCENT_RED)
        self.terminal.tag_config("gold", foreground=ACCENT_GOLD)
        self.terminal.tag_config("elx", foreground=ACCENT_ELX)
        self.terminal.tag_config("dark", foreground=ACCENT_DARK)

    def _clear_terminal(self):
        self.terminal.configure(state="normal")
        self.terminal.delete(1.0, tk.END)
        self.terminal.configure(state="disabled")

    def _on_preview_toggle(self):
        self.preview_enabled = self.preview_var.get()
        
    def _on_transparency_change(self, val):
        alpha = float(val) / 100.0
        self.root.attributes("-alpha", alpha)
        if hasattr(self, 'trans_lbl'):
            self.trans_lbl.config(text=f"{int(float(val))}%")
    
    def _get_target_info_string(self):
        def get_tgt_str(use_var, val_var, suffix):
            st = use_var.get()
            if st == 1: return f"AND {val_var.get():,} {suffix}"
            if st == 2: return f"OR  {val_var.get():,} {suffix}"
            return ""
        
        t_g = get_tgt_str(self.use_tgt_gold, self.tgt_gold_var, "G")
        t_e = get_tgt_str(self.use_tgt_elx, self.tgt_elx_var, "E")
        t_ge = get_tgt_str(self.use_tgt_goel, self.tgt_goel_var, "G+E")
        t_d = get_tgt_str(self.use_tgt_dark, self.tgt_dark_var, "D")
        
        active_targets = [t for t in[t_g, t_e, t_ge, t_d] if t]
        if not active_targets:
            return "NO TARGETS SET"
        return " | ".join(active_targets)
    
    def _validate_loot(self, gold, elixir, dark):
        and_count = sum(1 for v in[self.use_tgt_gold, self.use_tgt_elx, self.use_tgt_goel, self.use_tgt_dark] if v.get() == 1)
        or_count = sum(1 for v in[self.use_tgt_gold, self.use_tgt_elx, self.use_tgt_goel, self.use_tgt_dark] if v.get() == 2)
        
        and_conditions = []
        or_conditions =[]
        
        if self.use_tgt_gold.get() == 1:
            and_conditions.append(gold >= self.tgt_gold_var.get())
        elif self.use_tgt_gold.get() == 2:
            or_conditions.append(gold >= self.tgt_gold_var.get())
        
        if self.use_tgt_elx.get() == 1:
            and_conditions.append(elixir >= self.tgt_elx_var.get())
        elif self.use_tgt_elx.get() == 2:
            or_conditions.append(elixir >= self.tgt_elx_var.get())
        
        if self.use_tgt_goel.get() == 1:
            and_conditions.append((gold + elixir) >= self.tgt_goel_var.get())
        elif self.use_tgt_goel.get() == 2:
            or_conditions.append((gold + elixir) >= self.tgt_goel_var.get())
        
        if self.use_tgt_dark.get() == 1:
            and_conditions.append(dark >= self.tgt_dark_var.get())
        elif self.use_tgt_dark.get() == 2:
            or_conditions.append(dark >= self.tgt_dark_var.get())
        
        and_pass = all(and_conditions) if and_conditions else True
        or_pass = any(or_conditions) if or_conditions else True
        
        return and_pass and or_pass
    
    def _refresh_upgrades_display(self):
        upg = self.latest_data.get("upgrades_info", {})
        
        walls = sum(item.get("qty", 1) for item in upg.get("upgrades",[])
                    if "wall" in item.get("name", "").lower())
        self.badge_walls.set(str(walls))
        
        txt = json.dumps(upg, indent=2) if isinstance(upg, dict) else str(upg)
        self.upgrades_text.configure(state="normal")
        self.upgrades_text.delete(1.0, tk.END)
        self.upgrades_text.insert(tk.END, txt)
        self.upgrades_text.configure(state="disabled")

    def on_update_click(self, engine: str):
        for b in (self.btn_tess, self.btn_glm, self.btn_rapid):
            b.config(state="disabled", text="…")
        self.log_terminal(f"  ▸ Capturing with {engine.upper()}...", "sys")
        threading.Thread(target=self.run_ocr_once, args=(engine,), daemon=True).start()

    def on_detect_builders(self, engine: str):
        for b in (self.btn_upg_tess, self.btn_upg_glm, self.btn_upg_rapid):
            b.config(state="disabled", text="…")
        self.log_terminal(f"  ▸ Opening Upgrades Menu ({engine.upper()})...", "sys")
        threading.Thread(target=self.run_detect_builders, args=(engine,), daemon=True).start()

    def on_test_autowall(self):
        self.log_terminal("\n[TEST] Starting AutoWall Test...", "bot")
        self.btn_test_wall.config(state="disabled", text="TESTING...")
        threading.Thread(target=self.run_test_autowall, daemon=True).start()

    def run_test_autowall(self):
        original_bot_state = self.bot_running
        try:
            upg_info = self.latest_data.get("upgrades_info", {})
            
            if not upg_info or "upgrades" not in upg_info:
                self.root.after(0, self.log_terminal, "[TEST] No upgrades cache found. Please scan upgrades first!", "bot_off")
                self.root.after(0, lambda: self.btn_test_wall.config(state="normal", text="TEST AUTOWALL"))
                return
            
            walls =[u for u in upg_info.get("upgrades", []) if "wall" in u.get("name", "").lower()]
            
            if not walls:
                self.root.after(0, self.log_terminal, "[TEST] No walls found in upgrades. Please scan upgrades!", "bot_off")
                self.root.after(0, lambda: self.btn_test_wall.config(state="normal", text="TEST AUTOWALL"))
                return
            
            self.root.after(0, self.log_terminal, f"[TEST] Found {len(walls)} wall type(s) available:", "sys")
            for w in walls:
                self.root.after(0, self.log_terminal, f"[TEST]   - {w.get('name', 'Unknown')} (Cost: {w.get('cost', 0):,}, Qty: {w.get('qty', 1)})", "sys")
            
            self.root.after(0, self.log_terminal, f"[TEST] Current Resources (from UI): Gold={self.latest_data.get('gold', 0):,}, Elixir={self.latest_data.get('elixir', 0):,}", "gold")
            self.root.after(0, self.log_terminal, f"[TEST] Latest_data dict id: {id(self.latest_data)}", "sys")
            
            walls_copy = [w.copy() for w in walls]
            walls_copy.sort(key=lambda x: x.get("cost", float('inf')))
            self.root.after(0, self.log_terminal, f"[TEST] Starting upgrade sequence for {len(walls_copy)} wall type(s)...", "bot")
            
            self.bot_running = True
            
            success = self.upgrade_manager.upgrade_walls(walls_copy, self._safe_capture)
            
            if success:
                self.root.after(0, self.log_terminal, "[TEST] AutoWall test completed successfully!", "bot")
            else:
                self.root.after(0, self.log_terminal, "[TEST] AutoWall test completed with issues.", "sys")
                
        except Exception as e:
            import traceback
            self.root.after(0, self.log_terminal, f"[TEST] Error during AutoWall test: {str(e)}", "bot_off")
            self.root.after(0, self.log_terminal, f"[TEST] Traceback: {traceback.format_exc()}", "sys")
        finally:
            self.bot_running = original_bot_state
            self.root.after(0, lambda: self.btn_test_wall.config(state="normal", text="TEST AUTOWALL"))

    def on_start_bot(self):
        if not self.bot_running:
            self.bot_running = True
            self.btn_bot.config(text="■  STOP BOT", bg="#ef4444", activebackground="#dc2626")
            self.bot_status_lbl.config(text="● BOT RUNNING", fg="#22c55e")

            for w in self.config_widgets:
                w.config(state="disabled")
            self.reset_buttons()

            self.save_state()

            e_h = self.engine_home_var.get()
            e_u = self.engine_upg_var.get()
            e_e = self.engine_enemy_var.get()
            
            def get_tgt_str(use_var, val_var, suffix):
                st = use_var.get()
                if st == 1: return f"AND {val_var.get():,} {suffix}"
                if st == 2: return f"OR  {val_var.get():,} {suffix}"
                return ""

            t_g = get_tgt_str(self.use_tgt_gold, self.tgt_gold_var, "G")
            t_e = get_tgt_str(self.use_tgt_elx, self.tgt_elx_var, "E")
            t_ge = get_tgt_str(self.use_tgt_goel, self.tgt_goel_var, "G+E")
            t_d = get_tgt_str(self.use_tgt_dark, self.tgt_dark_var, "D")

            self.log_terminal("\n[BOT] Starting Automation Sequence...", "bot")
            self.log_terminal(f"[BOT] Home: Resources({e_h}) ➔ Upgrades({e_u})", "bot")
            self.log_terminal(f"[BOT] Attack: Enemy Loot({e_e})", "bot")
            
            active_targets = [t for t in[t_g, t_e, t_ge, t_d] if t]
            if not active_targets: active_targets = ["NO TARGETS SET"]
            
            self.log_terminal(f"[BOT] Min Loot:[ {' | '.join(active_targets)} ]", "bot")
            
            self.bot_orchestrator.start_bot()
        else:
            self.bot_running = False
            if self.bot_orchestrator:
                self.bot_orchestrator.stop_bot()
            self.btn_bot.config(text="▶  START BOT", bg="#22c55e", activebackground="#16a34a")
            self.bot_status_lbl.config(text="● BOT IDLE", fg=FG_DIM)
            
            for w in self.config_widgets:
                w.config(state="normal")
            self.reset_buttons()
            
            self.log_terminal("\n[BOT] Automation Sequence Stopped.", "bot_off")

    def open_debug_json_window(self):
        from src.utils.config import STATIC_ATTACK_FILE
        
        debug_win = tk.Toplevel(self.root)
        debug_win.title("Debug AI JSON Deployment")
        debug_win.geometry("600x500")
        debug_win.configure(bg=BG_DEEP)
        
        lbl = tk.Label(debug_win, text="Paste JSON response from AI:", font=("Courier", 9, "bold"), bg=BG_DEEP, fg=FG_PRIMARY)
        lbl.pack(anchor="w", padx=10, pady=10)
        
        txt = scrolledtext.ScrolledText(debug_win, bg=BG_CARD, fg=FG_GREEN, font=("Courier", 9), height=20)
        txt.pack(fill="both", expand=True, padx=10, pady=5)
        
        try:
            with open(STATIC_ATTACK_FILE, "r") as f:
                saved_json = json.load(f)
            txt.insert(tk.END, json.dumps(saved_json, indent=2))
        except:
            example_json = {
              "available_troops":[
                {"name": "White Dragon", "x": 0.49, "y": 0.90, "quantity": 10},
                {"name": "Clan Castle", "x": 0.55, "y": 0.90, "quantity": 1}
              ],
              "deployment_positions":[
                {"troop_name": "White Dragon", "quantity": 2, "x": 0.5, "y": 0.5},
                {"troop_name": "Clan Castle", "quantity": 1, "x": 0.15, "y": 0.15}
              ],
              "deployment_mode": "human"
            }
            txt.insert(tk.END, json.dumps(example_json, indent=2))
        
        def save_and_execute_manual():
            raw_text = txt.get("1.0", tk.END).strip()
            try:
                data = json.loads(raw_text)
                with open(STATIC_ATTACK_FILE, "w") as f:
                    json.dump(data, f, indent=2)
                self.log_terminal("[DEBUG] Saved to config/static_attack.json & running deployment...", "sys")
                
                def run_sequence():
                    self.log_terminal("[DEBUG] Executing zoom sequence (out -> in -> out)...", "sys")
                    zoom_camera(self.hwnd, ticks=15, direction="out")
                    time.sleep(1.0)
                    zoom_camera(self.hwnd, ticks=15, direction="in")
                    time.sleep(1.0)
                    zoom_camera(self.hwnd, ticks=15, direction="out")
                    time.sleep(1.0)
                    self.attack_manager.execute_deployment_plan(data, True)
                    
                threading.Thread(target=run_sequence, daemon=True).start()
            except Exception as e:
                self.log_terminal(f"[DEBUG] Invalid JSON: {e}", "sys")
                
        def save_only():
            raw_text = txt.get("1.0", tk.END).strip()
            try:
                data = json.loads(raw_text)
                with open(STATIC_ATTACK_FILE, "w") as f:
                    json.dump(data, f, indent=2)
                self.log_terminal("[DEBUG] Saved config/static_attack.json", "sys")
            except Exception as e:
                self.log_terminal(f"[DEBUG] Invalid JSON: {e}", "sys")
                
        btn_frame = tk.Frame(debug_win, bg=BG_DEEP)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        btn_save = tk.Button(btn_frame, text="SAVE (FOR STATIC MODE)", command=save_only, font=("Courier", 9, "bold"), bg=BG_CARD, fg=FG_PRIMARY, cursor="hand2")
        btn_save.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        btn_exec = tk.Button(btn_frame, text="SAVE & EXECUTE NOW", command=save_and_execute_manual, font=("Courier", 9, "bold"), bg=ACCENT_RED, fg=BG_DEEP, cursor="hand2")
        btn_exec.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def reset_buttons(self):
        st = "disabled" if self.bot_running else "normal"
        self.btn_tess.config(state=st, text="TESS")
        self.btn_glm.config(state=st, text="GLM")
        self.btn_rapid.config(state=st, text="RAPID")
        self.btn_upg_tess.config(state=st, text="TESS")
        self.btn_upg_glm.config(state=st, text="GLM")
        self.btn_upg_rapid.config(state=st, text="RAPID")
        if hasattr(self, 'btn_test_wall'):
            self.btn_test_wall.config(state=st, text="TEST AUTOWALL")

    def _preview_loop(self):
        window_name = "OCR LIVE PREVIEW"
        window_created = False
        while True:
            if self.preview_enabled:
                if not window_created:
                    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
                    window_created = True

                display_img = None
                if self.is_scanning_upgrades:
                    if self.current_upgrade_preview is not None:
                        display_img = self.current_upgrade_preview.copy()
                        if len(display_img.shape) == 2:
                            display_img = cv2.cvtColor(display_img, cv2.COLOR_GRAY2BGR)
                        if display_img.shape[0] > 700:
                            sf = 700.0 / display_img.shape[0]
                            display_img = cv2.resize(display_img, (0, 0), fx=sf, fy=sf)
                else:
                    try:
                        frame = self._safe_capture()
                    except ReloadGameException:
                        frame = None
                    except Exception as e:
                        print(f"[PREVIEW] Capture error: {e}")
                        frame = None

                    if frame is not None:
                        on_main = is_main_screen(frame, self.rois["main_screen_i"])
                        keys =["gold", "elixir", "dark_elixir"] if on_main \
                                  else["enemy_gold", "enemy_elixir", "enemy_dark_elixir"]
                        
                        crops =[]
                        for k in keys:
                            crops.append(preprocess_for_ocr(crop_roi(frame, self.rois[k]), k))
                        
                        if on_main:
                            crops.append(preprocess_for_ocr(
                                crop_roi(frame, self.rois["builders_icon"]), "builders_icon"))
                        
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
                            self.preview_enabled = False
                            self.root.after(0, lambda: self.preview_var.set(False))
                            window_created = False
                    except Exception:
                        self.preview_enabled = False
                        self.root.after(0, lambda: self.preview_var.set(False))
                        window_created = False
            else:
                if window_created:
                    cv2.destroyWindow(window_name)
                    window_created = False
                time.sleep(0.2)

    def run_ocr_once(self, engine: str):
        engine = engine.lower()
        start = time.time()
        frame = self._safe_capture()
        if frame is None:
            self.root.after(0, self.log_terminal, "[!] Failed to capture frame.", "sys")
            self.root.after(0, self.reset_buttons)
            return

        raw = self.latest_data.copy()
        on_main_screen = is_main_screen(frame, self.rois["main_screen_i"])

        if on_main_screen:
            self.root.after(0, self.log_terminal,
                            "  - Home Screen detected. Preparing sea background...", "sys")
            
            time.sleep(1.0)
            
            frame = self._safe_capture()
            if frame is None:
                self.root.after(0, self.reset_buttons)
                return

            builders_proc = preprocess_for_ocr(
                crop_roi(frame, self.rois["builders_icon"]), "builders_icon")
            if   engine == "tesseract": raw["builders"] = extract_builders_tesseract(builders_proc)
            elif engine == "glm":       raw["builders"] = extract_builders_glm(builders_proc)
            elif engine == "rapid":     raw["builders"] = extract_builders_rapid(builders_proc)

            self.root.after(0, self.log_terminal,
                            "  ▸ Scanning HOME resources & BUILDERS...", "sys")
            scan_keys =["gold", "elixir", "dark_elixir"]
        else:
            self.root.after(0, self.log_terminal,
                            "  ▸ Battle Screen detected. Scanning ENEMY resources...", "sys")
            scan_keys =["enemy_gold", "enemy_elixir", "enemy_dark_elixir"]

        crops =[preprocess_for_ocr(crop_roi(frame, self.rois[k]), k) for k in scan_keys]
        if engine == "tesseract":
            res = extract_all_tesseract(crops)
            for i, k in enumerate(scan_keys): raw[k] = res[i] if i < len(res) else 0
        elif engine == "glm":
            res = extract_all_glm(crops)
            for i, k in enumerate(scan_keys): raw[k] = res[i] if i < len(res) else 0
        elif engine == "rapid":
            res = extract_all_rapid(crops)
            for i, k in enumerate(scan_keys): raw[k] = res[i] if i < len(res) else 0

        self.latest_data = raw.copy()
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        elapsed = time.time() - start
        self.root.after(0, self.apply_update, raw, ts, elapsed, engine)

    def run_detect_builders(self, engine: str, is_bot=False):
        engine = engine.lower()
        self.is_scanning_upgrades = True
        start = time.time()
        frame = self._safe_capture()

        if frame is None:
            self.root.after(0, self.log_terminal, "  [!] Failed to capture frame.", "sys")
            self.root.after(0, self.reset_buttons)
            self.is_scanning_upgrades = False
            return

        if not is_main_screen(frame, self.rois["main_screen_i"]):
            self.root.after(0, self.log_terminal,
                            "[!] Must be on Home Screen to detect builders.", "sys")
            self.root.after(0, self.reset_buttons)
            self.is_scanning_upgrades = False
            return

        self.root.after(0, self.log_terminal, "  ▸ Preparing sea background...", "sys")
        
        time.sleep(1.0)
        
        zoom_camera(self.hwnd, ticks=15, direction="out")
        time.sleep(0.5)
        
        corner_top_right = {"x": 0.95, "y": 0.05, "w": 0, "h": 0}
        click_relative_roi(self.hwnd, corner_top_right)
        time.sleep(0.5)
        
        click_relative_roi(self.hwnd, self.rois["builders_icon"])
        time.sleep(1.0)
        
        menu_x = self.rois["upgrades_menu"]["x"] + (self.rois["upgrades_menu"]["w"] / 2.0)
        menu_y = self.rois["upgrades_menu"]["y"]
        menu_h = self.rois["upgrades_menu"]["h"]
        pan_camera(self.hwnd, start_rel=(menu_x, menu_y + menu_h * 0.3), end_rel=(menu_x, menu_y + menu_h * 0.8), drag_speed=15)
        time.sleep(0.5)
        
        click_relative_roi(self.hwnd, corner_top_right)
        time.sleep(0.5)
        
        click_relative_roi(self.hwnd, self.rois["builders_icon"])
        self.root.after(0, self.log_terminal, "  ▸ Menu opened. Starting scroll scan...", "sys")
        time.sleep(1.0)

        raw = self.latest_data.copy()
        master, seen, combined =[], set(), ""
        
        empty_scrolls = 0
        MAX_PAGES = 25

        for idx in range(MAX_PAGES):
            if is_bot and not self.bot_running:
                self.root.after(0, self.log_terminal, "  [!] Upgrades scan aborted by user.", "bot_off")
                self.is_scanning_upgrades = False
                self.root.after(0, self.reset_buttons)
                return 

            self.root.after(0, self.log_terminal, f"    - Scanning Page {idx+1}...", "sys")
            time.sleep(0.5)
            frame = self._safe_capture()
            if frame is None: break

            proc = preprocess_for_ocr(crop_roi(frame, self.rois["upgrades_menu"]), "upgrades_menu")
            self.current_upgrade_preview = proc

            if   engine == "tesseract": data = extract_upgrades_tesseract(proc)
            elif engine == "glm":       data = extract_upgrades_glm(proc)
            elif engine == "rapid":     data = extract_upgrades_rapid(proc)

            new = 0
            for item in data.get("upgrades", []):
                uid = f"{item['name']}_{item['cost']}"
                if uid not in seen:
                    seen.add(uid); master.append(item); new += 1

            combined += f"\n--- Page {idx+1} ---\n{data.get('raw_text', '')}"
            
            if new == 0:
                empty_scrolls += 1
                if empty_scrolls >= 2:
                    self.root.after(0, self.log_terminal, "  ✓ End of upgrades list.", "sys")
                    break
                else:
                    self.root.after(0, self.log_terminal, "    ⚠ No new items, trying one more scroll...", "sys")
            else:
                empty_scrolls = 0

            scroll_roi(self.hwnd, self.rois["upgrades_menu"])
            time.sleep(1.7)

        raw["upgrades_info"] = {
            "engine": engine, "total_items_found": len(master),
            "upgrades": master, "raw_text": combined.strip(),
        }
        self.latest_data = raw.copy()
        
        import time as time_module
        self.state_cache["last_upgrade_scan"] = time_module.time()
        
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        elapsed = time.time() - start
        self.root.after(0, self.apply_update, raw, ts, elapsed, engine)
        self.current_upgrade_preview = None
        self.is_scanning_upgrades = False

    def apply_update(self, raw: dict, ts: str, elapsed: float, engine: str):
        self.card_gold.set_value(raw["gold"]);                self.card_gold.push_spark(raw["gold"])
        self.card_elixir.set_value(raw["elixir"]);            self.card_elixir.push_spark(raw["elixir"])
        self.card_dark.set_value(raw["dark_elixir"]);         self.card_dark.push_spark(raw["dark_elixir"])
        self.card_enemy_gold.set_value(raw["enemy_gold"]);    self.card_enemy_gold.push_spark(raw["enemy_gold"])
        self.card_enemy_elixir.set_value(raw["enemy_elixir"]); self.card_enemy_elixir.push_spark(raw["enemy_elixir"])
        self.card_enemy_dark.set_value(raw["enemy_dark_elixir"]); self.card_enemy_dark.push_spark(raw["enemy_dark_elixir"])

        self.badge_builders.set(raw.get("builders", "?/?"))
        upg = raw.get("upgrades_info", {})
        walls = sum(item.get("qty", 1) for item in upg.get("upgrades",[])
                    if "wall" in item.get("name", "").lower())
        self.badge_walls.set(str(walls))

        txt = json.dumps(upg, indent=2) if isinstance(upg, dict) else str(upg)
        self.upgrades_text.delete(1.0, tk.END)
        self.upgrades_text.insert(tk.END, txt)
        
        self._render_walls_ui()

        self.log_rich(ts, raw)
        self.log_terminal(f"  ✓ {engine.upper()} scan complete in {elapsed:.2f}s\n", "sys")
        self.reset_buttons()

    def _save_upgrades_json(self):
        content = self.upgrades_text.get(1.0, tk.END).strip()
        try:
            parsed = json.loads(content)
            self.latest_data["upgrades_info"] = parsed
            self.state_cache["upgrades_info"] = parsed
            self.save_state()
            
            walls = sum(item.get("qty", 1) for item in parsed.get("upgrades", []) if "wall" in item.get("name", "").lower())
            self.badge_walls.set(str(walls))
            
            self._render_walls_ui()
            
            self.log_terminal("[SYS] Upgrades data manually updated and saved.", "sys")
        except Exception as e:
            self.log_terminal(f"[ERROR] Invalid JSON format: {e}", "bot_off")

    def _render_walls_ui(self):
        for widget in self.walls_container.winfo_children():
            widget.destroy()
            
        upg_data = self.latest_data.get("upgrades_info", {})
        walls =[item for item in upg_data.get("upgrades", []) if "wall" in item.get("name", "").lower()]
        
        if not walls:
            tk.Label(self.walls_container, text="No walls detected.", 
                     bg=BG_DEEP, fg=FG_DIM, font=("Courier", 8)).pack(anchor="w", pady=5)
            return

        self.wall_entries =[]
        for idx, wall in enumerate(upg_data.get("upgrades", [])):
            if "wall" not in wall.get("name", "").lower():
                continue
                
            row = tk.Frame(self.walls_container, bg=BG_DEEP)
            row.pack(fill="x", pady=2)
            
            qty = wall.get("qty", 1)
            name_text = f"Wall x{qty}"
            tk.Label(row, text=name_text, bg=BG_DEEP, fg=FG_PRIMARY, 
                     font=("Courier", 8, "bold"), width=12, anchor="w").pack(side="left")
            
            cost_var = tk.StringVar(value=str(wall.get("cost", 0)))
            entry = tk.Entry(row, textvariable=cost_var, bg=BG_PANEL, fg=FG_SECONDARY,
                             font=("Courier", 8), width=15, relief="flat",
                             highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT_GOLD)
            entry.pack(side="left", padx=5)
            
            self.wall_entries.append({"index": idx, "var": cost_var})
            
        btn_save_walls = make_btn(self.walls_container, "SAVE WALL COSTS",
                                  self._save_wall_targets_ui,
                                  "#22c55e", small=True)
        btn_save_walls.pack(anchor="e", pady=(5, 0))

    def _save_wall_targets_ui(self):
        try:
            upgrades = self.latest_data.get("upgrades_info", {}).get("upgrades", [])
            for entry_data in self.wall_entries:
                idx = entry_data["index"]
                val = entry_data["var"].get().replace(" ", "").replace(",", "")
                upgrades[idx]["cost"] = int(val)
                
            self.latest_data["upgrades_info"]["upgrades"] = upgrades
            self.state_cache["upgrades_info"] = self.latest_data["upgrades_info"]
            self.save_state()
            self.log_terminal("[SYS] Wall targets saved.", "sys")
            
            txt = json.dumps(self.latest_data["upgrades_info"], indent=2)
            self.upgrades_text.delete(1.0, tk.END)
            self.upgrades_text.insert(tk.END, txt)
            
        except Exception as e:
            self.log_terminal(f"[ERROR] Invalid wall cost: {e}", "bot_off")

    def log_rich(self, timestamp: str, raw: dict):
        self.terminal.configure(state="normal")
        self.terminal.insert(tk.END, f"[{timestamp}] ", "time")
        self.terminal.insert(tk.END, "H: ", "sys")
        self.terminal.insert(tk.END, f"{raw['gold']:>9,} ", "gold")
        self.terminal.insert(tk.END, f"{raw['elixir']:>9,} ", "elx")
        self.terminal.insert(tk.END, f"{raw['dark_elixir']:>7,} ", "dark")
        self.terminal.insert(tk.END, "| E: ", "sys")
        self.terminal.insert(tk.END, f"{raw['enemy_gold']:>8,} ", "gold")
        self.terminal.insert(tk.END, f"{raw['enemy_elixir']:>8,} ", "elx")
        self.terminal.insert(tk.END, f"{raw['enemy_dark_elixir']:>6,}\n", "dark")
        self.terminal.see(tk.END)
        self.terminal.configure(state="disabled")

    def log_terminal(self, message: str, tag: str = ""):
        self.terminal.configure(state="normal")
        self.terminal.insert(tk.END, message + "\n", tag if tag else None)
        self.terminal.see(tk.END)
        self.terminal.configure(state="disabled")

    def on_closing(self):
        self.log_terminal("[SYS] Saving configuration before exit...", "sys")
        self.save_state()
        self.root.destroy()