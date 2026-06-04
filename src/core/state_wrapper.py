"""
SimpleStateManager — thin adapter between the UI (AutoWallsUI) and BotOrchestrator.

Delegates OCR scanning to the existing controller functions while
exposing a clean interface that BotOrchestrator can call without
touching tkinter widgets directly.
"""

import time

from src.ui.controllers.ocr_controller import run_ocr_once, run_detect_builders

class SimpleStateManager:
    """Wraps the UI instance to give BotOrchestrator a state-oriented API."""

    def __init__(self, ui):
        self._ui = ui

    def get_state(self):
        return self._ui.latest_data
    
    def deduct_gold(self, amount):
        self._ui.latest_data["gold"] -= amount
        
    def deduct_elixir(self, amount):
        self._ui.latest_data["elixir"] -= amount
        
    def get_gold(self):
        return self._ui.latest_data.get("gold", 0)
        
    def get_elixir(self):
        return self._ui.latest_data.get("elixir", 0)
        
    def remove_zero_qty_walls(self):
        pass
        
    def count_remaining_walls(self):
        upg_info = self._ui.latest_data.get("upgrades_info", {})
        walls = [u for u in upg_info.get("upgrades", []) if "wall" in u.get("name", "").lower()]
        return sum(w.get("qty", 0) for w in walls)

    # ── home / enemy resource scanning ──────────────────────────────

    def scan_home_resources(self):
        """Run an OCR scan on the home screen (gold / elixir / dark)."""
        engine = (
            self._ui.engine_home_var.get()
            if hasattr(self._ui, "engine_home_var")
            else "RAPID"
        )
        # Use the controller function directly
        run_ocr_once(self._ui, engine)

    def scan_enemy_loot(self) -> dict:
        """Run an OCR scan on the enemy screen and return results."""
        engine = (
            self._ui.engine_enemy_var.get()
            if hasattr(self._ui, "engine_enemy_var")
            else "RAPID"
        )
        # Use the controller function directly
        run_ocr_once(self._ui, engine)
        data = self._ui.latest_data
        return {
            "gold": data.get("enemy_gold", 0),
            "elixir": data.get("enemy_elixir", 0),
            "dark_elixir": data.get("enemy_dark_elixir", 0),
        }

    # ── upgrades cache ──────────────────────────────────────────────

    def get_last_upgrades_scan_time(self) -> float:
        return self._ui.state_cache.get("last_upgrade_scan", 0)

    def has_upgrades_cache(self) -> bool:
        upg = self._ui.latest_data.get("upgrades_info", {})
        return bool(upg.get("upgrades"))

    def get_latest_upgrades(self) -> dict:
        return self._ui.latest_data.get("upgrades_info", {})

    def update_upgrades_cache(self, upgrades: dict):
        self._ui.state_cache["upgrades_cache"] = upgrades
        self._ui.state_cache["last_upgrade_scan"] = time.time()
        self._ui.latest_data["upgrades_info"] = upgrades

    def restore_upgrades_from_cache(self):
        cached = self._ui.state_cache.get("upgrades_cache")
        if cached:
            self._ui.latest_data["upgrades_info"] = cached

    def load_upgrades_from_cache(self):
        cached = self._ui.state_cache.get("upgrades_cache")
        if cached:
            self._ui.latest_data["upgrades_info"] = cached

    # ── wall helpers ────────────────────────────────────────────────

    def get_wall_upgrades(self) -> list:
        upg = self._ui.latest_data.get("upgrades_info", {})
        return [
            item
            for item in upg.get("upgrades", [])
            if "wall" in item.get("name", "").lower()
        ]
