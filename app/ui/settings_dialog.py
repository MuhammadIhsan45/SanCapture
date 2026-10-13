"""
Settings & Preferences Dialog for FastCapture.
Handles Hotkey customization with interactive key sequence recorder, Auto-Save directory, formats, and startup options.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QWidget, QFormLayout, QLineEdit, QPushButton, 
    QCheckBox, QComboBox, QFileDialog, QGroupBox, 
    QLabel, QDialogButtonBox, QMessageBox, QToolButton, QSpinBox
)
from PyQt6.QtGui import QKeyEvent, QKeySequence
from PyQt6.QtCore import Qt, pyqtSignal

from app.ui.theme import APP_STYLESHEET, ThemeColors
from app.ui.icons import IconFactory
from app.core.config import config, OutputDest

class HotkeyRecorderEdit(QLineEdit):
    """
    Interactive Hotkey Input that captures key combinations directly when pressed
    (e.g., user presses Alt + S, it captures and formats 'Alt+S' automatically).
    """
    def __init__(self, initial_hotkey: str = "", parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Click & press shortcut keys (e.g. Alt+S)...")
        self.setText(initial_hotkey)
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: #1E2227;
                color: #00E5FF;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #3B4048;
                border-radius: 3px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid #D32F2F;
                background-color: #16181D;
                color: #FFFFFF;
            }}
        """)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        # Handle Clear keys (Backspace or Delete) without modifiers
        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete) and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.setText("None")
            event.accept()
            return

        # Ignore standalone modifier presses while waiting for key
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            event.accept()
            return

        # Extract Modifiers
        mods = []
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            mods.append("Ctrl")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            mods.append("Alt")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            mods.append("Shift")
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            mods.append("Win")

        # Map Key Code to String
        key_name = ""
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            key_name = chr(key).upper()
        elif Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            key_name = chr(key)
        elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            key_name = f"F{key - Qt.Key.Key_F1 + 1}"
        elif key in (Qt.Key.Key_Print, Qt.Key.Key_SysReq):
            key_name = "PrintScreen"
        elif key == Qt.Key.Key_Space:
            key_name = "Space"
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            key_name = "Enter"
        elif key == Qt.Key.Key_Escape:
            key_name = "Escape"
        elif key == Qt.Key.Key_Insert:
            key_name = "Insert"
        elif key == Qt.Key.Key_Home:
            key_name = "Home"
        elif key == Qt.Key.Key_End:
            key_name = "End"
        elif key == Qt.Key.Key_PageUp:
            key_name = "PageUp"
        elif key == Qt.Key.Key_PageDown:
            key_name = "PageDown"
        else:
            # Fallback to key text or QKeySequence
            seq = QKeySequence(key).toString()
            if seq:
                key_name = seq

        if key_name:
            if mods:
                full_hotkey = "+".join(mods) + "+" + key_name
            else:
                full_hotkey = key_name
            self.setText(full_hotkey)

        event.accept()

