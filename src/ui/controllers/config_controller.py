import json

def load_state(ui):
    from src.utils.config import STATUS_FILE
    
    if not STATUS_FILE.exists():
        return
        
    try:
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        ui.state_cache = loaded
        cfg = loaded.get("config", {})
        
        if "engine_home" in cfg: ui.engine_home_var.set(cfg["engine_home"])
        if "engine_upg" in cfg: ui.engine_upg_var.set(cfg["engine_upg"])
        if "engine_enemy" in cfg: ui.engine_enemy_var.set(cfg["engine_enemy"])
        if "engine_wall" in cfg: ui.engine_wall_var.set(cfg["engine_wall"])
        if "use_tgt_gold" in cfg: ui.use_tgt_gold.set(cfg["use_tgt_gold"])
        if "use_tgt_elx" in cfg: ui.use_tgt_elx.set(cfg["use_tgt_elx"])
        if "use_tgt_goel" in cfg: ui.use_tgt_goel.set(cfg["use_tgt_goel"])
        if "use_tgt_dark" in cfg: ui.use_tgt_dark.set(cfg["use_tgt_dark"])
        if "tgt_gold" in cfg: ui.tgt_gold_var.set(cfg["tgt_gold"])
        if "tgt_elx" in cfg: ui.tgt_elx_var.set(cfg["tgt_elx"])
        if "tgt_goel" in cfg: ui.tgt_goel_var.set(cfg["tgt_goel"])
        if "tgt_dark" in cfg: ui.tgt_dark_var.set(cfg["tgt_dark"])
        if "ai_mode" in cfg: ui.ai_mode_var.set(cfg["ai_mode"])
        if "ai_model" in cfg: ui.ai_model_var.set(cfg["ai_model"])
        if "api_key" in cfg: ui.gemini_api_var.set(cfg["api_key"])
        if "auto_reinforce" in cfg: ui.auto_reinforce_var.set(cfg["auto_reinforce"])
        if "clan_donate" in cfg: ui.clan_donate_var.set(cfg["clan_donate"])
        if "anti_afk" in cfg: ui.anti_afk_var.set(cfg["anti_afk"])
        if "auto_wall" in cfg: ui.auto_wall_var.set(cfg["auto_wall"])
        if "wall_check_freq" in cfg: ui.wall_check_freq_var.set(cfg["wall_check_freq"])
        if "debug_ss" in cfg: ui.debug_ss_var.set(cfg["debug_ss"])
        if "opacity" in cfg and hasattr(ui, 'transparency_var'):
            ui.transparency_var.set(cfg["opacity"])
            ui._on_transparency_change(cfg["opacity"])
        
        cached_upg = ui.state_cache.get("upgrades_info")
        if cached_upg:
            ui.latest_data["upgrades_info"] = cached_upg
            
            walls = sum(item.get("qty", 1) for item in cached_upg.get("upgrades",[])
                        if "wall" in item.get("name", "").lower())
            ui.badge_walls.set(str(walls))
            
            from src.ui.controllers.walls_controller import render_walls_ui
            ui.root.after(100, lambda: render_walls_ui(ui))
        
        if hasattr(ui, 'global_validate_and_update'):
            ui.global_validate_and_update()
    except Exception:
        pass

def save_state(ui):
    from src.utils.config import STATUS_FILE
    
    ui.state_cache["config"] = {
        "engine_home": ui.engine_home_var.get(),
        "engine_upg": ui.engine_upg_var.get(),
        "engine_enemy": ui.engine_enemy_var.get(),
        "engine_wall": ui.engine_wall_var.get(),
        "use_tgt_gold": ui.use_tgt_gold.get(),
        "use_tgt_elx": ui.use_tgt_elx.get(),
        "use_tgt_goel": ui.use_tgt_goel.get(),
        "use_tgt_dark": ui.use_tgt_dark.get(),
        "tgt_gold": ui.tgt_gold_var.get(),
        "tgt_elx": ui.tgt_elx_var.get(),
        "tgt_goel": ui.tgt_goel_var.get(),
        "tgt_dark": ui.tgt_dark_var.get(),
        "ai_mode": ui.ai_mode_var.get(),
        "ai_model": ui.ai_model_var.get(),
        "api_key": ui.gemini_api_var.get(),
        "auto_reinforce": ui.auto_reinforce_var.get(),
        "clan_donate": ui.clan_donate_var.get(),
        "anti_afk": ui.anti_afk_var.get(),
        "auto_wall": ui.auto_wall_var.get(),
        "wall_check_freq": ui.wall_check_freq_var.get(),
        "debug_ss": ui.debug_ss_var.get() if hasattr(ui, 'debug_ss_var') else True,
        "opacity": ui.transparency_var.get() if hasattr(ui, 'transparency_var') else 100
    }
    
    try:
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ui.state_cache, f, indent=4)
    except Exception:
        pass
