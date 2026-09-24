from contextlib import closing
from datetime import datetime
import sqlite3
import pytest
from database import Database, DatabaseError
from domain import CATEGORIES, parse_amount, format_amount, cents_to_input, shift_month

WHEN = datetime(2026, 9, 19, 22, 15)


@pytest.mark.parametrize("text,cents", [
    ("28", 2800), ("28.50", 2850), ("0.01", 1), ("0001.2", 120),
    ("999999999.99", 99999999999), (" 5.00 ", 500),
])
def test_amount(text, cents):
    assert parse_amount(text) == cents
    assert format_amount(cents) == f"¥{cents//100:,}.{cents%100:02d}"
    assert cents_to_input(cents) == f"{cents//100}.{cents%100:02d}"


@pytest.mark.parametrize("cents,shown", [(1, "¥0.01"), (2850, "¥28.50"), (243850, "¥2,438.50"),
                                          (99999999999, "¥999,999,999.99")])
def test_grouped_static_amount(cents, shown):
    assert format_amount(cents) == shown


@pytest.mark.parametrize("text", ["", " ", "0", "0.00", "-1", "+1", "1.234",
    "1e3", "NaN", "inf", "1,000", ".5", "5.", "１２", "1 2", "1000000000", "¥20"])
def test_invalid_amount(text):
    with pytest.raises(ValueError):
        parse_amount(text)


@pytest.mark.parametrize("category", CATEGORIES)
def test_add_and_persist(database, category):
    rid = database.add_record(2850, WHEN, category, "晚饭 <b>原样</b>")
    reopened = Database(database.path)
    reopened.initialize_database()
    rows = reopened.get_records_by_month(2026, 9)
    assert len(rows) == 1
    assert rows[0]["id"] == rid
    assert rows[0]["amount_cents"] == 2850
    assert rows[0]["category"] == category
    assert rows[0]["description"] == "晚饭 <b>原样</b>"
    assert rows[0]["created_at"] and rows[0]["updated_at"]


def test_month_boundaries_and_sort(database):
    for when in [datetime(2026, 8, 31, 23, 59), datetime(2026, 9, 1),
                 WHEN, datetime(2026, 9, 30, 23, 59), datetime(2026, 10, 1)]:
        database.add_record(100, when, "生活")
    rows = database.get_records_by_month(2026, 9)
    assert [r["datetime"] for r in rows] == [
        "2026-09-30 23:59", "2026-09-19 22:15", "2026-09-01 00:00"]
    a = database.add_record(1, WHEN, "生活")
    b = database.add_record(2, WHEN, "生活")
    same = [r["id"] for r in database.get_records_by_month(2026, 9) if r["datetime"] == "2026-09-19 22:15"]
    assert same[:2] == [b, a]


def test_statistics_edit_delete_and_cross_month(database):
    a = database.add_record(2850, WHEN, "生活")
    database.add_record(10000, WHEN, "工具")
    database.add_record(5000, WHEN, "娱乐")
    assert database.get_month_statistics(2026, 9) == {
        "生活": 2850, "工具": 10000, "娱乐": 5000, "unknown": 0, "total": 17850}
    database.update_record(a, 3333, WHEN, "娱乐", "修改")
    stats = database.get_month_statistics(2026, 9)
    assert stats == {"生活": 0, "工具": 10000, "娱乐": 8333, "unknown": 0, "total": 18333}
    assert sum(stats[c] for c in CATEGORIES) + stats["unknown"] == stats["total"]
    database.update_record(a, 1, datetime(2027, 1, 1), "生活")
    assert database.get_month_statistics(2026, 9)["total"] == 15000
    assert database.get_month_statistics(2027, 1)["total"] == 1
    database.delete_record(a)
    assert database.get_records_by_month(2027, 1) == []
    assert len(database.get_records_by_month(2026, 9)) == 2
    assert database.get_month_statistics(2027, 1) == dict.fromkeys((*CATEGORIES, "unknown", "total"), 0)


