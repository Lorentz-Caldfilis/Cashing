from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import random
import sqlite3
import pytest
from database import Database, DatabaseError
from domain import CATEGORIES, MAX_CENTS, parse_amount
from paths import data_directory, prepare_smoke_directory, prepare_runtime, SMOKE_SENTINEL


@pytest.mark.parametrize("amount", ["0.001","1.00\n2","9"*200,"1\x00","１.００","1_000","-0.01"])
def test_more_invalid_money(amount):
    with pytest.raises(ValueError):
        parse_amount(amount)


@pytest.mark.parametrize("when", [None, "2026-01-01", datetime(1899,12,31),
                                 datetime(2026,1,1,tzinfo=timezone.utc)])
def test_unsupported_datetime_is_rejected(database, when):
    with pytest.raises(ValueError):
        database.add_record(1,when,"生活")


def test_months_and_integer_totals_against_independent_oracle(database):
    rng = random.Random(571)
    expected=[]
    for i in range(120):
        year,month = rng.choice([(2023,2),(2024,2),(2025,12),(2026,1),(2026,9),(9999,12)])
        day = rng.randint(1,28)
        date = datetime(year,month,day,rng.randrange(24),rng.randrange(60))
        cents = rng.choice([1,10,29,101,MAX_CENTS])
        cat = CATEGORIES[i%3]
        rid=database.add_record(cents,date,cat)
        expected.append((rid,cents,date,cat))
    # This oracle filters datetime objects, never the production string query helper.
    for year,month in [(2023,2),(2024,2),(2025,12),(2026,1),(2026,9),(9999,12),(2026,10)]:
        subset=[r for r in expected if (r[2].year,r[2].month)==(year,month)]
        subset.sort(key=lambda r:(r[2],r[0]),reverse=True)
        rows=database.get_records_by_month(year,month)
        assert [r["id"] for r in rows]==[r[0] for r in subset]
        stats=database.get_month_statistics(year,month)
        assert stats["total"]==sum(r[1] for r in subset)
        assert [stats[c] for c in CATEGORIES]==[sum(r[1] for r in subset if r[3]==c) for c in CATEGORIES]
        assert type(stats["total"]) is int


@pytest.mark.parametrize("year,last",[(2023,28),(2024,29)])
def test_february_excludes_both_neighbours(database,year,last):
    for when in [datetime(year,1,31,23,59),datetime(year,2,1),datetime(year,2,last,23,59),datetime(year,3,1)]:
        database.add_record(1,when,"生活")
    assert [r["datetime"] for r in database.get_records_by_month(year,2)]==[
        f"{year}-02-{last} 23:59", f"{year}-02-01 00:00"]


@pytest.mark.parametrize("operation", ["UPDATE","DELETE"])
def test_mid_operation_abort_rolls_back_other_writes(database,operation):
    a=database.add_record(100,datetime(2026,9,1),"生活")
    b=database.add_record(200,datetime(2026,9,1),"工具")
    with closing(sqlite3.connect(database.path)) as con,con:
        con.execute(f"""CREATE TRIGGER reject_change BEFORE {operation} ON records
                    WHEN OLD.id={a} BEGIN
                    UPDATE records SET amount_cents=999 WHERE id={b};
                    SELECT RAISE(ABORT,'test failure after a write'); END""")
    with pytest.raises(DatabaseError):
        if operation=="UPDATE":
            database.update_record(a,300,datetime(2026,9,1),"娱乐")
        else:
            database.delete_record(a)
    assert database.get_month_statistics(2026,9)=={"生活":100,"工具":200,"娱乐":0,"unknown":0,"total":300}


def test_failed_update_validation_leaves_original(database):
    rid=database.add_record(1234,datetime(2026,9,1),"工具","keep")
    before=database.get_records_by_month(2026,9)
    with pytest.raises(ValueError):
        database.update_record(rid,-1,datetime(2026,9,1),"生活")
    assert database.get_records_by_month(2026,9)==before


def test_corrupted_row_after_start_is_user_facing(database):
    database.add_record(1,datetime(2026,9,1),"生活")
    with closing(sqlite3.connect(database.path)) as con,con:
        con.execute("UPDATE records SET datetime='2026-09-31 00:00'")
    with pytest.raises(DatabaseError):
        database.get_records_by_month(2026,9)


def test_database_read_only_write_failure(database,monkeypatch):
    connect=sqlite3.connect
    def readonly(database_uri,**kwargs):
        return connect(database_uri.replace("?mode=rw","?mode=ro"),**kwargs)
    monkeypatch.setattr(sqlite3,"connect",readonly)
    with pytest.raises(DatabaseError):
        database.add_record(1,datetime(2026,9,1),"生活")
    assert database.get_records_by_month(2026,9)==[]


def test_connection_closes_on_failure(database):
    with pytest.raises(DatabaseError):
        database.delete_record(999)
    # Windows will reject this rename when sqlite3 still holds the file open.
    renamed=database.path.with_name("closed.sqlite3")
    database.path.rename(renamed)
    reopened=Database(renamed)
    reopened.initialize_database()


def test_unwritable_parent_is_user_facing(tmp_path):
    parent=tmp_path/"ordinary-file"
    parent.write_text("keep",encoding="utf8")
    with pytest.raises(DatabaseError):
        Database(parent/"ledger.sqlite3").initialize_database()
    assert parent.read_text()=="keep"


def test_chinese_spaces_and_uri_characters(tmp_path,monkeypatch):
    folder=tmp_path/"中文 用户 #100% 数据"
    monkeypatch.setenv("LOCALAPPDATA",str(folder))
    directory=data_directory()
    prepare_runtime(directory)
    db=Database(directory/"ledger.sqlite3")
    db.initialize_database()
    db.add_record(1,datetime(2026,9,1),"生活","特殊路径")
    assert db.get_month_statistics(2026,9)["total"]==1


def test_smoke_refuses_default_even_when_empty(tmp_path,monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA",str(tmp_path))
    default=data_directory()
    with pytest.raises(ValueError):
        prepare_smoke_directory(default)
    assert not default.exists()


@pytest.mark.parametrize("kind",["ledger","unmarked","wrong-marker"])
def test_smoke_refuses_other_existing_data(tmp_path,monkeypatch,kind):
    monkeypatch.setenv("LOCALAPPDATA",str(tmp_path/"local"))
    folder=tmp_path/"smoke"
    folder.mkdir()
    if kind=="ledger":
        (folder/"ledger.sqlite3").write_bytes(b"do not touch")
        (folder/".cashing-smoke-only").write_text(SMOKE_SENTINEL)
    elif kind=="unmarked":
        (folder/"notes.txt").write_text("keep")
    else:
        (folder/".cashing-smoke-only").write_text("unknown")
    before={p.name:p.read_bytes() for p in folder.iterdir()}
    with pytest.raises(ValueError):
        prepare_smoke_directory(folder)
    assert {p.name:p.read_bytes() for p in folder.iterdir()}==before


def test_smoke_directory_is_reusable_and_separate(tmp_path,monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA",str(tmp_path/"local"))
    folder=tmp_path/"smoke"
    prepare_smoke_directory(folder)
    Database(folder/"smoke-ledger.sqlite3").initialize_database()
    prepare_smoke_directory(folder)
    assert not (folder/"ledger.sqlite3").exists()
