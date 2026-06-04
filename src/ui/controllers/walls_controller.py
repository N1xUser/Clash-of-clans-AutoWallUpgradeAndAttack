import tkinter as tk
import json
from src.ui.widgets import BG_DEEP, FG_DIM, FG_PRIMARY, BG_PANEL, FG_SECONDARY, BORDER, ACCENT_GOLD, make_btn

def save_upgrades_json(ui):
    content = ui.upgrades_text.get(1.0, tk.END).strip()
    try:
        parsed = json.loads(content)
        ui.latest_data["upgrades_info"] = parsed
        ui.state_cache["upgrades_info"] = parsed
        
        from src.ui.controllers.config_controller import save_state
        save_state(ui)
        
        walls = sum(item.get("qty", 1) for item in parsed.get("upgrades", []) if "wall" in item.get("name", "").lower())
        ui.badge_walls.set(str(walls))
        
        render_walls_ui(ui)
        
        ui.log_terminal("[SYS] Upgrades data manually updated and saved.", "sys")
    except Exception as e:
        ui.log_terminal(f"[ERROR] Invalid JSON format: {e}", "bot_off")

def render_walls_ui(ui):
    for widget in ui.walls_container.winfo_children():
        widget.destroy()
        
    upg_data = ui.latest_data.get("upgrades_info", {})
    walls =[item for item in upg_data.get("upgrades", []) if "wall" in item.get("name", "").lower()]
    
    if not walls:
        tk.Label(ui.walls_container, text="No walls detected.", 
                 bg=BG_DEEP, fg=FG_DIM, font=("Courier", 8)).pack(anchor="w", pady=5)
        return

    ui.wall_entries =[]
    for idx, wall in enumerate(upg_data.get("upgrades", [])):
        if "wall" not in wall.get("name", "").lower():
            continue
            
        row = tk.Frame(ui.walls_container, bg=BG_DEEP)
        row.pack(fill="x", pady=2)
        
        qty = wall.get("qty", 1)
        name_text = f"Wall x{qty}"
        tk.Label(row, text=name_text, bg=BG_DEEP, fg=FG_PRIMARY, 
                 font=("Courier", 8, "bold"), width=12, anchor="w").pack(side="left")
        
        cost_var = tk.StringVar(value=str(wall.get("cost", 0)))
        entry = tk.Entry(row, textvariable=cost_var, bg=BG_PANEL, fg=FG_SECONDARY,
                         font=("Courier", 8), width=15, relief="flat",
                         highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT_GOLD)
        entry.pack(side="left", padx=5)
        
        ui.wall_entries.append({"index": idx, "var": cost_var})
        
    btn_save_walls = make_btn(ui.walls_container, "SAVE WALL COSTS",
                              lambda: save_wall_targets_ui(ui),
                              "#22c55e", small=True)
    btn_save_walls.pack(anchor="e", pady=(5, 0))

def save_wall_targets_ui(ui):
    try:
        upgrades = ui.latest_data.get("upgrades_info", {}).get("upgrades", [])
        for entry_data in ui.wall_entries:
            idx = entry_data["index"]
            val = entry_data["var"].get().replace(" ", "").replace(",", "")
            upgrades[idx]["cost"] = int(val)
            
        ui.latest_data["upgrades_info"]["upgrades"] = upgrades
        ui.state_cache["upgrades_info"] = ui.latest_data["upgrades_info"]
        
        from src.ui.controllers.config_controller import save_state
        save_state(ui)
        
        ui.log_terminal("[SYS] Wall targets saved.", "sys")
        
        txt = json.dumps(ui.latest_data["upgrades_info"], indent=2)
        ui.upgrades_text.configure(state="normal")
        ui.upgrades_text.delete(1.0, tk.END)
        ui.upgrades_text.insert(tk.END, txt)
        ui.upgrades_text.configure(state="disabled")
        
    except Exception as e:
        ui.log_terminal(f"[ERROR] Invalid wall cost: {e}", "bot_off")
