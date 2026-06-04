# --- START OF FILE recovery.py ---
# 
# Centralized recovery module. All recovery behavior lives here.
# Modify this file to change how the bot recovers from unknown states.
#

import time
import numpy as np

from src.vision.capture import click_relative_roi, send_esc_key
from src.vision.detection import is_main_screen, is_battle_screen


# ── Detection helpers ───────────────────────────────────────────────

def detect_battle_screen(frame):
    return is_battle_screen(frame)


def detect_match_end(frame):
    if frame is None or frame.size == 0:
        return False
    h, w = frame.shape[:2]
    s1_x, s1_y = int(0.870 * w), int(0.445 * h)
    s2_x, s2_y = int(0.170 * w), int(0.540 * h)
    crop1 = frame[max(0, s1_y-2):s1_y+3, max(0, s1_x-2):s1_x+3]
    crop2 = frame[max(0, s2_y-2):s2_y+3, max(0, s2_x-2):s2_x+3]
    s_col1 = np.mean(crop1) if crop1.size > 0 else 255
    s_col2 = np.mean(crop2) if crop2.size > 0 else 255
    return s_col1 < 20 and s_col2 < 20


# ── Recovery clicks ─────────────────────────────────────────────────

def click_return_home(hwnd):
    """Click the Return Home / OK button on match-end screen."""
    click_relative_roi(hwnd, {'x': 0.505, 'y': 0.850, 'w': 0, 'h': 0})
    time.sleep(3.0)


def click_recovery_sequence(hwnd):
    """Standard recovery: dismiss popups by clicking center-bottom + top-right."""
    click_relative_roi(hwnd, {'x': 0.990, 'y': 0.205, 'w': 0, 'h': 0})
    time.sleep(0.1)
    click_relative_roi(hwnd, {'x': 0.990, 'y': 0.205, 'w': 0, 'h': 0})
    time.sleep(0.1)
    click_relative_roi(hwnd, {'x': 0.990, 'y': 0.205, 'w': 0, 'h': 0})
    time.sleep(0.1)
    click_relative_roi(hwnd, {'x': 0.990, 'y': 0.205, 'w': 0, 'h': 0})
    time.sleep(0.1)


def esc_recovery(hwnd):
    send_esc_key(hwnd)
    time.sleep(1.5)

# ── Main recovery routine ──────────────────────────────────────────

def attempt_recovery(hwnd, rois, capture_fn, log_fn):
    """
    Attempt to recover to the main village screen.
    
    Args:
        hwnd:       Window handle of the emulator
        rois:       ROI dictionary (needs 'main_screen_i')
        capture_fn: Callable that returns a frame (or None)
        log_fn:     Callable(message, tag) for logging
    
    Returns:
        "main_screen"   — successfully recovered to home village
        "battle"        — detected active battle screen
        "failed"        — could not recover
    """
    frame = capture_fn()
    if frame is None:
        log_fn("[RECOVERY] Failed to capture frame.", "bot_off")
        return "failed"

    # Already on main screen
    if is_main_screen(frame, rois['main_screen_i']):
        log_fn("[RECOVERY] Already on main screen.", "sys")
        return "main_screen"

    # Active battle
    if detect_battle_screen(frame):
        log_fn("[RECOVERY] Battle screen detected!", "bot")
        return "battle"

    # Match end screen
    if detect_match_end(frame):
        log_fn("[RECOVERY] Match End screen detected. Clicking Return Home...", "bot")
        click_return_home(hwnd)
    else:
        # Unknown state — try standard recovery clicks
        log_fn("[RECOVERY] Not on main screen. Attempting recovery clicks...", "sys")
        click_recovery_sequence(hwnd)

    # Recheck after clicks
    recheck = capture_fn()
    if recheck is not None and is_main_screen(recheck, rois['main_screen_i']):
        log_fn("[RECOVERY] Recovery successful! Main screen detected.", "bot")
        return "main_screen"

    # Last resort: ESC key
    log_fn("[RECOVERY] Clicks failed. Sending ESC key...", "sys")
    esc_recovery(hwnd)

    recheck2 = capture_fn()
    if recheck2 is not None and is_main_screen(recheck2, rois['main_screen_i']):
        log_fn("[RECOVERY] ESC recovery successful!", "bot")
        return "main_screen"

    log_fn("[RECOVERY] Still not on main screen.", "bot_off")
    return "failed"
