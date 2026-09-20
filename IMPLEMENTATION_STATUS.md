# Cashing UI v2 (PC Light Mode) — Implementation Status

Branch: `ui-v2-pc-light` (based on `main` @ fef67a5, v1.0.0). One commit per milestone (M1–M7).
Normative inputs: `docs/design/*.md` (priority: Philosophy > IA > Interaction > Visual > PC Light Amendments > PNG).
A new session can resume from this file + git history + `docs/design/` alone.

## Milestones

| # | Milestone | State |
|---|-----------|-------|
| 1 | Spec audit + minimal core architecture (schema v2, migration, ledger service, draft store, classification interface) | **done** |
| 2 | Capture rebuild (amount hero, description, weak time + popover, 记录, Enter flow, save/undo toast, local errors) | **done** |
| 3 | Capture ⇄ Review spaces + horizontal page switching (dots, edges, Alt+←/→, trackpad wheel) | **done** |
| 4 | Review Summary + History (month nav, total, three categories, donut, day groups) | **done** |
| 5 | In-place edit, PC delete edge, delete/undo | **done** |
| 6 | Search, Utility (⋮), Draft persistence | **done** |
| 7 | Cleanup (old UI + matplotlib removed, smoke check rewritten, packaging/README), full tests, real launch/restart/migration/frozen verification | **done** |

## Current phase

All seven milestones complete on `ui-v2-pc-light`. Not merged into `main`; no release package produced (the v1.0.0 release in `release/` is untouched). Remaining work is human visual acceptance (see below) and release decisions (version bump, merge).

## Architecture (after this round)

```
ui/  (Qt)            main_window → spaces (SpaceSwitcher/PageDots/EdgeZone/WheelNavigator)
                     capture_page, review_page, record_row, toast, theme
ledger.py (core)     create / undo_create / month / search / update / delete / restore  — no Qt
classification.py    derive_category(description, lookup): identical description → latest category, else None
draft.py             Draft + DraftStore (draft.json beside the ledger; never in the DB)
domain.py            categories (生活/工具/娱乐 or None), money (integer cents), formatting, grouping, time text
database.py          all SQL; schema v2; v1→v2 migration with backup; strict validation of stored rows
paths.py             data directory / smoke-directory isolation
```

Rule kept from v1: the UI never writes SQL; everything goes through `Ledger`.

## Key decisions and gotchas (read before changing code)

- **Category is a derived interpretation.** `records.category` is nullable in v2; `None` = "暂未判断", shown only as a very weak line in the Review summary (and a neutral light-grey arc in the ring) when non-zero. The total always includes it. Never a task, badge or fourth category.
- **v1 `饮食` → v2 `生活`.** The migration renames the first bucket (1:1, reversible via the backup). Migration = validate → SQLite `backup()` to `ledger.sqlite3.before-v2.bak` → `BEGIN IMMEDIATE` table rebuild → verify → commit; failures roll back leaving the v1 file byte-identical. Ids and `sqlite_sequence` are preserved.
- **Classification is deliberately minimal** (Philosophy §4.5 layer 1 only). New records get the latest category the user gave an identical description (case-insensitive ASCII, trimmed); otherwise `None`. Replace `classification.py` when the Adaptive Classification spec is frozen.
- **QSS must not set `font-size`/`font-family` on `QWidget`**: stylesheet fonts override `setFont` and flatten the type scale. Base font is set programmatically (`theme.BASE_PX`), sizes via `theme.font(px, weight, tabular)`.
- **Centre columns with stretch factors, not alignment flags**: an aligned layout item only gets its size hint; the Review list jumped 372→514 px when editors were built until this was fixed (M5).
- **`HistoryList.clear()` hides + unparents before `deleteLater`** so a month switch never shows old and new rows together.
- **`QTest.keyClicks` with CJK text hard-crashes the native Windows QPA** (fine offscreen). Tests and the smoke check type ASCII or use `setText` for CJK.
- **Undo** = toast action: save-undo deletes the record and restores amount text / description / time; delete-undo re-inserts the snapshot with the same id (`restore_record`). A new toast expires the previous undo.
- **Edit state**: `RecordRow.edit_ended` is the single source of truth for leaving Edit; `ReviewPage.leave()` (edit) and `prepare_leave()` (edit + search) gate month change, search entry and page switch. `ClickOutsideGuard` is an application-level mouse filter armed only while editing.
- **Trackpad wheel**: `WheelNavigator` (application filter) treats a dominant horizontal `angleDelta().x()` accumulated to 150 within 0.3 s as a page move, then 0.5 s cooldown; negative dx (content follows fingers) goes right. Direction on real hardware is unverified.

