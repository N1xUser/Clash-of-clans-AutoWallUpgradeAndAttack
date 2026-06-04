"""
Modular UI Components for AutoWalls
Modern design components following MODE Design System principles
"""

import tkinter as tk
import math
try:
    from .theme import (
        BG_PRIMARY, BG_SECONDARY, BG_TERTIARY, BG_CARD, BG_ACCENT,
        TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, TEXT_INVERSE,
        ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_WARNING,
        ACCENT_DANGER, ACCENT_INFO, ACCENT_GOLD, ACCENT_ELIXIR, ACCENT_DARK,
        ACCENT_BUILDER, BORDER_LIGHT, BORDER_DEFAULT, BORDER_FOCUS,
        SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
        BORDER_RADIUS_SM, BORDER_RADIUS_MD, BORDER_RADIUS_LG,
        FONT_FAMILY_PRIMARY, FONT_FAMILY_MONO,
        FONT_SIZE_LABEL, FONT_SIZE_BODY, FONT_SIZE_BODY_SM, FONT_SIZE_SUBTITLE,
        FONT_SIZE_HEADING2, FONT_SIZE_HEADING1,
        FONT_WEIGHT_NORMAL, FONT_WEIGHT_MEDIUM, FONT_WEIGHT_BOLD,
        hex_to_rgb, interpolate_color, lighten, darken
    )
except ImportError:
    from theme import (
        BG_PRIMARY, BG_SECONDARY, BG_TERTIARY, BG_CARD, BG_ACCENT,
        TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, TEXT_INVERSE,
        ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_WARNING,
        ACCENT_DANGER, ACCENT_INFO, ACCENT_GOLD, ACCENT_ELIXIR, ACCENT_DARK,
        ACCENT_BUILDER, BORDER_LIGHT, BORDER_DEFAULT, BORDER_FOCUS,
        SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
        BORDER_RADIUS_SM, BORDER_RADIUS_MD, BORDER_RADIUS_LG,
        FONT_FAMILY_PRIMARY, FONT_FAMILY_MONO,
        FONT_SIZE_LABEL, FONT_SIZE_BODY, FONT_SIZE_BODY_SM, FONT_SIZE_SUBTITLE,
        FONT_SIZE_HEADING2, FONT_SIZE_HEADING1,
        FONT_WEIGHT_NORMAL, FONT_WEIGHT_MEDIUM, FONT_WEIGHT_BOLD,
        hex_to_rgb, interpolate_color, lighten, darken
    )


# ============================================================================
# BUTTON COMPONENTS
# ============================================================================

class Button(tk.Button):
    """Modern button component with multiple variants."""
    
    def __init__(self, parent, text, command=None, variant="primary", size="md", **kwargs):
        """
        Args:
            variant: "primary", "secondary", "success", "danger", "outline"
            size: "sm", "md", "lg"
        """
        self.variant = variant
        self.size = size
        
        # Variant colors
        variant_colors = {
            "primary": (ACCENT_PRIMARY, TEXT_INVERSE, lighten(ACCENT_PRIMARY, 0.1)),
            "secondary": (BG_SECONDARY, TEXT_PRIMARY, BG_TERTIARY),
            "success": (ACCENT_SUCCESS, TEXT_INVERSE, lighten(ACCENT_SUCCESS, 0.1)),
            "danger": (ACCENT_DANGER, TEXT_INVERSE, lighten(ACCENT_DANGER, 0.1)),
            "outline": (BG_PRIMARY, ACCENT_PRIMARY, BG_SECONDARY),
        }
        
        bg_color, fg_color, active_bg = variant_colors.get(variant, variant_colors["primary"])
        
        # Size settings
        size_settings = {
            "sm": (9, (6, 8), (4, 8)),
            "md": (11, (8, 12), (6, 12)),
            "lg": (12, (12, 16), (8, 16)),
        }
        
        font_size, (padx, pady), (active_px, active_py) = size_settings.get(size, size_settings["md"])
        
        super().__init__(
            parent, text=text, command=command,
            font=(FONT_FAMILY_MONO, font_size, FONT_WEIGHT_BOLD),
            bg=bg_color, fg=fg_color,
            activebackground=active_bg, activeforeground=fg_color,
            relief="flat", padx=padx, pady=pady,
            cursor="hand2", highlightthickness=0,
            **kwargs
        )
        
        self.bind("<Enter>", self._on_hover)
        self.bind("<Leave>", self._on_leave)
    
    def _on_hover(self, _):
        if self.variant == "outline":
            self.config(bg=BG_SECONDARY)
        else:
            self.config(relief="raised")
    
    def _on_leave(self, _):
        if self.variant == "outline":
            self.config(bg=BG_PRIMARY)
        else:
            self.config(relief="flat")


