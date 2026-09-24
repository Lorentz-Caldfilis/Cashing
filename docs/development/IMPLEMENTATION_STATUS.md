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
classification.py    Classifier: the person's phrase votes → longest match of their phrases + lexicon.py → None
                     (derived on every read by Ledger; never stored — see docs/development/CLASSIFICATION.md)
draft.py             Draft + DraftStore (draft.json beside the ledger; never in the DB)
domain.py            categories (生活/工具/娱乐 or None), money (integer cents), formatting, grouping, time text
database.py          all SQL; schema v2; v1→v2 migration with backup; strict validation of stored rows
paths.py             data directory / smoke-directory isolation
```

Rule kept from v1: the UI never writes SQL; everything goes through `Ledger`.

## Key decisions and gotchas (read before changing code)

- **Category is a derived interpretation.** `records.category` is nullable in v2; `None` = 尚未分类, shown only as one very weak sentence under the three categories ("另有 ¥X 尚未分类", no dot, no colour, nothing to click) when non-zero, plus a neutral light-grey arc in the ring whenever a ring is drawn at all. The total always includes it. Never a task, badge or fourth category.
- **v1 `饮食` → `生活`; v1/v2 → v3.** The migration renames the first bucket (1:1, reversible via the backup) and marks every stored category as the person's (`category_by_user = 1`). Migration = validate → SQLite `backup()` to `ledger.sqlite3.before-v3.bak` → `BEGIN IMMEDIATE` table rebuild → verify → commit; failures roll back leaving the v1 file byte-identical. Ids and `sqlite_sequence` are preserved.
- **Only the person's categories are stored** (schema v3). `Ledger` derives the rest on read, so never pass a record from the UI back into `Database` as if its `category` were stored: `Ledger.delete` hands back the stored row, `Ledger.update` rereads it. Direct `Database` writes (tests, smoke) are fine: `month()` / `search()` rebuild the classifier from the stored labels.
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

## Follow-up round: edit-state convergence (row only)

Scope limited to `ui/record_row.py` + the `#rowEdit` rules in `ui/theme.py` (+ tests). Editors read as text at rest
(the description kept a faint hint underline and hover showed one too — both removed in the round below); time shows `HH:mm`
and the full date only while focused (`_set_time_format` reopens the date range — QDateTimeEdit pins the range to the
current date while only time sections are shown); `¥` fixed prefix + `FittedLineEdit` so the amount stays one
right-anchored unit; category is a bare word with a small chevron; row padding 7 / lines 21+24 → 59 px in Rest and Edit
(grid spacing 0 — QGridLayout dropped its 1 px row spacing after an edit, which made rows jump 59→58); delete edge
2 px at 55 % alpha, expands to 36 px `删除` on approach; left bar unchanged at the time (3 px accent — dropped in the
round below). 176 tests, smoke ×2 PASS.

## Follow-up round: visual refinement / optical polish

No new elements, no structural change, no motion change (`ui/motion.py` untouched). `ui/theme.py`, `ui/capture_page.py`,
`ui/review_page.py`, `ui/record_row.py` (+ one test).

- **Ink is five levels** and they are meant to be told apart by eye: `TEXT #1b2430` / `TEXT_2 #4e5b69` /
  `TEXT_3 #87909c` / placeholder (~`#a7b0bc`, from `PLACEHOLDER_SOURCE` at Qt's half alpha) / disabled (an inert
  surface, not faint text). The Capture description used to draw its prompt at half of `TEXT` — darker than the
  amount's — and now shares the one placeholder level through the same `empty` property.
- **Review summary is no longer stretched onto the history's anchors.** The three categories are a 260 px group
  beside the ring, and the cluster sits on the page's centre line (`STRUCTURE_OPTICAL` 6 px left of it: words on the
  left, a dense ring on the right). The ring is 98/7 instead of 116/9. `SUMMARY_TO_HISTORY` 52 → 72 and the body's
  top margin 18 → 8, so the page reads month → total (tight) → shape → records (open).
