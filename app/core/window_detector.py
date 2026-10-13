import sys
import ctypes
from typing import Optional, List, Tuple
from PyQt6.QtCore import QRect, QPoint

if sys.platform == "win32":
    from ctypes import wintypes
    import win32gui
    import win32con
    import win32api
    from app.core.screen_capture import get_window_rect_dwm

class WindowDetector:
    """Detects Windows objects, UI controls, and top-level windows under the cursor."""

    @staticmethod
    def get_object_under_point(global_point: QPoint) -> Optional[QRect]:
        if sys.platform != "win32":
            return None

        pt = wintypes.POINT(global_point.x(), global_point.y())
        
        # 1. Find child window or control under point
        hwnd = win32gui.WindowFromPoint((global_point.x(), global_point.y()))
        if not hwnd:
            return None

        # Try to find specific child control inside
        client_pt = win32gui.ScreenToClient(hwnd, (global_point.x(), global_point.y()))
        child_hwnd = win32gui.ChildWindowFromPointEx(
            hwnd, 
            client_pt, 
            win32con.CWP_SKIPINVISIBLE | win32con.CWP_SKIPDISABLED
        )
        
        target_hwnd = child_hwnd if (child_hwnd and child_hwnd != hwnd) else hwnd

        # Get geometry
        try:
            # Check if it's a top-level window or child control
            parent = win32gui.GetParent(target_hwnd)
            if not parent:
                # Top-level window: use DWM bounds for clean edges
                x, y, w, h = get_window_rect_dwm(target_hwnd)
            else:
                # Child control: use standard window rect
                l, t, r, b = win32gui.GetWindowRect(target_hwnd)
                x, y, w, h = l, t, max(1, r - l), max(1, b - t)

            if w > 4 and h > 4:
                return QRect(x, y, w, h)
        except Exception:
            pass

        return None
