"""Profile an isolated synthetic durability fixture; report both first-input and correct-review time."""
import argparse
import cProfile
import io
import json
from pathlib import Path
import platform
import pstats
import shutil
import subprocess
import sys
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',required=True,help='Existing work/<label> from verify_durability.py')
    parser.add_argument('--label',required=True)
    args=parser.parse_args()
    if any(not value.replace('-','').replace('_','').isalnum() for value in (args.fixture,args.label)):
        parser.error('simple labels required')
    source=ROOT/'work'/args.fixture
    metadata=json.loads((source/'durability.json').read_text())
    if metadata.get('synthetic') is not True:parser.error('synthetic fixture required')
    directory=ROOT/'work'/args.label;directory.mkdir(exist_ok=False)
    shutil.copyfile(source/'snapshot.sqlite3',directory/'ledger.sqlite3')
    start=perf_counter();marks={}
    def mark(name):marks[name]=round(perf_counter()-start,4)
    from PySide6.QtWidgets import QApplication
    mark('qt_import')
    from database import Database
    from ui.main_window import MainWindow, REVIEW
    from ui import motion
    mark('app_modules_import')
    app=QApplication([]);motion.ENABLED=False;mark('application')
    db=Database(directory/'ledger.sqlite3');db.initialize_database();mark('database_initialize')
    profile=cProfile.Profile();profile.enable()
    window=MainWindow(db,directory);mark('window_constructed')
    window.show();app.processEvents();mark('capture_interactive')
    window.review.year,window.review.month=2026,9
    window.switch_to(REVIEW,animate=False);app.processEvents();mark('review_correct')
    profile.disable()
    report={'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'tracked_diff':bool(subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True)),
            'synthetic':True,'fixture':args.fixture,'count':metadata['count'],'platform':platform.platform(),
            'marks_seconds_from_import_start':marks,'total_cents':window.review.view.totals['total'],
            'method':'cProfile enabled only during window construction/show/review; includes profiler overhead; no background work'}
    (directory/'profile.json').write_text(json.dumps(report,indent=2)+'\n')
    output=io.StringIO();pstats.Stats(profile,stream=output).sort_stats('cumtime').print_stats(40)
    (directory/'profile.txt').write_text(output.getvalue())
    window.close();print(json.dumps(report))

if __name__=='__main__':main()
