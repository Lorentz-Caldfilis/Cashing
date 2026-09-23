"""Cashing motion: fast to respond, soft to settle.

One curve and one table of durations for the whole application, so every
state change moves with the same character. Motion only ever explains a
change that has already happened — it never gates the change, never delays
input, and never carries meaning on its own (Art Direction §13, Interaction
Specification §26–27).

Nothing here animates geometry that other widgets are laid out against: a
state may change, the coordinate system may not.
"""
import os
from PySide6.QtCore import QEasingCurve, QPointF, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect

# Motion explains changes; it never carries them. With CASHING_NO_MOTION=1 every state
# still arrives, instantly — which is how the static composition gets checked.
ENABLED = os.environ.get("CASHING_NO_MOTION", "") not in ("1", "true", "True")

# cubic-bezier(0.2, 0, 0, 1): leaves immediately, settles without overshoot.
_CONTROL_1 = QPointF(0.2, 0.0)
_CONTROL_2 = QPointF(0.0, 1.0)

# Durations (ms). The order is the hierarchy: the smaller the change, the shorter it is.
PRESS = 90
HOVER = 110
FOCUS = 140
EDIT = 150
MONTH = 160
SEARCH = 170
TOAST = 180
RECORD = 200      # a record leaving or coming back
SPACE = 200       # Capture ⇄ Review, the one spatial signature


def curve():
    """A fresh curve each time: QEasingCurve is copied by value into animations."""
    c = QEasingCurve(QEasingCurve.Type.BezierSpline)
    c.addCubicBezierSegment(_CONTROL_1, _CONTROL_2, QPointF(1.0, 1.0))
    return c


class Blend(QVariantAnimation):
    """A 0…1 float that follows a boolean state, for widgets that paint themselves.

    The widget keeps its geometry; only what it draws changes. ``set`` is safe to
    call repeatedly — it animates from wherever the value currently is, so a
    fast pointer never makes the surface jump.
    """

    def __init__(self, owner, duration, on_change=None):
        super().__init__(owner)
        self.setDuration(duration)
        self.setEasingCurve(curve())
        self.setStartValue(0.0)
        self.setEndValue(0.0)
        self._value = 0.0
        self.valueChanged.connect(self._store)
        if on_change is not None:
            self.valueChanged.connect(lambda _: on_change())
        self._on_change = on_change

    def _store(self, value):
        self._value = float(value)

    def value(self):
        return self._value

    def set(self, on, *, animate=True):
        target = 1.0 if on else 0.0
        self.stop()
        if not animate or not ENABLED or self._value == target:
            self._value = target
            if self._on_change is not None:
                self._on_change()
            return
        self.setStartValue(self._value)
        self.setEndValue(target)
        self.start()

    def jump_to(self, value):
        """No motion at all: used when a widget is rebuilt in a state it already had."""
        self.stop()
        self._value = float(value)
        if self._on_change is not None:
            self._on_change()


def fade_in(widget, start, duration):
    """Bring a widget back to full opacity from ``start``, then take the effect off again.

    The effect is installed only for the length of the animation: a permanent
    QGraphicsOpacityEffect would make every later repaint go through an offscreen
    buffer. Use it on bounded widgets (a header row, a viewport), never on a
    scroll body whose height follows the data.
    """
    if not ENABLED:
        return None
    # A second fade on the same widget must stop the first: installing an effect deletes
    # the one before it, and a running animation would then write to a dead object.
    running = getattr(widget, "_cashing_fade", None)
    if running is not None:
        running.stop()
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(start)
    widget.setGraphicsEffect(effect)
    animation = QVariantAnimation(widget)
    animation.setDuration(duration)
    animation.setEasingCurve(curve())
    animation.setStartValue(float(start))
    animation.setEndValue(1.0)

    def apply(value):
        try:
            effect.setOpacity(float(value))
        except RuntimeError:  # the widget went away mid-fade; nothing left to fade
            animation.stop()

    def done():
        widget._cashing_fade = None
        try:
            if widget.graphicsEffect() is effect:
                widget.setGraphicsEffect(None)
        except RuntimeError:
            pass
    animation.valueChanged.connect(apply)
    animation.finished.connect(done)
    widget._cashing_fade = animation
    animation.start(QVariantAnimation.DeletionPolicy.DeleteWhenStopped)
    return animation


def slide_home(widget, offset, duration, on_finished=None):
    """Move ``widget`` from ``offset`` pixels away back to where its layout put it.

    Only this widget's position changes; its own children are never re-laid out.
    If a layout pass intervenes it simply resets the origin, and the animation
    still ends exactly where the layout wants the widget.
    """
    if not ENABLED:
        if on_finished is not None:
            on_finished()
        return None
    running = getattr(widget, "_cashing_slide", None)
    if running is not None:
        running.stop()
    origin = widget.pos()
    animation = QVariantAnimation(widget)
    animation.setDuration(duration)
    animation.setEasingCurve(curve())
    animation.setStartValue(float(offset))
    animation.setEndValue(0.0)

    def apply(value):
        try:
            widget.move(origin.x() + int(round(float(value))), origin.y())
        except RuntimeError:
            animation.stop()

    animation.valueChanged.connect(apply)
    animation.finished.connect(lambda: setattr(widget, "_cashing_slide", None))
    if on_finished is not None:
        animation.finished.connect(on_finished)
    widget._cashing_slide = animation
    animation.start(QVariantAnimation.DeletionPolicy.DeleteWhenStopped)
    return animation


def collapse(widget, duration, on_finished=None):
    """A record leaving: it fades and gives its height back, then it is gone.

    The widget carries its own trailing gap, so closing it to zero closes exactly
    the space it occupied — the records below move up once, smoothly, and nothing
    jumps when the list is rebuilt afterwards.
    """
    if not ENABLED:
        widget.hide()
        if on_finished is not None:
            on_finished()
        return None
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    height = widget.height()
    animation = QVariantAnimation(widget)
    animation.setDuration(duration)
    animation.setEasingCurve(curve())
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)

    def apply(value):
        gone = float(value)
        try:
            effect.setOpacity(max(0.0, 1.0 - gone * 1.4))  # out of sight before out of space
            widget.setMaximumHeight(max(0, int(height * (1.0 - gone))))
        except RuntimeError:
            animation.stop()

    def done():
        try:
            widget.hide()
        except RuntimeError:
            pass
        if on_finished is not None:
            on_finished()
    animation.valueChanged.connect(apply)
    animation.finished.connect(done)
    animation.start(QVariantAnimation.DeletionPolicy.DeleteWhenStopped)
    return animation


def mix(a, b, t):
    """Blend two QColor-compatible values component-wise; ``t`` in 0…1."""
    return type(a).fromRgbF(
        a.redF() + (b.redF() - a.redF()) * t,
        a.greenF() + (b.greenF() - a.greenF()) * t,
        a.blueF() + (b.blueF() - a.blueF()) * t,
        a.alphaF() + (b.alphaF() - a.alphaF()) * t,
    )
