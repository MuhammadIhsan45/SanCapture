"""
Interactive Annotation & Drawing Canvas for FastCapture.
Supports Vector Arrows, Step Badges (1,2,3..), Shapes, Freehand & Rectangular Highlighter, Blur/Pixelate, Text, Pen, Crop, Zoom & Pan.
"""

import math
from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import QWidget, QInputDialog, QLineEdit
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap, 
    QMouseEvent, QKeyEvent, QWheelEvent, QPainterPath, 
    QPolygonF, QImage, QTransform
)
from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, pyqtSignal
from app.ui.effects import ImageEffects

class ToolType:
    SELECT = "select"
    ARROW = "arrow"
    RECT = "rect"
    ROUND_RECT = "round_rect"
    CIRCLE = "circle"
    STEP_BADGE = "step_badge"
    HIGHLIGHTER = "highlighter"          # Freehand highlighter pen
    HIGHLIGHTER_RECT = "highlighter_rect" # Rectangular text highlight box
    BLUR = "blur"
    PIXELATE = "pixelate"
    TEXT = "text"
    PEN = "pen"
    LINE = "line"
    HAND = "hand"
    CROP = "crop"

class CanvasItem:
    """Base class for drawable vector annotation items."""
    def __init__(self, tool_type: str, color: QColor, line_width: int, fill: bool = False, fill_color: QColor = None):
        self.tool_type = tool_type
        self.color = color
        self.line_width = line_width
        self.fill = fill
        self.fill_color = fill_color or QColor(color.red(), color.green(), color.blue(), 50)
        self.points: List[QPointF] = []
        self.text: str = ""
        self.font_size: int = 14
        self.step_number: int = 1
        self.is_selected = False

    def draw(self, p: QPainter):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        pen = QPen(self.color, self.line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)

        if self.tool_type == ToolType.PEN and len(self.points) >= 2:
            path = QPainterPath()
            path.moveTo(self.points[0])
            for pt in self.points[1:]:
                path.lineTo(pt)
            p.drawPath(path)

        elif self.tool_type == ToolType.LINE and len(self.points) >= 2:
            p.drawLine(self.points[0], self.points[1])

        elif self.tool_type == ToolType.ARROW and len(self.points) >= 2:
            p1, p2 = self.points[0], self.points[1]
            p.drawLine(p1, p2)
            # Arrow head
            angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
            arrow_len = max(12.0, self.line_width * 3.5)
            arrow_w = math.pi / 6
            h1 = QPointF(p2.x() - arrow_len * math.cos(angle - arrow_w), p2.y() - arrow_len * math.sin(angle - arrow_w))
            h2 = QPointF(p2.x() - arrow_len * math.cos(angle + arrow_w), p2.y() - arrow_len * math.sin(angle + arrow_w))
            p.setBrush(QBrush(self.color))
            p.drawPolygon(QPolygonF([p2, h1, h2]))

        elif self.tool_type == ToolType.RECT and len(self.points) >= 2:
            r = QRectF(self.points[0], self.points[1]).normalized()
            p.setBrush(QBrush(self.fill_color) if self.fill else Qt.BrushStyle.NoBrush)
            p.drawRect(r)

        elif self.tool_type == ToolType.ROUND_RECT and len(self.points) >= 2:
            r = QRectF(self.points[0], self.points[1]).normalized()
            p.setBrush(QBrush(self.fill_color) if self.fill else Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r, 8, 8)

        elif self.tool_type == ToolType.CIRCLE and len(self.points) >= 2:
            r = QRectF(self.points[0], self.points[1]).normalized()
            p.setBrush(QBrush(self.fill_color) if self.fill else Qt.BrushStyle.NoBrush)
            p.drawEllipse(r)

        elif self.tool_type == ToolType.HIGHLIGHTER and len(self.points) >= 2:
            # Semi-transparent broad fluorescent stroke
            hl_color = QColor(self.color.red(), self.color.green(), self.color.blue(), 115)
            p.setPen(QPen(hl_color, max(18, self.line_width * 4), Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
            path = QPainterPath()
            path.moveTo(self.points[0])
            for pt in self.points[1:]:
                path.lineTo(pt)
            p.drawPath(path)

        elif self.tool_type == ToolType.HIGHLIGHTER_RECT and len(self.points) >= 2:
            # Rectangular translucent highlighter box
            r = QRectF(self.points[0], self.points[1]).normalized()
            hl_color = QColor(self.color.red(), self.color.green(), self.color.blue(), 105)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(hl_color))
            p.drawRect(r)

        elif self.tool_type == ToolType.STEP_BADGE and len(self.points) >= 1:
            center = self.points[0]
            radius = max(14, self.line_width * 3.5)
            # Outer dark ring
            p.setPen(QPen(QColor("#000000"), 1.5))
            p.setBrush(QBrush(self.color))
            p.drawEllipse(center, radius, radius)
            # Badge number
            p.setPen(QColor("#FFFFFF"))
            p.setFont(QFont("Segoe UI", int(radius * 1.0), QFont.Weight.Bold))
            r = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, str(self.step_number))

        elif self.tool_type == ToolType.TEXT and len(self.points) >= 1 and self.text:
            pos = self.points[0]
            font = QFont("Segoe UI", self.font_size, QFont.Weight.Bold)
            p.setFont(font)
            metrics = p.fontMetrics()
            text_rect = metrics.boundingRect(self.text)
            padded_rect = QRectF(pos.x() - 4, pos.y() - 4, text_rect.width() + 8, text_rect.height() + 8)

            # Optional solid background box for high legibility
            p.setPen(QPen(self.color, 1))
            p.setBrush(QBrush(QColor("#1E2227")))
            p.drawRoundedRect(padded_rect, 3, 3)

            p.setPen(self.color)
            p.drawText(QRectF(pos.x(), pos.y(), text_rect.width() + 4, text_rect.height() + 4), 
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, self.text)

        p.restore()

