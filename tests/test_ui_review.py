"""Review: month context, totals that always add up, one restrained ring, history by day."""
import gc
import weakref
from datetime import datetime
import pytest
from PySide6.QtCore import Qt, QCoreApplication, QEvent, QPoint
from database import DatabaseError
from domain import CATEGORIES
from ui.main_window import MainWindow, REVIEW
from ui.review_page import RecordRow, DonutChart, DayHeading, MEASURE
from ui.record_row import VALUE_TAIL, CARET_ROOM


@pytest.fixture
def window(qtbot, database, tmp_path):
    widget = MainWindow(database, tmp_path)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def september(page):
    page.year, page.month = 2026, 9
    page.refresh()


def labels(page):
    return [(row.time.text(), row.amount.text(), row.description.full_text(), row.category_name.text())
            for row in page.rows()]


def test_summary_ring_history_and_month_bounds(window, qtbot, database):
    for category in CATEGORIES:
        database.add_record(2850, datetime(2026, 9, 19, 22, 15), category, "晚饭")
    window.switch_to(REVIEW, animate=False)
    page = window.review
    september(page)
    assert page.month_label.text() == "2026年9月"
    assert page.summary.total.text() == "85.50" and page.summary.currency.text() == "¥"
    assert [page.summary.lines[c].amount.text() for c in CATEGORIES] == ["¥28.50", "¥28.50", "¥28.50"]
    assert page.summary.unknown_note.text() == ""  # its line is reserved, but says nothing
    assert [cents for _, cents in page.summary.donut.segments] == [2850, 2850, 2850]
    assert not page.summary.empty.isVisible() and page.summary.structure.isVisible()
    assert len(page.rows()) == 3
    assert page.summary.donut.isVisible()
    page.change_month(-1)
    assert page.month_label.text() == "2026年8月"
    assert page.rows() == [] and page.summary.total.text() == "0.00"
    assert page.summary.empty.isVisible() and not page.summary.structure.isVisible()
    assert page.summary.donut.segments == []
    page.year, page.month = 2025, 12
    page.change_month(1)
    assert (page.year, page.month) == (2026, 1)
    page.change_month(-1)
    assert (page.year, page.month) == (2025, 12)
    page.year, page.month = 1900, 1
    page.refresh()
    assert not page.previous.isEnabled()
    page.change_month(-1)
    assert (page.year, page.month) == (1900, 1)


def test_no_future_month_and_label_returns_to_now(window):
    page = window.review
    now = datetime.now()
    assert (page.year, page.month) == (now.year, now.month)
    assert not page.next.isEnabled()
    page.change_month(1)
    assert (page.year, page.month) == (now.year, now.month)
    page.change_month(-3)
    assert page.next.isEnabled()
    page.month_label.click()
    assert (page.year, page.month) == (now.year, now.month) and not page.next.isEnabled()


def test_month_switch_replaces_everything_at_once(window, database):
    database.add_record(1000, datetime(2026, 9, 2, 9, 0), "生活", "九月")
    database.add_record(2000, datetime(2026, 8, 2, 9, 0), "工具", "八月")
    page = window.review
    september(page)
    assert labels(page) == [("09:00", "¥10.00", "九月", "生活")]
    page.change_month(-1)
    # Immediately after the switch: no stale September row anywhere, not even awaiting deletion.
    assert labels(page) == [("09:00", "¥20.00", "八月", "工具")]
    assert [r.record["description"] for r in page.history.findChildren(RecordRow)] == ["八月"]
    assert page.summary.total.text() == "20.00"
    assert [cents for _, cents in page.summary.donut.segments] == [2000]
    assert page.summary.lines["工具"].amount.text() == "¥20.00" and page.summary.lines["生活"].amount.text() == "¥0.00"


