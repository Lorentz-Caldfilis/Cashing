"""Capture ⇄ Review: two full-window spaces side by side, a short horizontal slide between them.

The spatial relation is fixed (Capture left, Review right, no wrap). Position is
shown by two wordless dots; the edges of the window and Alt+←/→ move between
the spaces; a horizontal trackpad scroll does too. Plain ←/→ are never used —
they belong to text editing.
"""
import time
from PySide6.QtCore import Qt, QObject, QEvent, QPropertyAnimation, Property, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath
from PySide6.QtWidgets import QWidget, QApplication
from ui import motion, theme

SLIDE_MS = motion.SPACE
EDGE_WIDTH = 28
# The window's bottom band: where the page dots live, in both spaces. Content never scrolls
# into it, so the dots are never drawn over a record; the dots sit on its middle line.
FOOTER_HEIGHT = 64
DOTS_HEIGHT = 24
WHEEL_THRESHOLD = 150   # accumulated angleDelta().x() units (one notch = 120)
WHEEL_COOLDOWN_S = 0.5
WHEEL_GESTURE_GAP_S = 0.3


class SpaceSwitcher(QWidget):
    changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("space")
        self._strip = QWidget(self)
        self._strip.setObjectName("space")
        self._pages = []
        self._index = 0
        self._offset = 0
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(SLIDE_MS)
        self._animation.setEasingCurve(motion.curve())  # leaves at once, settles without overshoot

    # ---- pages -----------------------------------------------------------
    def add_page(self, page):
        page.setParent(self._strip)
        self._pages.append(page)
        page.show()
        self._relayout()

    def page(self, index):
        return self._pages[index]

    def count(self):
        return len(self._pages)

    def current_index(self):
        return self._index

    def current_page(self):
        return self._pages[self._index] if self._pages else None

    def set_index(self, index, animate=True):
        index = max(0, min(index, len(self._pages) - 1))
        if index == self._index and not self.is_animating():
            return
        self._index = index
        target = index * self.width()
        self._animation.stop()
        if animate and motion.ENABLED and self.isVisible() and self.width() > 0:
            self._animation.setStartValue(self._offset)
            self._animation.setEndValue(target)
            self._animation.start()
        else:
            self._set_offset(target)
        self.changed.emit(index)

    def is_animating(self):
        return self._animation.state() == QPropertyAnimation.State.Running

    # ---- geometry ----------------------------------------------------------
    def _get_offset(self):
        return self._offset

    def _set_offset(self, value):
        """Only the strip's position changes. Both pages keep the geometry they already
        had, so no content is re-laid out while the spaces move."""
        self._offset = int(value)
        self._strip.move(-self._offset, 0)

    offset = Property(int, _get_offset, _set_offset)

    def _relayout(self):
        width, height = self.width(), self.height()
        self._strip.resize(max(1, width * max(1, len(self._pages))), height)
        for i, page in enumerate(self._pages):
            page.setGeometry(i * width, 0, width, height)
        self._animation.stop()
        self._set_offset(self._index * width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()


class PageDots(QWidget):
    """● ○ — position feedback, clickable but not a button."""
    activated = Signal(int)

    def __init__(self, count, parent=None):
        super().__init__(parent)
        self._count = count
        self._index = 0
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setFixedSize(count * 24, DOTS_HEIGHT)
        self.setAccessibleName("页面位置")

    def set_index(self, index):
        self._index = index
        self.update()

    def index_at(self, x):
        return max(0, min(x // 24, self._count - 1))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(self._count):
            current = i == self._index
            painter.setBrush(QColor(theme.ACCENT if current else "#cfd5db"))
            radius = 4.0 if current else 3.5
            cx, cy = i * 24 + 12, 12
            painter.drawEllipse(QRectF(cx - radius, cy - radius, 2 * radius, 2 * radius))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self.index_at(int(event.position().x())))
        event.accept()


class EdgeZone(QWidget):
    """A quiet strip along one window edge: a faint chevron on hover, a click moves over."""
    activated = Signal()

    def __init__(self, direction, parent=None):
        super().__init__(parent)
        self.direction = direction  # -1 = left edge (to Capture), +1 = right edge (to Review)
        self._hover = False
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("上一页" if direction < 0 else "下一页")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def paintEvent(self, event):
        if not self._hover:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(theme.TEXT_3))
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        cx, cy, s = self.width() / 2, self.height() / 2, 5.0
        path = QPainterPath()
        if self.direction < 0:
            path.moveTo(cx + s / 2, cy - s); path.lineTo(cx - s / 2, cy); path.lineTo(cx + s / 2, cy + s)
        else:
            path.moveTo(cx - s / 2, cy - s); path.lineTo(cx + s / 2, cy); path.lineTo(cx - s / 2, cy + s)
        painter.drawPath(path)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit()
        event.accept()


class WheelNavigator(QObject):
    """Horizontal trackpad scrolling inside the window moves between the spaces.

    Installed on the application so it sees wheel events before any scroll area
    (which cannot scroll horizontally anyway). Vertical scrolling is untouched.
    """

    def __init__(self, window, on_move):
        super().__init__(window)
        self.window = window
        self.on_move = on_move
        self._accumulated = 0
        self._last_event = 0.0
        self._locked_until = 0.0

    def eventFilter(self, watched, event):
        if event.type() != QEvent.Type.Wheel or not isinstance(watched, QWidget):
            return False
        if QApplication.activePopupWidget() is not None or watched.window() is not self.window:
            return False
        delta = event.angleDelta()
        if delta.x() == 0 or abs(delta.x()) <= abs(delta.y()):
            return False
        now = time.monotonic()
        if now < self._locked_until:
            return True
        if now - self._last_event > WHEEL_GESTURE_GAP_S:
            self._accumulated = 0
        self._last_event = now
        self._accumulated += delta.x()
        if abs(self._accumulated) >= WHEEL_THRESHOLD:
            direction = -1 if self._accumulated > 0 else 1  # content follows the fingers
            self._accumulated = 0
            self._locked_until = now + WHEEL_COOLDOWN_S
            self.on_move(direction)
        return True
