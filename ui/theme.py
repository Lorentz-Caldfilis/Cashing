"""PC Light Mode tokens (Visual Design System v1.0 + PC Light amendments).

Neutral colours carry almost the whole interface. The system accent is a
slate blue-grey that never means a category; the three category colours are
low-saturation and always accompanied by text. Danger is its own red.
Spacing follows the 4px scale: 4 8 12 16 24 32 48 64.

Ink is five levels, and they must be told apart by eye — muted, never washed
out (Art Direction §16). Three of them are reading levels and two are states:

    1 TEXT         the fact itself: an amount, a description, a month, a total
    2 TEXT_2       the fact's frame: a day, a ¥ mark, a time, a quiet control
    3 TEXT_3       derived reading: a category, a hint, an empty month
    4 placeholder  waiting for input — a shape, never a value, never unavailable
    5 disabled     currently unavailable: an inert surface, not faint text

Placeholder and disabled are never the same thing: the first invites, the
second refuses, so the first is free-standing text and the second keeps the
surface and edge of the control it belongs to.
"""
from PySide6.QtGui import QFont

# Neutrals
BG = "#f7f8fa"          # near white, never pure white over large areas
SURFACE = "#ffffff"     # real overlays only (toast, popover, menu)
TEXT = "#1b2430"        # 1 primary
TEXT_2 = "#4e5b69"      # 2 secondary
TEXT_3 = "#87909c"      # 3 tertiary — still readable at a glance, never a grey smear
HAIRLINE = "#e5e8ec"
HOVER = "#f1f3f6"       # the weakest state: the pointer passed here, nothing more
PRESSED = "#e5e9ee"     # a press: one clear step below Hover, so the hand is answered
# Keyboard focus. Controls take focus from the keyboard only, so the ring never lingers
# after a click and can afford to be plainly visible: 3:1 on the page and on Hover.
FOCUS_RING = "#7a8a9d"
# Qt draws a placeholder at half the field's colour, and a style sheet always wins over the
# palette — so an empty field sets this colour and lands on ~#a7b0bc over the background:
# one clear step weaker than TEXT_3, and nowhere near the grey of a disabled control.
PLACEHOLDER_SOURCE = "#576a7e"
# Disabled is a control that is currently unavailable, never a faint piece of information:
# it keeps a surface and an edge so it still reads as the button it is.
DISABLED_SURFACE = "#e8ebef"
DISABLED_BORDER = "#dadfe5"
DISABLED_TEXT = "#98a1ac"
# Inert, not absent: a month arrow with nowhere to go is still half of the navigation.
DISABLED_ARROW = "#c3cad3"
# System accent (focus, selected, current dot, primary action) — not a category
ACCENT = "#56687c"
ACCENT_HOVER = "#4a5a6c"
ACCENT_PRESSED = "#3f4e5e"
ACCENT_SOFT = "#bcc8d5"  # focus line
# The one primary action. It is the accent lightened by a step: clear enough to be the
# obvious thing to press and to carry white at AA contrast, quiet enough that the amount
# above it is still the loudest thing on the page. Hover and press walk it back down the
# accent's own values, so pressing still reads as pressing.
ACTION = "#66788c"
# Edit is said by a thin accent bar beside the record's two lines. The surface under it is
# only a shade above Hover: enough to hold the record together, never a card laid on the page.
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
    background: transparent; border: none; padding: 0px 0px 2px 0px; color: {TEXT};
    selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT}; }}
/* Empty: 0.00 is a shape, not a value, and must stay clearly weaker than a real amount. */
QLineEdit#amount[empty="true"] {{ color: {PLACEHOLDER_SOURCE}; }}
QLineEdit#description {{
    background: transparent; border: none; padding: 4px 8px 5px 8px; color: {TEXT};
    selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT}; }}
/* Empty: the prompt is waiting for input, at exactly the level the empty amount waits at. */
QLineEdit#description[empty="true"] {{ color: {PLACEHOLDER_SOURCE}; }}
QPushButton#time {{
    background: transparent; border: 1px solid transparent; border-radius: 6px;
    padding: 3px 10px; color: {TEXT_3}; font-size: 14px; }}
