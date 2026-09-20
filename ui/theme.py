"""PC Light Mode tokens (Visual Design System v1.0 + PC Light amendments).

Neutral colours carry almost the whole interface. The system accent is a
slate blue-grey that never means a category; the three category colours are
low-saturation and always accompanied by text. Danger is its own red.
Spacing follows the 4px scale: 4 8 12 16 24 32 48 64.
"""
from PySide6.QtGui import QFont

# Neutrals
BG = "#f7f8fa"          # near white, never pure white over large areas
SURFACE = "#ffffff"     # real overlays only (toast, popover, menu)
TEXT = "#1f2933"        # near black
TEXT_2 = "#5c6874"      # secondary
TEXT_3 = "#98a2ad"      # meta / muted
HAIRLINE = "#e5e8ec"
HOVER = "#eff1f4"       # weakest state
# System accent (focus, selected, current dot, primary action) — not a category
ACCENT = "#56687c"
ACCENT_HOVER = "#4a5a6c"
ACCENT_PRESSED = "#3f4e5e"
ACCENT_SOFT = "#c3cdd8"  # focus underline
ACCENT_TINT = "#eef1f5"  # edit background
# Category semantics
LIFE = "#6f8f72"
TOOL = "#627f9f"
FUN = "#b58a4a"
CATEGORY_COLORS = {"生活": LIFE, "工具": TOOL, "娱乐": FUN}
UNKNOWN_COLOR = "#c2c8cf"
# Danger
DANGER = "#b65f5f"
DANGER_TINT = "#f6ecec"
DANGER_STRONG = "#a04f4f"

BASE_PX = 14


def font(px, weight=QFont.Weight.Normal, *, tabular=False):
    """System UI font at a pixel size. Never set font-size in the stylesheet on QWidget:
    style-sheet fonts override QWidget.setFont and would flatten the type scale."""
    f = QFont()
    f.setPixelSize(px)
    f.setWeight(weight)
    if tabular:
        try:
            f.setFeature(QFont.Tag("tnum"), 1)
        except (AttributeError, TypeError):  # older Qt: system font digits are already tabular
            pass
    return f


MEDIUM = QFont.Weight.Medium

STYLE = f"""
QWidget {{ color: {TEXT}; }}
QMainWindow, QWidget#space, QWidget#column, QScrollArea, QWidget#scrollBody {{ background: {BG}; }}
QToolTip {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {HAIRLINE}; padding: 4px 8px; }}

/* Capture */
QLineEdit#amount {{
    background: transparent; border: none; border-bottom: 2px solid transparent;
    padding: 0px 2px 2px 2px; color: {TEXT}; selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT}; }}
QLineEdit#amount:focus {{ border-bottom: 2px solid {ACCENT_SOFT}; }}
QLineEdit#description {{
    background: transparent; border: none; border-bottom: 1px solid transparent;
    padding: 4px 8px 5px 8px; color: {TEXT}; selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT}; }}
QLineEdit#description:focus {{ border-bottom: 1px solid {ACCENT_SOFT}; }}
QPushButton#time {{
    background: transparent; border: 1px solid transparent; border-radius: 6px;
    padding: 3px 10px; color: {TEXT_3}; font-size: 14px; }}
QPushButton#time:hover {{ background: {HOVER}; color: {TEXT_2}; }}
QPushButton#time:focus {{ border-color: {ACCENT_SOFT}; color: {TEXT_2}; }}
QPushButton#record {{
    background: {ACCENT}; color: #ffffff; border: 2px solid {ACCENT}; border-radius: 6px;
    padding: 5px 26px; font-size: 15px; min-width: 60px; }}
QPushButton#record:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#record:pressed {{ background: {ACCENT_PRESSED}; border-color: {ACCENT_PRESSED}; }}
QPushButton#record:focus {{ border-color: {TEXT}; }}
QPushButton#record:disabled {{ background: #e3e6ea; color: #a5adb6; border-color: #e3e6ea; }}
QLabel#error {{ color: {DANGER}; font-size: 13px; }}
QLabel#errorDetail {{ color: {TEXT_3}; font-size: 12px; }}

/* Popover */
QFrame#popover {{ background: {SURFACE}; border: 1px solid {HAIRLINE}; border-radius: 10px; }}
QFrame#popover QDateTimeEdit {{
    background: transparent; border: 1px solid {HAIRLINE}; border-radius: 6px; padding: 4px 8px;
    font-size: 15px; selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT}; }}
QFrame#popover QDateTimeEdit:focus {{ border-color: {ACCENT_SOFT}; }}
QPushButton#quiet {{ background: transparent; border: 1px solid transparent; border-radius: 6px;
    padding: 3px 10px; color: {TEXT_2}; }}
QPushButton#quiet:hover {{ background: {HOVER}; }}
QPushButton#quiet:focus {{ border-color: {ACCENT_SOFT}; }}

/* Toast */
QFrame#toast {{ background: {SURFACE}; border: 1px solid {HAIRLINE}; border-radius: 10px; }}
QFrame#toast QLabel {{ color: {TEXT}; font-size: 14px; background: transparent; }}
QFrame#toast QLabel#toastDanger {{ color: {DANGER}; }}
QPushButton#undo {{ background: transparent; border: 1px solid transparent; border-radius: 6px;
    padding: 3px 10px; color: {ACCENT}; font-size: 14px; font-weight: 500; }}
QPushButton#undo:hover {{ background: {HOVER}; }}
QPushButton#undo:focus {{ border-color: {ACCENT_SOFT}; }}

/* Utility */
QToolButton#utility {{ background: transparent; border: 1px solid transparent; border-radius: 6px;
    color: {TEXT_3}; font-size: 20px; padding: 0px 6px; }}
QToolButton#utility:hover {{ background: {HOVER}; color: {TEXT_2}; }}
QToolButton#utility:focus {{ border-color: {ACCENT_SOFT}; }}
QToolButton#utility::menu-indicator {{ image: none; width: 0px; }}
QMenu {{ background: {SURFACE}; border: 1px solid {HAIRLINE}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}
QMenu::item:selected {{ background: {HOVER}; }}
QMenu::separator {{ height: 1px; background: {HAIRLINE}; margin: 4px 8px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #d5dae0; border-radius: 5px; min-height: 32px; }}
QScrollBar::handle:vertical:hover {{ background: #c3cad2; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
"""
