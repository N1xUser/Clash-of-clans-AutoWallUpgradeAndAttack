import tkinter as tk
from tkinter import scrolledtext
from src.ui.widgets import (
    BG_DEEP, BG_CARD, BORDER,
    ACCENT_GOLD, ACCENT_ELX, ACCENT_DARK, ACCENT_UPG, ACCENT_RED,
    FG_SECONDARY, Badge, make_btn
)

def build_home_col(ui, parent):
    col = tk.Frame(parent, bg=BG_DEEP)
    col.grid(row=0, column=0, sticky="nsew", padx=(16, 6), pady=14)

    ui._col_label(col, "HOME RESOURCES", ACCENT_GOLD)

    ui.card_gold = Badge(col, "Gold", "⚡", ACCENT_GOLD)
    ui.card_elixir = Badge(col, "Elixir", "✦", ACCENT_ELX)
    ui.card_dark = Badge(col, "Dark Elixir", "◈", ACCENT_DARK)
    for card in (ui.card_gold, ui.card_elixir, ui.card_dark):
        card.pack(fill="x", pady=3)
        card.configure(highlightthickness=1, highlightbackground=BORDER)

    ui._hsep(col)
    ui._col_label(col, "SCAN UPGRADES", ACCENT_UPG)

    upg_row = tk.Frame(col, bg=BG_DEEP)
    upg_row.pack(fill="x", pady=(0, 4))
    ui.btn_upg_tess = make_btn(upg_row, "TESS",
                                  lambda: ui.on_detect_builders("tesseract"),
                                  ACCENT_GOLD, small=True)
    ui.btn_upg_glm = make_btn(upg_row, "GLM",
                                  lambda: ui.on_detect_builders("glm"),
                                  ACCENT_ELX, small=True)
    ui.btn_upg_rapid = make_btn(upg_row, "RAPID",
                                  lambda: ui.on_detect_builders("rapid"),
                                  ACCENT_DARK, small=True)
    for b in (ui.btn_upg_tess, ui.btn_upg_glm, ui.btn_upg_rapid):
        b.pack(side="left", padx=(0, 4))
        
    ui.btn_save_upg = make_btn(upg_row, "SAVE EDITS",
                                  ui._save_upgrades_json,
                                  ACCENT_RED, small=True)
    ui.btn_save_upg.pack(side="right", padx=(0, 4))

    text_container = tk.Frame(col, bg=BG_DEEP, height=175)
    text_container.pack(fill="x", pady=(0, 5))
    text_container.pack_propagate(False)

    ui.upgrades_text = scrolledtext.ScrolledText(
        text_container, bg=BG_CARD, fg=FG_SECONDARY, font=("Courier", 8),
        relief="flat", bd=0, padx=8, pady=6,
        highlightthickness=1, highlightbackground=BORDER,
    )
    
    ui.upgrades_text.pack(fill="both", expand=True)
    
    ui.upgrades_text.insert(tk.END, "Waiting for Home Screen scan...")

    ui._hsep(col)
    ui._col_label(col, "WALL TARGETS", ACCENT_GOLD)

    ui.walls_container = tk.Frame(col, bg=BG_DEEP)
    ui.walls_container.pack(fill="x", pady=(0, 5))
