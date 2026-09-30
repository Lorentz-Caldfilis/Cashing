"""The derived category: high confidence or nothing, learnt from the person, bounded by votes."""
import pytest
from classification import Classifier, tokens, MAX_PHRASE
from scripts import classification_benchmark as bench


def teach(*labels):
    """labels: (description, category) in the order the person gave them."""
    return Classifier((i, text, category, i) for i, (text, category) in enumerate(labels))


def test_tokens_ignore_case_width_spaces_and_punctuation():
    assert tokens("ChatGPT Plus！") == ("chatgpt", "plus")
    assert tokens("ＫＦＣ 午饭+奶茶") == ("kfc", "午", "饭", "奶", "茶")
    assert tokens("  ") == () and tokens("？！") == () and tokens(None) == ()


@pytest.mark.parametrize("text,category", [
    ("午饭", "生活"), ("食堂晚饭", "生活"), ("滴滴打车回学校", "生活"), ("鸡公煲加饭", "生活"),
    ("烤冷面", "生活"), ("秋裤", "生活"), ("ChatGPT Plus", "工具"), ("打印 实验报告", "工具"),
    ("面包板", "工具"), ("Steam 秋促", "娱乐"), ("电影票", "娱乐"), ("吃鸡", "娱乐"), ("车模", "娱乐"),
    ("面试 打车", "生活"),
])
def test_built_in_words_decide_the_unambiguous(text, category):
    assert Classifier().classify(text) == category


@pytest.mark.parametrize("text", [
    "", "未知", "xq7", "给妈妈买的",   # no evidence
    "打车去看电影", "午饭 电影",       # the words disagree
    "奶茶", "瑞幸咖啡", "零食", "买书", "蛋糕", "午饭+奶茶",  # personal: only the person can place these
    "面试",                            # neutral: 面试 is not a noodle
    "gpt4all",                         # 'gpt' only matches as a whole word
])
def test_without_enough_evidence_nothing_is_decided(text):
    assert Classifier().classify(text) is None


def test_the_persons_phrase_is_learnt_at_once_and_reused_inside_longer_texts():
    model = teach(("奶茶", "娱乐"))
    assert model.classify("奶茶") == "娱乐"
    assert model.classify("奶茶 两杯 和室友") == "娱乐"
    assert model.classify("午饭+奶茶") is None  # 午饭 says 生活, the person's 奶茶 says 娱乐


def test_the_persons_phrase_beats_a_built_in_word_of_the_same_length():
    model = teach(("火锅", "娱乐"), ("火锅", "娱乐"))
    assert model.classify("和室友吃火锅") == "娱乐"
    assert Classifier().classify("和室友吃火锅") == "生活"


def test_single_characters_and_long_phrases_only_match_themselves():
    model = teach(("水", "娱乐"), ("一" * (MAX_PHRASE + 1), "工具"))
    assert model.classify("水") == "娱乐"
    assert model.classify("水彩") is None
    assert model.classify("一" * (MAX_PHRASE + 1)) == "工具"
    assert model.classify("一" * (MAX_PHRASE + 2)) is None


def test_one_exception_leaves_a_clear_opinion_two_corrections_change_it():
    assert teach(("午饭", "娱乐")).classify("午饭") == "生活"
    assert teach(("午饭", "娱乐"), ("午饭", "娱乐")).classify("午饭") == "娱乐"
    # Against the person's own habit, one exception does not count either.
    habit = [("霸王茶姬", "生活")] * 3
    assert teach(*habit, ("霸王茶姬", "娱乐")).classify("霸王茶姬") == "生活"


def test_a_changed_mind_wins_after_a_few_labels():
    old = [("拿铁", "工具")] * 3
    assert teach(*old, ("拿铁", "生活")).classify("拿铁") == "工具"
    assert teach(*old, *[("拿铁", "生活")] * 2).classify("拿铁") is None  # neither clearly: undecided
    assert teach(*old, *[("拿铁", "生活")] * 4).classify("拿铁") == "生活"


def test_the_persons_undecided_is_a_vote_and_blocks_longer_texts():
    assert teach(("红包", None)).classify("红包") is None
    assert teach(("红包", None), ("红包 午饭", "生活")).classify("红包 晚饭") is None
    # One 暂未判断 on a clear phrase is an exception like any other.
    assert teach(("午饭", None)).classify("午饭") == "生活"
    assert teach(("午饭", None), ("午饭", None)).classify("午饭") is None


def test_labels_can_move_and_disappear():
    model = Classifier()
    model.set_label(1, "瑞幸", "工具", 1)
    assert model.classify("瑞幸") == "工具"
    # A brand label does not settle a separate, ambiguous product or purpose.
    assert model.classify("瑞幸 生椰拿铁") is None
    model.set_label(1, "星巴克", "工具", 2)  # the record's description was edited
    assert model.classify("瑞幸") is None and model.classify("星巴克") == "工具"
    model.drop_label(1)
    assert model.classify("星巴克") is None
    model.drop_label(1)  # already gone: nothing happens
    model.set_label(2, "   ", "工具", 3)  # an empty description teaches nothing
    assert model.classify("") is None


def test_order_not_insertion_decides_recency():
    a = Classifier([(1, "拿铁", "生活", 5), (2, "拿铁", "工具", 1), (3, "拿铁", "工具", 2)])
    b = Classifier([(2, "拿铁", "工具", 1), (3, "拿铁", "工具", 2), (1, "拿铁", "生活", 5)])
    assert a.classify("拿铁") == b.classify("拿铁")


def test_rejects_unknown_categories():
    with pytest.raises(ValueError):
        Classifier().set_label(1, "午饭", "饮食", 1)


def test_benchmark_stays_precise_and_keeps_learning():
    """A short run of scripts/classification_benchmark.py; the full report is in
    docs/development/CLASSIFICATION.md. Thresholds sit a little below the measured values."""
    create, first, last = bench.evaluate(tail="fresh", seeds=range(2))
    assert create["precision"] >= 0.975 and first["precision"] >= 0.985 and last["precision"] >= 0.985
    assert create["coverage"] >= 0.72 and last["coverage"] >= 0.78
    assert last["coverage"] > first["coverage"]  # it learns
    right, wrong, _ = bench.cold_tail("fresh")
    assert right >= 30 and wrong <= 2
