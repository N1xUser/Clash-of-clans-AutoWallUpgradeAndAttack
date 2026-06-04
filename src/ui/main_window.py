import time
import tkinter as tk
import threading

from src.ui.widgets import BG_DEEP, MIN_W, MIN_H, WINDOW_W, WINDOW_H, FG_DIM
from src.core.bot import BotOrchestrator
from src.core.attack import AttackManager
from src.core.upgrade import UpgradeManager
from src.core.builder import BuilderScanner

from src.ui.panels.header import build_header
from src.ui.panels.home import build_home_col
from src.ui.panels.enemy import build_enemy_col
from src.ui.panels.config import build_config_col
from src.ui.panels.terminal import build_terminal

from src.core.state_wrapper import SimpleStateManager
from src.ui.controllers.vision_controller import update_mouse_coords, anti_afk_loop, safe_capture, preview_loop
from src.ui.controllers.ocr_controller import run_ocr_once, run_detect_builders, apply_update
from src.ui.controllers.bot_controller import on_start_bot, run_test_autowall
from src.ui.controllers.walls_controller import save_upgrades_json, render_walls_ui, save_wall_targets_ui
from src.ui.controllers.debug_controller import open_debug_json_window
from src.ui.controllers.config_controller import load_state, save_state

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
        self.config_widgets = []
        
        ai_config = {
            "api_key": "",
            "model": "gemini-2.0-flash-exp"
        }
        
        config_getters = {
            "get_target_info": self._get_target_info_string,
            "get_auto_reinforce": lambda: self.auto_reinforce_var.get() if hasattr(self, 'auto_reinforce_var') else False,
            "get_clan_donate": lambda: self.clan_donate_var.get() if hasattr(self, 'clan_donate_var') else False,
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
            capture_callback=lambda: safe_capture(self),
            bot_running_callback=lambda: self.bot_running,
            config_getters=config_getters
        )
        
        self.builder_scanner = BuilderScanner(hwnd, rois)
        
        ui_callbacks = {
            "log_terminal": self.log_terminal,
            "log_rich": self.log_rich,
            "apply_update": lambda raw, ts, el, eng: apply_update(self, raw, ts, el, eng),
            "reset_buttons": self.reset_buttons,
            "safe_capture": lambda: safe_capture(self),
            "get_bot_running": lambda: self.bot_running,
            "set_bot_running": self._set_bot_running,
            "reset_ui": self.reset_buttons,
            "trigger_cache_update": lambda: None,
            "run_ocr_once": lambda engine: run_ocr_once(self, engine),
            "scan_upgrades": lambda is_bot=False: run_detect_builders(self, self.engine_upg_var.get(), is_bot=is_bot),
            "refresh_upgrades_ui": self._refresh_upgrades_display,
            "set_scanning_upgrades": lambda val: setattr(self, "is_scanning_upgrades", val),
            "update_upgrade_preview": lambda proc: setattr(self, "current_upgrade_preview", proc),
            "update_gold": lambda val: self.card_gold.set_value(val) if hasattr(self, 'card_gold') else None,
            "update_elixir": lambda val: self.card_elixir.set_value(val) if hasattr(self, 'card_elixir') else None,
            "stop_bot": lambda: self.root.after(0, lambda: on_start_bot(self)) if self.bot_running else None,
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
        load_state(self)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        threading.Thread(target=preview_loop, args=(self,), daemon=True).start()
        threading.Thread(target=anti_afk_loop, args=(self,), daemon=True).start()
        update_mouse_coords(self)
        self.log_terminal("  ▸ Ready. Select an engine to scan or Start Bot.", "sys")

    def _get_config_getters(self):
        getters = {}
        def make_getter(attr):
            return lambda: getattr(self, attr, tk.StringVar()).get()
        
        for attr in['engine_home_var', 'engine_upg_var', 'engine_enemy_var', 'engine_wall_var',
                     'use_tgt_gold', 'use_tgt_elx', 'use_tgt_goel', 'use_tgt_dark',
                     'tgt_gold_var', 'tgt_elx_var', 'tgt_goel_var', 'tgt_dark_var',
                     'ai_mode_var', 'ai_model_var', 'gemini_api_var',
                     'auto_reinforce_var', 'clan_donate_var', 'anti_afk_var', 'auto_wall_var']:
            if hasattr(self, attr):
                getters[attr] = make_getter(attr)
        return getters

    def _set_bot_running(self, value):
        self.bot_running = value

    # Wrapper methods for the panels
    def save_state(self):
        save_state(self)

    def _on_transparency_change(self, val):
        alpha = float(val) / 100.0
        self.root.attributes("-alpha", alpha)
        if hasattr(self, 'trans_lbl'):
            self.trans_lbl.config(text=f"{int(float(val))}%")

    def on_update_click(self, engine: str):
        for b in (self.btn_tess, self.btn_glm, self.btn_rapid):
            b.config(state="disabled", text="…")
        self.log_terminal(f"  ▸ Capturing with {engine.upper()}...", "sys")
        threading.Thread(target=run_ocr_once, args=(self, engine,), daemon=True).start()

    def on_detect_builders(self, engine: str):
        for b in (self.btn_upg_tess, self.btn_upg_glm, self.btn_upg_rapid):
            b.config(state="disabled", text="…")
        self.log_terminal(f"  ▸ Opening Upgrades Menu ({engine.upper()})...", "sys")
        threading.Thread(target=run_detect_builders, args=(self, engine,), daemon=True).start()

    def on_test_autowall(self):
        self.log_terminal("\n[TEST] Starting AutoWall Test...", "bot")
        self.btn_test_wall.config(state="disabled", text="TESTING...")
        threading.Thread(target=run_test_autowall, args=(self,), daemon=True).start()

    def on_test_donate(self):
        self.log_terminal("\n[TEST] Starting Donation Test...", "bot")
        self.btn_test_donate.config(state="disabled", text="TESTING...")
        threading.Thread(target=self._run_test_donate, daemon=True).start()

    def _run_test_donate(self):
        from src.core.donation import run_donation_cycle

        def log_fn(msg, tag):
            self.root.after(0, self.log_terminal, msg, tag)

        donated = run_donation_cycle(
            self.hwnd,
            lambda: safe_capture(self),
            log_fn,
            skip_detection=True,
            save_screenshots=self.debug_ss_var.get() if hasattr(self, 'debug_ss_var') else True
        )

        if donated > 0:
            log_fn(f"[TEST] ✓ Donation test complete. Processed {donated} request(s).", "bot")
        else:
            log_fn("[TEST] No donation requests found or processed.", "sys")

        self.root.after(0, lambda: self.btn_test_donate.config(state="normal", text="TEST DONATE"))

    def on_start_bot(self):
        on_start_bot(self)

    def open_debug_json_window(self):
        open_debug_json_window(self)

    def _save_upgrades_json(self):
        save_upgrades_json(self)

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)

        build_header(self, self.root)
        
        from src.ui.widgets import ScrollableFrame
        self._scroll_body = ScrollableFrame(self.root, bg=BG_DEEP)
        self._scroll_body.grid(row=1, column=0, sticky="nsew")

        body = self._scroll_body.inner
        body.columnconfigure(0, weight=1, uniform="col")
        body.columnconfigure(1, weight=1, uniform="col")
        body.columnconfigure(2, weight=1, uniform="col")

        build_home_col(self, body)
        build_enemy_col(self, body)
        build_config_col(self, body)
        
        build_terminal(self, self.root)

    def _hsep(self, parent):
        from src.ui.widgets import BORDER
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=6)

    def _col_label(self, parent, text, color=FG_DIM):
        tk.Label(parent, text=text, font=("Courier", 8, "bold"),
                 bg=BG_DEEP, fg=color).pack(anchor="w", pady=(0, 5))

    def _style_dropdown(self, opt, width=8):
        from src.ui.widgets import BG_CARD2, FG_PRIMARY, BORDER_BRIGHT, BORDER
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

    def _clear_terminal(self):
        self.terminal.configure(state="normal")
        self.terminal.delete(1.0, tk.END)
        self.terminal.configure(state="disabled")

    def _on_preview_toggle(self):
        self.preview_enabled = self.preview_var.get()

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
        if hasattr(self, 'btn_test_donate'):
            self.btn_test_donate.config(state=st, text="TEST DONATE")

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
        
        import json
        txt = json.dumps(upg, indent=2) if isinstance(upg, dict) else str(upg)
        self.upgrades_text.configure(state="normal")
        self.upgrades_text.delete(1.0, tk.END)
        self.upgrades_text.insert(tk.END, txt)
        self.upgrades_text.configure(state="disabled")

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
        save_state(self)
        self.root.destroy()