class SettingsDialog(QDialog):
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SanCapture Settings")
        self.setFixedSize(600, 560)
        self.setStyleSheet(APP_STYLESHEET)
        self.setWindowIcon(IconFactory.get_icon("settings", 24))

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # -------------------------------------------------------------
        # Tab 1: General & Destination
        # -------------------------------------------------------------
        tab_gen = QWidget()
        layout_gen = QVBoxLayout(tab_gen)

        # Destination Group
        grp_dest = QGroupBox("Default Output & Save Options")
        form_dest = QFormLayout(grp_dest)

        self.combo_dest = QComboBox()
        for key, title in OutputDest.CHOICES:
            self.combo_dest.addItem(title, key)
        form_dest.addRow("Default Destination:", self.combo_dest)

        # Save Directory
        h_dir = QHBoxLayout()
        self.txt_dir = QLineEdit()
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_dir)
        h_dir.addWidget(self.txt_dir)
        h_dir.addWidget(btn_browse)
        form_dest.addRow("Auto-Save Folder:", h_dir)

        # Format
        self.combo_format = QComboBox()
        self.combo_format.addItems(["PNG", "WEBP", "JPG", "BMP", "PDF"])
        self.combo_format.currentIndexChanged.connect(self._update_filename_preview)
        form_dest.addRow("Default File Format:", self.combo_format)

        layout_gen.addWidget(grp_dest)

        # File Naming & Numbering Group
        grp_naming = QGroupBox("Capture Naming & Sequential Numbering")
        form_naming = QFormLayout(grp_naming)

        self.txt_prefix = QLineEdit()
        self.txt_prefix.setPlaceholderText("(Leave empty for pure numbers: 1, 2, 3...)")
        self.txt_prefix.textChanged.connect(self._update_filename_preview)
        form_naming.addRow("Filename Prefix:", self.txt_prefix)

        self.spin_start_num = QSpinBox()
        self.spin_start_num.setRange(1, 999999)
        self.spin_start_num.setValue(1)
        self.spin_start_num.setToolTip("Specify any starting number for sequential captures (e.g. 1, 100, etc.)")
        self.spin_start_num.valueChanged.connect(self._update_filename_preview)
        form_naming.addRow("Next / Starting Number:", self.spin_start_num)

        self.lbl_naming_preview = QLabel("Preview: 1.png")
        self.lbl_naming_preview.setStyleSheet(f"color: {ThemeColors.TEXT_HIGHLIGHT}; font-weight: bold; font-size: 11px;")
        form_naming.addRow("File Name Preview:", self.lbl_naming_preview)

        layout_gen.addWidget(grp_naming)

        # Behavior Group
        grp_beh = QGroupBox("Application Behavior")
        form_beh = QVBoxLayout(grp_beh)

        self.chk_sound = QCheckBox("Play camera shutter sound on capture")
        self.chk_ontop = QCheckBox("Keep floating toolbar always on top")
        self.chk_tray = QCheckBox("Minimize to System Tray when closed")

        form_beh.addWidget(self.chk_sound)
        form_beh.addWidget(self.chk_ontop)
        form_beh.addWidget(self.chk_tray)

        layout_gen.addWidget(grp_beh)
        layout_gen.addStretch()
        tabs.addTab(tab_gen, "General")

        # -------------------------------------------------------------
        # Tab 2: Image Quality & Compression (NEW)
        # -------------------------------------------------------------
        tab_qual = QWidget()
        layout_qual = QVBoxLayout(tab_qual)

        # Preset Group
        grp_preset = QGroupBox("Quality & Size Preset")
        layout_preset_box = QVBoxLayout(grp_preset)
        
        self.combo_preset = QComboBox()
        self.combo_preset.addItem("✨ Optimized Sharp (Balanced - Recommended)", "balanced")
        self.combo_preset.addItem("💎 Maximum Sharpness (100% Lossless)", "lossless")
        self.combo_preset.addItem("📦 High Compression (Compact Web / Smallest Size)", "compact")
        self.combo_preset.currentIndexChanged.connect(self._on_preset_changed)
        layout_preset_box.addWidget(self.combo_preset)

        self.lbl_preset_desc = QLabel()
        self.lbl_preset_desc.setWordWrap(True)
        self.lbl_preset_desc.setStyleSheet(f"color: {ThemeColors.TEXT_HIGHLIGHT}; font-size: 11px; padding-top: 2px;")
        layout_preset_box.addWidget(self.lbl_preset_desc)
        layout_qual.addWidget(grp_preset)

        # Detailed Format Tuning
        grp_tune = QGroupBox("Format-Specific Sharpness & Compression Tuning")
        form_tune = QFormLayout(grp_tune)

        # JPEG Quality
        h_jpg = QHBoxLayout()
        self.spin_jpg_qual = QSpinBox()
        self.spin_jpg_qual.setRange(40, 100)
        self.spin_jpg_qual.setValue(90)
        self.spin_jpg_qual.setSuffix("%")
        h_jpg.addWidget(self.spin_jpg_qual)
        self.chk_subsampling = QCheckBox("4:4:4 Chroma Subsampling (Keeps colored text razor-sharp)")
        self.chk_subsampling.setChecked(True)
        self.chk_subsampling.setToolTip("Eliminates color blurring on text and sharp UI lines in JPEG images")
        h_jpg.addWidget(self.chk_subsampling)
        form_tune.addRow("JPEG Quality & Sharpness:", h_jpg)

        # PNG Compression
        h_png = QHBoxLayout()
        self.spin_png_comp = QSpinBox()
        self.spin_png_comp.setRange(1, 9)
        self.spin_png_comp.setValue(9)
        self.spin_png_comp.setToolTip("Level 9 = Maximum lossless compression (smallest size, 100% sharp)")
        h_png.addWidget(self.spin_png_comp)
        lbl_png_info = QLabel("(Level 9 = Deepest lossless compression, 100% pixel-perfect)")
        lbl_png_info.setStyleSheet("color: #ABB2BF; font-size: 11px;")
        h_png.addWidget(lbl_png_info)
        h_png.addStretch()
        form_tune.addRow("PNG Compression Level:", h_png)

        # WebP Settings
        h_webp = QHBoxLayout()
        self.chk_webp_lossless = QCheckBox("WebP Lossless Mode (100% sharp text, 30-50% smaller than PNG)")
        self.chk_webp_lossless.setChecked(True)
        h_webp.addWidget(self.chk_webp_lossless)
        form_tune.addRow("WebP Mode:", h_webp)

        # Auto-enhance sharpness
        self.chk_auto_sharpen = QCheckBox("Apply subtle edge crispness filter automatically on capture")
        form_tune.addRow("Auto-Enhance:", self.chk_auto_sharpen)

        layout_qual.addWidget(grp_tune)

        # Recommendation Banner
        grp_info = QGroupBox("💡 Format Recommendation Guide")
        layout_info = QVBoxLayout(grp_info)
        lbl_guide = QLabel(
            "• <b>WebP</b>: The most efficient format for screenshots! 100% pixel-sharp text at 30-50% smaller size than PNG.<br>"
            "• <b>PNG</b>: Universal lossless format with Level 9 compression. Zero artifacts, perfect crispness.<br>"
            "• <b>JPEG</b>: Compact size with 4:4:4 subsampling to prevent blurry text edges."
        )
        lbl_guide.setStyleSheet("color: #ABB2BF; font-size: 11px; line-height: 140%;")
        lbl_guide.setTextFormat(Qt.TextFormat.RichText)
        layout_info.addWidget(lbl_guide)
        layout_qual.addWidget(grp_info)

        layout_qual.addStretch()
        tabs.addTab(tab_qual, "Quality & Size")

        # -------------------------------------------------------------
        # Tab 3: Hotkeys
        # -------------------------------------------------------------
        tab_hk = QWidget()
        layout_hk = QVBoxLayout(tab_hk)

        grp_hk = QGroupBox("Global Shortcut Hotkeys (Click box & press combination on keyboard)")
        form_hk = QFormLayout(grp_hk)

        self.txt_hk_active = HotkeyRecorderEdit()
        self.txt_hk_obj = HotkeyRecorderEdit()
        self.txt_hk_rect = HotkeyRecorderEdit()
        self.txt_hk_free = HotkeyRecorderEdit()
        self.txt_hk_full = HotkeyRecorderEdit()
        self.txt_hk_color = HotkeyRecorderEdit()

        form_hk.addRow("Capture Active Window:", self._wrap_recorder(self.txt_hk_active))
        form_hk.addRow("Capture Window / Object:", self._wrap_recorder(self.txt_hk_obj))
        form_hk.addRow("Capture Rectangular Region:", self._wrap_recorder(self.txt_hk_rect))
        form_hk.addRow("Capture Freehand Region:", self._wrap_recorder(self.txt_hk_free))
        form_hk.addRow("Capture Full Screen:", self._wrap_recorder(self.txt_hk_full))
        form_hk.addRow("Screen Color Picker:", self._wrap_recorder(self.txt_hk_color))

        layout_hk.addWidget(grp_hk)
        
        lbl_tip = QLabel("💡 Tip: Click any input field above and directly press your shortcut (e.g. Alt+S, Ctrl+PrtScn). Press Backspace to reset.")
        lbl_tip.setStyleSheet(f"color: {ThemeColors.TEXT_HIGHLIGHT}; font-size: 11px; padding-top: 4px;")
        layout_hk.addWidget(lbl_tip)
        layout_hk.addStretch()
        tabs.addTab(tab_hk, "Hotkeys")

        main_layout.addWidget(tabs)

        # Dialog Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._save_values)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

    def _wrap_recorder(self, recorder: HotkeyRecorderEdit) -> QWidget:
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        h.addWidget(recorder, 1)

        btn_clear = QToolButton()
        btn_clear.setText("✕")
        btn_clear.setToolTip("Clear / Disable Hotkey")
        btn_clear.setStyleSheet("color: #ABB2BF; font-weight: bold; padding: 2px 4px;")
        btn_clear.clicked.connect(lambda: recorder.setText("None"))
        h.addWidget(btn_clear)
        return container

    def _on_preset_changed(self):
        preset = self.combo_preset.currentData()
        if preset == "balanced":
            self.lbl_preset_desc.setText("✓ Ideal for daily use: 100% sharp text, deep compression, compact file sizes.")
            self.spin_jpg_qual.setValue(90)
            self.chk_subsampling.setChecked(True)
            self.spin_png_comp.setValue(9)
            self.chk_webp_lossless.setChecked(True)
        elif preset == "lossless":
            self.lbl_preset_desc.setText("✓ Maximum quality: 100% bit-exact pixel perfection with deep lossless compression.")
            self.spin_jpg_qual.setValue(98)
            self.chk_subsampling.setChecked(True)
            self.spin_png_comp.setValue(9)
            self.chk_webp_lossless.setChecked(True)
        elif preset == "compact":
            self.lbl_preset_desc.setText("✓ Smallest file size: High compression with 4:4:4 crisp edges for easy sharing.")
            self.spin_jpg_qual.setValue(82)
            self.chk_subsampling.setChecked(True)
            self.spin_png_comp.setValue(8)
            self.chk_webp_lossless.setChecked(False)

    def _update_filename_preview(self):
        pfx = self.txt_prefix.text().strip()
        num = self.spin_start_num.value()
        fmt = self.combo_format.currentText().lower()
        if pfx:
            fname = f"{pfx}_{num}" if not pfx.endswith(('_', '-')) else f"{pfx}{num}"
        else:
            fname = str(num)
        self.lbl_naming_preview.setText(f"Preview: {fname}.{fmt}")

    def _load_values(self):
        # Dest
        cur_dest = config.get("output_dest", OutputDest.EDITOR)
        idx = self.combo_dest.findData(cur_dest)
        if idx >= 0:
            self.combo_dest.setCurrentIndex(idx)

        self.txt_dir.setText(str(config.get("save_dir", "")))
        
        cur_fmt = config.get("image_format", "PNG")
        idx_fmt = self.combo_format.findText(cur_fmt)
        if idx_fmt >= 0:
            self.combo_format.setCurrentIndex(idx_fmt)

        self.txt_prefix.setText(str(config.get("filename_prefix", "")))
        try:
            cur_num = int(config.get("next_capture_number", 1))
        except (ValueError, TypeError):
            cur_num = 1
        self.spin_start_num.setValue(cur_num)
        self._update_filename_preview()

        # Quality Preset
        cur_preset = config.get("quality_preset", "balanced")
        idx_preset = self.combo_preset.findData(cur_preset)
        if idx_preset >= 0:
            self.combo_preset.setCurrentIndex(idx_preset)
        self._on_preset_changed()

        self.spin_jpg_qual.setValue(int(config.get("jpeg_quality", 90)))
        self.chk_subsampling.setChecked(int(config.get("jpeg_subsampling", 0)) == 0)
        self.spin_png_comp.setValue(int(config.get("png_compression_level", 9)))
        self.chk_webp_lossless.setChecked(bool(config.get("webp_lossless", True)))
        self.chk_auto_sharpen.setChecked(bool(config.get("auto_enhance_sharpness", False)))

        self.chk_sound.setChecked(config.get("play_sound", True))
        self.chk_ontop.setChecked(config.get("always_on_top", True))
        self.chk_tray.setChecked(config.get("minimize_to_tray", True))

        # Hotkeys
        hk = config.get("hotkeys", {})
        self.txt_hk_active.setText(hk.get("active_window", "Alt+W"))
        self.txt_hk_obj.setText(hk.get("window_object", "Alt+O"))
        self.txt_hk_rect.setText(hk.get("rectangular_region", "Alt+S"))
        self.txt_hk_free.setText(hk.get("freehand_region", "Alt+F"))
        self.txt_hk_full.setText(hk.get("full_screen", "Alt+A"))
        self.txt_hk_color.setText(hk.get("color_picker", "Alt+C"))

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Auto-Save Folder", self.txt_dir.text())
        if folder:
            self.txt_dir.setText(folder)

    def _save_values(self):
        config.set("output_dest", self.combo_dest.currentData())
        config.set("save_dir", self.txt_dir.text().strip())
        config.set("image_format", self.combo_format.currentText())
        config.set("filename_prefix", self.txt_prefix.text().strip())
        config.set_next_capture_number(self.spin_start_num.value())

        # Quality & Compression
        config.set("quality_preset", self.combo_preset.currentData())
        config.set("jpeg_quality", self.spin_jpg_qual.value())
        config.set("jpeg_subsampling", 0 if self.chk_subsampling.isChecked() else 2)
        config.set("png_compression_level", self.spin_png_comp.value())
        config.set("webp_lossless", self.chk_webp_lossless.isChecked())
        config.set("auto_enhance_sharpness", self.chk_auto_sharpen.isChecked())

        config.set("play_sound", self.chk_sound.isChecked())
        config.set("always_on_top", self.chk_ontop.isChecked())
        config.set("minimize_to_tray", self.chk_tray.isChecked())

        # Hotkeys
        new_hk = {
            "active_window": self.txt_hk_active.text().strip(),
            "window_object": self.txt_hk_obj.text().strip(),
            "rectangular_region": self.txt_hk_rect.text().strip(),
            "freehand_region": self.txt_hk_free.text().strip(),
            "full_screen": self.txt_hk_full.text().strip(),
            "color_picker": self.txt_hk_color.text().strip()
        }
        config.set("hotkeys", new_hk)

        self.settings_saved.emit()
        self.accept()

