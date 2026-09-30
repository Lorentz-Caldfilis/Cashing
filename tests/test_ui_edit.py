"""In-place edit, PC delete edge, delete + undo. Legal changes take effect at once; illegal ones never leave."""
from datetime import datetime
import pytest
from PySide6.QtCore import Qt, QPoint, QEvent, QCoreApplication
from PySide6.QtGui import QMouseEvent, QFontMetrics
from PySide6.QtWidgets import QApplication
from database import DatabaseError
from ui.main_window import MainWindow, CAPTURE, REVIEW
from ui.record_row import EDGE_COLLAPSED, EDGE_EXPANDED


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
    database.add_record(2850, datetime(2026, 9, 20, 18, 42), "生活", "晚饭")
    database.add_record(5900, datetime(2026, 9, 20, 15, 17), "工具", "ChatGPT")
    database.add_record(3600, datetime(2026, 9, 19, 21, 3), None, "电影")
    review = window.review
    review.year, review.month = 2026, 9
    review.refresh()
    QCoreApplication.processEvents()
    return review


def click(qtbot, row, cell=None):
    target = getattr(row, cell) if cell else None
    pos = target.geometry().center() if target else QPoint(row.width() // 2, row.height() // 2)
    qtbot.mouseClick(row, Qt.MouseButton.LeftButton, pos=pos)


def press_outside(page):
    """A press on the page body, delivered through the application filter like a real click."""
    body = page.scroll.widget()
    pos = QPoint(5, 5)
    event = QMouseEvent(QEvent.Type.MouseButtonPress, pos, body.mapToGlobal(pos),
                        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(body, event)


def test_single_click_enters_edit_in_place(page, qtbot):
    row = page.rows()[0]
    assert not row.editing and row.time.isVisibleTo(row)
    click(qtbot, row, "description")
    assert row.editing and page.editing_row is row
    assert row.description_edit.hasFocus()
    assert row.description_edit.text() == "晚饭" and row.amount_edit.text() == "28.50"
    assert row.time_edit.dateTime().toString("yyyy-MM-dd HH:mm") == "2026-09-20 18:42"
    assert row.category_box.currentText() == "生活"
    assert row.time.isHidden() and not row.time_edit.isHidden()
    assert not row.edge.isHidden() and row.edge.span() == EDGE_COLLAPSED
    assert row.graphicsEffect() is None  # no shadow, nothing floats
    assert page.rows()[1].edge.isHidden()  # only the edited row shows the edge


def test_enter_commits_and_leaves_edit(page, qtbot, database):
    row = page.rows()[0]
    click(qtbot, row, "amount")
    assert row.amount_edit.hasFocus()
    row.amount_edit.selectAll()
    qtbot.keyClicks(row.amount_edit, "30")
    qtbot.keyClick(row.amount_edit, Qt.Key.Key_Return)
    assert not row.editing and page.editing_row is None
    assert database.get_record(row.record["id"])["amount_cents"] == 3000
    assert row.amount.text() == "¥30.00" and not row.amount.isHidden() and row.amount_unit.isHidden()
    assert page.summary.total.text() == "125.00"
    assert page.summary.lines["生活"].amount.text() == "¥30.00"


def test_leaving_a_field_applies_it_while_editing_continues(page, qtbot, database):
    row = page.rows()[0]
    click(qtbot, row, "description")
    row.description_edit.setText("夜宵")
    qtbot.keyClick(row.description_edit, Qt.Key.Key_Tab)
    assert row.editing
    assert database.get_record(row.record["id"])["description"] == "夜宵"
    assert row.description.full_text() == "夜宵"
    assert row.time_edit.hasFocus()


def test_intermediate_amount_is_forgiven_on_enter(page, qtbot, database):
    row = page.rows()[0]
    click(qtbot, row, "amount")
    row.amount_edit.setText("5.")
    qtbot.keyClick(row.amount_edit, Qt.Key.Key_Return)
    assert not row.editing
    assert database.get_record(row.record["id"])["amount_cents"] == 500


def test_invalid_amount_blocks_leaving_until_fixed_or_cancelled(page, qtbot, database):
    row = page.rows()[0]
    click(qtbot, row, "amount")
    row.amount_edit.setText("0")
    qtbot.keyClick(row.amount_edit, Qt.Key.Key_Return)
    assert row.editing and row.hint.isVisibleTo(row) and "金额" in row.hint.text()
    assert database.get_record(row.record["id"])["amount_cents"] == 2850
    press_outside(page)
    assert row.editing and page.editing_row is row  # the click was swallowed
    click(qtbot, page.rows()[1], "description")
    assert page.editing_row is row and not page.rows()[1].editing
    page.change_month(-1)
    assert (page.year, page.month) == (2026, 9)
    assert not page.window().switch_to(CAPTURE) and page.window().current_index() == REVIEW
    qtbot.keyClick(row.amount_edit, Qt.Key.Key_Escape)
    assert not row.editing and page.editing_row is None
    assert database.get_record(row.record["id"])["amount_cents"] == 2850
    assert row.amount.text() == "¥28.50" and row.hint.isHidden()


def test_write_failure_keeps_the_edit_open_and_the_record_unchanged(page, qtbot, database, monkeypatch):
    row = page.rows()[0]
    click(qtbot, row, "amount")
    row.amount_edit.setText("8.88")

    def fail(*args, **kwargs):
        raise DatabaseError("无法保存")
    monkeypatch.setattr(database, "update_record", fail)
    qtbot.keyClick(row.amount_edit, Qt.Key.Key_Return)
    assert row.editing and "保持原样" in row.hint.text()
    assert database.get_record(row.record["id"])["amount_cents"] == 2850
    monkeypatch.undo()
    qtbot.keyClick(row.amount_edit, Qt.Key.Key_Return)
    assert not row.editing and database.get_record(row.record["id"])["amount_cents"] == 888


def test_click_outside_or_another_row_moves_the_edit(page, qtbot):
    first, second = page.rows()[0], page.rows()[1]
    click(qtbot, first, "description")
    click(qtbot, second, "amount")
    assert not first.editing and second.editing and page.editing_row is second
    assert second.amount_edit.hasFocus()
    press_outside(page)
    assert not second.editing and page.editing_row is None


def test_category_changes_at_once_including_back_to_unknown(page, qtbot, database):
    row = page.rows()[2]
    assert row.category_name.text() == "娱乐"  # derived, not stored
    assert database.get_record(row.record["id"])["category"] is None
    click(qtbot, row, "category")
    row.category_box.setCurrentText("生活")
    assert database.get_record(row.record["id"])["category"] == "生活"
    assert page.summary.lines["生活"].amount.text() == "¥64.50"
    assert page.summary.unknown_note.text() == ""
    row.category_box.setCurrentText("暂未判断")
    stored = database.get_record(row.record["id"])
    assert (stored["category"], stored["category_by_user"]) == (None, 1)  # the person's choice, kept
    assert page.summary.unknown_note.text() == "另有 ¥36.00 尚未分类"
    qtbot.keyClick(row.category_box, Qt.Key.Key_Return)
    assert not row.editing and row.category_name.text() == "暂未判断" and row.category_dot.isHidden()
    page.refresh()
    assert page.rows()[2].category_name.text() == "暂未判断"  # not re-derived as 娱乐


def test_a_correction_rereads_the_other_rows_in_place(page, qtbot, database):
    database.add_record(1500, datetime(2026, 9, 18, 12, 0), None, "蜜雪冰城")
    database.add_record(1600, datetime(2026, 9, 17, 12, 0), None, "蜜雪冰城")
    page.refresh()
    first, second = page.rows()[3], page.rows()[4]
    assert first.category_name.text() == second.category_name.text() == "暂未判断"
    click(qtbot, first, "category")
    first.category_box.setCurrentText("娱乐")
    assert second.category_name.text() == "娱乐" and not second.category_dot.isHidden()
    assert page.summary.lines["娱乐"].amount.text() == "¥67.00"
    assert second in page.rows()  # updated in place, not rebuilt


def test_edit_time_across_month_moves_the_record(page, qtbot, database):
    row = page.rows()[1]
    click(qtbot, row, "time")
    assert row.time_edit.hasFocus()  # focused: the full date is shown and any date may be entered
    row.time_edit.setDateTime(datetime(2026, 10, 1, 0, 0))
    row.time_edit.editingFinished.emit()
    assert row.editing  # still editing; the summary is already honest
    assert page.summary.total.text() == "64.50"
    assert database.get_record(row.record["id"])["datetime"] == "2026-10-01 00:00"
    press_outside(page)
    assert page.editing_row is None
    assert [r.record["description"] for r in page.rows()] == ["晚饭", "电影"]
    assert database.get_month_statistics(2026, 10)["工具"] == 5900


def test_delete_edge_arms_on_approach_and_deletes_with_undo(page, qtbot, database):
    row = page.rows()[1]
    click(qtbot, row, "description")
    edge = row.edge
    edge.enterEvent(None)
    qtbot.waitUntil(lambda: edge.span() == EDGE_EXPANDED, timeout=1000)
    assert edge.armed()
    edge.leaveEvent(None)
    qtbot.waitUntil(lambda: edge.span() == EDGE_COLLAPSED, timeout=1000)
    assert not edge.armed()
    record_id = row.record["id"]
    scroll_before = page.scroll.verticalScrollBar().value()
    qtbot.mouseClick(edge, Qt.MouseButton.LeftButton, pos=QPoint(edge.width() - 2, edge.height() // 2))
    assert [r.record["description"] for r in page.rows()] == ["晚饭", "电影"]
    assert page.editing_row is None
    assert page.summary.total.text() == "64.50"
    assert [cents for _, cents in page.summary.donut.segments] == [2850, 3600]
    window = page.window()
    assert window.toast.label.text() == "已删除 ¥59.00 · ChatGPT" and window.toast.can_undo()
    with pytest.raises(DatabaseError):
        database.get_record(record_id)
    qtbot.mouseClick(window.toast.undo_button, Qt.MouseButton.LeftButton)
    assert [r.record["description"] for r in page.rows()] == ["晚饭", "ChatGPT", "电影"]
    assert page.rows()[1].record["id"] == record_id
    assert page.summary.total.text() == "123.50"
    assert page.editing_row is None and not window.toast.isVisible()
    assert page.scroll.verticalScrollBar().value() == scroll_before


def test_failed_delete_keeps_the_record_and_the_totals(page, qtbot, database, monkeypatch):
    row = page.rows()[0]
    click(qtbot, row, "description")

    def fail(*args):
        raise DatabaseError("测试锁库")
    monkeypatch.setattr(database, "delete_record", fail)
    qtbot.mouseClick(row.edge, Qt.MouseButton.LeftButton)
    assert len(page.rows()) == 3 and page.summary.total.text() == "123.50"
    window = page.window()
    assert "仍然保留" in window.toast.label.text() and not window.toast.can_undo()
    assert row.editing  # the context is kept


def test_delete_key_only_acts_on_a_selected_record(page, qtbot, database):
    row = page.rows()[0]
    click(qtbot, row, "description")
    qtbot.keyClick(row.description_edit, Qt.Key.Key_Delete)  # text editing wins inside a field
    assert len(page.rows()) == 3 and row.editing
    click(qtbot, row)  # empty part of the row: the record itself is selected
    assert row.hasFocus()
    qtbot.keyClick(row, Qt.Key.Key_Delete)
    assert [r.record["description"] for r in page.rows()] == ["ChatGPT", "电影"]
    assert page.window().toast.can_undo()
    # Browse state: Delete with nothing selected does nothing.
    qtbot.keyClick(page, Qt.Key.Key_Delete)
    assert len(page.rows()) == 2


def test_undo_delete_returns_to_browse_and_a_new_toast_expires_the_old_undo(page, qtbot, database):
    first = page.rows()[0]
    click(qtbot, first, "description")
    qtbot.mouseClick(first.edge, Qt.MouseButton.LeftButton)
    window = page.window()
    click(qtbot, page.rows()[0], "description")
    qtbot.mouseClick(page.rows()[0].edge, Qt.MouseButton.LeftButton)
    assert len(page.rows()) == 1 and window.toast.label.text() == "已删除 ¥59.00 · ChatGPT"
    qtbot.mouseClick(window.toast.undo_button, Qt.MouseButton.LeftButton)
    assert [r.record["description"] for r in page.rows()] == ["ChatGPT", "电影"]  # only the last delete is undone
    assert page.editing_row is None


def test_escape_from_the_page_cancels_the_edit(page, qtbot):
    row = page.rows()[0]
    click(qtbot, row)
    row.amount_edit.setText("-")
    qtbot.keyClick(row, Qt.Key.Key_Escape)
    assert not row.editing and row.amount.text() == "¥28.50"


def settled_geometry(page, row, qtbot):
    """Force the lazy layout passes to finish (Qt applies nested LayoutRequests one loop turn at a time)."""
    page.history.layout().activate()
    qtbot.wait(20)
    page.history.layout().activate()
    return (row.height(), row.y(), page.rows()[1].y())


def test_edit_keeps_the_row_height_and_reads_as_the_same_record(page, qtbot):
    row = page.rows()[0]
    before = settled_geometry(page, row, qtbot)
    click(qtbot, row, "description")
    assert settled_geometry(page, row, qtbot) == before  # entering Edit moves nothing
    # Fields read as text. Nothing is underlined at rest, and the focused field's line is
    # as wide as its own text — never the width of the row. ¥ stays a fixed prefix.
    assert row.amount_currency.text() == "¥" and row.amount_edit.text() == "28.50"
    assert row.description_edit.hasFocus()
    assert row.description_edit.underline_rect().width() < row.description_edit.width() / 2
    assert row.amount_edit._focus.value() == 0.0  # an unfocused field draws nothing at all
    assert row.time_edit.displayFormat() == "HH:mm" and row.time_edit.text() == "18:42"
    assert row.edge.span() == EDGE_COLLAPSED and EDGE_COLLAPSED <= 3
    qtbot.keyClick(row.description_edit, Qt.Key.Key_Escape)
    assert settled_geometry(page, row, qtbot) == before


def test_the_amount_is_opened_whole_mark_and_caret_included(page, qtbot):
    """Edit shows the amount the record showed: ¥ keeps its full advance instead of being
    cut to make room, and the caret after the last digit is drawn inside the field."""
    row = page.rows()[0]
    click(qtbot, row, "amount")
    editor = row.amount_edit
    assert editor.hasFocus() and editor.cursorPosition() == len(editor.text())
    assert editor.cursorRect().center().x() < editor.width()
    assert row.amount_currency.width() == QFontMetrics(row.amount_currency.font()).horizontalAdvance("¥")
    # Rest and Edit end the value column on the same line.
    assert (row.amount_unit.geometry().right() == row.amount.geometry().right()
            == row.category.geometry().right() == row.category_box.geometry().right())


def test_time_shows_the_short_form_and_the_full_date_only_while_focused(page, qtbot, database):
    row = page.rows()[0]
    click(qtbot, row, "description")
    assert row.time_edit.text() == "18:42"
    row.time_edit.setFocus()
    assert row.time_edit.displayFormat() == "yyyy-MM-dd HH:mm"
    assert row.time_edit.text() == "2026-09-20 18:42"  # the date is still there and editable
    row.time_edit.setDateTime(datetime(2026, 9, 19, 9, 5))
    row.description_edit.setFocus()  # leaving the field commits it and returns to the short form
    assert row.time_edit.displayFormat() == "HH:mm" and row.time_edit.text() == "09:05"
    assert database.get_record(row.record["id"])["datetime"] == "2026-09-19 09:05"
    press_outside(page)
    assert page.editing_row is None
    assert [r.record["description"] for r in page.rows()][-1] == "晚饭"  # re-sorted into 9月19日
