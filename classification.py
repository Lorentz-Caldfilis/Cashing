"""Derived category: 生活, 工具, 娱乐 — or None when the evidence is not strong enough.

A category is an interpretation, not a fact (Philosophy §2.3). The only category facts are the
ones the person states in Review; everything else is computed from them and from built-in
knowledge whenever a record is read, so the interpretation improves as the person corrects it
and never trains on its own guesses. Layers, as in Philosophy §4.5:

1. The person's own phrase. Every record the person categorised is a vote for that exact
   description. Votes decay by RECENCY per newer label, the built-in opinion of the phrase adds
   PRIOR, and a category is taken only when it outweighs the runner-up DOMINANCE times; if none
   does, the built-in opinion stands (or, without one, nothing is decided). So a first label on
   something new is learnt at once, one exception (a birthday 午饭 marked 娱乐) does not
   reinterpret every 午饭, and two consistent corrections do. Choosing 暂未判断 is a vote too.
2. Phrases inside the text, longest first: the person's labelled phrases (at least MIN_PHRASE
   characters) and the built-in words of lexicon.py, the person's winning a tie. All must agree;
   a phrase the person left undecided, or a built-in AMBIGUOUS word without any of the person's
   phrases beside it, means nothing is decided.
3. Otherwise nothing is decided. That is not a task for anyone (Philosophy §4.3).

No statistics over character n-grams: on short Chinese descriptions they generalise from
shared characters (周黑鸭 ~ 烤鸭 ~ 小黄鸭), which measured as the main source of wrong guesses.
Evaluation, alternatives considered and the numbers behind the constants:
docs/development/CLASSIFICATION.md. Standard library only; no model files, no network.
"""
from collections import Counter
import re
import unicodedata
from domain import CATEGORIES
import lexicon

RECENCY = 0.85        # weight of each older label relative to the next newer one
PRIOR = 0.8           # the built-in opinion counts a little less than one label of the person's
DOMINANCE = 2.0       # a winner must outweigh the runner-up this many times
MIN_PHRASE = 2        # shorter labelled phrases only ever match themselves exactly
MAX_PHRASE = 12       # longer labelled phrases only match themselves exactly (bounds the matching)
CACHE_LIMIT = 4096

_TOKEN = re.compile(r"[㐀-䶿一-鿿豈-﫿]|[^\W_㐀-䶿一-鿿豈-﫿]+")
_UNDECIDED = "?"      # evidence exists but does not settle it (conflict, ambiguity, the person's 暂未判断)
_AMBIGUOUS = object()
_NEUTRAL = object()
_PERSONAL = "personal"
_BUILTIN = "builtin"


def tokens(text):
    """CJK characters one by one; runs of other letters/digits as words. Case, width and
    punctuation are ignored: 'ChatGPT Plus！' → ('chatgpt', 'plus')."""
    return tuple(_TOKEN.findall(unicodedata.normalize("NFKC", text or "").lower()))


def _load_builtin():
    words = {}
    for category, block in lexicon.HEADS.items():
        for word in block.split():
            words[tokens(word)] = category
    for category, block in lexicon.TERMS.items():
        for word in block.split():
            words[tokens(word)] = category
    for word in lexicon.AMBIGUOUS.split():
        words[tokens(word)] = _AMBIGUOUS
    for word in lexicon.NEUTRAL.split():
        words[tokens(word)] = _NEUTRAL
    return words


BUILTIN = _load_builtin()
_BUILTIN_LONGEST = max(map(len, BUILTIN))


