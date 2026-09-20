# Cashing UI v2 (PC Light Mode) — Implementation Status

Branch: `ui-v2-pc-light` (based on `main` @ fef67a5, v1.0.0).
Normative inputs: `docs/design/*.md` (priority: Philosophy > IA > Interaction > Visual > PC Light Amendments > PNG).
A new session must be able to resume from this file + git history + `docs/design/` alone.

## Milestones

| # | Milestone | State |
|---|-----------|-------|
| 1 | Spec audit + minimal core architecture (schema v2, migration, ledger service, draft store, classification interface) | **done** |
| 2 | Capture rebuild (amount hero, description, weak time + popover, 记录, Enter flow, save/undo toast, local errors) | **done** |
| 3 | Capture ⇄ Review spaces + horizontal page switching (dots, edges, Alt+←/→, trackpad wheel) | **done** |
| 4 | Review Summary + History (month nav, total, three categories, donut, day groups) | **done** |
| 5 | In-place edit, PC delete edge, delete/undo | **done** |
| 6 | Search, Utility (⋮), Draft persistence | **done** |
| 7 | Full tests, real launch verification, cleanup (remove old UI, matplotlib, smoke check rewrite, README) | pending |

## Current phase

Milestone 6 complete. Next: Milestone 7 (cleanup: delete old UI files + matplotlib, rewrite smoke_check.py, packaging config, README; full tests; real launch + restart verification; final report).

## Audit result (M1): gaps between v1.0.0 and the frozen spec

- v1 UI = sidebar navigation ("记账 / 查看账单"), brand block, form with mandatory category combo, table + edit dialog + confirm dialog. Spec: two full-window spaces Capture ⇄ Review, dots only, no brand, no category in Capture, in-place edit, undo instead of confirm.
- v1 schema stored `category NOT NULL IN ('饮食','工具','娱乐')`. Spec categories are 生活/工具/娱乐 and category is a *derived* interpretation that may be unknown.
- v1 chart = matplotlib pie with percentages inside cards; spec = restrained donut, no percentages, no cards.
- No search, no draft, no undo in v1.

## Done in M1 (files)

- `domain.py`: `CATEGORIES = (生活, 工具, 娱乐)`, category may be `None` (unknown), `summarize_records` adds `unknown` (total always includes it), grouped static amounts `¥2,438.50`, `cents_to_input`, `group_by_day`, `describe_time/day/month`, `parse_stored_datetime`.
- `database.py`: schema v2 (`category` nullable, CHECK on the three names), `PRAGMA user_version = 2`. v1 → v2 migration: validate → SQLite backup `ledger.sqlite3.before-v2.bak` → `BEGIN IMMEDIATE` table rebuild (`饮食` → `生活`, ids/timestamps preserved, `sqlite_sequence` kept so ids never reuse) → verify → commit. Failures roll back and leave the v1 file byte-identical. New queries: `get_record`, `restore_record` (undo delete, same id), `search_records` (LIKE on description, escaped), `latest_category_for` (exact-text history match).
- `classification.py`: `derive_category(description, lookup)` — only layer 1 of Philosophy §4.5 (identical description → latest user category); everything else stays unknown. Deliberately tiny; the formal Adaptive Classification spec is not frozen.
- `ledger.py`: `Ledger` service (create / undo_create / month / search / update / delete / restore) + `MonthView`. UI must go through this, never SQL.
- `draft.py`: `Draft` + `DraftStore` (JSON file `draft.json` in the data directory; never in the DB).
- Tests: `tests/test_migration.py`, `tests/test_ledger.py`, `tests/test_draft.py`; existing tests updated for the rename (`饮食`→`生活`) and the `unknown` total key. Old UI tests still pass against the old UI (interim).

## Done in M2 (files)

