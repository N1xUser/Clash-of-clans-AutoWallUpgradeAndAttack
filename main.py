import sys
import os
os.environ["QT_QPA_PLATFORM"] = "xcb"
import tkinter as tk

from src.utils.config import ROIS_FILE, CALIBRATION_ITEMS
from src.vision.capture import find_coc_hwnd
from src.utils.roi_manager import load_rois
from src.utils.calibration import calibrate
from src.ui.main_window import AutoWallsUI

if __name__ == "__main__":
    hwnd = find_coc_hwnd()
    if hwnd is None:
        sys.exit(1)

    force = len(sys.argv) > 1 and sys.argv[1] == "calibrate"
    rois = load_rois() if not force else None

    if rois is None or not all(r in rois for r in CALIBRATION_ITEMS):
        print("\n=== ROI CALIBRATION REQUIRED ===\n")
        rois = calibrate(hwnd, existing_rois=rois if not force else None)

    if rois:
        root = tk.Tk()
        app = AutoWallsUI(root, hwnd, rois)
        root.mainloop()