class Classifier:
    """Interpretations from the person's labels. ``labels`` are ``(record_id, description,
    category_or_None, order)``; ``order`` sorts labels in the order they were given."""

    def __init__(self, labels=()):
        self._records = {}   # record id -> (phrase, order, category)
        self._phrases = {}   # phrase -> {record id: (order, category)}
        self._longest = 0
        self._cache = {}
        for record_id, description, category, order in labels:
            self._add(record_id, description, category, order)

    # ---- the person's labels ------------------------------------------------------------------
    def set_label(self, record_id, description, category, order):
        """Record (or move) the label the person gave one record."""
        self._remove(record_id)
        self._add(record_id, description, category, order)
        self._cache.clear()

    def drop_label(self, record_id):
        if self._remove(record_id):
            self._cache.clear()

    def _add(self, record_id, description, category, order):
        if category is not None and category not in CATEGORIES:
            raise ValueError(f"Unknown category {category!r}")
        phrase = tokens(description)
        if not phrase:
            return  # an empty description says nothing about any other record
        self._records[record_id] = (phrase, order, category)
        self._phrases.setdefault(phrase, {})[record_id] = (order, category)
        if len(phrase) <= MAX_PHRASE:
            self._longest = max(self._longest, len(phrase))

    def _remove(self, record_id):
        entry = self._records.pop(record_id, None)
        if entry is None:
            return False
        phrase = entry[0]
        votes = self._phrases[phrase]
        del votes[record_id]
        if not votes:
            del self._phrases[phrase]
        return True

    # ---- interpretation -------------------------------------------------------------------------
    def classify(self, description):
        """生活 / 工具 / 娱乐, or None when the evidence does not settle it."""
        phrase = tokens(description)
        if not phrase:
            return None
        category = self._resolve(phrase)
        return category if category in CATEGORIES else None

    def _resolve(self, phrase):
        if phrase in self._cache:
            return self._cache[phrase]
        if phrase in self._phrases:
            prior = self._builtin(phrase, personal=False)
            votes = Counter()
            labels = sorted(self._phrases[phrase].values(), key=lambda item: item[0], reverse=True)
            for age, (_, category) in enumerate(labels):
                votes[category] += RECENCY ** age
            if prior in CATEGORIES:
                votes[prior] += PRIOR
            result = _dominant(votes)
            if result is _UNDECIDED and prior in CATEGORIES:
                result = prior  # one exception does not overturn what is otherwise clear
            elif result is None:
                result = _UNDECIDED  # the person's own 暂未判断 wins
        else:
            result = self._builtin(phrase, personal=True)
        if len(self._cache) >= CACHE_LIMIT:
            self._cache.clear()
        self._cache[phrase] = result
        return result

    def _builtin(self, phrase, *, personal):
        """What the phrases inside the text say: a category, None (no evidence) or _UNDECIDED."""
        decided, blocked, ambiguous, own = set(), False, False, False
        for span, source in self._spans(phrase, personal):
            if source is _PERSONAL:
                own = True
                category = self._resolve(span)
                if category in CATEGORIES:
                    decided.add(category)
                else:
                    blocked = True
                continue
            value = BUILTIN[span]
            if value is _AMBIGUOUS:
                ambiguous = True
            elif value is not _NEUTRAL:
                decided.add(value)
        if blocked or (ambiguous and not own) or len(decided) > 1:
            return _UNDECIDED
        return decided.pop() if decided else None

    def _spans(self, phrase, personal):
        """Forward longest match; the person's phrase wins a tie with a built-in word."""
        longest = max(_BUILTIN_LONGEST, self._longest if personal else 0)
        i = 0
        while i < len(phrase):
            for n in range(min(longest, len(phrase) - i), 0, -1):
                span = phrase[i:i + n]
                if (personal and span in self._phrases and span != phrase
                        and n <= MAX_PHRASE and sum(map(len, span)) >= MIN_PHRASE):
                    yield span, _PERSONAL
                    break
                if span in BUILTIN:
                    yield span, _BUILTIN
                    break
            else:
                n = 1
            i += n



def _dominant(votes):
    """The category (or None, for 暂未判断) that outweighs every other DOMINANCE times, else _UNDECIDED."""
    ranked = votes.most_common(2)
    if not ranked:
        return _UNDECIDED
    if len(ranked) == 2 and ranked[0][1] < DOMINANCE * ranked[1][1]:
        return _UNDECIDED
    return ranked[0][0]