- `ui/theme.py`: PC Light tokens (neutrals, slate accent, category greens/blues/ambers, danger), `font(px, weight, tabular)`, global stylesheet. **Rule:** never put `font-size`/`font-family` on `QWidget` in QSS — it overrides `setFont` and flattened the type scale once already; the app base font is set programmatically (`theme.BASE_PX`).
- `ui/toast.py`: bottom-centre overlay, fade-in, auto-dismiss (5 s / 8 s danger), single `撤销` action; a new toast expires the previous undo.
- `ui/capture_page.py`: `AmountEdit` (width follows the number so ¥+number stay centred; validator; static formatting only on focus-out/save), description (no chrome, focus underline, `做了什么？`), weak time button + `TimePopover` (Qt.Popup, QDateTimeEdit + 现在), `记录` (disabled while amount empty), local `amount_error` / `save_error(+detail)`. Enter path: amount → description → record; empty description records. Save clears only after the ledger confirmed. Undo deletes the record and restores amount text / description / time. `draft()` / `restore_draft()` / `focus_default()`.
- `ui/main_window.py`: rewritten shell (title `Cashing`, no sidebar/status bar/brand), hosts Capture + the *old* `RecordsPage` (interim) in a `QStackedWidget`; Alt+←/→ switch; draft saved on close, restored on start. `main.py` now passes the data directory.
- Tests: `tests/test_ui_capture.py` (17 cases). Old `test_ui.py` / `test_ui_audit.py` trimmed to the Review parts and pointed at `window.review` (interim).
- Gotcha recorded: `QTest.keyClicks` with CJK text hard-crashes the native Windows QPA (fine offscreen) — tests type ASCII or use `setText` for CJK.

## Done in M3 (files)

- `ui/spaces.py`: `SpaceSwitcher` (pages side by side in a strip; `offset` property animated 180 ms OutCubic, no overshoot; resize re-aligns), `PageDots` (● ○, clickable, NoFocus), `EdgeZone` (28 px strip, faint chevron only on hover, click switches; only the edge that leads somewhere is shown), `WheelNavigator` (application event filter: dominant horizontal `angleDelta().x()` accumulated to 150 units within a 0.3 s gesture → switch, then 0.5 s cooldown; vertical untouched; ignored while a popup is open; negative dx = content follows fingers = go right).
- `ui/main_window.py`: uses the switcher; overlays (dots, edges, toast) are children of the central widget, repositioned in `_update_overlays`; `switch_to(index)` clamps (no wrap), returns False when already there; Alt+←/→ shortcuts; plain ←/→ untouched (text editing).
- Tests: `tests/test_ui_spaces.py` (8 cases). Native drive `work/drive_m3.py` confirmed the slide (mid-frame offset 745/900) and focus return to the amount.

## Done in M4 (files)

- `ui/review_page.py`: `ReviewPage` = fixed header (‹ month ›; › disabled at the current month, month label click = back to now, ‹ disabled at 1900-01) + one vertical `QScrollArea` (column ≤ 600 px, centred). `SummaryBlock`: neutral total (`¥` 22 px + number 40 px Medium tabular), `CategoryLine` ×3 (8 px dot, name, right-aligned tabular amount) + a weak `暂未判断` line only when unknown > 0, `DonutChart` (QPainter, 112 px, 14 px ring, 2.5° gaps, unknown share as a neutral light-grey arc, nothing in the centre; not drawn when the month is empty → `本月暂无记录`). `HistoryList` rebuilds `DayHeading` (`9 月 20 日 星期日`) + `RecordRow` (grid: time 13 px grey / amount 17 px Medium tabular; description 16 px elided / category 6 px dot + 13 px grey; blank for unknown). Rows reserve `EDGE_ROOM` = 44 px on the right for the M5 delete edge, hover = faint rounded tint, `clicked(row)` signal ready for M5. `clear()` hides + unparents before `deleteLater` so a month never shows mixed data. Read failure: total `—`, rows cleared, message.
- `ui/theme.py`: month arrow / month label styles.
- `ui/main_window.py`: uses `ReviewPage(ledger, notify)`; Review refreshes on every Capture change and on entering the space.
- Tests: `tests/test_ui_review.py` (10 cases) replaces `tests/test_ui.py` + `tests/test_ui_audit.py` (their intents ported: chart/navigation/bounds, long plain description, refresh reuse + failure never looks empty, no duplicate widgets after repeated switching, destruction after close; edit/delete intents move to M5). Native drive `work/drive_m4.py` screenshots checked.

