"""Draft ≠ Record: unfinished input survives a restart but never touches the ledger."""
from datetime import datetime
from draft import Draft, DraftStore
from ledger import Ledger


def test_draft_round_trip_and_clear(tmp_path):
    store = DraftStore(tmp_path)
    assert store.load() is None
    store.save(Draft("28.5", "晚饭", "2026-09-20 20:10"))
    loaded = DraftStore(tmp_path).load()
    assert loaded == Draft("28.5", "晚饭", "2026-09-20 20:10")
    assert loaded.when_as_datetime() == datetime(2026, 9, 20, 20, 10)
    store.clear()
    assert store.load() is None
    store.clear()  # idempotent


def test_empty_draft_is_not_stored(tmp_path):
    store = DraftStore(tmp_path)
    store.save(Draft("28.5", "x", ""))
    store.save(Draft("  ", "", ""))
    assert store.load() is None and not store.path.exists()


def test_broken_draft_file_is_ignored(tmp_path):
    store = DraftStore(tmp_path)
    store.path.write_text("{not json", "utf-8")
    assert store.load() is None
    store.path.write_text('{"amount_text": 5, "description": null, "when": "bad"}', "utf-8")
    loaded = store.load()
    assert loaded == Draft("5", "None", "bad") and loaded.when_as_datetime() is None


def test_draft_never_enters_the_ledger(database, tmp_path):
    ledger = Ledger(database)
    DraftStore(tmp_path).save(Draft("28.5", "晚饭", "2026-09-20 20:10"))
    view = ledger.month(2026, 9)
    assert view.is_empty and view.totals["total"] == 0
    assert ledger.search("晚饭") == []
    assert database.user_labels() == []
