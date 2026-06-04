import tkinter as tk
import webbrowser
from src.ui.widgets import (
    BG_DEEP, BG_PANEL, BG_CARD2, BORDER, BORDER_BRIGHT,
    ACCENT_GOLD, ACCENT_ELX, ACCENT_DARK, ACCENT_UPG,
    FG_PRIMARY, FG_SECONDARY, FG_DIM,
    make_btn, StatBadge
)

def build_header(ui, parent):
    hdr = tk.Frame(parent, bg=BG_DEEP)
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

    ui.mouse_coords_lbl = tk.Label(right, text="X: ---  Y: ---", font=("Courier", 8, "bold"), bg=BG_DEEP, fg="#737373")
    ui.mouse_coords_lbl.pack(side="left", padx=(0, 15))

    ui.preview_var = tk.BooleanVar(value=False)
    ui.anti_afk_var = tk.BooleanVar(value=False)
    ui.auto_wall_var = tk.BooleanVar(value=False)
    ui.auto_reinforce_var = tk.BooleanVar(value=False)
    ui.clan_donate_var = tk.BooleanVar(value=False)
    
    cb_auto_reinforce = tk.Checkbutton(
        right, text="AUTO REINFORCE", variable=ui.auto_reinforce_var,
        bg=BG_DEEP, fg=FG_SECONDARY, selectcolor=BG_PANEL,
        activebackground=BG_DEEP, activeforeground=FG_PRIMARY,
        font=("Courier", 8, "bold"), cursor="hand2",
        command=ui.save_state,
    )
    cb_auto_reinforce.pack(side="left", padx=(0, 4))
    ui.config_widgets.append(cb_auto_reinforce)

    cb_clan_donate = tk.Checkbutton(
        right, text="CLAN DONATE", variable=ui.clan_donate_var,
        bg=BG_DEEP, fg=FG_SECONDARY, selectcolor=BG_PANEL,
        activebackground=BG_DEEP, activeforeground=FG_PRIMARY,
        font=("Courier", 8, "bold"), cursor="hand2",
        command=ui.save_state,
    )
    cb_clan_donate.pack(side="left", padx=(0, 4))
    ui.config_widgets.append(cb_clan_donate)
    
    cb_auto_wall = tk.Checkbutton(
        right, text="AUTO WALLS", variable=ui.auto_wall_var,
        bg=BG_DEEP, fg=FG_SECONDARY, selectcolor=BG_PANEL,
        activebackground=BG_DEEP, activeforeground=FG_PRIMARY,
        font=("Courier", 8, "bold"), cursor="hand2",
        command=ui.save_state,
    )
    cb_auto_wall.pack(side="left", padx=(0, 4))
    ui.config_widgets.append(cb_auto_wall)

    ui.wall_check_freq_var = tk.IntVar(value=1)
    freq_frame = tk.Frame(right, bg=BG_DEEP)
    freq_frame.pack(side="left", padx=(0, 8))
    tk.Label(freq_frame, text="EVERY", font=("Courier", 7, "bold"),
             bg=BG_DEEP, fg=FG_DIM).pack(side="left")
    freq_spin = tk.Spinbox(
        freq_frame, from_=1, to=20, width=3,
        textvariable=ui.wall_check_freq_var,
        font=("Courier", 8, "bold"),
        bg=BG_CARD2, fg=FG_PRIMARY, buttonbackground=BG_CARD2,
        relief="flat", highlightthickness=1, highlightbackground=BORDER,
        command=ui.save_state,
    )
    freq_spin.pack(side="left", padx=2)
    ui.config_widgets.append(freq_spin)
    tk.Label(freq_frame, text="ATK", font=("Courier", 7, "bold"),
             bg=BG_DEEP, fg=FG_DIM).pack(side="left")
    
    cb_anti_afk = tk.Checkbutton(
        right, text="ANTI AFK", variable=ui.anti_afk_var,
        bg=BG_DEEP, fg=FG_SECONDARY, selectcolor=BG_PANEL,
        activebackground=BG_DEEP, activeforeground=FG_PRIMARY,
        font=("Courier", 8, "bold"), cursor="hand2",
        command=ui.save_state,
    )
    cb_anti_afk.pack(side="left", padx=(0, 8))
    ui.config_widgets.append(cb_anti_afk)
    tk.Checkbutton(
        right, text="PREVIEW", variable=ui.preview_var,
        bg=BG_DEEP, fg=FG_SECONDARY, selectcolor=BG_PANEL,
        activebackground=BG_DEEP, activeforeground=FG_PRIMARY,
        font=("Courier", 8, "bold"), cursor="hand2",
        command=ui._on_preview_toggle,
    ).pack(side="left", padx=(0, 12))

    strip = tk.Frame(hdr, bg=BG_DEEP)
    strip.pack(fill="x", padx=16, pady=(8, 0))

    ui.badge_builders = StatBadge(strip, "BUILDERS", "?/?", FG_PRIMARY)
    ui.badge_builders.pack(side="left", padx=(0, 4))

    ui.badge_walls = StatBadge(strip, "WALLS", "0", ACCENT_UPG)
    ui.badge_walls.pack(side="left", padx=(0, 4))

    ui.bot_status_lbl = tk.Label(
        strip, text="● BOT IDLE", font=("Courier", 8, "bold"),
        bg=BG_DEEP, fg=FG_DIM,
    )
    ui.bot_status_lbl.pack(side="left", padx=(10, 0))

    right_strip = tk.Frame(strip, bg=BG_DEEP)
    right_strip.pack(side="right")

    tk.Label(right_strip, text="SCAN", font=("Courier", 7, "bold"),
             bg=BG_DEEP, fg=FG_DIM).pack(side="left", padx=(0, 8))

    ui.btn_tess = make_btn(right_strip, "TESS",
                              lambda: ui.on_update_click("tesseract"), ACCENT_GOLD)
    ui.btn_glm = make_btn(right_strip, "GLM",
                              lambda: ui.on_update_click("glm"), ACCENT_ELX)
    ui.btn_rapid = make_btn(right_strip, "RAPID",
                              lambda: ui.on_update_click("rapid"), ACCENT_DARK)
    for b in (ui.btn_tess, ui.btn_glm, ui.btn_rapid):
        b.pack(side="left", padx=3)

    tk.Frame(right_strip, bg=BORDER, width=1).pack(
        side="left", fill="y", pady=4, padx=(12, 12))

    trans_frame = tk.Frame(right_strip, bg=BG_DEEP)
    trans_frame.pack(side="left", padx=(0, 12))
    tk.Label(trans_frame, text="OPACITY", font=("Courier", 7, "bold"), bg=BG_DEEP, fg=FG_DIM).pack(side="left")
    
    ui.transparency_var = tk.IntVar(value=100)
    ui.trans_scale = tk.Scale(
        trans_frame, from_=20, to=100, orient="horizontal",
        variable=ui.transparency_var, command=ui._on_transparency_change,
        bg=BG_DEEP, fg=FG_PRIMARY, troughcolor=BG_PANEL,
        highlightthickness=0, bd=0, activebackground=BG_DEEP,
        font=("Courier", 7), sliderlength=10, length=60, showvalue=0
    )
    ui.trans_scale.pack(side="left", padx=2)
    ui.trans_scale.bind("<ButtonRelease-1>", lambda e: ui.save_state())
    
    ui.trans_lbl = tk.Label(trans_frame, text="100%", font=("Courier", 7, "bold"), bg=BG_DEEP, fg=FG_PRIMARY)
    ui.trans_lbl.pack(side="left")

    ui.btn_bot = tk.Button(
        right_strip, text="▶  START BOT", font=("Courier", 9, "bold"),
        bg="#22c55e", fg=BG_DEEP,
        activebackground="#16a34a", activeforeground=BG_DEEP,
        relief="flat", padx=14, pady=4, cursor="hand2",
        command=ui.on_start_bot,
    )
    ui.btn_bot.pack(side="left", padx=(10, 0))

    tk.Frame(hdr, bg=BORDER, height=1).pack(fill="x", pady=(8, 0))
