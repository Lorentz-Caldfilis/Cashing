"""Bounded synthetic 10k-ledger timing, memory, state and backup/restore checks."""
import argparse
from contextlib import closing
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
from time import perf_counter
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from database import Database
from ledger import Ledger, AUTO


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label', required=True)
    p.add_argument('--dense', action='store_true')
    args = p.parse_args()
    if not args.label.replace('-', '').replace('_', '').isalnum():
        p.error('simple label required')
    folder = ROOT / 'work' / args.label
    folder.mkdir(exist_ok=False)
    report = {'synthetic': True, 'count': 10000, 'dense': args.dense,
              'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'platform': platform.platform(), 'python': platform.python_version(),
              'cpu_count': os.cpu_count(), 'measurements': {}, 'checks': {}}
    if Path('/proc/cpuinfo').exists():
        report['cpu'] = next(line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
        report['mem_total'] = Path('/proc/meminfo').read_text().splitlines()[0]
    def save():
        (folder / 'durability.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    def rss():
        return next(int(line.split()[1])/1024 for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('VmRSS:')) if Path('/proc/self/status').exists() else None
    def measure(name, fn):
        before = rss(); start = perf_counter(); result = fn()
        report['measurements'][name] = {'seconds': round(perf_counter()-start, 4), 'rss_mib': rss(), 'rss_delta_mib': round(rss()-before, 2) if before else None}
        save(); print(name, report['measurements'][name], flush=True)
        return result
    db = Database(folder/'ledger.sqlite3'); db.initialize_database()
    texts = ['食堂午饭','京东微积分教材','咖啡赶论文','周末电影票','宿舍洗衣液补充装']
    rows = []
    for i in range(10000):
        month = 9 if args.dense else i % 24 % 12 + 1
        year = 2026 if args.dense else 2025 + (i % 24)//12
        when = f'{year}-{month:02d}-{i%28+1:02d} 12:00'
        labelled = i % 5 == 0
        text = texts[i % 5] + (f' 合成{i}' if i % 3 == 0 else '')
        rows.append((100+i%5000, when, '生活' if labelled else None, text, when, when, int(labelled)))
    with closing(sqlite3.connect(db.path)) as con:
        with con: con.executemany('INSERT INTO records(amount_cents,datetime,category,description,created_at,updated_at,category_by_user) VALUES(?,?,?,?,?,?,?)', rows)
    measure('initialize', db.initialize_database)
    ledger = Ledger(db)
    measure('month_service', lambda: ledger.month(2026,9))
    measure('narrow_search_service', lambda: ledger.search('合成9999'))
    measure('broad_search_service', lambda: ledger.search('食堂'))
    def cycles():
        r=ledger.create(100,datetime(2026,9,30,10,0),'耐用性星云店')
        for _ in range(100):
            chosen, correction=ledger.update_undoable(r,category='工具')
            reset, receipt=ledger.update_undoable(chosen,category=AUTO)
            assert ledger.classifier().classify(r['description']) is None
            ledger.undo_update(receipt)
            assert ledger.classifier().classify(r['description']) == '工具'
            ledger.undo_update(correction)
            assert db.get_record(r['id'])['category_by_user']==0
        ledger.undo_create(r['id'])
        report['checks']['100_correction_reset_double_undo']=True
    measure('100_state_cycles', cycles)
    backup=folder/'snapshot.sqlite3'
    measure('backup', lambda: ledger.backup_to(backup))
    restored_dir=folder/'restored'; restored_dir.mkdir()
    shutil.copyfile(backup, restored_dir/'ledger.sqlite3')
    restored=Database(restored_dir/'ledger.sqlite3')
    measure('restored_initialize', restored.initialize_database)
    def raw(path):
        with closing(sqlite3.connect(path)) as c: return c.execute('SELECT * FROM records ORDER BY id').fetchall()
    assert raw(db.path)==raw(restored.path)
    assert db.user_labels()==restored.user_labels()
    assert ledger.month(2026,9).totals==Ledger(restored).month(2026,9).totals
    report['checks']['fresh_directory_restore_all_facts_labels_totals']=True
    from PySide6 import __version__ as qt_version
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow, REVIEW
    from ui import motion
    app=QApplication([]); motion.ENABLED=False
    report['qt']=qt_version; report['qt_platform']=app.platformName()
    def settle():
        app.processEvents(); QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
    def start():
        w=MainWindow(db,folder); w.show(); settle(); return w
    window=measure('gui_start_capture',start)
    def review():
        window.review.year,window.review.month=2026,9
        window.switch_to(REVIEW,animate=False); window.review.refresh(); settle()
    measure('gui_month',review)
    def search(text):
        window.review.enter_search(); window.review.search_field.setText(text)
        window.review._search_timer.stop(); window.review._run_search(); settle()
    measure('gui_narrow_search',lambda:search('合成9999'))
    measure('gui_broad_search',lambda:search('食堂'))
    report['visible_rows']=len(window.review.rows())
    window.grab().save(str(folder/'broad-search.png'))
    window.close(); settle(); save()
    print(folder,flush=True)

if __name__=='__main__': main()
