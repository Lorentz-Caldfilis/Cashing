"""Search is a temporary Review state across all history; Utility is a quiet ⋮, never a third space."""
from datetime import datetime
import pytest
from PySide6.QtCore import Qt, QCoreApplication, QPoint
from PySide6.QtWidgets import QMenu
from ui.main_window import MainWindow, CAPTURE, REVIEW
from ui.record_row import DayHeading
from ui.review_page import SEARCH_TEXT_INSET


@pytest.fixture
def window(qtbot, database, tmp_path):
    widget = MainWindow(database, tmp_path)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    widget.switch_to(REVIEW, animate=False)
    return widget


@pytest.fixture
def page(window, database):
    database.add_record(5900, datetime(2026, 9, 12, 9, 0), "工具", "ChatGPT Plus")
    database.add_record(5900, datetime(2026, 8, 12, 9, 0), "工具", "ChatGPT Plus")
    database.add_record(2850, datetime(2026, 9, 20, 18, 42), "生活", "晚饭")
    database.add_record(1500, datetime(2025, 3, 1, 12, 0), None, "chatgpt 礼品卡")
    review = window.review
    review.year, review.month = 2026, 9
    review.refresh()
    QCoreApplication.processEvents()
    return review


def search(qtbot, page, text):
    page.search_field.setText(text)
    qtbot.waitUntil(lambda: not page._search_timer.isActive(), timeout=2000)
    QCoreApplication.processEvents()


def test_search_replaces_the_month_row_and_spans_all_history(page, qtbot):
    assert not page.searching and page.header_stack.currentIndex() == 0
    scroll = page.scroll.verticalScrollBar()
    scroll.setValue(scroll.maximum())
    saved = scroll.value()
    qtbot.mouseClick(page.search_button, Qt.MouseButton.LeftButton)
    assert page.searching and page.header_stack.currentIndex() == 1
    assert page.search_field.hasFocus()
    assert page.search_button.isHidden() and not page.summary.isVisibleTo(page)
    assert not page.previous.isVisibleTo(page) and not page.next.isVisibleTo(page)
    assert page.rows() == []  # nothing until something is typed
    search(qtbot, page, "chat")
    assert [(r.record["datetime"][:10], r.record["description"]) for r in page.rows()] == [
        ("2026-09-12", "ChatGPT Plus"), ("2026-08-12", "ChatGPT Plus"), ("2025-03-01", "chatgpt 礼品卡")]
    headings = [h.text() for h in page.history.findChildren(DayHeading)]
    assert headings == ["2026年9月12日 星期六", "2026年8月12日 星期三", "2025年3月1日 星期六"]
    assert not page.no_results.isVisibleTo(page)
    search(qtbot, page, "键盘")
    assert page.rows() == [] and page.no_results.isVisibleTo(page)
    assert page.no_results.text() == "没有找到“键盘”相关记录"
    search(qtbot, page, "59")  # amounts are not searched, only the description
    assert page.rows() == []
    qtbot.mouseClick(page.search_close, Qt.MouseButton.LeftButton)
    assert not page.searching and page.header_stack.currentIndex() == 0
    assert (page.year, page.month) == (2026, 9) and page.month_label.text() == "2026年9月"
    assert page.summary.isVisibleTo(page) and not page.search_button.isHidden()
    assert [r.record["description"] for r in page.rows()] == ["晚饭", "ChatGPT Plus"]
    assert page.search_field.text() == ""
    QCoreApplication.processEvents()
    assert scroll.value() == saved


