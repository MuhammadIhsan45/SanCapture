"""
Sniper Overlay with 8x Loupe Magnifier for FastCapture.
Provides pixel-precision crosshair, live color sampler (RGB/HEX), coordinates, and resizing handles.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap, 
    QKeyEvent, QMouseEvent, QCursor, QImage
)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal

class SniperOverlay(QWidget):
    capture_completed = pyqtSignal(QPixmap)
    capture_cancelled = pyqtSignal()

    def __init__(self, full_screen_pixmap: QPixmap, virtual_offset: QPoint):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.full_pixmap = full_screen_pixmap
        self.full_image = full_screen_pixmap.toImage()
        self.virtual_offset = virtual_offset

        self.start_pos: QPoint = None
        self.current_pos: QPoint = None
        self.selected_rect: QRect = None
        self.is_selecting = False
        self.is_resizing = False
        self.active_handle = None

        # Resize handles size
        self.handle_size = 7

        # Set geometry to cover the full virtual desktop
        self.setGeometry(
            virtual_offset.x(), 
            virtual_offset.y(), 
            full_screen_pixmap.width(), 
            full_screen_pixmap.height()
        )

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            # Check if clicking on resize handles
            if self.selected_rect and not self.selected_rect.isEmpty():
                handle = self._get_handle_at(pos)
                if handle:
                    self.is_resizing = True
                    self.active_handle = handle
                    return

                # If clicking inside existing selection, confirm on double click or start move
                if self.selected_rect.contains(pos):
                    # Keep existing selection
                    return

            self.is_selecting = True
            self.start_pos = pos
            self.current_pos = pos
            self.selected_rect = QRect(pos, pos)
            self.update()

        elif event.button() == Qt.MouseButton.RightButton:
            # If selection exists, clear selection first; if none, cancel overlay
            if self.selected_rect and not self.selected_rect.isEmpty():
                self.selected_rect = None
                self.start_pos = None
                self.update()
            else:
                self.close()
                self.capture_cancelled.emit()

    def mouseMoveEvent(self, event: QMouseEvent):
        self.current_pos = event.pos()

        if self.is_selecting:
            self.selected_rect = QRect(self.start_pos, self.current_pos).normalized()
        elif self.is_resizing and self.selected_rect:
            self._resize_selection(self.current_pos)
        elif self.selected_rect and not self.selected_rect.isEmpty():
            handle = self._get_handle_at(self.current_pos)
            if handle:
                self._update_cursor_for_handle(handle)
            elif self.selected_rect.contains(self.current_pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_selecting:
                self.is_selecting = False
                if self.selected_rect and (self.selected_rect.width() < 3 or self.selected_rect.height() < 3):
                    self.selected_rect = None
            elif self.is_resizing:
                self.is_resizing = False
                self.active_handle = None
            self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.selected_rect and self.selected_rect.contains(event.pos()):
                self._finish_capture()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close()
            self.capture_cancelled.emit()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self.selected_rect and not self.selected_rect.isEmpty():
                self._finish_capture()
        # Pixel nudge with arrow keys
        elif self.selected_rect and not self.selected_rect.isEmpty():
            step = 10 if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 1
            r = self.selected_rect
            if key == Qt.Key.Key_Left:
                self.selected_rect = r.translated(-step, 0)
            elif key == Qt.Key.Key_Right:
                self.selected_rect = r.translated(step, 0)
            elif key == Qt.Key.Key_Up:
                self.selected_rect = r.translated(0, -step)
            elif key == Qt.Key.Key_Down:
                self.selected_rect = r.translated(0, step)
            self.update()

    def _finish_capture(self):
        if not self.selected_rect or self.selected_rect.isEmpty():
            return
        
        # Intersect with full image
        target = self.selected_rect.intersected(QRect(0, 0, self.full_pixmap.width(), self.full_pixmap.height()))
        if target.isEmpty() or target.width() < 2 or target.height() < 2:
            return

        captured_pixmap = self.full_pixmap.copy(target)
        self.close()
        self.capture_completed.emit(captured_pixmap)

    def _get_handles(self) -> dict:
        if not self.selected_rect or self.selected_rect.isEmpty():
            return {}
        r = self.selected_rect
        s = self.handle_size
        hs = s // 2
        return {
            "top_left": QRect(r.left() - hs, r.top() - hs, s, s),
            "top_mid": QRect(r.center().x() - hs, r.top() - hs, s, s),
            "top_right": QRect(r.right() - hs, r.top() - hs, s, s),
            "mid_left": QRect(r.left() - hs, r.center().y() - hs, s, s),
            "mid_right": QRect(r.right() - hs, r.center().y() - hs, s, s),
            "bottom_left": QRect(r.left() - hs, r.bottom() - hs, s, s),
            "bottom_mid": QRect(r.center().x() - hs, r.bottom() - hs, s, s),
            "bottom_right": QRect(r.right() - hs, r.bottom() - hs, s, s),
        }

    def _get_handle_at(self, pos: QPoint):
        for name, rect in self._get_handles().items():
            if rect.contains(pos):
                return name
        return None

    def _update_cursor_for_handle(self, handle: str):
        if handle in ("top_left", "bottom_right"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif handle in ("top_right", "bottom_left"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif handle in ("top_mid", "bottom_mid"):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif handle in ("mid_left", "mid_right"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)

    def _resize_selection(self, pos: QPoint):
        r = self.selected_rect
        h = self.active_handle
        if h == "top_left":
            self.selected_rect = QRect(pos, r.bottomRight()).normalized()
        elif h == "top_mid":
            self.selected_rect = QRect(r.left(), min(pos.y(), r.bottom()), r.width(), abs(r.bottom() - pos.y()))
        elif h == "top_right":
            self.selected_rect = QRect(QPoint(r.left(), pos.y()), QPoint(pos.x(), r.bottom())).normalized()
        elif h == "mid_left":
            self.selected_rect = QRect(min(pos.x(), r.right()), r.top(), abs(r.right() - pos.x()), r.height())
        elif h == "mid_right":
            self.selected_rect = QRect(r.left(), r.top(), max(1, pos.x() - r.left()), r.height())
        elif h == "bottom_left":
            self.selected_rect = QRect(QPoint(pos.x(), r.top()), QPoint(r.right(), pos.y())).normalized()
        elif h == "bottom_mid":
            self.selected_rect = QRect(r.left(), r.top(), r.width(), max(1, pos.y() - r.top()))
        elif h == "bottom_right":
            self.selected_rect = QRect(r.topLeft(), pos).normalized()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 1. Draw base frozen desktop
        painter.drawPixmap(0, 0, self.full_pixmap)

        # 2. Dimmed overlay
        dim_color = QColor(0, 0, 0, 100)
        if self.selected_rect and not self.selected_rect.isEmpty():
            # Draw 4 dark surrounding rectangles around the clear selected box
            r = self.selected_rect
            w = self.width()
            h = self.height()
            painter.fillRect(0, 0, w, r.top(), dim_color)
            painter.fillRect(0, r.bottom() + 1, w, h - r.bottom() - 1, dim_color)
            painter.fillRect(0, r.top(), r.left(), r.height() + 1, dim_color)
            painter.fillRect(r.right() + 1, r.top(), w - r.right() - 1, r.height() + 1, dim_color)

            # Draw crisp cyan/red border around selection
            pen = QPen(QColor("#00E5FF"), 1.5, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(r)

            # Draw 8 resize handles
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.setPen(QPen(QColor("#007ACC"), 1))
            for h_rect in self._get_handles().values():
                painter.drawRect(h_rect)

            # Draw dimension tooltip badge above or inside selection
            dim_text = f"{r.width()} × {r.height()} px"
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            badge_w = 90
            badge_h = 22
            badge_x = r.left()
            badge_y = r.top() - badge_h - 4 if r.top() > badge_h + 8 else r.top() + 6
            painter.setBrush(QBrush(QColor("#181A1F")))
            painter.setPen(QPen(QColor("#00E5FF"), 1))
            painter.drawRect(badge_x, badge_y, badge_w, badge_h)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(QRect(badge_x, badge_y, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, dim_text)

        else:
            # Full screen dim
            painter.fillRect(0, 0, self.width(), self.height(), dim_color)

        # 3. Draw Sniper Crosshair across full screen or local
        if self.current_pos:
            cx = self.current_pos.x()
            cy = self.current_pos.y()
            
            # Subtle full-length sniper crosshair
            pen_cross = QPen(QColor(229, 57, 53, 160), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen_cross)
            painter.drawLine(0, cy, self.width(), cy)
            painter.drawLine(cx, 0, cx, self.height())

            # 4. Draw FastStone-style 8x Loupe Magnifier
            if not self.is_selecting and (not self.selected_rect or self.selected_rect.isEmpty()):
                self._draw_loupe(painter, cx, cy)

        painter.end()

    def _draw_loupe(self, p: QPainter, cx: int, cy: int):
        """Draws the 8x live pixel loupe magnifier near the cursor."""
        zoom = 8
        grid_cells = 17  # 17x17 grid
        cell_px = 6
        loupe_w = grid_cells * cell_px
        loupe_h = loupe_w
        info_panel_h = 55
        total_w = loupe_w + 4
        total_h = loupe_h + info_panel_h + 4

        # Position loupe: smart flip away from cursor
        offset_x = 25
        offset_y = 25
        if cx + offset_x + total_w > self.width():
            lx = cx - offset_x - total_w
        else:
            lx = cx + offset_x

        if cy + offset_y + total_h > self.height():
            ly = cy - offset_y - total_h
        else:
            ly = cy + offset_y

        # Loupe container background & crisp border
        p.setBrush(QBrush(QColor("#1A1D21")))
        p.setPen(QPen(QColor("#D32F2F"), 1.5))
        p.drawRect(lx, ly, total_w, total_h)

        # Draw magnified pixels
        half = grid_cells // 2
        start_gx = cx - half
        start_gy = cy - half

        # Sample center pixel color
        center_color = QColor(0, 0, 0)
        if 0 <= cx < self.full_image.width() and 0 <= cy < self.full_image.height():
            center_color = self.full_image.pixelColor(cx, cy)

        grid_start_x = lx + 2
        grid_start_y = ly + 2

        for row in range(grid_cells):
            for col in range(grid_cells):
                src_x = start_gx + col
                src_y = start_gy + row
                if 0 <= src_x < self.full_image.width() and 0 <= src_y < self.full_image.height():
                    pixel_col = self.full_image.pixelColor(src_x, src_y)
                else:
                    pixel_col = QColor(0, 0, 0)

                cell_rect = QRect(grid_start_x + col * cell_px, grid_start_y + row * cell_px, cell_px, cell_px)
                p.fillRect(cell_rect, pixel_col)

        # Draw pixel grid overlay
        p.setPen(QPen(QColor(255, 255, 255, 35), 1))
        for i in range(grid_cells + 1):
            p.drawLine(grid_start_x + i * cell_px, grid_start_y, grid_start_x + i * cell_px, grid_start_y + loupe_h)
            p.drawLine(grid_start_x, grid_start_y + i * cell_px, grid_start_x + loupe_w, grid_start_y + i * cell_px)

        # Center pixel sniper box (red square)
        center_cell_rect = QRect(grid_start_x + half * cell_px, grid_start_y + half * cell_px, cell_px, cell_px)
        p.setPen(QPen(QColor("#FF0000"), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(center_cell_rect)

        # Info Box (Coordinates, HEX, RGB)
        info_y = grid_start_y + loupe_h + 2
        p.fillRect(lx + 2, info_y, total_w - 4, info_panel_h, QColor("#111317"))
        
        # Color preview block
        p.fillRect(lx + 6, info_y + 6, 20, 20, center_color)
        p.setPen(QPen(QColor("#ECEFF4"), 1))
        p.drawRect(lx + 6, info_y + 6, 20, 20)

        # Text labels
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        hex_str = center_color.name().upper()
        rgb_str = f"RGB: {center_color.red()}, {center_color.green()}, {center_color.blue()}"
        pos_str = f"Pos: ({cx + self.virtual_offset.x()}, {cy + self.virtual_offset.y()})"

        p.setPen(QColor("#00E5FF"))
        p.drawText(lx + 32, info_y + 16, hex_str)

        p.setFont(QFont("Segoe UI", 7))
        p.setPen(QColor("#ABB2BF"))
        p.drawText(lx + 32, info_y + 28, rgb_str)
        p.drawText(lx + 6, info_y + 44, pos_str)
