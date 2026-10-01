"""Typed lexical evidence, bounded composition and explicit residual handling.

Offsets index normalized tokens, not original string character positions. No signal
here writes a label or claims a statistical confidence probability.
"""
from dataclasses import dataclass
from functools import lru_cache
import re
import lexicon


@dataclass(frozen=True)
class Evidence:
    start: int
    end: int
    text: str
    kind: str
    category: str | None = None
    strength: str = 'none'


@dataclass(frozen=True)
class Decision:
    category: str | None
    reason: str
    evidence: tuple[Evidence, ...] = ()
    label_count: int = 0


QUANTITY = re.compile(r'(?:[0-9一二三四五六七八九十两半]+(?:份|杯|瓶|包|盒|件|支|个|本|张|次)|x[0-9]+|[0-9]+号线|第?[0-9一二三四五六七八九十]+|[0-9]+(?:g|gb|m|mb|t|tb))')
PACK = re.compile(r'(?:补充|家庭|旅行|便携|大|小|独立|试用)装')
# Product composition is bounded and has explicit semantic parts, not arbitrary .*.
CLOTHING = re.compile(r'(?:春|夏|秋|冬|羊毛|棉|绒|保暖|加厚|长|短|内|外|睡|运动|围){1,3}(?:衣|裤|袜|帽|巾|鞋)')
COOKED = re.compile(r'(?:烤|炒|炸|蒸|煮|炖|卤|焖)(?:冷|热|干|酸|辣|甜|咸|香|油|葱|蒜|肉|牛|羊|猪|鸡|鸭|虾|蛋){0,4}(?:面|粉|饭|汤|饼|饺|鸡|鸭|虾|蛋|串|肠|红薯|土豆|玉米|茄子|豆腐)')
RECIPE = re.compile(r'(?:牛|羊|猪|鸡|鱼|虾|肉|蛋|香|丝|葱|油|番茄|酸辣|热干|麻酱|炸酱|豆角|排骨|挂){1,5}(?:面|粉|饭|盖饭|汤|饼|饺|串|包)')
VEHICLE = re.compile(r'(?:(?:修|维修)?(?:自行|电动|共享|出租)车(?:维修|保养)?|洗车)')
POT = re.compile(r'(?:鸡|鸭|牛|羊|虾)(?:公|肉|仔)?(?:煲|锅)')
QUALIFIER = re.compile(r'[㐀-䶿一-鿿豈-﫿a-z0-9]{1,16}')


@lru_cache(maxsize=4096)
def composition(text):
    if any(pattern.fullmatch(text) for pattern in (CLOTHING, COOKED, POT, RECIPE, VEHICLE)):
        return '生活'
    return None


def context_pattern(text):
    if QUANTITY.fullmatch(text):
        return 'quantity'
    if PACK.fullmatch(text):
        return 'package_size'
    return None


def derived_suffix(head, tail):
    """Typed derivation; arbitrary unknown suffixes are never discarded."""
    if tail == '费':
        return 'charge_suffix'
    if tail == '院' and head == '电影':
        return 'venue_suffix'
    return None


def explain_residual(item, items):
    """Return the explicit local role of a previously unmatched fragment, or None.

    A recognized word elsewhere is insufficient: qualifiers must be adjacent to
    the relevant typed head/action, and are never allowed to hide another signal.
    """
    before = next((x for x in items if x.end == item.start), None)
    after = next((x for x in items if x.start == item.end), None)
    if after and after.text in lexicon.SUBJECT_HEADS.split() and QUALIFIER.fullmatch(item.text):
        return 'subject_qualifier'
    if after and after.text in lexicon.EVENT_HEADS.split() and QUALIFIER.fullmatch(item.text):
        return 'event_qualifier'
    if after and after.text in lexicon.FOOD_HEADS.split() and re.fullmatch(r'[㐀-䶿一-鿿]{1,5}(?:省|市|县|州)', item.text):
        return 'place_qualifier'
    if ((before and before.text in (lexicon.DOCUMENT_ACTIONS + ' ' + lexicon.STUDY_ACTIVITIES).split())
            or (after and after.text in lexicon.DOCUMENT_ACTIONS.split())):
        if any(item.text.endswith(word) for word in lexicon.DOCUMENT_OBJECTS.split()):
            return 'document_object'
    if after and after.text in lexicon.HARDWARE_HEADS.split():
        if item.text in lexicon.HARDWARE_QUALIFIERS.split():
            return 'hardware_qualifier'
    if after and after.text in lexicon.PHYSICAL_HEADS.split() and item.text in lexicon.PHYSICAL_MODIFIERS.split():
        return 'product_modifier'
    if after and after.text in {'话费', '流量'} and item.text == '手机':
        return 'account_qualifier'
    if before and before.kind in {'term', 'personal'}:
        if PACK.fullmatch(item.text):
            return 'package_size'
        if item.text == '费':
            return 'charge_suffix'
        if item.text == '维修' and before.text in lexicon.HARDWARE_HEADS.split():
            return 'maintenance'
        if item.text == '电子版' and before.text in {'小说', '漫画', *lexicon.SUBJECT_HEADS.split()}:
            return 'format'
        if item.text in {'局', '吧'} and before.text in {'桌游', '台球', '游戏'}:
            return 'activity_suffix'
        if item.text in {'pro', 'plus', '会员', '秋促', '春促', '夏促', '冬促'}:
            return 'service_variant'
        if item.text == '票' and before.text in {'高铁', '火车', '动车', '地铁', '公交'}:
            return 'ticket_suffix'
        if item.text == '包' and before.text in {'流量', '话费', '网盘'}:
            return 'plan_variant'
        if item.text in {'碗', '杯'} and before.text in lexicon.FOOD_HEADS.split():
            return 'serving_container'
        if item.text == '包厢' and before.text == 'ktv':
            return 'venue_option'
    return None
