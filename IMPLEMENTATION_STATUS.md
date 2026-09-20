# Cashing UI v2 (PC Light Mode) — Implementation Status

Branch: `ui-v2-pc-light` (based on `main` @ fef67a5, v1.0.0).
Normative inputs: `docs/design/*.md` (priority: Philosophy > IA > Interaction > Visual > PC Light Amendments > PNG).
A new session must be able to resume from this file + git history + `docs/design/` alone.

## Milestones

| # | Milestone | State |
|---|-----------|-------|
| 1 | Spec audit + minimal core architecture (schema v2, migration, ledger service, draft store, classification interface) | **done** |
| 2 | Capture rebuild (amount hero, description, weak time + popover, 记录, Enter flow, save/undo toast, local errors) | pending |
| 3 | Capture ⇄ Review spaces + horizontal page switching (dots, edges, Alt+←/→, trackpad wheel) | pending |
| 4 | Review Summary + History (month nav, total, three categories, donut, day groups) | pending |
| 5 | In-place edit, PC delete edge, delete/undo | pending |
| 6 | Search, Utility (⋮), Draft persistence | pending |
| 7 | Full tests, real launch verification, cleanup (remove old UI, matplotlib, smoke check rewrite, README) | pending |

## Current phase

Milestone 1 complete. Next: Milestone 2 (Capture).

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

## Spec items implemented so far

- Store facts, derive interpretation; unknown category allowed and never a task (domain/db level).
- Backward-compatible migration with tests (real user ledger at `%LOCALAPPDATA%\Cashing\ledger.sqlite3` was inspected via a copy only: schema v1, 0 records).

## Not yet implemented

Everything visual/interactive (M2–M6); removal of old UI/matplotlib (M7).

## Known issues

- Old UI (`ui/input_page.py`, `ui/records_page.py`, `ui/edit_dialog.py`, `ui/record_form.py`) is still wired in `ui/main_window.py` and still asks for a category; it is replaced from M2 on.

## Tests run

- M1: `pytest --basetemp ./work/pytest-m1b -q` → 132 passed (100 original + 32 new/updated).
- Launch check: `python main.py --data-dir D:\Dev\Cashing\work\m1-launch` starts with empty stderr.

## Resume here

Start Milestone 2: create `ui/theme.py` (tokens + stylesheet), `ui/capture_page.py`, a toast widget; wire `Ledger` into the window; port Capture tests. Keep `main.py` data-dir/smoke isolation intact.
