import gc
import weakref
from datetime import datetime
import pytest
from PySide6.QtCore import Qt, QTimer, QCoreApplication, QEvent, QDateTime
from PySide6.QtWidgets import QApplication, QMessageBox, QMenu
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from database import DatabaseError
from ui.main_window import MainWindow
from ui.edit_dialog import EditDialog
from tests.test_ui import fill, september


@pytest.fixture
def window(qtbot,database):
    w=MainWindow(database)
    qtbot.addWidget(w)
    w.show()
    return w


def test_failed_delete_retains_record_and_totals(window,database,qtbot,monkeypatch):
    database.add_record(567,datetime(2026,9,1),"工具")
    p=window.review
    september(p)
    p.table.selectRow(0)
    def answer():
        box=QApplication.activeModalWidget()
        next(b for b in box.buttons() if b.text()=="删除").click()
    def fail(*args):
        raise DatabaseError("测试锁库")
    monkeypatch.setattr(database,"delete_record",fail)
    QTimer.singleShot(20,answer)
    p.delete_selected()
    assert p.table.rowCount()==1 and p.stat_labels["total"].text()=="¥5.67"
    assert "锁库" in p.message.text()


def test_keyboard_flow_and_no_duplicate_signals(window,qtbot,database):
    for _ in range(8):
        window.switch_to(1)
        window.switch_to(0)
    capture=window.capture
    capture.amount.setFocus()
    qtbot.keyClicks(capture.amount,"12.34")
    capture.set_time(datetime(2026,9,19,22,15))
    capture.description.setFocus()
    qtbot.keyClicks(capture.description,"one")
    qtbot.keyClick(capture.description,Qt.Key.Key_Return)
    assert len(database.get_records_by_month(2026,9))==1
    assert capture.amount.hasFocus()
    assert len(window.findChildren(FigureCanvasQTAgg))==1


def test_table_resize_preserves_long_text_visibility(window,database,qtbot):
    database.add_record(1234,datetime(2026,9,1),"生活","很长的中文说明"*24)
    window.switch_to(1)
    september(window.review)
    window.resize(1180,780)
    qtbot.wait(120)
    window.resize(900,600)
    qtbot.wait(160)
    table=window.review.table
    assert table.rowHeight(0)>=table.sizeHintForRow(0)
    table.selectRow(0)
    assert window.review.description.toPlainText()=="很长的中文说明"*24


def test_mouse_double_click_edit_and_cancel(window,database,qtbot):
    database.add_record(1,datetime(2026,9,1),"生活")
    window.switch_to(1)
    p=window.review
    september(p)
    seen=[]
    def reject():
        dialog=QApplication.activeModalWidget()
        seen.append(isinstance(dialog,EditDialog))
        dialog.reject()
    timer=QTimer(window)
    timer.setSingleShot(True)
    timer.timeout.connect(reject)
    qtbot.wait(100)
    rect=p.table.visualItemRect(p.table.item(0,0))
    qtbot.mouseClick(p.table.viewport(),Qt.MouseButton.LeftButton,pos=rect.center())
    timer.start(80)
    qtbot.mouseDClick(p.table.viewport(),Qt.MouseButton.LeftButton,pos=rect.center())
    timer.stop()
    assert seen==[True]
    assert database.get_month_statistics(2026,9)["total"]==1


def test_context_menu_opens_edit(window,database,qtbot):
    database.add_record(1,datetime(2026,9,1),"生活")
    window.switch_to(1)
    p=window.review
    september(p)
    seen=[]
    def choose():
        menu=QApplication.activePopupWidget()
        seen.append(isinstance(menu,QMenu))
        qtbot.keyClick(menu,Qt.Key.Key_Down)
        qtbot.keyClick(menu,Qt.Key.Key_Return)
    def cancel():
        dialog=QApplication.activeModalWidget()
        seen.append(isinstance(dialog,EditDialog))
        dialog.reject()
    QTimer.singleShot(50,choose)
    QTimer.singleShot(120,cancel)
    p.table.customContextMenuRequested.emit(p.table.visualItemRect(p.table.item(0,0)).center())
    assert seen==[True,True]


def test_widget_and_figure_destroyed_after_close(database,qtbot):
    window=MainWindow(database)
    window.show()
    figure=weakref.ref(window.review.chart.figure)
    canvas=weakref.ref(window.review.chart.canvas)
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    del window
    gc.collect()
    assert canvas() is None
    assert figure() is None
