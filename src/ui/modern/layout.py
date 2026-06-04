"""
Layout sections and helpers for modern modular UI
"""

import tkinter as tk
try:
    from .theme import (
        BG_PRIMARY, BG_SECONDARY, TEXT_PRIMARY, TEXT_SECONDARY,
        ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_GOLD, ACCENT_ELIXIR, ACCENT_DARK,
        ACCENT_BUILDER, SPACING_LG, SPACING_MD, FONT_SIZE_HEADING1,
        FONT_FAMILY_PRIMARY, FONT_WEIGHT_BOLD
    )
    from .components import Card, MetricCard, Panel, Button, Grid, ScrollableFrame
except ImportError:
    from theme import (
        BG_PRIMARY, BG_SECONDARY, TEXT_PRIMARY, TEXT_SECONDARY,
        ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_GOLD, ACCENT_ELIXIR, ACCENT_DARK,
        ACCENT_BUILDER, SPACING_LG, SPACING_MD, FONT_SIZE_HEADING1,
        FONT_FAMILY_PRIMARY, FONT_WEIGHT_BOLD
    )
    from components import Card, MetricCard, Panel, Button, Grid, ScrollableFrame


# ============================================================================
# SECTION: HEADER
# ============================================================================

class HeaderSection(tk.Frame):
    """Application header with title and controls."""
    
    def __init__(self, parent, title="AutoWalls", **kwargs):
        super().__init__(parent, bg=BG_PRIMARY, **kwargs)
        
        # Title
        tk.Label(
            self, text=title,
            font=(FONT_FAMILY_PRIMARY, FONT_SIZE_HEADING1, FONT_WEIGHT_BOLD),
            bg=BG_PRIMARY, fg=TEXT_PRIMARY
        ).pack(side="left", padx=SPACING_LG, pady=SPACING_LG)
        
        # Spacer
        tk.Frame(self, bg=BG_PRIMARY).pack(side="left", expand=True)


# ============================================================================
# SECTION: METRICS/RESOURCES GRID
# ============================================================================

class MetricsSection(tk.Frame):
    """Display resource metrics in a grid layout."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_PRIMARY, **kwargs)
        
        # Title
        tk.Label(
            self, text="RESOURCES",
            font=(FONT_FAMILY_PRIMARY, 12, FONT_WEIGHT_BOLD),
            bg=BG_PRIMARY, fg=TEXT_SECONDARY
        ).pack(fill="x", padx=SPACING_LG, pady=(SPACING_LG, SPACING_MD))
        
        # Grid of metrics
        grid_frame = tk.Frame(self, bg=BG_PRIMARY)
        grid_frame.pack(fill="both", expand=True, padx=SPACING_LG, pady=(0, SPACING_LG))
        
        # Configure grid columns
        for i in range(6):
            grid_frame.columnconfigure(i, weight=1)
        
        self.metrics = {}
        
        # Home Resources
        self.metrics['gold'] = MetricCard(
            grid_frame, "Home Gold", "💰", ACCENT_GOLD
        )
        self.metrics['gold'].grid(row=0, column=0, padx=SPACING_MD, pady=SPACING_MD, sticky="nsew")
        
        self.metrics['elixir'] = MetricCard(
            grid_frame, "Home Elixir", "⚡", ACCENT_ELIXIR
        )
        self.metrics['elixir'].grid(row=0, column=1, padx=SPACING_MD, pady=SPACING_MD, sticky="nsew")
        
        self.metrics['dark'] = MetricCard(
            grid_frame, "Home Dark", "🌑", ACCENT_DARK
        )
        self.metrics['dark'].grid(row=0, column=2, padx=SPACING_MD, pady=SPACING_MD, sticky="nsew")
        
        # Enemy Resources
        self.metrics['enemy_gold'] = MetricCard(
            grid_frame, "Enemy Gold", "💰", ACCENT_GOLD
        )
        self.metrics['enemy_gold'].grid(row=0, column=3, padx=SPACING_MD, pady=SPACING_MD, sticky="nsew")
        
        self.metrics['enemy_elixir'] = MetricCard(
            grid_frame, "Enemy Elixir", "⚡", ACCENT_ELIXIR
        )
        self.metrics['enemy_elixir'].grid(row=0, column=4, padx=SPACING_MD, pady=SPACING_MD, sticky="nsew")
        
        self.metrics['enemy_dark'] = MetricCard(
            grid_frame, "Enemy Dark", "🌑", ACCENT_DARK
        )
        self.metrics['enemy_dark'].grid(row=0, column=5, padx=SPACING_MD, pady=SPACING_MD, sticky="nsew")


# ============================================================================
# SECTION: STATUS & CONTROLS
# ============================================================================

class ControlsSection(tk.Frame):
    """Bot controls and status displays."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_PRIMARY, **kwargs)
        
        # Title
        tk.Label(
            self, text="CONTROLS",
            font=(FONT_FAMILY_PRIMARY, 12, FONT_WEIGHT_BOLD),
            bg=BG_PRIMARY, fg=TEXT_SECONDARY
        ).pack(fill="x", padx=SPACING_LG, pady=(SPACING_LG, SPACING_MD))
        
        # Buttons frame
        buttons_frame = tk.Frame(self, bg=BG_PRIMARY)
        buttons_frame.pack(fill="x", padx=SPACING_LG, pady=(0, SPACING_LG))
        
        self.btn_start = Button(
            buttons_frame, "START BOT",
            variant="success", size="lg"
        )
        self.btn_start.pack(side="left", padx=(0, SPACING_MD))
        
        self.btn_stop = Button(
            buttons_frame, "STOP BOT",
            variant="danger", size="lg"
        )
        self.btn_stop.pack(side="left", padx=(0, SPACING_MD))
        
        self.btn_calibrate = Button(
            buttons_frame, "CALIBRATE",
            variant="secondary", size="md"
        )
        self.btn_calibrate.pack(side="left", padx=(0, SPACING_MD))