- **`¥` is part of the number.** `CurrencyMark` paints the mark on the digits' own baseline with one optical gap
  (bottom-aligning two fonts left it ~2 px high and ~2 digits away); the pair is set `CURRENCY_OPTICAL` left of the
  box centre so the digits land on the axis. An empty amount mutes the mark with the digits. In a record the mark
  is `TEXT_2` at rest too (`RowAmount`), which is what Edit already showed.
- **Month navigation is painted** (`MonthArrow`): `‹` at 22 px is four pixels of ink. Chevron on the month's optical
  centre, ~15 px from the words; the label's padding is uneven because 月 has the wider side bearing.
- **Edit sheds its form.** No line under any field at rest, none on hover; the focused field paints a line as wide as
  its own text, just clear of it. The left accent bar is gone — `ACCENT_TINT` was within a hair of `HOVER`, so the
  bar was carrying the whole difference; Hover is now `#f1f3f6` and Edit `#e9edf4`, which separates them on their own.
- Rest/Edit ink verified equal at 1.5× on both lines (left ≤0.7 px, right edges equal); the time now shares the
  amount's baseline (`TIME_BASELINE_PAD`, mirrored in the editor's text margins).
- Capture: `TEXT_TO_TIME` 2 / `TIME_TO_ACTION` 36 so what+when is a pair and the action stands apart; the visible
  group sits at ~43 % of the window (`ABOVE`/`BELOW` place the visible group, not the column, which carries a
  reserved error slot); the record button is 96×34 r5 on `ACTION` (the accent lightened one step, white still at AA).

178 tests, no-motion run, smoke ×2 (43 / 46 checks, empty stderr). Screenshots reviewed: Capture empty / typed /
focused, Review unclassified / classified / history / edit / search / toast, at 1000×760 and 1320×860.

## Follow-up round: aesthetic synthesis pass

No new elements, information, motion or structure. `domain.py` (dates), `ui/review_page.py`, `ui/record_row.py`,
`ui/theme.py`, `ui/main_window.py` (+ tests, README). Measured, not eyeballed: ink probes compare Rest/Edit per field.