## Done in M5 (files)

- `ui/record_row.py` (new; `ElidedLabel`, `DayHeading`, `DeleteEdge`, `CategoryBox`, `RecordRow` moved here): single click → `begin_edit(cell)` swaps labels for frameless editors of identical heights (`LINE1_HEIGHT`/`LINE2_HEIGHT`), accent bar + `ACCENT_TINT` painted in `paintEvent`, no shadow. Each field commits on `editingFinished` (category on index change) through `Ledger.update`; unchanged → no write; `ValueError`/`DatabaseError` → hint under the row, stay in Edit. Enter (event filter on editors, also catches validator-intermediate text like `5.`) = commit all + leave; Esc = reload fields + leave; Tab = next field; Delete with focus on the row itself = `delete_requested`; Delete inside a field edits text. `edit_ended` tells the page whenever the row leaves Edit. `DeleteEdge` lives in the reserved 44 px: 3 px danger strip, `enterEvent` animates to 40 px with `删除` on `DANGER_TINT`, click → delete.
- `ui/review_page.py`: `editing_row` state; `leave()` (used by month change, page switch, search later) returns False while a field is invalid; `ClickOutsideGuard` (application mouse-press filter armed only during an edit: presses outside the row end the edit, or are swallowed if it is invalid; popups excluded). `_row_changed` refreshes only the summary immediately and defers the re-sort until the edit ends when the datetime changed. `_delete_row` → `Ledger.delete` → rebuild keeping scroll → toast `已删除 ¥ · 说明  撤销` → `Ledger.restore` (same id, same place) → Browse. Failures: `删除失败，这条记录仍然保留。` / `无法恢复，这条记录仍处于已删除状态。` as danger toasts. Column is now centred with stretch factors (an aligned widget only got its size hint and the list jumped 372→514 px when editors were built — fixed in Capture too).
- `ui/main_window.py`: `switch_to(CAPTURE)` refuses while an edit is invalid. `ui/theme.py`: `#rowEdit` styles.
- Tests: `tests/test_ui_edit.py` (14 cases). Native drive `work/drive_m5.py` confirmed edit → commit → delete → undo.

## Done in M6 (files)

- `ui/review_page.py`: header = `QStackedWidget` (month row | search row) + `SearchGlyph` (painted magnifier, hidden while searching). `enter_search()` (glyph, Ctrl+F in Review) only after `leave()`; saves scroll, hides summary, clears rows, focuses the field. Live search debounced 150 ms → `Ledger.search` across all history, day groups with year headings, `没有找到“…”相关记录` when empty; read failure reported. Results use the same edit/delete/undo machinery and `refresh()` re-runs the search so the context is kept. `exit_search()` (×, Esc with no edit) restores month + scroll. `prepare_leave()` = leave edit (refuse if invalid) then exit search; `MainWindow.switch_to(CAPTURE)` uses it.
- `ui/main_window.py`: `⋮` `QToolButton#utility` overlay top-right on both spaces, InstantPopup `QMenu`: `打开数据目录` (QDesktopServices) and `关于 Cashing` (QMessageBox.about with version + ledger path). No settings.
- `ui/theme.py`: `#search`, `#searchGlyph` styles.
- Tests: `tests/test_ui_search.py` (6 cases). Native drive `work/drive_m6.py` checked the search header and cross-year results.
- Draft: implemented in M2 (`draft.py`, Capture `draft()/restore_draft()`, window close/start); real-process restart check is part of M7.

## Spec items implemented so far

