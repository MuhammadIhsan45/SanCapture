"""
Thumbnail Drawer & Multi-Capture Gallery for SAN Capture.
Allows switching between multiple captured screenshots, annotating them, multi-selection, and deleting/saving individually or in batch.
"""

from datetime import datetime
from typing import List, Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QScrollArea, 
    QLabel, QToolButton, QFrame, QMenu, QFileDialog, 
    QMessageBox, QPushButton, QInputDialog, QLineEdit, QSpinBox
)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QFont, QCursor
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QRectF

from app.ui.theme import ThemeColors
from app.ui.icons import IconFactory
from app.core.config import config

class CaptureItem:
    """Holds state of a single captured screenshot in the gallery."""
    def __init__(self, pixmap: QPixmap, name: str = ""):
        self.name = name if name else config.get_next_capture_name(auto_increment=True)
        self.base_pixmap = QPixmap(pixmap)
        self.items = []  # Vector CanvasItems
        self.undo_stack = []
        self.redo_stack = []
        self.next_step_number = 1
        self.saved_path: Optional[str] = None
        self.is_modified = False

    def get_rendered_pixmap(self) -> QPixmap:
        result = QPixmap(self.base_pixmap)
        painter = QPainter(result)
        for item in self.items:
            item.draw(painter)
        painter.end()
        return result

    def get_thumbnail(self, max_w: int = 80, max_h: int = 55) -> QPixmap:
        rendered = self.get_rendered_pixmap()
        return rendered.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