def test_unknown_amounts_count_in_the_total_but_never_as_a_fourth_category(window, database):
    database.add_record(1200, datetime(2026, 9, 20, 12, 0), None, "未知")
    database.add_record(800, datetime(2026, 9, 20, 13, 0), "生活", "午饭")
    page = window.review
    september(page)
    assert page.summary.total.text() == "20.00"
    assert page.summary.lines["生活"].amount.text() == "¥8.00"
    assert page.summary.unknown_note.text() == "另有 ¥12.00 尚未分类"
    assert len(page.summary.lines) == 3  # the three core categories only
    # The ring shows the unjudged share only as a neutral sliver, in last place.
    assert [cents for _, cents in page.summary.donut.segments] == [800, 1200]
    rows = page.rows()
    assert rows[0].category_name.text() == "生活" and not rows[0].category_dot.isHidden()
    assert rows[1].category_name.text() == "" and rows[1].category_dot.isHidden()


def test_no_ring_without_a_classified_proportion(window, database):
    """Nothing judged yet is not a proportion: the ring disappears instead of
    drawing a grey circle, while the total and the history stay complete."""
    database.add_record(1200, datetime(2026, 9, 20, 12, 0), None, "未知 A")
    database.add_record(800, datetime(2026, 9, 20, 13, 0), None, "未知 B")
    page = window.review
    september(page)
    assert page.summary.total.text() == "20.00"
    assert page.summary.donut.segments == [] and page.summary.donut.isHidden()
    assert page.summary.unknown_note.text() == "另有 ¥20.00 尚未分类"
    assert len(page.rows()) == 2
    page.rows()[0].begin_edit("category")
    page.rows()[0].category_box.setCurrentText("生活")
    assert not page.summary.donut.isHidden()
    assert [cents for _, cents in page.summary.donut.segments] == [800, 1200]


def x_in(page, widget, x=0):
    """Where x (in the widget) lands in the page's coordinates."""
    return widget.mapTo(page, QPoint(x, 0)).x()


def settle(qtbot, page):
    for _ in range(2):
        page.body_layout.activate()
        qtbot.wait(10)