class EditorCanvas(QWidget):
    status_updated = pyqtSignal(str)
    zoom_changed = pyqtSignal(float)
    can_undo_changed = pyqtSignal(bool)
    can_redo_changed = pyqtSignal(bool)
    content_modified = pyqtSignal()
    tool_change_requested = pyqtSignal(str)

    def __init__(self, initial_pixmap: QPixmap = None):
        super().__init__()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Base Image
        self.base_pixmap: QPixmap = initial_pixmap if initial_pixmap else QPixmap(800, 600)
        if initial_pixmap is None:
            self.base_pixmap.fill(QColor("#21252B"))

        # History Stack (snapshots of base_pixmap & items)
        self.undo_stack: List[tuple] = []
        self.redo_stack: List[tuple] = []

        # Items
        self.items: List[CanvasItem] = []
        self.current_item: Optional[CanvasItem] = None

        # Tool & Styles
        self._current_tool: str = ToolType.SELECT
        self.stroke_color = QColor("#D32F2F")  # Signature red default
        self.fill_color = QColor(211, 47, 47, 60)
        self.line_width = 3
        self.fill_enabled = False
        self.font_size = 14
        self.next_step_number = 1

        # Crop Tool state
        self.crop_rect: Optional[QRect] = None
        self.is_cropping = False

        # Figma-style Pan & Zoom state
        self.zoom_factor: float = 1.0
        self.pan_offset = QPoint(40, 40)
        self.is_panning = False
        self.is_space_held = False
        self.last_pan_pos = QPoint()

        # Enable Drag & Drop
        self.setAcceptDrops(True)

        # Save initial state to undo
        self._push_undo()

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

    def set_pixmap(self, pixmap: QPixmap):
        self.base_pixmap = QPixmap(pixmap)
        self.items.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.crop_rect = None
        self.next_step_number = 1
        self._push_undo()
        self.zoom_factor = 1.0
        self.pan_offset = QPoint(40, 40)
        self.update()
        self.zoom_changed.emit(self.zoom_factor)

    def load_capture_state(self, base_pixmap: QPixmap, items: list, undo_stack: list, redo_stack: list, next_step: int):
        self.base_pixmap = QPixmap(base_pixmap)
        self.items = [self._clone_item(i) for i in items]
        self.undo_stack = [(QPixmap(u[0]), [self._clone_item(i) for i in u[1]], u[2]) for u in undo_stack] if undo_stack else []
        self.redo_stack = [(QPixmap(r[0]), [self._clone_item(i) for i in r[1]], r[2]) for r in redo_stack] if redo_stack else []
        self.next_step_number = next_step
        if not self.undo_stack:
            self._push_undo()
        self.crop_rect = None
        self.can_undo_changed.emit(len(self.undo_stack) > 1)
        self.can_redo_changed.emit(len(self.redo_stack) > 0)
        self.update()

    def get_state(self):
        return (
            QPixmap(self.base_pixmap),
            [self._clone_item(i) for i in self.items],
            [(QPixmap(u[0]), [self._clone_item(i) for i in u[1]], u[2]) for u in self.undo_stack],
            [(QPixmap(r[0]), [self._clone_item(i) for i in r[1]], r[2]) for r in self.redo_stack],
            self.next_step_number
        )

    def get_rendered_pixmap(self) -> QPixmap:
        """Bakes all vector layers onto the base pixmap."""
        result = QPixmap(self.base_pixmap)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        for item in self.items:
            item.draw(painter)
        painter.end()
        return result

    def _push_undo(self):
        # Save snapshot
        snapshot = (QPixmap(self.base_pixmap), [self._clone_item(i) for i in self.items], self.next_step_number)
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > 30:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.can_undo_changed.emit(len(self.undo_stack) > 1)
        self.can_redo_changed.emit(False)
        self.content_modified.emit()

    def _clone_item(self, item: CanvasItem) -> CanvasItem:
        cloned = CanvasItem(item.tool_type, QColor(item.color), item.line_width, item.fill, QColor(item.fill_color))
        cloned.points = [QPointF(p.x(), p.y()) for p in item.points]
        cloned.text = item.text
        cloned.font_size = item.font_size
        cloned.step_number = item.step_number
        return cloned

    def undo(self):
        if len(self.undo_stack) > 1:
            current = self.undo_stack.pop()
            self.redo_stack.append((QPixmap(self.base_pixmap), [self._clone_item(i) for i in self.items], self.next_step_number))
            prev = self.undo_stack[-1]
            self.base_pixmap = QPixmap(prev[0])
            self.items = [self._clone_item(i) for i in prev[1]]
            self.next_step_number = prev[2]
            self.update()
            self.can_undo_changed.emit(len(self.undo_stack) > 1)
            self.can_redo_changed.emit(len(self.redo_stack) > 0)
            self.content_modified.emit()

    def redo(self):
        if self.redo_stack:
            next_state = self.redo_stack.pop()
            self.undo_stack.append(next_state)
            self.base_pixmap = QPixmap(next_state[0])
            self.items = [self._clone_item(i) for i in next_state[1]]
            self.next_step_number = next_state[2]
            self.update()
            self.can_undo_changed.emit(len(self.undo_stack) > 1)
            self.can_redo_changed.emit(len(self.redo_stack) > 0)
            self.content_modified.emit()

    # -------------------------------------------------------------
    # Tool Management & Cursors
    # -------------------------------------------------------------
    @property
    def current_tool(self) -> str:
        return self._current_tool

    @current_tool.setter
    def current_tool(self, tool_type: str):
        self._current_tool = tool_type
        if tool_type != ToolType.HAND and not self.is_space_held:
            self.is_panning = False
        self._update_cursor_for_tool()
        self.update()

    def set_tool(self, tool_type: str):
        self.current_tool = tool_type

    def screen_to_canvas(self, screen_pos: QPoint) -> QPointF:
        x = (screen_pos.x() - self.pan_offset.x()) / self.zoom_factor
        y = (screen_pos.y() - self.pan_offset.y()) / self.zoom_factor
        return QPointF(x, y)

    def canvas_to_screen(self, canvas_pt: QPointF) -> QPoint:
        x = int(canvas_pt.x() * self.zoom_factor + self.pan_offset.x())
        y = int(canvas_pt.y() * self.zoom_factor + self.pan_offset.y())
        return QPoint(x, y)

    def _update_cursor_for_tool(self):
        if self.is_space_held or self._current_tool == ToolType.HAND:
            if self.is_panning:
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif self._current_tool == ToolType.SELECT:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif self._current_tool == ToolType.TEXT:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        elif self._current_tool == ToolType.CROP:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            # Drawing tools (RECT, ROUND_RECT, CIRCLE, ARROW, LINE, PEN, HIGHLIGHTER, STEP_BADGE, BLUR, PIXELATE)
            self.setCursor(Qt.CursorShape.CrossCursor)

    # -------------------------------------------------------------
    # Keyboard Navigation (Figma Spacebar, Shortcuts)
    # -------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.is_space_held = True
            if not self.is_panning:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return

        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        # Figma Zoom Shortcuts
        if ctrl and event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom_in()
            event.accept()
            return
        elif ctrl and event.key() == Qt.Key.Key_Minus:
            self.zoom_out()
            event.accept()
            return
        elif ctrl and event.key() == Qt.Key.Key_0:
            self.zoom_100()
            event.accept()
            return
        elif (ctrl and event.key() == Qt.Key.Key_1) or (shift and event.key() == Qt.Key.Key_1):
            self.zoom_fit()
            event.accept()
            return

        # Tool Switching Shortcuts
        if not ctrl and not shift:
            if event.key() == Qt.Key.Key_H:
                self.tool_change_requested.emit(ToolType.HAND)
                return
            elif event.key() == Qt.Key.Key_V:
                self.tool_change_requested.emit(ToolType.SELECT)
                return
            elif event.key() == Qt.Key.Key_A:
                self.tool_change_requested.emit(ToolType.ARROW)
                return
            elif event.key() == Qt.Key.Key_R:
                self.tool_change_requested.emit(ToolType.RECT)
                return
            elif event.key() == Qt.Key.Key_T:
                self.tool_change_requested.emit(ToolType.TEXT)
                return
            elif event.key() == Qt.Key.Key_Right:
                top_win = self.window()
                if hasattr(top_win, '_action_next_image'):
                    top_win._action_next_image()
                    event.accept()
                    return
            elif event.key() == Qt.Key.Key_Left:
                top_win = self.window()
                if hasattr(top_win, '_action_prev_image'):
                    top_win._action_prev_image()
                    event.accept()
                    return

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.is_space_held = False
            if not self.is_panning:
                self._update_cursor_for_tool()
            event.accept()
            return
        super().keyReleaseEvent(event)

    # -------------------------------------------------------------
    # Mouse Events (Pan & Draw)
    # -------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent):
        # 1. Panning Trigger (Spacebar + Left Click, Middle Click, Hand Tool, Alt + Click, or Right Click drag)
        should_pan = (
            event.button() == Qt.MouseButton.MiddleButton or
            self.is_space_held or
            self.current_tool == ToolType.HAND or
            (event.button() == Qt.MouseButton.LeftButton and (event.modifiers() & Qt.KeyboardModifier.AltModifier)) or
            event.button() == Qt.MouseButton.RightButton
        )

        if should_pan:
            self.is_panning = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            canvas_pos = self.screen_to_canvas(event.pos())

            if self.current_tool == ToolType.CROP:
                self.is_cropping = True
                self.crop_rect = QRect(int(canvas_pos.x()), int(canvas_pos.y()), 0, 0)
                self.update()
                return

            if self.current_tool in (ToolType.BLUR, ToolType.PIXELATE):
                self.current_item = CanvasItem(self.current_tool, self.stroke_color, self.line_width)
                self.current_item.points = [canvas_pos, canvas_pos]
                self.update()
                return

            if self.current_tool == ToolType.STEP_BADGE:
                item = CanvasItem(ToolType.STEP_BADGE, self.stroke_color, self.line_width)
                item.points = [canvas_pos]
                item.step_number = self.next_step_number
                self.next_step_number += 1
                self.items.append(item)
                self._push_undo()
                self.update()
                return

            if self.current_tool == ToolType.TEXT:
                text, ok = QInputDialog.getText(self, "Add Text Annotation", "Enter text:")
                if ok and text.strip():
                    item = CanvasItem(ToolType.TEXT, self.stroke_color, self.line_width)
                    item.points = [canvas_pos]
                    item.text = text.strip()
                    item.font_size = self.font_size
                    self.items.append(item)
                    self._push_undo()
                    self.update()
                return

            # Shape / Arrow / Pen / Highlighter tools
            if self.current_tool not in (ToolType.SELECT, ToolType.HAND):
                self.current_item = CanvasItem(
                    self.current_tool, 
                    self.stroke_color, 
                    self.line_width, 
                    self.fill_enabled, 
                    self.fill_color
                )
                self.current_item.points = [canvas_pos]
                self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_panning:
            delta = event.pos() - self.last_pan_pos
            self.last_pan_pos = event.pos()
            self.pan_offset += delta
            self.update()
            return

        canvas_pos = self.screen_to_canvas(event.pos())
        self.status_updated.emit(f"Pos: ({int(canvas_pos.x())}, {int(canvas_pos.y())}) px | Size: {self.base_pixmap.width()} × {self.base_pixmap.height()} px | Zoom: {int(self.zoom_factor * 100)}%")

        if self.is_cropping and self.crop_rect:
            start_x = self.crop_rect.x()
            start_y = self.crop_rect.y()
            self.crop_rect = QRect(QPoint(start_x, start_y), QPoint(int(canvas_pos.x()), int(canvas_pos.y()))).normalized()
            self.update()
            return

        if self.current_item:
            if self.current_item.tool_type in (ToolType.PEN, ToolType.HIGHLIGHTER):
                self.current_item.points.append(canvas_pos)
            else:
                if len(self.current_item.points) == 1:
                    self.current_item.points.append(canvas_pos)
                else:
                    self.current_item.points[1] = canvas_pos
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.is_panning:
            self.is_panning = False
            self._update_cursor_for_tool()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_cropping and self.crop_rect:
                self.is_cropping = False
                self.update()
                return

            if self.current_item:
                # Handle Blur / Pixelate directly on base pixmap
                if self.current_item.tool_type in (ToolType.BLUR, ToolType.PIXELATE) and len(self.current_item.points) >= 2:
                    r = QRectF(self.current_item.points[0], self.current_item.points[1]).normalized().toRect()
                    if r.width() > 3 and r.height() > 3:
                        baked = self.get_rendered_pixmap()
                        self.items.clear()
                        if self.current_item.tool_type == ToolType.BLUR:
                            self.base_pixmap = ImageEffects.apply_blur(baked, r, radius=10)
                        else:
                            self.base_pixmap = ImageEffects.apply_pixelate(baked, r, pixel_size=12)
                        self._push_undo()
                    self.current_item = None
                    self.update()
                    return

                if len(self.current_item.points) >= 2:
                    self.items.append(self.current_item)
                    self._push_undo()
                self.current_item = None
                self.update()

    def apply_crop(self):
        if self.crop_rect and not self.crop_rect.isEmpty():
            target = self.crop_rect.intersected(QRect(0, 0, self.base_pixmap.width(), self.base_pixmap.height()))
            if target.width() > 4 and target.height() > 4:
                rendered = self.get_rendered_pixmap()
                self.base_pixmap = rendered.copy(target)
                self.items.clear()
                self.crop_rect = None
                self.current_tool = ToolType.SELECT
                self._push_undo()
                self.update()

    def cancel_crop(self):
        self.crop_rect = None
        self.current_tool = ToolType.SELECT
        self.update()

    # -------------------------------------------------------------
    # Figma Wheel Interactions (Ctrl+Wheel Zoom, Shift+Wheel Pan Horizontal, Normal Pan)
    # -------------------------------------------------------------
    def wheelEvent(self, event: QWheelEvent):
        modifiers = event.modifiers()

        # 1. Figma Zooming (Ctrl + Mouse Wheel or Trackpad Pinch)
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta == 0:
                delta = event.angleDelta().x()
            if delta == 0:
                return

            mouse_pos = event.position().toPoint()
            canvas_before = self.screen_to_canvas(mouse_pos)

            zoom_step = 1.15 if delta > 0 else (1.0 / 1.15)
            new_zoom = max(0.05, min(32.0, self.zoom_factor * zoom_step))
            self.zoom_factor = new_zoom

            canvas_after = self.screen_to_canvas(mouse_pos)
            self.pan_offset += (self.canvas_to_screen(canvas_after) - self.canvas_to_screen(canvas_before))

            self.zoom_changed.emit(self.zoom_factor)
            self.update()
            event.accept()
            return

        # 2. Figma Horizontal Scrolling (Shift + Wheel - Geser Kanan Kiri)
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            delta_y = event.angleDelta().y()
            if delta_y != 0:
                self.pan_offset.setX(self.pan_offset.x() + delta_y)
                self.update()
                event.accept()
                return

        # 3. Normal 2-Axis Scrolling (Trackpad or Mouse Wheel Vertical)
        else:
            dx = event.angleDelta().x()
            dy = event.angleDelta().y()
            if dx != 0 or dy != 0:
                self.pan_offset += QPoint(dx, dy)
                self.update()
                event.accept()
                return

    # -------------------------------------------------------------
    # Zoom Helpers
    # -------------------------------------------------------------
    def zoom_in(self):
        center = QPoint(self.width() // 2, self.height() // 2)
        canvas_before = self.screen_to_canvas(center)
        self.zoom_factor = min(32.0, self.zoom_factor * 1.25)
        canvas_after = self.screen_to_canvas(center)
        self.pan_offset += (self.canvas_to_screen(canvas_after) - self.canvas_to_screen(canvas_before))
        self.zoom_changed.emit(self.zoom_factor)
        self.update()

    def zoom_out(self):
        center = QPoint(self.width() // 2, self.height() // 2)
        canvas_before = self.screen_to_canvas(center)
        self.zoom_factor = max(0.05, self.zoom_factor / 1.25)
        canvas_after = self.screen_to_canvas(center)
        self.pan_offset += (self.canvas_to_screen(canvas_after) - self.canvas_to_screen(canvas_before))
        self.zoom_changed.emit(self.zoom_factor)
        self.update()

    def set_zoom(self, zoom: float):
        center = QPoint(self.width() // 2, self.height() // 2)
        canvas_before = self.screen_to_canvas(center)
        self.zoom_factor = max(0.05, min(32.0, zoom))
        canvas_after = self.screen_to_canvas(center)
        self.pan_offset += (self.canvas_to_screen(canvas_after) - self.canvas_to_screen(canvas_before))
        self.zoom_changed.emit(self.zoom_factor)
        self.update()

    def zoom_fit(self):
        if self.base_pixmap.isNull():
            return
        w_ratio = (self.width() - 80) / self.base_pixmap.width()
        h_ratio = (self.height() - 80) / self.base_pixmap.height()
        fit_zoom = min(w_ratio, h_ratio, 1.0)
        self.zoom_factor = max(0.05, fit_zoom)
        self.pan_offset = QPoint(
            int((self.width() - self.base_pixmap.width() * self.zoom_factor) / 2),
            int((self.height() - self.base_pixmap.height() * self.zoom_factor) / 2)
        )
        self.zoom_changed.emit(self.zoom_factor)
        self.update()

    def zoom_100(self):
        self.zoom_factor = 1.0
        if not self.base_pixmap.isNull() and self.base_pixmap.width() <= self.width() - 80:
            cx = int((self.width() - self.base_pixmap.width()) / 2)
        else:
            cx = 40
        if not self.base_pixmap.isNull() and self.base_pixmap.height() <= self.height() - 80:
            cy = int((self.height() - self.base_pixmap.height()) / 2)
        else:
            cy = 40
        self.pan_offset = QPoint(cx, cy)
        self.zoom_changed.emit(self.zoom_factor)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if hasattr(QPainter.RenderHint, "TextAntialiasing"):
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        if hasattr(QPainter.RenderHint, "LosslessImageRendering") and abs(self.zoom_factor - 1.0) < 1e-4:
            painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering, True)

        # 1. Dark canvas background
        painter.fillRect(self.rect(), QColor("#1E2227"))

        # 2. Draw subtle grid pattern
        painter.setPen(QPen(QColor(255, 255, 255, 12), 1))
        grid_step = 25
        for x in range(0, self.width(), grid_step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), grid_step):
            painter.drawLine(0, y, self.width(), y)

        # 3. Apply Zoom & Pan Transform
        painter.save()
        painter.translate(self.pan_offset.x(), self.pan_offset.y())
        painter.scale(self.zoom_factor, self.zoom_factor)

        # Drop shadow behind canvas
        img_w = self.base_pixmap.width()
        img_h = self.base_pixmap.height()
        shadow_rect = QRectF(4, 4, img_w, img_h)
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 80))

        # Base Image
        painter.drawPixmap(0, 0, self.base_pixmap)

        # Thin crisp border around base image
        painter.setPen(QPen(QColor("#3B4048"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(0, 0, img_w, img_h))

        # 4. Draw Vector Items
        for item in self.items:
            item.draw(painter)

        # 5. Draw Currently Active Drawing Item
        if self.current_item:
            if self.current_item.tool_type in (ToolType.BLUR, ToolType.PIXELATE) and len(self.current_item.points) >= 2:
                r = QRectF(self.current_item.points[0], self.current_item.points[1]).normalized()
                painter.setPen(QPen(QColor("#00E5FF"), 1.5, Qt.PenStyle.DashLine))
                painter.setBrush(QBrush(QColor(0, 229, 255, 30)))
                painter.drawRect(r)
            else:
                self.current_item.draw(painter)

        # 6. Draw Crop Overlay if active
        if self.crop_rect and not self.crop_rect.isEmpty():
            r = self.crop_rect
            # Dim outside
            painter.fillRect(QRectF(0, 0, img_w, r.top()), QColor(0, 0, 0, 140))
            painter.fillRect(QRectF(0, r.bottom(), img_w, img_h - r.bottom()), QColor(0, 0, 0, 140))
            painter.fillRect(QRectF(0, r.top(), r.left(), r.height()), QColor(0, 0, 0, 140))
            painter.fillRect(QRectF(r.right(), r.top(), img_w - r.right(), r.height()), QColor(0, 0, 0, 140))

            # Crop box border
            painter.setPen(QPen(QColor("#00E5FF"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(r)

        painter.restore()
        painter.end()
