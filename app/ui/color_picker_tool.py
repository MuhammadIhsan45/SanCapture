"""
Dedicated Screen Color Picker Tool with Loupe Magnifier for FastCapture.
Instantly samples pixel colors across any screen and copies HEX / RGB to clipboard.
"""

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPixmap, QMouseEvent, QKeyEvent
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal

class ColorPickerTool(QWidget):
    color_picked = pyqtSignal(str, QColor)  # hex_string, QColor
    cancelled = pyqtSignal()

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
        self.current_pos = QPoint(0, 0)

        self.setGeometry(
            virtual_offset.x(), 
            virtual_offset.y(), 
            full_screen_pixmap.width(), 
            full_screen_pixmap.height()
        )

    def mouseMoveEvent(self, event: QMouseEvent):
        self.current_pos = event.pos()
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            cx = self.current_pos.x()
            cy = self.current_pos.y()
            if 0 <= cx < self.full_image.width() and 0 <= cy < self.full_image.height():
                color = self.full_image.pixelColor(cx, cy)
                hex_str = color.name().upper()
                # Copy to system clipboard
                clipboard = QApplication.clipboard()
                clipboard.setText(hex_str)
                self.close()
                self.color_picked.emit(hex_str, color)
        elif event.button() == Qt.MouseButton.RightButton:
            self.close()
            self.cancelled.emit()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            self.cancelled.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(0, 0, self.full_pixmap)

        cx = self.current_pos.x()
        cy = self.current_pos.y()

        # Draw Loupe Magnifier 11x11
        zoom = 8
        grid_cells = 17
        cell_px = 7
        loupe_w = grid_cells * cell_px
        info_panel_h = 60
        total_w = loupe_w + 4
        total_h = loupe_w + info_panel_h + 4

        # Smart position
        offset_x, offset_y = 25, 25
        lx = cx - offset_x - total_w if cx + offset_x + total_w > self.width() else cx + offset_x
        ly = cy - offset_y - total_h if cy + offset_y + total_h > self.height() else cy + offset_y

        # Loupe container
        painter.setBrush(QBrush(QColor("#1A1D21")))
        painter.setPen(QPen(QColor("#F57C00"), 1.5))
        painter.drawRect(lx, ly, total_w, total_h)

        half = grid_cells // 2
        start_gx = cx - half
        start_gy = cy - half
        center_color = QColor(0, 0, 0)
        if 0 <= cx < self.full_image.width() and 0 <= cy < self.full_image.height():
            center_color = self.full_image.pixelColor(cx, cy)

        grid_start_x = lx + 2
        grid_start_y = ly + 2

        for row in range(grid_cells):
            for col in range(grid_cells):
                sx = start_gx + col
                sy = start_gy + row
                if 0 <= sx < self.full_image.width() and 0 <= sy < self.full_image.height():
                    pixel_col = self.full_image.pixelColor(sx, sy)
                else:
                    pixel_col = QColor(0, 0, 0)
                cell_rect = QRect(grid_start_x + col * cell_px, grid_start_y + row * cell_px, cell_px, cell_px)
                painter.fillRect(cell_rect, pixel_col)

        # Grid lines
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        for i in range(grid_cells + 1):
            painter.drawLine(grid_start_x + i * cell_px, grid_start_y, grid_start_x + i * cell_px, grid_start_y + loupe_w)
            painter.drawLine(grid_start_x, grid_start_y + i * cell_px, grid_start_x + loupe_w, grid_start_y + i * cell_px)

        # Center target
        center_cell_rect = QRect(grid_start_x + half * cell_px, grid_start_y + half * cell_px, cell_px, cell_px)
        painter.setPen(QPen(QColor("#FF0000"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(center_cell_rect)

        # Info Box
        info_y = grid_start_y + loupe_w + 2
        painter.fillRect(lx + 2, info_y, total_w - 4, info_panel_h, QColor("#111317"))
        
        # Swatch
        painter.fillRect(lx + 6, info_y + 8, 22, 22, center_color)
        painter.setPen(QPen(QColor("#ECEFF4"), 1))
        painter.drawRect(lx + 6, info_y + 8, 22, 22)

        # Info text
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#00E5FF"))
        painter.drawText(lx + 34, info_y + 18, center_color.name().upper())

        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.setPen(QColor("#ECEFF4"))
        painter.drawText(lx + 34, info_y + 30, f"RGB: {center_color.red()}, {center_color.green()}, {center_color.blue()}")
        painter.setPen(QColor("#F57C00"))
        painter.drawText(lx + 6, info_y + 48, "Click to copy HEX to clipboard")

        painter.end()
