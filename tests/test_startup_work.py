"""Capture does not eagerly classify a hidden month; entering Review stays fresh."""
from datetime import datetime
from ledger import Ledger
from ui.main_window import MainWindow, REVIEW, CAPTURE


def test_capture_defers_month_work_without_reusing_stale_totals(qtbot,database,tmp_path,monkeypatch):
    calls=[]; original=Ledger.month
    def tracked(self,*args):
        calls.append(args)
        return original(self,*args)
    monkeypatch.setattr(Ledger,'month',tracked)
    window=MainWindow(database,tmp_path); qtbot.addWidget(window); window.show()
    assert calls==[]
    window.capture.amount.setText('1'); window.capture.description.setText('午饭'); window.capture.record()
    assert calls==[]
    window.switch_to(REVIEW,animate=False)
    assert len(calls)==1 and window.review.view.totals['total']==100
    window.switch_to(CAPTURE,animate=False)
    database.add_record(200,datetime.now(),None,'教材')
    window.switch_to(REVIEW,animate=False)
    assert len(calls)==2 and window.review.view.totals['total']==300
