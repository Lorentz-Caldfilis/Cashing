"""Only synthetic ledgers; backup must preserve facts and never overwrite a file."""
from datetime import datetime
import sqlite3
import pytest
from database import Database, DatabaseError


def test_consistent_backup_preserves_labels_and_can_reopen(database, tmp_path):
    rid = database.add_record(1850, datetime(2026, 9, 20, 12, 0), "工具", "合成打印费")
    destination = tmp_path / "独立备份.sqlite3"
    database.backup_to(destination)
    copy = Database(destination)
    copy.initialize_database()
    assert copy.get_record(rid) == database.get_record(rid)
    database.delete_record(rid)
    assert copy.get_record(rid)["amount_cents"] == 1850
    assert not list(tmp_path.glob(".cashing-backup-*.tmp"))


def test_backup_never_overwrites_existing_file(database, tmp_path):
    destination = tmp_path / "keep.sqlite3"
    destination.write_bytes(b"existing data")
    with pytest.raises(DatabaseError, match="已存在"):
        database.backup_to(destination)
    assert destination.read_bytes() == b"existing data"
    with pytest.raises(DatabaseError):
        database.backup_to(database.path)


def test_failed_publish_keeps_ledger_and_cleans_temporary(database, tmp_path, monkeypatch):
    import database as module
    previous = database.path.read_bytes()
    def fail(*args):
        raise OSError("synthetic unsupported link")
    monkeypatch.setattr(module.os, "link", fail)
    with pytest.raises(DatabaseError, match="无法创建备份"):
        database.backup_to(tmp_path / "backup.sqlite3")
    assert database.path.read_bytes() == previous
    assert not (tmp_path / "backup.sqlite3").exists()
    assert not list(tmp_path.glob(".cashing-backup-*.tmp"))


@pytest.mark.parametrize("version,other_table", [(3, False), (0, True)])
def test_missing_records_table_is_not_recreated(tmp_path, version, other_table):
    path = tmp_path / "unknown.sqlite3"
    with sqlite3.connect(path) as con:
        con.execute(f"PRAGMA user_version = {version}")
        if other_table:
            con.execute("CREATE TABLE other_app (value TEXT)")
    previous = path.read_bytes()
    with pytest.raises(DatabaseError, match="未创建空账本"):
        Database(path).initialize_database()
    assert path.read_bytes() == previous
