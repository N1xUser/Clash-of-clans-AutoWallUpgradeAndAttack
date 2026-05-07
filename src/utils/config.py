from pathlib import Path

ROIS_FILE = Path("config/rois.json")
STATUS_FILE = Path("config/status.json")
STATIC_ATTACK_FILE = Path("config/static_attack.json")


RESOURCES =[
    "gold", "elixir", "dark_elixir",
    "enemy_gold", "enemy_elixir", "enemy_dark_elixir"
]

UI_ELEMENTS =["main_screen_i", "upgrades_menu", "builders_icon"]

CALIBRATION_ITEMS = RESOURCES + UI_ELEMENTS

ROI_COLORS = {
    "gold":              (0, 215, 255),
    "elixir":            (255, 0, 200),
    "dark_elixir":       (180, 180, 180),
    "enemy_gold":        (0, 215, 255),
    "enemy_elixir":      (255, 0, 200),
    "enemy_dark_elixir": (180, 180, 180),
    "main_screen_i":     (255, 255, 255),
    "upgrades_menu":     (100, 255, 100),
    "builders_icon":     (255, 200, 100), # Light orange for Builders status
}

HEADER_OFFSET_PX = 36
PW_RENDERFULLCONTENT = 2


UPGRADES_SCROLL_TICKS = 2
UPGRADES_SCROLL_AMOUNT = -120