"""Cashing desktop entry point. No networking or runtime downloads."""
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import sys
import traceback

from PySide6.QtCore import QLibraryInfo, QTranslator, QLocale
from PySide6.QtWidgets import QApplication, QMessageBox
from database import Database, DatabaseError
from paths import data_directory, prepare_runtime, prepare_smoke_directory


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cashing 本地个人记账")
    parser.add_argument("--data-dir", help="独立数据目录（绝对路径，用于验证）")
    parser.add_argument("--smoke-test", action="store_true", help="在独立目录自动 GUI 验收后退出")
    args = parser.parse_args(argv)
    if args.smoke_test and not args.data_dir:
        parser.error("--smoke-test 必须同时指定独立的 --data-dir")
    QLocale.setDefault(QLocale('zh_CN'))
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Cashing")
    app.setOrganizationName("Cashing")
    app.setApplicationVersion("1.0.0")
    translator = QTranslator(app)
    translated = translator.load("qtbase_zh_CN", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    app.setProperty("chinese_translation_loaded", translated)
    if translated:
        app.installTranslator(translator)
    handler = None
    try:
        directory = data_directory(args.data_dir)
        if args.smoke_test:
            prepare_smoke_directory(directory)
        prepare_runtime(directory)
        handler = RotatingFileHandler(directory / "cashing.log", maxBytes=1_000_000,
                                      backupCount=2, encoding="utf-8")
        logging.basicConfig(handlers=[handler], level=logging.WARNING,
                            format="%(asctime)s %(levelname)s %(message)s")
        # Smoke mode can never open the production filename.
        database = Database(directory / ("smoke-ledger.sqlite3" if args.smoke_test else "ledger.sqlite3"))
        database.initialize_database()
        from ui.main_window import MainWindow
        window = MainWindow(database, directory)
    except (OSError, ValueError, DatabaseError) as exc:
        logging.exception("Startup failed")
        if not args.smoke_test:
            QMessageBox.critical(None, "无法启动 Cashing", f"{exc}\n请检查数据目录和备份，原有账单不会被清空。")
        if handler:
            handler.close()
        return 1

    old_hook = sys.excepthook
    def report_unhandled(exc_type, exc, tb):
        logging.error("Unexpected error", exc_info=(exc_type, exc, tb))
        if args.smoke_test:
            (directory / "smoke-result.json").write_text(json.dumps({
                "status": "FAIL", "traceback": "".join(traceback.format_exception(exc_type, exc, tb))
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            app.exit(1)
        else:
            QMessageBox.critical(window, "操作未完成",
                                 "程序遇到意外错误，请重新打开程序。错误已记录到数据目录的 cashing.log。")

    sys.excepthook = report_unhandled
    window.show()
    if args.smoke_test:
        from smoke_check import schedule_smoke_check
        schedule_smoke_check(app, window, database, directory)
    try:
        return app.exec()
    finally:
        sys.excepthook = old_hook
        logging.getLogger().removeHandler(handler)
        handler.close()


if __name__ == "__main__":
    raise SystemExit(main())