# ============================================================================
# SECTION: CONFIGURATION PANEL
# ============================================================================

class ConfigSection(tk.Frame):
    """Configuration and settings panel."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_PRIMARY, **kwargs)
        
        panel = Panel(self, title="CONFIGURATION", bg=BG_SECONDARY, fill="both", expand=True)
        panel.pack(fill="both", expand=True, padx=SPACING_LG, pady=(SPACING_LG, SPACING_LG))
        
        # Create scrollable content area
        self.scroll = ScrollableFrame(panel, bg=BG_SECONDARY)
        self.scroll.pack(fill="both", expand=True, padx=SPACING_LG, pady=SPACING_LG)
        
        self.config_widgets = []
    
    def add_config_widget(self, label, widget):
        """Add a configuration widget."""
        row = tk.Frame(self.scroll.inner, bg=BG_SECONDARY)
        row.pack(fill="x", pady=SPACING_MD)
        
        tk.Label(
            row, text=label,
            font=(FONT_FAMILY_PRIMARY, 10),
            bg=BG_SECONDARY, fg=TEXT_PRIMARY
        ).pack(side="left", padx=(0, SPACING_MD))
        
        widget.pack(side="left")
        self.config_widgets.append(widget)


# ============================================================================
# SECTION: UPGRADES/WALLS
# ============================================================================

class UpgradesSection(tk.Frame):
    """Upgrades and walls information display."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_PRIMARY, **kwargs)
        
        # Title
        tk.Label(
            self, text="UPGRADES & WALLS",
            font=(FONT_FAMILY_PRIMARY, 12, FONT_WEIGHT_BOLD),
            bg=BG_PRIMARY, fg=TEXT_SECONDARY
        ).pack(fill="x", padx=SPACING_LG, pady=(SPACING_LG, SPACING_MD))
        
        # Content area
        content = tk.Frame(self, bg=BG_PRIMARY)
        content.pack(fill="both", expand=True, padx=SPACING_LG, pady=(0, SPACING_LG))
        
        # Scrollable wall entries
        self.scroll = ScrollableFrame(content, bg=BG_PRIMARY)
        self.scroll.pack(side="left", fill="both", expand=True, padx=(0, SPACING_MD))
        
        # Text display (for JSON/details)
        self.text_display = tk.Text(
            content, font=("Courier", 9),
            bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            relief="solid", bd=1, highlightthickness=0
        )
        self.text_display.pack(side="right", fill="both", expand=True)


# ============================================================================
# SECTION: TERMINAL/LOGS
# ============================================================================

class TerminalSection(tk.Frame):
    """Terminal/log output area."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_PRIMARY, **kwargs)
        
        # Title
        tk.Label(
            self, text="TERMINAL OUTPUT",
            font=(FONT_FAMILY_PRIMARY, 12, FONT_WEIGHT_BOLD),
            bg=BG_PRIMARY, fg=TEXT_SECONDARY
        ).pack(fill="x", padx=SPACING_LG, pady=(SPACING_LG, SPACING_MD))
        
        # Terminal text widget
        self.terminal = tk.Text(
            self, font=("Courier", 9),
            bg="#0a0e27", fg="#e2e8f0",
            relief="solid", bd=1, highlightthickness=0,
            height=10
        )
        self.terminal.pack(fill="both", expand=True, padx=SPACING_LG, pady=(0, SPACING_LG))
        
        # Configure tags for colored output
        self.terminal.tag_config("sys", foreground="#06b6d4")
        self.terminal.tag_config("bot_on", foreground="#10b981")
        self.terminal.tag_config("bot_off", foreground="#ef4444")
        self.terminal.tag_config("gold", foreground="#fbbf24")
        self.terminal.tag_config("elx", foreground="#8b5cf6")
        self.terminal.tag_config("dark", foreground="#06b6d4")
        self.terminal.tag_config("time", foreground="#94a3b8")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_divider(parent, bg=BG_PRIMARY):
    """Create a visual divider."""
    return tk.Frame(parent, bg="#e5e7eb", height=1)
