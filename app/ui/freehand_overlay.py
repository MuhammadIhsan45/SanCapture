"""
Freehand (Lasso) Capture Overlay for FastCapture.
Allows freeform polygonal screen capture with transparent cutout.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap, 
    QMouseEvent, QKeyEvent, QPainterPath, QPolygonF
)
from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, pyqtSignal

class FreehandOverlay(QWidget):
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
        self.virtual_offset = virtual_offset
        self.points = []
        self.is_drawing = False

        self.setGeometry(
            virtual_offset.x(), 
            virtual_offset.y(), 
            full_screen_pixmap.width(), 
            full_screen_pixmap.height()
        )

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = True
            self.points = [event.pos()]
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.close()
            self.capture_cancelled.emit()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_drawing:
            self.points.append(event.pos())
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            self.is_drawing = False
            if len(self.points) > 5:
                self._finish_freehand()
            else:
                self.points = []
                self.update()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            self.capture_cancelled.emit()

    def _finish_freehand(self):
        if len(self.points) < 3:
            return

        poly = QPolygonF([QPointF(p.x(), p.y()) for p in self.points])
        bounding_rect = poly.boundingRect().toRect()
        
        if bounding_rect.width() < 4 or bounding_rect.height() < 4:
            return

        # Create transparent canvas matching bounding box
        result_pixmap = QPixmap(bounding_rect.size())
        result_pixmap.fill(Qt.GlobalColor.transparent)

        # Clip and draw the freehand polygon
        painter = QPainter(result_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        path = QPainterPath()
        # Translate polygon to (0,0) relative to bounding_rect
        shifted_poly = QPolygonF([QPointF(p.x() - bounding_rect.x(), p.y() - bounding_rect.y()) for p in self.points])
        path.addPolygon(shifted_poly)
        path.closeSubpath()

        painter.setClipPath(path)
        # Draw source image shifted
        painter.drawPixmap(-bounding_rect.x(), -bounding_rect.y(), self.full_pixmap)
        painter.end()

        self.close()
        self.capture_completed.emit(result_pixmap)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(0, 0, self.full_pixmap)

        # Dim background
        painter.fillRect(0, 0, self.width(), self.height(), QColor(0, 0, 0, 90))

        if len(self.points) > 1:
            pen = QPen(QColor("#FF9800"), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 152, 0, 50)))

            path = QPainterPath()
            path.moveTo(QPointF(self.points[0].x(), self.points[0].y()))
            for p in self.points[1:]:
                path.lineTo(QPointF(p.x(), p.y()))
            painter.drawPath(path)

        painter.end()
