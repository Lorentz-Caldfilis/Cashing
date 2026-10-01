"""Capture: keyboard path, local errors, write-before-clear, undo restores input, draft."""
from datetime import datetime
import socket
import pytest
from PySide6.QtCore import Qt
from database import DatabaseError
from draft import DraftStore
from ui.main_window import MainWindow


@pytest.fixture
def window(qtbot, database, tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("核心功能不应访问网络")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    widget = MainWindow(database, tmp_path)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def stored(database):
    now = datetime.now()
    return database.get_records_by_month(now.year, now.month)


def test_startup_focus_is_the_amount(window):
    assert window.current_index() == 0
    assert window.capture.amount.hasFocus()
    assert not window.capture.record_button.isEnabled()


def test_empty_amount_shows_a_placeholder_that_is_never_a_value(window, qtbot, database):
    capture = window.capture
    assert capture.amount.text() == "" and capture.amount.placeholderText() == "0.00"
    assert not capture.record_button.isEnabled()
    capture.record()
    assert stored(database) == [] and not window.toast.isVisible()
    qtbot.keyClicks(capture.amount, "28.5")
    assert capture.amount.text() == "28.5"


def test_enter_path_amount_then_description_then_record(window, qtbot, database):
    capture = window.capture
    qtbot.keyClicks(capture.amount, "28.5")
    assert capture.amount.text() == "28.5"  # no live reformatting while typing
    assert capture.record_button.isEnabled()
    qtbot.keyClick(capture.amount, Qt.Key.Key_Return)
    assert capture.description.hasFocus()
    capture.description.setText("晚饭")
    qtbot.keyClick(capture.description, Qt.Key.Key_Return)
    records = stored(database)
    assert [(r["amount_cents"], r["description"], r["category"]) for r in records] == [(2850, "晚饭", None)]
    assert capture.amount.text() == "" and capture.description.text() == ""
    assert capture.amount.hasFocus()
    assert capture.time_is_auto()
    assert window.current_index() == 0  # stays in Capture
    assert window.toast.isVisible() and window.toast.label.text() == "已记录 ¥28.50 · 晚饭"
    assert window.toast.can_undo()


def test_empty_description_still_records(window, qtbot, database):
    capture = window.capture
    qtbot.keyClicks(capture.amount, "12")
    qtbot.keyClick(capture.amount, Qt.Key.Key_Return)
    qtbot.keyClick(capture.description, Qt.Key.Key_Return)
    assert [(r["amount_cents"], r["description"]) for r in stored(database)] == [(1200, "")]
    assert window.toast.label.text() == "已记录 ¥12.00"


def test_focus_out_formats_the_amount_statically(window, qtbot):
    capture = window.capture
    qtbot.keyClicks(capture.amount, "28.5")
    capture.description.setFocus()
    assert capture.amount.text() == "28.50"
    capture.amount.setFocus()
    capture.amount.setText(".5")
    capture.description.setFocus()
    assert capture.amount.text() == "0.50"
    capture.amount.setFocus()
    capture.amount.setText("7.")
    capture.description.setFocus()
    assert capture.amount.text() == "7.00"


@pytest.mark.parametrize("text", ["0", "0.00", "."])
def test_invalid_amount_is_explained_next_to_the_amount(window, qtbot, database, text):
    capture = window.capture
    capture.amount.setText(text)
    qtbot.keyClick(capture.amount, Qt.Key.Key_Return)
    assert capture.amount_error.text()
    assert capture.amount.hasFocus()
    capture.description.setText("x")
    capture.record()
    assert stored(database) == []
    assert capture.amount_error.text() and capture.amount.hasFocus()
    assert capture.save_error.text() == ""
    capture.amount.setText("1")
    assert capture.amount_error.text() == ""  # typing again clears the local hint


def test_tab_keeps_native_focus_order(window, qtbot):
    capture = window.capture
    qtbot.keyClicks(capture.amount, "5")
    qtbot.keyClick(capture.amount, Qt.Key.Key_Tab)
    assert capture.description.hasFocus()
    qtbot.keyClick(capture.description, Qt.Key.Key_Tab)
    assert capture.time_button.hasFocus()
    qtbot.keyClick(capture.time_button, Qt.Key.Key_Tab)
    for button in capture.category_buttons.values():
        assert button.hasFocus()
        qtbot.keyClick(button, Qt.Key.Key_Tab)
    assert capture.record_button.hasFocus()


def test_write_failure_keeps_every_input(window, qtbot, database, monkeypatch):
    capture = window.capture
    capture.amount.setText("28.50")
    capture.description.setText("晚饭")
    capture.set_time(datetime(2026, 9, 19, 22, 15))

    def fail(*args, **kwargs):
        raise DatabaseError("测试：磁盘不可写")
    monkeypatch.setattr(window.ledger, "create", fail)
    capture.record()
    assert capture.amount.text() == "28.50" and capture.description.text() == "晚饭"
    assert capture.current_time() == datetime(2026, 9, 19, 22, 15)
    assert capture.save_error.text() == "无法保存，这笔记录尚未写入。"
    assert "磁盘不可写" in capture.save_error_detail.toPlainText()
    assert not window.toast.isVisible()
    assert stored(database) == []
    capture.description.setText("晚饭 2")
    assert capture.save_error.text() == ""


def test_undo_deletes_the_record_and_restores_the_input(window, qtbot, database):
    capture = window.capture
    capture.amount.setText("28.5")
    capture.description.setText("晚饭")
    capture.set_time(datetime(2026, 9, 19, 22, 15))
    capture.record()
    assert len(database.get_records_by_month(2026, 9)) == 1
    assert capture.amount.text() == ""
    qtbot.mouseClick(window.toast.undo_button, Qt.MouseButton.LeftButton)
    assert database.get_records_by_month(2026, 9) == []
    assert capture.amount.text() == "28.5"
    assert capture.description.text() == "晚饭"
    assert capture.current_time() == datetime(2026, 9, 19, 22, 15)
    assert capture.amount.hasFocus()
    assert not window.toast.isVisible()


def test_undo_failure_reports_and_keeps_the_record(window, qtbot, database, monkeypatch):
    capture = window.capture
    capture.amount.setText("28.5")
    capture.record()
    monkeypatch.setattr(window.ledger, "undo_create", lambda rid: (_ for _ in ()).throw(DatabaseError("锁库")))
    qtbot.mouseClick(window.toast.undo_button, Qt.MouseButton.LeftButton)
    assert len(stored(database)) == 1
    assert capture.amount.text() == ""
    assert window.toast.isVisible() and "仍然保留" in window.toast.label.text()
    assert not window.toast.can_undo()


def test_a_new_toast_expires_the_previous_undo(window, database):
    capture = window.capture
    capture.amount.setText("1")
    capture.record()
    first_undo = window.toast._action
    capture.amount.setText("2")
    capture.record()
    assert window.toast._action is not first_undo and len(stored(database)) == 2
    window.toast.dismiss()
    assert not window.toast.can_undo()


def test_time_editor_changes_only_the_pending_record(window, qtbot):
    capture = window.capture
    assert capture.time_button.text().startswith("今天 ")
    capture.popover.changed.emit(datetime(2026, 9, 19, 22, 15))
    assert not capture.time_is_auto()
    assert capture.time_button.text().startswith("9月19日 22:15") or capture.time_button.text().startswith("昨天 22:15") \
        or capture.time_button.text().startswith("2026年9月19日 22:15")
    capture.popover.reset.emit()
    assert capture.time_is_auto() and capture.time_button.text().startswith("今天 ")


def test_unsaved_input_survives_a_page_switch(window):
    capture = window.capture
    capture.amount.setText("28.5")
    capture.description.setText("晚饭")
    window.switch_to(1)
    assert window.current_index() == 1
    window.switch_to(0)
    # Leaving the field formatted the amount statically; nothing was saved or cleared.
    assert capture.amount.text() == "28.50" and capture.description.text() == "晚饭"
    assert capture.description.hasFocus()  # the amount is already there: continue with the description


def test_draft_is_kept_across_restart_and_never_counted(qtbot, database, tmp_path):
    first = MainWindow(database, tmp_path)
    qtbot.addWidget(first)
    first.show()
    first.capture.amount.setText("28.5")
    first.capture.description.setText("晚饭")
    first.capture.set_time(datetime(2026, 9, 19, 22, 15))
    first.close()
    assert DraftStore(tmp_path).load() is not None
    assert database.get_month_statistics(2026, 9)["total"] == 0
    second = MainWindow(database, tmp_path)
    qtbot.addWidget(second)
    second.show()
    assert second.capture.amount.text() == "28.5"
    assert second.capture.description.text() == "晚饭"
    assert second.capture.current_time() == datetime(2026, 9, 19, 22, 15)
    second.capture.record()
    second.close()
    assert DraftStore(tmp_path).load() is None
    assert database.get_month_statistics(2026, 9)["total"] == 2850


def test_empty_capture_leaves_no_draft(qtbot, database, tmp_path):
    window = MainWindow(database, tmp_path)
    qtbot.addWidget(window)
    window.show()
    window.close()
    assert DraftStore(tmp_path).load() is None and not DraftStore(tmp_path).path.exists()


def test_no_brand_or_navigation_text_inside_the_capture_space(window):
    texts = {label.text() for label in window.capture.findChildren(type(window.capture.amount_error))}
    assert not any(t for t in texts if "Cashing" in t or "记账" in t or "Capture" in t)
    assert window.windowTitle() == "Cashing"


def test_time_layer_speaks_the_app_date_language_and_returns_focus(window, qtbot):
    capture = window.capture
    capture.amount.setFocus()
    qtbot.mouseClick(capture.time_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(capture.popover.isVisible, timeout=1000)
    capture.popover.edit.setDateTime(datetime(2026, 9, 19, 22, 15))
    assert capture.popover.edit.text() == "2026年9月19日 22:15"
    capture.popover.close()
    qtbot.wait(20)
    assert not capture.time_button.hasFocus()  # no frame left around the time
    assert capture.time_button.focusPolicy() == Qt.FocusPolicy.TabFocus


def test_the_toast_leaves_the_way_it_came_in(window, qtbot):
    from ui import motion
    capture = window.capture
    capture.amount.setText("1")
    capture.record()
    toast = window.toast
    assert toast.can_undo()
    toast.dismiss()
    assert not toast.can_undo()  # the offer ends at once
    if motion.ENABLED:
        assert toast.isVisible()  # the surface fades out rather than blinking away
    qtbot.waitUntil(lambda: not toast.isVisible(), timeout=2000)


def test_undo_preserves_the_next_pending_record(window, database):
    capture = window.capture
    capture.amount.setText("12")
    capture.description.setText("食堂")
    capture.record()
    capture.amount.setText("18")
    capture.description.setText("打印资料")
    capture.set_time(datetime(2026, 9, 28, 9, 0))
    pending = capture.draft()
    window.toast._run_undo()
    assert stored(database) == []
    assert capture.draft() == pending
    assert "已保留" in window.toast.label.text()


def test_draft_is_saved_while_window_is_open(window, qtbot, tmp_path):
    capture = window.capture
    capture.amount.setText("15")
    capture.description.setText("合成草稿")
    capture.set_time(datetime(2026, 9, 28, 9, 0))
    qtbot.waitUntil(lambda: DraftStore(tmp_path).load() == capture.draft(), timeout=2000)
    capture.record()
    assert DraftStore(tmp_path).load() is None


def test_failed_draft_write_keeps_window_open(window, monkeypatch):
    window.capture.amount.setText("20")
    monkeypatch.setattr(window.drafts, "save", lambda draft: False)
    window.close()
    assert window.isVisible()
    assert window.capture.amount.text() == "20"
    assert "草稿未能保存" in window.toast.label.text()
    monkeypatch.undo()


def test_long_notification_fits_window_and_keyboard_undo_works(window, qtbot, database):
    capture = window.capture
    capture.amount.setText("12")
    capture.description.setText("合成说明" * 50)
    capture.record()
    assert window.toast.width() <= window.centralWidget().width()
    qtbot.keyClick(capture.amount, Qt.Key.Key_Z,
                   Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)
    assert stored(database) == []
    assert capture.description.text() == "合成说明" * 50


def test_paste_expense_is_reviewable_and_never_overwrites_description(window, qtbot, database):
    from PySide6.QtWidgets import QApplication
    capture = window.capture
    QApplication.clipboard().setText("￥２８．５０ 食堂午饭")
    qtbot.keyClick(capture.amount, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    assert capture.amount.text() == "28.50"
    assert capture.description.text() == "食堂午饭"
    assert stored(database) == []
    capture.amount.selectAll()
    QApplication.clipboard().setText("12 打印")
    qtbot.keyClick(capture.amount, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    assert capture.description.text() == "食堂午饭"
    assert capture.amount.text() == "28.50"
    assert "说明已有内容" in capture.amount_error.text()


def test_long_storage_error_remains_readable_in_small_window(window, qtbot, monkeypatch):
    window.resize(680, 440)
    capture = window.capture
    detail = "合成磁盘错误，请检查目录权限。" * 100
    def fail(*args, **kwargs):
        raise DatabaseError(detail)
    monkeypatch.setattr(window.ledger, "create", fail)
    capture.amount.setText("18.50")
    capture.description.setText("合成午饭")
    capture.record()
    qtbot.wait(40)
    assert window.size().width() == 680 and window.size().height() == 440
    assert capture.amount.height() >= capture.amount.sizeHint().height()
    assert capture.save_error_detail.toPlainText() == detail
    assert capture.save_error_detail.verticalScrollBar().maximum() > 0
    top = capture.save_error_detail.mapTo(capture.scroll.viewport(), capture.save_error_detail.rect().topLeft()).y()
    assert 0 <= top < capture.scroll.viewport().height()
    assert capture.amount.text() == "18.50" and capture.description.text() == "合成午饭"
