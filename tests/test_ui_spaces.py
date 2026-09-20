"""Capture ⇄ Review: fixed left/right relation, dots, edges, Alt+arrows, trackpad wheel; no wrap."""
import pytest
from PySide6.QtCore import Qt, QPoint, QPointF, QEvent
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow, CAPTURE, REVIEW
from ui import spaces


@pytest.fixture
def window(qtbot, database, tmp_path):
    widget = MainWindow(database, tmp_path)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def settled(qtbot, window):
    qtbot.waitUntil(lambda: not window.spaces.is_animating(), timeout=2000)


def test_starts_in_capture_with_dots_and_only_the_right_edge(window):
    assert window.current_index() == CAPTURE
    assert window.dots._index == CAPTURE
    assert window.right_edge.isVisible() and not window.left_edge.isVisible()
    assert window.spaces.page(REVIEW).x() == window.spaces.width()


def test_alt_arrows_switch_and_never_wrap(window, qtbot):
    assert not window.switch_to(CAPTURE)  # already there: nothing happens
    qtbot.keyClick(window.capture.amount, Qt.Key.Key_Right, Qt.KeyboardModifier.AltModifier)
    settled(qtbot, window)
    assert window.current_index() == REVIEW
    assert window.spaces.offset == window.spaces.width()
    assert window.dots._index == REVIEW
    assert window.left_edge.isVisible() and not window.right_edge.isVisible()
    qtbot.keyClick(window, Qt.Key.Key_Right, Qt.KeyboardModifier.AltModifier)
    settled(qtbot, window)
    assert window.current_index() == REVIEW  # no wrap to Capture
    qtbot.keyClick(window, Qt.Key.Key_Left, Qt.KeyboardModifier.AltModifier)
    settled(qtbot, window)
    assert window.current_index() == CAPTURE and window.spaces.offset == 0
    assert window.capture.amount.hasFocus()
    qtbot.keyClick(window.capture.amount, Qt.Key.Key_Left, Qt.KeyboardModifier.AltModifier)
    settled(qtbot, window)
    assert window.current_index() == CAPTURE


def test_plain_arrows_edit_text_and_never_switch(window, qtbot):
    amount = window.capture.amount
    qtbot.keyClicks(amount, "28")
    qtbot.keyClick(amount, Qt.Key.Key_Left)
    assert amount.cursorPosition() == 1
    qtbot.keyClick(amount, Qt.Key.Key_Right)
    qtbot.keyClick(amount, Qt.Key.Key_Right)
    assert amount.cursorPosition() == 2
    assert window.current_index() == CAPTURE and not window.spaces.is_animating()


def test_dots_and_edges_switch(window, qtbot):
    qtbot.mouseClick(window.dots, Qt.MouseButton.LeftButton, pos=QPoint(36, 12))
    settled(qtbot, window)
    assert window.current_index() == REVIEW
    qtbot.mouseClick(window.left_edge, Qt.MouseButton.LeftButton)
    settled(qtbot, window)
    assert window.current_index() == CAPTURE
    qtbot.mouseClick(window.right_edge, Qt.MouseButton.LeftButton)
    settled(qtbot, window)
    assert window.current_index() == REVIEW
    qtbot.mouseClick(window.dots, Qt.MouseButton.LeftButton, pos=QPoint(12, 12))
    settled(qtbot, window)
    assert window.current_index() == CAPTURE


def wheel(widget, dx, dy=0):
    pos = QPointF(widget.width() / 2, widget.height() / 2)
    event = QWheelEvent(pos, widget.mapToGlobal(pos), QPoint(0, 0), QPoint(dx, dy),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(widget, event)


def test_horizontal_wheel_moves_between_spaces_with_threshold_and_cooldown(window, qtbot, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(spaces.time, "monotonic", lambda: clock[0])
    wheel(window.capture, -60)
    assert window.current_index() == CAPTURE  # below threshold
    clock[0] += 0.05
    wheel(window.capture, -60)
    clock[0] += 0.05
    wheel(window.capture, -60)
    settled(qtbot, window)
    assert window.current_index() == REVIEW  # content followed the fingers
    clock[0] += 0.1
    wheel(window.review, 400)  # inside the cooldown: ignored
    assert window.current_index() == REVIEW
    clock[0] += 1.0
    wheel(window.review, 0, -400)  # vertical scrolling is not navigation
    assert window.current_index() == REVIEW
    wheel(window.review, 400)
    settled(qtbot, window)
    assert window.current_index() == CAPTURE
    clock[0] += 1.0
    wheel(window.capture, 60)  # already leftmost: nothing, no wrap
    clock[0] += 0.05
    wheel(window.capture, 120)
    assert window.current_index() == CAPTURE


def test_wheel_gesture_gap_resets_accumulation(window, qtbot, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(spaces.time, "monotonic", lambda: clock[0])
    wheel(window.capture, -100)
    clock[0] += 1.0  # a new gesture: the old partial swipe is forgotten
    wheel(window.capture, -100)
    assert window.current_index() == CAPTURE


def test_slide_is_short_and_lands_exactly(window, qtbot):
    window.switch_to(REVIEW)
    assert window.spaces.is_animating()
    assert spaces.SLIDE_MS <= 220
    settled(qtbot, window)
    assert window.spaces.offset == window.spaces.width()
    window.resize(window.width() + 40, window.height())
    qtbot.wait(20)
    assert window.spaces.offset == window.spaces.width()  # a resize keeps the current space aligned
    assert window.spaces.page(CAPTURE).width() == window.spaces.width()


def test_overlays_follow_the_window(window, qtbot):
    window.resize(720, 560)
    qtbot.wait(20)
    central = window.centralWidget()
    assert abs(window.dots.x() + window.dots.width() // 2 - central.width() // 2) <= 1
    assert window.dots.y() + window.dots.height() == central.height() - 20
    assert window.right_edge.x() + window.right_edge.width() == central.width()
