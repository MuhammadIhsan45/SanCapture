import sys
from pathlib import Path
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QBrush, 
    QFont, QPainterPath, QPolygonF
)
from PyQt6.QtCore import QPointF, QRectF, Qt

def _get_asset_path(filename: str) -> Path:
    if getattr(sys, 'frozen', False):
        base = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base / "assets" / filename

class IconFactory:
    _cache = {}

    @classmethod
    def get_icon(cls, name: str, size: int = 24, color: str = None) -> QIcon:
        key = f"{name}_{size}_{color}"
        if key in cls._cache:
            return cls._cache[key]

        if name == "app_icon":
            png_file = _get_asset_path("app_icon.png")
            if png_file.exists():
                orig = QPixmap(str(png_file))
                if not orig.isNull():
                    scaled = orig.scaled(
                        size, size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    icon = QIcon(scaled)
                    cls._cache[key] = icon
                    return icon

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        method = getattr(cls, f"_draw_{name}", None)
        if method:
            method(painter, size, color)
        else:
            cls._draw_default(painter, size, color)

        painter.end()

        icon = QIcon(pixmap)
        cls._cache[key] = icon
        return icon

    @classmethod
    def get_pixmap(cls, name: str, size: int = 24, color: str = None) -> QPixmap:
        icon = cls.get_icon(name, size, color)
        return icon.pixmap(size, size)

    # -------------------------------------------------------------
    # Capture Toolbar Icons
    # -------------------------------------------------------------
    @classmethod
    def _draw_app_icon(cls, p: QPainter, s: int, c: str):
        # High-def vector fallback for SanCapture (Cobalt Squircle + Cyan Reticle + Lens)
        # 1. Base Squircle
        p.setPen(QPen(QColor("#3B82F6"), max(1.0, s * 0.05)))
        p.setBrush(QBrush(QColor("#0F172A")))
        p.drawRoundedRect(QRectF(1, 1, s - 2, s - 2), s * 0.22, s * 0.22)

        # 2. Reticle Corners (Electric Cyan)
        p.setPen(QPen(QColor("#00D2FF"), max(1.5, s * 0.08)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        inset = s * 0.22
        rlen = s * 0.16
        # TL
        p.drawLine(QPointF(inset, inset), QPointF(inset + rlen, inset))
        p.drawLine(QPointF(inset, inset), QPointF(inset, inset + rlen))
        # TR
        p.drawLine(QPointF(s - inset, inset), QPointF(s - inset - rlen, inset))
        p.drawLine(QPointF(s - inset, inset), QPointF(s - inset, inset + rlen))
        # BL
        p.drawLine(QPointF(inset, s - inset), QPointF(inset + rlen, s - inset))
        p.drawLine(QPointF(inset, s - inset), QPointF(inset, s - inset - rlen))
        # BR
        p.drawLine(QPointF(s - inset, s - inset), QPointF(s - inset - rlen, s - inset))
        p.drawLine(QPointF(s - inset, s - inset), QPointF(s - inset, s - inset - rlen))

        # 3. Center Shutter Lens
        cx, cy = s / 2.0, s / 2.0
        p.setPen(QPen(QColor("#2563EB"), max(1.0, s * 0.06)))
        p.setBrush(QBrush(QColor("#1E293B")))
        p.drawEllipse(QPointF(cx, cy), s * 0.22, s * 0.22)

        # Inner Lens Glow & Center Target Dot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#00E5FF")))
        p.drawEllipse(QPointF(cx, cy), s * 0.09, s * 0.09)
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(QPointF(cx, cy), s * 0.04, s * 0.04)

    @classmethod
    def _draw_capture_active_win(cls, p: QPainter, s: int, c: str):
        # Window frame
        p.setPen(QPen(QColor("#3B4048"), 1))
        p.setBrush(QBrush(QColor("#21252B")))
        p.drawRect(QRectF(3, 4, s - 6, s - 8))
        # Active blue header
        p.setBrush(QBrush(QColor("#0288D1")))
        p.drawRect(QRectF(3, 4, s - 6, 5))
        # Red highlight border
        p.setPen(QPen(QColor("#E53935"), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(2, 3, s - 4, s - 6))

    @classmethod
    def _draw_capture_win_object(cls, p: QPainter, s: int, c: str):
        # Outer window
        p.setPen(QPen(QColor("#ABB2BF"), 1))
        p.setBrush(QBrush(QColor("#282C34")))
        p.drawRect(QRectF(2, 3, s - 4, s - 6))
        # Inner child control highlighted in red
        p.setPen(QPen(QColor("#E53935"), 1.5))
        p.setBrush(QBrush(QColor(229, 57, 53, 60)))
        p.drawRect(QRectF(5, 7, s - 10, s - 14))

    @classmethod
    def _draw_capture_rect(cls, p: QPainter, s: int, c: str):
        # Dashed / sharp rectangular region with crosshair
        p.setPen(QPen(QColor("#E53935"), 1.5, Qt.PenStyle.DashLine))
        p.setBrush(QBrush(QColor(229, 57, 53, 40)))
        p.drawRect(QRectF(4, 4, s - 8, s - 8))
        # Corner markers
        p.setPen(QPen(QColor("#00E5FF"), 2))
        # Top-left corner
        p.drawLine(QPointF(2, 5), QPointF(5, 5))
        p.drawLine(QPointF(5, 2), QPointF(5, 5))
        # Bottom-right corner
        p.drawLine(QPointF(s - 5, s - 2), QPointF(s - 5, s - 5))
        p.drawLine(QPointF(s - 2, s - 5), QPointF(s - 5, s - 5))

    @classmethod
    def _draw_capture_freehand(cls, p: QPainter, s: int, c: str):
        p.setPen(QPen(QColor("#FF9800"), 1.8))
        path = QPainterPath()
        path.moveTo(s * 0.25, s * 0.75)
        path.cubicTo(s * 0.1, s * 0.2, s * 0.8, s * 0.1, s * 0.75, s * 0.5)
        path.cubicTo(s * 0.7, s * 0.85, s * 0.4, s * 0.9, s * 0.25, s * 0.75)
        p.setBrush(QBrush(QColor(255, 152, 0, 40)))
        p.drawPath(path)

    @classmethod
    def _draw_capture_fullscreen(cls, p: QPainter, s: int, c: str):
        # Monitor outline
        p.setPen(QPen(QColor("#ECEFF4"), 1.5))
        p.setBrush(QBrush(QColor("#1E2227")))
        p.drawRoundedRect(QRectF(3, 3, s - 6, s - 9), 2, 2)
        # Stand
        p.drawLine(QPointF(s / 2, s - 6), QPointF(s / 2, s - 3))
        p.drawLine(QPointF(s * 0.35, s - 3), QPointF(s * 0.65, s - 3))
        # 4 outward expansion arrows
        p.setPen(QPen(QColor("#0288D1"), 1.2))
        p.drawLine(QPointF(5, 5), QPointF(9, 9))
        p.drawLine(QPointF(s - 5, 5), QPointF(s - 9, 9))
        p.drawLine(QPointF(5, s - 8), QPointF(9, s - 12))
        p.drawLine(QPointF(s - 5, s - 8), QPointF(s - 9, s - 12))

    @classmethod
    def _draw_color_picker(cls, p: QPainter, s: int, c: str):
        # Pipette dropper
        p.setPen(QPen(QColor("#ECEFF4"), 1.5))
        p.setBrush(QBrush(QColor("#F57C00")))
        path = QPainterPath()
        path.moveTo(s * 0.75, s * 0.15)
        path.lineTo(s * 0.85, s * 0.25)
        path.lineTo(s * 0.45, s * 0.65)
        path.lineTo(s * 0.2, s * 0.75)
        path.lineTo(s * 0.25, s * 0.5)
        path.closeSubpath()
        p.drawPath(path)
        # Pipette tip drop
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#00E5FF")))
        p.drawEllipse(QPointF(s * 0.18, s * 0.82), 2, 2)

    @classmethod
    def _draw_open_editor(cls, p: QPainter, s: int, c: str):
        # Clean editor studio canvas with pencil & color palette badge
        p.setPen(QPen(QColor("#3B4048"), 1))
        p.setBrush(QBrush(QColor("#21252B")))
        p.drawRoundedRect(QRectF(3, 3, s - 6, s - 6), 2, 2)
        # Top titlebar header of mini editor
        p.setBrush(QBrush(QColor("#0288D1")))
        p.drawRect(QRectF(3, 3, s - 6, 4))
        # Inner canvas area
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#282C34")))
        p.drawRect(QRectF(5, 8, s - 10, s - 12))
        # Angled yellow pencil / stylus
        p.setPen(QPen(QColor("#FFEE58"), 2.2))
        p.drawLine(QPointF(6, s - 7), QPointF(s - 7, 10))
        # Stylus tip in crimson red
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#D32F2F")))
        p.drawEllipse(QPointF(s - 7, 10), 2, 2)

    @classmethod
    def _draw_open_image(cls, p: QPainter, s: int, c: str):
        # Yellow folder
        p.setPen(QPen(QColor("#F57F17"), 1))
        p.setBrush(QBrush(QColor("#FBC02D")))
        path = QPainterPath()
        path.moveTo(3, 6)
        path.lineTo(9, 6)
        path.lineTo(12, 8)
        path.lineTo(s - 3, 8)
        path.lineTo(s - 3, s - 5)
        path.lineTo(3, s - 5)
        path.closeSubpath()
        p.drawPath(path)

    @classmethod
    def _draw_settings(cls, p: QPainter, s: int, c: str):
        # Mechanical gear
        p.setPen(QPen(QColor("#D8DEE9"), 1.5))
        p.setBrush(QBrush(QColor("#4C5362")))
        p.drawEllipse(QPointF(s / 2, s / 2), s * 0.28, s * 0.28)
        p.setBrush(QBrush(QColor("#21252B")))
        p.drawEllipse(QPointF(s / 2, s / 2), s * 0.12, s * 0.12)
        # Teeth
        for angle in range(0, 360, 45):
            p.save()
            p.translate(s / 2, s / 2)
            p.rotate(angle)
            p.setPen(QPen(QColor("#D8DEE9"), 2))
            p.drawLine(QPointF(0, -s * 0.38), QPointF(0, -s * 0.28))
            p.restore()

    # -------------------------------------------------------------
    # Editor Annotation Icons
    # -------------------------------------------------------------
    @classmethod
    def _draw_tool_select(cls, p: QPainter, s: int, c: str):
        # Crisp cursor arrow (Select tool)
        p.setPen(QPen(QColor("#FFFFFF"), 1.2))
        p.setBrush(QBrush(QColor("#ECEFF4")))
        poly = QPolygonF([
            QPointF(4, 3),
            QPointF(4, s - 5),
            QPointF(s * 0.38, s * 0.58),
            QPointF(s * 0.62, s - 3),
            QPointF(s * 0.74, s * 0.78),
            QPointF(s * 0.48, s * 0.44),
            QPointF(s * 0.68, s * 0.44),
        ])
        p.drawPolygon(poly)

    @classmethod
    def _draw_tool_hand(cls, p: QPainter, s: int, c: str):
        # Open hand / Pan canvas tool ✋
        p.setPen(QPen(QColor("#FFFFFF"), 1.2))
        p.setBrush(QBrush(QColor("#61AFEF")))
        path = QPainterPath()
        # Palm & fingers
        path.moveTo(s * 0.28, s * 0.85)
        path.lineTo(s * 0.18, s * 0.58) # Thumb base
        path.lineTo(s * 0.26, s * 0.38) # Thumb tip
        path.lineTo(s * 0.36, s * 0.48)
        path.lineTo(s * 0.40, s * 0.18) # Index finger
        path.lineTo(s * 0.48, s * 0.18)
        path.lineTo(s * 0.51, s * 0.12) # Middle finger
        path.lineTo(s * 0.59, s * 0.12)
        path.lineTo(s * 0.62, s * 0.18) # Ring finger
        path.lineTo(s * 0.70, s * 0.18)
        path.lineTo(s * 0.73, s * 0.32) # Pinky finger
        path.lineTo(s * 0.80, s * 0.32)
        path.lineTo(s * 0.82, s * 0.68)
        path.lineTo(s * 0.70, s * 0.88)
        path.closeSubpath()
        p.drawPath(path)

    @classmethod
    def _draw_tool_arrow(cls, p: QPainter, s: int, c: str):
        # Directional annotation arrow
        p.setPen(QPen(QColor(c or "#E06C75"), 2.2))
        p.drawLine(QPointF(4, s - 5), QPointF(s - 6, 6))
        poly = QPolygonF([
            QPointF(s - 3, 3),
            QPointF(s - 10, 4),
            QPointF(s - 4, 10),
        ])
        p.setBrush(QBrush(QColor(c or "#E06C75")))
        p.drawPolygon(poly)

    @classmethod
    def _draw_tool_pen(cls, p: QPainter, s: int, c: str):
        # Stylus / Freehand drawing pen ✏️
        p.setPen(QPen(QColor("#FFFFFF"), 1))
        p.setBrush(QBrush(QColor("#98C379"))) # Crisp green pen body
        path = QPainterPath()
        path.moveTo(s * 0.62, 3)
        path.lineTo(s - 3, s * 0.38)
        path.lineTo(s * 0.48, s - 4)
        path.lineTo(s * 0.22, s * 0.72)
        path.closeSubpath()
        p.drawPath(path)
        
        # Golden sharp nib
        nib = QPolygonF([
            QPointF(s * 0.22, s * 0.72),
            QPointF(s * 0.48, s - 4),
            QPointF(3, s - 3),
        ])
        p.setPen(QPen(QColor("#D19A66"), 1))
        p.setBrush(QBrush(QColor("#E5C07B")))
        p.drawPolygon(nib)
        
        # Pen tip point
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(QPointF(3, s - 3), 1.2, 1.2)

    @classmethod
    def _draw_tool_highlighter(cls, p: QPainter, s: int, c: str):
        # Slanted fluorescent highlighter marker
        p.setPen(QPen(QColor("#D19A66"), 1.2))
        p.setBrush(QBrush(QColor("#E5C07B")))
        path = QPainterPath()
        path.moveTo(s * 0.7, 4)
        path.lineTo(s - 4, s * 0.3)
        path.lineTo(s * 0.45, s - 4)
        path.lineTo(4, s * 0.75)
        path.closeSubpath()
        p.drawPath(path)
        # Chisel tip glow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#FFE066")))
        p.drawRect(QRectF(3, s - 8, 5, 5))

    @classmethod
    def _draw_tool_highlighter_rect(cls, p: QPainter, s: int, c: str):
        # Yellow highlighted rectangular block / text marker box
        p.setPen(QPen(QColor("#FFE066"), 1.8))
        p.setBrush(QBrush(QColor(255, 224, 102, 120)))
        p.drawRoundedRect(QRectF(3, 4, s - 6, s - 8), 2, 2)
        # Internal text highlight strip
        p.setPen(QPen(QColor("#FFFFFF"), 1.8))
        p.drawLine(QPointF(6, s / 2), QPointF(s - 6, s / 2))

    @classmethod
    def _draw_tool_step_badge(cls, p: QPainter, s: int, c: str):
        # Red circular badge with "1" inside
        p.setPen(QPen(QColor("#FFFFFF"), 1.2))
        p.setBrush(QBrush(QColor(c or "#E06C75")))
        p.drawEllipse(QPointF(s / 2, s / 2), s * 0.42, s * 0.42)
        p.setPen(QColor("#FFFFFF"))
        f = QFont("Segoe UI", int(s * 0.48), QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(QRectF(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, "1")

    @classmethod
    def _draw_tool_step(cls, p: QPainter, s: int, c: str):
        cls._draw_tool_step_badge(p, s, c)

    @classmethod
    def _draw_tool_rect(cls, p: QPainter, s: int, c: str):
        p.setPen(QPen(QColor(c or "#E06C75"), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(4, 4, s - 8, s - 8))

    @classmethod
    def _draw_tool_round_rect(cls, p: QPainter, s: int, c: str):
        p.setPen(QPen(QColor(c or "#61AFEF"), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(4, 4, s - 8, s - 8), 4, 4)

    @classmethod
    def _draw_tool_circle(cls, p: QPainter, s: int, c: str):
        p.setPen(QPen(QColor(c or "#E06C75"), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(4, 4, s - 8, s - 8))

    @classmethod
    def _draw_tool_line(cls, p: QPainter, s: int, c: str):
        p.setPen(QPen(QColor(c or "#E06C75"), 2.5))
        p.drawLine(QPointF(4, s - 4), QPointF(s - 4, 4))

    @classmethod
    def _draw_tool_text(cls, p: QPainter, s: int, c: str):
        p.setPen(QColor(c or "#ECEFF4"))
        f = QFont("Segoe UI", int(s * 0.65), QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(QRectF(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, "T")

    @classmethod
    def _draw_tool_blur(cls, p: QPainter, s: int, c: str):
        # Water drop / soft blur lens icon 💧
        p.setPen(QPen(QColor("#61AFEF"), 1.5))
        p.setBrush(QBrush(QColor(97, 175, 239, 130)))
        path = QPainterPath()
        path.moveTo(s / 2, 3)
        path.cubicTo(s * 0.85, s * 0.55, s * 0.8, s * 0.85, s / 2, s - 3)
        path.cubicTo(s * 0.2, s * 0.85, s * 0.15, s * 0.55, s / 2, 3)
        p.drawPath(path)
        # Shiny glass reflection
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(QPointF(s * 0.42, s * 0.45), 1.2, 2.2)

    @classmethod
    def _draw_tool_pixelate(cls, p: QPainter, s: int, c: str):
        # 4x4 High-contrast mosaic / censor pixel grid
        cols = [
            [QColor("#21252B"), QColor("#8892B0"), QColor("#3B4048"), QColor("#61AFEF")],
            [QColor("#ABB2BF"), QColor("#21252B"), QColor("#E06C75"), QColor("#3B4048")],
            [QColor("#3B4048"), QColor("#98C379"), QColor("#21252B"), QColor("#8892B0")],
            [QColor("#61AFEF"), QColor("#3B4048"), QColor("#ABB2BF"), QColor("#21252B")]
        ]
        cell = (s - 6) / 4
        for r in range(4):
            for col in range(4):
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(cols[r][col]))
                p.drawRect(QRectF(3 + col * cell, 3 + r * cell, cell + 0.4, cell + 0.4))
        p.setPen(QPen(QColor("#ABB2BF"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(3, 3, s - 6, s - 6))

    @classmethod
    def _draw_tool_crop(cls, p: QPainter, s: int, c: str):
        p.setPen(QPen(QColor("#ECEFF4"), 2))
        # Top-left and bottom-right crop marks
        p.drawLine(QPointF(3, 7), QPointF(s - 7, 7))
        p.drawLine(QPointF(7, 3), QPointF(7, s - 7))
        p.drawLine(QPointF(s - 3, s - 7), QPointF(7, s - 7))
        p.drawLine(QPointF(s - 7, s - 3), QPointF(s - 7, 7))

    @classmethod
    def _draw_undo(cls, p: QPainter, s: int, c: str):
        p.setPen(QPen(QColor("#ECEFF4"), 2))
        path = QPainterPath()
        path.moveTo(s - 6, s * 0.7)
        path.cubicTo(s - 6, s * 0.35, s * 0.4, s * 0.35, 6, s * 0.45)
        p.drawPath(path)
        # Arrow tip
        poly = QPolygonF([QPointF(4, s * 0.45), QPointF(9, s * 0.25), QPointF(9, s * 0.65)])
        p.setBrush(QBrush(QColor("#ECEFF4")))
        p.drawPolygon(poly)

    @classmethod
    def _draw_redo(cls, p: QPainter, s: int, c: str):
        p.setPen(QPen(QColor("#ECEFF4"), 2))
        path = QPainterPath()
        path.moveTo(6, s * 0.7)
        path.cubicTo(6, s * 0.35, s * 0.6, s * 0.35, s - 6, s * 0.45)
        p.drawPath(path)
        # Arrow tip
        poly = QPolygonF([QPointF(s - 4, s * 0.45), QPointF(s - 9, s * 0.25), QPointF(s - 9, s * 0.65)])
        p.setBrush(QBrush(QColor("#ECEFF4")))
        p.drawPolygon(poly)

    @classmethod
    def _draw_save(cls, p: QPainter, s: int, c: str):
        # 3.5" Diskette
        p.setPen(QPen(QColor("#0288D1"), 1))
        p.setBrush(QBrush(QColor("#0288D1")))
        path = QPainterPath()
        path.moveTo(3, 3)
        path.lineTo(s - 6, 3)
        path.lineTo(s - 3, 6)
        path.lineTo(s - 3, s - 3)
        path.lineTo(3, s - 3)
        path.closeSubpath()
        p.drawPath(path)
        # Top metal slider
        p.setBrush(QBrush(QColor("#ECEFF4")))
        p.drawRect(QRectF(s * 0.3, 3, s * 0.4, s * 0.32))
        # Label area
        p.drawRect(QRectF(s * 0.25, s * 0.55, s * 0.5, s * 0.35))

    @classmethod
    def _draw_copy(cls, p: QPainter, s: int, c: str):
        p.setPen(QPen(QColor("#ECEFF4"), 1.5))
        p.setBrush(QBrush(QColor("#282C34")))
        # Back sheet
        p.drawRect(QRectF(7, 3, s - 10, s - 10))
        # Front sheet
        p.drawRect(QRectF(3, 7, s - 10, s - 10))

    @classmethod
    def _draw_print(cls, p: QPainter, s: int, c: str):
        p.setPen(QPen(QColor("#ECEFF4"), 1.2))
        p.setBrush(QBrush(QColor("#3B4048")))
        # Base
        p.drawRoundedRect(QRectF(3, 8, s - 6, 9), 2, 2)
        # Top paper
        p.setBrush(QBrush(QColor("#ECEFF4")))
        p.drawRect(QRectF(6, 3, s - 12, 5))
        # Feed slot paper
        p.drawRect(QRectF(6, 12, s - 12, 6))

    @classmethod
    def _draw_trash(cls, p: QPainter, s: int, c: str):
        # Crisp trash can icon
        col = QColor(c or "#E06C75")
        p.setPen(QPen(col, 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Lid handle
        p.drawLine(QPointF(s * 0.38, 3), QPointF(s * 0.62, 3))
        # Lid bar
        p.drawLine(QPointF(3, 5), QPointF(s - 3, 5))
        # Body
        body = QPainterPath()
        body.moveTo(5, 6)
        body.lineTo(6, s - 3)
        body.lineTo(s - 6, s - 3)
        body.lineTo(s - 5, 6)
        p.drawPath(body)
        # Vertical slots
        p.drawLine(QPointF(s * 0.38, 8), QPointF(s * 0.38, s - 6))
        p.drawLine(QPointF(s * 0.62, 8), QPointF(s * 0.62, s - 6))

    @classmethod
    def _draw_delete(cls, p: QPainter, s: int, c: str):
        cls._draw_trash(p, s, c)

    @classmethod
    def _draw_paste(cls, p: QPainter, s: int, c: str):
        # Crisp clipboard paste icon
        p.setPen(QPen(QColor(c or "#ECEFF4"), 1.2))
        p.setBrush(QBrush(QColor("#21252B")))
        # Clipboard board
        p.drawRoundedRect(QRectF(3, 4, s - 6, s - 6), 2, 2)
        # Top clip
        p.setBrush(QBrush(QColor("#61AFEF")))
        p.drawRoundedRect(QRectF(s * 0.32, 2, s * 0.36, 4), 1, 1)
        # Paper sheet inside
        p.setBrush(QBrush(QColor("#2C313A")))
        p.drawRect(QRectF(5, 7, s - 10, s - 11))
        # Text lines
        p.setPen(QPen(QColor("#ABB2BF"), 1))
        p.drawLine(QPointF(7, 10), QPointF(s - 7, 10))
        p.drawLine(QPointF(7, 13), QPointF(s - 7, 13))

    @classmethod
    def _draw_renumber(cls, p: QPainter, s: int, c: str):
        # List with number 1,2,3
        p.setPen(QColor(c or "#61AFEF"))
        f = QFont("Segoe UI", int(s * 0.38), QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(QRectF(2, 1, s * 0.45, s * 0.45), Qt.AlignmentFlag.AlignCenter, "1")
        p.drawText(QRectF(2, s * 0.48, s * 0.45, s * 0.45), Qt.AlignmentFlag.AlignCenter, "2")
        p.setPen(QPen(QColor(c or "#ECEFF4"), 1.8))
        p.drawLine(QPointF(s * 0.5, 5), QPointF(s - 3, 5))
        p.drawLine(QPointF(s * 0.5, s - 6), QPointF(s - 3, s - 6))

    @classmethod
    def _draw_gallery(cls, p: QPainter, s: int, c: str):
        # Photo card stack / gallery icon
        p.setPen(QPen(QColor("#4B5263"), 1.2))
        p.setBrush(QBrush(QColor("#21252B")))
        # Back photo frame
        p.drawRoundedRect(QRectF(6, 2, s - 8, s - 8), 2, 2)
        # Front photo frame
        p.setPen(QPen(QColor(c or "#61AFEF"), 1.2))
        p.setBrush(QBrush(QColor("#282C34")))
        p.drawRoundedRect(QRectF(2, 6, s - 8, s - 8), 2, 2)
        # Inner landscape (sun & mountain)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#E5C07B")))
        p.drawEllipse(QPointF(6, 10), 1.5, 1.5)
        # Mountain
        p.setBrush(QBrush(QColor("#98C379")))
        mount = QPolygonF([
            QPointF(3, s - 4),
            QPointF(8, 12),
            QPointF(12, s - 4),
        ])
        p.drawPolygon(mount)

    @classmethod
    def _draw_sharpen(cls, p: QPainter, s: int, c: str):
        # Sparkle / Diamond focus crispness icon
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(c or "#00E5FF")))
        # Center large diamond sparkle
        cx, cy = s / 2.0, s / 2.0
        r = s * 0.38
        poly = QPolygonF([
            QPointF(cx, cy - r),
            QPointF(cx + r * 0.32, cy - r * 0.32),
            QPointF(cx + r, cy),
            QPointF(cx + r * 0.32, cy + r * 0.32),
            QPointF(cx, cy + r),
            QPointF(cx - r * 0.32, cy + r * 0.32),
            QPointF(cx - r, cy),
            QPointF(cx - r * 0.32, cy - r * 0.32),
        ])
        p.drawPolygon(poly)
        # Small corner sparkle
        p.setBrush(QBrush(QColor("#E5C07B")))
        sx, sy, sr = s * 0.78, s * 0.25, s * 0.18
        p.drawPolygon(QPolygonF([
            QPointF(sx, sy - sr),
            QPointF(sx + sr, sy),
            QPointF(sx, sy + sr),
            QPointF(sx - sr, sy),
        ]))

    @classmethod
    def _draw_default(cls, p: QPainter, s: int, c: str):
        p.setPen(QPen(QColor(c or "#ECEFF4"), 1.5))
        p.drawRect(QRectF(4, 4, s - 8, s - 8))
