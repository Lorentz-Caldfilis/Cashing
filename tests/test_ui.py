from datetime import datetime
import socket
import pytest
from PySide6.QtCore import Qt, QDateTime, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from database import DatabaseError
from ui.main_window import MainWindow
from ui.edit_dialog import EditDialog
from domain import CATEGORIES


@pytest.fixture
def window(qtbot, database, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("核心功能不应访问网络")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    widget = MainWindow(database)
    qtbot.addWidget(widget)
    widget.show()
    return widget


def fill(form, amount="28.50", category="饮食", when="2026-09-19 22:15", description="晚饭"):
    form.amount.setText(amount)
    form.category.setCurrentText(category)
    form.when.setDateTime(QDateTime.fromString(when,"yyyy-MM-dd HH:mm"))
    form.description.setText(description)


def september(page):
    page.year, page.month = 2026,9
    page.refresh()


def test_add_reset_chart_and_navigation(window,qtbot,database):
    for category in CATEGORIES:
        fill(window.input_page.form,category=category)
        qtbot.mouseClick(window.input_page.save_button,Qt.MouseButton.LeftButton)
        assert window.input_page.form.amount.text() == ""
        assert window.input_page.form.description.text() == ""
        assert window.input_page.form.category.currentText() == category
        assert window.input_page.form.when.dateTime().secsTo(QDateTime.currentDateTime()) in range(-2,3)
        assert "已保存" in window.input_page.feedback.text()
    window.navigation.setCurrentRow(1)
    page = window.records_page
    september(page)
    assert page.table.rowCount() == 3
    assert page.stat_labels["total"].text() == "¥85.50"
    assert len(page.chart.axes.patches) == 3
    assert all(page.chart.legend[c].text() == "33.3%" for c in CATEGORIES)
    page.change_month(1)
    assert page.table.rowCount() == 0
    assert page.stat_labels["total"].text() == "¥0.00"
    assert not page.chart.empty.isHidden()
    assert not page.chart.axes.patches
    page.year,page.month = 2026,12
    page.change_month(1)
    assert (page.year,page.month) == (2027,1)
    page.change_month(-1)
    assert (page.year,page.month) == (2026,12)
    page.year,page.month=1900,1
    page.refresh()
    assert not page.previous.isEnabled()
    page.year,page.month=9999,12
    page.refresh()
    assert not page.next.isEnabled()


def test_bad_input_and_write_failure_preserve_form(window,qtbot,monkeypatch):
    form=window.input_page.form
    for amount in ["", "0", "-1", "NaN","1.234"]:
        fill(form,amount=amount)
        window.input_page.save()
        assert "已保存" not in window.input_page.feedback.text()
    fill(form)
    def fail(*args):
        raise DatabaseError("测试：磁盘不可写")
    monkeypatch.setattr(window.input_page.database,"add_record",fail)
    window.input_page.save()
    assert form.amount.text()=="28.50"
    assert form.description.text()=="晚饭"
    assert "磁盘不可写" in window.input_page.feedback.text()


def test_edit_across_month(window,database,qtbot):
    database.add_record(100,datetime(2026,9,19),"饮食")
    page=window.records_page
    september(page)
    page.table.selectRow(0)
    def edit():
        dialog=QApplication.activeModalWidget()
        assert isinstance(dialog,EditDialog)
        fill(dialog.form,"20.01","工具","2026-10-01 00:00","跨月")
        dialog.save()
    QTimer.singleShot(30,edit)
    page.edit_selected()
    assert page.table.rowCount()==0
    assert page.stat_labels["total"].text()=="¥0.00"
    page.change_month(1)
    assert page.stat_labels["工具"].text()=="¥20.01"
    assert len(page.chart.axes.patches)==1
    assert database.get_month_statistics(2026,10)["total"]==2001


def test_delete_cancel_then_confirm_and_no_selection(window,database,qtbot):
    database.add_record(2850,datetime(2026,9,19),"饮食")
    page=window.records_page
    september(page)
    page.edit_selected()
    page.delete_selected()
    assert not page.edit_button.isEnabled()
    page.table.selectRow(0)
    def answer(text):
        box=QApplication.activeModalWidget()
        assert isinstance(box,QMessageBox)
        next(b for b in box.buttons() if b.text()==text).click()
    QTimer.singleShot(30,lambda:answer("取消"))
    page.delete_selected()
    assert page.table.rowCount()==1
    QTimer.singleShot(30,lambda:answer("删除"))
    page.delete_selected()
    assert page.table.rowCount()==0
    assert page.stat_labels["total"].text()=="¥0.00"
    assert not page.chart.axes.patches
    assert database.get_month_statistics(2026,9)["total"]==0


def test_long_plain_description(window,database):
    text="<b>普通文本</b>"+"中"*185
    database.add_record(1,datetime(2026,9,19),"饮食",text)
    page=window.records_page
    september(page)
    page.table.selectRow(0)
    assert page.description.toPlainText()==text
    assert page.table.item(0,3).text()==text


def test_refresh_reuses_figure_and_failure_never_looks_empty(window,database,monkeypatch):
    database.add_record(100,datetime(2026,9,19),"饮食")
    page=window.records_page
    september(page)
    figure,axes,canvas=page.chart.figure,page.chart.axes,page.chart.canvas
    for _ in range(60):
        page.refresh()
    assert page.chart.figure is figure and page.chart.axes is axes and page.chart.canvas is canvas
    assert len(figure.axes)==1 and len(axes.patches)==1
    def fail(*args):
        raise DatabaseError("测试：数据库读取失败")
    monkeypatch.setattr(database,"get_records_by_month",fail)
    page.refresh()
    assert page.table.rowCount()==0
    assert page.stat_labels["total"].text()=="—"
    assert "读取失败" in page.count_label.text()
    assert page.chart.isHidden()


def test_edit_failure_keeps_dialog_open(qtbot,database,monkeypatch):
    database.add_record(1,datetime(2026,9,19),"饮食")
    record=database.get_records_by_month(2026,9)[0]
    dialog=EditDialog(database,record)
    qtbot.addWidget(dialog)
    dialog.show()
    fill(dialog.form,"8.88")
    def fail(*args):
        raise DatabaseError("无法保存")
    monkeypatch.setattr(database,"update_record",fail)
    dialog.save()
    assert dialog.isVisible()
    assert dialog.error.text()=="无法保存"
