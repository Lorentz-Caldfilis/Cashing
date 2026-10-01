"""Cashing's small controls: one family of icon buttons, and the quiet date-time field.

Every icon button is the same object — month arrows, search, close, more. A 32 px
square, one glyph drawn in one 1.5 px stroke, and three states that answer the
hand: a surface that settles in under the pointer, a darker one under a press, and
a ring for keyboard focus. Buttons take focus from the keyboard only, so a click
never leaves a frame behind and the ring always means "the keyboard is here".
At rest the square is not drawn: the glyph alone is the object, as quiet as before.
"""
from PySide6.QtCore import Qt, QEvent, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFontMetrics
from PySide6.QtWidgets import QToolButton, QDateTimeEdit
from ui import motion, theme

ICON_BUTTON = 32
ICON_RADIUS = 6
STROKE = 1.5
# A QDateTimeEdit starts its text 6 px inside its box (2 px of QLineEdit margin, and its own
# line edit sits 4 px in). A field that reads as written text pulls it back by exactly that.
DATE_TEXT_NUDGE = -6


class IconButton(QToolButton):
    """The shared object; subclasses only say which glyph it carries and how loud it is."""
    REST = "TEXT_3"      # token names, resolved at paint time
    ACTIVE = "TEXT_2"

    def __init__(self, name, parent=None, *, size=ICON_BUTTON):
        super().__init__(parent)
        self.setAccessibleName(name)
        self.setToolTip(name)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._hover = motion.Blend(self, motion.HOVER, self.update)
        self._press = motion.Blend(self, motion.PRESS, self.update)
        self.pressed.connect(lambda: self._press.set(True))
        self.released.connect(lambda: self._press.set(False))

    def enterEvent(self, event):
        super().enterEvent(event)
        self._hover.set(self.isEnabled())

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hover.set(False)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self._hover.jump_to(0.0)
            self._press.jump_to(0.0)

    def hover_weight(self):
        return self._hover.value()

    def ink(self):
        if not self.isEnabled():
            return QColor(theme.DISABLED_ARROW)
        lift = max(self.hover_weight(), self._press.value(), 1.0 if self.hasFocus() else 0.0)
        return motion.mix(QColor(getattr(theme, self.REST)), QColor(getattr(theme, self.ACTIVE)), lift)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(Qt.PenStyle.NoPen)
        for color, weight in ((theme.HOVER, self.hover_weight()), (theme.PRESSED, self._press.value())):
            if weight > 0.001:
                surface = QColor(color)
                surface.setAlphaF(weight)
                painter.setBrush(surface)
                painter.drawRoundedRect(box, ICON_RADIUS, ICON_RADIUS)
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(theme.FOCUS_RING), 1.0))
            painter.drawRoundedRect(box, ICON_RADIUS, ICON_RADIUS)
        pen = QPen(self.ink(), STROKE)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        self.draw_glyph(painter, QPointF(self.width() / 2.0, self.height() / 2.0))

    def draw_glyph(self, painter, centre):
        raise NotImplementedError


class ChevronButton(IconButton):
    """One half of the month's navigation: the point leads the way the month moves."""
    REST, ACTIVE = "TEXT_2", "TEXT"  # the month is read, so its arrows speak a step louder
    ARM = 3.4
    REACH = 5.2

    def __init__(self, direction, name, parent=None):
        super().__init__(name, parent)
        self.direction = direction

    def draw_glyph(self, painter, centre):
        tip = centre.x() + self.ARM * self.direction
        back = centre.x() - self.ARM * self.direction
        painter.drawLine(QPointF(back, centre.y() - self.REACH), QPointF(tip, centre.y()))
        painter.drawLine(QPointF(tip, centre.y()), QPointF(back, centre.y() + self.REACH))


class SearchButton(IconButton):
    """A magnifier; its ink is centred on the button, so its edge is where the grid puts it."""

    def draw_glyph(self, painter, centre):
        lens = QPointF(centre.x() - 1.5, centre.y() - 1.5)
        painter.drawEllipse(lens, 5.5, 5.5)
        painter.drawLine(QPointF(lens.x() + 4.2, lens.y() + 4.2), QPointF(lens.x() + 8.5, lens.y() + 8.5))


class CloseButton(IconButton):
    """× — a way out of a temporary state, the size of the field it sits in."""
    HALF = 4.0

    def draw_glyph(self, painter, centre):
        h = self.HALF
        painter.drawLine(QPointF(centre.x() - h, centre.y() - h), QPointF(centre.x() + h, centre.y() + h))
        painter.drawLine(QPointF(centre.x() + h, centre.y() - h), QPointF(centre.x() - h, centre.y() + h))


class MoreButton(IconButton):
    """⋮ — three points in the same ink as the other glyphs, not a character from the font."""
    GAP = 5.0
    DOT = 1.4

    def draw_glyph(self, painter, centre):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.ink())
        for step in (-1, 0, 1):
            painter.drawEllipse(QPointF(centre.x(), centre.y() + step * self.GAP), self.DOT, self.DOT)


class QuietDateTimeEdit(QDateTimeEdit):
    """The time, editable, with the same restraint as the other fields: no box, and a
    focus line only as wide as the time it underlines."""

    def __init__(self, parent=None, *, line_lift=0):
        super().__init__(parent)
        self._line_lift = line_lift
        self._focus = motion.Blend(self, motion.FOCUS, self.update)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._focus.set(True)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._focus.set(False)

    def paintEvent(self, event):
        super().paintEvent(event)
        weight = self._focus.value()
        if weight <= 0.001:
            return
        metrics = QFontMetrics(self.font())
        width = min(metrics.horizontalAdvance(self.text()) + 4, self.width())
        paint_focus_line(self, QRectF(0, self.height() - self._line_lift - 1.0, width, 1.0), weight)


def paint_focus_line(widget, rect, weight):
    """The one mark a focused field makes: a hairline under its own text."""
    painter = QPainter(widget)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor(theme.ACCENT_SOFT)
    color.setAlphaF(weight)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRect(rect)
