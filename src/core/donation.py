# --- START OF FILE donation.py ---
#
# Centralized donation module.
# Detects donation requests in clan chat and auto-donates all available troops/spells.
#

import time
import os
import cv2
import numpy as np
from datetime import datetime

from src.vision.capture import click_relative_roi, capture_frame, pan_camera


# ── Debug ───────────────────────────────────────────────────────────

def _save_debug_frame(frame, clicks, label, log_fn, save_screenshots=True):
    """
    Save a debug screenshot with click positions marked.
    clicks: list of (rel_x, rel_y, text_label) tuples
    """
    if not save_screenshots:
        return
    if frame is None or frame.size == 0:
        return
    try:
        debug_dir = os.path.join("response", "donate_debug")
        os.makedirs(debug_dir, exist_ok=True)

        debug_img = frame.copy()
        h, w = debug_img.shape[:2]

        for i, (cx, cy, txt) in enumerate(clicks):
            px, py = int(cx * w), int(cy * h)
            # Red filled circle
            cv2.circle(debug_img, (px, py), 8, (0, 0, 255), -1)
            # White border
            cv2.circle(debug_img, (px, py), 8, (255, 255, 255), 2)
            # Label
            cv2.putText(debug_img, f"{i+1}:{txt}",
                        (px + 12, py + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = os.path.join(debug_dir, f"{label}_{ts}.png")
        cv2.imwrite(filename, debug_img)
        log_fn(f"[DEBUG] Saved: {filename}", "sys")
    except Exception as e:
        log_fn(f"[DEBUG] Failed to save screenshot: {e}", "sys")


# ── Config ──────────────────────────────────────────────────────────

# Red badge on chat ICON (indicates pending requests) #BC0715 → BGR(21, 7, 188)
BADGE_COLOR_BGR = np.array([21, 7, 188])
BADGE_TOLERANCE = 25

# Chat icon badge position (on main village screen)
BADGE_X = 0.051
BADGE_Y = 0.422

# Click position to OPEN the chat panel
CHAT_OPEN_X = 0.033
CHAT_OPEN_Y = 0.454

# Green "Donate" button color (inside chat) — approximate BGR
DONATE_BTN_COLOR_BGR = np.array([60, 180, 60])  # green
DONATE_BTN_TOLERANCE = 50

# X position to scan for green Donate buttons inside the open chat
DONATE_BTN_SCAN_X = 0.275


def detect_donation_badge(frame):
    """Check if the red badge exists on the chat icon."""
    if frame is None or frame.size == 0:
        return False
    h, w = frame.shape[:2]
    px, py = int(BADGE_X * w), int(BADGE_Y * h)
    px, py = min(px, w - 1), min(py, h - 1)
    color = frame[py, px].astype(np.int32)
    return bool(np.all(np.abs(color - BADGE_COLOR_BGR) <= BADGE_TOLERANCE))


def open_chat(hwnd):
    """Click the chat icon to open the chat panel."""
    click_relative_roi(hwnd, {'x': CHAT_OPEN_X, 'y': CHAT_OPEN_Y, 'w': 0, 'h': 0})
    time.sleep(1.5)


def close_chat(hwnd):
    """Click away from chat to close it."""
    click_relative_roi(hwnd, {'x': 0.350, 'y': 0.450, 'w': 0, 'h': 0})
    time.sleep(0.5)


def click_messages_tab(hwnd):
    """Click the messages tab in chat to ensure we're on the right section."""
    click_relative_roi(hwnd, {'x': 0.340, 'y': 0.209, 'w': 0, 'h': 0})
    time.sleep(1.0)


def scroll_chat_up(hwnd):
    """Scroll up in the chat to reveal older messages/requests."""
    pan_camera(hwnd, start_rel=(0.200, 0.400), end_rel=(0.200, 0.800))
    time.sleep(1.0)


def find_donate_buttons(frame):
    """
    Scan the chat panel for green 'Donate' buttons.
    Scans along x=0.275 from y=0.10 to y=0.90 looking for green pixels.
    Measures the vertical height of green segments to exclude large banners.
    Also checks horizontal span to avoid banners broken up by text.
    Returns list of (rel_x, rel_y) tuples where Donate buttons are found.
    """
    if frame is None or frame.size == 0:
        return []
    h, w = frame.shape[:2]
    
    scan_xs = [int(0.275 * w)]
    scan_xs = [min(x, w - 1) for x in scan_xs]

    raw_found = []
    y_start = int(0.10 * h)
    y_end = int(0.90 * h)
    
    def _is_green(pixel):
        return pixel[1] > 120 and pixel[1] > pixel[0] + 30 and pixel[1] > pixel[2] + 30

    for scan_x in scan_xs:
        in_green_block = False
        block_start_y = 0
        
        for y_abs in range(y_start, y_end):
            pixel = frame[y_abs, scan_x].astype(np.int32)
            
            if _is_green(pixel):
                if not in_green_block:
                    in_green_block = True
                    block_start_y = y_abs
            else:
                if in_green_block:
                    in_green_block = False
                    block_h = y_abs - block_start_y
                    
                    # A valid Donate button height is around 1% to 8% of screen height
                    if int(0.01 * h) < block_h < int(0.08 * h):
                        center_y = int(block_start_y + block_h / 2)
                        
                        # Verify it's a right-aligned button, not a banner broken by text.
                        # Banners span the whole chat. Check if exactly left (x=0.08) is also green.
                        left_px = frame[center_y, int(0.08 * w)].astype(np.int32)
                        if not _is_green(left_px):
                            raw_found.append((float(scan_x) / w, float(center_y) / h))

        # Handle green block ending at the bound
        if in_green_block:
            block_h = y_end - block_start_y
            if int(0.01 * h) < block_h < int(0.08 * h):
                center_y = int(block_start_y + block_h / 2)
                left_px = frame[center_y, int(0.08 * w)].astype(np.int32)
                if not _is_green(left_px):
                    raw_found.append((float(scan_x) / w, float(center_y) / h))

    # De-duplicate buttons that are roughly at the same Y level
    found = []
    for rx, ry in raw_found:
        if not any(abs(ry - ey) < 0.05 for _, ey in found):
            found.append((rx, ry))

    # Sort top-to-bottom
    found.sort(key=lambda item: item[1])
    return found


def _verify_color(frame, rel_x, rel_y, target_bgr, tolerance=15):
    """Check if the pixel at (rel_x, rel_y) matches target_bgr within tolerance."""
    if frame is None or frame.size == 0:
        return False
    h, w = frame.shape[:2]
    px, py = int(rel_x * w), int(rel_y * h)
    px, py = min(max(0, px), w - 1), min(max(0, py), h - 1)
    pixel = frame[py, px].astype(np.int32)
    return bool(np.all(np.abs(pixel - target_bgr) <= tolerance))


def _find_colorful_cards(frame):
    """
    Find available (colorful) donation cards using the exact #CBCBCB color mask approach.
    1. Crop to X: 0.314-0.780, Y: 0.003-0.995 to limit search.
    2. Mask exact #CBCBCB (BGR 203, 203, 203).
    3. Find the largest contour (Troops rectangle) and get its top-right corner.
    4. Compute troops and spells regions relative to this top-right corner.
    5. Sample card centers (7x2 for troops, 7x1 for spells) and check for colorfulness.
    """
    if frame is None or frame.size == 0:
        return [], 0, 0

    h, w = frame.shape[:2]

    # 1. Crop to search area
    rx1, ry1 = 0.314, 0.003
    rx2, ry2 = 0.780, 0.995
    cx1, cy1 = int(rx1 * w), int(ry1 * h)
    cx2, cy2 = int(rx2 * w), int(ry2 * h)
    
    # safeguard bounds
    cx1, cy1 = max(0, cx1), max(0, cy1)
    cx2, cy2 = min(w, cx2), min(h, cy2)
    
    if cx1 >= cx2 or cy1 >= cy2:
        return [], 0, 0

    cropped = frame[cy1:cy2, cx1:cx2]

    # 2. Mask exact #CBCBCB (BGR 203, 203, 203) or #E7E7E7 (BGR 231, 231, 231)
    target_bgr1 = np.array([203, 203, 203], dtype=np.uint8)
    target_bgr2 = np.array([231, 231, 231], dtype=np.uint8)
    
    mask1 = cv2.inRange(cropped, target_bgr1, target_bgr1)
    mask2 = cv2.inRange(cropped, target_bgr2, target_bgr2)
    mask = cv2.bitwise_or(mask1, mask2)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return [], 0, 0
        
    # Get the bounding box of the largest #CBCBCB contour (which is the Troops container)
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, rw, rh = cv2.boundingRect(largest_contour)
    
    # Top-right corner of the Troops container in full-image relative coords
    tr_x = (cx1 + x + rw) / w
    tr_y = (cy1 + y) / h
    
    # The reference right edge is 0.750 and top edge is 0.143
    ref_tr_x, ref_tr_y = 0.750, 0.143
    offset_x = tr_x - ref_tr_x
    offset_y = tr_y - ref_tr_y
    
    # Troops rectangle (with offsets applied)
    t_rx1 = 0.340 + offset_x
    t_ry1 = 0.143 + offset_y
    t_rx2 = 0.750 + offset_x
    t_ry2 = 0.404 + offset_y
    
    # Spells rectangle (with offsets applied)
    s_rx1 = 0.338 + offset_x
    s_ry1 = 0.464 + offset_y
    s_rx2 = 0.756 + offset_x
    s_ry2 = 0.597 + offset_y
    
    available = []
    
    # Helper to check if a card center is colorful
    def _is_card_colorful(cx_r, cy_r):
        sx, sy = int(cx_r * w), int(cy_r * h)
        patch = frame[max(0, sy - 8):sy + 9, max(0, sx - 8):sx + 9]
        if patch.size == 0:
            return False
        # Calculate color range
        mean_c = np.mean(patch, axis=(0, 1))
        ch_range = float(np.max(mean_c) - np.min(mean_c))
        # More than a 25 difference between RGB channels means it's colorful (not grayscale)
        return ch_range > 25

    # Troops: 7 cols, 2 rows
    for row in range(2):
        for col in range(7):
            cx_r = t_rx1 + (t_rx2 - t_rx1) * (col + 0.5) / 7.0
            cy_r = t_ry1 + (t_ry2 - t_ry1) * (row + 0.5) / 2.0
            if _is_card_colorful(cx_r, cy_r):
                available.append((cx_r, cy_r))
                
    # Spells: 7 cols, 1 row
    for col in range(7):
        cx_r = s_rx1 + (s_rx2 - s_rx1) * (col + 0.5) / 7.0
        cy_r = s_ry1 + (s_ry2 - s_ry1) * 0.5
        if _is_card_colorful(cx_r, cy_r):
            available.append((cx_r, cy_r))
            
    return available, offset_x, offset_y


# ── Donation actions ────────────────────────────────────────────────

def donate_all_available(hwnd, capture_fn, log_fn, max_clicks=20, save_screenshots=True, test_mode=False):
    """Scan → click one card → rescan → repeat until no colorful cards remain.
    If no cards are found, swipe right to check if more are available."""
    total_clicked = 0
    troops_scrolls = 0
    spells_scrolls = 0

    for attempt in range(max_clicks):
        frame = capture_fn()
        if frame is None:
            log_fn("[DONATE] Failed to capture donation popup.", "bot_off")
            break

        cards, offset_x, offset_y = _find_colorful_cards(frame)
        
        if test_mode:
            cards = [] # Force empty to trigger swiping
            
        if not cards:
            if troops_scrolls < 3:
                log_fn(f"[DONATE] No available cards in view. Swiping troops ({troops_scrolls+1}/3)...", "sys")
                start_x, end_x = 0.725 + offset_x, 0.310 + offset_x
                y_coord = 0.404 - ((0.404-0.143)*0.5) + offset_y
                _save_debug_frame(frame, [(start_x, y_coord, "swipe_start"), (end_x, y_coord, "swipe_end")], f"04_donate_swipe_troops_{troops_scrolls+1}", log_fn, save_screenshots)
                pan_camera(hwnd, start_rel=(start_x, y_coord), end_rel=(end_x, y_coord), stop_inertia=True)
                time.sleep(1.0)
                troops_scrolls += 1
                continue
            elif spells_scrolls < 2:
                log_fn(f"[DONATE] No available cards in view. Swiping spells ({spells_scrolls+1}/2)...", "sys")
                start_x, end_x = 0.700 + offset_x, 0.400 + offset_x
                y_coord = 0.597 - ((0.597-0.464)*0.5) + offset_y
                _save_debug_frame(frame, [(start_x, y_coord, "swipe_start"), (end_x, y_coord, "swipe_end")], f"04_donate_swipe_spells_{spells_scrolls+1}", log_fn, save_screenshots)
                pan_camera(hwnd, start_rel=(start_x, y_coord), end_rel=(end_x, y_coord), stop_inertia=True)
                time.sleep(1.0)
                spells_scrolls += 1
                continue
            else:
                break

        if total_clicked == 0 and troops_scrolls == 0 and spells_scrolls == 0:
            log_fn(f"[DONATE] Found available cards. Donating...", "bot")

        cx, cy = cards[0]
        
        _save_debug_frame(frame, [(cx, cy, f"click_{total_clicked+1}")], f"04_donate_click_{attempt+1}", log_fn, save_screenshots)

        click_relative_roi(hwnd, {'x': cx, 'y': cy, 'w': 0, 'h': 0})
        time.sleep(0.4)
        total_clicked += 1

        # Check if popup is still open
        check_frame = capture_fn()
        is_popup_open = _verify_color(check_frame, 0.327, 0.372, np.array([203, 203, 203]), tolerance=5) or \
                        _verify_color(check_frame, 0.327, 0.505, np.array([203, 203, 203]), tolerance=5) or \
                        _verify_color(check_frame, 0.327, 0.372, np.array([231, 231, 231]), tolerance=5) or \
                        _verify_color(check_frame, 0.327, 0.505, np.array([231, 231, 231]), tolerance=5)
        if not is_popup_open:
            log_fn("[DONATE] Donation popup closed automatically after click.", "sys")
            break

    if total_clicked > 0:
        log_fn(f"[DONATE] Donated {total_clicked} card(s).", "bot")
    else:
        log_fn("[DONATE] No available cards found in popup.", "sys")


def close_donation_popup(hwnd):
    """Close the donation popup by clicking outside."""
    click_relative_roi(hwnd, {'x': 0.900, 'y': 0.130, 'w': 0, 'h': 0})
    time.sleep(0.5)


# ── Main donation routine ──────────────────────────────────────────

def run_donation_cycle(hwnd, capture_fn, log_fn, skip_detection=False, save_screenshots=True):
    """
    Full donation cycle:
    1. Check for donation badge on chat icon
    2. Open chat
    3. Find green Donate buttons
    4. Click each, donate all available cards
    5. Close chat
    """
    all_clicks = []  # track all clicks for debug image

    # Step 1: Check badge (unless skipping)
    if not skip_detection:
        frame = capture_fn()
        _save_debug_frame(frame, [(BADGE_X, BADGE_Y, "badge_check")], "01_badge_check", log_fn, save_screenshots)
        if not detect_donation_badge(frame):
            log_fn("[DONATE] No donation requests detected.", "sys")
            return 0

    # Step 2: Open the chat panel
    log_fn("[DONATE] Opening chat panel...", "bot")
    all_clicks.append((CHAT_OPEN_X, CHAT_OPEN_Y, "open_chat"))
    open_chat(hwnd)
    time.sleep(1.0)
    
    # Verify we are on the valid chat screen (#D59524 at X0.345 Y0.425 or #F3AA29 at X0.339 Y0.431)
    frame = capture_fn()
    is_chat_open = _verify_color(frame, 0.345, 0.425, np.array([36, 149, 213]), tolerance=20) or \
                   _verify_color(frame, 0.339, 0.431, np.array([41, 170, 243]), tolerance=20)
    if not is_chat_open:
        log_fn("[DONATE] Valid chat screen not detected (#D59524 / #F3AA29 check failed).", "sys")
        close_chat(hwnd)
        return 0

    donated = 0
    max_donations = 10
    
    # Step 3 & 4: Continuously scan and process Donate buttons
    while donated < max_donations:
        time.sleep(1.0)
        frame = capture_fn()

        donate_positions = find_donate_buttons(frame)

        # Save debug: chat open with detected donate button positions
        btn_clicks = [(x, y, f"donate_btn") for x, y in donate_positions]
        _save_debug_frame(frame, btn_clicks, f"02_chat_scan_{donated}", log_fn, save_screenshots)

        if not donate_positions:
            # Check for green indicator buttons that jump to pending requests (#84B212 -> BGR 18, 178, 132)
            target_indicator_bgr = np.array([18, 178, 132])
            
            if _verify_color(frame, 0.301, 0.109, target_indicator_bgr, tolerance=25):
                log_fn("[DONATE] Found top indicator button. Clicking to jump to request...", "sys")
                click_relative_roi(hwnd, {'x': 0.301, 'y': 0.109, 'w': 0, 'h': 0})
                time.sleep(0.7)
                continue
            elif _verify_color(frame, 0.301, 0.881, target_indicator_bgr, tolerance=25):
                log_fn("[DONATE] Found bottom indicator button. Clicking to jump to request...", "sys")
                click_relative_roi(hwnd, {'x': 0.301, 'y': 0.881, 'w': 0, 'h': 0})
                time.sleep(0.7)
                continue
            else:
                log_fn("[DONATE] No visible donate buttons or indicators found.", "sys")
                break # Exit the loop if no buttons or indicators are found

        # We found at least one button. Click the first one.
        btn_x, btn_y = donate_positions[0]
        log_fn(f"[DONATE] Clicking Donate button at x={btn_x:.3f}, y={btn_y:.3f}...", "sys")
        all_clicks.append((btn_x, btn_y, f"donate_btn_{donated}"))

        # Click the green Donate button
        click_relative_roi(hwnd, {'x': btn_x, 'y': btn_y, 'w': 0, 'h': 0})
        time.sleep(1.5)

        # Verify donation popup opened successfully (#CBCBCB or #E7E7E7 at X0.327 Y0.372 or X0.327 Y0.505)
        popup_frame = capture_fn()
        valid_popup = _verify_color(popup_frame, 0.327, 0.372, np.array([203, 203, 203]), tolerance=5) or \
                      _verify_color(popup_frame, 0.327, 0.505, np.array([203, 203, 203]), tolerance=5) or \
                      _verify_color(popup_frame, 0.327, 0.372, np.array([231, 231, 231]), tolerance=5) or \
                      _verify_color(popup_frame, 0.327, 0.505, np.array([231, 231, 231]), tolerance=5)
        
        if not valid_popup:
            log_fn("[DONATE] Donation popup did not open successfully.", "sys")
            break

        # Save debug: donation popup opened
        popup_cards, _, _ = _find_colorful_cards(popup_frame)
        card_clicks = [(cx, cy, f"card") for cx, cy in popup_cards]
        _save_debug_frame(popup_frame, card_clicks, f"03_popup_{donated}", log_fn, save_screenshots)

        # Donate all available cards in the popup
        donate_all_available(hwnd, capture_fn, log_fn, save_screenshots=save_screenshots)

        # Check if the popup is still open before trying to close it
        post_donate_frame = capture_fn()
        is_popup_open = _verify_color(post_donate_frame, 0.327, 0.372, np.array([203, 203, 203]), tolerance=5) or \
                        _verify_color(post_donate_frame, 0.327, 0.505, np.array([203, 203, 203]), tolerance=5) or \
                        _verify_color(post_donate_frame, 0.327, 0.372, np.array([231, 231, 231]), tolerance=5) or \
                        _verify_color(post_donate_frame, 0.327, 0.505, np.array([231, 231, 231]), tolerance=5)
        
        # Close the donation popup
        if is_popup_open:
            close_donation_popup(hwnd)
            time.sleep(1.0)
        
        # Verify chat is active again (#D59524 at X0.345 Y0.425 or #F3AA29 at X0.339 Y0.431)
        after_frame = capture_fn()
        is_chat_active = _verify_color(after_frame, 0.345, 0.425, np.array([36, 149, 213]), tolerance=20) or \
                         _verify_color(after_frame, 0.339, 0.431, np.array([41, 170, 243]), tolerance=20)
        if not is_chat_active:
            log_fn("[DONATE] Failed to return to chat screen after donation.", "sys")
            break

        # Return to messages section for next request
        click_messages_tab(hwnd)

        donated += 1

    log_fn(f"[DONATE] Donation cycle complete. Processed {donated} request(s).", "bot")

    # Step 5: Close chat
    close_chat(hwnd)

    return donated
