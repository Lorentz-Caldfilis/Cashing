"""Actual Qt event-loop / frozen-executable acceptance, always opt-in and isolated.

Drives the real window the way a user would: Enter path in Capture, Alt+→ to
Review, in-place edit, delete edge, undo, search, month navigation, then a
restart check (persistence + draft) on the second run in the same directory.
"""
import json
import os
import socket
import sys
import traceback
from time import monotonic
from datetime import datetime
from PySide6.QtCore import QTimer, Qt, QPoint
from PySide6.QtTest import QTest
from database import Database
from draft import DraftStore
from ui.main_window import CAPTURE, REVIEW

DRAFT_AMOUNT, DRAFT_TEXT = "12.5", "自动验收草稿"


def schedule_smoke_check(app, window, database, directory):
    result = {"platform": sys.platform, "qt_platform": app.platformName(),
              "native_windows": sys.platform == "win32" and app.platformName() == "windows",
              "status": "RUNNING", "checks": [], "database": str(database.path),
              "device_pixel_ratio": window.devicePixelRatioF(),
              "window_size": [window.width(), window.height()],
              "screen_available": [app.primaryScreen().availableGeometry().width(),
                                   app.primaryScreen().availableGeometry().height()]}
    result["clipboard_mode"] = os.environ.get("CASHING_SMOKE_CLIPBOARD_MODE", "system")

    def check(condition, message):
        if not condition:
            raise AssertionError(message)
        result["checks"].append(message)

    def settle(ms=320):
        deadline = datetime.now().timestamp() + ms / 1000
        while datetime.now().timestamp() < deadline:
            app.processEvents()
            QTest.qWait(10)

    def wait_for_space(index, name):
        start = monotonic()
        while monotonic() - start < 2.0:
            app.processEvents()
            if window.current_index() == index and not window.spaces.is_animating():
                break
            QTest.qWait(10)
        result.setdefault("navigation", {})[name] = {
            "elapsed_seconds": round(monotonic() - start, 4),
            "index": window.current_index(), "animating": window.spaces.is_animating()}
        check(window.current_index() == index and not window.spaces.is_animating(), name)

    def click_row(row, cell=None):
        target = getattr(row, cell) if cell else None
        pos = target.geometry().center() if target else QPoint(row.width() // 2, row.height() // 2)
        QTest.mouseClick(row, Qt.MouseButton.LeftButton, pos=pos)
        app.processEvents()

    def exercise():
        try:
            # Native keyboard shortcuts require an active window. Automation can
            # launch behind the editor; wait for real activation before driving it.
            window.raise_()
            window.activateWindow()
            check(QTest.qWaitForWindowActive(window, 5000), "native_window_active")
            def blocked(*args, **kwargs):
                raise AssertionError("Unexpected network access")
            socket.socket.connect = blocked
            socket.create_connection = blocked
            socket.getaddrinfo = blocked
            capture, review = window.capture, window.review
            marker = directory / "smoke-marker.json"
            previous = json.loads(marker.read_text("utf-8")) if marker.exists() else None
            if previous:
                persisted = database.get_records_by_month(2020, 1)
                check(any(r["id"] == previous["id"] and r["amount_cents"] == 1234 for r in persisted),
                      "previous_process_persistence")
                check(capture.amount.text() == DRAFT_AMOUNT and capture.description.text() == DRAFT_TEXT,
                      "draft_restored_after_restart")
                check(database.get_month_statistics(2020, 1)["total"] == 1234, "draft_not_counted")
                check(capture.description.hasFocus(), "draft_focus_continues_at_description")
                capture.amount.clear()
                capture.description.clear()
                capture.reset_time()
                capture.focus_default()
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
            check(window.current_index() == CAPTURE and capture.amount.hasFocus(), "starts_in_capture_with_amount_focus")
            check(window.grab().save(str(directory / "01-capture.png")), "capture_screenshot")

            # New capture path: clipboard fills a reviewable draft, then autosaves it.
            if result["clipboard_mode"] == "parser":
                check(capture.paste_entry("￥１８．５０ 合成午饭"), "synthetic_paste_parser_only")
            else:
                app.clipboard().setText("￥１８．５０ 合成午饭")
                start = monotonic()
                while app.clipboard().text() != "￥１８．５０ 合成午饭" and monotonic() - start < 2:
                    QTest.qWait(50)
                    app.clipboard().setText("￥１８．５０ 合成午饭")
                check(app.clipboard().text() == "￥１８．５０ 合成午饭", "system_clipboard_available")
                QTest.keyClick(capture.amount, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
            check(capture.amount.text() == "18.50" and capture.description.text() == "合成午饭",
                  "single_entry_clipboard_fills_inputs")
            check(not database.get_records_by_month(2026, 9), "paste_does_not_save_record")
            settle(450)
            check(DraftStore(directory).load() == capture.draft(), "draft_saved_before_close")
            capture._reset_inputs()

            # Optional purpose, raw origin, undo, and the fixed light appearance.
            capture.amount.setText("9")
            capture.description.setText("合成用途选择")
            capture.select_category("娱乐")
            capture.record()
            selected = database.get_records_by_month(capture.ledger.now().year, capture.ledger.now().month)[0]
            check(selected["category"] == "娱乐" and selected["category_by_user"] == 1,
                  "capture_personal_category_stored")
            window.toast._run_undo()
            check(capture.selected_category == "娱乐", "undo_restores_capture_category")
            capture._reset_inputs()
            check(window.centralWidget().objectName() == "space", "fixed_light_surface")
            check([a.text() for a in window.utility_menu.actions() if not a.isSeparator()]
                  == ["打开数据目录", "备份账本…", "关于 Cashing"], "utility_menu_without_background")
            check(not window.windowIcon().isNull(), "application_icon_loaded")

            # Capture: local error, then three records through the Enter path.
            QTest.keyClicks(capture.amount, "0")
            QTest.keyClick(capture.amount, Qt.Key.Key_Return)
            check(capture.amount_error.text() and not database.get_records_by_month(2026, 9), "zero_amount_rejected")
            capture.amount.clear()
            for amount, text in [("28.50", "本地 GUI 自动验收 A"), ("100.00", "本地 GUI 自动验收 B"), ("50.00", "本地 GUI 自动验收 C")]:
                QTest.keyClicks(capture.amount, amount)
                QTest.keyClick(capture.amount, Qt.Key.Key_Return)
                check(capture.description.hasFocus(), "enter_moves_to_description")
                capture.set_time(datetime(2026, 9, 19, 22, 15))
                capture.description.setText(text)  # CJK typed through QTest crashes the Windows QPA
                QTest.keyClick(capture.description, Qt.Key.Key_Return)
                check(not capture.amount.text() and not capture.description.text() and capture.amount.hasFocus(),
                      "save_clears_and_refocuses")
                check(window.toast.isVisible() and window.toast.label.text().startswith("已记录 "), "save_toast")
            check(window.current_index() == CAPTURE, "stays_in_capture_after_save")
            capture.amount.setText("9.99")
            capture.record()
            window.toast.undo_button.click()
            app.processEvents()
            check(capture.amount.text() == "9.99" and len(database.get_records_by_month(2026, 9)) == 3, "undo_save_restores_input")
            capture.amount.clear()

            # Review: Alt+→ slides over; summary and history agree with the ledger.
            QTest.keyClick(window, Qt.Key.Key_Right, Qt.KeyboardModifier.AltModifier)
            wait_for_space(REVIEW, "alt_right_switches_to_review")
            review.year, review.month = 2026, 9
            review.refresh()
            app.processEvents()
            check(len(review.rows()) == 3, "three_records")
            check(review.summary.total.text() == "178.50", "monthly_total")
            check(review.summary.unknown_note.text() == "另有 ¥178.50 尚未分类",
                  "unknown_amount_shown_weakly")
            # Nothing is classified yet, so there is no proportion and no ring.
            check(not review.summary.donut.segments and review.summary.donut.isHidden(), "no_ring_without_structure")
            settle(120)
            check(window.grab().save(str(directory / "02-review.png")), "review_screenshot")

            # In-place edit: category then amount.
            row = review.rows()[0]
            click_row(row, "category")
            check(row.editing and review.editing_row is row, "single_click_edits_in_place")
            row.category_box.setCurrentText("工具")
            app.processEvents()
            check(review.summary.lines["工具"].amount.text() == "¥50.00", "category_edit_applies_at_once")  # newest id first among equal times
            row.category_box.setCurrentText("自动判断")
            check(not database.get_record(row.record["id"])["category_by_user"], "reset_personal_label")
            QTest.keyClick(window, Qt.Key.Key_Z,
                           Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)
            app.processEvents()
            row = review.rows()[0]
            check(database.get_record(row.record["id"])["category_by_user"] == 1,
                  "keyboard_undo_restores_personal_label")
            click_row(row, "amount")
            row.amount_edit.setText("60.01")
            QTest.keyClick(row.amount_edit, Qt.Key.Key_Return)
            app.processEvents()
            check(not row.editing and review.summary.total.text() == "188.51", "amount_edit_committed_on_enter")
            check(len(review.summary.donut.segments) == 2 and not review.summary.donut.isHidden(),
                  "ring_follows_edit")

            backup_path = directory / ("restart-backup.sqlite3" if previous else "first-backup.sqlite3")
            window.ledger.backup_to(backup_path)
            check(Database(backup_path).get_record(row.record["id"]) == database.get_record(row.record["id"]),
                  "live_backup_preserves_edited_record")

            # Delete edge + undo.
            row = review.rows()[0]
            click_row(row, "description")
            check(not row.edge.isHidden(), "delete_edge_shown_in_edit")
            QTest.mouseClick(row.edge, Qt.MouseButton.LeftButton)
            app.processEvents()
            check(len(review.rows()) == 2 and window.toast.label.text().startswith("已删除 "), "delete_without_confirm")
            window.toast.undo_button.click()
            app.processEvents()
            check(len(review.rows()) == 3 and review.summary.total.text() == "188.51", "undo_delete_restores")

            # Search across all history, then back to the month.
            review.enter_search()
            review.search_field.setText("自动验收 B")
            review._run_search()
            check(review.searching and [r.record["description"] for r in review.rows()] == ["本地 GUI 自动验收 B"], "search_results")
            review.search_field.setText("不存在的记录")
            review._run_search()
            check(review.no_results.isVisibleTo(review), "search_no_results")
            review.exit_search()
            check(not review.searching and len(review.rows()) == 3, "search_exit_restores_month")

            # Delete everything: quiet empty state.
            for _ in range(3):
                row = review.rows()[0]
                click_row(row, "description")
                QTest.mouseClick(row.edge, Qt.MouseButton.LeftButton)
                app.processEvents()
            check(review.rows() == [] and review.summary.total.text() == "0.00", "delete_and_empty_month")
            check(review.summary.empty.isVisibleTo(review) and not review.summary.donut.segments, "empty_month_no_ring")

            # Month navigation never enters the future.
            review.show_current_month()
            check(not review.next.isEnabled(), "no_future_month")
            QTest.mouseClick(review.previous, Qt.MouseButton.LeftButton)
            app.processEvents()
            expected = (review.year, review.month)
            check(review.next.isEnabled(), "previous_month")
            QTest.mouseClick(review.next, Qt.MouseButton.LeftButton)
            app.processEvents()
            check(review.at_current_month() and expected != (review.year, review.month), "next_month_back_to_now")
            settle(120)
            check(window.grab().save(str(directory / "03-empty.png")), "empty_screenshot")

            # Back to Capture; leave a draft for the next process.
            QTest.keyClick(window, Qt.Key.Key_Left, Qt.KeyboardModifier.AltModifier)
            settle()
            check(window.current_index() == CAPTURE and capture.amount.hasFocus(), "alt_left_back_to_capture")
            capture.amount.setText(DRAFT_AMOUNT)
            capture.description.setText(DRAFT_TEXT)

            reopened = Database(database.path)
            reopened.initialize_database()
            check(reopened.get_month_statistics(2020, 1)["total"] == 1234, "reopen_persistence")
            if sys.platform == "win32":
                check(app.platformName() == "windows", "native_windows_qt_platform")
            else:
                check(app.platformName() in ("xcb", "offscreen", "wayland"),
                      "non_windows_qt_platform_recorded")
            result["status"] = "PASS"
        except Exception:
            result["status"] = "FAIL"
            result["traceback"] = traceback.format_exc()
        finally:
            (directory / "smoke-result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            window.close()
            if result["status"] == "PASS":
                result["draft_saved"] = DraftStore(directory).load() is not None
                (directory / "smoke-result.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            app.exit(0 if result["status"] == "PASS" else 1)
    QTimer.singleShot(500, exercise)