- **One grid for Review.** `MEASURE = 400` (Capture's column width) from the text edge to the value edge. Category
  names, the unknown note, day headings, times and descriptions start on the text edge; the ring and every record amount
  end on the value edge; the two edges sit evenly about the centre line the month and total use. Rows keep the delete
  edge's room after their values, so the list starts `HISTORY_LEAD` (= `EDGE_ROOM`) into a `COLUMN_WIDTH` column that is
  symmetric about the axis (before: a 612 px record span whose ink sat 22 px left of the axis). Category dots hang in
  the margin (`DOT_LEAD`) so the names, not the dots, are on the edge.
- **No ring, no slot.** The ring and the air before it are one `chart_slot`; a month with nothing classified hides it
  and the three lines move onto the centre line (spatial stability yields to balance here, by decision).
- **Edit is a bar, not a card.** `ACCENT_TINT` `#e9edf4` → `#eef1f5` (a shade above Hover) and a 2 px accent bar
  beside the two text lines carries the state (the Visual spec's "细 Accent 色条 + 极弱背景"). Radius unchanged.
- **Chinese dates**: `2026年9月`, `9月22日 星期二`, `9月18日 12:00` — no Western space between digits and 年/月/日.
  Month label padding rebalanced for the new string (chevron gaps 16.0 / 16.0 px).
- **Edit moved text and clipped it** (the previous check read left edges, which the clip hid): time and description
  shifted 2 px left and lost their first stroke (晚); ¥ was 2 px narrower than its glyph; the amount's caret at the end
  sat outside the field (never drawn). Now: `TIME_TEXT_NUDGE -6`, `DESCRIPTION_TEXT_NUDGE -2`, ¥ at full advance, the
  whole value column keeps `CARET_ROOM` in both states, amount field margins `(-2, -2)`. Resting labels that an editor
  replaces draw on the editor's own baseline (`field_baseline`: whole-pixel line top + fractional ascent, as QLineEdit
  does) — Rest = Edit to ≤0.04 px at 1.25×/1.5×/1.75×/2×/2.5×; before, the digits dropped a device pixel at 2×.
- **Search field on the grid**: max width `MEASURE + 30`, so the typed query starts on the text edge above the
  descriptions it finds (shrinks to 280 on narrow windows). The mirror that centres it now uses ×'s fixed width, not its
  font-dependent size hint (which pushed the field 12 px off centre under other fonts).
- **⋮ on the header line** (`HEADER_LINE`), level with the month and 🔍 instead of 19 px above them; same place in Capture.

182 tests (+4: shared grid, no-ring room, caret/¥ in Edit, query on the text edge; the utility test also checks the
header line), `-W error`,
no-motion run, smoke ×2 (43 / 46 checks, empty stderr), pyflakes clean on touched files.

## Follow-up round: productization / completion pass

Why it read as a script: no window skeleton (the list slid under the page dots and was sliced by an
unmarked edge under the month; Review sat 5 px off the window's centre line; the search glyph hugged the
window edge), controls that were not one family (26×30 / 32×30 / 32×32 boxes, font glyphs beside painted
ones, no pressed state), focus that leaked from the mouse (a frame stayed on the time or the month after a
click), popups that behaved like defaults (a box inside the time layer writing `2026-09-23`; the ⋮ menu
hanging outside the window), and a toast that blinked out. No information, structure or motion curve added.

- **Skeleton.** One axis: `PAGE_SIDE` reserves the scroll-bar gutter on both sides, so Review, Capture, the
  dots and the toast share the window's centre line. `FOOTER_HEIGHT` (in `ui/spaces.py`) is a band the dots
  sit on the middle of (`DOTS_BOTTOM` derived); the Review list stops above it, and the toast rests on it.
  `EdgeLine` hairlines at the header and footer edges fade in only while records continue past that edge.
- **Header on the grid.** The header uses the body's centred column: month centred, the search glyph's ink
  ending on the value edge (`SEARCH_GLYPH_CENTRE`), ⋮ kept at the window corner (window-level). × lives
  inside the search field (`SearchField`), centred exactly where the magnifier was (the IA's `[ 搜索记录… × ]`).
- **One control family** (`ui/controls.py`): `IconButton` → `ChevronButton`, `SearchButton`, `CloseButton`,
  `MoreButton`; 32 px, one 1.5 px stroke, painted ⋮ and ×, hover / `PRESSED` surfaces blended with the existing
  HOVER / PRESS durations, a `FOCUS_RING` (3.3:1) for keyboard focus. Every button — icon or text (month, time,
  记录, 现在, 撤销) — takes focus from the keyboard only (`TabFocus`), so a click never leaves a frame; text
  buttons gained `:pressed`. `QuietDateTimeEdit` moved here (shared by the row editor and the time layer).
- **Popups.** The time layer is one object: `QuietDateTimeEdit` in `yyyy年M月d日 HH:mm`, no inner box, same
  focus line as a record's time. The ⋮ menu (`AnchoredMenu`) opens under its button, right edges aligned.
- **Toast** fades out on expiry with the same curve and duration it fades in with; the undo is withdrawn at
  once, and Undo itself still hides it immediately.

189 tests (+7: shared axis / footer band, scroll edges, × in the magnifier's place, anchored menu, no focus
after clicks, time-layer format and focus return, toast fade-out), `-W error`, no-motion run, smoke ×2
(43 / 46, empty stderr). Rest = Edit ink still exact at 1.5×.

## Follow-up round: adaptive classification (schema v3)

Replaces the exact-description-only `classification.py`. Design, alternatives and numbers:
`docs/development/CLASSIFICATION.md`; benchmark: `scripts/classification_benchmark.py`.

- **Store facts, derive interpretations, literally.** Schema v3 adds `category_by_user`; `category` holds
  only what the person stated (`NULL, 1` = they chose 暂未判断). The software's judgement is never
  written: `Ledger.month()` / `search()` rebuild the classifier from the stored labels (~20 ms per 10k
  labels incl. the query) and derive each record's `category` on read. v1/v2 categories migrate as the
  person's; backup is now `ledger.sqlite3.before-v3.bak`. The version gate accepts 0/1/2/3.
- **Algorithm** (stdlib only): the person's phrase (recency-weighted votes + built-in prior 0.8, winner
  must be 2× the runner-up, else the built-in opinion stands) → longest match of the person's phrases and
  `lexicon.py` words (ambiguous words block built-in evidence; all must agree) → undecided.
  One exception does not reinterpret a whole phrase; two consistent corrections do.
- **UI**: one hook — `HistoryList.reinterpret()` re-reads other visible rows in place after a category or
  description change (`ReviewPage._row_changed`); nothing else in `ui/` changed.
- Benchmark (new user, month 6): 99.2–99.4 % precision at 82–83 % coverage; from v1 99.4–99.6 % at
  85–88 %; the old behaviour covered ~30 %. Embedding / local LLM not adopted (no local model; bounded
  gain ≤ ~10 % coverage vs. +100 MB and numpy) — reasoning in the doc.

236 tests (`-W error`), pyflakes clean on touched files, smoke ×2 (43 / 46, empty stderr). Frozen build
not rebuilt this round (`lexicon.py` is a plain import; PyInstaller picks it up).

## Repository tidy-up

`smoke_check.py` moved to `scripts/` (imported by `main.py --smoke-test` as `scripts.smoke_check`, an implicit
namespace — no package restructuring; PyInstaller collects it). `*.bak` (pre-upgrade ledger copies) is ignored.

## Needs human visual acceptance

- Trackpad two-finger horizontal swipe: direction, threshold feel, no interference with vertical scrolling.
- Edge-zone chevron on hover, delete-edge expansion on approach, row hover/edit tint strength (synthetic mouse moves produce no enter events).
- Motion feel on a real display: one curve (cubic-bezier 0.2, 0, 0, 1) and one duration table in `ui/motion.py`
  — press 90, hover 110, focus 140, edit 150, month 160, search 170, toast 180, record 200, space 200 ms.
  `CASHING_NO_MOTION=1` turns all of it off; every state still arrives, which is how the static composition is checked.
- Slide feel, toast fade, time popover placement, category chevron, ring proportions, overall spacing on a real 100 %/125 %/150 % display.
- A month where every record is still unclassified shows three ¥0.00 lines and no ring: without a classified share there is no proportion to draw.
  The lines then sit on the centre line; classifying a record brings the ring back and the lines return to the grid at once (no animation).
- The 400 px measure at wide windows (1320+), the Edit accent bar's strength, and the ⋮'s new height in Capture.
- Scroll-edge hairlines and the footer band on a real display; the keyboard focus ring's strength; the time layer's
  width (QDateTimeEdit sizes for its longest date).

## Known issues / open decisions

- Version still reads 1.0.0 (`main.py`, `version_info.txt`, README title, `package_release.py` NAME); a release of this UI should bump it — not done here.
- `DeleteEdge` hit zone is the whole reserved 44 px room (the painted strip is 3 px) so it can be reached; the strip itself is small by design.
- Windows 10, clean machines, real IME input, multi-monitor moves: not verified (same limits as v1).
- Rebuilding a month's rows costs ~3 ms per record (Qt style-sheet polish dominates), so a 200-record month takes
  ~600 ms. Refreshes now skip the rebuild when the records are unchanged, and a delete removes only its own row,
  so this is paid once per real data change — but saving a record on a very heavy month still shows it.
