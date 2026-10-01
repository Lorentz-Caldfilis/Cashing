from datetime import datetime
import json
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from database import DatabaseError
from draft import Draft, DraftStore
from ledger import Ledger
from ui.background import BackgroundStore, read_image
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


def test_background_copy_restart_reset_and_bad_replacement(tmp_path):
    source = tmp_path / "source.png"
    image = QImage(40, 30, QImage.Format.Format_ARGB32)
    image.fill(QColor("#243f78"))
    assert image.save(str(source))
    store = BackgroundStore(tmp_path / "data")
    store.import_image(source)
    original = store.path.read_bytes()
    source.unlink()
    assert BackgroundStore(store.path.parent).load().pixelColor(0, 0) == QColor("#243f78")
    invalid = tmp_path / "invalid.png"
    invalid.write_bytes(b"invalid")
    with pytest.raises(ValueError):
        store.import_image(invalid)
    assert store.path.read_bytes() == original
    store.reset()
    assert store.load().isNull()
    store.path.write_bytes(b"corrupt stored file")
    assert store.load().isNull()


def test_image_size_limit_and_menu_cancel(window, tmp_path, monkeypatch):
    from ui import background
    from PySide6.QtWidgets import QFileDialog
    source = tmp_path / "large.png"
    image = QImage(20, 20, QImage.Format.Format_RGB32)
    image.fill(QColor("black"))
    image.save(str(source))
    monkeypatch.setattr(background, "MAX_PIXELS", 100)
    with pytest.raises(ValueError, match="像素"):
        read_image(source)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a: ("", ""))
    window.choose_background()
    assert window.centralWidget().image.isNull()
    assert not window.background_store.path.exists()


def test_reading_surface_and_icon_and_small_window(window, qtbot):
    image = QImage(60, 40, QImage.Format.Format_RGB32)
    image.fill(QColor("black"))
    window._apply_background(image)
    window.resize(640, 440)
    qtbot.wait(80)
    canvas = window.centralWidget()
    pixel = canvas.grab().toImage().pixelColor(canvas.width() // 2, 105)
    assert min(pixel.red(), pixel.green(), pixel.blue()) >= 220
    assert not window.windowIcon().isNull()
    for button in window.capture.category_buttons.values():
        window.capture.scroll.ensureWidgetVisible(button)
        qtbot.wait(10)
        assert button.isVisible() and button.width() >= 60
