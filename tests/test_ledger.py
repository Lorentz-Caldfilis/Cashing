"""Ledger service: the operations the UI performs, without any widget."""
from datetime import datetime
import pytest
from database import DatabaseError
from domain import group_by_day, describe_time, describe_day, summarize_records
from ledger import Ledger

WHEN = datetime(2026, 9, 19, 22, 15)


@pytest.fixture
def ledger(database):
    return Ledger(database)


def test_create_stores_facts_and_derives_the_category(ledger):
    record = ledger.create(2850, WHEN, "  晚饭  ")
    assert record["amount_cents"] == 2850
    assert record["datetime"] == "2026-09-19 22:15"
    assert record["description"] == "晚饭"
    assert (record["category"], record["category_by_user"]) == ("生活", False)
    # Only facts are stored; the interpretation is derived whenever the record is read.
    stored = ledger.database.get_record(record["id"])
    assert (stored["category"], stored["category_by_user"]) == (None, 0)
    view = ledger.month(2026, 9)
    assert view.totals == {"生活": 2850, "工具": 0, "娱乐": 0, "unknown": 0, "total": 2850}


def test_without_enough_evidence_the_category_stays_unknown(ledger):
    for text in ["", "未知", "xq7", "打车去看电影", "奶茶"]:  # nothing / unknown / conflict / personal
        assert ledger.create(1, WHEN, text)["category"] is None, text
    assert ledger.month(2026, 9).totals["unknown"] == 5


def test_empty_description_is_a_complete_record(ledger):
    record = ledger.create(1200, WHEN, "")
    assert record["description"] == ""
    assert ledger.month(2026, 9).totals["total"] == 1200


def test_the_persons_label_teaches_every_record_with_that_phrase(ledger):
    first = ledger.create(1500, datetime(2026, 8, 12, 9, 0), "蜜雪冰城")
    earlier = ledger.create(1500, datetime(2026, 8, 1, 9, 0), "蜜雪冰城")
    assert first["category"] is None  # a milk-tea brand: personal, so not guessed
    ledger.update(first, category="娱乐")
    assert ledger.create(1500, datetime(2026, 9, 12, 9, 0), "蜜雪冰城 ")["category"] == "娱乐"
    assert ledger.create(1500, datetime(2026, 9, 13, 9, 0), "蜜雪冰城 和室友")["category"] == "娱乐"
    # Earlier records read the same way now: interpretations are derived, not stored.
    assert ledger.month(2026, 8).records[0]["category"] == "娱乐"
    assert ledger.database.get_record(earlier["id"])["category"] is None
    assert ledger.create(1, WHEN, "")["category"] is None


def test_one_exception_does_not_reinterpret_everything(ledger):
    lunches = [ledger.create(1500, datetime(2026, 9, day, 12, 0), "午饭") for day in range(1, 6)]
    ledger.update(lunches[0], category="娱乐")  # a birthday lunch
    view = ledger.month(2026, 9)
    assert [r["category"] for r in view.records] == ["生活"] * 4 + ["娱乐"]
    ledger.update(lunches[1], category="娱乐")  # the person means it
    assert [r["category"] for r in ledger.month(2026, 9).records] == ["娱乐"] * 5


def test_explicit_unknown_is_the_persons_and_sticks(ledger):
    record = ledger.create(3600, WHEN, "电影")
    assert record["category"] == "娱乐"
    record = ledger.update(record, category=None)
    assert (record["category"], record["category_by_user"]) == (None, True)
    assert ledger.month(2026, 9).records[0]["category"] is None
    record = ledger.update(record, amount_cents=3700)  # other edits keep it
    assert (record["category"], record["category_by_user"]) == (None, True)


def test_description_edit_rederives_unless_the_person_chose(ledger):
    record = ledger.create(1200, WHEN, "晚饭")
    record = ledger.update(record, description="电影票")
    assert record["category"] == "娱乐"
    record = ledger.update(record, category="生活")
    record = ledger.update(record, description="电影票 两张")
    assert (record["category"], record["category_by_user"]) == ("生活", True)
    # One label against a clear built-in opinion is an exception, not a new rule.
    assert ledger.create(1, WHEN, "电影票 两张")["category"] == "娱乐"


def test_a_label_moves_with_its_record(ledger):
    record = ledger.update(ledger.create(1800, WHEN, "霸王茶姬"), category="娱乐")
    assert ledger.create(1, WHEN, "霸王茶姬")["category"] == "娱乐"
    ledger.update(record, description="喜茶")
    assert ledger.create(1, WHEN, "霸王茶姬")["category"] is None
    assert ledger.create(1, WHEN, "喜茶")["category"] == "娱乐"


def test_delete_and_restore_keep_what_the_person_said(ledger):
    labelled = ledger.create(1500, WHEN, "古茗")
    labelled = ledger.update(labelled, category="娱乐")
    other = ledger.create(1500, datetime(2026, 9, 20, 12, 0), "古茗")
    assert ledger.month(2026, 9).records[0]["category"] == "娱乐"
    snapshot = ledger.delete(labelled)
    assert snapshot["category_by_user"] == 1 and snapshot["category"] == "娱乐"
    assert ledger.month(2026, 9).records[0]["category"] is None  # the lesson went with it
    ledger.restore(snapshot)
    assert [r["category"] for r in ledger.month(2026, 9).records] == ["娱乐", "娱乐"]
    assert ledger.database.get_record(other["id"])["category_by_user"] == 0


