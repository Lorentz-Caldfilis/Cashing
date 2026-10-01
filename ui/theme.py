"""System light/dark tokens; shared by native widgets, QSS and painted controls.

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
from PySide6.QtCore import QObject, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPalette

# Neutrals
BG = "#f7f8fa"          # near white, never pure white over large areas
SURFACE = "#ffffff"     # real overlays only (toast, popover, menu)
TEXT = "#1b2430"        # 1 primary
TEXT_2 = "#4e5b69"      # 2 secondary
TEXT_3 = "#596778"      # 3 tertiary — readable in both schemes
HAIRLINE = "#e5e8ec"
HOVER = "#f1f3f6"       # the weakest state: the pointer passed here, nothing more
PRESSED = "#e5e9ee"     # a press: one clear step below Hover, so the hand is answered
# Keyboard focus. Controls take focus from the keyboard only, so the ring never lingers
# after a click and can afford to be plainly visible: 3:1 on the page and on Hover.
FOCUS_RING = "#7a8a9d"
# Specify the actual placeholder colour, avoiding Qt's translucent text fallback.
PLACEHOLDER = "#636f80"
# Disabled is a control that is currently unavailable, never a faint piece of information:
# it keeps a surface and an edge so it still reads as the button it is.
DISABLED_SURFACE = "#e8ebef"
DISABLED_BORDER = "#dadfe5"
DISABLED_TEXT = "#697587"
# Inert, not absent: a month arrow with nowhere to go is still half of the navigation.
DISABLED_ARROW = "#c3cad3"
# System accent (focus, selected, current dot, primary action) — not a category
ACCENT = "#405f86"
ACCENT_HOVER = "#4a5a6c"
ACCENT_PRESSED = "#3f4e5e"
ACCENT_SOFT = "#bcc8d5"  # focus line
# The one primary action. It is the accent lightened by a step: clear enough to be the
# obvious thing to press and to carry white at AA contrast, quiet enough that the amount
# above it is still the loudest thing on the page. Hover and press walk it back down the
# accent's own values, so pressing still reads as pressing.
ACTION = "#496b94"
ACTION_HOVER = "#405f86"
ACTION_PRESSED = "#3f4e5e"
ACTION_TEXT = "#ffffff"
SCROLL_HANDLE = "#d5dae0"
SCROLL_HOVER = "#c3cad2"
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
DANGER = "#a95050"
DANGER_TINT = "#f6ecec"
DANGER_STRONG = "#a04f4f"

BASE_PX = 14

LIGHT = {name: value for name, value in globals().copy().items()
         if name.isupper() and isinstance(value, str) and value.startswith("#")}
DARK = {**LIGHT,
        "BG": "#171c24", "SURFACE": "#222a35", "TEXT": "#e7edf4",
        "TEXT_2": "#b9c5d2", "TEXT_3": "#a1afbf", "PLACEHOLDER": "#8c9bae",
        "HAIRLINE": "#394452", "HOVER": "#28323e", "PRESSED": "#354253",
        "FOCUS_RING": "#9bbce1", "DISABLED_SURFACE": "#28313b",
        "DISABLED_BORDER": "#425062", "DISABLED_TEXT": "#8a98a9",
        "DISABLED_ARROW": "#738299", "ACCENT": "#9bbce1",
        "ACCENT_HOVER": "#3c5b81", "ACCENT_PRESSED": "#314b6b",
        "ACCENT_SOFT": "#456284", "ACCENT_TINT": "#27384d",
        "ACTION": "#466b96", "ACTION_HOVER": "#3c5b81", "ACTION_PRESSED": "#314b6b",
        "LIFE": "#92b698", "TOOL": "#92b3d7", "FUN": "#d0ad74",
        "UNKNOWN_COLOR": "#6c7a8c", "DANGER": "#e49b9b",
        "DANGER_TINT": "#402b32", "DANGER_STRONG": "#f1b0b0",
        "SCROLL_HANDLE": "#526173", "SCROLL_HOVER": "#6b7e94"}
IS_DARK = False


def set_style(widget, template):
    """Remember semantic colours so existing widgets can be recoloured in place."""
    widget.setProperty("cashingStyle", template)
    widget.setStyleSheet(template.format_map(globals()))


def palette():
    result = QPalette()
    roles = {"Window": BG, "Base": SURFACE, "AlternateBase": HOVER, "Button": SURFACE,
             "WindowText": TEXT, "Text": TEXT, "ButtonText": TEXT, "BrightText": ACTION_TEXT,
             "ToolTipBase": SURFACE, "ToolTipText": TEXT, "PlaceholderText": PLACEHOLDER,
             "Highlight": ACCENT_SOFT, "HighlightedText": TEXT,
             "Link": ACCENT, "LinkVisited": ACCENT, "Accent": ACCENT,
             "Light": HAIRLINE, "Midlight": HOVER, "Mid": HAIRLINE,
             "Dark": PRESSED, "Shadow": BG}
    for role, value in roles.items():
        result.setColor(getattr(QPalette.ColorRole, role), QColor(value))
    for role in ("WindowText", "Text", "ButtonText", "PlaceholderText"):
        result.setColor(QPalette.ColorGroup.Disabled, getattr(QPalette.ColorRole, role),
                        QColor(DISABLED_TEXT))
    result.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, QColor(DISABLED_SURFACE))
    return result


class SystemTheme(QObject):
    """Follow Qt's OS scheme; never override the user's system setting."""
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self._applying = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.sync)
        app.styleHints().colorSchemeChanged.connect(self._schedule)
        app.paletteChanged.connect(self._schedule)
        self.sync()

    def _schedule(self, *_):
        # Qt signals the scheme before updating its native palette; coalesce both.
        if not self._applying:
            self._timer.start(0)

    def sync(self):
        global IS_DARK, STYLE, CATEGORY_COLORS
        scheme = self.app.styleHints().colorScheme()
        dark = (scheme == Qt.ColorScheme.Dark if scheme != Qt.ColorScheme.Unknown
                else self.app.style().standardPalette().color(QPalette.ColorRole.Window).lightness() < 128)
        if (IS_DARK == dark and self.app.styleSheet() == STYLE
                and self.app.palette().color(QPalette.ColorRole.Window) == QColor(BG)
                and self.app.palette().color(QPalette.ColorRole.Text) == QColor(TEXT)):
            return
        self._applying = True
        try:
            IS_DARK = dark
            globals().update(DARK if dark else LIGHT)
            CATEGORY_COLORS = {"生活": LIFE, "工具": TOOL, "娱乐": FUN}
            STYLE = STYLE_TEMPLATE.format_map(globals())
            self.app.setPalette(palette())
            self.app.setStyleSheet(STYLE)
            for widget in self.app.allWidgets():
                template = widget.property("cashingStyle")
                if template:
                    widget.setStyleSheet(template.format_map(globals()))
                widget.update()
        finally:
            self._applying = False


def install(app):
    if not hasattr(app, "_cashing_theme"):
        app._cashing_theme = SystemTheme(app)
    return app._cashing_theme


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

STYLE_TEMPLATE = """
QWidget {{ color: {TEXT}; }}
QMainWindow, QDialog, QWidget#space, QWidget#column, QScrollArea, QWidget#scrollBody {{ background: {BG}; }}
QLineEdit, QTextEdit, QPlainTextEdit {{ placeholder-text-color: {PLACEHOLDER};
    selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT}; }}
