from contextlib import closing
from datetime import datetime
import sqlite3
import pytest
from database import Database, DatabaseError


def test_same_column_names_do_not_make_wrong_schema_compatible(tmp_path):
    path = tmp_path / "wrong-schema.sqlite3"
    with closing(sqlite3.connect(path)) as con, con:
        con.execute("""CREATE TABLE records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, amount_cents TEXT NOT NULL,
            datetime TEXT NOT NULL, category TEXT NOT NULL,
            description TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    before = path.read_bytes()
    with pytest.raises(DatabaseError):
        Database(path).initialize_database()
    assert path.read_bytes() == before


@pytest.mark.parametrize("bad_time", [
    "2026-09-31 22:15", "2026-9-01 00:00", "2026-09-01T00:00",
    "2026-09-01 00:00:59", "2026-09-01 00:00+08:00",
])
def test_bad_stored_time_is_reported_without_overwriting(database, bad_time):
    database.add_record(1234, datetime(2026, 9, 1), "生活")
    with closing(sqlite3.connect(database.path)) as con, con:
        con.execute("UPDATE records SET datetime=?", (bad_time,))
    before = database.path.read_bytes()
    with pytest.raises(DatabaseError):
        database.initialize_database()
    assert database.path.read_bytes() == before


def test_initialization_is_atomic_when_index_creation_fails(tmp_path):
    path = tmp_path / "index-collision.sqlite3"
    with closing(sqlite3.connect(path)) as con, con:
        con.execute("CREATE TABLE idx_records_datetime (id INTEGER)")
    with pytest.raises(DatabaseError):
        Database(path).initialize_database()
    with closing(sqlite3.connect(path)) as con:
        assert not con.execute("SELECT name FROM sqlite_master WHERE name='records'").fetchall()
