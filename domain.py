"""Small, UI-independent validation helpers. All money is integer cents."""
import re
from datetime import datetime

CATEGORIES = ("饮食", "工具", "娱乐")
MAX_CENTS = 99_999_999_999
MIN_YEAR = 1900
MAX_YEAR = 9999


def parse_amount(text: str) -> int:
    text = text.strip()
    if not re.fullmatch(r"[0-9]{1,9}(?:\.[0-9]{1,2})?", text):
        raise ValueError("请输入有效金额，最多 9 位整数和 2 位小数。")
    whole, _, fraction = text.partition(".")
    cents = int(whole) * 100 + int(fraction.ljust(2, "0") or "0")
    validate_cents(cents)
    return cents


def validate_cents(cents: int) -> None:
    if type(cents) is not int or not 0 < cents <= MAX_CENTS:
        raise ValueError("金额必须大于 0，且不超过 ¥999999999.99。")


def format_amount(cents: int) -> str:
    return f"¥{cents // 100}.{cents % 100:02d}"


def validate_record(amount_cents, when, category, description):
    validate_cents(amount_cents)
    if not isinstance(when, datetime) or when.tzinfo is not None:
        raise ValueError("请选择有效的本地消费时间。")
    if not MIN_YEAR <= when.year <= MAX_YEAR:
        raise ValueError("时间年份必须在 1900 至 9999 之间。")
    if category not in CATEGORIES:
        raise ValueError("类别只能是饮食、工具或娱乐。")
    if not isinstance(description, str) or len(description) > 200:
        raise ValueError("详细说明不能超过 200 个字符。")


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    if not MIN_YEAR <= year <= MAX_YEAR or not 1 <= month <= 12:
        raise ValueError("无效月份。")
    index = year * 12 + month - 1 + delta
    new_year, new_month = divmod(index, 12)
    if not MIN_YEAR <= new_year <= MAX_YEAR:
        raise ValueError("已到可查看的日期边界。")
    return new_year, new_month + 1


def summarize_records(records):
    totals = dict.fromkeys(CATEGORIES, 0)
    for record in records:
        totals[record["category"]] += record["amount_cents"]
    totals["total"] = sum(totals.values())
    return totals
