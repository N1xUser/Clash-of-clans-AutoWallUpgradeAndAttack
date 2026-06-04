import tkinter as tk
from tkinter import scrolledtext
from src.ui.widgets import (
    BG_DEEP, BG_PANEL, BG_CARD2, BORDER,
    ACCENT_GOLD, ACCENT_ELX, ACCENT_DARK, ACCENT_RED,
    FG_PRIMARY, FG_DIM, FG_GREEN
)

def build_terminal(ui, parent):
    TERM_H = 200

    outer = tk.Frame(parent, bg=BG_DEEP, height=TERM_H)
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
        command=ui._clear_terminal,
    ).pack(side="right", pady=(4, 3))

    wrap = tk.Frame(outer, bg=BORDER, bd=0)
    wrap.pack(fill="both", expand=True)

    ui.terminal = scrolledtext.ScrolledText(
        wrap, bg=BG_PANEL, fg=FG_GREEN, font=("Courier", 8),
        insertbackground=FG_PRIMARY, relief="flat", bd=0,
        padx=10, pady=8, wrap="word",
    )
    ui.terminal.pack(fill="both", expand=True, padx=1, pady=1)
    ui.terminal.tag_config("sys", foreground=FG_DIM)
    ui.terminal.tag_config("time", foreground="#475569")
    ui.terminal.tag_config("bot", foreground="#22c55e")
    ui.terminal.tag_config("bot_off", foreground=ACCENT_RED)
    ui.terminal.tag_config("gold", foreground=ACCENT_GOLD)
    ui.terminal.tag_config("elx", foreground=ACCENT_ELX)
    ui.terminal.tag_config("dark", foreground=ACCENT_DARK)
