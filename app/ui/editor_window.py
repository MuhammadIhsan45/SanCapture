"""
Full Image Annotation & Editing Studio for FastCapture.
Includes Multi-Capture Gallery/Thumbnail Bar, Highlighters, Vector Annotations, Effects, and Batch Export.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Set
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QToolBar, QToolButton, QComboBox, QSpinBox, 
    QLabel, QFileDialog, QMessageBox, QColorDialog,
    QStatusBar, QMenuBar, QMenu, QButtonGroup, QFrame,
    QPushButton, QDialog, QFormLayout, QDialogButtonBox,
    QApplication
)
from PyQt6.QtGui import QAction, QPixmap, QColor, QFont, QIcon, QKeySequence, QImage
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPoint

from app.ui.theme import ThemeColors, APP_STYLESHEET
from app.ui.icons import IconFactory
from app.ui.editor_canvas import EditorCanvas, ToolType
from app.ui.thumbnail_bar import ThumbnailBar, CaptureItem
from app.ui.effects import ImageEffects
from app.core.config import config
from app.core.image_optimizer import ImageOptimizer, format_file_size

def natural_sort_key(s: str):
    """Sort strings containing numbers in human/natural order (e.g. 1, 2, ..., 10, 11)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

class ResizeDialog(QDialog):
    def __init__(self, current_w: int, current_h: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resize Image")
        self.setFixedSize(300, 160)
        self.setStyleSheet(APP_STYLESHEET)

        layout = QFormLayout(self)

        self.spin_w = QSpinBox()
        self.spin_w.setRange(10, 10000)
        self.spin_w.setValue(current_w)

        self.spin_h = QSpinBox()
        self.spin_h.setRange(10, 10000)
        self.spin_h.setValue(current_h)

        self.aspect_ratio = current_w / max(1, current_h)
        self.lock_aspect = True

        self.spin_w.valueChanged.connect(self._on_w_changed)
        self.spin_h.valueChanged.connect(self._on_h_changed)

        layout.addRow("Width (px):", self.spin_w)
        layout.addRow("Height (px):", self.spin_h)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_w_changed(self, val):
        if self.lock_aspect and not self.spin_h.hasFocus():
            self.spin_h.blockSignals(True)
            self.spin_h.setValue(int(val / self.aspect_ratio))
            self.spin_h.blockSignals(False)

    def _on_h_changed(self, val):
        if self.lock_aspect and not self.spin_w.hasFocus():
            self.spin_w.blockSignals(True)
            self.spin_w.setValue(int(val * self.aspect_ratio))
            self.spin_w.blockSignals(False)

    def get_size(self):
        return self.spin_w.value(), self.spin_h.value()

class EditorWindow(QMainWindow):
    closed = pyqtSignal()

    def __init__(self, initial_pixmap: QPixmap = None):
        super().__init__()
        self.setWindowTitle("SanCapture - Image Editor & Annotation Studio")
        self.setMinimumSize(980, 680)
        self.resize(1150, 780)
        self.setStyleSheet(APP_STYLESHEET)
        self.setWindowIcon(IconFactory.get_icon("app_icon", 32))
        self.setAcceptDrops(True)

        # Main Container Layout
        container = QWidget()
        self.main_vlayout = QVBoxLayout(container)
        self.main_vlayout.setContentsMargins(0, 0, 0, 0)
        self.main_vlayout.setSpacing(0)
        self.setCentralWidget(container)

        # 1. Central Drawing Canvas
        self.canvas = EditorCanvas(initial_pixmap)
        self.main_vlayout.addWidget(self.canvas, 1)

        # 2. Thumbnail & Recent Captures Gallery Bar (Bottom)
        self.thumb_bar = ThumbnailBar(self)
        self.main_vlayout.addWidget(self.thumb_bar)

        self._build_menus()
        self._build_toolbars()
        self._build_statusbar()

        # Connect Canvas Signals
        self.canvas.status_updated.connect(self._update_status)
        self.canvas.zoom_changed.connect(self._update_zoom_label)
        self.canvas.can_undo_changed.connect(self._update_undo_state)
        self.canvas.can_redo_changed.connect(self._update_redo_state)
        self.canvas.content_modified.connect(self._on_canvas_modified)
        self.canvas.tool_change_requested.connect(self._on_tool_change_requested)

        # Connect Gallery Bar Signals
        self.thumb_bar.capture_selected.connect(self._on_gallery_item_selected)
        self.thumb_bar.save_all_requested.connect(self._action_save_all)
        self.thumb_bar.open_image_requested.connect(self._action_open)
        self.thumb_bar.paste_requested.connect(self._action_paste)

        # Add initial image if provided
        if initial_pixmap and not initial_pixmap.isNull():
            self.thumb_bar.add_capture(initial_pixmap)
        else:
            self.canvas.zoom_fit()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        self.handle_dropped_mime_data(event)

    def handle_dropped_mime_data(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.tif', '.tiff')
            file_paths = []
            for url in mime_data.urls():
                fpath = url.toLocalFile()
                if fpath and Path(fpath).suffix.lower() in valid_extensions and Path(fpath).is_file():
                    file_paths.append(fpath)
            
            if file_paths:
                file_paths.sort(key=lambda p: natural_sort_key(Path(p).name))
                self._save_active_canvas_to_gallery()
                added_count = 0
                first_item = None
                for fpath in file_paths:
                    loaded_pm = QPixmap(fpath)
                    if loaded_pm and not loaded_pm.isNull():
                        name = Path(fpath).stem
                        item = self.thumb_bar.add_capture(loaded_pm, name)
                        if first_item is None:
                            first_item = item
                        added_count += 1
                if added_count > 0:
                    if first_item:
                        self.thumb_bar.select_item(first_item)
                    self.lbl_status.setText(f"✓ Drag & dropped {added_count} image(s) in natural order.")
                    event.acceptProposedAction()
                    return

        elif mime_data.hasImage():
            img = mime_data.imageData()
            if img:
                pm = QPixmap.fromImage(img) if isinstance(img, QImage) else QPixmap(img)
                if pm and not pm.isNull():
                    self._save_active_canvas_to_gallery()
                    item = self.thumb_bar.add_capture(pm)
                    self.thumb_bar.select_item(item)
                    self.lbl_status.setText(f"✓ Dropped image added as #{item.name}")
                    event.acceptProposedAction()
                    return

        event.ignore()

    def set_image(self, pixmap: QPixmap, name: str = ""):
        """Adds a newly captured screenshot or opened file to the gallery and displays it."""
        self._save_active_canvas_to_gallery()
        item = self.thumb_bar.add_capture(pixmap, name)
        self.show()
        self.raise_()
        self.activateWindow()

    def _save_active_canvas_to_gallery(self):
        if self.thumb_bar.active_item:
            state = self.canvas.get_state()
            self.thumb_bar.active_item.base_pixmap = state[0]
            self.thumb_bar.active_item.items = state[1]
            self.thumb_bar.active_item.undo_stack = state[2]
            self.thumb_bar.active_item.redo_stack = state[3]
            self.thumb_bar.active_item.next_step_number = state[4]
            self.thumb_bar.update_active_thumbnail()

    def _on_gallery_item_selected(self, item: Optional[CaptureItem]):
        if not item:
            blank = QPixmap(800, 600)
            blank.fill(QColor("#282C34"))
            self.canvas.set_pixmap(blank)
            self.lbl_status.setText("Gallery is empty. Capture, paste, or drop images here.")
            return
        self.canvas.load_capture_state(
            item.base_pixmap, 
            item.items, 
            item.undo_stack, 
            item.redo_stack, 
            item.next_step_number
        )
        self.canvas.zoom_fit()
        if item in self.thumb_bar.captures:
            idx = self.thumb_bar.captures.index(item) + 1
            total = len(self.thumb_bar.captures)
            self.lbl_status.setText(f"Active Image: #{item.name} ({idx} of {total}) — [← / →] to navigate images")

    def _on_canvas_modified(self):
        if self.thumb_bar.active_item:
            state = self.canvas.get_state()
            self.thumb_bar.active_item.base_pixmap = state[0]
            self.thumb_bar.active_item.items = state[1]
            self.thumb_bar.active_item.undo_stack = state[2]
            self.thumb_bar.active_item.redo_stack = state[3]
            self.thumb_bar.active_item.next_step_number = state[4]
            self.thumb_bar.active_item.is_modified = True
            self.thumb_bar.update_active_thumbnail()

    # -------------------------------------------------------------
    # Menu Bar Setup
    # -------------------------------------------------------------
    def _build_menus(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")
        
        act_open = file_menu.addAction(IconFactory.get_icon("open_image", 16), "&Open Image...")
        act_open.setShortcut(QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self._action_open)

        act_save = file_menu.addAction(IconFactory.get_icon("save", 16), "&Save Image (Ctrl+S)")
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self._action_save)

        act_save_all = file_menu.addAction("Save &All Images in Gallery (Batch)...")
        act_save_all.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_all.triggered.connect(self._action_save_all)

        file_menu.addSeparator()

        act_copy = file_menu.addAction(IconFactory.get_icon("copy", 16), "&Copy to Clipboard")
        act_copy.setShortcut(QKeySequence("Ctrl+C"))
        act_copy.triggered.connect(self._action_copy_clipboard)

        act_paste = file_menu.addAction(IconFactory.get_icon("paste", 16), "&Paste from Clipboard")
        act_paste.setShortcut(QKeySequence("Ctrl+V"))
        act_paste.triggered.connect(self._action_paste)

        act_print = file_menu.addAction(IconFactory.get_icon("print", 16), "&Print...")
        act_print.setShortcut(QKeySequence("Ctrl+P"))
        act_print.triggered.connect(self._action_print)

        file_menu.addSeparator()
        act_close = file_menu.addAction("&Close")
        act_close.setShortcut(QKeySequence("Esc"))
        act_close.triggered.connect(self.close)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")
        self.act_undo = edit_menu.addAction(IconFactory.get_icon("undo", 16), "&Undo")
        self.act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.act_undo.setEnabled(False)
        self.act_undo.triggered.connect(self.canvas.undo)

        self.act_redo = edit_menu.addAction(IconFactory.get_icon("redo", 16), "&Redo")
        self.act_redo.setShortcut(QKeySequence("Ctrl+Y"))
        self.act_redo.setEnabled(False)
        self.act_redo.triggered.connect(self.canvas.redo)

        edit_menu.addSeparator()
        act_del = edit_menu.addAction(IconFactory.get_icon("delete", 16), "&Delete Selected Image(s)...")
        act_del.setShortcut(QKeySequence("Delete"))
        act_del.triggered.connect(self.thumb_bar.delete_selected_items)

        # Image Menu
        img_menu = menubar.addMenu("&Image")
        act_crop = img_menu.addAction(IconFactory.get_icon("tool_crop", 16), "&Crop Selection")
        act_crop.setShortcut(QKeySequence("C"))
        act_crop.triggered.connect(self._action_crop)

        act_resize = img_menu.addAction("Re&size Canvas / Image...")
        act_resize.setShortcut(QKeySequence("Ctrl+R"))
        act_resize.triggered.connect(self._action_resize)

        img_menu.addSeparator()
        act_rot_cw = img_menu.addAction("Rotate 90° &Clockwise")
        act_rot_cw.triggered.connect(lambda: self._apply_effect(ImageEffects.rotate, 90))

        act_rot_ccw = img_menu.addAction("Rotate 90° &Counter-Clockwise")
        act_rot_ccw.triggered.connect(lambda: self._apply_effect(ImageEffects.rotate, -90))

        act_flip_h = img_menu.addAction("Flip &Horizontal")
        act_flip_h.triggered.connect(lambda: self._apply_effect(ImageEffects.flip_horizontal))

        act_flip_v = img_menu.addAction("Flip &Vertical")
        act_flip_v.triggered.connect(lambda: self._apply_effect(ImageEffects.flip_vertical))

        img_menu.addSeparator()
        act_shadow = img_menu.addAction("Add &Drop Shadow")
        act_shadow.triggered.connect(lambda: self._apply_effect(ImageEffects.add_drop_shadow))

        act_border = img_menu.addAction("Add Crisp &Border...")
        act_border.triggered.connect(self._action_add_border)

        act_sharpen = img_menu.addAction(IconFactory.get_icon("sharpen", 16), "Enhance &Sharpness / Crispness")
        act_sharpen.setShortcut(QKeySequence("Ctrl+Shift+E"))
        act_sharpen.setToolTip("Enhance fine text clarity and sharp edges")
        act_sharpen.triggered.connect(self._action_enhance_sharpness)

        # View Menu
        view_menu = menubar.addMenu("&View")
        act_zoom_in = view_menu.addAction("Zoom &In")
        act_zoom_in.setShortcut(QKeySequence("Ctrl++"))
        act_zoom_in.triggered.connect(lambda: self.canvas.set_zoom(self.canvas.zoom_factor * 1.25))

        act_zoom_out = view_menu.addAction("Zoom &Out")
        act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        act_zoom_out.triggered.connect(lambda: self.canvas.set_zoom(self.canvas.zoom_factor / 1.25))

        act_zoom_100 = view_menu.addAction("Zoom &100% (Actual Size)")
        act_zoom_100.setShortcut(QKeySequence("Ctrl+1"))
        act_zoom_100.triggered.connect(self.canvas.zoom_100)

        act_zoom_fit = view_menu.addAction("Zoom &Fit to Window")
        act_zoom_fit.setShortcut(QKeySequence("Shift+1"))
        act_zoom_fit.triggered.connect(self.canvas.zoom_fit)

        view_menu.addSeparator()
        act_next_img = view_menu.addAction("Next Image in Gallery (→)")
        act_next_img.setShortcut(QKeySequence("Right"))
        act_next_img.triggered.connect(self._action_next_image)

        act_prev_img = view_menu.addAction("Previous Image in Gallery (←)")
        act_prev_img.setShortcut(QKeySequence("Left"))
        act_prev_img.triggered.connect(self._action_prev_image)

    # -------------------------------------------------------------
    # Toolbar Setup
    # -------------------------------------------------------------
    def _build_toolbars(self):
        # 1. Left Vertical Annotation Toolbar
        tb_tools = QToolBar("Annotation Tools", self)
        tb_tools.setOrientation(Qt.Orientation.Vertical)
        tb_tools.setIconSize(QSize(22, 22))
        tb_tools.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, tb_tools)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        tool_specs = [
            (ToolType.SELECT, "Select / Move Objects (V)", "tool_select"),
            (ToolType.HAND, "Hand Tool - Pan Canvas (H, Space+Drag)", "tool_hand"),
            (ToolType.ARROW, "Arrow Annotation (A)", "tool_arrow"),
            (ToolType.PEN, "Smooth Freehand Pen (P)", "tool_pen"),
            (ToolType.HIGHLIGHTER, "Neon Freehand Highlighter (H)", "tool_highlighter"),
            (ToolType.HIGHLIGHTER_RECT, "Neon Rectangular Text Highlight Box (Shift+H)", "tool_highlighter_rect"),
            (ToolType.STEP_BADGE, "Step Number Stamp 1,2,3.. (N)", "tool_step"),
            (ToolType.RECT, "Crisp Rectangle (R)", "tool_rect"),
            (ToolType.ROUND_RECT, "Rounded Rectangle", "tool_round_rect"),
            (ToolType.CIRCLE, "Circle / Oval (O)", "tool_circle"),
            (ToolType.LINE, "Straight Line (L)", "tool_line"),
            (ToolType.TEXT, "Text Callout (T)", "tool_text"),
            (ToolType.BLUR, "Blur Region (B)", "tool_blur"),
            (ToolType.PIXELATE, "Pixelate / Censor Region", "tool_pixelate"),
        ]

        for t_type, tooltip, icon_key in tool_specs:
            btn = QToolButton()
            btn.setIcon(IconFactory.get_icon(icon_key, 20))
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setProperty("tool_type", t_type)
            if t_type == ToolType.SELECT:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, t=t_type: self._set_tool(t))
            self.tool_group.addButton(btn)
            tb_tools.addWidget(btn)

        # 2. Top Properties Toolbar (Color Palette, Stroke, Action Buttons)
        prop_bar = QToolBar("Tool Properties", self)
        prop_bar.setIconSize(QSize(18, 18))
        prop_bar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, prop_bar)

        # Undo / Redo
        self.btn_undo = QToolButton()
        self.btn_undo.setIcon(IconFactory.get_icon("undo", 16))
        self.btn_undo.setToolTip("Undo (Ctrl+Z)")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self.canvas.undo)
        prop_bar.addWidget(self.btn_undo)

        self.btn_redo = QToolButton()
        self.btn_redo.setIcon(IconFactory.get_icon("redo", 16))
        self.btn_redo.setToolTip("Redo (Ctrl+Y)")
        self.btn_redo.setEnabled(False)
        self.btn_redo.clicked.connect(self.canvas.redo)
        prop_bar.addWidget(self.btn_redo)

        prop_bar.addSeparator()

        # Zoom Controls
        btn_fit = QPushButton("Fit")
        btn_fit.setToolTip("Fit Image to Window (Shift+1)")
        btn_fit.clicked.connect(self.canvas.zoom_fit)
        prop_bar.addWidget(btn_fit)

        btn_100 = QPushButton("100%")
        btn_100.setToolTip("Actual 100% Size (Ctrl+1)")
        btn_100.clicked.connect(self.canvas.zoom_100)
        prop_bar.addWidget(btn_100)

        btn_zoom_minus = QToolButton()
        btn_zoom_minus.setText("−")
        btn_zoom_minus.setToolTip("Zoom Out (Ctrl+Minus)")
        btn_zoom_minus.setStyleSheet("font-weight: bold; font-size: 13px; padding: 1px 6px;")
        btn_zoom_minus.clicked.connect(lambda: self.canvas.set_zoom(self.canvas.zoom_factor / 1.25))
        prop_bar.addWidget(btn_zoom_minus)

        self.lbl_zoom = QLabel(" 100% ")
        self.lbl_zoom.setStyleSheet(f"color: {ThemeColors.TEXT_HIGHLIGHT}; font-weight: bold; padding: 0 4px;")
        prop_bar.addWidget(self.lbl_zoom)

        btn_zoom_plus = QToolButton()
        btn_zoom_plus.setText("+")
        btn_zoom_plus.setToolTip("Zoom In (Ctrl+Plus)")
        btn_zoom_plus.setStyleSheet("font-weight: bold; font-size: 13px; padding: 1px 6px;")
        btn_zoom_plus.clicked.connect(lambda: self.canvas.set_zoom(self.canvas.zoom_factor * 1.25))
        prop_bar.addWidget(btn_zoom_plus)

        prop_bar.addSeparator()

        # Stroke Width Spinner
        lbl_stroke = QLabel("Stroke:")
        prop_bar.addWidget(lbl_stroke)

        self.spin_stroke = QSpinBox()
        self.spin_stroke.setRange(1, 40)
        self.spin_stroke.setValue(3)
        self.spin_stroke.setToolTip("Stroke Line Width")
        self.spin_stroke.valueChanged.connect(self._on_stroke_changed)
        prop_bar.addWidget(self.spin_stroke)

        prop_bar.addSeparator()

        # Solid High-Contrast Color Palette
        lbl_col = QLabel("Color:")
        prop_bar.addWidget(lbl_col)

        self.palette_colors = [
            "#FFEE58",  # Neon Yellow (Highlighter Default)
            "#00E676",  # Neon Green (Highlight)
            "#00E5FF",  # Neon Cyan
            "#FF9100",  # Neon Orange (Highlight)
            "#FF4081",  # Magenta / Pink
            "#D32F2F",  # FastStone Crimson Red
            "#0288D1",  # Cobalt Blue
            "#7B1FA2",  # Purple
            "#FFFFFF",  # White
            "#000000",  # Black
        ]

        self.color_buttons = []
        for hex_col in self.palette_colors:
            c_btn = QToolButton()
            c_btn.setFixedSize(22, 22)
            c_btn.setStyleSheet(f"background-color: {hex_col}; border: 1px solid #181A1F; border-radius: 2px;")
            c_btn.clicked.connect(lambda checked, c=hex_col: self._set_color(c))
            prop_bar.addWidget(c_btn)
            self.color_buttons.append(c_btn)

        # Custom Color Dialog button
        btn_custom_col = QToolButton()
        btn_custom_col.setIcon(IconFactory.get_icon("color_picker", 16))
        btn_custom_col.setToolTip("Choose Custom Color...")
        btn_custom_col.clicked.connect(self._choose_custom_color)
        prop_bar.addWidget(btn_custom_col)

        prop_bar.addSeparator()

        # Enhance Sharpness button
        btn_sharpen = QToolButton()
        btn_sharpen.setIcon(IconFactory.get_icon("sharpen", 16))
        btn_sharpen.setToolTip("Enhance Sharpness / Pertajam Teks & Garis (Ctrl+Shift+E)")
        btn_sharpen.clicked.connect(self._action_enhance_sharpness)
        prop_bar.addWidget(btn_sharpen)

        prop_bar.addSeparator()
        # Crop Confirmation Bar (Hidden by default, shown ONLY when Crop Tool is active)
        self.btn_apply_crop = QPushButton("✓ Apply Crop")
        self.btn_apply_crop.setObjectName("PrimaryBtn")
        self.btn_apply_crop.clicked.connect(self._apply_crop_action)
        self.btn_apply_crop.setVisible(False)
        prop_bar.addWidget(self.btn_apply_crop)

        self.btn_cancel_crop = QPushButton("✕ Cancel")
        self.btn_cancel_crop.clicked.connect(self._cancel_crop_action)
        self.btn_cancel_crop.setVisible(False)
        prop_bar.addWidget(self.btn_cancel_crop)

    # -------------------------------------------------------------
    # Status Bar Setup
    # -------------------------------------------------------------
    def _build_statusbar(self):
        status = self.statusBar()
        self.lbl_status = QLabel("Ready")
        status.addWidget(self.lbl_status, 1)

    def _set_tool(self, tool_type: str):
        self.canvas.current_tool = tool_type
        if tool_type in (ToolType.HIGHLIGHTER, ToolType.HIGHLIGHTER_RECT):
            if self.canvas.stroke_color.red() < 100 and self.canvas.stroke_color.green() < 100:
                self._set_color("#FFEE58")
        
        if tool_type == ToolType.CROP:
            self.canvas.is_cropping = True
            self.btn_apply_crop.setVisible(True)
            self.btn_cancel_crop.setVisible(True)
        else:
            self.canvas.is_cropping = False
            self.canvas.crop_rect = None
            self.btn_apply_crop.setVisible(False)
            self.btn_cancel_crop.setVisible(False)
            
        self.canvas.update()

    def _apply_crop_action(self):
        self.canvas.apply_crop()
        self._select_default_tool()

    def _cancel_crop_action(self):
        self.canvas.cancel_crop()
        self._select_default_tool()

    def _select_default_tool(self):
        self._set_tool(ToolType.SELECT)
        for btn in self.tool_group.buttons():
            if btn.property("tool_type") == ToolType.SELECT:
                btn.setChecked(True)
                break

    def _on_tool_change_requested(self, tool_type: str):
        self._set_tool(tool_type)
        for btn in self.tool_group.buttons():
            if btn.property("tool_type") == tool_type:
                btn.setChecked(True)
                break

    def _set_color(self, hex_color: str):
        col = QColor(hex_color)
        self.canvas.stroke_color = col
        self.canvas.fill_color = QColor(col.red(), col.green(), col.blue(), 60)
        self.canvas.update()

    def _choose_custom_color(self):
        col = QColorDialog.getColor(self.canvas.stroke_color, self, "Choose Annotation Color")
        if col.isValid():
            self._set_color(col.name())

    def _on_stroke_changed(self, val: int):
        self.canvas.line_width = val
        self.canvas.update()

    def _update_status(self, pos: QPoint, img_w: int, img_h: int):
        zoom_pct = int(self.canvas.zoom_factor * 100)
        self.lbl_status.setText(f"Pos: ({pos.x()}, {pos.y()}) px | Size: {img_w} x {img_h} px | Zoom: {zoom_pct}%")

    def _update_zoom_label(self, zoom: float):
        zoom_pct = int(zoom * 100)
        self.lbl_zoom.setText(f" {zoom_pct}% ")

    def _update_undo_state(self, can_undo: bool):
        self.act_undo.setEnabled(can_undo)
        self.btn_undo.setEnabled(can_undo)

    def _update_redo_state(self, can_redo: bool):
        self.act_redo.setEnabled(can_redo)
        self.btn_redo.setEnabled(can_redo)

    # -------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------
    def _action_open(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Open Images", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tif *.tiff)")
        if paths:
            paths.sort(key=lambda p: natural_sort_key(Path(p).name))
            self._save_active_canvas_to_gallery()
            first_item = None
            added_count = 0
            for path in paths:
                pm = QPixmap(path)
                if not pm.isNull():
                    name = Path(path).stem
                    item = self.thumb_bar.add_capture(pm, name)
                    if first_item is None:
                        first_item = item
                    added_count += 1
            if first_item:
                self.thumb_bar.select_item(first_item)
            self.lbl_status.setText(f"✓ Opened {added_count} image(s) in natural order.")

    def _action_paste(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        # 1. File URLs from clipboard (e.g. user selected multiple files in explorer, pressed Ctrl+C, then Ctrl+V in app)
        if mime_data and mime_data.hasUrls():
            valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.tif', '.tiff')
            file_paths = []
            for url in mime_data.urls():
                fpath = url.toLocalFile()
                if fpath and Path(fpath).suffix.lower() in valid_extensions and Path(fpath).is_file():
                    file_paths.append(fpath)
            
            if file_paths:
                file_paths.sort(key=lambda p: natural_sort_key(Path(p).name))
                self._save_active_canvas_to_gallery()
                added_count = 0
                first_item = None
                for fpath in file_paths:
                    loaded_pm = QPixmap(fpath)
                    if loaded_pm and not loaded_pm.isNull():
                        name = Path(fpath).stem
                        item = self.thumb_bar.add_capture(loaded_pm, name)
                        if first_item is None:
                            first_item = item
                        added_count += 1
                if added_count > 0:
                    if first_item:
                        self.thumb_bar.select_item(first_item)
                    self.lbl_status.setText(f"✓ Pasted {added_count} image(s) into gallery in natural order.")
                    return

        # 2. Direct Pixmap
        pm = clipboard.pixmap()
        if pm and not pm.isNull():
            self._save_active_canvas_to_gallery()
            item = self.thumb_bar.add_capture(pm)
            self.thumb_bar.select_item(item)
            self.lbl_status.setText(f"✓ Image pasted into gallery as #{item.name}")
            return

        # 3. QImage from clipboard
        img = clipboard.image()
        if img and not img.isNull():
            pm = QPixmap.fromImage(img)
            self._save_active_canvas_to_gallery()
            item = self.thumb_bar.add_capture(pm)
            self.thumb_bar.select_item(item)
            self.lbl_status.setText(f"✓ Image pasted into gallery as #{item.name}")
            return

        self.lbl_status.setText("No image found in clipboard.")

    def _action_enhance_sharpness(self):
        rendered = self.canvas.get_rendered_pixmap()
        sharpened = ImageEffects.enhance_sharpness(rendered, factor=1.25)
        self.canvas.set_pixmap(sharpened)
        self._on_canvas_modified()
        self.lbl_status.setText("✓ Image sharpness and fine text clarity enhanced!")

    def _action_save(self) -> bool:
        rendered = self.canvas.get_rendered_pixmap()
        default_dir = str(config.get_save_dir())
        
        name_hint = self.thumb_bar.active_item.name if self.thumb_bar.active_item else "Screenshot"
        fmt = config.get("image_format", "PNG").lower()
        default_path = os.path.join(default_dir, f"{name_hint}.{fmt}")
        
        filter_str = (
            "PNG Image - Lossless Sharp (*.png);;"
            "WebP Image - Ultra Compact & Sharp (*.webp);;"
            "JPEG Image - Sharp 4:4:4 (*.jpg *.jpeg);;"
            "Bitmap Image (*.bmp);;"
            "PDF Document (*.pdf)"
        )
        path, selected_filter = QFileDialog.getSaveFileName(self, "Save Screenshot As", default_path, filter_str)
        if path:
            success, size_bytes, msg = ImageOptimizer.save_pixmap(rendered, path)
            if success:
                if self.thumb_bar.active_item:
                    self.thumb_bar.active_item.saved_path = path
                    self.thumb_bar.active_item.name = Path(path).stem
                    self.thumb_bar.active_item.is_modified = False
                    self.thumb_bar.update_active_thumbnail()

                self.lbl_status.setText(f"✓ Saved successfully: {Path(path).name} ({format_file_size(size_bytes)})")
                return True
            else:
                QMessageBox.warning(self, "Save Error", f"Could not save image:\n{msg}")
                return False
        return False

    def _action_save_all(self) -> bool:
        if not self.thumb_bar.captures:
            QMessageBox.information(self, "Save All", "No images in gallery to save.")
            return False

        target_dir = QFileDialog.getExistingDirectory(self, "Select Folder to Save All Images", str(config.get_save_dir()))
        if target_dir:
            self._save_active_canvas_to_gallery()
            fmt = config.get("image_format", "PNG").lower()
            count = 0
            total_size = 0
            for idx, item in enumerate(self.thumb_bar.captures, start=1):
                rendered = item.get_rendered_pixmap()
                file_name = f"{item.name}.{fmt}"
                save_path = os.path.join(target_dir, file_name)
                success, size_bytes, msg = ImageOptimizer.save_pixmap(rendered, save_path)
                if success:
                    item.saved_path = save_path
                    item.is_modified = False
                    count += 1
                    total_size += size_bytes

            self.lbl_status.setText(f"✓ Successfully saved {count} images ({format_file_size(total_size)}) to {target_dir}")
            QMessageBox.information(self, "Save All Complete", f"Successfully saved {count} optimized images ({format_file_size(total_size)}) to:\n{target_dir}")
            return True
        return False

    def _action_copy_clipboard(self):
        rendered = self.canvas.get_rendered_pixmap()
        QApplication.clipboard().setPixmap(rendered)
        self.lbl_status.setText("✓ Image copied to clipboard!")

    def _action_print(self):
        from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec():
            from PyQt6.QtGui import QPainter
            p = QPainter(printer)
            rendered = self.canvas.get_rendered_pixmap()
            p.drawPixmap(0, 0, rendered.scaled(printer.pageRect(QPrinter.Unit.Point).size().toSize(), Qt.AspectRatioMode.KeepAspectRatio))
            p.end()

    def _action_crop(self):
        self._set_tool(ToolType.CROP)
        self.lbl_status.setText("Click and drag on the image to crop. Press Enter to confirm, Esc to cancel.")

    def _action_resize(self):
        w = self.canvas.base_pixmap.width()
        h = self.canvas.base_pixmap.height()
        dlg = ResizeDialog(w, h, self)
        if dlg.exec():
            nw, nh = dlg.get_size()
            rendered = self.canvas.get_rendered_pixmap()
            resized = rendered.scaled(nw, nh, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.canvas.set_pixmap(resized)
            self._on_canvas_modified()

    def _action_add_border(self):
        col = QColorDialog.getColor(QColor("#D32F2F"), self, "Select Border Color")
        if col.isValid():
            rendered = self.canvas.get_rendered_pixmap()
            bordered = ImageEffects.add_border(rendered, border_width=3, color=col)
            self.canvas.set_pixmap(bordered)
            self._on_canvas_modified()

    def _apply_effect(self, func, *args):
        rendered = self.canvas.get_rendered_pixmap()
        result = func(rendered, *args)
        self.canvas.set_pixmap(result)
        self._on_canvas_modified()

    def prompt_save_on_close(self) -> bool:
        """
        Prompts the user with a confirmation popup if there are images in the gallery before closing.
        Returns True if closing should proceed, False if cancelled.
        """
        if not self.thumb_bar.captures:
            return True

        num_imgs = len(self.thumb_bar.captures)
        msg = f"Terdapat {num_imgs} gambar di dalam galeri aplikasi.\nApakah Anda ingin menyimpannya terlebih dahulu sebelum menutup?"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Simpan Gambar Sebelum Menutup?")
        msg_box.setText(msg)
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        btn_save = msg_box.addButton("Simpan (Save)", QMessageBox.ButtonRole.AcceptRole)
        btn_discard = msg_box.addButton("Jangan Simpan (Don't Save)", QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = msg_box.addButton("Batal (Cancel)", QMessageBox.ButtonRole.RejectRole)
        msg_box.setDefaultButton(btn_save)

        msg_box.exec()
        clicked = msg_box.clickedButton()

        if clicked == btn_save:
            if num_imgs == 1:
                return self._action_save()
            else:
                return self._action_save_all()
        elif clicked == btn_discard:
            return True
        else:
            return False

    def _action_next_image(self):
        """Switches to the next image in the gallery."""
        self._save_active_canvas_to_gallery()
        self.thumb_bar.select_next_item()

    def _action_prev_image(self):
        """Switches to the previous image in the gallery."""
        self._save_active_canvas_to_gallery()
        self.thumb_bar.select_previous_item()

    def keyPressEvent(self, event):
        from PyQt6.QtWidgets import QLineEdit, QTextEdit, QSpinBox
        focus_w = QApplication.focusWidget()
        if focus_w and isinstance(focus_w, (QLineEdit, QTextEdit, QSpinBox)):
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_Right:
            self._action_next_image()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Left:
            self._action_prev_image()
            event.accept()
            return

        super().keyPressEvent(event)

    def closeEvent(self, event):
        if not self.prompt_save_on_close():
            event.ignore()
            return
        self._save_active_canvas_to_gallery()
        self.closed.emit()
        super().closeEvent(event)