# ============================================================================
# CARD COMPONENTS
# ============================================================================

class Card(tk.Frame):
    """Modern card component with shadow and border."""
    
    def __init__(self, parent, title="", **kwargs):
        super().__init__(parent, bg=BG_CARD, **kwargs)
        
        self.config(
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
            highlightcolor=BORDER_FOCUS,
        )
        
        if title:
            header = tk.Label(
                self, text=title,
                font=(FONT_FAMILY_PRIMARY, FONT_SIZE_SUBTITLE, FONT_WEIGHT_BOLD),
                bg=BG_CARD, fg=TEXT_PRIMARY
            )
            header.pack(fill="x", padx=SPACING_LG, pady=(SPACING_LG, SPACING_SM))


class MetricCard(tk.Frame):
    """Card component for displaying metrics with value and sparkline."""
    
    def __init__(self, parent, label, icon, accent_color=ACCENT_PRIMARY, **kwargs):
        super().__init__(parent, bg=BG_CARD, **kwargs)
        
        self.config(
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
        )
        
        # Header with icon and label
        header = tk.Frame(self, bg=BG_CARD)
        header.pack(fill="x", padx=SPACING_LG, pady=(SPACING_LG, SPACING_SM))
        
        tk.Label(
            header, text=icon,
            font=("Segoe UI Emoji", 14),
            bg=BG_CARD, fg=accent_color
        ).pack(side="left", padx=(0, SPACING_SM))
        
        tk.Label(
            header, text=label.upper(),
            font=(FONT_FAMILY_MONO, FONT_SIZE_LABEL_SM, FONT_WEIGHT_BOLD),
            bg=BG_CARD, fg=TEXT_TERTIARY
        ).pack(side="left")
        
        # Value display
        self.value_var = tk.StringVar(value="0")
        tk.Label(
            self, textvariable=self.value_var,
            font=(FONT_FAMILY_MONO, FONT_SIZE_HEADING2, FONT_WEIGHT_BOLD),
            bg=BG_CARD, fg=accent_color
        ).pack(fill="x", padx=SPACING_LG)
        
        # Sparkline
        self.sparkline = Sparkline(self, accent_color, maxlen=20)
        self.sparkline.pack(fill="x", padx=SPACING_LG, pady=(SPACING_SM, SPACING_LG))
        
        self.accent = accent_color
    
    def set_value(self, value: int):
        """Update the displayed value."""
        self.value_var.set(f"{value:,}")
    
    def push_spark(self, value: int):
        """Push a value to the sparkline."""
        self.sparkline.push(value)


class StatBadge(tk.Frame):
    """Small stat display component."""
    
    def __init__(self, parent, label, value="—", color=TEXT_PRIMARY, **kwargs):
        super().__init__(parent, bg=BG_SECONDARY, **kwargs)
        
        self.config(
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
        )
        
        tk.Label(
            self, text=label,
            font=(FONT_FAMILY_MONO, FONT_SIZE_LABEL_SM, FONT_WEIGHT_BOLD),
            bg=BG_SECONDARY, fg=TEXT_TERTIARY
        ).pack(side="left", padx=(SPACING_LG, SPACING_SM), pady=SPACING_MD)
        
        self.value_var = tk.StringVar(value=str(value))
        tk.Label(
            self, textvariable=self.value_var,
            font=(FONT_FAMILY_MONO, FONT_SIZE_BODY, FONT_WEIGHT_BOLD),
            bg=BG_SECONDARY, fg=color
        ).pack(side="left", padx=(0, SPACING_LG), pady=SPACING_MD)
    
    def set(self, value):
        """Update the value."""
        self.value_var.set(str(value))


