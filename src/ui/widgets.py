import tkinter as tk
import math

BG_DEEP       = "#0b0d11"
BG_PANEL      = "#0f1217"
BG_CARD       = "#141820"
BG_CARD2      = "#1a1f28"
BORDER        = "#252c38"
BORDER_BRIGHT = "#2e3847"
ACCENT_GOLD   = "#f0b429"
ACCENT_ELX    = "#c084fc"
ACCENT_DARK   = "#38bdf8"
ACCENT_UPG    = "#4ade80"
ACCENT_RED    = "#f87171"
FG_PRIMARY    = "#e2e8f0"
FG_SECONDARY  = "#94a3b8"
FG_DIM        = "#4a5568"
FG_GREEN      = "#4ade80"

WINDOW_W, WINDOW_H = 1140, 740
MIN_W,     MIN_H   = 920,  600

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def interpolate_color(c1, c2, t):
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"

def make_btn(parent, text, command, accent=FG_PRIMARY, small=False):
    f  = ("Courier", 8, "bold") if small else ("Courier", 9, "bold")
    px = 8  if small else 12
    py = 3  if small else 5
    return tk.Button(
        parent, text=text, command=command,
        font=f, bg=BG_CARD2, fg=accent,
        activebackground=BORDER_BRIGHT, activeforeground=accent,
        relief="flat", padx=px, pady=py, cursor="hand2",
        highlightthickness=1, highlightbackground=BORDER,
        highlightcolor=accent,
    )

class PulseDot(tk.Canvas):
    def __init__(self, parent, color, bg=BG_CARD, **kwargs):
        super().__init__(parent, width=10, height=10, bg=bg,
                         highlightthickness=0, **kwargs)
        self.color = color
        self._phase = 0
        self._animate()

    def _animate(self):
        self.delete("all")
        t = (math.sin(self._phase) + 1) / 2
        r = 3.5 + 1.5 * t
        c = interpolate_color(self.color, "#ffffff", t * 0.25)
        self.create_oval(5 - r, 5 - r, 5 + r, 5 + r, fill=c, outline="")
        self._phase += 0.12
        self.after(40, self._animate)

class Sparkline(tk.Canvas):
    def __init__(self, parent, color, maxlen=24, **kwargs):
        super().__init__(parent, height=22, bg=BG_CARD, highlightthickness=0, **kwargs)
        self.color  = color
        self.maxlen = maxlen
        self._data  = []
        self.bind("<Configure>", lambda e: self._draw())

    def push(self, value):
        self._data.append(value)
        if len(self._data) > self.maxlen:
            self._data = self._data[-self.maxlen:]
        self._draw()

    def _draw(self):
        self.delete("all")
        if len(self._data) < 2:
            return
        w, h = self.winfo_width(), self.winfo_height()
        lo, hi = min(self._data), max(self._data)
        rng = (hi - lo) or 1
        pts = []
        for i, v in enumerate(self._data):
            pts.extend([
                i * w / (len(self._data) - 1),
                h - 3 - (v - lo) / rng * (h - 6),
            ])
        if len(pts) >= 4:
            self.create_line(*pts, fill=self.color, width=1.5, smooth=True)

class Badge(tk.Frame):
    def __init__(self, parent, label, icon, accent, **kwargs):
        super().__init__(parent, bg=BG_CARD, bd=0, **kwargs)
        tk.Frame(self, bg=accent, width=2).pack(side="left", fill="y")
        inner = tk.Frame(self, bg=BG_CARD)
        inner.pack(side="left", fill="both", expand=True, padx=(10, 8), pady=6)

        top = tk.Frame(inner, bg=BG_CARD)
        top.pack(fill="x")
        tk.Label(top, text=icon, font=("Segoe UI Emoji", 10),
                 bg=BG_CARD, fg=accent).pack(side="left")
        tk.Label(top, text=label.upper(), font=("Courier", 7, "bold"),
                 bg=BG_CARD, fg=FG_DIM, padx=4).pack(side="left")
        PulseDot(top, accent, bg=BG_CARD).pack(side="right")

        self.value_var = tk.StringVar(value="0")
        tk.Label(inner, textvariable=self.value_var,
                 font=("Courier", 17, "bold"),
                 bg=BG_CARD, fg=accent, anchor="w").pack(fill="x")
        self.spark = Sparkline(inner, color=accent)
        self.spark.pack(fill="x", pady=(1, 0))

    def set_value(self, v: int):
        self.value_var.set(f"{v:,}")
    
    def push_spark(self, v: int):
        self.spark.push(v)

class StatBadge(tk.Frame):
    def __init__(self, parent, label, default="—", color=FG_PRIMARY, **kwargs):
        super().__init__(parent, bg=BG_CARD2,
                         highlightthickness=1, highlightbackground=BORDER, **kwargs)
        tk.Label(self, text=label, font=("Courier", 7, "bold"),
                 bg=BG_CARD2, fg=FG_DIM).pack(side="left", padx=(8, 4), pady=5)
        self.var = tk.StringVar(value=default)
        tk.Label(self, textvariable=self.var, font=("Courier", 11, "bold"),
                 bg=BG_CARD2, fg=color).pack(side="left", padx=(0, 10), pady=5)

    def set(self, v): self.var.set(str(v))

class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg=BG_DEEP, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)

        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self._vsb    = tk.Scrollbar(self, orient="vertical",
                                    command=self._canvas.yview,
                                    bg=BG_CARD2, troughcolor=BG_DEEP,
                                    relief="flat", bd=0)
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self._vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self._canvas, bg=bg)
        self._win_id = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>",   self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        for w in (self._canvas, self.inner):
            w.bind("<MouseWheel>", self._on_mw)
            w.bind("<Button-4>",   self._scroll_up)
            w.bind("<Button-5>",   self._scroll_dn)
            
        self.after(100, self._bind_all_children)

    def _bind_all_children(self):
        def bind_tree(widget):
            widget.bind("<MouseWheel>", self._on_mw, add="+")
            widget.bind("<Button-4>", self._scroll_up, add="+")
            widget.bind("<Button-5>", self._scroll_dn, add="+")
            for child in widget.winfo_children():
                bind_tree(child)
        bind_tree(self.inner)
        self.after(1000, self._bind_all_children)

    def _on_frame_configure(self, _e):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self._canvas.itemconfig(self._win_id, width=e.width)
        if self.inner.winfo_height() <= e.height:
            self._canvas.yview_moveto(0)

    def _on_mw(self, e):
        if self.inner.winfo_height() > self._canvas.winfo_height():
            self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            
    def _scroll_up(self, _e):
        if self.inner.winfo_height() > self._canvas.winfo_height():
            self._canvas.yview_scroll(-1, "units")
            
    def _scroll_dn(self, _e):
        if self.inner.winfo_height() > self._canvas.winfo_height():
            self._canvas.yview_scroll(1, "units")
