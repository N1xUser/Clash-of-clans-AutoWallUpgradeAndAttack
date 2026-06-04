import threading
import traceback
from src.ui.controllers.vision_controller import safe_capture

def on_start_bot(ui):
    if not ui.bot_running:
        ui.bot_running = True
        ui.btn_bot.config(text="■  STOP BOT", bg="#ef4444", activebackground="#dc2626")
        ui.bot_status_lbl.config(text="● BOT RUNNING", fg="#22c55e")

        for w in ui.config_widgets:
            w.config(state="disabled")
        ui.reset_buttons()

        from src.ui.controllers.config_controller import save_state
        save_state(ui)

        e_h = ui.engine_home_var.get()
        e_u = ui.engine_upg_var.get()
        e_e = ui.engine_enemy_var.get()
        
        def get_tgt_str(use_var, val_var, suffix):
            st = use_var.get()
            if st == 1: return f"AND {val_var.get():,} {suffix}"
            if st == 2: return f"OR  {val_var.get():,} {suffix}"
            return ""

        t_g = get_tgt_str(ui.use_tgt_gold, ui.tgt_gold_var, "G")
        t_e = get_tgt_str(ui.use_tgt_elx, ui.tgt_elx_var, "E")
        t_ge = get_tgt_str(ui.use_tgt_goel, ui.tgt_goel_var, "G+E")
        t_d = get_tgt_str(ui.use_tgt_dark, ui.tgt_dark_var, "D")

        ui.log_terminal("\n[BOT] Starting Automation Sequence...", "bot")
        ui.log_terminal(f"[BOT] Home: Resources({e_h}) ➔ Upgrades({e_u})", "bot")
        ui.log_terminal(f"[BOT] Attack: Enemy Loot({e_e})", "bot")
        
        active_targets = [t for t in[t_g, t_e, t_ge, t_d] if t]
        if not active_targets: active_targets = ["NO TARGETS SET"]
        
        ui.log_terminal(f"[BOT] Min Loot:[ {' | '.join(active_targets)} ]", "bot")
        
        ui.bot_orchestrator.start_bot()
    else:
        ui.bot_running = False
        if ui.bot_orchestrator:
            ui.bot_orchestrator.stop_bot()
        ui.btn_bot.config(text="▶  START BOT", bg="#22c55e", activebackground="#16a34a")
        ui.bot_status_lbl.config(text="● BOT IDLE", fg="#737373") 
        
        for w in ui.config_widgets:
            w.config(state="normal")
        ui.reset_buttons()
        
        ui.log_terminal("\n[BOT] Automation Sequence Stopped.", "bot_off")

def run_test_autowall(ui):
    original_bot_state = ui.bot_running
    try:
        upg_info = ui.latest_data.get("upgrades_info", {})
        
        if not upg_info or "upgrades" not in upg_info:
            ui.root.after(0, ui.log_terminal, "[TEST] No upgrades cache found. Please scan upgrades first!", "bot_off")
            ui.root.after(0, lambda: ui.btn_test_wall.config(state="normal", text="TEST AUTOWALL"))
            return
        
        walls =[u for u in upg_info.get("upgrades", []) if "wall" in u.get("name", "").lower()]
        
        if not walls:
            ui.root.after(0, ui.log_terminal, "[TEST] No walls found in upgrades. Please scan upgrades!", "bot_off")
            ui.root.after(0, lambda: ui.btn_test_wall.config(state="normal", text="TEST AUTOWALL"))
            return
        
        ui.root.after(0, ui.log_terminal, f"[TEST] Found {len(walls)} wall type(s) available:", "sys")
        for w in walls:
            ui.root.after(0, ui.log_terminal, f"[TEST]   - {w.get('name', 'Unknown')} (Cost: {w.get('cost', 0):,}, Qty: {w.get('qty', 1)})", "sys")
        
        ui.root.after(0, ui.log_terminal, f"[TEST] Current Resources (from UI): Gold={ui.latest_data.get('gold', 0):,}, Elixir={ui.latest_data.get('elixir', 0):,}", "gold")
        ui.root.after(0, ui.log_terminal, f"[TEST] Latest_data dict id: {id(ui.latest_data)}", "sys")
        
        walls_copy = [w.copy() for w in walls]
        walls_copy.sort(key=lambda x: x.get("cost", float('inf')))
        ui.root.after(0, ui.log_terminal, f"[TEST] Starting upgrade sequence for {len(walls_copy)} wall type(s)...", "bot")
        
        ui.bot_running = True
        
        success = ui.upgrade_manager.upgrade_walls(walls_copy, lambda: safe_capture(ui))
        
        if success:
            ui.root.after(0, ui.log_terminal, "[TEST] AutoWall test completed successfully!", "bot")
        else:
            ui.root.after(0, ui.log_terminal, "[TEST] AutoWall test completed with issues.", "sys")
            
    except Exception as e:
        ui.root.after(0, ui.log_terminal, f"[TEST] Error during AutoWall test: {str(e)}", "bot_off")
        ui.root.after(0, ui.log_terminal, f"[TEST] Traceback: {traceback.format_exc()}", "sys")
    finally:
        ui.bot_running = original_bot_state
        ui.root.after(0, lambda: ui.btn_test_wall.config(state="normal", text="TEST AUTOWALL"))
