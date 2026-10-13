"""
Visual Theme System for FastCapture
Solid, sharp, classic professional desktop utility styling (Non-AI look).
Crisp 1px borders, high-contrast readability, solid dark slate & steel blue palette.
"""

class ThemeColors:
    # Main backgrounds
    BG_DARK = "#1E2227"
    BG_PANEL = "#282C34"
    BG_PANEL_ALT = "#21252B"
    BG_HOVER = "#353B45"
    BG_ACTIVE = "#3E4451"
    BG_SELECTION = "#2C3E50"

    # Borders & Lines
    BORDER_DARK = "#181A1F"
    BORDER_LIGHT = "#3B4048"
    BORDER_FOCUS = "#007ACC"
    BORDER_CRISP = "#4C5362"

    # Accent Colors (FastStone & Professional Utility Accents)
    ACCENT_RED = "#D32F2F"       # Capture Red / Record
    ACCENT_BLUE = "#0288D1"      # Primary Action Blue
    ACCENT_ORANGE = "#F57C00"    # Highlight Orange
    ACCENT_GREEN = "#388E3C"     # Success / Check Green
    ACCENT_YELLOW = "#FBC02D"    # Tool Yellow
    ACCENT_PURPLE = "#7B1FA2"    # Detail Purple

    # Text Colors
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#ABB2BF"
    TEXT_MUTED = "#5C6370"
    TEXT_HIGHLIGHT = "#61AFEF"

    # Overlay & Magnifier
    OVERLAY_BG = "#000000"
    SNIPER_LINE = "#E53935"
    LOUPE_BORDER = "#D32F2F"
    LOUPE_BG = "#1A1D21"
    SELECTION_FILL = "rgba(33, 150, 243, 0.15)"
    SELECTION_BORDER = "#00E5FF"


APP_STYLESHEET = f"""
/* Global Reset & Typography */
QWidget {{
    background-color: {ThemeColors.BG_PANEL};
    color: {ThemeColors.TEXT_PRIMARY};
    font-family: "Segoe UI", "Tahoma", "Arial", sans-serif;
    font-size: 12px;
    font-weight: 500;
}}

/* Floating Toolbar Window */
#FloatingToolbar {{
    background-color: {ThemeColors.BG_PANEL_ALT};
    border: 1px solid {ThemeColors.BORDER_CRISP};
    border-radius: 3px;
}}

#ToolbarGrip {{
    background-color: #1A1D22;
    border-right: 1px solid {ThemeColors.BORDER_LIGHT};
    padding: 0px 4px;
}}

/* Utility Action Buttons */
QToolButton, QPushButton {{
    background-color: transparent;
    color: {ThemeColors.TEXT_PRIMARY};
    border: 1px solid transparent;
    border-radius: 2px;
    padding: 3px 6px;
    font-weight: 600;
}}

QToolButton:hover, QPushButton:hover {{
    background-color: {ThemeColors.BG_HOVER};
    border: 1px solid {ThemeColors.BORDER_LIGHT};
}}

QToolButton:pressed, QPushButton:pressed {{
    background-color: {ThemeColors.BG_ACTIVE};
    border: 1px solid {ThemeColors.ACCENT_BLUE};
}}

QToolButton:checked, QPushButton:checked {{
    background-color: {ThemeColors.BG_SELECTION};
    border: 1px solid {ThemeColors.BORDER_FOCUS};
    color: #61AFEF;
}}

QToolButton:disabled, QPushButton:disabled {{
    color: {ThemeColors.TEXT_MUTED};
    background-color: transparent;
    border-color: transparent;
}}

/* Crisp Accent Button */
QPushButton#PrimaryBtn {{
    background-color: {ThemeColors.ACCENT_BLUE};
    border: 1px solid #01579B;
    color: #FFFFFF;
    font-weight: bold;
    padding: 5px 12px;
}}

QPushButton#PrimaryBtn:hover {{
    background-color: #039BE5;
}}

QPushButton#PrimaryBtn:pressed {{
    background-color: #0277BD;
}}

QPushButton#DangerBtn {{
    background-color: {ThemeColors.ACCENT_RED};
    border: 1px solid #B71C1C;
    color: #FFFFFF;
    font-weight: bold;
    padding: 5px 12px;
}}

QPushButton#DangerBtn:hover {{
    background-color: #E53935;
}}

/* ComboBox */
QComboBox {{
    background-color: {ThemeColors.BG_PANEL_ALT};
    border: 1px solid {ThemeColors.BORDER_LIGHT};
    border-radius: 2px;
    padding: 2px 8px;
    color: {ThemeColors.TEXT_PRIMARY};
    min-height: 22px;
}}

QComboBox:hover {{
    border: 1px solid {ThemeColors.BORDER_CRISP};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid {ThemeColors.BORDER_LIGHT};
}}

QComboBox QAbstractItemView {{
    background-color: {ThemeColors.BG_PANEL_ALT};
    border: 1px solid {ThemeColors.BORDER_CRISP};
    selection-background-color: {ThemeColors.BG_HOVER};
    selection-color: {ThemeColors.TEXT_PRIMARY};
    outline: none;
    padding: 2px;
}}

/* Menu Bar & Menus */
QMenuBar {{
    background-color: {ThemeColors.BG_PANEL_ALT};
    border-bottom: 1px solid {ThemeColors.BORDER_LIGHT};
    color: {ThemeColors.TEXT_PRIMARY};
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 4px 8px;
}}

QMenuBar::item:selected {{
    background-color: {ThemeColors.BG_HOVER};
}}

QMenu {{
    background-color: {ThemeColors.BG_PANEL_ALT};
    border: 1px solid {ThemeColors.BORDER_CRISP};
    color: {ThemeColors.TEXT_PRIMARY};
    padding: 4px;
}}

QMenu::item {{
    padding: 5px 24px 5px 16px;
    border-radius: 2px;
}}

QMenu::item:selected {{
    background-color: {ThemeColors.BG_HOVER};
    color: #FFFFFF;
}}

QMenu::separator {{
    height: 1px;
    background: {ThemeColors.BORDER_LIGHT};
    margin: 4px 0px;
}}

/* Status Bar */
QStatusBar {{
    background-color: {ThemeColors.BG_PANEL_ALT};
    border-top: 1px solid {ThemeColors.BORDER_LIGHT};
    color: {ThemeColors.TEXT_SECONDARY};
    font-size: 11px;
}}

/* ScrollBar (Crisp Slim) */
QScrollBar:vertical {{
    background: {ThemeColors.BG_DARK};
    width: 12px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {ThemeColors.BORDER_CRISP};
    min-height: 20px;
    border-radius: 2px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: {ThemeColors.TEXT_SECONDARY};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: {ThemeColors.BG_DARK};
    height: 12px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {ThemeColors.BORDER_CRISP};
    min-width: 20px;
    border-radius: 2px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {ThemeColors.TEXT_SECONDARY};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Tooltips */
QToolTip {{
    background-color: #111317;
    color: #FFFFFF;
    border: 1px solid {ThemeColors.ACCENT_BLUE};
    padding: 4px 8px;
    font-size: 11px;
    font-weight: bold;
}}

/* Inputs & SpinBoxes */
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {ThemeColors.BG_DARK};
    border: 1px solid {ThemeColors.BORDER_LIGHT};
    border-radius: 2px;
    padding: 3px 6px;
    color: #FFFFFF;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {ThemeColors.ACCENT_BLUE};
}}

/* Group Box */
QGroupBox {{
    border: 1px solid {ThemeColors.BORDER_LIGHT};
    border-radius: 3px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: {ThemeColors.TEXT_HIGHLIGHT};
}}
"""