# ============================================================================
# DATA VISUALIZATION COMPONENTS
# ============================================================================

class Sparkline(tk.Canvas):
    """Inline sparkline chart."""
    
    def __init__(self, parent, color, maxlen=20, **kwargs):
        super().__init__(
            parent, height=24, bg=BG_CARD,
            highlightthickness=0, **kwargs
        )
        
        self.color = color
        self.maxlen = maxlen
        self._data = []
        self.bind("<Configure>", lambda _: self._draw())
    
    def push(self, value):
        """Add value to sparkline."""
        self._data.append(value)
        if len(self._data) > self.maxlen:
            self._data = self._data[-self.maxlen:]
        self._draw()
    
    def _draw(self):
        """Redraw the sparkline."""
        self.delete("all")
        if len(self._data) < 2:
            return
        
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2:
            return
        
        lo, hi = min(self._data), max(self._data)
        rng = (hi - lo) or 1
        
        pts = []
        for i, v in enumerate(self._data):
            x = i * w / (len(self._data) - 1)
            y = h - 4 - (v - lo) / rng * (h - 8)
            pts.extend([x, y])
        
        if len(pts) >= 4:
            self.create_line(*pts, fill=self.color, width=2, smooth=True)


class PulseDot(tk.Canvas):
    """Animated pulsing dot indicator."""
    
    def __init__(self, parent, color=ACCENT_PRIMARY, bg=BG_CARD, **kwargs):
        super().__init__(
            parent, width=10, height=10, bg=bg,
            highlightthickness=0, **kwargs
        )
        
        self.color = color
        self._phase = 0
        self._animate()
    
    def _animate(self):
        """Animation loop."""
        self.delete("all")
        t = (math.sin(self._phase) + 1) / 2
        r = 3.5 + 1.5 * t
        c = interpolate_color(self.color, "#ffffff", t * 0.3)
        self.create_oval(5-r, 5-r, 5+r, 5+r, fill=c, outline="")
        self._phase += 0.12
        self.after(40, self._animate)


# ============================================================================
# CONTAINER COMPONENTS
# ============================================================================

