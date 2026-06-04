import time
import datetime
import tkinter as tk
import json

from src.vision.capture import zoom_camera, click_relative_roi, pan_camera, scroll_roi
from src.vision.detection import crop_roi, preprocess_for_ocr, is_main_screen, is_battle_screen
from src.vision.ocr import (
    extract_all_tesseract, extract_all_glm, extract_all_rapid,
    extract_upgrades_tesseract, extract_upgrades_glm, extract_upgrades_rapid,
    extract_builders_tesseract, extract_builders_glm, extract_builders_rapid
)
from src.ui.controllers.vision_controller import safe_capture

def run_ocr_once(ui, engine: str):
    engine = engine.lower()
    start = time.time()
    frame = safe_capture(ui)
    if frame is None:
        ui.root.after(0, ui.log_terminal, "[!] Failed to capture frame.", "sys")
        ui.root.after(0, ui.reset_buttons)
        return

    raw = ui.latest_data.copy()
    on_main_screen = is_main_screen(frame, ui.rois["main_screen_i"])

    if on_main_screen:
        ui.root.after(0, ui.log_terminal,
                        "  - Home Screen detected. Preparing sea background...", "sys")
        
        time.sleep(1.0)
        
        frame = safe_capture(ui)
        if frame is None:
            ui.root.after(0, ui.reset_buttons)
            return

        builders_proc = preprocess_for_ocr(
            crop_roi(frame, ui.rois["builders_icon"]), "builders_icon")
        if   engine == "tesseract": raw["builders"] = extract_builders_tesseract(builders_proc)
        elif engine == "glm":       raw["builders"] = extract_builders_glm(builders_proc)
        elif engine == "rapid":     raw["builders"] = extract_builders_rapid(builders_proc)

        ui.root.after(0, ui.log_terminal,
                        "  ▸ Scanning HOME resources & BUILDERS...", "sys")
        scan_keys =["gold", "elixir", "dark_elixir"]
    elif is_battle_screen(frame):
        ui.root.after(0, ui.log_terminal,
                        "  ▸ Battle Screen detected. Scanning ENEMY resources...", "sys")
        scan_keys =["enemy_gold", "enemy_elixir", "enemy_dark_elixir"]
    else:
        ui.root.after(0, ui.log_terminal,
                        "[ERROR] Not on home or battle screen. Cannot scan.", "bot_off")
        ui.root.after(0, ui.reset_buttons)
        return

    crops =[preprocess_for_ocr(crop_roi(frame, ui.rois[k]), k) for k in scan_keys]
    if engine == "tesseract":
        res = extract_all_tesseract(crops)
        for i, k in enumerate(scan_keys): raw[k] = res[i] if i < len(res) else 0
    elif engine == "glm":
        res = extract_all_glm(crops)
        for i, k in enumerate(scan_keys): raw[k] = res[i] if i < len(res) else 0
    elif engine == "rapid":
        res = extract_all_rapid(crops)
        for i, k in enumerate(scan_keys): raw[k] = res[i] if i < len(res) else 0

    ui.latest_data = raw.copy()
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    elapsed = time.time() - start
    ui.root.after(0, apply_update, ui, raw, ts, elapsed, engine)

