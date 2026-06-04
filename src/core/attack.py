import time
import random
import json
import os
import cv2
import numpy as np
from datetime import datetime

from src.vision.capture import click_relative_roi


class ReloadGameException(Exception):
    pass


class AttackManager:

    # --- TROOP DEPLOYMENT ---
    # Delay after clicking the troop card at the bottom to select it. 
    # Increase if the bot switches troops too fast and the game doesn't register it.
    ROBOT_DELAY_AFTER_SELECT = 0.05 
    
    # Delay after clicking the map to deploy the selected troop. 
    # Increase if the bot drops troops too fast and the game skips some placements.
    ROBOT_DELAY_AFTER_DROP = 0.03
    
    # --- SPELL DEPLOYMENT ---
    # Delay after clicking a spell card to select it.
    SPELL_DELAY_AFTER_SELECT = 0.2
    
    # Delay after dropping a spell on the map.
    SPELL_DELAY_AFTER_DROP = 0.1
    
    # Delay to wait after ALL spells are dropped before moving to Heroes.
    SPELL_DELAY_TRANSITION = 0.5

    # --- HERO DEPLOYMENT & ABILITIES ---
    # Delay after clicking a hero card to select them.
    HERO_DELAY_AFTER_SELECT = 0.15
    
    # Delay after dropping a hero on the map.
    HERO_DELAY_AFTER_DROP = 0.1
    
    # Crucial delay: Time to wait for heroes to spawn, land, and start walking 
    # BEFORE clicking their cards again to activate their abilities.
    HERO_DELAY_BEFORE_ABILITY = 3.0
    
    # Delay after clicking the hero card to activate their ability.
    HERO_DELAY_AFTER_ABILITY = 0.1
    # =====================================================================

    SEGMENTS =[
        (0.161, 0.368, 0.364, 0.077),
        (0.615, 0.057, 0.812, 0.338),
        (0.821, 0.578, 0.681, 0.799),
        (0.251, 0.710, 0.184, 0.611)
    ]
    
    def __init__(self, hwnd, rois, ai_config, log_callback, capture_callback, bot_running_callback, config_getters=None):
        self.hwnd = hwnd
        self.rois = rois
        self.ai_config = ai_config
        self.log_terminal = log_callback
        self._safe_capture = capture_callback
        self.get_bot_running = bot_running_callback
        self.config_getters = config_getters or {}
        self.current_layout_style = "expanded"
    
    def get_active_targets(self):
        get_tgt = self.config_getters.get("get_target_info")
        if get_tgt:
            return get_tgt()
        return "NO TARGETS CONFIGURED"
    
    def is_auto_reinforce_enabled(self):
        get_reinforce = self.config_getters.get("get_auto_reinforce")
        return get_reinforce() if get_reinforce else False

    def is_clan_donate_enabled(self):
        get_donate = self.config_getters.get("get_clan_donate")
        return get_donate() if get_donate else False
    
    def validate_loot(self, gold, elixir, dark):
        validator = self.config_getters.get("validate_loot")
        if validator:
            return validator(gold, elixir, dark)
        return True
    
    def get_ai_mode(self):
        get_mode = self.config_getters.get("get_ai_mode")
        if get_mode:
            return get_mode()
        return "none"
    
    def detect_and_plan_attack(self, frame):
        return None
    
    def execute_fallback_deployment(self, is_debug=False):
        self.log_terminal("[BOT] Executing fallback deployment (no JSON/empty config)...", "bot")
        
        tracked_drops = []
        last_capture_time = time.time()
        
        # 1. Loop through all dynamically detected cards
        if getattr(self, "detected_cards", None):
            self.log_terminal(f"[BOT] Fallback: Found {len(self.detected_cards)} cards visually. Auto-deploying all...", "sys")
            for i, (cx, cy) in enumerate(self.detected_cards):
                if not self.get_bot_running() and not is_debug:
                    self.log_terminal("[BOT] Fallback deployment aborted by user.", "bot_off")
                    return
                
                self.log_terminal(f"[BOT] Fallback: Selecting Card {i+1} at ({cx:.3f}, {cy:.3f})...", "sys")
                
                # Select the card slot
                click_relative_roi(self.hwnd, {"x": cx, "y": cy, "w": 0.0, "h": 0.0})
                time.sleep(self.ROBOT_DELAY_AFTER_SELECT)
                
                # Deploy 100 times along the red border lines
                for drop_idx in range(100):
                    if not self.get_bot_running() and not is_debug:
                        self.log_terminal("[BOT] Fallback deployment aborted by user.", "bot_off")
                        return
                    
                    dx, dy = self._get_red_line_point(random.random())
                    click_relative_roi(self.hwnd, {"x": dx, "y": dy, "w": 0.0, "h": 0.0})
                    time.sleep(self.ROBOT_DELAY_AFTER_DROP)
                    
                    # Capture occasionally to keep state updated
                    if time.time() - last_capture_time > 1.0:
                        try:
                            self._safe_capture()
                            last_capture_time = time.time()
                        except ReloadGameException:
                            raise
                            
                    if drop_idx % 10 == 0:
                        tracked_drops.append((dx, dy, f"Card {i+1}"))
        else:
            self.log_terminal("[WARN] Fallback: No cards detected visually! Aborting automated deployment.", "sys")
            return

        # Save deployment visualization
        if tracked_drops:
            self._save_deployment_visualization([("drop", dx, dy, 0, n) for dx, dy, n in tracked_drops])
            
        # 2. Wait 10 seconds
        if self.get_bot_running() or is_debug:
            self.log_terminal("[BOT] Fallback: Waiting 10 seconds before activating hero abilities...", "sys")
            for _ in range(10):
                if not self.get_bot_running() and not is_debug:
                    self.log_terminal("[BOT] Fallback deployment aborted by user.", "bot_off")
                    return
                time.sleep(1.0)
                
        # 3. Press once all the cards again to activate the heroes
        self.log_terminal("[BOT] Fallback: Activating hero abilities...", "bot")
        for i, (cx, cy) in enumerate(getattr(self, "detected_cards", [])):
            if not self.get_bot_running() and not is_debug:
                self.log_terminal("[BOT] Fallback deployment aborted by user.", "bot_off")
                return
            
            self.log_terminal(f"[BOT] Fallback: Activating Card {i+1}...", "sys")
            click_relative_roi(self.hwnd, {"x": cx, "y": cy, "w": 0.0, "h": 0.0})
            time.sleep(self.HERO_DELAY_AFTER_ABILITY)
            
            if time.time() - last_capture_time > 1.0:
                try:
                    self._safe_capture()
                    last_capture_time = time.time()
                except ReloadGameException:
                    raise
                    
        self.log_terminal("[BOT] Automated Fallback Sequence Stopped.", "bot")
        self.log_terminal("[BOT] Fallback Deployment Complete! Watching battle...", "bot")

    def execute_deployment_plan(self, ai_data, is_debug=False):
        if not ai_data:
            ai_data = {}
            
        self.current_layout_style = ai_data.get("layout_style", "expanded")
        
        deployment_mode = ai_data.get("deployment_mode")
        if isinstance(deployment_mode, list) and len(deployment_mode) > 0:
            deployment_mode = deployment_mode[0]
        
        deployment = ai_data.get("deployment_positions",[])
        troops_list = ai_data.get("available_troops", [])
        spells_list = ai_data.get("available_spells",[])
        heroes_list = ai_data.get("available_heros",[])
        
        # --- DYNAMIC CARD DETECTION ---
        frame = self._safe_capture()
        if frame is not None:
            self.detected_cards = self._detect_card_squares(frame)
            if self.detected_cards:
                self.log_terminal(f"[BOT] Visually detected {len(self.detected_cards)} cards on the deployment bar.", "bot")
            else:
                self.log_terminal("[WARN] Failed to visually detect any cards. Falling back to static math.", "sys")
        else:
            self.detected_cards = []
        # ------------------------------
        
        # 1. Check if fallback deployment is needed
        if not troops_list and not spells_list and not heroes_list and not deployment:
            self.execute_fallback_deployment(is_debug)
            return
            
        # 2. Check if available troops are provided but no manual deployment_positions
        if not deployment and (troops_list or spells_list or heroes_list):
            self.log_terminal("[BOT] Troops/Spells/Heroes provided but no deployment positions. Auto-assigning card slots...", "sys")
            self._assign_positions_by_order(troops_list, spells_list, heroes_list)
            if not isinstance(deployment_mode, str) or deployment_mode.lower() not in ["human", "random", "robot"]:
                deployment_mode = "human"
            self.execute_advanced_deployment(deployment_mode.lower(), troops_list, spells_list, heroes_list, is_debug)
            return
            
        if isinstance(deployment_mode, str) and deployment_mode.lower() in ["human", "random", "robot"]:
            self.execute_advanced_deployment(deployment_mode.lower(), troops_list, spells_list, heroes_list, is_debug)
            return

        self.log_terminal("[BOT] Precalculating Attack Plan...", "sys")
        
        action_queue = []
        tracked_drops =[]
        
        for dep in deployment:
            t_name = dep.get("troop_name", "")
            qty = dep.get("quantity", 1)
            dx = float(dep.get("x", 0))
            dy = float(dep.get("y", 0))
            
            troop_info = next((t for t in troops_list if t.get("name") == t_name), None)
            if not troop_info:
                self.log_terminal(f"[WARN] Troop '{t_name}' not found in available troops! Skipping.", "bot_off")
                continue
                
            t_cx, t_cy = self._get_troop_center(troop_info)
            
            action_queue.append(("select", t_cx, t_cy, self.ROBOT_DELAY_AFTER_SELECT, t_name))
            
            for _ in range(qty):
                action_queue.append(("drop", dx, dy, self.ROBOT_DELAY_AFTER_DROP, t_name))
                tracked_drops.append((dx, dy, t_name))
        
        if action_queue:
            self._save_deployment_visualization(action_queue)
            
        self.log_terminal(f"[BOT] Executing fast deployment ({len(action_queue)} actions)...", "bot")
        
        last_capture_time = time.time()
        for act_type, x, y, delay, label in action_queue:
            if not self.get_bot_running() and not is_debug:
                self.log_terminal("[BOT] Deployment aborted by user.", "bot_off")
                break
            
            click_relative_roi(self.hwnd, {"x": x, "y": y, "w": 0.0, "h": 0.0})
            time.sleep(delay)
            
            if time.time() - last_capture_time > 1.0:
                try:
                    self._safe_capture()
                    last_capture_time = time.time()
                except ReloadGameException:
                    raise
            
        if self.get_bot_running() or is_debug:
            self.log_terminal("[BOT] Deployment Complete! Watching battle...", "bot")
    
    def execute_advanced_deployment(self, mode, troops_list, spells_list, heroes_list, is_debug):
        self.log_terminal(f"[BOT] Precalculating Advanced Deployment ({mode})...", "bot")
        
        action_queue = []
        tracked_drops =[]
        
        # ----------------------------------------------------
        # 1. TROOPS CALCULATION
        # ----------------------------------------------------
        global_card_idx = 0
        if mode == "human":
            for troop in troops_list:
                t_qty = troop.get("quantity", 15)
                if t_qty <= 0: continue
                t_name = troop.get("name", "Unknown")
                t_cx, t_cy = self._get_troop_center(troop, global_card_idx)
                global_card_idx += 1
                
                # Select troop once
                action_queue.append(("select", t_cx, t_cy, self.ROBOT_DELAY_AFTER_SELECT, t_name))
                
                # Queue drops
                for i in range(t_qty):
                    dx, dy = self._get_red_line_point(i / max(1, t_qty - 1))
                    action_queue.append(("drop", dx, dy, self.ROBOT_DELAY_AFTER_DROP, t_name))
                    tracked_drops.append((dx, dy, t_name))
                
        elif mode == "random":
            click_counts = {i: 0 for i in range(len(troops_list))}
            last_troop_idx = None
            
            while True:
                available_indices =[i for i, c in click_counts.items() if c < troops_list[i].get("quantity", 15)]
                if not available_indices:
                    break
                
                troop_idx = random.choice(available_indices)
                troop = troops_list[troop_idx]
                t_name = troop.get("name", "Unknown")
                t_qty = troop.get("quantity", 15)
                t_cx, t_cy = self._get_troop_center(troop, troop_idx)
                
                # Only select if it changed from the last random selection
                if troop_idx != last_troop_idx:
                    action_queue.append(("select", t_cx, t_cy, self.ROBOT_DELAY_AFTER_SELECT, t_name))
                    last_troop_idx = troop_idx
                
                puts = min(3, t_qty - click_counts[troop_idx])
                for _ in range(puts):
                    dx, dy = self._get_red_line_point(random.random())
                    action_queue.append(("drop", dx, dy, self.ROBOT_DELAY_AFTER_DROP, t_name))
                    tracked_drops.append((dx, dy, t_name))
                    click_counts[troop_idx] += 1
                
        elif mode == "robot":
            robot_sequence =[]
            for idx, troop in enumerate(troops_list):
                qty = troop.get("quantity", 15)
                robot_sequence.extend([idx] * qty)
            
            total_clicks = len(robot_sequence)
            if total_clicks > 0:
                counts = {i: 0 for i in range(len(troops_list))}
                interleaved_sequence =[]
                while len(interleaved_sequence) < total_clicks:
                    for i, troop in enumerate(troops_list):
                        if counts[i] < troop.get("quantity", 15):
                            interleaved_sequence.append(i)
                            counts[i] += 1

                total_per_seg = [0, 0, 0, 0]
                for i in range(total_clicks):
                    total_per_seg[i % 4] += 1
                
                seg_counts = [0, 0, 0, 0]
                last_troop_idx = None

                for i, troop_idx in enumerate(interleaved_sequence):
                    troop = troops_list[troop_idx]
                    t_name = troop.get("name", "Unknown")
                    t_cx, t_cy = self._get_troop_center(troop, troop_idx)
                    
                    # 🔥 Massive speed boost: only click selection card if the troop changed
                    if troop_idx != last_troop_idx:
                        action_queue.append(("select", t_cx, t_cy, self.ROBOT_DELAY_AFTER_SELECT, t_name))
                        last_troop_idx = troop_idx
                    
                    seg = i % 4
                    local_idx = seg_counts[seg]
                    seg_counts[seg] += 1
                    
                    local_t = local_idx / max(1, total_per_seg[seg] - 1) if total_per_seg[seg] > 1 else 0.5
                    dx, dy = self._get_segment_point(seg, local_t)
                    
                    action_queue.append(("drop", dx, dy, self.ROBOT_DELAY_AFTER_DROP, t_name))
                    tracked_drops.append((dx, dy, t_name))

        # ----------------------------------------------------
        # 2. HEROES CALCULATION
        # ----------------------------------------------------
        global_card_idx = len(troops_list)
        hero_drops = []
        if heroes_list:
            for i, hero in enumerate(heroes_list):
                h_name = hero.get("name", "Unknown")
                h_cx, h_cy = self._get_troop_center(hero, global_card_idx)
                global_card_idx += 1
                
                action_queue.append(("select", h_cx, h_cy, self.HERO_DELAY_AFTER_SELECT, h_name))
                
                seg = i % 4
                dx, dy = self._get_segment_point(seg, 0.5)
                
                action_queue.append(("drop", dx, dy, self.HERO_DELAY_AFTER_DROP, h_name))
                tracked_drops.append((dx, dy, h_name))
                
                power_delay = hero.get("power_delay", 7)
                hero_drops.append((h_name, h_cx, h_cy, power_delay))

        # ----------------------------------------------------
        # 3. SPELLS CALCULATION
        # ----------------------------------------------------
        if spells_list:
            for spell in spells_list:
                s_name = spell.get("name", "Unknown Spell")
                s_qty = spell.get("quantity", 1)
                if s_qty <= 0: continue
                s_cx, s_cy = self._get_troop_center(spell, global_card_idx)
                global_card_idx += 1
                
                action_queue.append(("select", s_cx, s_cy, self.SPELL_DELAY_AFTER_SELECT, s_name))
                for _ in range(s_qty):
                    dx = random.uniform(0.35, 0.65)
                    dy = random.uniform(0.35, 0.65)
                    action_queue.append(("drop", dx, dy, self.SPELL_DELAY_AFTER_DROP, s_name))
                    tracked_drops.append((dx, dy, s_name))
                    
            # Transition wait after spells
            action_queue.append(("wait", 0, 0, self.SPELL_DELAY_TRANSITION, "Wait for Spells"))
            
        if hero_drops:
                # Sort by power_delay so we wait incrementally
                hero_drops_sorted = sorted(hero_drops, key=lambda h: h[3])
                elapsed = 0.0
                for h_name, h_cx, h_cy, p_delay in hero_drops_sorted:
                    wait_now = max(0, p_delay - elapsed)
                    if wait_now > 0:
                        action_queue.append(("wait", 0, 0, wait_now, f"Wait {wait_now:.1f}s for {h_name} ability"))
                        elapsed += wait_now
                    action_queue.append(("select", h_cx, h_cy, self.HERO_DELAY_AFTER_ABILITY, f"Ability {h_name}"))

        # ----------------------------------------------------
        # 4. PRE-VISUALIZATION (Save screenshot before executing)
        # ----------------------------------------------------
        if action_queue:
            self._save_deployment_visualization(action_queue)

        # ----------------------------------------------------
        # 5. EXECUTE ALL FAST QUEUED ACTIONS
        # ----------------------------------------------------
        self.log_terminal(f"[BOT] Executing rapid deployment ({len(action_queue)} actions)...", "bot")
        
        last_capture_time = time.time()
        for act_type, x, y, delay, label in action_queue:
            if not self.get_bot_running() and not is_debug:
                self.log_terminal("[BOT] Deployment aborted by user.", "bot_off")
                break
                
            if act_type == "select" or act_type == "drop":
                click_relative_roi(self.hwnd, {"x": x, "y": y, "w": 0.0, "h": 0.0})
                time.sleep(delay)
            elif act_type == "wait":
                self.log_terminal(f"[BOT] {label} ({delay}s)...", "sys")
                time.sleep(delay)
                
            # Run heavy safe_capture loop only once a second to avoid bottlenecking fast drops
            if time.time() - last_capture_time > 1.0:
                try:
                    self._safe_capture()
                    last_capture_time = time.time()
                except ReloadGameException:
                    raise

        if self.get_bot_running() or is_debug:
            self.log_terminal("[BOT] Advanced Deployment Complete! Watching battle...", "bot")
            
    def analyze_base_with_ai(self, image):
        ui_model = self.ai_config.get("model", "GEMINI FLASH LITE")
        self.log_terminal(f"[AI] Connecting to {ui_model}...", "bot")
        try:
            from google import genai
            from google.genai import types
            import PIL.Image
        except ImportError:
            self.log_terminal("[ERROR] 'google-genai' package is not installed. Please pip install google-genai", "sys")
            return None

        api_key = self.ai_config.get("api_key", "")
        if not api_key:
            self.log_terminal("[ERROR] Gemini API Key is missing. Please set it in config.", "sys")
            return None

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = PIL.Image.fromarray(image_rgb)

        client = genai.Client(api_key=api_key)
        
        try:
            from pydantic import BaseModel, Field
        except ImportError:
            self.log_terminal("[ERROR] 'pydantic' is missing. Please pip install pydantic", "sys")
            return None

        class BoundingBoxBase(BaseModel):
            box_2d: list[int] = Field(description="[y_min, x_min, y_max, x_max] coordinates (0-1000)")

        class Troop(BoundingBoxBase):
            name: str = Field(description="Name of the troop (e.g. Electro Dragon, Lightning Spell)")
            quantity: int = Field(default=15, description="Number of troops available for this unit")

        class Deployment(BaseModel):
            troop_name: str
            quantity: int
            box_2d: list[int] = Field(description="[y_min, x_min, y_max, x_max] coordinate of where to deploy. MUST be on the corners or very far of the village because you can't place directly on the village.")

        class AttackPlan(BaseModel):
            air_defenses: list[BoundingBoxBase] = Field(description="List of air defense buildings. Each will be destroyed by 3 lightning spells.")
            available_troops: list[Troop] = Field(description="Available troops for the attack found at the bottom of the screen. ONLY Electro Dragon, the 4 heroes, lightning spells, log launcher, and clan donations.")
            deployment_positions: list[Deployment] = Field(description="Optimal deployment positions to execute the attack against the air defenses. Keep coordinates far from the village.")

        prompt = "Analyze the image for a Clash of Clans attack. Identify air defenses, available troops, and provide an optimal deployment plan keeping troop placements very far outside the village borders or corners."
        
        model_map = {
            "GEMINI FLASH LITE": "gemini-3.1-flash-lite-preview",
            "GEMINI 1.5 PRO": "gemini-1.5-pro",
            "GEMINI 3 FLASH PREVIEW": "gemini-3-flash-preview",
            "GEMINI 3.1 PRO PREVIEW": "gemini-3.1-pro-preview",
            "GPT-4O MINI": "gpt-4o-mini"
        }
        actual_model = model_map.get(ui_model, "gemini-3.1-flash-lite-preview")

        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AttackPlan,
                temperature=0.4
            )
            response = client.models.generate_content(
                model=actual_model,
                contents=[prompt, pil_img],
                config=config
            )
            
            plan = response.parsed
            
            data = {
                "air_defenses":[],
                "available_troops": [],
                "deployment_positions":[]
            }
            
            if plan:
                for ad in plan.air_defenses:
                    if len(ad.box_2d) == 4:
                        y1, x1, y2, x2 = ad.box_2d
                        data["air_defenses"].append({"ymin": y1/1000.0, "xmin": x1/1000.0, "ymax": y2/1000.0, "xmax": x2/1000.0})
                        
                for tr in plan.available_troops:
                    if len(tr.box_2d) == 4:
                        y1, x1, y2, x2 = tr.box_2d
                        data["available_troops"].append({"name": tr.name, "quantity": tr.quantity, "ymin": y1/1000.0, "xmin": x1/1000.0, "ymax": y2/1000.0, "xmax": x2/1000.0})
                        
                for dep in plan.deployment_positions:
                    if len(dep.box_2d) == 4:
                        y1, x1, y2, x2 = dep.box_2d
                        cx = (x1 + x2) / 2.0 / 1000.0
                        cy = (y1 + y2) / 2.0 / 1000.0
                        data["deployment_positions"].append({"troop_name": dep.troop_name, "quantity": dep.quantity, "x": cx, "y": cy})
            
            save_screenshots = self.config_getters.get("get_debug_screenshots", lambda: True)()
            
            if save_screenshots:
                try:
                    import json
                    import os
                    from datetime import datetime
                    
                    resp_dir = "response"
                    os.makedirs(resp_dir, exist_ok=True)
                    
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    req_dir = os.path.join(resp_dir, f"request_{ts}")
                    os.makedirs(req_dir, exist_ok=True)
                    
                    img_path = os.path.join(req_dir, "screenshot.png")
                    pil_img.save(img_path)
                    
                    txt_path = os.path.join(req_dir, "raw_response.txt")
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(response.text if response.text else "No text response")
                        
                    json_path = os.path.join(req_dir, "parsed.json")
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                        
                    marked_img = image.copy()
                    img_h, img_w = marked_img.shape[:2]
                    
                    for ad in data.get("air_defenses",[]):
                        x1, y1 = int(ad.get("xmin", 0) * img_w), int(ad.get("ymin", 0) * img_h)
                        x2, y2 = int(ad.get("xmax", 0) * img_w), int(ad.get("ymax", 0) * img_h)
                        cv2.rectangle(marked_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(marked_img, "AD", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        
                    for tr in data.get("available_troops",[]):
                        x1, y1 = int(tr.get("xmin", 0) * img_w), int(tr.get("ymin", 0) * img_h)
                        x2, y2 = int(tr.get("xmax", 0) * img_w), int(tr.get("ymax", 0) * img_h)
                        cv2.rectangle(marked_img, (x1, y1), (x2, y2), (255, 255, 0), 2)
                        cx = (tr.get("xmin", 0) + tr.get("xmax", 0)) / 2.0
                        cy = (tr.get("ymin", 0) + tr.get("ymax", 0)) / 2.0
                        text = f"{tr.get('name', '')} (X:{cx:.3f}, Y:{cy:.3f})"
                        cv2.putText(marked_img, text, (x1, max(15, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 2)
                        
                    for dep in data.get("deployment_positions",[]):
                        dx, dy = int(dep.get("x", 0) * img_w), int(dep.get("y", 0) * img_h)
                        cv2.circle(marked_img, (dx, dy), 6, (0, 255, 0), -1)
                        cv2.putText(marked_img, f"{dep.get('quantity', 1)}x {dep.get('troop_name', '')}", (dx + 8, dy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                    marked_path = os.path.join(req_dir, "marked_screenshot.png")
                    cv2.imwrite(marked_path, marked_img)
                        
                    self.log_terminal(f"[AI] Saved response logs to {req_dir}", "sys")
                except Exception as save_err:
                    self.log_terminal(f"[WARN] Failed to save AI response logs: {save_err}", "sys")

            return data
        except Exception as e:
            self.log_terminal(f"[ERROR] Gemini API Request Failed: {e}", "sys")
            return None
    
    def _get_segment_point(self, seg_idx, t):
        s = self.SEGMENTS[seg_idx % 4]
        x = s[0] + t * (s[2] - s[0])
        y = s[1] + t * (s[3] - s[1])
        return x, y

    def _get_red_line_point(self, t):
        s1, s2, s3, s4 = self.SEGMENTS
        
        l1 = ((s1[2]-s1[0])**2 + (s1[3]-s1[1])**2)**0.5
        l2 = ((s2[2]-s2[0])**2 + (s2[3]-s2[1])**2)**0.5
        l3 = ((s3[2]-s3[0])**2 + (s3[3]-s3[1])**2)**0.5
        l4 = ((s4[2]-s4[0])**2 + (s4[3]-s4[1])**2)**0.5
        
        total = l1 + l2 + l3 + l4
        t1 = l1 / total
        t2 = t1 + l2 / total
        t3 = t2 + l3 / total
        
        if t <= t1:
            p = t / t1
            x = s1[0] + p * (s1[2] - s1[0])
            y = s1[1] + p * (s1[3] - s1[1])
        elif t <= t2:
            p = (t - t1) / (t2 - t1)
            x = s2[0] + p * (s2[2] - s2[0])
            y = s2[1] + p * (s2[3] - s2[1])
        elif t <= t3:
            p = (t - t2) / (t3 - t2)
            x = s3[0] + p * (s3[2] - s3[0])
            y = s3[1] + p * (s3[3] - s3[1])
        else:
            p = (t - t3) / (1.0 - t3)
            x = s4[0] + p * (s4[2] - s4[0])
            y = s4[1] + p * (s4[3] - s4[1])
        return x, y

    def _detect_card_squares(self, frame):
        """Scans the bottom of the screen for the #292828 level-indicator squares."""
        if frame is None or frame.size == 0:
            return []
            
        h, w = frame.shape[:2]
        
        # User specified extreme deployment area bounds.
        min_x = int(0.05 * w)
        max_x = int(0.95 * w)
        min_y = int(0.80 * h)
        max_y = h
        
        cropped = frame[min_y:max_y, min_x:max_x]
        
        # 1. True Dark Gray Mask (#292828)
        lower_gray = np.array([20, 20, 20], dtype=np.uint8)
        upper_gray = np.array([70, 70, 70], dtype=np.uint8)
        mask_gray_range = cv2.inRange(cropped, lower_gray, upper_gray)
        
        # Mathematically enforce "grayness" (R, G, B channels must be close in value)
        # This perfectly rejects dark blue water, dark green grass, and dark brown rocks.
        b, g, r = cv2.split(cropped)
        max_c = np.maximum(np.maximum(b, g), r)
        min_c = np.minimum(np.minimum(b, g), r)
        grayness = cv2.subtract(max_c, min_c)
        mask_true_gray = cv2.bitwise_and(mask_gray_range, cv2.inRange(grayness, 0, 15))
        
        # 2. Gold Max Level Box (#C19348)
        lower_gold = np.array([30, 90, 130], dtype=np.uint8)
        upper_gold = np.array([110, 190, 255], dtype=np.uint8)
        mask_gold = cv2.inRange(cropped, lower_gold, upper_gold)
        
        mask = cv2.bitwise_or(mask_true_gray, mask_gold)
        
        # Slight dilation to connect the broken gray border around the white level text
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        # Save vision mask for debugging colors
        if self.config_getters.get("get_debug_screenshots", lambda: True)():
            try:
                os.makedirs("response", exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(f"response/vision_mask_debug_{ts}.png", mask)
            except:
                pass
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Level squares are small. Usually 15-1000 pixels.
            if 15 < area < 1000:
                x, y, cw, ch = cv2.boundingRect(cnt)
                # Loose aspect ratio since the white text breaks it into a hollow rectangle
                aspect_ratio = float(cw) / max(1, ch)
                if 0.4 < aspect_ratio < 2.5:
                    # Center of the level box
                    cx_rel = (min_x + x + cw / 2.0) / w
                    cy_rel = (min_y + y + ch / 2.0) / h
                    
                    # Offset RIGHT and UP from the bottom-left level box 
                    # to hit the dead center of the card
                    cx_rel += 0.020
                    cy_rel -= 0.040
                    
                    # Ensure it's inside the deployment bar bounds
                    if cy_rel > 0.81:
                        detected.append((cx_rel, cy_rel))
                    
        # Filter duplicates that are very close to each other
        filtered = []
        for cx, cy in detected:
            if not any(abs(cx - ex) < 0.02 and abs(cy - ey) < 0.02 for ex, ey in filtered):
                filtered.append((cx, cy))
                
        # Sort top-to-bottom (grouping into rows), then left-to-right.
        # We group Y into "bands" of 5% of screen height to handle slight pixel variations in the same row.
        filtered.sort(key=lambda p: (int(p[1] * 20), p[0]))
        return filtered

    def _get_troop_center(self, troop_info, global_index=None):
        # 1. If we have dynamically detected squares, use them sequentially!
        if getattr(self, "detected_cards", None) and global_index is not None:
            if global_index < len(self.detected_cards):
                return self.detected_cards[global_index]
                
        # 2. If it has dynamic AI bounding box (e.g. from detect_and_plan_attack)
        if "xmin" in troop_info and "ymin" in troop_info:
            t_xmin = float(troop_info.get("xmin", 0))
            t_ymin = float(troop_info.get("ymin", 0))
            t_xmax = float(troop_info.get("xmax", 0))
            t_ymax = float(troop_info.get("ymax", 0))
            if t_xmin > 0 and t_ymax > 0:
                return (t_xmin + t_xmax) / 2.0, (t_ymin + t_ymax) / 2.0
                
        # 3. Fallback to assigned static positions
        if "pos" in troop_info:
            return self._get_card_coords(troop_info["pos"])
        if "x" in troop_info and "y" in troop_info:
            return float(troop_info["x"]), float(troop_info["y"])
            
        return 0.0, 0.0

    def _get_card_coords(self, pos_str: str) -> tuple[float, float]:
        try:
            parts = pos_str.split(",")
            row = int(parts[0].strip())
            col = int(parts[1].strip())
            
            style = str(getattr(self, "current_layout_style", "expanded")).strip().lower()
            if style == "standard":
                y = 0.864
                x = 0.281 + (col - 1) * 0.050
                return x, y
            
            # Determine Y coordinate based on row (1 or 2)
            if row == 1:
                y = 0.850
            elif row == 2:
                y = 0.950
            else:
                y = 0.950
                
            # Determine X coordinate based on column (1-indexed)
            if col <= 1:
                x = 0.160
            elif col == 2:
                x = 0.195
            else:
                x = 0.195 + (col - 2) * 0.040
                
            return x, y
        except Exception:
            return 0.0, 0.0

    def _assign_positions_by_order(self, troops_list, spells_list, heroes_list):
        card_idx = 0
        for troop in troops_list:
            if "pos" not in troop:
                row = 1 if card_idx < 14 else 2
                col = (card_idx % 14) + 1
                troop["pos"] = f"{row},{col}"
            card_idx += 1
        for hero in heroes_list:
            if "pos" not in hero:
                row = 1 if card_idx < 14 else 2
                col = (card_idx % 14) + 1
                hero["pos"] = f"{row},{col}"
            card_idx += 1
        for spell in spells_list:
            if "pos" not in spell:
                row = 1 if card_idx < 14 else 2
                col = (card_idx % 14) + 1
                spell["pos"] = f"{row},{col}"
            card_idx += 1
    
    def _save_deployment_visualization(self, action_queue):
        if not self.config_getters.get("get_debug_screenshots", lambda: True)():
            return
            
        self.log_terminal("[DEBUG] Generating deployment visualization...", "sys")
        try:
            frame = self._safe_capture()
            if frame is None:
                frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
                
            debug_img = frame.copy()
            h, w = debug_img.shape[:2]
            
            drop_idx = 1
            for act_type, dx, dy, delay, label in action_queue:
                if act_type == "wait":
                    continue
                px, py = int(dx * w), int(dy * h)
                
                if act_type == "select":
                    cv2.circle(debug_img, (px, py), 15, (255, 0, 0), 2)
                    cv2.putText(debug_img, f"SEL: {label}", (px - 20, py - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                elif act_type == "drop":
                    cv2.circle(debug_img, (px, py), 6, (0, 0, 255), -1)
                    cv2.putText(debug_img, str(drop_idx), (px + 8, py + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    drop_idx += 1
                
            os.makedirs("response", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = f"response/deployment_debug_{ts}.png"
            cv2.imwrite(out_path, debug_img)
            self.log_terminal(f"[DEBUG] Saved visualization: {out_path}", "bot")
        except Exception as e:
            self.log_terminal(f"[ERROR] Failed to create deployment visualization: {e}", "sys")