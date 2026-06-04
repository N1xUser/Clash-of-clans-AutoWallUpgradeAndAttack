import tkinter as tk
from src.ui.widgets import (
    BG_DEEP, BG_PANEL, BG_CARD, BORDER, BORDER_BRIGHT,
    ACCENT_GOLD, ACCENT_ELX, ACCENT_DARK, ACCENT_UPG, ACCENT_RED,
    FG_PRIMARY, FG_SECONDARY, FG_DIM
)

def build_config_col(ui, parent):
    col = tk.Frame(parent, bg=BG_DEEP)
    col.grid(row=0, column=2, sticky="nsew", padx=(6, 16), pady=14)

    ui._col_label(col, "PIPELINE CONFIG", FG_DIM)

    card = tk.Frame(col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
    card.pack(fill="x")

    inner = tk.Frame(card, bg=BG_CARD)
    inner.pack(fill="both", expand=True, padx=14, pady=12)
    inner.columnconfigure(0, weight=0)
    inner.columnconfigure(1, weight=1)

    ui.engine_home_var = tk.StringVar(value="RAPID")
    ui.engine_upg_var = tk.StringVar(value="RAPID")
    ui.engine_enemy_var = tk.StringVar(value="RAPID")
    ui.engine_wall_var = tk.StringVar(value="GLM")
    ui.use_tgt_gold = tk.IntVar(value=1)
    ui.use_tgt_elx = tk.IntVar(value=1)
    ui.use_tgt_goel = tk.IntVar(value=0)
    ui.use_tgt_dark = tk.IntVar(value=0)
    
    ui.tgt_gold_var = tk.IntVar(value=500000)
    ui.tgt_elx_var = tk.IntVar(value=500000)
    ui.tgt_goel_var = tk.IntVar(value=1000000)
    ui.tgt_dark_var = tk.IntVar(value=3000)

    engines = ["TESSERACT", "GLM", "RAPID"]
    r = [0]
    ui.ui_updaters =[]

    def global_validate_and_update(triggered_by=None):
        if triggered_by == "GO&EL" and ui.use_tgt_goel.get() > 0:
            ui.use_tgt_gold.set(0)
            ui.use_tgt_elx.set(0)
        elif triggered_by in ["GOLD", "ELIXIR"] and (ui.use_tgt_gold.get() > 0 or ui.use_tgt_elx.get() > 0):
            ui.use_tgt_goel.set(0)

        active_vars =[v for v in (ui.use_tgt_gold, ui.use_tgt_elx, ui.use_tgt_dark, ui.use_tgt_goel) if v.get() > 0]
        if len(active_vars) == 1 and active_vars[0].get() == 2:
            active_vars[0].set(1)
            
        for update_fn in ui.ui_updaters:
            update_fn()
            
    ui.global_validate_and_update = global_validate_and_update

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
        ui._style_dropdown(opt, width=7)
        opt.grid(row=r[0], column=1, sticky="e", pady=2)
        ui.config_widgets.append(opt)
        r[0] += 1

    def divider():
        tk.Frame(inner, bg=BORDER, height=1).grid(
            row=r[0], column=0, columnspan=2, sticky="ew", pady=6)
        r[0] += 1

    def target_row(label_text, toggle_var, scale_var, max_val, step, color, name_id):
        def toggle():
            current = toggle_var.get()
            active_count = sum(1 for v in (ui.use_tgt_gold, ui.use_tgt_elx, ui.use_tgt_dark, ui.use_tgt_goel) if v.get() > 0)
            
            if active_count <= 1 and current > 0:
                toggle_var.set(0)
            elif active_count == 0 and current == 0:
                toggle_var.set(1)
            else:
                toggle_var.set((current + 1) % 3)
            
            ui.global_validate_and_update(name_id)

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
        ui.config_widgets.append(chk_btn)

        scale = tk.Scale(
            inner, variable=scale_var, from_=0, to=max_val, resolution=step,
            orient="horizontal", bg=BG_CARD, fg=color, troughcolor=BG_PANEL,
            highlightthickness=0, bd=0, activebackground=BORDER_BRIGHT,
            font=("Courier", 7), sliderlength=12,
        )
        scale.grid(row=r[0], column=1, sticky="ew", padx=(8, 0), pady=2)
        ui.config_widgets.append(scale)
        
        ui.ui_updaters.append(update_ui)
        update_ui()
        r[0] += 1

    section_lbl("HOME PIPELINE", ACCENT_UPG)
    cfg_row("1. RESOURCES", ui.engine_home_var)
    cfg_row("2. UPGRADES", ui.engine_upg_var)
    divider()

    section_lbl("ATTACK CONFIG", ACCENT_RED)
    cfg_row("ENEMY LOOT", ui.engine_enemy_var)
    cfg_row("WALL OCR", ui.engine_wall_var)
    divider()

    section_lbl("MIN TARGETS  (✓=AND, •=OR)", FG_DIM)
    target_row("GOLD", ui.use_tgt_gold, ui.tgt_gold_var, 1500000, 50000, ACCENT_GOLD, "GOLD")
    target_row("ELIXIR", ui.use_tgt_elx, ui.tgt_elx_var, 1500000, 50000, ACCENT_ELX, "ELIXIR")
    target_row("GO&EL", ui.use_tgt_goel, ui.tgt_goel_var, 2500000, 50000, "#10b981", "GO&EL")
    target_row("DARK", ui.use_tgt_dark, ui.tgt_dark_var, 15000, 500, ACCENT_DARK, "DARK")

    tk.Frame(inner, bg=BG_CARD, height=8).grid(row=r[0], column=0, columnspan=2, sticky="ew")
    ui._hsep(col)

    ui._col_label(col, "ATTACK SETTINGS", ACCENT_DARK)
    
    atk_card = tk.Frame(col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
    atk_card.pack(fill="x")
    
    atk_inner = tk.Frame(atk_card, bg=BG_CARD)
    atk_inner.pack(fill="both", expand=True, padx=12, pady=20)
    
    ui.debug_ss_var = tk.BooleanVar(value=True)
    cb_debug_ss = tk.Checkbutton(
        atk_inner, text="SAVE DEBUG SCREENSHOTS", variable=ui.debug_ss_var,
        bg=BG_CARD, fg=FG_PRIMARY, selectcolor=BG_DEEP,
        activebackground=BG_CARD, activeforeground=FG_PRIMARY,
        font=("Courier", 8, "bold"), cursor="hand2"
    )
    cb_debug_ss.pack(anchor="w", pady=(0, 8))
    ui.config_widgets.append(cb_debug_ss)

    tk.Frame(atk_inner, bg=BORDER, height=1).pack(fill="x", pady=10)
    
    tk.Label(atk_inner, text="TESTS", font=("Courier", 7, "bold"), 
             bg=BG_CARD, fg=FG_DIM).pack(anchor="w", pady=(0, 8))
    
    ui.btn_test_wall = tk.Button(
        atk_inner, text="TEST AUTOWALL", font=("Courier", 9, "bold"),
        bg=ACCENT_UPG, fg=BG_DEEP,
        activebackground="#7c3aed", activeforeground=BG_DEEP,
        relief="flat", padx=12, pady=6, cursor="hand2",
        command=ui.on_test_autowall,
    )
    ui.btn_test_wall.pack(fill="x", pady=(0, 6))

    ui.btn_test_donate = tk.Button(
        atk_inner, text="TEST DONATE", font=("Courier", 9, "bold"),
        bg="#dc2626", fg="#ffffff",
        activebackground="#b91c1c", activeforeground="#ffffff",
        relief="flat", padx=12, pady=6, cursor="hand2",
        command=ui.on_test_donate,
    )
    ui.btn_test_donate.pack(fill="x", pady=(0, 10))
    
    tk.Frame(atk_inner, bg=BORDER, height=1).pack(fill="x", pady=10)
    
    tk.Label(atk_inner, text="PRIMARY DEPLOYMENT", font=("Courier", 7, "bold"), 
             bg=BG_CARD, fg=FG_DIM).pack(anchor="w")
    
    troop_frame = tk.Frame(atk_inner, bg=BG_CARD)
    troop_frame.pack(anchor="w", pady=(3, 0))
    tk.Label(troop_frame, text="⚡", font=("Segoe UI Emoji", 10), 
             bg=BG_CARD, fg=ACCENT_DARK).pack(side="left")
    tk.Label(troop_frame, text="ELECTRIC DRAGONS", font=("Courier", 9, "bold"), 
             bg=BG_CARD, fg=ACCENT_DARK).pack(side="left", padx=(4, 0))
