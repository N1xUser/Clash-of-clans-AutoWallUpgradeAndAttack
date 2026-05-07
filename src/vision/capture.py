import numpy as np
import cv2
import win32gui
import win32ui
import win32api
import win32con
import time
from ctypes import windll, wintypes, byref
from src.utils.config import HEADER_OFFSET_PX, PW_RENDERFULLCONTENT, UPGRADES_SCROLL_TICKS, UPGRADES_SCROLL_AMOUNT

def find_coc_hwnd() -> int | None:
    result = {}
    def _cb(hwnd, ctx):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if "Clash of Clans" in t and "Firefox" not in t and "Chrome" not in t and "Edge" not in t:
                ctx["hwnd"] = hwnd
    win32gui.EnumWindows(_cb, result)
    hwnd = result.get("hwnd")
    if hwnd:
        print(f"[OK] '{win32gui.GetWindowText(hwnd)}' HWND={hwnd}")
    else:
        print("[ERROR] CoC window not found.")
    return hwnd

def get_client_rect(hwnd: int) -> tuple[int, int, int, int]:
    client_rect = win32gui.GetClientRect(hwnd)
    cw = client_rect[2]
    ch = client_rect[3]
    pt = wintypes.POINT(0, 0)
    windll.user32.ClientToScreen(hwnd, byref(pt))
    return pt.x, pt.y, cw, ch

