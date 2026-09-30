import pytest
from quick_entry import parse_quick_entry, QuickEntry


@pytest.mark.parametrize("text,expected", [
    ("18.5 午饭", QuickEntry("18.50", "午饭")),
    ("￥１，２８０．５０ 打印 Ａ版①", QuickEntry("1280.50", "打印 Ａ版①")),
    (" ¥ 12.00 ", QuickEntry("12.00", "")),
    ("20\t电影", QuickEntry("20.00", "电影")),
])
def test_single_entry(text, expected):
    assert parse_quick_entry(text) == expected


@pytest.mark.parametrize("text", ["1,23 午饭", "18.567 午饭", "0 午饭", "-12 午饭",
    "12 午饭\n18 打印", "$12 午饭", "12元午饭", "1000000000 午饭", "12 " + "😀" * 101])
def test_ambiguous_or_truncating_input_is_rejected(text):
    with pytest.raises(ValueError):
        parse_quick_entry(text)
