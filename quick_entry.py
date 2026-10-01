"""Parse one pasted expense without guessing dates, currencies, or multiple rows."""
import re
import unicodedata
from dataclasses import dataclass
from domain import MAX_DESCRIPTION, parse_amount, cents_to_input

_ENTRY = re.compile(r"(?:[¥￥]\s*)?([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)(?:[ \t]+(.+))?")


@dataclass(frozen=True)
class QuickEntry:
    amount_text: str
    description: str


def parse_quick_entry(text: str) -> QuickEntry:
    """Accept a single RMB amount and optional space-separated description.

    Normalize only the amount's width. Keep the person's description verbatim.
    Grouping is validated before removal; 1,23 must never silently become 123.
    """
    text = text.strip()
    if "\n" in text or "\r" in text:
        raise ValueError("一次只能粘贴一笔：例如 18.5 午饭")
    normalized = unicodedata.normalize("NFKC", text)
    match = _ENTRY.fullmatch(normalized)
    if not match:
        raise ValueError("请使用“金额 说明”，例如 18.5 午饭")
    amount = match.group(1)
    if "," in amount and not re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{1,2})?", amount):
        raise ValueError("金额的千分位格式不正确")
    cents = parse_amount(amount.replace(",", ""))
    # NFKC can change the length of description characters. Locate its boundary
    # in the original text using only the amount/currency prefix.
    original = re.fullmatch(r"[¥￥]?\s*[0-9０-９,，.．]+(?:[ \t　]+(.+))?", text)
    if original is None:
        raise ValueError("请使用人民币金额和说明")
    description = (original.group(1) or "").strip()
    if len(description.encode("utf-16-le")) // 2 > MAX_DESCRIPTION:
        raise ValueError("说明过长，请缩短后再粘贴")
    return QuickEntry(cents_to_input(cents), description)
