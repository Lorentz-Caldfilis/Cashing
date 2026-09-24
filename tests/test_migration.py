"""Schema v1/v2 -> v3: existing ledgers open unchanged in meaning, never rebuilt from scratch."""
from contextlib import closing
from datetime import datetime
import sqlite3
import pytest
from database import Database, DatabaseError, BACKUP_SUFFIX

V1_DDL = """
    CREATE TABLE records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount_cents INTEGER NOT NULL
            CHECK(typeof(amount_cents) = 'integer'
                  AND amount_cents BETWEEN 1 AND 99999999999),
        datetime TEXT NOT NULL,
        category TEXT NOT NULL CHECK(category IN ('饮食','工具','娱乐')),
        description TEXT NOT NULL DEFAULT '' CHECK(length(description) <= 200),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
"""
V1_ROWS = [
    (1, 2850, "2026-09-19 22:15", "饮食", "晚饭", "2026-09-19T22:15:00", "2026-09-19T22:15:00"),
    (2, 5900, "2026-09-12 09:00", "工具", "ChatGPT", "2026-09-12T09:00:00", "2026-09-12T09:01:00"),
    (4, 3600, "2026-08-30 21:03", "娱乐", "电影", "2026-08-30T21:03:00", "2026-08-30T21:03:00"),
    (7, 1, "2024-02-29 23:59", "饮食", "", "2024-02-29T23:59:00", "2024-02-29T23:59:00"),
]


def make_v1(path, rows=V1_ROWS, *, sequence=9):
    with closing(sqlite3.connect(path)) as con, con:
        con.execute(V1_DDL)
        con.execute("CREATE INDEX idx_records_datetime ON records(datetime DESC, id DESC)")
        con.executemany("INSERT INTO records VALUES (?,?,?,?,?,?,?)", rows)
        if sequence is not None:
            con.execute("DELETE FROM sqlite_sequence WHERE name='records'")
            con.execute("INSERT INTO sqlite_sequence VALUES ('records', ?)", (sequence,))
        con.execute("PRAGMA user_version = 1")


def dump(path):
    with closing(sqlite3.connect(path)) as con:
        return con.execute("SELECT * FROM records ORDER BY id").fetchall()


