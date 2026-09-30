"""Evidence safety and useful coverage; fixed corpora are never rewritten to improve scores."""
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import pytest
from classification import Classifier, tokens
from scripts.classification_challenges import C2, metrics
from scripts.student_scenarios import DEV, HOLDOUT


@pytest.mark.parametrize('text,expected', [
    ('淘宝 买课本', '工具'), ('京东 纸巾三包', '生活'), ('拼多多 桌游两盒', '娱乐'),
    ('买水果', '生活'), ('量子力学教材', '工具'), ('打印流体力学报告', '工具'),
    ('鸡车', None), ('租用电脑', None), ('共享充电宝', None),
    ('打印机玩具', None), ('未知品牌手机', None), ('苹果', None),
    ('京东手机牙膏', None), ('淘宝烤冷面', None), ('奶茶耳机', None),
])
def test_explicit_purpose_and_residuals_have_different_strength(text, expected):
    assert Classifier().classify(text) == expected


def test_every_unmatched_fragment_survives_with_normalized_token_offsets():
    text = '京东 苹果手机'
    result = Classifier().explain(text)
    assert result.category is None and result.reason == 'unresolved_ambiguity'
    assert [(e.text, e.kind) for e in result.evidence] == [
        ('京东', 'platform'), ('苹果', 'polysemy'), ('手机', 'unknown')]
    assert [e.start for e in result.evidence] == [0, 2, 4]
    assert result.evidence[-1].end == len(tokens(text))
    with pytest.raises(FrozenInstanceError):
        result.category = '生活'


def test_global_segmentation_does_not_truncate_complete_fruit_word():
    result = Classifier().explain('买水果')
    assert result.category == '生活'
    assert [(e.text, e.kind) for e in result.evidence] == [('买', 'context'), ('水果', 'term')]


def test_personal_phrase_cannot_silence_another_ambiguous_item():
    model = Classifier([(1, '奶茶', '娱乐', 1)])
    assert model.classify('奶茶 两杯 和室友') == '娱乐'
    assert model.classify('奶茶 耳机') is None
    assert model.explain('奶茶 耳机').reason == 'unresolved_ambiguity'


def test_exact_personal_purpose_and_retraction_do_not_spread_to_brand():
    model = Classifier()
    a, b = '瑞幸 咖啡 赶论文', '瑞幸 咖啡 周末约会'
    model.set_label(1, a, '工具', 1)
    assert model.classify(a) == '工具'
    assert model.classify(b) is None and model.classify('瑞幸') is None
    result = model.explain(a)
    assert result.reason == 'personal_vote' and result.label_count == 1
    model.set_label(2, b, '娱乐', 2)
    assert model.classify(a) == '工具' and model.classify(b) == '娱乐'
    model.drop_label(1)
    assert model.classify(a) is None and model.classify(b) == '娱乐'


def test_explanation_rebuilds_after_correction_and_drop():
    model = Classifier()
    assert model.explain('午饭').category == '生活'
    model.set_label(1, '午饭', '娱乐', 1)
    assert model.explain('午饭').reason == 'prior_after_exception'
    model.set_label(2, '午饭', '娱乐', 2)
    assert model.explain('午饭').category == '娱乐'
    model.drop_label(2)
    assert model.explain('午饭').category == '生活'


@pytest.mark.parametrize('name,cases', [('dev', DEV), ('holdout', HOLDOUT), ('C2', C2)])
def test_frozen_scenarios_gain_useful_safe_coverage(name, cases):
    report = metrics(cases)
    assert report['wrong_decisions'] == 0
    minimum = 4/6 if name == 'holdout' else .7
    assert report['safe_clear_coverage'] >= minimum


def test_reviewer_c1_original_expectations_are_retained():
    fixture = Path(__file__).parent / 'fixtures/classification_challenge_c1.json'
    original = json.loads(fixture.read_text('utf-8'))
    assert len(original['cases']) == 32
    report = metrics(original['cases'])
    assert report['wrong_decisions'] == 0
    assert report['safe_clear_coverage'] >= .7


@pytest.mark.parametrize('text,expected', [
    ('苹果', None), ('皮肤', None), ('月卡', None), ('粉丝', None),
    ('水果苹果', '生活'), ('苹果电脑', '工具'), ('原神皮肤', '娱乐'),
    ('公交月卡', '生活'), ('原神月卡', '娱乐'), ('健身月卡', None),
    ('炒粉丝', '生活'), ('粉丝应援', '娱乐'), ('京东苹果键盘膜', None),
])
def test_homonyms_require_adjacent_explicit_sense_markers(text, expected):
    assert Classifier().classify(text) == expected


def test_challenge_reads_and_creates_never_become_training_labels(database):
    from datetime import datetime
    from ledger import Ledger
    fixture = Path(__file__).parent / 'fixtures/classification_challenge_c1.json'
    cases = json.loads(fixture.read_text('utf-8'))['cases']
    ledger = Ledger(database)
    for text, expected in cases:
        row = ledger.create(100, datetime(2026, 9, 30, 12, 0), text)
        assert database.user_labels() == []
        assert not row['category_by_user']
        ledger.classifier().explain(text)
        ledger.month(2026, 9)
        assert database.user_labels() == []
        stored = database.get_record(row['id'])
        assert stored['category'] is None and stored['category_by_user'] == 0


def test_exact_purpose_reset_and_undo_leave_other_brand_purposes_untouched(database):
    from datetime import datetime
    from ledger import AUTO, Ledger
    ledger = Ledger(database)
    a = ledger.create(100, datetime(2026, 9, 30, 12, 0), '瑞幸咖啡赶论文')
    b = ledger.create(100, datetime(2026, 9, 30, 13, 0), '瑞幸咖啡周末约会')
    a, correction = ledger.update_undoable(a, category='工具')
    assert len(database.user_labels()) == 1
    assert ledger.interpret(database.get_record(b['id']))['category'] is None
    a, reset = ledger.update_undoable(a, category=AUTO)
    assert database.user_labels() == []
    assert ledger.classifier().classify(a['description']) is None
    ledger.undo_update(reset)
    assert len(database.user_labels()) == 1
    assert ledger.classifier().classify(a['description']) == '工具'
    assert ledger.interpret(database.get_record(b['id']))['category'] is None
    ledger.undo_update(correction)
    assert database.user_labels() == []
    assert ledger.classifier().classify(a['description']) is None