def test_undo_create_removes_only_that_record(ledger):
    keep = ledger.create(100, WHEN, "keep")
    gone = ledger.create(200, WHEN, "gone")
    ledger.undo_create(gone["id"])
    assert [r["id"] for r in ledger.month(2026, 9).records] == [keep["id"]]
    with pytest.raises(DatabaseError):
        ledger.undo_create(gone["id"])


def test_update_single_fields(ledger):
    record = ledger.create(2850, WHEN, "晚饭")
    record = ledger.update(record, amount_cents=3000)
    assert (record["amount_cents"], record["description"], record["category"]) == (3000, "晚饭", "生活")
    assert not record["category_by_user"]
    record = ledger.update(record, description=" 夜宵 ")
    assert record["description"] == "夜宵"
    record = ledger.update(record, category="生活")
    assert record["category"] == "生活"
    record = ledger.update(record, when=datetime(2026, 10, 1, 8, 0))
    assert record["datetime"] == "2026-10-01 08:00"
    assert ledger.month(2026, 9).is_empty
    assert ledger.month(2026, 10).totals["生活"] == 3000


def test_invalid_update_changes_nothing(ledger):
    record = ledger.create(2850, WHEN, "晚饭")
    for bad in [dict(amount_cents=0), dict(amount_cents=-5), dict(category="饮食"),
                dict(description="长" * 201), dict(when=datetime(1800, 1, 1))]:
        with pytest.raises(ValueError):
            ledger.update(record, **bad)
    assert ledger.interpret(ledger.database.get_record(record["id"])) == record


def test_delete_then_restore_returns_the_same_record_in_the_same_place(ledger):
    a = ledger.create(100, datetime(2026, 9, 19, 22, 15), "a")
    b = ledger.create(200, datetime(2026, 9, 19, 22, 15), "b")
    c = ledger.create(300, datetime(2026, 9, 20, 8, 0), "c")
    assert [r["id"] for r in ledger.month(2026, 9).records] == [c["id"], b["id"], a["id"]]
    snapshot = ledger.delete(b)
    assert [r["id"] for r in ledger.month(2026, 9).records] == [c["id"], a["id"]]
    assert ledger.month(2026, 9).totals["total"] == 400
    restored = ledger.restore(snapshot)
    assert restored == b
    assert [r["id"] for r in ledger.month(2026, 9).records] == [c["id"], b["id"], a["id"]]
    assert ledger.month(2026, 9).totals["total"] == 600
    with pytest.raises(DatabaseError):
        ledger.restore(snapshot)  # already present


def test_search_spans_all_months_and_only_matches_description(ledger):
    ledger.create(5900, datetime(2026, 9, 12, 9, 0), "ChatGPT Plus")
    ledger.create(5900, datetime(2026, 8, 12, 9, 0), "ChatGPT Plus")
    ledger.create(1500, datetime(2026, 9, 1, 12, 0), "打印 100% 报告")
    ledger.create(5900, datetime(2026, 7, 1, 12, 0), "地铁")
    found = ledger.search("chatgpt")
    assert [r["datetime"] for r in found] == ["2026-09-12 09:00", "2026-08-12 09:00"]
    assert [r["description"] for r in ledger.search("100%")] == ["打印 100% 报告"]
    assert ledger.search("_") == [] and ledger.search("5900") == []
    assert ledger.search("   ") == []


def test_search_results_can_be_edited_in_place(ledger):
    record = ledger.create(5900, datetime(2026, 8, 12, 9, 0), "ChatGPT")
    hit = ledger.search("Chat")[0]
    updated = ledger.update(hit, amount_cents=6000)
    assert updated["id"] == record["id"] and ledger.search("Chat")[0]["amount_cents"] == 6000


def test_month_view_groups_by_day_newest_first(ledger):
    ledger.create(1, datetime(2026, 9, 19, 8, 0), "x")
    ledger.create(2, datetime(2026, 9, 20, 18, 42), "y")
    ledger.create(3, datetime(2026, 9, 20, 15, 17), "z")
    view = ledger.month(2026, 9)
    assert [(day, [r["amount_cents"] for r in rows]) for day, rows in view.groups] == [
        ("2026-09-20", [2, 3]), ("2026-09-19", [1])]
    assert group_by_day([]) == []
    assert summarize_records([])["total"] == 0


def test_time_descriptions():
    now = datetime(2026, 9, 20, 20, 10)
    assert describe_time(datetime(2026, 9, 20, 20, 10), now) == "今天 20:10"
    assert describe_time(datetime(2026, 9, 19, 23, 59), now) == "昨天 23:59"
    assert describe_time(datetime(2026, 9, 1, 8, 5), now) == "9月1日 08:05"
    assert describe_time(datetime(2025, 12, 31, 8, 5), now) == "2025年12月31日 08:05"
    assert describe_day("2026-09-20", now) == "9月20日 星期日"
    assert describe_day("2026-09-20", now, with_year=True) == "2026年9月20日 星期日"
    assert describe_day("2025-01-01", now) == "2025年1月1日 星期三"
