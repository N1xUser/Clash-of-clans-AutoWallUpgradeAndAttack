import json
import threading
from pathlib import Path
from typing import Dict, Any, Optional


class BotState:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.status_file = self.config_dir / "status.json"
        
        self.capture_lock = threading.Lock()
        
        self.bot_running = False
        self.latest_data = {
            "resources": {},
            "enemy_resources": {},
            "builders": {},
            "upgrades_info": {}
        }
        
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_status(self) -> bool:
        if not self.status_file.exists():
            return False
        
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with self.capture_lock:
                self.bot_running = data.get("bot_running", False)
                self.latest_data = data.get("latest_data", {
                    "resources": {},
                    "enemy_resources": {},
                    "builders": {},
                    "upgrades_info": {}
                })
            
            return True
        except Exception:
            return False
    
    def save_status(self) -> bool:
        try:
            with self.capture_lock:
                data = {
                    "bot_running": self.bot_running,
                    "latest_data": self.latest_data
                }
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            
            return True
        except Exception:
            return False
    
    def is_running(self) -> bool:
        with self.capture_lock:
            return self.bot_running
    
    def start(self):
        with self.capture_lock:
            self.bot_running = True
        self.save_status()
    
    def stop(self):
        with self.capture_lock:
            self.bot_running = False
        self.save_status()
    
    def get_latest_data(self) -> Dict[str, Any]:
        with self.capture_lock:
            return self.latest_data.copy()
    
    def update_resources(self, resources: Dict[str, Any]):
        with self.capture_lock:
            self.latest_data["resources"] = resources
        self.save_status()
    
    def update_enemy_resources(self, enemy_resources: Dict[str, Any]):
        with self.capture_lock:
            self.latest_data["enemy_resources"] = enemy_resources
        self.save_status()
    
    def update_builders(self, builders: Dict[str, Any]):
        with self.capture_lock:
            self.latest_data["builders"] = builders
        self.save_status()
    
    def update_upgrades_info(self, upgrades_info: Dict[str, Any]):
        with self.capture_lock:
            self.latest_data["upgrades_info"] = upgrades_info
        self.save_status()
    
    def update_all_data(self, resources: Optional[Dict[str, Any]] = None,
                       enemy_resources: Optional[Dict[str, Any]] = None,
                       builders: Optional[Dict[str, Any]] = None,
                       upgrades_info: Optional[Dict[str, Any]] = None):
        with self.capture_lock:
            if resources is not None:
                self.latest_data["resources"] = resources
            if enemy_resources is not None:
                self.latest_data["enemy_resources"] = enemy_resources
            if builders is not None:
                self.latest_data["builders"] = builders
            if upgrades_info is not None:
                self.latest_data["upgrades_info"] = upgrades_info
        self.save_status()
    
    def get_resources(self) -> Dict[str, Any]:
        with self.capture_lock:
            return self.latest_data.get("resources", {}).copy()
    
    def get_enemy_resources(self) -> Dict[str, Any]:
        with self.capture_lock:
            return self.latest_data.get("enemy_resources", {}).copy()
    
    def get_builders(self) -> Dict[str, Any]:
        with self.capture_lock:
            return self.latest_data.get("builders", {}).copy()
    
    def get_upgrades_info(self) -> Dict[str, Any]:
        with self.capture_lock:
            return self.latest_data.get("upgrades_info", {}).copy()
    
    def reset_data(self):
        with self.capture_lock:
            self.latest_data = {
                "resources": {},
                "enemy_resources": {},
                "builders": {},
                "upgrades_info": {}
            }
        self.save_status()
