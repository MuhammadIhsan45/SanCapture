"""
Window / Object Picker Overlay for FastCapture.
Detects windows and controls under the cursor in real time with a bold red target highlight.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPixmap, QMouseEvent, QKeyEvent, QCursor
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from app.core.window_detector import WindowDetector

class WindowPickerOverlay(QWidget):
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
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.full_pixmap = full_screen_pixmap
        self.virtual_offset = virtual_offset
        self.highlight_rect: QRect = None

        self.setGeometry(
            virtual_offset.x(), 
            virtual_offset.y(), 
            full_screen_pixmap.width(), 
            full_screen_pixmap.height()
        )

    def mouseMoveEvent(self, event: QMouseEvent):
        # Global screen coordinate
        global_x = event.pos().x() + self.virtual_offset.x()
        global_y = event.pos().y() + self.virtual_offset.y()

        detected = WindowDetector.get_object_under_point(QPoint(global_x, global_y))
        if detected:
            # Map back to local widget coordinates
            local_x = detected.x() - self.virtual_offset.x()
            local_y = detected.y() - self.virtual_offset.y()
            self.highlight_rect = QRect(local_x, local_y, detected.width(), detected.height())
        else:
            self.highlight_rect = None

        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.highlight_rect and not self.highlight_rect.isEmpty():
                target = self.highlight_rect.intersected(QRect(0, 0, self.full_pixmap.width(), self.full_pixmap.height()))
                if not target.isEmpty():
                    captured = self.full_pixmap.copy(target)
                    self.close()
                    self.capture_completed.emit(captured)
                    return
            # Fallback: capture full screen
            self.close()
            self.capture_completed.emit(self.full_pixmap)

        elif event.button() == Qt.MouseButton.RightButton:
            self.close()
            self.capture_cancelled.emit()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            self.capture_cancelled.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        # Draw background frozen screen
        painter.drawPixmap(0, 0, self.full_pixmap)

        if self.highlight_rect and not self.highlight_rect.isEmpty():
            r = self.highlight_rect
            # Highlight target area with subtle red wash
            painter.fillRect(r, QColor(229, 57, 53, 30))

            # Bold red solid border (FastStone signature)
            pen = QPen(QColor("#D32F2F"), 3, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(r)

            # Dimension badge
            dim_str = f"Target: {r.width()} × {r.height()} px  (Click to capture)"
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            badge_w = 230
            badge_h = 24
            badge_x = max(10, min(r.left(), self.width() - badge_w - 10))
            badge_y = r.top() - badge_h - 4 if r.top() > badge_h + 8 else r.bottom() + 4
            
            painter.setBrush(QBrush(QColor("#181A1F")))
            painter.setPen(QPen(QColor("#D32F2F"), 1.5))
            painter.drawRect(badge_x, badge_y, badge_w, badge_h)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(QRect(badge_x, badge_y, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, dim_str)

        painter.end()
