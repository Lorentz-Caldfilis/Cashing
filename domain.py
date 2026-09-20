"""Small, UI-independent rules and formatting. All money is integer cents.

A record stores facts (amount, time, description) and one derived
interpretation (category). The category may be ``None``: the software has
not judged yet. That is not a fourth category and never a task for the user.
"""
import re
from datetime import datetime, date

CATEGORIES = ("生活", "工具", "娱乐")
UNKNOWN_LABEL = "暂未判断"
MAX_CENTS = 99_999_999_999
MIN_YEAR = 1900
MAX_YEAR = 9999
MAX_DESCRIPTION = 200
WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def parse_amount(text: str) -> int:
    text = text.strip()
    if not re.fullmatch(r"[0-9]{1,9}(?:\.[0-9]{1,2})?", text):
        raise ValueError("金额格式不正确")
    whole, _, fraction = text.partition(".")
    cents = int(whole) * 100 + int(fraction.ljust(2, "0") or "0")
    validate_cents(cents)
    return cents


def validate_cents(cents: int) -> None:
    if type(cents) is not int or not 0 < cents <= MAX_CENTS:
        raise ValueError("金额必须大于 0，且不超过 ¥999,999,999.99")


def format_cents(cents: int) -> str:
    """Static display: grouped thousands, always two decimals: 2,438.50."""
    return f"{cents // 100:,}.{cents % 100:02d}"


def format_amount(cents: int) -> str:
    return "¥" + format_cents(cents)


def cents_to_input(cents: int) -> str:
    """Plain editable text for an input field: 28.50 (no symbol, no grouping)."""
    return f"{cents // 100}.{cents % 100:02d}"


def validate_category(category) -> None:
    if category is not None and category not in CATEGORIES:
        raise ValueError("类别只能是生活、工具、娱乐或暂未判断。")


def validate_record(amount_cents, when, category, description):
    validate_cents(amount_cents)
    if not isinstance(when, datetime) or when.tzinfo is not None:
        raise ValueError("请选择有效的本地消费时间。")
    if not MIN_YEAR <= when.year <= MAX_YEAR:
        raise ValueError("时间年份必须在 1900 至 9999 之间。")
    validate_category(category)
    if not isinstance(description, str) or len(description) > MAX_DESCRIPTION:
        raise ValueError(f"说明不能超过 {MAX_DESCRIPTION} 个字符。")


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    if not MIN_YEAR <= year <= MAX_YEAR or not 1 <= month <= 12:
        raise ValueError("无效月份。")
    index = year * 12 + month - 1 + delta
    new_year, new_month = divmod(index, 12)
    if not MIN_YEAR <= new_year <= MAX_YEAR:
        raise ValueError("已到可查看的日期边界。")
    return new_year, new_month + 1


def summarize_records(records):
    """Totals per category plus ``unknown`` and ``total``; the total always
    includes records the software has not classified."""
    totals = dict.fromkeys(CATEGORIES, 0)
    totals["unknown"] = 0
    for record in records:
        key = record["category"] if record["category"] in CATEGORIES else "unknown"
        totals[key] += record["amount_cents"]
    totals["total"] = sum(totals[c] for c in CATEGORIES) + totals["unknown"]
    return totals


def parse_stored_datetime(text: str) -> datetime:
    """Strict canonical local time ``YYYY-MM-DD HH:MM``."""
    when = datetime.strptime(text, "%Y-%m-%d %H:%M")
    if when.isoformat(sep=" ", timespec="minutes") != text:
        raise ValueError("Noncanonical local time")
    return when


def group_by_day(records):
    """Preserve the incoming (newest first) order; yield (date, [records])."""
    groups = []
    for record in records:
        day = record["datetime"][:10]
        if not groups or groups[-1][0] != day:
            groups.append((day, []))
        groups[-1][1].append(record)
    return groups


def describe_time(when: datetime, now: datetime | None = None) -> str:
    """Weak, natural time for Capture: 今天 20:10 / 昨天 19:30 / 9 月 18 日 12:00."""
    now = now or datetime.now()
    clock = f"{when.hour:02d}:{when.minute:02d}"
    delta = (now.date() - when.date()).days
    if delta == 0:
        return f"今天 {clock}"
    if delta == 1:
        return f"昨天 {clock}"
    if when.year == now.year:
        return f"{when.month} 月 {when.day} 日 {clock}"
    return f"{when.year} 年 {when.month} 月 {when.day} 日 {clock}"


def describe_day(day: str, now: datetime | None = None, *, with_year=False) -> str:
    """History group heading: 9 月 20 日 星期六, with the year when asked or when it differs."""
    now = now or datetime.now()
    value = date.fromisoformat(day)
    weekday = WEEKDAYS[value.weekday()]
    if with_year or value.year != now.year:
        return f"{value.year} 年 {value.month} 月 {value.day} 日 {weekday}"
    return f"{value.month} 月 {value.day} 日 {weekday}"


def describe_month(year: int, month: int) -> str:
    return f"{year} 年 {month} 月"