class ScrollableFrame(tk.Frame):
    """Container with vertical scrollbar."""
    
    def __init__(self, parent, bg=BG_PRIMARY, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        
        # Canvas for scrolling
        self._canvas = tk.Canvas(
            self, bg=bg, highlightthickness=0, bd=0
        )
        
        # Scrollbar
        self._scrollbar = tk.Scrollbar(
            self, orient="vertical",
            command=self._canvas.yview,
            bg=BG_SECONDARY, troughcolor=BG_PRIMARY,
            relief="flat", bd=0
        )
        
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        
        # Inner frame
        self.inner = tk.Frame(self._canvas, bg=bg)
        self._window_id = self._canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )
        
        # Bind events
        self.inner.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        
        for w in (self._canvas, self.inner):
            w.bind("<MouseWheel>", self._on_scroll)
            w.bind("<Button-4>", self._scroll_up)
            w.bind("<Button-5>", self._scroll_down)
        
        self.after(100, self._bind_children)
    
    def _bind_children(self):
        """Recursively bind scroll events to all children."""
        def bind_tree(widget):
            widget.bind("<MouseWheel>", self._on_scroll, add="+")
            widget.bind("<Button-4>", self._scroll_up, add="+")
            widget.bind("<Button-5>", self._scroll_down, add="+")
            for child in widget.winfo_children():
                bind_tree(child)
        
        bind_tree(self.inner)
        self.after(1000, self._bind_children)
    
    def _on_frame_configure(self, _):
        """Update scroll region when frame changes."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
    
    def _on_canvas_configure(self, e):
        """Update window width and reset scroll position."""
        self._canvas.itemconfig(self._window_id, width=e.width)
        if self.inner.winfo_height() <= e.height:
            self._canvas.yview_moveto(0)
    
    def _on_scroll(self, e):
        """Handle mouse wheel scroll."""
        if self.inner.winfo_height() > self._canvas.winfo_height():
            self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    
    def _scroll_up(self, _):
        """Scroll up (Linux)."""
        if self.inner.winfo_height() > self._canvas.winfo_height():
            self._canvas.yview_scroll(-1, "units")
    
    def _scroll_down(self, _):
        """Scroll down (Linux)."""
        if self.inner.winfo_height() > self._canvas.winfo_height():
            self._canvas.yview_scroll(1, "units")


class Panel(tk.Frame):
    """General purpose panel container."""
    
    def __init__(self, parent, title="", bg=BG_SECONDARY, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        
        self.config(
            highlightthickness=1,
            highlightbackground=BORDER_LIGHT,
        )
        
        if title:
            header = tk.Label(
                self, text=title,
                font=(FONT_FAMILY_PRIMARY, FONT_SIZE_SUBTITLE, FONT_WEIGHT_BOLD),
                bg=bg, fg=TEXT_PRIMARY
            )
            header.pack(fill="x", padx=SPACING_LG, pady=(SPACING_LG, SPACING_MD))
            
            # Divider
            tk.Frame(self, bg=BORDER_LIGHT, height=1).pack(
                fill="x", padx=SPACING_LG, pady=(0, SPACING_MD)
            )


class Grid(tk.Frame):
    """Grid layout container with responsive columns."""
    
    def __init__(self, parent, columns=3, gap=SPACING_LG, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.columns = columns
        self.gap = gap
        self._row = 0
        self._col = 0
        self._items = []
    
    def add(self, widget):
        """Add widget to grid."""
        widget.grid(
            row=self._row, column=self._col,
            sticky="nsew", padx=self.gap//2, pady=self.gap//2
        )
        
        self._items.append(widget)
        self._col += 1
        
        if self._col >= self.columns:
            self._col = 0
            self._row += 1


# ============================================================================
# INPUT COMPONENTS
# ============================================================================

class TextInput(tk.Frame):
    """Modern text input field."""
    
    def __init__(self, parent, label="", placeholder="", **kwargs):
        super().__init__(parent, bg=BG_PRIMARY, **kwargs)
        
        if label:
            tk.Label(
                self, text=label,
                font=(FONT_FAMILY_PRIMARY, FONT_SIZE_BODY_SM, FONT_WEIGHT_BOLD),
                bg=BG_PRIMARY, fg=TEXT_PRIMARY
            ).pack(fill="x", pady=(0, SPACING_SM))
        
        self.entry = tk.Entry(
            self, font=(FONT_FAMILY_MONO, FONT_SIZE_BODY),
            bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            relief="solid", bd=1, highlightthickness=0,
            insertbackground=ACCENT_PRIMARY
        )
        self.entry.pack(fill="x", ipady=SPACING_SM)
        
        if placeholder:
            self.entry.insert(0, placeholder)
            self.entry.bind("<FocusIn>", lambda _: self._on_focus())
            self.entry.bind("<FocusOut>", lambda _: self._on_blur())
            self.placeholder = placeholder
        
        self.entry.bind("<FocusIn>", lambda _: self.entry.config(bg=lighten(BG_SECONDARY, 0.1)))
        self.entry.bind("<FocusOut>", lambda _: self.entry.config(bg=BG_SECONDARY))
    
    def _on_focus(self):
        """Handle focus (remove placeholder)."""
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, tk.END)
            self.entry.config(fg=TEXT_PRIMARY)
    
    def _on_blur(self):
        """Handle blur (show placeholder if empty)."""
        if not self.entry.get():
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg=TEXT_TERTIARY)
    
    def get(self):
        """Get entry value."""
        val = self.entry.get()
        if val == getattr(self, 'placeholder', ''):
            return ""
        return val
    
    def set(self, value):
        """Set entry value."""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, str(value))
