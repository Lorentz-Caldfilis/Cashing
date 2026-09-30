"""Small fixed synthetic student scenarios; not a real-user accuracy estimate."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from classification import Classifier
from database import Database
from ledger import Ledger, AUTO

DEV = [
    ("食堂午饭", "生活"), ("咖啡", None), ("瑞幸咖啡", None), ("打印实验报告", "工具"),
    ("高数教材", "工具"), ("地铁回宿舍", "生活"), ("宿舍洗衣液", "生活"), ("宿舍插排", "工具"),
    ("淘宝 高数教材", "工具"), ("京东 洗衣液", "生活"), ("拼多多 桌游", "娱乐"), ("网购 教材", "工具"),
    ("淘宝", None), ("京东 耳机", None), ("午饭+电影", None), ("给室友转账", None),
    ("咖啡 小组讨论", None), ("咖啡 周末聊天", None), ("宿舍超市 插排", None),
    ("校园卡充值", "生活"), ("复印讲义", "工具"), ("咖啡店 打印", None), ("书", None), ("未知商户", None),
]
# Fixed before the implementation; never extend to patch a disappointing result.
HOLDOUT = [
    ("淘宝 课本", "工具"), ("京东 牙膏", "生活"), ("拼多多 小说", "娱乐"), ("网购 硬盘", "工具"),
    ("淘宝 礼物", None), ("京东 耳机", None), ("拼多多", None), ("网购", None),
    ("淘宝 教材和电影票", None), ("图书馆复印讲义", "工具"), ("宿舍电费", "生活"), ("咖啡约会", None),
]


def cold(cases):
    model = Classifier()
    rows = [{"text": text, "expected": expected, "actual": model.classify(text)} for text, expected in cases]
    return {"cases": rows, "exact_agreement": sum(r["expected"] == r["actual"] for r in rows),
            "total": len(rows), "wrong_decisions": sum(r["actual"] is not None and r["actual"] != r["expected"] for r in rows),
            "resolved_clear_cases": sum(r["actual"] == r["expected"] and r["expected"] is not None for r in rows),
            "clear_cases": sum(r["expected"] is not None for r in rows)}


def learning(directory):
    db = Database(Path(directory) / "synthetic.sqlite3")
    db.initialize_database()
    ledger = Ledger(db)
    when = datetime(2026, 9, 20, 12, 0)
    a = ledger.create(1800, when, "瑞幸 咖啡 赶论文")
    older = ledger.create(1800, when, "瑞幸 咖啡 赶论文")
    b = ledger.create(1800, when, "瑞幸 咖啡 周末约会")
    results = {}
    def shown(record):
        return ledger.interpret(db.get_record(record["id"]))["category"]
    results["cold_coffee_abstains"] = shown(a) is None and shown(b) is None
    a, receipt = ledger.update_undoable(a, category="工具")
    results["correction_updates_older_matching_record"] = shown(older) == "工具"
    results["other_purpose_still_abstains"] = shown(b) is None
    b = ledger.update(b, category="娱乐")
    results["same_merchant_two_purposes"] = shown(a) == "工具" and shown(b) == "娱乐"
    results["merchant_alone_not_guessed"] = ledger.classifier().classify("瑞幸") is None
    reset, reset_receipt = ledger.update_undoable(a, category=AUTO)
    results["reset_retracts_learning"] = shown(older) is None and shown(b) == "娱乐"
    ledger.undo_update(reset_receipt)
    results["undo_reset_restores_learning"] = shown(older) == "工具"
    ledger.undo_update(receipt)
    results["undo_correction_retracts_learning"] = shown(older) is None
    snapshot = ledger.delete(b)
    results["delete_retracts_learning"] = ledger.classifier().classify(b["description"]) is None
    ledger.restore(snapshot)
    results["restore_relearns"] = ledger.classifier().classify(b["description"]) == "娱乐"
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error("Choose a new output file")
    work = ROOT / "work"
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="student-scenarios-", dir=work) as directory:
        report = {"data": "fixed synthetic scenarios; not real usage", "dev": cold(DEV),
                  "holdout": cold(HOLDOUT), "learning": learning(directory)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps({k: {a: b for a, b in v.items() if a != "cases"} for k, v in report.items() if isinstance(v, dict)}, ensure_ascii=False))
    return 0 if all(report["learning"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