def test_escape_and_ctrl_f(page, qtbot):
    qtbot.keyClick(page, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    assert page.searching and page.search_field.hasFocus()
    search(qtbot, page, "晚")
    assert len(page.rows()) == 1
    qtbot.keyClick(page.search_field, Qt.Key.Key_Escape)
    assert not page.searching
    assert [r.record["description"] for r in page.rows()] == ["晚饭", "ChatGPT Plus"]


def test_search_results_edit_in_place_and_stay_in_context(page, qtbot, database):
    page.enter_search()
    search(qtbot, page, "chatgpt")
    row = page.rows()[1]  # the August record
    qtbot.mouseClick(row, Qt.MouseButton.LeftButton, pos=row.amount.geometry().center())
    assert row.editing and page.editing_row is row
    row.amount_edit.setText("60")
    qtbot.keyClick(row.amount_edit, Qt.Key.Key_Return)
    assert page.searching and page.header_stack.currentIndex() == 1
    assert database.get_record(row.record["id"])["amount_cents"] == 6000
    assert [r.amount.text() for r in page.rows()] == ["¥59.00", "¥60.00", "¥15.00"]
    assert (page.year, page.month) == (2026, 9)  # never jumps to the record's month
    # Delete + undo also keep the search context.
    row = page.rows()[2]
    qtbot.mouseClick(row, Qt.MouseButton.LeftButton, pos=row.description.geometry().center())
    qtbot.mouseClick(row.edge, Qt.MouseButton.LeftButton)
    assert page.searching and len(page.rows()) == 2
    window = page.window()
    assert window.toast.label.text() == "已删除 ¥15.00 · chatgpt 礼品卡"
    qtbot.mouseClick(window.toast.undo_button, Qt.MouseButton.LeftButton)
    assert page.searching and [r.record["description"] for r in page.rows()][2] == "chatgpt 礼品卡"


def test_invalid_edit_blocks_search_and_switching_to_capture_exits_search(page, qtbot):
    row = page.rows()[0]
    qtbot.mouseClick(row, Qt.MouseButton.LeftButton, pos=row.amount.geometry().center())
    row.amount_edit.setText("0")
    page.enter_search()
    assert not page.searching and row.editing  # fix or cancel first
    qtbot.keyClick(row.amount_edit, Qt.Key.Key_Escape)
    page.enter_search()
    assert page.searching
    window = page.window()
    assert window.switch_to(CAPTURE, animate=False)
    assert not page.searching and window.current_index() == CAPTURE
    assert window.capture.amount.hasFocus()


def test_search_read_failure_is_reported(page, qtbot, monkeypatch, database):
    page.enter_search()
    from database import DatabaseError

    def fail(*args):
        raise DatabaseError("测试：读取失败")
    monkeypatch.setattr(database, "search_records", fail)
    search(qtbot, page, "x")
    assert page.failure.isVisibleTo(page) and "读取失败" in page.failure.text()
    monkeypatch.undo()
    search(qtbot, page, "晚")
    assert not page.failure.isVisibleTo(page) and len(page.rows()) == 1


def test_the_query_is_typed_on_the_records_text_edge(page, qtbot):
    page.enter_search()
    search(qtbot, page, "晚")
    page.body_layout.activate()
    qtbot.wait(10)
    typed = page.search_field.mapTo(page, QPoint(SEARCH_TEXT_INSET, 0)).x()
    found = page.rows()[0].description.mapTo(page, QPoint(0, 0)).x()
    assert abs(typed - found) <= 1


def test_utility_is_a_quiet_overlay_on_both_spaces(window, qtbot, tmp_path, database):
    utility = window.utility
    assert utility.text() == "⋮" and utility.isVisible()
    assert utility.x() + utility.width() <= window.centralWidget().width()
    assert utility.y() < 40
    # On the header's line, not a near miss above it.
    glyph = window.review.search_button
    central = window.centralWidget()
    assert glyph.mapTo(central, glyph.rect().center()).y() == utility.geometry().center().y()
    window.switch_to(CAPTURE, animate=False)
    assert utility.isVisible()
    actions = [a.text() for a in window.utility_menu.actions() if not a.isSeparator()]
    assert actions == ["打开数据目录", "关于 Cashing"]
    assert str(database.path) in window.about_text()
    assert window.data_directory == tmp_path
    # No settings, no third space: the menu is the whole utility surface.
    assert isinstance(utility.menu(), QMenu) and len(actions) == 2
