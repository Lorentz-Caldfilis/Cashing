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
| 5 | In-place edit, PC delete edge, delete/undo | pending |
| 6 | Search, Utility (⋮), Draft persistence | pending |
| 7 | Full tests, real launch verification, cleanup (remove old UI, matplotlib, smoke check rewrite, README) | pending |

## Current phase

Milestone 4 complete. Next: Milestone 5 (in-place edit on `RecordRow`, PC delete edge, delete + undo toast, Delete/Esc/Enter keys, click-outside exit, invalid edits block leaving).

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

## Spec items implemented so far

- Store facts, derive interpretation; unknown category allowed and never a task (domain/db level).
- Capture (IA §5, Interaction §2–§9, VDS §10/§11/§21, Amendments §1): default focus, Enter path, no category control, weak time with light editor, write-before-clear, stay in Capture, toast + undo restoring input, local errors, draft on close.
- Review = Summary + History in one reading (IA §6–§9, VDS §20/§22, Amendments §2–§4): month nav with no future, neutral total, three categories without percentages, small ring without centre text, empty month without ring, history by day with two-line rows, no per-row separators, category weakest.
- Two spaces, fixed left/right relation, no wrap, wordless dots, edge click, Alt+←/→, trackpad horizontal wheel, short non-elastic slide (IA §3, Interaction §19–§21, §24, Amendments §8).
- Backward-compatible migration with tests (real user ledger at `%LOCALAPPDATA%\Cashing\ledger.sqlite3` was inspected via a copy only: schema v1, 0 records).

## Not yet implemented

Everything visual/interactive (M2–M6); removal of old UI/matplotlib (M7).

## Known issues

- Interim: no editing or deleting until M5 (the old table/dialog UI is no longer wired; `ui/records_page.py`, `ui/edit_dialog.py`, `ui/record_form.py`, `ui/input_page.py` are dead files kept only until M7's cleanup, together with the matplotlib dependency).
- `smoke_check.py` still drives the old UI and cannot run; rewritten in M7.
- Month switch has no fade (Interaction §22 says "may"); content simply replaces. Trackpad wheel direction, edge chevrons and the ring need human visual validation.

## Tests run

- M1: `pytest --basetemp ./work/pytest-m1b -q` → 132 passed (100 original + 32 new/updated).
- M2: `PYTHONUTF8=1 pytest --basetemp ./work/pytest-m2 -q` → 148 passed.
- M3: `PYTHONUTF8=1 pytest --basetemp ./work/pytest-m3 -q` → 156 passed.
- M4: `PYTHONUTF8=1 pytest --basetemp ./work/pytest-m4 -q` → 154 passed (old table/dialog tests removed, Review tests ported). Native-platform drive script `work/drive_m2.py` (not committed) produced screenshots and confirmed Enter path, toast, undo.
- Launch check: `python main.py --data-dir D:\Dev\Cashing\work\m1-launch` starts with empty stderr.

## Resume here (superseded — see below)

Old M4 note: write `ui/review_page.py` — fixed header (‹ 2026 年 9 月 › centred; › disabled at the current month; label click = back to this month), scrollable body: total `¥ 2,438.50` (neutral, 40 px Medium), three categories as a compact list with small colour dots + right-aligned tabular amounts (+ a very weak `暂未判断 ¥X` line only when non-zero), a QPainter donut (~110 px, no centre text, no empty ring: `本月暂无记录`), history grouped by day (`9 月 20 日 星期日`), rows = two lines (time/amount, description/category), no per-row separators. Use `Ledger.month()`. Swap it into `MainWindow` for the old `RecordsPage`; port `test_ui.py`/`test_ui_audit.py` Review tests to the new page (`window.review`). Trackpad wheel direction and edge chevrons still need human validation.

## Resume here

Start Milestone 5 in `ui/review_page.py`: give `RecordRow` an edit mode (swap labels for frameless editors of the same fonts/heights: amount QLineEdit right-aligned with the amount validator, description QLineEdit, time QDateTimeEdit `yyyy-MM-dd HH:mm`, category flat QComboBox 生活/工具/娱乐/暂未判断), accent bar on the left + `ACCENT_TINT` background, no shadow. Commit each field on `editingFinished` through `Ledger.update(record, **change)` (immediate effect); invalid → local hint under the row, stay in edit; Enter = commit + exit, Esc = discard field + exit, Tab = next field, Delete with focus on the row (not in an editor) = delete. Click outside (application-level mouse-press filter) exits when valid. `DeleteEdge` child in the reserved 44 px: 3 px danger strip, expands to ~40 px with `删除` on hover, click → `Ledger.delete` → row removed + toast `已删除 ¥ · 说明  撤销` → `Ledger.restore`. `ReviewPage.leave()` must finish/refuse (invalid) before month change / page switch / search. Port the M5 intents from the removed tests: edit across month moves the record, edit failure keeps the edit open, failed delete keeps the row and totals.
