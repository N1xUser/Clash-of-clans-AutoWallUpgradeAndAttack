import json
from src.utils.config import ROIS_FILE

def save_rois(rois: dict):
    with open(ROIS_FILE, "w") as f:
        json.dump(rois, f, indent=2)
    print(f"[OK] ROIs saved in {ROIS_FILE}")
    print(json.dumps(rois, indent=2))

def load_rois() -> dict | None:
    if ROIS_FILE.exists():
        with open(ROIS_FILE) as f:
            data = json.load(f)
        print(f"[OK] ROIs loaded from {ROIS_FILE}")
        return data
    return None