@pytest.mark.parametrize("year,month,delta,expected", [
    (2026,12,1,(2027,1)), (2026,1,-1,(2025,12)),
    (2024,2,1,(2024,3)), (2026,9,0,(2026,9)),
])
def test_month_shift(year,month,delta,expected):
    assert shift_month(year,month,delta) == expected


@pytest.mark.parametrize("year,month,delta", [(1900,1,-1),(9999,12,1),(2026,0,1),(2026,13,1)])
def test_month_out_of_bounds(year,month,delta):
    with pytest.raises(ValueError):
        shift_month(year,month,delta)


def test_leap_year_and_last_supported_month(database):
    database.add_record(1, datetime(2024,2,29,23,59), "生活")
    database.add_record(2, datetime(9999,12,31,23,59), "工具")
    assert database.get_month_statistics(2024,2)["total"] == 1
    assert database.get_month_statistics(9999,12)["total"] == 2


@pytest.mark.parametrize("amount,category,description", [
    (0,"生活",""), (-1,"生活",""), (1.5,"生活",""), (True,"生活",""),
    (10**11,"生活",""), (1,"其他",""), (1,"生活","长"*201),
])
def test_direct_invalid_write(database,amount,category,description):
    with pytest.raises(ValueError):
        database.add_record(amount, WHEN, category, description)
    assert database.get_records_by_month(2026,9) == []


def test_long_text_and_sql_safety(database):
    text = "'; DROP TABLE records; -- " + "中" * 170
    database.add_record(1, WHEN, "生活", text)
    assert database.get_records_by_month(2026,9)[0]["description"] == text


def test_missing_record(database):
    with pytest.raises(DatabaseError):
        database.update_record(999, 100, WHEN, "生活")
    with pytest.raises(DatabaseError):
        database.delete_record(999)


def test_missing_database_after_start_is_not_recreated(database):
    database.path.unlink()  # Fixture database only.
    with pytest.raises(DatabaseError):
        database.get_records_by_month(2026,9)
    assert not database.path.exists()


def test_corrupt_database_is_preserved(tmp_path):
    path = tmp_path / "corrupt.sqlite3"
    payload = b"not a database"
    path.write_bytes(payload)
    with pytest.raises(DatabaseError):
        Database(path).initialize_database()
    assert path.read_bytes() == payload


def test_future_schema_is_preserved(database):
    with closing(sqlite3.connect(database.path)) as con, con:
        con.execute("PRAGMA user_version = 99")
    with pytest.raises(DatabaseError):
        database.initialize_database()
    with closing(sqlite3.connect(database.path)) as con, con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 99


def test_locked_database_rollback(database):
    con = sqlite3.connect(database.path)
    try:
        con.execute("BEGIN EXCLUSIVE")
        with pytest.raises(DatabaseError):
            database.add_record(100,WHEN,"生活")
    finally:
        con.rollback()
        con.close()
    assert database.get_records_by_month(2026,9) == []


def test_database_constraints(database):
    con = sqlite3.connect(database.path)
    try:
        for amount,category,by_user in [(0,"生活",1),(-1,"生活",1),(1.5,"生活",1),(100,"其他",1),(100,"饮食",1),
                                        (100,"生活",0),(100,None,2)]:
            with pytest.raises(sqlite3.IntegrityError):
                con.execute("INSERT INTO records VALUES(NULL,?, '2026-09-01 00:00', ?, '', '', '', ?)",
                            (amount,category,by_user))
        with con:
            con.execute("INSERT INTO records VALUES(NULL,100, '2026-09-01 00:00', NULL, '', '', '', 0)")
    finally:
        con.close()
    assert database.get_month_statistics(2026, 9) == {
        "生活": 0, "工具": 0, "娱乐": 0, "unknown": 100, "total": 100}
