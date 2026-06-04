import tkinter as tk
from tkinter import scrolledtext
import json
import threading
import time
from src.ui.widgets import BG_DEEP, BG_CARD, FG_PRIMARY, FG_GREEN, ACCENT_RED
from src.vision.capture import zoom_camera

def open_debug_json_window(ui):
    from src.utils.config import STATIC_ATTACK_FILE
    
    debug_win = tk.Toplevel(ui.root)
    debug_win.title("Debug AI JSON Deployment")
    debug_win.geometry("600x500")
    debug_win.configure(bg=BG_DEEP)
    
    lbl = tk.Label(debug_win, text="Paste JSON response from AI:", font=("Courier", 9, "bold"), bg=BG_DEEP, fg=FG_PRIMARY)
    lbl.pack(anchor="w", padx=10, pady=10)
    
    txt = scrolledtext.ScrolledText(debug_win, bg=BG_CARD, fg=FG_GREEN, font=("Courier", 9), height=20)
    txt.pack(fill="both", expand=True, padx=10, pady=5)
    
    try:
        with open(STATIC_ATTACK_FILE, "r") as f:
            saved_json = json.load(f)
        txt.insert(tk.END, json.dumps(saved_json, indent=2))
    except:
        example_json = {
          "available_troops":[
            {"name": "White Dragon", "x": 0.49, "y": 0.90, "quantity": 10},
            {"name": "Clan Castle", "x": 0.55, "y": 0.90, "quantity": 1}
          ],
          "deployment_positions":[
            {"troop_name": "White Dragon", "quantity": 2, "x": 0.5, "y": 0.5},
            {"troop_name": "Clan Castle", "quantity": 1, "x": 0.15, "y": 0.15}
          ],
          "deployment_mode": "human"
        }
        txt.insert(tk.END, json.dumps(example_json, indent=2))
    
    def save_and_execute_manual():
        raw_text = txt.get("1.0", tk.END).strip()
        try:
            data = json.loads(raw_text)
            with open(STATIC_ATTACK_FILE, "w") as f:
                json.dump(data, f, indent=2)
            ui.log_terminal("[DEBUG] Saved to config/static_attack.json & running deployment...", "sys")
            
            def run_sequence():
                ui.log_terminal("[DEBUG] Executing zoom sequence (out -> in -> out)...", "sys")
                zoom_camera(ui.hwnd, ticks=15, direction="out")
                time.sleep(1.0)
                zoom_camera(ui.hwnd, ticks=15, direction="in")
                time.sleep(1.0)
                zoom_camera(ui.hwnd, ticks=15, direction="out")
                time.sleep(1.0)
                ui.attack_manager.execute_deployment_plan(data, True)
                
            threading.Thread(target=run_sequence, daemon=True).start()
        except Exception as e:
            ui.log_terminal(f"[DEBUG] Invalid JSON: {e}", "sys")
            
    def save_only():
        raw_text = txt.get("1.0", tk.END).strip()
        try:
            data = json.loads(raw_text)
            with open(STATIC_ATTACK_FILE, "w") as f:
                json.dump(data, f, indent=2)
            ui.log_terminal("[DEBUG] Saved config/static_attack.json", "sys")
        except Exception as e:
            ui.log_terminal(f"[DEBUG] Invalid JSON: {e}", "sys")
            
    btn_frame = tk.Frame(debug_win, bg=BG_DEEP)
    btn_frame.pack(fill="x", padx=10, pady=10)
    
    btn_save = tk.Button(btn_frame, text="SAVE (FOR STATIC MODE)", command=save_only, font=("Courier", 9, "bold"), bg=BG_CARD, fg=FG_PRIMARY, cursor="hand2")
    btn_save.pack(side="left", fill="x", expand=True, padx=(0, 5))
    
    btn_exec = tk.Button(btn_frame, text="SAVE & EXECUTE NOW", command=save_and_execute_manual, font=("Courier", 9, "bold"), bg=ACCENT_RED, fg=BG_DEEP, cursor="hand2")
    btn_exec.pack(side="right", fill="x", expand=True, padx=(5, 0))