def capture_frame(hwnd: int) -> np.ndarray | None:
    try:
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        ww, wh = r - l, b - t
        if ww <= 0 or wh <= 0: return None

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc  = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bmp     = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mfc_dc, ww, wh)
        save_dc.SelectObject(bmp)
        windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
        data = bmp.GetBitmapBits(True)
        full = np.frombuffer(data, dtype=np.uint8).reshape(wh, ww, 4)
        full = cv2.cvtColor(full, cv2.COLOR_BGRA2BGR)

        cx, cy, cw, ch = get_client_rect(hwnd)
        
        ox = max(cx - l, 0)
        oy = max(cy - t, 0) + HEADER_OFFSET_PX
        ch = max(ch - HEADER_OFFSET_PX, 1)

        return full[oy:oy+ch, ox:ox+cw]

    except Exception as e:
        print(f"[ERROR] capture_frame: {e}")
        return None
    finally:
        try:
            win32gui.DeleteObject(bmp.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
        except Exception:
            pass

def click_relative_roi(hwnd: int, roi: dict):
    cx, cy, cw, ch = get_client_rect(hwnd)
    ch_capture = max(ch - HEADER_OFFSET_PX, 1)
    
    center_x = roi["x"] + (roi["w"] / 2.0)
    center_y = roi["y"] + (roi["h"] / 2.0)
    
    screen_x = cx + int(center_x * cw)
    screen_y = cy + int(center_y * ch_capture) + HEADER_OFFSET_PX
    
    child_windows =[]
    def enum_child_cb(child_hwnd, ctx):
        child_windows.append(child_hwnd)
        return True
        
    win32gui.EnumChildWindows(hwnd, enum_child_cb, None)
    
    targets = [hwnd] + child_windows
    
    for t_hwnd in targets:
        try:
            rel_x, rel_y = win32gui.ScreenToClient(t_hwnd, (screen_x, screen_y))
            lparam = win32api.MAKELONG(rel_x, rel_y)
            
            win32gui.PostMessage(t_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
            win32gui.PostMessage(t_hwnd, win32con.WM_LBUTTONUP, 0, lparam)
        except Exception:
            pass

def get_relative_mouse_pos(hwnd: int) -> tuple[float, float]:
    try:
        mx, my = win32gui.GetCursorPos()
        cx, cy, cw, ch = get_client_rect(hwnd)
        ch_capture = max(ch - HEADER_OFFSET_PX, 1)
        
        if cw <= 0 or ch_capture <= 0:
            return (-1.0, -1.0)
            
        rel_x = (mx - cx) / cw
        rel_y = (my - cy - HEADER_OFFSET_PX) / ch_capture
        return (rel_x, rel_y)
    except Exception:
        return (-1.0, -1.0)
    
    targets = [hwnd] + child_windows

    for target in targets:
        try:
            client_pos = win32gui.ScreenToClient(target, (screen_x, screen_y))
            client_x = client_pos[0] & 0xFFFF
            client_y = client_pos[1] & 0xFFFF
            lparam = (client_y << 16) | client_x
            
            win32gui.PostMessage(target, win32con.WM_MOUSEMOVE, 0, lparam)
            win32gui.PostMessage(target, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
            win32gui.PostMessage(target, win32con.WM_LBUTTONUP, 0, lparam)
        except Exception:
            pass

def scroll_roi(hwnd: int, roi: dict):
    cx, cy, cw, ch = get_client_rect(hwnd)
    ch_capture = max(ch - HEADER_OFFSET_PX, 1)
    
    center_x = roi["x"] + (roi["w"] / 2.0)
    center_y = roi["y"] + (roi["h"] / 2.0)
    
    screen_x = cx + int(center_x * cw)
    screen_y = cy + int(center_y * ch_capture) + HEADER_OFFSET_PX
    
    child_windows =[]
    def enum_child_cb(child_hwnd, ctx):
        ctx.append(child_hwnd)
    try:
        win32gui.EnumChildWindows(hwnd, enum_child_cb, child_windows)
    except Exception:
        pass
    targets = [hwnd] + child_windows

    for target in targets:
        client_pos = win32gui.ScreenToClient(target, (screen_x, screen_y))
        lparam_client = ((client_pos[1] & 0xFFFF) << 16) | (client_pos[0] & 0xFFFF)
        win32gui.PostMessage(target, win32con.WM_MOUSEMOVE, 0, lparam_client)
    time.sleep(0.05)

    lparam_screen = ((screen_y & 0xFFFF) << 16) | (screen_x & 0xFFFF)
    wparam = ((UPGRADES_SCROLL_AMOUNT & 0xFFFF) << 16) | 0
    
    for _ in range(UPGRADES_SCROLL_TICKS):
        for target in targets:
            win32gui.PostMessage(target, win32con.WM_MOUSEWHEEL, wparam, lparam_screen)
        time.sleep(0.04)

    time.sleep(0.6)

def focus_sea_background(hwnd: int):
    ZOOM_OUT_TICKS  = 15
    ZOOM_IN_TICKS   = 15
    
    SWIPES_DOWN     = 4
    SWIPES_LEFT     = 4
    DRAG_SPEED      = 2
    
    ZOOM_OUT_X_RATIO = 0.85
    ZOOM_OUT_Y_RATIO = 0.15

    ZOOM_IN_X_RATIO = 0.15
    ZOOM_IN_Y_RATIO = 0.85

    cx, cy, cw, ch = get_client_rect(hwnd)
    ch_capture = max(ch - HEADER_OFFSET_PX, 1)

    child_windows =[]
    def enum_child_cb(child_hwnd, ctx):
        ctx.append(child_hwnd)
    try:
        win32gui.EnumChildWindows(hwnd, enum_child_cb, child_windows)
    except Exception:
        pass
    targets = [hwnd] + child_windows

    center_x = cw // 2
    center_y = ch_capture // 2 + HEADER_OFFSET_PX

    def perform_scroll(ticks, direction="in", focus_x=None, focus_y=None):
        if focus_x is None: focus_x = center_x
        if focus_y is None: focus_y = center_y

        pt = wintypes.POINT(int(focus_x), int(focus_y))
        windll.user32.ClientToScreen(hwnd, byref(pt))
        screen_x, screen_y = pt.x, pt.y
        lparam_screen = ((screen_y & 0xFFFF) << 16) | (screen_x & 0xFFFF)

        val = 120 if direction == "in" else -120
        wparam = ((val & 0xFFFF) << 16) | 0
        
        for _ in range(ticks):
            for target in targets:
                client_pos = win32gui.ScreenToClient(target, (screen_x, screen_y))
                lparam_client = ((client_pos[1] & 0xFFFF) << 16) | (client_pos[0] & 0xFFFF)
                win32gui.PostMessage(target, win32con.WM_MOUSEMOVE, 0, lparam_client)
                win32gui.PostMessage(target, win32con.WM_MOUSEWHEEL, wparam, lparam_screen)
            time.sleep(0.01)
        time.sleep(0.1)

    def perform_swipe(start_x, start_y, end_x, end_y, count):
        for _ in range(count):
            for target in targets:
                client_pos_start = win32gui.ScreenToClient(target, (cx + start_x, cy + start_y))
                lparam_start = ((client_pos_start[1] & 0xFFFF) << 16) | (client_pos_start[0] & 0xFFFF)
                win32gui.PostMessage(target, win32con.WM_MOUSEMOVE, 0, lparam_start)
                win32gui.PostMessage(target, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam_start)
            time.sleep(0.01)

            for i in range(1, DRAG_SPEED + 1):
                cur_x = int(start_x + (end_x - start_x) * (i / DRAG_SPEED))
                cur_y = int(start_y + (end_y - start_y) * (i / DRAG_SPEED))
                for target in targets:
                    client_pos_move = win32gui.ScreenToClient(target, (cx + cur_x, cy + cur_y))
                    lparam_move = ((client_pos_move[1] & 0xFFFF) << 16) | (client_pos_move[0] & 0xFFFF)
                    win32gui.PostMessage(target, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lparam_move)
                time.sleep(0.005)

            for target in targets:
                client_pos_end = win32gui.ScreenToClient(target, (cx + end_x, cy + end_y))
                lparam_end = ((client_pos_end[1] & 0xFFFF) << 16) | (client_pos_end[0] & 0xFFFF)
                win32gui.PostMessage(target, win32con.WM_LBUTTONUP, 0, lparam_end)
            time.sleep(0.05)
        time.sleep(0.05)

    corner_out_x = cw * ZOOM_OUT_X_RATIO
    corner_out_y = (ch_capture * ZOOM_OUT_Y_RATIO) + HEADER_OFFSET_PX
    
    perform_scroll(ZOOM_OUT_TICKS, direction="out", focus_x=corner_out_x, focus_y=corner_out_y)

    if SWIPES_DOWN > 0:
        sx_down = center_x
        sy_down = center_y + int(ch_capture * 0.3)
        ex_down = center_x
        ey_down = center_y - int(ch_capture * 0.3)
        perform_swipe(sx_down, sy_down, ex_down, ey_down, SWIPES_DOWN)

    if SWIPES_LEFT > 0:
        sx_left = center_x - int(cw * 0.3)
        sy_left = center_y
        ex_left = center_x + int(cw * 0.3)
        ey_left = center_y
        perform_swipe(sx_left, sy_left, ex_left, ey_left, SWIPES_LEFT)

    corner_in_x = cw * ZOOM_IN_X_RATIO
    corner_in_y = (ch_capture * ZOOM_IN_Y_RATIO) + HEADER_OFFSET_PX
    
    perform_scroll(ZOOM_IN_TICKS, direction="in", focus_x=corner_in_x, focus_y=corner_in_y)


def zoom_camera(hwnd: int, ticks: int, direction="in"):
    cx, cy, cw, ch = get_client_rect(hwnd)
    ch_capture = max(ch - HEADER_OFFSET_PX, 1)

    center_x = cw // 2
    center_y = ch_capture // 2 + HEADER_OFFSET_PX

    pt = wintypes.POINT(int(center_x), int(center_y))
    windll.user32.ClientToScreen(hwnd, byref(pt))
    screen_x, screen_y = pt.x, pt.y
    lparam_screen = ((screen_y & 0xFFFF) << 16) | (screen_x & 0xFFFF)

    val = 120 if direction == "in" else -120
    wparam = ((val & 0xFFFF) << 16) | 0
    
    child_windows = []
    def enum_child_cb(child_hwnd, ctx):
        ctx.append(child_hwnd)
    try:
        win32gui.EnumChildWindows(hwnd, enum_child_cb, child_windows)
    except Exception:
        pass
    targets = [hwnd] + child_windows

    for _ in range(ticks):
        for target in targets:
            client_pos = win32gui.ScreenToClient(target, (screen_x, screen_y))
            lparam_client = ((client_pos[1] & 0xFFFF) << 16) | (client_pos[0] & 0xFFFF)
            win32gui.PostMessage(target, win32con.WM_MOUSEMOVE, 0, lparam_client)
            win32gui.PostMessage(target, win32con.WM_MOUSEWHEEL, wparam, lparam_screen)
        time.sleep(0.05)

def pan_camera(hwnd: int, start_rel: tuple, end_rel: tuple, drag_speed=10):
    cx, cy, cw, ch = get_client_rect(hwnd)
    ch_capture = max(ch - HEADER_OFFSET_PX, 1)
    
    start_x = int(cw * start_rel[0])
    start_y = int(ch_capture * start_rel[1]) + HEADER_OFFSET_PX
    end_x = int(cw * end_rel[0])
    end_y = int(ch_capture * end_rel[1]) + HEADER_OFFSET_PX
    
    child_windows = []
    def enum_child_cb(child_hwnd, ctx):
        ctx.append(child_hwnd)
    try:
        win32gui.EnumChildWindows(hwnd, enum_child_cb, child_windows)
    except Exception:
        pass
    targets = [hwnd] + child_windows

    for target in targets:
        client_pos_start = win32gui.ScreenToClient(target, (cx + start_x, cy + start_y))
        lparam_start = ((client_pos_start[1] & 0xFFFF) << 16) | (client_pos_start[0] & 0xFFFF)
        win32gui.PostMessage(target, win32con.WM_MOUSEMOVE, 0, lparam_start)
        win32gui.PostMessage(target, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam_start)
    time.sleep(0.05)

    for i in range(1, drag_speed + 1):
        cur_x = int(start_x + (end_x - start_x) * (i / drag_speed))
        cur_y = int(start_y + (end_y - start_y) * (i / drag_speed))
        for target in targets:
            client_pos_move = win32gui.ScreenToClient(target, (cx + cur_x, cy + cur_y))
            lparam_move = ((client_pos_move[1] & 0xFFFF) << 16) | (client_pos_move[0] & 0xFFFF)
            win32gui.PostMessage(target, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lparam_move)
        time.sleep(0.01)

    for target in targets:
        client_pos_end = win32gui.ScreenToClient(target, (cx + end_x, cy + end_y))
        lparam_end = ((client_pos_end[1] & 0xFFFF) << 16) | (client_pos_end[0] & 0xFFFF)
        win32gui.PostMessage(target, win32con.WM_LBUTTONUP, 0, lparam_end)
    time.sleep(0.1)
