"""
FastStone-style Floating Capture Toolbar for FastCapture.
Compact, always-on-top, draggable desktop widget with iconic capture buttons.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton, 
    QComboBox, QFrame, QMenu, QApplication
)
from PyQt6.QtGui import QMouseEvent, QCursor, QAction
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize

from app.ui.theme import APP_STYLESHEET, ThemeColors
from app.ui.icons import IconFactory
from app.core.config import config, OutputDest

class FloatingToolbar(QWidget):
    # Capture action signals
    request_capture_active_win = pyqtSignal()
    request_capture_win_object = pyqtSignal()
    request_capture_rect = pyqtSignal()
    request_capture_freehand = pyqtSignal()
    request_capture_fullscreen = pyqtSignal()
    request_open_editor = pyqtSignal()
    request_color_picker = pyqtSignal()
    request_open_file = pyqtSignal()
    request_settings = pyqtSignal()
    request_minimize_tray = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("FloatingToolbar")
        self.setWindowTitle("SanCapture")
        self.setWindowIcon(IconFactory.get_icon("app_icon", 32))
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(APP_STYLESHEET)
        self.setFixedHeight(38)

        self._drag_pos = None

        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 2, 3, 2)
        layout.setSpacing(2)

        # 1. Drag Grip Handle
        grip = QLabel(" ⠿ ")
        grip.setObjectName("ToolbarGrip")
        grip.setToolTip("Drag to move SanCapture Toolbar")
        grip.setCursor(Qt.CursorShape.SizeAllCursor)
        grip.setStyleSheet(f"color: {ThemeColors.TEXT_MUTED}; font-size: 14px; font-weight: bold;")
        layout.addWidget(grip)

        # 2. Capture Buttons
        self.btn_active = self._create_btn("capture_active_win", "", self.request_capture_active_win.emit)
        self.btn_obj = self._create_btn("capture_win_object", "", self.request_capture_win_object.emit)
        self.btn_rect = self._create_btn("capture_rect", "", self.request_capture_rect.emit)
        self.btn_free = self._create_btn("capture_freehand", "", self.request_capture_freehand.emit)
        self.btn_full = self._create_btn("capture_fullscreen", "", self.request_capture_fullscreen.emit)
        
        layout.addWidget(self.btn_active)
        layout.addWidget(self.btn_obj)
        layout.addWidget(self.btn_rect)
        layout.addWidget(self.btn_free)
        layout.addWidget(self.btn_full)

        layout.addWidget(self._create_separator())

        # 3. Utility Tools & Studio Editor
        self.btn_editor = self._create_btn("open_editor", "Open Image Editor & Studio", self.request_open_editor.emit)
        self.btn_color = self._create_btn("color_picker", "", self.request_color_picker.emit)
        self.btn_open = self._create_btn("open_image", "Open Image File in Editor", self.request_open_file.emit)
        
        layout.addWidget(self.btn_editor)
        layout.addWidget(self.btn_color)
        layout.addWidget(self.btn_open)

        layout.addWidget(self._create_separator())

        # 4. Output Destination Dropdown
        self.combo_dest = QComboBox()
        self.combo_dest.setToolTip("Output Destination for Captured Images")
        for key, title in OutputDest.CHOICES:
            self.combo_dest.addItem(title, key)

        # Set initial
        cur_dest = config.get("output_dest", OutputDest.EDITOR)
        idx = self.combo_dest.findData(cur_dest)
        if idx >= 0:
            self.combo_dest.setCurrentIndex(idx)

        self.combo_dest.currentIndexChanged.connect(self._on_dest_changed)
        layout.addWidget(self.combo_dest)

        layout.addWidget(self._create_separator())

        # 5. Settings & Close
        btn_settings = self._create_btn("settings", "SanCapture Settings", self.request_settings.emit)
        layout.addWidget(btn_settings)

        btn_close = QToolButton()
        btn_close.setText("✕")
        btn_close.setToolTip("Minimize to System Tray")
        btn_close.setStyleSheet(f"color: {ThemeColors.TEXT_MUTED}; font-weight: bold; padding: 2px 5px;")
        btn_close.clicked.connect(self.request_minimize_tray.emit)
        layout.addWidget(btn_close)

        self.update_tooltips()

    def update_tooltips(self):
        hk = config.get("hotkeys", {})
        self.btn_active.setToolTip(f"Capture Active Window ({hk.get('active_window', 'Alt+PrintScreen')})")
        self.btn_obj.setToolTip(f"Capture Window / Object ({hk.get('window_object', 'Shift+PrintScreen')})")
        self.btn_rect.setToolTip(f"Capture Rectangular Region ({hk.get('rectangular_region', 'Ctrl+PrintScreen')})")
        self.btn_free.setToolTip(f"Capture Freehand Region ({hk.get('freehand_region', 'Ctrl+Shift+PrintScreen')})")
        self.btn_full.setToolTip(f"Capture Full Screen ({hk.get('full_screen', 'PrintScreen')})")
        self.btn_color.setToolTip(f"Screen Color Picker ({hk.get('color_picker', 'Ctrl+Alt+C')})")

    def _create_btn(self, icon_name: str, tooltip: str, callback) -> QToolButton:
        btn = QToolButton()
        btn.setIcon(IconFactory.get_icon(icon_name, 22))
        btn.setIconSize(QSize(22, 22))
        btn.setToolTip(tooltip)
        btn.clicked.connect(callback)
        return btn

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet(f"background-color: {ThemeColors.BORDER_LIGHT}; width: 1px; margin: 4px 1px;")
        return sep

    def _on_dest_changed(self, index: int):
        dest_key = self.combo_dest.itemData(index)
        config.set("output_dest", dest_key)

    # -------------------------------------------------------------
    # Drag window handling
    # -------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
