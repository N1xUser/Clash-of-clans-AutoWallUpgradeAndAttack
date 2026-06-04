import tkinter as tk
from src.ui.widgets import (
    BG_DEEP, BG_CARD, BG_PANEL, BORDER,
    ACCENT_GOLD, ACCENT_ELX, ACCENT_DARK, ACCENT_RED,
    FG_PRIMARY, FG_SECONDARY, Badge
)

def build_enemy_col(ui, parent):
    col = tk.Frame(parent, bg=BG_DEEP)
    col.grid(row=0, column=1, sticky="nsew", padx=6, pady=14)

    ui._col_label(col, "ENEMY LOOT", ACCENT_RED)

    ui.card_enemy_gold = Badge(col, "Enemy Gold", "⚡", ACCENT_GOLD)
    ui.card_enemy_elixir = Badge(col, "Enemy Elixir", "✦", ACCENT_ELX)
    ui.card_enemy_dark = Badge(col, "Enemy Dark", "◈", ACCENT_DARK)
    for card in (ui.card_enemy_gold, ui.card_enemy_elixir, ui.card_enemy_dark):
        card.pack(fill="x", pady=3)
        card.configure(highlightthickness=1, highlightbackground=BORDER)

    ui._hsep(col)

    ui._col_label(col, "AI INTEGRATION", ACCENT_ELX)
    
    api_card = tk.Frame(col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER, height=210)
    api_card.pack_propagate(False)
    api_card.pack(fill="x", pady=(0, 6))
    
    api_inner = tk.Frame(api_card, bg=BG_CARD)
    api_inner.pack(fill="both", expand=True, padx=12, pady=10)

    btn_debug = tk.Button(
        api_inner, text="DEBUG JSON", command=ui.open_debug_json_window,
        font=("Courier", 8, "bold"), bg=BG_DEEP, fg=ACCENT_ELX, cursor="hand2"
    )
    btn_debug.pack(anchor="w", pady=(0, 8))

    def ai_cfg_row(label_text, var_obj, options_list):
        row = tk.Frame(api_inner, bg=BG_CARD)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label_text, font=("Courier", 8), 
                 bg=BG_CARD, fg=FG_SECONDARY).pack(side="left")
        opt = tk.OptionMenu(row, var_obj, *options_list)
        ui._style_dropdown(opt, width=17)
        opt.pack(side="right")
        ui.config_widgets.append(opt)

    ui.ai_mode_var = tk.StringVar(value="STATIC")
    ai_cfg_row("ATTACK MODE", ui.ai_mode_var, ["STATIC", "DYNAMIC AI"])

    ui.ai_model_var = tk.StringVar(value="GEMINI FLASH LITE")
    ai_cfg_row("MODEL", ui.ai_model_var,["GEMINI FLASH LITE", "GEMINI 1.5 PRO", "GPT-4O MINI", "GEMINI 3 FLASH PREVIEW", "GEMINI 3.1 PRO PREVIEW"])

    tk.Frame(api_inner, bg=BORDER, height=1).pack(fill="x", pady=10)

    tk.Label(api_inner, text="API KEY", font=("Courier", 8, "bold"), 
             bg=BG_CARD, fg=FG_SECONDARY).pack(anchor="w", pady=(0, 5))
    
    ui.gemini_api_var = tk.StringVar()
    api_entry = tk.Entry(
        api_inner, textvariable=ui.gemini_api_var, font=("Courier", 8),
        bg=BG_PANEL, fg=FG_PRIMARY, insertbackground=FG_PRIMARY,
        relief="flat", show="*", highlightthickness=1, 
        highlightbackground=BORDER, highlightcolor=ACCENT_ELX
    )
    api_entry.pack(fill="x", ipady=4, padx=1)
    ui.config_widgets.append(api_entry)