QToolTip {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {HAIRLINE}; padding: 4px 8px; }}

/* Named navigation keeps two spaces discoverable and keyboard reachable. */
QWidget#navigation {{ background: {HAIRLINE}; border-radius: 10px; }}
QPushButton#spaceTab {{ background: transparent; color: {TEXT_2}; border: 1px solid transparent;
    border-radius: 7px; padding: 5px 18px; font-size: 14px; }}
QPushButton#spaceTab:checked {{ background: {SURFACE}; color: {ACCENT}; font-weight: 500; }}
QPushButton#spaceTab:hover {{ color: {TEXT}; }}
QPushButton#spaceTab:focus {{ border-color: {FOCUS_RING}; }}

/* Capture */
QLineEdit#amount {{
    background: transparent; border: none; padding: 0px 0px 2px 0px; color: {TEXT};
    selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT}; }}
/* Empty: 0.00 is a shape, not a value, and must stay clearly weaker than a real amount. */
QLineEdit#amount[empty="true"] {{ color: {TEXT}; }}
QLineEdit#description {{
    background: transparent; border: none; padding: 4px 8px 5px 8px; color: {TEXT};
    selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT}; }}
/* Empty: the prompt is waiting for input, at exactly the level the empty amount waits at. */
QLineEdit#description[empty="true"] {{ color: {TEXT}; }}
QPushButton#time {{
    background: transparent; border: 1px solid transparent; border-radius: 6px;
    padding: 3px 10px; color: {TEXT_3}; font-size: 14px; }}
QPushButton#time:hover {{ background: {HOVER}; color: {TEXT_2}; }}
QPushButton#time:pressed {{ background: {PRESSED}; color: {TEXT_2}; }}
QPushButton#time:focus {{ border-color: {FOCUS_RING}; color: {TEXT_2}; }}
QPushButton#purpose {{ background: transparent; border: 1px solid {HAIRLINE};
    border-radius: 8px; color: {TEXT_2}; font-size: 14px; }}
QPushButton#purpose:hover {{ background: {HOVER}; }}
QPushButton#purpose:checked {{ background: {ACCENT_TINT}; color: {ACCENT}; border-color: {ACCENT_SOFT}; }}
QPushButton#purpose:focus {{ border-color: {FOCUS_RING}; }}
QLabel#error {{ color: {DANGER}; font-size: 13px; }}
QPlainTextEdit#errorDetail {{ color: {TEXT_3}; background: transparent; border: none; font-size: 12px; }}

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
QScrollBar::handle:vertical {{ background: {SCROLL_HANDLE}; border-radius: 5px; min-height: 32px; }}
QScrollBar::handle:vertical:hover {{ background: {SCROLL_HOVER}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
"""
STYLE = STYLE_TEMPLATE.format_map(globals())