class ThumbnailCard(QFrame):
    clicked = pyqtSignal(object, object)      # passes (CaptureItem, modifiers)
    delete_requested = pyqtSignal(object)    # passes CaptureItem
    save_requested = pyqtSignal(object)

    def __init__(self, item: CaptureItem, is_active: bool = False, is_selected: bool = False, parent=None):
        super().__init__(parent)
        self.item = item
        self.is_active = is_active
        self.is_selected = is_selected
        self.is_hovered = False
        self.setFixedSize(110, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{self.item.name} ({self.item.base_pixmap.width()}x{self.item.base_pixmap.height()})\nClick to select, Ctrl/Shift+Click for multi-select")
        self.update_style()

    def set_selection_state(self, is_active: bool, is_selected: bool):
        self.is_active = is_active
        self.is_selected = is_selected
        self.update_style()

    def update_style(self):
        if self.is_active:
            border_col = ThemeColors.ACCENT_BLUE
            bg_col = "#2C3E50"
        elif self.is_selected:
            border_col = "#61AFEF"
            bg_col = "#212836"
        else:
            border_col = ThemeColors.BORDER_LIGHT
            bg_col = "#1E2227"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_col};
                border: 2px solid {border_col};
                border-radius: 4px;
            }}
        """)
        self.update()

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicked on the hover close button (top right 18x18)
            if self.is_hovered and event.position().x() >= 86 and event.position().y() <= 24:
                self.delete_requested.emit(self.item)
                return
            self.clicked.emit(self.item, event.modifiers())
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def _show_context_menu(self, global_pos):
        parent_bar = self.parentWidget()
        while parent_bar and not isinstance(parent_bar, ThumbnailBar):
            parent_bar = parent_bar.parentWidget()
        
        selected_items = parent_bar.get_selected_items() if parent_bar else [self.item]
        if self.item not in selected_items:
            selected_items = [self.item]

        menu = QMenu(self)
        if len(selected_items) > 1:
            act_del = menu.addAction(IconFactory.get_icon("delete", 16), f"Delete {len(selected_items)} Selected Images...")
        else:
            act_del = menu.addAction(IconFactory.get_icon("delete", 16), f"Delete Image '{self.item.name}'...")

        menu.addSeparator()
        act_save = menu.addAction(IconFactory.get_icon("save", 16), "Save Image As...")
        act_copy = menu.addAction(IconFactory.get_icon("copy", 16), "Copy to Clipboard")
        act_rename = menu.addAction(IconFactory.get_icon("tool_text", 16), "Rename...")

        action = menu.exec(global_pos)
        if action == act_del:
            if parent_bar:
                parent_bar.delete_items_with_confirmation(selected_items)
            else:
                self.delete_requested.emit(self.item)
        elif action == act_save:
            self.save_requested.emit(self.item)
        elif action == act_copy:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setPixmap(self.item.get_rendered_pixmap())
        elif action == act_rename:
            new_name, ok = QInputDialog.getText(self, "Rename Capture", "Name:", text=self.item.name)
            if ok and new_name.strip():
                self.item.name = new_name.strip()
                self.setToolTip(f"{self.item.name} ({self.item.base_pixmap.width()}x{self.item.base_pixmap.height()})")
                self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Draw thumbnail centered
        thumb = self.item.get_thumbnail(84, 50)
        tx = (self.width() - thumb.width()) // 2
        ty = 5 + (50 - thumb.height()) // 2
        p.drawPixmap(tx, ty, thumb)

        # Draw title & dimensions
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor("#FFFFFF" if (self.is_active or self.is_selected) else "#ABB2BF"))
        name_str = self.item.name
        if len(name_str) > 13:
            name_str = name_str[:11] + ".."
        p.drawText(QRect(2, 58, self.width() - 4, 18), Qt.AlignmentFlag.AlignCenter, name_str)

        # If multi-selected, draw a check badge on top-left
        if self.is_selected and not self.is_active:
            p.setBrush(QBrush(QColor("#61AFEF")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(4, 4, 14, 14, 3, 3)
            p.setPen(QColor("#FFFFFF"))
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.drawText(QRect(4, 4, 14, 14), Qt.AlignmentFlag.AlignCenter, "✓")

        # If hovered, draw small close button '✕' on top-right
        if self.is_hovered:
            p.setBrush(QBrush(QColor(211, 47, 47, 220)))  # crimson red
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRect(88, 4, 18, 18), 3, 3)
            p.setPen(QColor("#FFFFFF"))
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.drawText(QRect(88, 3, 18, 18), Qt.AlignmentFlag.AlignCenter, "✕")

        p.end()

class ThumbnailBar(QWidget):
    capture_selected = pyqtSignal(object)  # CaptureItem or None
    save_all_requested = pyqtSignal()
    open_image_requested = pyqtSignal()
    paste_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setStyleSheet(f"""
            QWidget#ThumbnailBarContainer {{
                background-color: #181A1F;
                border-top: 1px solid {ThemeColors.BORDER_LIGHT};
            }}
        """)
        self.setObjectName("ThumbnailBarContainer")

        self.captures: List[CaptureItem] = []
        self.active_item: Optional[CaptureItem] = None
        self.selected_items: List[CaptureItem] = []
        self.card_widgets: List[ThumbnailCard] = []

        if not self.captures:
            config.set_next_capture_number(1)

        self.setAcceptDrops(True)
        self._init_ui()
        self.sync_config_values()

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
        top_window = self.window()
        if hasattr(top_window, 'handle_dropped_mime_data'):
            top_window.handle_dropped_mime_data(event)
        else:
            event.ignore()

    def _create_header_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        sep.setStyleSheet("background-color: #3E4451; max-width: 1px; margin: 3px 4px;")
        return sep

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(5)

        # -------------------------------------------------------------
        # Header Control Bar (Solid Pro Dark UI)
        # -------------------------------------------------------------
        h_top = QHBoxLayout()
        h_top.setContentsMargins(0, 0, 0, 0)
        h_top.setSpacing(8)

        # Section 1: Gallery Info Badge
        gallery_info_layout = QHBoxLayout()
        gallery_info_layout.setSpacing(6)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconFactory.get_pixmap("gallery", 16))
        gallery_info_layout.addWidget(lbl_icon)

        lbl_title = QLabel("GALLERY")
        lbl_title.setStyleSheet("""
            font-size: 10px;
            font-weight: 800;
            color: #828997;
            letter-spacing: 0.5px;
        """)
        gallery_info_layout.addWidget(lbl_title)

        self.lbl_count_badge = QLabel("0")
        self.lbl_count_badge.setStyleSheet("""
            QLabel {
                background-color: #282C34;
                color: #61AFEF;
                font-size: 11px;
                font-weight: bold;
                padding: 1px 7px;
                border-radius: 9px;
                border: 1px solid #3E4451;
            }
        """)
        gallery_info_layout.addWidget(self.lbl_count_badge)
        h_top.addLayout(gallery_info_layout)

        # Delete Selected Button
        self.btn_delete_selected = QPushButton("Delete Selected")
        self.btn_delete_selected.setIcon(IconFactory.get_icon("delete", 13))
        self.btn_delete_selected.setIconSize(QSize(13, 13))
        self.btn_delete_selected.setFixedHeight(26)
        self.btn_delete_selected.setToolTip("Delete selected image(s) from gallery (Delete key)")
        self.btn_delete_selected.setStyleSheet("""
            QPushButton {
                background-color: #21252B;
                color: #E06C75;
                border: 1px solid #3E4451;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 9px;
            }
            QPushButton:hover {
                background-color: #3B2024;
                border: 1px solid #E06C75;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #5C1D24;
            }
        """)
        self.btn_delete_selected.clicked.connect(self.delete_selected_items)
        h_top.addWidget(self.btn_delete_selected)

        # Divider 1
        h_top.addWidget(self._create_header_separator())

        # Section 2: Sequential Naming Controls
        lbl_pfx = QLabel("Prefix:")
        lbl_pfx.setStyleSheet("color: #ABB2BF; font-size: 11px; font-weight: 600;")
        h_top.addWidget(lbl_pfx)

        self.txt_prefix = QLineEdit()
        self.txt_prefix.setPlaceholderText("(None)")
        self.txt_prefix.setToolTip("Prefix for capture filenames (leave empty for pure numbers: 1, 2, 3...)")
        self.txt_prefix.setFixedWidth(70)
        self.txt_prefix.setFixedHeight(26)
        self.txt_prefix.setStyleSheet("""
            QLineEdit {
                background-color: #181A1F;
                color: #ECEFF4;
                font-size: 11px;
                font-weight: 500;
                border: 1px solid #3E4451;
                border-radius: 4px;
                padding: 2px 6px;
            }
            QLineEdit:focus {
                border: 1px solid #61AFEF;
                background-color: #1E2227;
            }
        """)
        self.txt_prefix.textChanged.connect(self._on_prefix_changed)
        h_top.addWidget(self.txt_prefix)

        lbl_next = QLabel("Next #:")
        lbl_next.setStyleSheet("color: #ABB2BF; font-size: 11px; font-weight: 600;")
        h_top.addWidget(lbl_next)

        self.spin_next_num = QSpinBox()
        self.spin_next_num.setRange(1, 999999)
        self.spin_next_num.setValue(1)
        self.spin_next_num.setToolTip("Starting / Next capture number (1, 2, 3...).")
        self.spin_next_num.setFixedWidth(70)
        self.spin_next_num.setFixedHeight(26)
        self.spin_next_num.setStyleSheet("""
            QSpinBox {
                background-color: #181A1F;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #3E4451;
                border-radius: 4px;
                padding: 1px 4px;
            }
            QSpinBox:focus {
                border: 1px solid #61AFEF;
                background-color: #1E2227;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #282C34;
                border-left: 1px solid #3E4451;
                width: 16px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #3E4451;
            }
        """)
        self.spin_next_num.valueChanged.connect(self._on_next_num_changed)
        h_top.addWidget(self.spin_next_num)

        btn_renumber = QPushButton("Renumber")
        btn_renumber.setIcon(IconFactory.get_icon("renumber", 13))
        btn_renumber.setIconSize(QSize(13, 13))
        btn_renumber.setFixedHeight(26)
        btn_renumber.setToolTip("Renumber all existing captures in gallery sequentially starting from current number (1, 2, 3...)")
        btn_renumber.setStyleSheet("""
            QPushButton {
                background-color: #282C34;
                color: #D8DEE9;
                border: 1px solid #3E4451;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                padding: 2px 9px;
            }
            QPushButton:hover {
                background-color: #353B45;
                color: #FFFFFF;
                border-color: #4B5263;
            }
            QPushButton:pressed {
                background-color: #21252B;
            }
        """)
        btn_renumber.clicked.connect(self.renumber_gallery)
        h_top.addWidget(btn_renumber)

        h_top.addStretch()

        # Section 3: Action Buttons (Right)
        btn_save_all = QPushButton("Save All (Batch)")
        btn_save_all.setIcon(IconFactory.get_icon("save", 14))
        btn_save_all.setIconSize(QSize(14, 14))
        btn_save_all.setFixedHeight(26)
        btn_save_all.setToolTip("Save all images in gallery to configured folder (Ctrl+Shift+S)")
        btn_save_all.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border: 1px solid #3B82F6;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 12px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
                border-color: #60A5FA;
            }
            QPushButton:pressed {
                background-color: #1E40AF;
            }
        """)
        btn_save_all.clicked.connect(self.save_all_requested.emit)
        h_top.addWidget(btn_save_all)

        btn_paste = QPushButton("Paste")
        btn_paste.setIcon(IconFactory.get_icon("paste", 13))
        btn_paste.setIconSize(QSize(13, 13))
        btn_paste.setFixedHeight(26)
        btn_paste.setToolTip("Paste image from clipboard into gallery (Ctrl+V)")
        btn_paste.setStyleSheet("""
            QPushButton {
                background-color: #282C34;
                color: #D8DEE9;
                border: 1px solid #3E4451;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                padding: 2px 10px;
            }
            QPushButton:hover {
                background-color: #353B45;
                color: #FFFFFF;
                border-color: #4B5263;
            }
            QPushButton:pressed {
                background-color: #21252B;
            }
        """)
        btn_paste.clicked.connect(self.paste_requested.emit)
        h_top.addWidget(btn_paste)

        btn_open = QPushButton("Open...")
        btn_open.setIcon(IconFactory.get_icon("open_image", 13))
        btn_open.setIconSize(QSize(13, 13))
        btn_open.setFixedHeight(26)
        btn_open.setToolTip("Add image from disk to gallery")
        btn_open.setStyleSheet("""
            QPushButton {
                background-color: #282C34;
                color: #D8DEE9;
                border: 1px solid #3E4451;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                padding: 2px 10px;
            }
            QPushButton:hover {
                background-color: #353B45;
                color: #FFFFFF;
                border-color: #4B5263;
            }
            QPushButton:pressed {
                background-color: #21252B;
            }
        """)
        btn_open.clicked.connect(self.open_image_requested.emit)
        h_top.addWidget(btn_open)

        btn_clear = QPushButton("Clear All")
        btn_clear.setIcon(IconFactory.get_icon("delete", 13))
        btn_clear.setIconSize(QSize(13, 13))
        btn_clear.setFixedHeight(26)
        btn_clear.setToolTip("Clear all images from gallery")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #282C34;
                color: #ABB2BF;
                border: 1px solid #3E4451;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                padding: 2px 10px;
            }
            QPushButton:hover {
                background-color: #3E2723;
                color: #E06C75;
                border-color: #E06C75;
            }
            QPushButton:pressed {
                background-color: #4E1F24;
            }
        """)
        btn_clear.clicked.connect(self.clear_all)
        h_top.addWidget(btn_clear)

        main_layout.addLayout(h_top)

        # Horizontal Scroll Area for Thumbnails
        self.scroll = QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background-color: transparent; border: none;")

        self.scroll_widget = QWidget()
        self.scroll_layout = QHBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(2, 2, 2, 2)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.scroll.setWidget(self.scroll_widget)
        main_layout.addWidget(self.scroll)

    def sync_config_values(self):
        """Syncs GUI controls with current config values."""
        self.txt_prefix.blockSignals(True)
        self.txt_prefix.setText(str(config.get("filename_prefix", "")))
        self.txt_prefix.blockSignals(False)

        self.spin_next_num.blockSignals(True)
        try:
            num = int(config.get("next_capture_number", 1))
        except (ValueError, TypeError):
            num = 1
        self.spin_next_num.setValue(num)
        self.spin_next_num.blockSignals(False)

    def _on_prefix_changed(self, text: str):
        config.set("filename_prefix", text.strip())

    def _on_next_num_changed(self, val: int):
        config.set_next_capture_number(val)

    def renumber_gallery(self):
        """Renumbers all images in gallery starting from current spin_next_num and prefix."""
        if not self.captures:
            return
        prefix = self.txt_prefix.text().strip()
        start_num = self.spin_next_num.value()
        for idx, item in enumerate(self.captures):
            n = start_num + idx
            if prefix:
                item.name = f"{prefix}_{n}" if not prefix.endswith(('_', '-')) else f"{prefix}{n}"
            else:
                item.name = str(n)
        
        next_num = start_num + len(self.captures)
        config.set_next_capture_number(next_num)
        self.spin_next_num.blockSignals(True)
        self.spin_next_num.setValue(next_num)
        self.spin_next_num.blockSignals(False)
        self.refresh_thumbnails()

    def add_capture(self, pixmap: QPixmap, name: str = "") -> CaptureItem:
        if not name and not self.captures:
            # Gallery is starting fresh -> reset counter to 1
            config.set_next_capture_number(1)
        item = CaptureItem(pixmap, name)
        self.captures.append(item)
        self.active_item = item
        self.selected_items = [item]
        self.refresh_thumbnails()
        self.capture_selected.emit(item)
        
        # If item has a purely numeric name (e.g. "14"), update next_capture_number to max(current, num + 1)
        if item.name and item.name.strip().isdigit():
            cur_next = int(config.get("next_capture_number", 1))
            num_val = int(item.name.strip())
            if num_val >= cur_next:
                config.set_next_capture_number(num_val + 1)

        # Update spinbox to show the next number
        self.spin_next_num.blockSignals(True)
        self.spin_next_num.setValue(int(config.get("next_capture_number", 1)))
        self.spin_next_num.blockSignals(False)

        # Scroll to the rightmost end
        self.scroll.horizontalScrollBar().setValue(self.scroll.horizontalScrollBar().maximum())
        return item

    def get_selected_items(self) -> List[CaptureItem]:
        if self.selected_items:
            return [it for it in self.selected_items if it in self.captures]
        elif self.active_item and self.active_item in self.captures:
            return [self.active_item]
        return []

    def handle_card_clicked(self, item: CaptureItem, modifiers=None):
        if modifiers and (modifiers & Qt.KeyboardModifier.ControlModifier):
            # Ctrl+Click: Toggle selection
            if item in self.selected_items:
                self.selected_items.remove(item)
                if self.active_item == item:
                    self.active_item = self.selected_items[-1] if self.selected_items else None
            else:
                self.selected_items.append(item)
                self.active_item = item
        elif modifiers and (modifiers & Qt.KeyboardModifier.ShiftModifier) and self.active_item in self.captures and item in self.captures:
            # Shift+Click: Select range
            idx_from = self.captures.index(self.active_item)
            idx_to = self.captures.index(item)
            start_i = min(idx_from, idx_to)
            end_i = max(idx_from, idx_to)
            self.selected_items = self.captures[start_i:end_i + 1]
            self.active_item = item
        else:
            # Normal Click: Select single item
            self.active_item = item
            self.selected_items = [item]

        self._update_cards_selection()
        if self.active_item:
            self.capture_selected.emit(self.active_item)

    def select_item(self, item: CaptureItem):
        self.active_item = item
        self.selected_items = [item]
        self._update_cards_selection()
        self.capture_selected.emit(item)
        self._ensure_card_visible(item)

    def select_next_item(self):
        """Navigates to the next image in the gallery (Right Arrow)."""
        if not self.captures:
            return
        if self.active_item in self.captures:
            cur_idx = self.captures.index(self.active_item)
            next_idx = (cur_idx + 1) % len(self.captures)
        else:
            next_idx = 0
        self.select_item(self.captures[next_idx])

    def select_previous_item(self):
        """Navigates to the previous image in the gallery (Left Arrow)."""
        if not self.captures:
            return
        if self.active_item in self.captures:
            cur_idx = self.captures.index(self.active_item)
            prev_idx = (cur_idx - 1) % len(self.captures)
        else:
            prev_idx = len(self.captures) - 1
        self.select_item(self.captures[prev_idx])

    def _ensure_card_visible(self, item: CaptureItem):
        """Ensures the card corresponding to item is smoothly scrolled into view."""
        for card in self.card_widgets:
            if card.item == item:
                self.scroll.ensureWidgetVisible(card, 50, 0)
                break

    def _update_cards_selection(self):
        sel_set = set(self.selected_items)
        for card in self.card_widgets:
            card.set_selection_state(
                is_active=(card.item == self.active_item),
                is_selected=(card.item in sel_set)
            )
        count_sel = len(self.get_selected_items())
        if count_sel > 1:
            self.btn_delete_selected.setText(f"Delete ({count_sel})")
        else:
            self.btn_delete_selected.setText("Delete Selected")

    def delete_single_item(self, item: CaptureItem):
        """Prompts confirmation popup before deleting a single image."""
        if not item or item not in self.captures:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete Image",
            f"Are you sure you want to delete image '{item.name}' from the gallery?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._do_remove_items([item])

    def delete_items_with_confirmation(self, items: List[CaptureItem]):
        """Prompts confirmation popup before deleting one or multiple selected images."""
        if not items:
            return
        if len(items) == 1:
            self.delete_single_item(items[0])
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete Multiple Images",
            f"Are you sure you want to delete {len(items)} selected images from the gallery?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._do_remove_items(items)

    def delete_selected_items(self):
        """Deletes all currently selected images with confirmation popup."""
        items = self.get_selected_items()
        if not items:
            return
        self.delete_items_with_confirmation(items)

    def _do_remove_items(self, items: List[CaptureItem]):
        """Internal worker that removes items from list and refreshes UI."""
        items_set = set(items)
        self.captures = [it for it in self.captures if it not in items_set]
        self.selected_items = [it for it in self.selected_items if it not in items_set]

        if not self.captures:
            # Gallery is completely empty -> reset next capture number to 1!
            config.set_next_capture_number(1)
            self.spin_next_num.blockSignals(True)
            self.spin_next_num.setValue(1)
            self.spin_next_num.blockSignals(False)
            self.active_item = None
            self.selected_items = []
        elif self.active_item in items_set or not self.active_item:
            self.active_item = self.captures[0]
            self.selected_items = [self.active_item]

        self.refresh_thumbnails()
        self.capture_selected.emit(self.active_item)

    def clear_all(self):
        """Prompts confirmation popup before clearing all gallery images."""
        if not self.captures:
            return
        res = QMessageBox.question(
            self, 
            "Clear Gallery", 
            f"Are you sure you want to remove all {len(self.captures)} images from the gallery?", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self.captures.clear()
            self.selected_items.clear()
            self.active_item = None
            # Reset next number to 1
            config.set_next_capture_number(1)
            self.spin_next_num.blockSignals(True)
            self.spin_next_num.setValue(1)
            self.spin_next_num.blockSignals(False)
            self.refresh_thumbnails()
            self.capture_selected.emit(None)

    def refresh_thumbnails(self):
        # Clear existing cards
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.card_widgets.clear()

        sel_set = set(self.selected_items)
        for item in self.captures:
            card = ThumbnailCard(
                item, 
                is_active=(item == self.active_item),
                is_selected=(item in sel_set)
            )
            card.clicked.connect(self.handle_card_clicked)
            card.delete_requested.connect(self.delete_single_item)
            card.save_requested.connect(lambda it: self.save_all_requested.emit())
            self.scroll_layout.addWidget(card)
            self.card_widgets.append(card)

        self.lbl_count_badge.setText(str(len(self.captures)))
        count_sel = len(self.get_selected_items())
        if count_sel > 1:
            self.btn_delete_selected.setText(f"Delete ({count_sel})")
        else:
            self.btn_delete_selected.setText("Delete Selected")

    def update_active_thumbnail(self):
        for card in self.card_widgets:
            if card.item == self.active_item:
                card.update()
                break
