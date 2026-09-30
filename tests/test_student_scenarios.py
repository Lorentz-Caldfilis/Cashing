"""Small fixed synthetic acceptance corpus; abstention is valid for ambiguity."""
from scripts.student_scenarios import DEV, HOLDOUT, cold, learning


def test_student_development_scenarios():
    report = cold(DEV)
    assert report["wrong_decisions"] == 0
    assert report["resolved_clear_cases"] == report["clear_cases"]


def test_holdout_does_not_trade_precision_for_coverage():
    report = cold(HOLDOUT)
    assert report["wrong_decisions"] == 0
    # 图书馆复印讲义 remains conservatively undecided: 图书 is ambiguous.
    assert report["resolved_clear_cases"] >= 5


def test_student_learning_and_retraction(tmp_path):
    results = learning(tmp_path)
    assert all(results.values()), results