def test_summary_and_history_hang_off_one_grid(window, qtbot, database):
    """Category names start on the records' text edge, the ring ends on their value edge,
    and the two edges sit evenly about the page's centre line."""
    database.add_record(2850, datetime(2026, 9, 20, 18, 42), "生活", "晚饭")
    database.add_record(5900, datetime(2026, 9, 20, 15, 17), "工具", "ChatGPT")
    page = window.review
    september(page)
    settle(qtbot, page)
    row = page.rows()[0]
    text_edge = x_in(page, row.description)
    value_edge = x_in(page, row, row.width() - VALUE_TAIL)
    assert value_edge - text_edge == MEASURE  # one record is read across a short measure
    assert x_in(page, row.amount, row.amount.width() - CARET_ROOM) == value_edge
    assert [x_in(page, line.name) for line in page.summary.lines.values()] == [text_edge] * 3
    assert x_in(page, page.summary.donut, page.summary.donut.width()) == value_edge
    centre = x_in(page, page.column, page.column.width() // 2)
    assert abs((text_edge + value_edge) / 2 - centre) <= 1


def test_a_month_without_a_ring_keeps_no_room_for_one(window, qtbot, database):
    """Nothing classified: the ring's slot goes too, and the three lines sit on the centre
    line instead of beside an empty space."""
    database.add_record(1200, datetime(2026, 9, 20, 12, 0), None, "未知")
    page = window.review
    september(page)
    settle(qtbot, page)
    assert page.summary.chart_slot.isHidden()
    line = page.summary.lines["生活"]
    words = (x_in(page, line.name) + x_in(page, line.amount, line.amount.width())) / 2
    assert abs(words - x_in(page, page.column, page.column.width() // 2)) <= 1
    page.rows()[0].begin_edit("category")
    page.rows()[0].category_box.setCurrentText("生活")  # a proportion exists: the ring and its room return
    settle(qtbot, page)
    assert not page.summary.chart_slot.isHidden()
    assert x_in(page, line.name) == x_in(page, page.rows()[0].description)


def test_history_is_grouped_by_day_newest_first(window, database):
    database.add_record(2850, datetime(2026, 9, 20, 18, 42), "生活", "晚饭")
    database.add_record(5900, datetime(2026, 9, 20, 15, 17), "工具", "ChatGPT")
    database.add_record(3600, datetime(2026, 9, 19, 21, 3), "娱乐", "电影")
    page = window.review
    september(page)
    headings = [h.text() for h in page.history.findChildren(DayHeading)]
    assert headings == ["9月20日 星期日", "9月19日 星期六"]
    assert labels(page) == [("18:42", "¥28.50", "晚饭", "生活"), ("15:17", "¥59.00", "ChatGPT", "工具"),
                            ("21:03", "¥36.00", "电影", "娱乐")]
    QCoreApplication.processEvents()
    ordered = page.history.findChildren(DayHeading) + page.history.findChildren(RecordRow)
    ordered.sort(key=lambda w: w.mapTo(page.history, QPoint(0, 0)).y())
    assert [type(w).__name__ for w in ordered] == ["DayHeading", "RecordRow", "RecordRow", "DayHeading", "RecordRow"]


def test_long_and_html_like_descriptions_stay_plain_and_available(window, database, qtbot):
    text = "<b>普通文本</b>" + "中" * 185
    database.add_record(1, datetime(2026, 9, 19), "生活", text)
    page = window.review
    september(page)
    row = page.rows()[0]
    assert row.description.full_text() == text
    assert row.description.toolTip() == text
    assert row.description.textFormat() == Qt.TextFormat.PlainText
    window.resize(720, 560)
    qtbot.wait(30)
    window.resize(900, 720)
    qtbot.wait(30)
    assert row.description.full_text() == text
    assert row.height() < 80  # one visual row, never a growing block


def test_empty_description_shows_nothing_extra(window, database):
    database.add_record(1, datetime(2026, 9, 19), "生活", "")
    page = window.review
    september(page)
    assert page.rows()[0].description.full_text() == ""


def test_refresh_reuses_widgets_and_failure_never_looks_empty(window, database, monkeypatch):
    database.add_record(100, datetime(2026, 9, 19), "生活")
    page = window.review
    september(page)
    donut, summary = page.summary.donut, page.summary
    for _ in range(60):
        page.refresh()
    assert page.summary.donut is donut and page.summary is summary
    assert len(page.findChildren(DonutChart)) == 1
    assert len(page.history.findChildren(RecordRow)) == 1

    def fail(*args):
        raise DatabaseError("测试：数据库读取失败")
    monkeypatch.setattr(database, "get_records_by_month", fail)
    page.refresh()
    assert page.rows() == []
    assert page.summary.total.text() == "—"
    assert not page.summary.empty.isVisible()
    assert page.failure.isVisible() and "读取失败" in page.failure.text()
    monkeypatch.undo()
    page.refresh()
    assert not page.failure.isVisible() and page.summary.total.text() == "1.00"


def test_capture_save_shows_up_in_review_without_leaving_capture(window, qtbot, database):
    capture = window.capture
    capture.amount.setText("28.5")
    capture.description.setText("晚饭")
    capture.record()
    assert window.current_index() == 0
    now = datetime.now()
    page = window.review
    assert (page.year, page.month) == (now.year, now.month)
    assert [r.description.full_text() for r in page.rows()] == ["晚饭"]
    for _ in range(8):
        window.switch_to(REVIEW, animate=False)
        window.switch_to(0, animate=False)
    assert len(page.history.findChildren(RecordRow)) == 1
    assert len(window.findChildren(DonutChart)) == 1


def test_widgets_are_destroyed_after_close(database, qtbot):
    window = MainWindow(database)
    window.show()
    QCoreApplication.processEvents()
    donut = weakref.ref(window.review.summary.donut)
    review = weakref.ref(window.review)
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    del window
    gc.collect()
    assert donut() is None
    assert review() is None
