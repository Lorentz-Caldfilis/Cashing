"""Create reproducible UI screenshots from synthetic student expenses only."""
import argparse
from datetime import datetime
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QTimer, QLocale
from PySide6.QtWidgets import QApplication
from database import Database
from ui.main_window import MainWindow, REVIEW
from ui import motion


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.label):
        parser.error("Use a simple label, not a path")
    directory = ROOT / "work" / args.label
    directory.mkdir(parents=True, exist_ok=False)
    QLocale.setDefault(QLocale("zh_CN"))
    app = QApplication(sys.argv[:1])
    motion.ENABLED = False
    database = Database(directory / "synthetic-preview.sqlite3")
    database.initialize_database()
    for day, hour, amount, description, category in [
        (30, 12, 1850, "食堂午饭", None), (30, 9, 600, "打印课程资料", "工具"),
        (29, 19, 3500, "和室友看电影", None), (29, 12, 2200, "午饭", None),
        (28, 15, 1800, "咖啡 · 小组讨论", "工具"), (28, 8, 450, "地铁", None),
        (27, 18, 3200, "晚饭", None), (27, 10, 1200, "奶茶", None),
    ]:
        database.add_record(amount, datetime(2026, 9, day, hour, 0), category, description)
    window = MainWindow(database, directory)
    window.show()

    def capture():
        window.capture.amount.setText("18.50")
        window.capture.description.setText("食堂午饭")
        window.capture.description.setFocus()
        window.grab().save(str(directory / "capture.png"))
        window.switch_to(REVIEW, animate=False)
        window.review.year, window.review.month = 2026, 9
        window.review.refresh()
        QTimer.singleShot(200, review)

    def review():
        window.grab().save(str(directory / "review.png"))
        row = window.review.rows()[0]
        window.review._row_clicked(row, "category")
        QTimer.singleShot(100, edit)

    def edit():
        window.grab().save(str(directory / "edit.png"))
        window.review.cancel_edit()
        window.resize(640, 480)
        QTimer.singleShot(100, compact)

    def compact():
        window.grab().save(str(directory / "compact.png"))
        window.close()
        app.quit()

    QTimer.singleShot(300, capture)
    result = app.exec()
    print(directory)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
