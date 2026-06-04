"""
Modern Modular AutoWalls UI
Uses theme, components, and layout modules
"""

import tkinter as tk
import time
import threading
try:
    from .theme import (
        WINDOW_W, WINDOW_H, MIN_W, MIN_H,
        BG_PRIMARY, BG_SECONDARY, TEXT_PRIMARY, ACCENT_PRIMARY,
        SPACING_LG, SPACING_MD
    )
    from .components import (
        Button, MetricCard, StatBadge, Panel, ScrollableFrame,
        PulseDot, Card
    )
    from .layout import (
        HeaderSection, MetricsSection, ControlsSection,
        ConfigSection, UpgradesSection, TerminalSection,
        create_divider
    )
except ImportError:
    from theme import (
        WINDOW_W, WINDOW_H, MIN_W, MIN_H,
        BG_PRIMARY, BG_SECONDARY, TEXT_PRIMARY, ACCENT_PRIMARY,
        SPACING_LG, SPACING_MD
    )
    from components import (
        Button, MetricCard, StatBadge, Panel, ScrollableFrame,
        PulseDot, Card
    )
    from layout import (
        HeaderSection, MetricsSection, ControlsSection,
        ConfigSection, UpgradesSection, TerminalSection,
        create_divider
    )


class ModernAutoWallsUI:
    """Modern modular UI for AutoWalls bot."""
    
    def __init__(self, root, hwnd, rois):
        """
        Initialize the modern AutoWalls UI.
        
        Args:
            root: Tkinter root window
            hwnd: Window handle for the target application
            rois: Region of interest configuration dictionary
        """
        self.root = root
        self.hwnd = hwnd
        self.rois = rois
        
        # Configure root window
        self.root.title("AutoWalls · Modern Control Panel")
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.configure(bg=BG_PRIMARY)
        self.root.resizable(True, True)
        self.root.minsize(MIN_W, MIN_H)
        
        # State variables
        self.bot_running = False
        self.latest_data = {
            "gold": 0, "elixir": 0, "dark_elixir": 0,
            "enemy_gold": 0, "enemy_elixir": 0, "enemy_dark_elixir": 0,
            "builders": "?/?",
            "upgrades_info": {"status": "Pending Scan..."},
        }
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Construct the entire UI."""
        
        # ============================================================
        # TOP: Header
        # ============================================================
        header = HeaderSection(self.root, title="AutoWalls Control Panel")
        header.pack(fill="x", bg=BG_PRIMARY)
        
        # Divider
        create_divider(self.root).pack(fill="x", pady=(SPACING_MD, 0))
        
        # ============================================================
        # MAIN: Scrollable content
        # ============================================================
        main_scroll = ScrollableFrame(self.root, bg=BG_PRIMARY)
        main_scroll.pack(fill="both", expand=True, padx=SPACING_LG, pady=SPACING_LG)
        
        # Metrics section
        self.metrics_section = MetricsSection(main_scroll.inner)
        self.metrics_section.pack(fill="x", pady=(0, SPACING_LG))
        
        # Controls section
        self.controls_section = ControlsSection(main_scroll.inner)
        self.controls_section.pack(fill="x", pady=(0, SPACING_LG))
        
        # Configuration section
        self.config_section = ConfigSection(main_scroll.inner)
        self.config_section.pack(fill="x", pady=(0, SPACING_LG))
        
        # Upgrades section
        self.upgrades_section = UpgradesSection(main_scroll.inner)
        self.upgrades_section.pack(fill="x", pady=(0, SPACING_LG))
        
        # Terminal section
        self.terminal_section = TerminalSection(main_scroll.inner)
        self.terminal_section.pack(fill="both", expand=True)
        
        # ============================================================
        # Expose key components for easy access
        # ============================================================
        self.card_gold = self.metrics_section.metrics['gold']
        self.card_elixir = self.metrics_section.metrics['elixir']
        self.card_dark = self.metrics_section.metrics['dark']
        self.card_enemy_gold = self.metrics_section.metrics['enemy_gold']
        self.card_enemy_elixir = self.metrics_section.metrics['enemy_elixir']
        self.card_enemy_dark = self.metrics_section.metrics['enemy_dark']
        
        self.terminal = self.terminal_section.terminal
        self.upgrades_text = self.upgrades_section.text_display
        
        self.btn_start = self.controls_section.btn_start
        self.btn_stop = self.controls_section.btn_stop
        self.btn_calibrate = self.controls_section.btn_calibrate
    
    # ====================================================================
    # LOGGING & OUTPUT
    # ====================================================================
    
    def log_terminal(self, message: str, tag: str = ""):
        """Log message to terminal with optional color tag."""
        self.terminal.configure(state="normal")
        self.terminal.insert(tk.END, message + "\n", tag if tag else None)
        self.terminal.see(tk.END)
        self.terminal.configure(state="disabled")
    
    def log_rich(self, timestamp: str, raw: dict):
        """Log formatted resource data with colors."""
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
    
    def apply_update(self, raw: dict, ts: str, elapsed: float, engine: str):
        """Apply data updates to UI components."""
        # Update metric cards
        self.card_gold.set_value(raw["gold"])
        self.card_gold.push_spark(raw["gold"])
        
        self.card_elixir.set_value(raw["elixir"])
        self.card_elixir.push_spark(raw["elixir"])
        
        self.card_dark.set_value(raw["dark_elixir"])
        self.card_dark.push_spark(raw["dark_elixir"])
        
        self.card_enemy_gold.set_value(raw["enemy_gold"])
        self.card_enemy_gold.push_spark(raw["enemy_gold"])
        
        self.card_enemy_elixir.set_value(raw["enemy_elixir"])
        self.card_enemy_elixir.push_spark(raw["enemy_elixir"])
        
        self.card_enemy_dark.set_value(raw["enemy_dark_elixir"])
        self.card_enemy_dark.push_spark(raw["enemy_dark_elixir"])
        
        # Log completion
        self.log_rich(ts, raw)
        self.log_terminal(f"  ✓ {engine.upper()} scan complete in {elapsed:.2f}s\n", "sys")
    
    def reset_buttons(self):
        """Reset button states."""
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="normal")
        self.btn_calibrate.config(state="normal")
    
    def disable_buttons(self):
        """Disable all control buttons."""
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="disabled")
        self.btn_calibrate.config(state="disabled")
    
    def update_metric(self, metric_key: str, value: int):
        """Update a metric value."""
        if metric_key in self.metrics_section.metrics:
            card = self.metrics_section.metrics[metric_key]
            card.set_value(value)
            card.push_spark(value)
    
    def show_status(self, message: str, status: str = "sys"):
        """Display a status message."""
        self.log_terminal(message, status)


# ============================================================================
# DEMO: Simple test window
# ============================================================================

def demo():
    """Simple demo of the modern UI."""
    root = tk.Tk()
    ui = ModernAutoWallsUI(root, None, {})
    
    # Demo: Simulate data updates
    def update_demo():
        import random
        gold = random.randint(1000000, 5000000)
        elixir = random.randint(800000, 4000000)
        dark = random.randint(50000, 200000)
        
        ui.update_metric("gold", gold)
        ui.update_metric("elixir", elixir)
        ui.update_metric("dark", dark)
        ui.update_metric("enemy_gold", random.randint(2000000, 6000000))
        ui.update_metric("enemy_elixir", random.randint(1500000, 5000000))
        ui.update_metric("enemy_dark", random.randint(100000, 300000))
        
        ui.log_terminal(f"[{time.strftime('%H:%M:%S')}] Demo update", "sys")
    
    # Button bindings
    ui.btn_start.config(command=lambda: ui.log_terminal("Bot started!", "bot_on"))
    ui.btn_stop.config(command=lambda: ui.log_terminal("Bot stopped.", "bot_off"))
    ui.btn_calibrate.config(command=update_demo)
    
    # Demo log
    ui.log_terminal("Welcome to AutoWalls Modern UI", "sys")
    ui.log_terminal("Click CALIBRATE to see demo updates", "sys")
    
    root.mainloop()


if __name__ == "__main__":
    demo()