def test_v1_ledger_is_migrated_with_every_fact_preserved(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    make_v1(path)
    db = Database(path)
    db.initialize_database()
    with closing(sqlite3.connect(path)) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 3
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert "records" in names and "records_v3" not in names
        assert con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_records_datetime'").fetchone()
    migrated = dump(path)
    # v1 made the person choose every category, so every one is the person's own.
    expected = [(i, a, d, {"饮食": "生活"}.get(c, c), desc, ca, ua, 1) for i, a, d, c, desc, ca, ua in V1_ROWS]
    assert migrated == expected
    # Reading through the application layer agrees and the month totals are unchanged.
    september = db.get_records_by_month(2026, 9)
    assert [r["id"] for r in september] == [1, 2]
    assert db.get_month_statistics(2026, 9) == {"生活": 2850, "工具": 5900, "娱乐": 0, "unknown": 0, "total": 8750}
    assert db.get_month_statistics(2024, 2)["生活"] == 1


def test_migration_keeps_a_backup_of_the_original_file(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    make_v1(path)
    Database(path).initialize_database()
    backup = tmp_path / ("ledger.sqlite3" + BACKUP_SUFFIX)
    assert backup.is_file()
    with closing(sqlite3.connect(backup)) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 1
        assert con.execute("SELECT category FROM records WHERE id=1").fetchone()[0] == "饮食"
        assert len(con.execute("SELECT * FROM records").fetchall()) == len(V1_ROWS)


def test_migration_runs_once_and_reopen_is_stable(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    make_v1(path)
    Database(path).initialize_database()
    after_first = dump(path)
    backup = tmp_path / ("ledger.sqlite3" + BACKUP_SUFFIX)
    stamp = backup.read_bytes()
    Database(path).initialize_database()
    Database(path).initialize_database()
    assert dump(path) == after_first
    assert backup.read_bytes() == stamp


def test_new_ids_continue_after_the_old_counter(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    make_v1(path, sequence=9)  # ids 8 and 9 existed once and were deleted
    db = Database(path)
    db.initialize_database()
    rid = db.add_record(100, datetime(2026, 9, 20, 10, 0), "工具", "new")
    assert rid == 10
    with closing(sqlite3.connect(path)) as con:
        assert con.execute("SELECT seq FROM sqlite_sequence WHERE name='records'").fetchone()[0] == 10
        assert con.execute("SELECT COUNT(*) FROM sqlite_sequence").fetchone()[0] == 1


def test_migration_without_sequence_row_still_avoids_collisions(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    make_v1(path, sequence=None)
    with closing(sqlite3.connect(path)) as con, con:
        con.execute("DELETE FROM sqlite_sequence")
    db = Database(path)
    db.initialize_database()
    rid = db.add_record(100, datetime(2026, 9, 20, 10, 0), "工具", "new")
    assert rid == 8
    assert [r["id"] for r in db.get_records_by_month(2026, 9)] == [8, 1, 2]


def test_invalid_legacy_row_stops_migration_and_leaves_v1_untouched(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    rows = V1_ROWS + [(9, 100, "2026-09-31 00:00", "饮食", "bad day", "x", "x")]
    make_v1(path, rows)
    before = path.read_bytes()
    with pytest.raises(DatabaseError):
        Database(path).initialize_database()
    assert path.read_bytes() == before
    assert not (tmp_path / ("ledger.sqlite3" + BACKUP_SUFFIX)).exists()
    with closing(sqlite3.connect(path)) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 1
        assert con.execute("SELECT category FROM records WHERE id=1").fetchone()[0] == "饮食"


def test_failed_rebuild_rolls_back_to_v1(tmp_path, monkeypatch):
    path = tmp_path / "ledger.sqlite3"
    make_v1(path)
    original = Database._migrate_to_v3

    def broken(con):
        original(con)
        raise DatabaseError("simulated failure after the rebuild")
    monkeypatch.setattr(Database, "_migrate_to_v3", staticmethod(broken))
    with pytest.raises(DatabaseError):
        Database(path).initialize_database()
    with closing(sqlite3.connect(path)) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 1
        assert con.execute("SELECT category FROM records WHERE id=1").fetchone()[0] == "饮食"
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    monkeypatch.undo()
    Database(path).initialize_database()  # The untouched v1 file still migrates cleanly afterwards.
    assert dump(path)[0][3] == "生活"


def test_unknown_category_is_allowed_and_counted_in_total(database):
    a = database.add_record(1200, datetime(2026, 9, 20, 12, 0), None, "未知")
    database.add_record(800, datetime(2026, 9, 20, 13, 0), "生活", "午饭")
    stats = database.get_month_statistics(2026, 9)
    assert stats == {"生活": 800, "工具": 0, "娱乐": 0, "unknown": 1200, "total": 2000}
    assert database.get_record(a)["category"] is None
    database.update_record(a, 1200, datetime(2026, 9, 20, 12, 0), "工具", "未知")
    assert database.get_month_statistics(2026, 9)["unknown"] == 0
    database.update_record(a, 1200, datetime(2026, 9, 20, 12, 0), None, "未知")
    assert database.get_record(a)["category"] is None


@pytest.mark.parametrize("category", ["饮食", "其他", "", 1])
def test_legacy_or_foreign_categories_are_rejected_by_the_domain(database, category):
    with pytest.raises(ValueError):
        database.add_record(1, datetime(2026, 9, 1), category)


def test_v2_shape_is_verified_strictly(tmp_path):
    path = tmp_path / "v2-wrong.sqlite3"
    with closing(sqlite3.connect(path)) as con, con:
        con.execute("""CREATE TABLE records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, amount_cents TEXT NOT NULL,
            datetime TEXT NOT NULL, category TEXT,
            description TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
        con.execute("PRAGMA user_version = 2")
    before = path.read_bytes()
    with pytest.raises(DatabaseError):
        Database(path).initialize_database()
    assert path.read_bytes() == before


V2_DDL = V1_DDL.replace("category TEXT NOT NULL CHECK(category IN ('饮食','工具','娱乐'))",
                        "category TEXT CHECK(category IS NULL OR category IN ('生活','工具','娱乐'))")


def test_v2_ledger_gains_the_origin_of_each_category(tmp_path):
    """v2 stored the person's categories (or exact copies of them) and NULL for 'not judged':
    stored categories become the person's, NULLs are left for the software to judge."""
    path = tmp_path / "ledger.sqlite3"
    with closing(sqlite3.connect(path)) as con, con:
        con.execute(V2_DDL)
        con.executemany("INSERT INTO records VALUES (?,?,?,?,?,?,?)", [
            (1, 2850, "2026-09-19 22:15", None, "晚饭", "2026-09-19T22:15:00", "2026-09-19T22:15:00"),
            (3, 5900, "2026-09-12 09:00", "工具", "ChatGPT", "2026-09-12T09:00:00", "2026-09-12T09:00:00")])
        con.execute("PRAGMA user_version = 2")
    db = Database(path)
    db.initialize_database()
    assert [(r[0], r[3], r[7]) for r in dump(path)] == [(1, None, 0), (3, "工具", 1)]
    assert db.user_labels() == [(3, "ChatGPT", "工具", ("2026-09-12T09:00:00", 3))]
    backup = tmp_path / ("ledger.sqlite3" + BACKUP_SUFFIX)
    with closing(sqlite3.connect(backup)) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 2
        assert len(con.execute("PRAGMA table_info(records)").fetchall()) == 7
