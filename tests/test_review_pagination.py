"""Large results stay complete while live row widgets remain bounded."""
from datetime import datetime
import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from ui.main_window import MainWindow, REVIEW
from ui.record_row import RecordRow
from ui import motion


@pytest.fixture
def page(qtbot, database, tmp_path, monkeypatch):
    monkeypatch.setattr(motion, 'ENABLED', False)
    for i in range(125):
        database.add_record(100, datetime(2026,9,20,12,0), None, f'合成午饭{i}')
    widget=MainWindow(database,tmp_path)
    qtbot.addWidget(widget); widget.show(); widget.switch_to(REVIEW,animate=False)
    page=widget.review; page.year,page.month=2026,9; page.refresh()
    return page


def settle():
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    QCoreApplication.processEvents()


def test_all_records_are_reachable_once_with_full_totals_and_bounded_widgets(page):
    seen=[]
    for count in (60,60,5):
        settle()
        assert len(page.rows())==count
        assert len(page.history.findChildren(RecordRow))<=page.PAGE_SIZE
        assert page.summary.total.text()=='125.00'
        seen += [r.record['id'] for r in page.rows()]
        page._change_result_page(1)
    assert len(seen)==len(set(seen))==125
    assert not page.page_next.isEnabled()
    page._change_result_page(-1)
    assert page.page_count.text()=='61–120 / 125 条'


def test_invalid_edit_blocks_page_change_and_valid_change_remains_saved(page,database):
    row=page.rows()[0]; page._row_clicked(row,'amount'); row.amount_edit.setText('bad')
    page._change_result_page(1)
    assert page._page_index==0 and page.editing_row is row
    row.amount_edit.setText('2'); page._change_result_page(1)
    assert page._page_index==1
    assert database.get_record(row.record['id'])['amount_cents']==200
    assert page.summary.total.text()=='126.00'


def test_search_context_resets_page_and_delete_clamps_last_page(page):
    page._change_result_page(1)
    page.enter_search(); page.search_field.setText('午饭'); page._search_timer.stop(); page._run_search()
    assert page._page_index==0 and page._result_count==125
    page._change_result_page(1); page._change_result_page(1)
    for _ in range(5): page._delete_row(page.rows()[-1])
    assert page._page_index==1 and page._result_count==120
    assert len(page.rows())==60
    page.search_field.setText('不存在'); page._search_timer.stop(); page._run_search()
    assert not page.rows() and page.pager.isHidden()
    page.exit_search()
    assert page.summary.total.text()=='120.00'
