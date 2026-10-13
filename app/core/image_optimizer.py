"""
Image Optimization & Smart Saving Engine for SanCapture.
Ensures maximum visual sharpness (especially for UI text, icons, and borders)
while minimizing file size through modern compression techniques (PNG L9, WebP, JPEG 4:4:4).
"""

import io
import os
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image, ImageEnhance, ImageFilter

from app.core.config import config

def format_file_size(size_bytes: int) -> str:
    """Formats byte count into a human-readable string (e.g. 142.5 KB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def qpixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    """Converts a PyQt6 QPixmap to a PIL Image accurately preserving full alpha channel."""
    qimg = pixmap.toImage()
    if qimg.format() != QImage.Format.Format_ARGB32_Premultiplied and qimg.format() != QImage.Format.Format_ARGB32:
        qimg = qimg.convertToFormat(QImage.Format.Format_ARGB32)
    
    ptr = qimg.bits()
    ptr.setsize(qimg.sizeInBytes())
    pil_img = Image.frombuffer('RGBA', (qimg.width(), qimg.height()), ptr, 'raw', 'BGRA', 0, 1)
    return pil_img

def pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    """Converts a PIL Image back to PyQt6 QPixmap."""
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    data = pil_img.tobytes("raw", "BGRA")
    qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_ARGB32)
    return QPixmap.fromImage(qimg)

class ImageOptimizer:
    """
    Centralized image optimizer and saver.
    Provides intelligent format-specific compression preserving razor-sharp text.
    """

    @classmethod
    def save_pixmap(
        cls,
        pixmap: QPixmap,
        file_path: str,
        format_name: Optional[str] = None,
        quality: Optional[int] = None,
        subsampling: Optional[int] = None,
        png_compression: Optional[int] = None,
        webp_lossless: Optional[bool] = None
    ) -> Tuple[bool, int, str]:
        """
        Saves a QPixmap to disk using optimized compression algorithms.
        Returns: (success: bool, file_size_bytes: int, message: str)
        """
        if pixmap.isNull() or pixmap.width() <= 0 or pixmap.height() <= 0:
            return False, 0, "Pixmap is empty or invalid."

        path_obj = Path(file_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        ext = path_obj.suffix.lower().lstrip(".")

        if not format_name:
            format_name = ext.upper() if ext else config.get("image_format", "PNG").upper()

        format_name = format_name.upper()
        if format_name in ("JPG", "JPEG"):
            target_format = "JPEG"
        elif format_name == "WEBP":
            target_format = "WEBP"
        elif format_name == "PDF":
            target_format = "PDF"
        elif format_name == "BMP":
            target_format = "BMP"
        else:
            target_format = "PNG"

        # Read config defaults if not explicitly passed
        if quality is None:
            quality = int(config.get("jpeg_quality", 90))
        if subsampling is None:
            subsampling = int(config.get("jpeg_subsampling", 0))  # 0 = 4:4:4 (no color blur)
        if png_compression is None:
            png_compression = int(config.get("png_compression_level", 9))
        if webp_lossless is None:
            webp_lossless = bool(config.get("webp_lossless", True))

        try:
            pil_img = qpixmap_to_pil(pixmap)

            if target_format == "PNG":
                # PNG: 100% Lossless, maximum zlib compression level
                # Optimization removes unnecessary chunks while keeping exact pixels
                pil_img.save(
                    str(path_obj),
                    format="PNG",
                    optimize=True,
                    compress_level=max(1, min(9, png_compression))
                )

            elif target_format == "WEBP":
                # WebP: Lossless mode provides pixel-exact sharpness at 30-50% smaller size than PNG
                # Lossy mode provides near-lossless sharpness with method=6 for high compression
                if webp_lossless:
                    pil_img.save(
                        str(path_obj),
                        format="WEBP",
                        lossless=True,
                        quality=quality,
                        method=6
                    )
                else:
                    # High-fidelity lossy WebP
                    if pil_img.mode == "RGBA":
                        if not cls._has_transparency(pil_img):
                            pil_img = pil_img.convert("RGB")
                    pil_img.save(
                        str(path_obj),
                        format="WEBP",
                        lossless=False,
                        quality=quality,
                        method=6
                    )

            elif target_format == "JPEG":
                # JPEG does not support alpha channel, composite onto white background
                if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
                    bg = Image.new("RGB", pil_img.size, (255, 255, 255))
                    bg.paste(pil_img, mask=pil_img.split()[-1])
                    rgb_img = bg
                else:
                    rgb_img = pil_img.convert("RGB")

                # Subsampling=0 (4:4:4) keeps red/colored text and sharp UI lines crisp without color bleeding
                rgb_img.save(
                    str(path_obj),
                    format="JPEG",
                    quality=max(30, min(100, quality)),
                    subsampling=subsampling,
                    optimize=True,
                    progressive=True
                )

            elif target_format == "PDF":
                if pil_img.mode == "RGBA":
                    bg = Image.new("RGB", pil_img.size, (255, 255, 255))
                    bg.paste(pil_img, mask=pil_img.split()[-1])
                    rgb_img = bg
                else:
                    rgb_img = pil_img.convert("RGB")
                rgb_img.save(str(path_obj), "PDF", resolution=150.0)

            elif target_format == "BMP":
                pil_img.save(str(path_obj), format="BMP")

            else:
                # Fallback to PNG
                pil_img.save(str(path_obj), format="PNG", optimize=True, compress_level=9)

            if path_obj.exists():
                file_size = path_obj.stat().st_size
                return True, file_size, f"Saved successfully ({format_file_size(file_size)})"
            else:
                return False, 0, "File not found after write."

        except Exception as e:
            # Fallback to standard Qt save
            try:
                success = pixmap.save(str(path_obj))
                if success and path_obj.exists():
                    file_size = path_obj.stat().st_size
                    return True, file_size, f"Saved (fallback) ({format_file_size(file_size)})"
                return False, 0, f"Save failed: {str(e)}"
            except Exception as e2:
                return False, 0, f"Error saving image: {str(e2)}"

    @staticmethod
    def _has_transparency(img: Image.Image) -> bool:
        """Checks if an RGBA image contains any actual transparent or semi-transparent pixels."""
        if img.mode != "RGBA":
            return False
        alpha = img.getchannel("A")
        min_val, max_val = alpha.getextrema()
        return min_val < 255

    @classmethod
    def enhance_sharpness(cls, pixmap: QPixmap, factor: float = 1.25) -> QPixmap:
        """
        Enhances edge crispness and text sharpness using smart unsharp mask and contrast tuning.
        Factor 1.0 = unchanged, 1.25 = subtle crisp boost, 1.5 = high sharpness.
        """
        if pixmap.isNull() or pixmap.width() <= 0 or pixmap.height() <= 0:
            return pixmap

        try:
            pil_img = qpixmap_to_pil(pixmap)
            
            # Subtle Unsharp Mask to enhance high-contrast text edges without noise
            sharpened = pil_img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=int(100 * factor), threshold=2))
            
            # Slight sharpness enhancer
            enhancer = ImageEnhance.Sharpness(sharpened)
            final_pil = enhancer.enhance(1.1)

            return pil_to_qpixmap(final_pil)
        except Exception:
            return pixmap