- Store facts, derive interpretation; unknown category allowed and never a task (domain/db level).
- Capture (IA §5, Interaction §2–§9, VDS §10/§11/§21, Amendments §1): default focus, Enter path, no category control, weak time with light editor, write-before-clear, stay in Capture, toast + undo restoring input, local errors, draft on close.
- Search as a temporary Review state across all history, editable results that keep the context, exit restores month + scroll, leaving the space exits search (IA §12, Interaction §17–§18); Utility as a low-presence ⋮ with 数据/关于 only (IA §14).
- In-place Edit / Delete Armed / Undo (IA §10–§11, Interaction §12–§16, §23–§25, Amendments §5–§7): click to edit in place, legal changes at once, illegal ones explained locally and blocking, click outside exits, Esc cancels, Delete only on a selected record, PC delete edge, execute + undo instead of confirm.
- Review = Summary + History in one reading (IA §6–§9, VDS §20/§22, Amendments §2–§4): month nav with no future, neutral total, three categories without percentages, small ring without centre text, empty month without ring, history by day with two-line rows, no per-row separators, category weakest.
- Two spaces, fixed left/right relation, no wrap, wordless dots, edge click, Alt+←/→, trackpad horizontal wheel, short non-elastic slide (IA §3, Interaction §19–§21, §24, Amendments §8).
- Backward-compatible migration with tests (real user ledger at `%LOCALAPPDATA%\Cashing\ledger.sqlite3` was inspected via a copy only: schema v1, 0 records).

## Not yet implemented

Everything visual/interactive (M2–M6); removal of old UI/matplotlib (M7).

## Known issues

- `ui/records_page.py`, `ui/edit_dialog.py`, `ui/record_form.py`, `ui/input_page.py` are dead files kept only until M7's cleanup, together with the matplotlib dependency.
- Delete-edge hover expansion and the edit tint/bar need human visual validation (synthetic mouse moves do not produce enter events).
- `smoke_check.py` still drives the old UI and cannot run; rewritten in M7.
- Month switch has no fade (Interaction §22 says "may"); content simply replaces. Trackpad wheel direction, edge chevrons and the ring need human visual validation.

## Tests run

- M1: `pytest --basetemp ./work/pytest-m1b -q` → 132 passed (100 original + 32 new/updated).
- M2: `PYTHONUTF8=1 pytest --basetemp ./work/pytest-m2 -q` → 148 passed.
- M3: `PYTHONUTF8=1 pytest --basetemp ./work/pytest-m3 -q` → 156 passed.
- M4: `PYTHONUTF8=1 pytest --basetemp ./work/pytest-m4 -q` → 154 passed (old table/dialog tests removed, Review tests ported).
- M5: `PYTHONUTF8=1 pytest --basetemp ./work/pytest-m5 -q` → 168 passed.
- M6: `PYTHONUTF8=1 pytest --basetemp ./work/pytest-m6 -q` → 174 passed. Native-platform drive script `work/drive_m2.py` (not committed) produced screenshots and confirmed Enter path, toast, undo.
- Launch check: `python main.py --data-dir D:\Dev\Cashing\work\m1-launch` starts with empty stderr.

## Resume here

Start Milestone 7 (cleanup + verification):
1. Delete dead files: `ui/input_page.py`, `ui/records_page.py`, `ui/edit_dialog.py`, `ui/record_form.py`.
2. Remove matplotlib: `requirements.txt`, `requirements-lock.txt` (matplotlib + its transitive deps), `Cashing.spec` (hiddenimports/hooksconfig), `paths.py` (`MPLCONFIGDIR` / cache dir), `tests/conftest.py`, `scripts/package_release.py` (required file + packages list).
3. Rewrite `smoke_check.py` for the new UI (Capture Enter path → toast → Review totals/rows → edit → delete → undo → search → month nav → screenshots → reopen persistence), keeping the isolated-directory guarantees; `main.py` already passes the data directory.
4. README: describe the new UI and data locations (draft.json, backup file), keep data/backup guidance.
5. Run the full suite, launch the source app against an isolated data dir twice (restart persistence + draft), and against a copy of a v1 ledger (migration). Never touch `%LOCALAPPDATA%\Cashing`.
6. Write the final report (see the task's section 三十九).
