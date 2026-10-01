from datetime import datetime
import json
import pytest
from PySide6.QtCore import Qt
from database import DatabaseError
from draft import Draft, DraftStore
from ui.main_window import MainWindow


@pytest.fixture
def window(qtbot, database, tmp_path):
    window = MainWindow(database, tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def test_selection_save_learning_undo_and_next_input(window, database, qtbot):
    c = window.capture
    # Warm classification before the new user label arrives.
    window.ledger.classifier()
    c.amount.setText("9")
    c.description.setText("专属用途例子")
    qtbot.mouseClick(c.category_buttons["娱乐"], Qt.MouseButton.LeftButton)
    c.record()
    record = database.get_records_by_month(datetime.now().year, datetime.now().month)[0]
    assert record["category"] == "娱乐" and record["category_by_user"] == 1
    assert window.ledger.classifier().classify("专属用途例子") == "娱乐"
    assert c.selected_category is None
    window.toast._run_undo()
    assert c.selected_category == "娱乐" and c.description.text() == "专属用途例子"
    assert window.ledger.classifier().classify("专属用途例子") is None
    c.record()
    c.select_category("工具")
    window.toast._run_undo()
    assert c.selected_category == "工具" and c.amount.text() == ""


def test_toggle_auto_and_failure_preserve_category(window, database, monkeypatch):
    c = window.capture
    c.select_category("生活")
    c.select_category("生活")
    assert c.selected_category is None and not any(b.isChecked() for b in c.category_buttons.values())
    c.amount.setText("6")
    c.record()
    record = database.get_records_by_month(datetime.now().year, datetime.now().month)[0]
    assert record["category"] is None and record["category_by_user"] == 0
    c.amount.setText("8")
    c.select_category("工具")
    def fail(*args, **kwargs):
        raise DatabaseError("synthetic failure")
    monkeypatch.setattr(window.ledger, "create", fail)
    c.record()
    assert c.selected_category == "工具" and c.amount.text() == "8"


def test_category_only_draft_and_legacy(tmp_path):
    store = DraftStore(tmp_path)
    assert store.save(Draft(category="生活"))
    assert store.load() == Draft(category="生活")
    store.path.write_text(json.dumps({"amount_text": "12", "description": "old"}))
    assert store.load() == Draft("12", "old")
    store.path.write_text(json.dumps({"amount_text": "12", "category": ["invalid"]}))
    assert store.load() == Draft("12")


def test_legacy_background_is_ignored_and_preserved(database, tmp_path, qtbot):
    legacy = tmp_path / "appearance-background.png"
    original = b"synthetic legacy file; deliberately not a valid image"
    legacy.write_bytes(original)
    window = MainWindow(database, tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    assert window.centralWidget().objectName() == "space"
    assert [a.text() for a in window.utility_menu.actions() if not a.isSeparator()] == [
        "打开数据目录", "备份账本…", "关于 Cashing"]
    window.capture.amount.setText("12")
    window.capture.select_category("生活")
    window.capture.record()
    window.close()
    assert legacy.read_bytes() == original
    record = database.get_records_by_month(datetime.now().year, datetime.now().month)[0]
    assert record["amount_cents"] == 1200 and record["category"] == "生活"


def test_icon_and_small_window(window, qtbot):
    window.resize(640, 440)
    qtbot.wait(80)
    assert not window.windowIcon().isNull()
    for button in window.capture.category_buttons.values():
        window.capture.scroll.ensureWidgetVisible(button)
        qtbot.wait(10)
        assert button.isVisible() and button.width() >= 60
