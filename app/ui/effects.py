"""
Image Processing & Visual Effects for FastCapture.
Handles Drop Shadow, Borders, Rotate, Resize, Blur, and Pixelate.
"""

from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush, QTransform
from PyQt6.QtCore import Qt, QRect, QPoint
from PIL import Image, ImageFilter
import io

def qpixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    buffer = pixmap.toImage()
    ptr = buffer.bits()
    ptr.setsize(buffer.sizeInBytes())
    img = Image.frombuffer('RGBA', (buffer.width(), buffer.height()), ptr, 'raw', 'BGRA', 0, 1)
    return img

def pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    data = pil_img.tobytes("raw", "BGRA")
    qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_ARGB32)
    return QPixmap.fromImage(qimg)

class ImageEffects:
    @staticmethod
    def apply_pixelate(pixmap: QPixmap, rect: QRect, pixel_size: int = 12) -> QPixmap:
        """Applies pixelate redaction effect to the specified region."""
        target_rect = rect.intersected(QRect(0, 0, pixmap.width(), pixmap.height()))
        if target_rect.isEmpty() or target_rect.width() < 2 or target_rect.height() < 2:
            return pixmap

        crop = pixmap.copy(target_rect)
        # Downscale then upscale with NearestNeighbor
        down_w = max(1, target_rect.width() // pixel_size)
        down_h = max(1, target_rect.height() // pixel_size)
        
        downscaled = crop.scaled(down_w, down_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
        pixelated = downscaled.scaled(target_rect.width(), target_rect.height(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)

        result = QPixmap(pixmap)
        painter = QPainter(result)
        painter.drawPixmap(target_rect.topLeft(), pixelated)
        painter.end()
        return result

    @staticmethod
    def apply_blur(pixmap: QPixmap, rect: QRect, radius: int = 8) -> QPixmap:
        """Applies gaussian blur redaction effect to the specified region."""
        target_rect = rect.intersected(QRect(0, 0, pixmap.width(), pixmap.height()))
        if target_rect.isEmpty() or target_rect.width() < 2 or target_rect.height() < 2:
            return pixmap

        crop = pixmap.copy(target_rect)
        pil_crop = qpixmap_to_pil(crop)
        blurred_pil = pil_crop.filter(ImageFilter.GaussianBlur(radius))
        blurred_pixmap = pil_to_qpixmap(blurred_pil)

        result = QPixmap(pixmap)
        painter = QPainter(result)
        painter.drawPixmap(target_rect.topLeft(), blurred_pixmap)
        painter.end()
        return result

    @staticmethod
    def add_drop_shadow(pixmap: QPixmap, margin: int = 16, blur_radius: int = 12, shadow_opacity: int = 140) -> QPixmap:
        """Adds a professional FastStone-style drop shadow around the image."""
        w = pixmap.width()
        h = pixmap.height()
        new_w = w + margin * 2
        new_h = h + margin * 2

        # Create transparent canvas
        canvas = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        # Draw shadow rectangle
        shadow_box = Image.new("RGBA", (w, h), (0, 0, 0, shadow_opacity))
        canvas.paste(shadow_box, (margin + 3, margin + 4))
        # Blur shadow
        blurred_canvas = canvas.filter(ImageFilter.GaussianBlur(blur_radius / 2))
        
        # Paste original image on top
        orig_pil = qpixmap_to_pil(pixmap)
        blurred_canvas.paste(orig_pil, (margin, margin), orig_pil)

        return pil_to_qpixmap(blurred_canvas)

    @staticmethod
    def add_border(pixmap: QPixmap, border_width: int = 2, color: QColor = QColor("#D32F2F")) -> QPixmap:
        """Adds a solid crisp border around the image."""
        result = QPixmap(pixmap)
        painter = QPainter(result)
        pen = QPen(color, border_width)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Inset half border width to avoid clipping
        half = border_width / 2.0
        painter.drawRect(int(half), int(half), int(pixmap.width() - border_width), int(pixmap.height() - border_width))
        painter.end()
        return result

    @staticmethod
    def rotate(pixmap: QPixmap, degrees: int) -> QPixmap:
        transform = QTransform().rotate(degrees)
        return pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)

    @staticmethod
    def flip_horizontal(pixmap: QPixmap) -> QPixmap:
        transform = QTransform().scale(-1, 1)
        return pixmap.transformed(transform)

    @staticmethod
    def flip_vertical(pixmap: QPixmap) -> QPixmap:
        transform = QTransform().scale(1, -1)
        return pixmap.transformed(transform)

    @staticmethod
    def enhance_sharpness(pixmap: QPixmap, factor: float = 1.25) -> QPixmap:
        """Smart crispness and sharpness enhancer for clear UI text and edges."""
        from app.core.image_optimizer import ImageOptimizer
        return ImageOptimizer.enhance_sharpness(pixmap, factor=factor)