QPushButton#time:hover {{ background: {HOVER}; color: {TEXT_2}; }}
QPushButton#time:pressed {{ background: {PRESSED}; color: {TEXT_2}; }}
QPushButton#time:focus {{ border-color: {FOCUS_RING}; color: {TEXT_2}; }}
QLabel#error {{ color: {DANGER}; font-size: 13px; }}
QLabel#errorDetail {{ color: {TEXT_3}; font-size: 12px; }}

/* Review header. The arrows, search, close and ⋮ are one painted family (ui/controls.py).
   Text buttons follow the same three states: hover, a darker press, a keyboard-only ring.
   The month ends in 月, whose right side bearing is wider than the first digit's left one,
   so the box is padded unevenly to leave the ink evenly spaced between the two chevrons
   (measured on 2026年9月: 15.7 px of air on each side). */
QPushButton#monthLabel {{ background: transparent; border: 1px solid transparent; border-radius: 6px;
    color: {TEXT}; padding: 2px 3px 2px 5px; }}
QPushButton#monthLabel:hover {{ background: {HOVER}; }}
QPushButton#monthLabel:pressed {{ background: {PRESSED}; }}
QPushButton#monthLabel:focus {{ border-color: {FOCUS_RING}; }}

/* Search */
QLineEdit#search {{ background: {SURFACE}; border: 1px solid {HAIRLINE}; border-radius: 8px;
    padding: 5px 12px; font-size: 15px; color: {TEXT}; selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT}; }}
QLineEdit#search:focus {{ border-color: {ACCENT_SOFT}; }}

/* In-place row editors: an edited record is still a record. No field carries a line at
   rest and none carries one on hover — a field that is not focused looks exactly like the
   label it replaced. The focused one paints its own line, as wide as its text. */
QLineEdit#rowEdit, QDateTimeEdit#rowEdit {{
    background: transparent; border: none; padding: 0px;
    color: {TEXT}; selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT}; }}
QDateTimeEdit#rowEdit {{ color: {TEXT_2}; }}
/* The category box paints itself (dot, word, chevron) so Edit keeps the row's anchors. */
QComboBox QAbstractItemView {{ background: {SURFACE}; border: 1px solid {HAIRLINE}; padding: 4px;
    selection-background-color: {HOVER}; selection-color: {TEXT}; outline: 0; }}

/* Popover: the layer is the object. The time inside it is written, not boxed — the same
   quiet field as the time of a record being edited, with its own focus line. */
QFrame#popover {{ background: {SURFACE}; border: 1px solid {HAIRLINE}; border-radius: 10px; }}
QFrame#popover QDateTimeEdit {{
    background: transparent; border: none; padding: 0px; color: {TEXT};
    selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT}; }}
QPushButton#quiet {{ background: transparent; border: 1px solid transparent; border-radius: 6px;
    padding: 3px 10px; color: {TEXT_2}; }}
QPushButton#quiet:hover {{ background: {HOVER}; }}
QPushButton#quiet:pressed {{ background: {PRESSED}; }}
QPushButton#quiet:focus {{ border-color: {FOCUS_RING}; }}

/* Toast */
QFrame#toast {{ background: {SURFACE}; border: 1px solid {HAIRLINE}; border-radius: 10px; }}
QFrame#toast QLabel {{ color: {TEXT}; font-size: 14px; background: transparent; }}
QFrame#toast QLabel#toastDanger {{ color: {DANGER}; }}
QPushButton#undo {{ background: transparent; border: 1px solid transparent; border-radius: 6px;
    padding: 3px 10px; color: {ACCENT}; font-size: 14px; font-weight: 500; }}
QPushButton#undo:hover {{ background: {HOVER}; }}
QPushButton#undo:pressed {{ background: {PRESSED}; }}
QPushButton#undo:focus {{ border-color: {FOCUS_RING}; }}

/* Utility (⋮ paints itself; its menu opens under it, right-aligned, inside the window) */
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
