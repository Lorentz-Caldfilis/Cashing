"""Synthetic first-use GUI journey; no real IME or physical-device claim."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog
from database import Database
from ui.main_window import MainWindow, REVIEW
from ui import motion


def run_journey(app, directory):
    directory=Path(directory)
    directory.mkdir(exist_ok=False)
    db=Database(directory/'ledger.sqlite3'); db.initialize_database()
    old_motion=motion.ENABLED; motion.ENABLED=False
    windows=[]; checks=[]
    def check(condition,name):
        assert condition,name
        checks.append(name)
    def frame(window,name):
        app.processEvents(); check(window.grab().save(str(directory/(name+'.png'))),name)
    try:
        window=MainWindow(db,directory); windows.append(window); window.show(); app.processEvents()
        check(window.current_index()==0 and db.user_labels()==[], 'new_empty_capture')
        frame(window,'01-first-capture')
        for amount,text in [('18.50','食堂午饭'),('15','咖啡赶论文'),('16','咖啡赶论文')]:
            QTest.keyClicks(window.capture.amount,amount)
            QTest.keyClick(window.capture.amount,Qt.Key.Key_Return)
            window.capture.description.setText(text)  # synthetic Unicode; not an IME test
            QTest.keyClick(window.capture.description,Qt.Key.Key_Return)
            app.processEvents()
        check(db.user_labels()==[], 'automatic_capture_does_not_train')
        window.switch_to(REVIEW,animate=False)
        check(window.review.view.totals['total']==4950,'three_record_total')
        coffee=[r for r in window.review.rows() if r.record['description']=='咖啡赶论文']
        window.review._row_clicked(coffee[0],'category')
        coffee[0].category_box.setCurrentText('工具')
        window.review.leave(); app.processEvents()
        check(len(db.user_labels())==1,'explicit_correction_is_one_label')
        check(all(r.record['category']=='工具' for r in window.review.rows() if r.record['description']=='咖啡赶论文'),'same_purpose_learns')
        frame(window,'02-learned-review')
        window.toast.undo_button.click(); app.processEvents()
        check(db.user_labels()==[], 'undo_removes_learning')
        check(all(r.record['category'] is None for r in window.review.rows() if r.record['description']=='咖啡赶论文'),'undo_rederives_both_coffees')
        # Keep one intentional label in the backup so restore verifies personalization too.
        row=next(r for r in window.review.rows() if r.record['description']=='咖啡赶论文')
        window.review._row_clicked(row,'category'); row.category_box.setCurrentText('工具'); window.review.leave()
        window.review.enter_search(); window.review.search_field.setText('咖啡')
        window.review._search_timer.stop(); window.review._run_search()
        check(window.review._result_count==2,'search_finds_both')
        frame(window,'03-search')
        window.review.exit_search()
        backup=directory/'chosen-backup.sqlite3'
        original=QFileDialog.getSaveFileName
        try:
            QFileDialog.getSaveFileName=lambda *a,**k:(str(backup),'SQLite 账本 (*.sqlite3)')
            window.backup_ledger()  # same menu action, deterministic synthetic file chooser
        finally: QFileDialog.getSaveFileName=original
        check(backup.is_file(),'backup_menu_action_created_snapshot')
        window.close(); app.processEvents()
        fresh=directory/'restored'; fresh.mkdir()
        shutil.copyfile(backup,fresh/'ledger.sqlite3')
        restored=Database(fresh/'ledger.sqlite3'); restored.initialize_database()
        def facts(database):
            with closing(sqlite3.connect(database.path)) as con:
                return con.execute('SELECT * FROM records ORDER BY id').fetchall()
        check(facts(db)==facts(restored),'restore_all_facts_equal')
        check(db.user_labels()==restored.user_labels(),'restore_labels_equal')
        reopened=MainWindow(restored,fresh); windows.append(reopened); reopened.show()
        reopened.switch_to(REVIEW,animate=False); app.processEvents()
        check(reopened.review.view.totals['total']==4950,'restored_gui_total')
        check(reopened.review.view.totals['工具']==3100,'restored_gui_learning')
        frame(reopened,'04-restored-review')
        report={'status':'PASS','synthetic':True,'platform':sys.platform,'qt_platform':app.platformName(),
                'scale':reopened.devicePixelRatioF(),'checks':checks,
                'limits':['Qt synthetic text, not IME','file chooser destination supplied by harness','reopen in same process, not OS restart']}
        (directory/'journey.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        return report
    finally:
        for window in windows: window.close()
        motion.ENABLED=old_motion


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--label',required=True)
    args=parser.parse_args()
    if not args.label.replace('-','').replace('_','').isalnum():parser.error('simple label required')
    app=QApplication([])
    print(json.dumps(run_journey(app,ROOT/'work'/args.label),ensure_ascii=False))

if __name__=='__main__':main()
