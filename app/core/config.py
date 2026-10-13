import os
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".san_capture"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_SAVE_DIR = Path.home() / "Pictures" / "SAN_Capture"

class OutputDest:
    EDITOR = "editor"
    CLIPBOARD = "clipboard"
    FILE_SAVE = "file_save"
    AUTO_SAVE = "auto_save"
    PRINT = "print"

    CHOICES = [
        (EDITOR, "To Editor"),
        (CLIPBOARD, "To Clipboard"),
        (FILE_SAVE, "To File (Save As)"),
        (AUTO_SAVE, "To Auto-Save Folder"),
        (PRINT, "To Printer")
    ]

DEFAULT_CONFIG = {
    "output_dest": OutputDest.EDITOR,
    "save_dir": str(DEFAULT_SAVE_DIR),
    "image_format": "PNG",
    "quality_preset": "balanced",
    "jpeg_quality": 90,
    "jpeg_subsampling": 0,          # 0 = 4:4:4 Chroma Subsampling for crisp sharp text
    "png_compression_level": 9,     # 1-9 (9 = max lossless compression)
    "webp_lossless": True,          # 100% sharp text with 30-50% smaller size than PNG
    "webp_quality": 90,
    "optimize_image_size": True,
    "auto_enhance_sharpness": False,
    "filename_prefix": "",
    "next_capture_number": 1,
    "filename_pattern": "{n}",
    "play_sound": True,
    "include_cursor": False,
    "always_on_top": True,
    "minimize_to_tray": True,
    "magnifier_zoom": 8,
    "grid_color": "#4A90E2",
    "hotkeys": {
        "active_window": "Alt+W",
        "window_object": "Alt+O",
        "rectangular_region": "Alt+S",
        "freehand_region": "Alt+F",
        "full_screen": "Alt+A",
        "color_picker": "Alt+C"
    }
}

class AppConfig:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance._data = DEFAULT_CONFIG.copy()
            cls._instance.load()
        return cls._instance

    def load(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Migrate legacy "Capture" prefix to empty string for pure number naming
                    if loaded.get("filename_prefix") == "Capture":
                        loaded["filename_prefix"] = ""
                    self._data.update(loaded)
        except Exception:
            pass

    def save(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4)
        except Exception:
            pass

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def get_save_dir(self) -> Path:
        p = Path(self.get("save_dir", str(DEFAULT_SAVE_DIR)))
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_next_capture_name(self, auto_increment: bool = True) -> str:
        prefix = str(self.get("filename_prefix", "")).strip()
        try:
            num = int(self.get("next_capture_number", 1))
        except (ValueError, TypeError):
            num = 1
        
        if prefix:
            name = f"{prefix}_{num}" if not prefix.endswith(('_', '-')) else f"{prefix}{num}"
        else:
            name = str(num)

        if auto_increment:
            self.set("next_capture_number", num + 1)
        return name

    def peek_next_capture_name(self) -> str:
        return self.get_next_capture_name(auto_increment=False)

    def set_next_capture_number(self, num: int):
        self.set("next_capture_number", max(1, int(num)))

config = AppConfig()
