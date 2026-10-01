"""Live Qt scheme changes must preserve work and leave every reading surface legible."""
from datetime import datetime

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QMessageBox

from draft import DraftStore
from ui import theme
from ui.main_window import MainWindow, REVIEW


def contrast(ink, surface):
    def luminance(value):
        color = QColor(value)
        channels = [c / 255 for c in (color.red(), color.green(), color.blue())]
        linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
        return sum(c * w for c, w in zip(linear, (.2126, .7152, .0722)))
    a, b = sorted((luminance(ink), luminance(surface)))
    return (b + .05) / (a + .05)


@pytest.fixture
def scheme_notifications(qapp, monkeypatch):
    # Offscreen has no OS scheme API. Exercise the same Qt notification path with
    # a synthetic hint there; Windows GUI verification uses the real platform API.
    hints = qapp.styleHints()
    if qapp.platformName() == "offscreen":
        current = [Qt.ColorScheme.Light]
        def set_scheme(scheme):
            current[0] = scheme
            hints.colorSchemeChanged.emit(scheme)
        monkeypatch.setattr(hints, "colorScheme", lambda: current[0])
        monkeypatch.setattr(hints, "setColorScheme", set_scheme)
        monkeypatch.setattr(hints, "unsetColorScheme", lambda: set_scheme(Qt.ColorScheme.Light))
    yield hints
    hints.unsetColorScheme()
    theme.install(qapp).sync()


@pytest.fixture
def window(qtbot, database, tmp_path, qapp, scheme_notifications):
    widget = MainWindow(database, tmp_path)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    yield widget


def change_scheme(qapp, qtbot, dark):
    qapp.styleHints().setColorScheme(Qt.ColorScheme.Dark if dark else Qt.ColorScheme.Light)
    qtbot.waitUntil(lambda: theme.IS_DARK == dark)
    qtbot.wait(20)


@pytest.mark.parametrize("dark", [True, False])
def test_live_capture_keeps_draft_focus_selection_and_undo(window, qapp, qtbot, tmp_path, dark):
    change_scheme(qapp, qtbot, not dark)
    capture = window.capture
    capture.amount.setText("18.50")
    capture.description.setText("合成主题草稿")
    capture.select_category("工具")
    capture.description.setFocus()
    capture.description.setSelection(2, 2)
    window._save_draft()
    draft = capture.draft()
    change_scheme(qapp, qtbot, dark)
    assert capture.draft() == draft == DraftStore(tmp_path).load()
    assert capture.description.hasFocus() and capture.description.selectedText() == "主题"
    assert contrast(capture.description.palette().color(QPalette.ColorRole.Text), theme.BG) >= 4.5
    assert contrast(capture.amount.palette().color(QPalette.ColorRole.PlaceholderText), theme.BG) >= 4.5
    capture.record()
    change_scheme(qapp, qtbot, not dark)
    window.toast._run_undo()
    assert capture.draft() == draft


def test_live_review_keeps_invalid_edit_and_recolours_existing_chart(window, database, qapp, qtbot):
    change_scheme(qapp, qtbot, False)
    record_id = database.add_record(1200, datetime(2026, 9, 20, 12, 30), "生活", "合成主题记录")
    review = window.review
    review.year, review.month = 2026, 9
    window.switch_to(REVIEW, animate=False)
    row = review.rows()[0]
    qtbot.mouseClick(row, Qt.MouseButton.LeftButton, pos=row.amount.geometry().center())
    row.amount_edit.setText("0")
    row.amount_edit.setFocus()
    qtbot.waitUntil(row.amount_edit.hasFocus)
    row.amount_edit.selectAll()
    old = review.summary.donut.grab().toImage()
    change_scheme(qapp, qtbot, True)
    assert review.editing_row is row and row.editing and row.amount_edit.text() == "0"
    assert row.amount_edit.hasFocus() and row.amount_edit.selectedText() == "0"
    assert database.get_record(record_id)["amount_cents"] == 1200
    assert row.description.palette().color(QPalette.ColorRole.WindowText) == QColor(theme.TEXT)
    image = review.summary.donut.grab().toImage()
    assert image != old
    assert any(image.pixelColor(x, image.height() // 2) == QColor(theme.LIFE)
               for x in range(image.width() - 10, image.width()))
    assert row.category_dot.styleSheet().startswith(f"background: {theme.LIFE};")
    row.cancel_edit()


@pytest.mark.parametrize("dark", [True, False])
def test_existing_menu_dialog_and_selection_palette(window, qapp, qtbot, dark):
    box = QMessageBox(window)
    box.setText("合成对话框")
    qtbot.addWidget(box)
    change_scheme(qapp, qtbot, not dark)
    change_scheme(qapp, qtbot, dark)
    for widget in (box, window.utility_menu, window.capture.popover,
                   window.capture.popover.edit, window.review.search_field):
        palette = widget.palette()
        for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
            # Transparent QSS editors paint their parent's surface; Qt reports an
            # opaque black Base for them even though that brush is never painted.
            surface = palette.color(group, QPalette.ColorRole.Window)
            if surface.alpha() == 0:
                surface = widget.parentWidget().palette().color(group, QPalette.ColorRole.Window)
            assert contrast(palette.color(group, QPalette.ColorRole.Text),
                            surface) >= 4.5, (type(widget).__name__, widget.objectName())
            assert contrast(palette.color(group, QPalette.ColorRole.HighlightedText),
                            palette.color(group, QPalette.ColorRole.Highlight)) >= 4.5
            assert contrast(palette.color(group, QPalette.ColorRole.ToolTipText),
                            palette.color(group, QPalette.ColorRole.ToolTipBase)) >= 4.5
    assert window.utility.ink() == QColor(theme.TEXT_3)


@pytest.mark.parametrize("colors", [theme.LIGHT, theme.DARK], ids=["light", "dark"])
def test_enabled_text_contrast_across_states(colors):
    for surface in ("BG", "SURFACE", "HOVER"):
        for ink in ("TEXT", "TEXT_2", "TEXT_3", "PLACEHOLDER", "ACCENT", "DANGER"):
            assert contrast(colors[ink], colors[surface]) >= 4.5, (ink, surface)
    for surface in ("ACTION", "ACTION_HOVER", "ACTION_PRESSED"):
        assert contrast(colors["ACTION_TEXT"], colors[surface]) >= 4.5
    assert contrast(colors["TEXT"], colors["ACCENT_SOFT"]) >= 4.5