def run_detect_builders(ui, engine: str, is_bot=False):
    engine = engine.lower()
    ui.is_scanning_upgrades = True
    start = time.time()
    frame = safe_capture(ui)

    if frame is None:
        ui.root.after(0, ui.log_terminal, "  [!] Failed to capture frame.", "sys")
        ui.root.after(0, ui.reset_buttons)
        ui.is_scanning_upgrades = False
        return

    if not is_main_screen(frame, ui.rois["main_screen_i"]):
        ui.root.after(0, ui.log_terminal,
                        "[!] Must be on Home Screen to detect builders.", "sys")
        ui.root.after(0, ui.reset_buttons)
        ui.is_scanning_upgrades = False
        return

    ui.root.after(0, ui.log_terminal, "  ▸ Preparing sea background...", "sys")
    
    time.sleep(1.0)
    
    zoom_camera(ui.hwnd, ticks=15, direction="out")
    time.sleep(0.5)
    
    corner_top_right = {"x": 0.95, "y": 0.05, "w": 0, "h": 0}
    click_relative_roi(ui.hwnd, corner_top_right)
    time.sleep(0.5)
    
    click_relative_roi(ui.hwnd, ui.rois["builders_icon"])
    time.sleep(1.0)
    
    menu_x = ui.rois["upgrades_menu"]["x"] + (ui.rois["upgrades_menu"]["w"] / 2.0)
    menu_y = ui.rois["upgrades_menu"]["y"]
    menu_h = ui.rois["upgrades_menu"]["h"]
    pan_camera(ui.hwnd, start_rel=(menu_x, menu_y + menu_h * 0.3), end_rel=(menu_x, menu_y + menu_h * 0.8), drag_speed=15)
    time.sleep(0.5)
    
    click_relative_roi(ui.hwnd, corner_top_right)
    time.sleep(0.5)
    
    click_relative_roi(ui.hwnd, ui.rois["builders_icon"])
    ui.root.after(0, ui.log_terminal, "  ▸ Menu opened. Starting scroll scan...", "sys")
    time.sleep(1.0)

    raw = ui.latest_data.copy()
    master, seen, combined =[], set(), ""
    
    empty_scrolls = 0
    MAX_PAGES = 25

    for idx in range(MAX_PAGES):
        if is_bot and not ui.bot_running:
            ui.root.after(0, ui.log_terminal, "  [!] Upgrades scan aborted by user.", "bot_off")
            ui.is_scanning_upgrades = False
            ui.root.after(0, ui.reset_buttons)
            return 

        ui.root.after(0, ui.log_terminal, f"    - Scanning Page {idx+1}...", "sys")
        time.sleep(0.5)
        frame = safe_capture(ui)
        if frame is None: break

        proc = preprocess_for_ocr(crop_roi(frame, ui.rois["upgrades_menu"]), "upgrades_menu")
        ui.current_upgrade_preview = proc

        if   engine == "tesseract": data = extract_upgrades_tesseract(proc)
        elif engine == "glm":       data = extract_upgrades_glm(proc)
        elif engine == "rapid":     data = extract_upgrades_rapid(proc)

        new = 0
        for item in data.get("upgrades", []):
            uid = f"{item['name']}_{item['cost']}"
            if uid not in seen:
                seen.add(uid); master.append(item); new += 1

        combined += f"\n--- Page {idx+1} ---\n{data.get('raw_text', '')}"
        
        if new == 0:
            empty_scrolls += 1
            if empty_scrolls >= 2:
                ui.root.after(0, ui.log_terminal, "  ✓ End of upgrades list.", "sys")
                break
            else:
                ui.root.after(0, ui.log_terminal, "    ⚠ No new items, trying one more scroll...", "sys")
        else:
            empty_scrolls = 0

        scroll_roi(ui.hwnd, ui.rois["upgrades_menu"])
        time.sleep(1.7)

    raw["upgrades_info"] = {
        "engine": engine, "total_items_found": len(master),
        "upgrades": master, "raw_text": combined.strip(),
    }
    ui.latest_data = raw.copy()
    
    import time as time_module
    ui.state_cache["last_upgrade_scan"] = time_module.time()
    
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    elapsed = time.time() - start
    ui.root.after(0, apply_update, ui, raw, ts, elapsed, engine)
    ui.current_upgrade_preview = None
    ui.is_scanning_upgrades = False

def apply_update(ui, raw: dict, ts: str, elapsed: float, engine: str):
    ui.card_gold.set_value(raw["gold"]);                ui.card_gold.push_spark(raw["gold"])
    ui.card_elixir.set_value(raw["elixir"]);            ui.card_elixir.push_spark(raw["elixir"])
    ui.card_dark.set_value(raw["dark_elixir"]);         ui.card_dark.push_spark(raw["dark_elixir"])
    ui.card_enemy_gold.set_value(raw["enemy_gold"]);    ui.card_enemy_gold.push_spark(raw["enemy_gold"])
    ui.card_enemy_elixir.set_value(raw["enemy_elixir"]); ui.card_enemy_elixir.push_spark(raw["enemy_elixir"])
    ui.card_enemy_dark.set_value(raw["enemy_dark_elixir"]); ui.card_enemy_dark.push_spark(raw["enemy_dark_elixir"])

    ui.badge_builders.set(raw.get("builders", "?/?"))
    upg = raw.get("upgrades_info", {})
    walls = sum(item.get("qty", 1) for item in upg.get("upgrades",[])
                if "wall" in item.get("name", "").lower())
    ui.badge_walls.set(str(walls))

    txt = json.dumps(upg, indent=2) if isinstance(upg, dict) else str(upg)
    ui.upgrades_text.configure(state="normal")
    ui.upgrades_text.delete(1.0, tk.END)
    ui.upgrades_text.insert(tk.END, txt)
    ui.upgrades_text.configure(state="disabled")
    
    from src.ui.controllers.walls_controller import render_walls_ui
    render_walls_ui(ui)

    ui.log_rich(ts, raw)
    ui.log_terminal(f"  ✓ {engine.upper()} scan complete in {elapsed:.2f}s\n", "sys")
    ui.reset_buttons()