## Spec coverage

Implemented: IA §1–§12, §14 (数据/关于 only), §15–§19; Interaction §1–§9, §10–§21 (PC), §23–§28; VDS §3–§17, §20–§26 (Light only); Amendments §1–§13.
Deliberately not done: Dark Mode, mobile, month-switch fade (Interaction §22 "may"), export/import, any settings, any classifier beyond exact-description reuse, version bump / release packaging / merge.

## Files changed this round

Core: `domain.py`, `database.py`, `ledger.py` (new), `classification.py` (new), `draft.py` (new), `paths.py`, `main.py`.
UI: `ui/theme.py`, `ui/toast.py`, `ui/spaces.py`, `ui/capture_page.py`, `ui/review_page.py`, `ui/record_row.py` (all new), `ui/main_window.py` (rewritten). Deleted: `ui/input_page.py`, `ui/records_page.py`, `ui/edit_dialog.py`, `ui/record_form.py`.
Tooling: `smoke_check.py` (rewritten for the new UI), `Cashing.spec`, `requirements*.txt` (matplotlib removed), `scripts/package_release.py`, `tests/conftest.py`, `README.md`.
Tests: new `test_migration.py`, `test_ledger.py`, `test_draft.py`, `test_ui_capture.py`, `test_ui_spaces.py`, `test_ui_review.py`, `test_ui_edit.py`, `test_ui_search.py`; updated `test_database.py`, `test_reliability.py`, `test_audit_regressions.py`; removed `test_ui.py`, `test_ui_audit.py` (intents ported).

## Tests and verification (final)

- `PYTHONUTF8=1 pytest --basetemp ./work/pytest-m7f -q` → **174 passed, 0 failed, 0 skipped**; also clean with `-W error`. `pytest.ini` already turns ResourceWarning / unraisable warnings into errors.
- `pyflakes` clean on all files touched this round.
- Real processes (native Windows QPA, isolated data dirs under `work/`, real `%LOCALAPPDATA%\Cashing` never touched):
  - `python main.py --data-dir … --smoke-test` twice in the same directory: run 1 PASS (43 checks), run 2 PASS (46 checks: persistence across restart, draft restored, draft not counted, draft focus rule). stderr empty.
  - `scripts/verify_release.py --phase source --label ui-v2-source`: PASS, 5 GUI processes (2 restart runs + scales 1.25/1.5/2 → device pixel ratios 1.5/1.875/2.25/3.0; at 3.0 the window is 813×449 and still lays out).
  - `main.py --data-dir work/m7-migrate` with a synthetic **v1** ledger (饮食/工具/娱乐 rows): after launch `user_version = 2`, rows mapped, `ledger.sqlite3.before-v2.bak` holds the v1 copy, empty log.
  - `build.ps1` → `dist/Cashing/Cashing.exe` (115 MB, no matplotlib/numpy); the frozen EXE passes the same two smoke runs (43 / 46 checks, empty stderr). `scripts/package_release.py` was **not** run (version unchanged; existing v1.0.0 release kept).
- Screenshots reviewed during development: `work/shots/*.png` (not committed).

## Needs human visual acceptance

- Trackpad two-finger horizontal swipe: direction, threshold feel, no interference with vertical scrolling.
- Edge-zone chevron on hover, delete-edge expansion on approach, row hover/edit tint strength (synthetic mouse moves produce no enter events).
- Slide animation feel (180 ms OutCubic), toast fade, time popover placement, category chevron, ring proportions, overall spacing on a real 100 %/125 %/150 % display.
- A month where every record is still 暂未判断 shows three ¥0.00 lines and a fully grey ring (honest but bare) — decide if acceptable until the classifier exists.

## Known issues / open decisions

- Version still reads 1.0.0 (`main.py`, `version_info.txt`, README title, `package_release.py` NAME); a release of this UI should bump it — not done here.
- `DeleteEdge` hit zone is the whole reserved 44 px room (the painted strip is 3 px) so it can be reached; the strip itself is small by design.
- Windows 10, clean machines, real IME input, multi-monitor moves: not verified (same limits as v1).
