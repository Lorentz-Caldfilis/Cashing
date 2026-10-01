"""Small fixed synthetic acceptance corpus; abstention is valid for ambiguity."""
from scripts.student_scenarios import DEV, HOLDOUT, cold, learning


def test_student_development_scenarios():
    report = cold(DEV)
    assert report["wrong_decisions"] == 0
    # Marketplace evidence stays conservative until unknown-token provenance is modeled.
    assert report["resolved_clear_cases"] >= 8


def test_holdout_does_not_trade_precision_for_coverage():
    report = cold(HOLDOUT)
    assert report["wrong_decisions"] == 0
    # Keep the fixed corpus unchanged; abstention is safer than substring guesses.
    assert report["resolved_clear_cases"] >= 1


def test_student_learning_and_retraction(tmp_path):
    results = learning(tmp_path)
    assert all(results.values()), results


# Independent review regressions, separate from the frozen DEV/HOLDOUT corpora.
# Their purposes cannot be inferred safely from a fruit/food/head-character substring.
def test_marketplaces_do_not_enable_weak_substring_or_brand_guesses():
    from classification import Classifier
    model = Classifier()
    for text in ("京东 苹果手机", "淘宝 面具", "拼多多 汤勺", "网购 粉底",
                 "京东 苹果配件", "淘宝 面部清洁仪", "京东 Apple iPhone", "淘宝 手工鸡毛毽", "拼多多 茶盘"):
        assert model.classify(text) is None, text


def test_explicit_personal_product_phrase_still_works_after_safe_rollback():
    from classification import Classifier
    model = Classifier([(1, "京东 苹果手机", "工具", 1)])
    assert model.classify("京东 苹果手机") == "工具"
    assert model.classify("京东 苹果配件") is None
