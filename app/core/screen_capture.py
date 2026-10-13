import sys
import os
import ctypes
from typing import Tuple, Optional
from PyQt6.QtGui import QGuiApplication, QPixmap, QPainter, QImage, QColor
from PyQt6.QtCore import QRect, QPoint, Qt

if sys.platform == "win32":
    from ctypes import wintypes
    try:
        import win32gui
        import win32con
        import win32process
        import win32api
    except ImportError:
        pass

# DWM Extended Frame Bounds for accurate Windows 10/11 window bounds
DWMWA_EXTENDED_FRAME_BOUNDS = 9

def get_window_rect_dwm(hwnd: int) -> Tuple[int, int, int, int]:
    """Get accurate window bounds excluding invisible DWM shadow margins."""
    try:
        rect = wintypes.RECT()
        dwm = ctypes.windll.dwmapi
        result = dwm.DwmGetWindowAttribute(
            hwnd,
            DWMWA_EXTENDED_FRAME_BOUNDS,
            ctypes.byref(rect),
            ctypes.sizeof(rect)
        )
        if result == 0:
            return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    except Exception:
        pass
    
    # Fallback to standard Win32 GetWindowRect
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        return (left, top, max(1, right - left), max(1, bottom - top))
    except Exception:
        return (0, 0, 800, 600)

class ScreenCaptureEngine:
    @staticmethod
    def get_virtual_geometry() -> QRect:
        """Returns the union bounding rectangle of all connected screens."""
        screens = QGuiApplication.screens()
        if not screens:
            return QRect(0, 0, 1920, 1080)
        
        virtual_rect = screens[0].geometry()
        for screen in screens[1:]:
            virtual_rect = virtual_rect.united(screen.geometry())
        return virtual_rect

    @classmethod
    def capture_all_screens(cls) -> Tuple[QPixmap, QRect]:
        """
        Captures the entire virtual desktop spanning all monitors.
        Returns combined QPixmap and virtual desktop QRect.
        """
        screens = QGuiApplication.screens()
        if not screens:
            return QPixmap(100, 100), QRect(0, 0, 100, 100)

        if len(screens) == 1:
            screen = screens[0]
            screen_pixmap = screen.grabWindow(0)
            return screen_pixmap, screen.geometry()

        virtual_rect = cls.get_virtual_geometry()
        combined_pixmap = QPixmap(virtual_rect.size())
        combined_pixmap.fill(QColor(0, 0, 0))

        painter = QPainter(combined_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        for screen in screens:
            screen_geo = screen.geometry()
            # Grab full screen pixmap
            screen_pixmap = screen.grabWindow(0)
            # Paint onto virtual canvas at relative offset
            offset_x = screen_geo.x() - virtual_rect.x()
            offset_y = screen_geo.y() - virtual_rect.y()
            painter.drawPixmap(offset_x, offset_y, screen_pixmap)
        painter.end()

        return combined_pixmap, virtual_rect

    @classmethod
    def capture_active_window(cls) -> Optional[QPixmap]:
        """Captures the currently active foreground window cleanly."""
        if sys.platform != "win32":
            return cls.capture_all_screens()[0]

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd or hwnd == win32gui.GetDesktopWindow():
            return cls.capture_all_screens()[0]

        x, y, w, h = get_window_rect_dwm(hwnd)
        if w <= 0 or h <= 0:
            return None

        # Grab virtual desktop and crop the exact window rectangle
        full_pixmap, virtual_rect = cls.capture_all_screens()
        crop_x = x - virtual_rect.x()
        crop_y = y - virtual_rect.y()
        
        # Guard bounds
        crop_rect = QRect(crop_x, crop_y, w, h).intersected(QRect(0, 0, full_pixmap.width(), full_pixmap.height()))
        if crop_rect.isEmpty():
            return full_pixmap
        
        return full_pixmap.copy(crop_rect)

    @classmethod
    def capture_region(cls, global_rect: QRect) -> QPixmap:
        """Captures a specific global screen coordinate rectangle."""
        full_pixmap, virtual_rect = cls.capture_all_screens()
        crop_x = global_rect.x() - virtual_rect.x()
        crop_y = global_rect.y() - virtual_rect.y()
        
        target_rect = QRect(crop_x, crop_y, global_rect.width(), global_rect.height())
        target_rect = target_rect.intersected(QRect(0, 0, full_pixmap.width(), full_pixmap.height()))
        
        if target_rect.isEmpty():
            return QPixmap(10, 10)
        return full_pixmap.copy(target_rect)
