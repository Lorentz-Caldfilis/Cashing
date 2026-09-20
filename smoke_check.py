"""Actual Qt event-loop / frozen-executable acceptance, always opt-in and isolated."""
import json
import socket
import traceback
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QDateTime, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
from database import Database
from ui.edit_dialog import EditDialog


def schedule_smoke_check(app, window, database, directory):
    result = {"status": "RUNNING", "checks": [], "database": str(database.path),
              "device_pixel_ratio": window.devicePixelRatioF(),
              "window_size": [window.width(), window.height()],
              "screen_available": [app.primaryScreen().availableGeometry().width(),
                                   app.primaryScreen().availableGeometry().height()]}
    def check(condition, message):
        if not condition:
            raise AssertionError(message)
        result["checks"].append(message)

    def exercise():
        try:
            def blocked(*args, **kwargs):
                raise AssertionError("Unexpected network access")
            socket.socket.connect = blocked
            socket.create_connection = blocked
            socket.getaddrinfo = blocked
            marker = directory / "smoke-marker.json"
            previous = json.loads(marker.read_text("utf-8")) if marker.exists() else None
            if previous:
                persisted = database.get_records_by_month(2020, 1)
                check(any(r["id"] == previous["id"] and r["amount_cents"] == 1234 for r in persisted),
                      "previous_process_persistence")
            else:
                # Never run the destructive smoke flow against an existing user data file.
                check(not database.get_records_by_month(2020, 1)
                      and not database.get_records_by_month(2026, 9), "isolated_database")
                rid = database.add_record(1234, datetime(2020, 1, 1), "工具", "自动验收持久化标记")
                marker.write_text(json.dumps({"id": rid}), encoding="utf-8")
            check(window.isVisible(), "main_window_visible")
            available = app.primaryScreen().availableGeometry()
            check(window.width() <= available.width() and window.height() <= available.height(),
                  "window_fits_available_screen")
            check(app.property("chinese_translation_loaded") is True, "chinese_translation_loaded")
            check(window.grab().save(str(directory / "01-input.png")), "input_screenshot")
            form = window.input_page.form
            form.amount.setText("0")
            window.content_scroll.ensureWidgetVisible(window.input_page.save_button)
            QTest.mouseClick(window.input_page.save_button, Qt.MouseButton.LeftButton)
            check("已保存" not in window.input_page.feedback.text(), "zero_amount_rejected")
            for amount, category in [("28.50", "生活"), ("100.00", "工具"), ("50.00", "娱乐")]:
                form.amount.clear()
                QTest.keyClicks(form.amount, amount)
                form.category.setCurrentText(category)
                form.when.setDateTime(QDateTime.fromString("2026-09-19 22:15", "yyyy-MM-dd HH:mm"))
                form.description.setText("本地 GUI 自动验收 · "+category)
                window.content_scroll.ensureWidgetVisible(window.input_page.save_button)
                QTest.mouseClick(window.input_page.save_button, Qt.MouseButton.LeftButton)
                check(not form.amount.text() and not form.description.text(), "save_reset_"+category)
            QTest.mouseClick(window.navigation.viewport(), Qt.MouseButton.LeftButton,
                             pos=window.navigation.visualItemRect(window.navigation.item(1)).center())
            page = window.records_page
            page.year, page.month = 2026, 9
            page.refresh()
            check(page.table.rowCount() == 3, "three_records")
            check(page.stat_labels["total"].text() == "¥178.50", "monthly_total")
            check(len(page.chart.axes.patches) == 3, "three_pie_slices")
            page.chart.canvas.draw()
            app.processEvents()
            check(window.grab().save(str(directory / "02-bills.png")), "bills_screenshot")
            page.table.selectRow(0)
            callback_errors = []
            def edit():
                try:
                    dialog = QApplication.activeModalWidget()
                    check(isinstance(dialog, EditDialog), "edit_dialog_created")
                    dialog.form.amount.setText("60.01")
                    dialog.form.category.setCurrentText("工具")
                    QTest.mouseClick(dialog.save_button, Qt.MouseButton.LeftButton)
                except Exception:
                    callback_errors.append(traceback.format_exc())
                    modal = QApplication.activeModalWidget()
                    if modal:
                        modal.reject()
            QTimer.singleShot(50, edit)
            window.content_scroll.ensureWidgetVisible(page.edit_button)
            QTest.mouseClick(page.edit_button, Qt.MouseButton.LeftButton)
            check(not callback_errors, "edit_callback")
            check(page.stat_labels["total"].text() == "¥188.51", "edit_total_refreshed")
            check(page.stat_labels["工具"].text() == "¥160.01", "edit_category_refreshed")
            check(len(page.chart.axes.patches) == 2, "edit_chart_refreshed")
            for _ in range(3):
                page.table.selectRow(0)
                def confirm():
                    box = QApplication.activeModalWidget()
                    if isinstance(box, QMessageBox):
                        next(b for b in box.buttons() if b.text() == "删除").click()
                QTimer.singleShot(50, confirm)
                window.content_scroll.ensureWidgetVisible(page.delete_button)
                QTest.mouseClick(page.delete_button, Qt.MouseButton.LeftButton)
            check(page.table.rowCount() == 0 and page.stat_labels["total"].text() == "¥0.00",
                  "delete_and_empty_month")
            check(not page.chart.axes.patches and not page.chart.empty.isHidden(), "empty_chart")
            page.year, page.month = 2026, 12
            QTest.mouseClick(page.next, Qt.MouseButton.LeftButton)
            check((page.year, page.month) == (2027, 1), "next_year")
            QTest.mouseClick(page.previous, Qt.MouseButton.LeftButton)
            check((page.year, page.month) == (2026, 12), "previous_year")
            app.processEvents()
            check(window.grab().save(str(directory / "03-empty.png")), "empty_screenshot")
            reopened = Database(database.path)
            reopened.initialize_database()
            check(reopened.get_month_statistics(2020, 1)["total"] == 1234, "reopen_persistence")
            check(app.platformName() == "windows", "native_windows_qt_platform")
            result["status"] = "PASS"
        except Exception:
            result["status"] = "FAIL"
            result["traceback"] = traceback.format_exc()
        finally:
            (directory / "smoke-result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            window.close()
            app.exit(0 if result["status"] == "PASS" else 1)
    QTimer.singleShot(500, exercise)
