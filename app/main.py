"""
FastCapture - Main Application Entrypoint
Orchestrates Floating Toolbar, Overlays, Image Editor Studio, System Tray, and Global Hotkeys.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe stdout/stderr redirect for GUI mode
class SafeStream:
    def write(self, s):
        pass
    def flush(self):
        pass

if sys.stdout is None:
    sys.stdout = SafeStream()
if sys.stderr is None:
    sys.stderr = SafeStream()

def global_exception_handler(exc_type, exc_value, exc_traceback):
    import traceback
    err_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        if sys.platform == "darwin":
            crash_dir = Path.home() / "Library" / "Application Support" / "SanCapture"
        elif sys.platform == "win32":
            crash_dir = Path(os.environ.get("APPDATA", Path.home())) / "SAN_Capture"
        else:
            crash_dir = Path.home() / ".config" / "sancapture"
        crash_file = crash_dir / "crash_log.txt"
        crash_file.parent.mkdir(parents=True, exist_ok=True)
        with open(crash_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now().isoformat()}] Unhandled Exception:\n{err_str}\n")
    except Exception:
        pass

sys.excepthook = global_exception_handler

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMessageBox, 
    QFileDialog, QWidget
)
from PyQt6.QtGui import QPixmap, QIcon, QAction
from PyQt6.QtCore import Qt, QPoint, QTimer

from app.ui.theme import APP_STYLESHEET
from app.ui.icons import IconFactory
from app.ui.floating_toolbar import FloatingToolbar
from app.ui.sniper_overlay import SniperOverlay
from app.ui.window_picker import WindowPickerOverlay
from app.ui.freehand_overlay import FreehandOverlay
from app.ui.color_picker_tool import ColorPickerTool
from app.ui.editor_window import EditorWindow
from app.ui.settings_dialog import SettingsDialog
from app.core.screen_capture import ScreenCaptureEngine
from app.core.hotkeys import GlobalHotkeyManager
from app.core.config import config, OutputDest
from app.core.sound import play_shutter_sound
from app.core.image_optimizer import ImageOptimizer, format_file_size

class FastCaptureApp:
    def __init__(self, qapp: QApplication):
        self.qapp = qapp
        self.qapp.setStyleSheet(APP_STYLESHEET)
        self.qapp.setQuitOnLastWindowClosed(False)

        # Core Windows
        self.toolbar = FloatingToolbar()
        self.editor: EditorWindow = None
        self.settings_dlg: SettingsDialog = None
        self.active_overlay = None

        # System Tray
        self._init_tray()

        # Connect Toolbar Signals
        self.toolbar.request_capture_active_win.connect(self.capture_active_window)
        self.toolbar.request_capture_win_object.connect(self.capture_win_object)
        self.toolbar.request_capture_rect.connect(self.capture_rectangular_region)
        self.toolbar.request_capture_freehand.connect(self.capture_freehand_region)
        self.toolbar.request_capture_fullscreen.connect(self.capture_fullscreen)
        self.toolbar.request_open_editor.connect(self.open_editor_blank)
        self.toolbar.request_color_picker.connect(self.start_color_picker)
        self.toolbar.request_open_file.connect(self.open_file_in_editor)
        self.toolbar.request_settings.connect(self.open_settings)
        self.toolbar.request_minimize_tray.connect(self.minimize_to_tray)

        # Position Floating Toolbar at top-center of primary screen
        self.toolbar.adjustSize()
        primary_geo = self.qapp.primaryScreen().geometry()
        tb_w = self.toolbar.sizeHint().width() if self.toolbar.sizeHint().width() > 0 else self.toolbar.width()
        tb_x = primary_geo.x() + (primary_geo.width() - tb_w) // 2
        tb_y = primary_geo.y() + 60
        self.toolbar.move(tb_x, tb_y)
        self.toolbar.show()
        self.toolbar.raise_()
        self.toolbar.activateWindow()

        # Initialize Global Hotkeys
        self.hotkey_mgr = GlobalHotkeyManager(config.get("hotkeys", {}))
        self.hotkey_mgr.active_window_pressed.connect(self.capture_active_window)
        self.hotkey_mgr.window_object_pressed.connect(self.capture_win_object)
        self.hotkey_mgr.rectangular_region_pressed.connect(self.capture_rectangular_region)
        self.hotkey_mgr.freehand_region_pressed.connect(self.capture_freehand_region)
        self.hotkey_mgr.full_screen_pressed.connect(self.capture_fullscreen)
        self.hotkey_mgr.color_picker_pressed.connect(self.start_color_picker)

        # Show notification that SanCapture is running
        self.tray.showMessage(
            "SanCapture",
            "SanCapture is active! Capture toolbar is ready at the top of your screen.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def _init_tray(self):
        self.tray = QSystemTrayIcon(IconFactory.get_icon("app_icon", 24), self.qapp)
        self.tray.setToolTip("SanCapture - Screenshot & Annotation Studio")

        menu = QMenu()
        act_show = menu.addAction("Show Toolbar")
        act_show.triggered.connect(self.restore_toolbar)

        menu.addSeparator()
        act_active = menu.addAction(IconFactory.get_icon("capture_active_win", 16), "Capture Active Window")
        act_active.triggered.connect(self.capture_active_window)

        act_obj = menu.addAction(IconFactory.get_icon("capture_win_object", 16), "Capture Window / Object")
        act_obj.triggered.connect(self.capture_win_object)

        act_rect = menu.addAction(IconFactory.get_icon("capture_rect", 16), "Capture Rectangular Region")
        act_rect.triggered.connect(self.capture_rectangular_region)

        act_free = menu.addAction(IconFactory.get_icon("capture_freehand", 16), "Capture Freehand Region")
        act_free.triggered.connect(self.capture_freehand_region)

        act_full = menu.addAction(IconFactory.get_icon("capture_fullscreen", 16), "Capture Full Screen")
        act_full.triggered.connect(self.capture_fullscreen)

        menu.addSeparator()
        act_color = menu.addAction(IconFactory.get_icon("color_picker", 16), "Screen Color Picker")
        act_color.triggered.connect(self.start_color_picker)

        act_editor = menu.addAction("Open Editor")
        act_editor.triggered.connect(self.open_editor_blank)

        act_settings = menu.addAction(IconFactory.get_icon("settings", 16), "Settings...")
        act_settings.triggered.connect(self.open_settings)

        menu.addSeparator()
        act_exit = menu.addAction("Exit SanCapture")
        act_exit.triggered.connect(self.quit_app)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.restore_toolbar()

    def restore_toolbar(self):
        self.toolbar.show()
        self.toolbar.raise_()
        self.toolbar.activateWindow()

    def minimize_to_tray(self):
        self.toolbar.hide()
        self.tray.showMessage(
            "SanCapture", 
            "SanCapture is running in background. Use hotkeys or click tray icon to capture.",
            QSystemTrayIcon.MessageIcon.Information,
            2500
        )

    # -------------------------------------------------------------
    # Capture Workflows
    # -------------------------------------------------------------
    def capture_active_window(self):
        self.toolbar.hide()
        QTimer.singleShot(150, self._do_capture_active)

    def _do_capture_active(self):
        pixmap = ScreenCaptureEngine.capture_active_window()
        self.toolbar.show()
        if pixmap and not pixmap.isNull():
            self._handle_captured_image(pixmap)

    def capture_win_object(self):
        self.toolbar.hide()
        QTimer.singleShot(100, self._do_capture_win_object)

    def _do_capture_win_object(self):
        full_pixmap, v_rect = ScreenCaptureEngine.capture_all_screens()
        self.active_overlay = WindowPickerOverlay(full_pixmap, v_rect.topLeft())
        self.active_overlay.capture_completed.connect(self._on_overlay_captured)
        self.active_overlay.capture_cancelled.connect(self._on_overlay_cancelled)
        self.active_overlay.show()
        self.active_overlay.raise_()
        self.active_overlay.activateWindow()

    def capture_rectangular_region(self):
        self.toolbar.hide()
        QTimer.singleShot(100, self._do_capture_rect)

    def _do_capture_rect(self):
        full_pixmap, v_rect = ScreenCaptureEngine.capture_all_screens()
        self.active_overlay = SniperOverlay(full_pixmap, v_rect.topLeft())
        self.active_overlay.capture_completed.connect(self._on_overlay_captured)
        self.active_overlay.capture_cancelled.connect(self._on_overlay_cancelled)
        self.active_overlay.show()
        self.active_overlay.raise_()
        self.active_overlay.activateWindow()

    def capture_freehand_region(self):
        self.toolbar.hide()
        QTimer.singleShot(100, self._do_capture_freehand)

    def _do_capture_freehand(self):
        full_pixmap, v_rect = ScreenCaptureEngine.capture_all_screens()
        self.active_overlay = FreehandOverlay(full_pixmap, v_rect.topLeft())
        self.active_overlay.capture_completed.connect(self._on_overlay_captured)
        self.active_overlay.capture_cancelled.connect(self._on_overlay_cancelled)
        self.active_overlay.show()
        self.active_overlay.raise_()
        self.active_overlay.activateWindow()

    def capture_fullscreen(self):
        self.toolbar.hide()
        QTimer.singleShot(150, self._do_capture_fullscreen)

    def _do_capture_fullscreen(self):
        pixmap, _ = ScreenCaptureEngine.capture_all_screens()
        self.toolbar.show()
        if pixmap and not pixmap.isNull():
            self._handle_captured_image(pixmap)

    def start_color_picker(self):
        self.toolbar.hide()
        QTimer.singleShot(100, self._do_color_picker)

    def _do_color_picker(self):
        full_pixmap, v_rect = ScreenCaptureEngine.capture_all_screens()
        self.active_overlay = ColorPickerTool(full_pixmap, v_rect.topLeft())
        self.active_overlay.color_picked.connect(self._on_color_picked)
        self.active_overlay.cancelled.connect(self._on_overlay_cancelled)
        self.active_overlay.show()
        self.active_overlay.raise_()
        self.active_overlay.activateWindow()

    def _on_color_picked(self, hex_str, color):
        self.toolbar.show()
        self.tray.showMessage(
            "Color Dropper Copied",
            f"Color {hex_str} copied to clipboard!",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def _on_overlay_captured(self, pixmap: QPixmap):
        self.toolbar.show()
        self._handle_captured_image(pixmap)

    def _on_overlay_cancelled(self):
        self.toolbar.show()

    # -------------------------------------------------------------
    # Output Destination Handler
    # -------------------------------------------------------------
    def _handle_captured_image(self, pixmap: QPixmap):
        if config.get("play_sound", True):
            play_shutter_sound()

        dest = config.get("output_dest", OutputDest.EDITOR)

        if dest == OutputDest.EDITOR:
            if not self.editor:
                self.editor = EditorWindow(pixmap)
            else:
                self.editor.set_image(pixmap)
            self.editor.show()
            self.editor.raise_()
            self.editor.activateWindow()

        elif dest == OutputDest.CLIPBOARD:
            self.qapp.clipboard().setPixmap(pixmap)
            self.tray.showMessage("Screenshot Captured", "Image copied to clipboard.", QSystemTrayIcon.MessageIcon.Information, 1800)

        elif dest == OutputDest.AUTO_SAVE:
            save_dir = config.get_save_dir()
            name = config.get_next_capture_name(auto_increment=True)
            fmt = config.get("image_format", "PNG").lower()
            file_path = save_dir / f"{name}.{fmt}"
            
            # Auto enhance sharpness if user enabled it in settings
            if config.get("auto_enhance_sharpness", False):
                pixmap = ImageOptimizer.enhance_sharpness(pixmap, factor=1.2)

            success, size_bytes, msg = ImageOptimizer.save_pixmap(pixmap, str(file_path))
            if success:
                self.tray.showMessage(
                    "Screenshot Saved", 
                    f"Saved to {file_path.name} ({format_file_size(size_bytes)})", 
                    QSystemTrayIcon.MessageIcon.Information, 
                    2500
                )
            else:
                self.tray.showMessage(
                    "Save Failed", 
                    f"Could not save to {file_path.name}", 
                    QSystemTrayIcon.MessageIcon.Warning, 
                    3000
                )

        elif dest == OutputDest.FILE_SAVE:
            if not self.editor:
                self.editor = EditorWindow(pixmap)
            else:
                self.editor.set_image(pixmap)
            self.editor._action_save()

        elif dest == OutputDest.PRINT:
            if not self.editor:
                self.editor = EditorWindow(pixmap)
            else:
                self.editor.set_image(pixmap)
            self.editor._action_print()

    # -------------------------------------------------------------
    # Utility Actions
    # -------------------------------------------------------------
    def open_file_in_editor(self):
        path, _ = QFileDialog.getOpenFileName(None, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
        if path:
            pm = QPixmap(path)
            if not pm.isNull():
                if not self.editor:
                    self.editor = EditorWindow(pm)
                else:
                    self.editor.set_image(pm)
                self.editor.show()
                self.editor.raise_()
                self.editor.activateWindow()

    def open_editor_blank(self):
        if not self.editor:
            self.editor = EditorWindow()
        self.editor.show()
        self.editor.raise_()
        self.editor.activateWindow()

    def open_settings(self):
        if not self.settings_dlg:
            self.settings_dlg = SettingsDialog()
            self.settings_dlg.settings_saved.connect(self._on_settings_saved)
        self.settings_dlg.exec()

    def _on_settings_saved(self):
        # Re-initialize hotkeys
        self.hotkey_mgr.config_hotkeys = config.get("hotkeys", {})
        self.hotkey_mgr.init_hotkeys()
        self.toolbar.update_tooltips()
        if self.editor and hasattr(self.editor, 'thumb_bar'):
            self.editor.thumb_bar.sync_config_values()

    def quit_app(self):
        if self.editor and hasattr(self.editor, 'prompt_save_on_close'):
            if not self.editor.prompt_save_on_close():
                return
        self.hotkey_mgr.stop()
        self.tray.hide()
        self.qapp.quit()

def main():
    # Enable hardware Per-Monitor DPI awareness on Windows to eliminate OS bitmap scaling blur
    if sys.platform == "win32":
        try:
            import ctypes
            # Context -4 corresponds to DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass

    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("SanCapture")
    app.setOrganizationName("SanCapture")

    fc_app = FastCaptureApp(app)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
