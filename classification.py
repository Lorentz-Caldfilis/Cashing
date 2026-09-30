"""Local, derived categories from explicit personal votes and typed lexical evidence.

Unknown fragments remain visible to the decision rule. A marketplace, a weak
character or a personal phrase elsewhere cannot silently erase missing evidence.
Stored labels, decay and reversible learning remain unchanged; see STUDENT_PHASE4.md.
"""
from collections import Counter
import re
import unicodedata
from domain import CATEGORIES
import lexicon
from classification_evidence import Evidence, Decision, composition, context_pattern, explain_residual, derived_suffix

RECENCY = 0.85        # weight of each older label relative to the next newer one
PRIOR = 0.8           # the built-in opinion counts a little less than one label of the person's
DOMINANCE = 2.0       # a winner must outweigh the runner-up this many times
MIN_PHRASE = 2        # shorter labelled phrases only ever match themselves exactly
MAX_PHRASE = 12       # longer labelled phrases only match themselves exactly (bounds the matching)
CACHE_LIMIT = 4096

_TOKEN = re.compile(r"[㐀-䶿一-鿿豈-﫿]|[^\W_㐀-䶿一-鿿豈-﫿]+")
_UNDECIDED = "?"      # evidence exists but does not settle it (conflict, ambiguity, the person's 暂未判断)


def tokens(text):
    """CJK characters one by one; runs of other letters/digits as words. Case, width and
    punctuation are ignored: 'ChatGPT Plus！' → ('chatgpt', 'plus')."""
    return tuple(_TOKEN.findall(unicodedata.normalize("NFKC", text or "").lower()))


def _load_builtin():
    words = {}
    for category, block in lexicon.HEADS.items():
        for word in block.split():
            words[tokens(word)] = ('head', category, 'weak')
    for category, block in lexicon.TERMS.items():
        for word in block.split():
            words[tokens(word)] = ('term', category, 'strong') if len(word) > 1 else ('head', category, 'weak')
    for word in lexicon.AMBIGUOUS.split():
        words[tokens(word)] = ('ambiguous', None, 'none')
    for word in lexicon.POLYSEMOUS_CONTEXTS:
        words[tokens(word)] = ('polysemy', None, 'none')
    for word in lexicon.NEUTRAL.split() + lexicon.CONTEXT.split():
        words[tokens(word)] = ('context', None, 'none')
    for word in lexicon.PLATFORMS.split():
        words[tokens(word)] = ('platform', None, 'none')
    for span, (kind, category, strength) in list(words.items()):
        if kind == 'term':
            for suffix in ('费', '院'):
                if derived_suffix(''.join(span), suffix):
                    words[span + tokens(suffix)] = ('term', category, strength)
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
        """生活 / 工具 / 娱乐, or None when evidence does not settle it."""
        return self.explain(description).category

    def explain(self, description):
        """Immutable, local explanation; offsets index normalized tokens."""
        phrase = tokens(description)
        return self._resolve(phrase) if phrase else Decision(None, 'empty')

    def _resolve(self, phrase):
        if phrase in self._cache:
            return self._cache[phrase]
        if phrase in self._phrases:
            prior = self._builtin(phrase, personal=False)
            votes = Counter()
            labels = sorted(self._phrases[phrase].values(), key=lambda item: item[0], reverse=True)
            for age, (_, category) in enumerate(labels):
                votes[category] += RECENCY ** age
            if prior.category in CATEGORIES:
                votes[prior.category] += PRIOR
            winner = _dominant(votes)
            if winner is _UNDECIDED:
                category = prior.category
                reason = 'prior_after_exception' if category else 'personal_conflict'
            else:
                category = winner
                reason = 'personal_vote' if category else 'personal_abstention'
            evidence = (Evidence(0, len(phrase), ''.join(phrase), 'personal', category, 'personal'),)
            result = Decision(category, reason, evidence + prior.evidence, len(labels))
        else:
            result = self._builtin(phrase, personal=True)
        if len(self._cache) >= CACHE_LIMIT:
            self._cache.clear()
        self._cache[phrase] = result
        return result

    def _builtin(self, phrase, *, personal):
        items = list(self._spans(phrase, personal))
        resolved = []
        for item in items:
            if item.kind == 'unknown':
                role = explain_residual(item, items)
                if role:
                    item = Evidence(item.start, item.end, item.text, role)
            elif item.kind == 'polysemy':
                senses = lexicon.POLYSEMOUS_CONTEXTS[item.text]
                compatible = {senses[near.text] for near in items
                              if near.text in senses and near.kind in {'term', 'head'}
                              and (near.end == item.start or near.start == item.end)}
                if len(compatible) == 1:
                    item = Evidence(item.start, item.end, item.text, 'contextual_sense', compatible.pop(), 'strong')
            resolved.append(item)
        evidence = tuple(resolved)
        decided = {item.category for item in evidence if item.category in CATEGORIES}
        if len(decided) > 1:
            return Decision(None, 'conflicting_categories', evidence)
        if any(item.kind == 'personal' and item.category is None for item in evidence):
            return Decision(None, 'personal_abstention', evidence)
        if any(item.kind in {'ambiguous', 'polysemy'} for item in evidence):
            return Decision(None, 'unresolved_ambiguity', evidence)
        if any(item.kind == 'unknown' for item in evidence):
            return Decision(None, 'unexplained_fragment', evidence)
        if not decided:
            return Decision(None, 'no_purpose_evidence', evidence)
        if sum(item.kind == 'head' for item in evidence) > 1 and not any(
                item.kind in {'term', 'composition', 'personal'} for item in evidence):
            return Decision(None, 'unvalidated_heads', evidence)
        if any(item.kind == 'platform' for item in evidence) and not any(
                item.strength in {'strong', 'personal'} for item in evidence):
            return Decision(None, 'weak_platform_evidence', evidence)
        return Decision(decided.pop(), 'compatible_evidence', evidence)

    def _spans(self, phrase, personal):
        """Cover known lexical units before preferring longer matches.

        Forward greedy matching splits 买水果 into 买水 + 果. This bounded dynamic
        program prefers 买 + 水果 without scoring or favouring any category.
        Unknown tokens remain in the winning path; longer units win coverage ties.
        """
        longest = max(_BUILTIN_LONGEST, self._longest if personal else 0, 8)
        count = len(phrase)
        scores, paths = [None] * (count + 1), [None] * (count + 1)
        scores[count], paths[count] = (0, 0, 0), ()
        for i in range(count - 1, -1, -1):
            tail = scores[i + 1]
            scores[i] = (tail[0] - 1, tail[1], tail[2] - 1)
            paths[i] = (Evidence(i, i + 1, phrase[i], 'unknown'),) + paths[i + 1]
            for n in range(min(longest, count - i), 0, -1):
                span, item = phrase[i:i + n], None
                text = ''.join(span)
                if (personal and span in self._phrases and span != phrase
                        and n <= MAX_PHRASE and len(text) >= MIN_PHRASE):
                    item = Evidence(i, i + n, text, 'personal', self._resolve(span).category, 'personal')
                elif span in BUILTIN:
                    kind, category, strength = BUILTIN[span]
                    item = Evidence(i, i + n, text, kind, category, strength)
                elif n <= 8 and composition(text):
                    item = Evidence(i, i + n, text, 'composition', composition(text), 'weak')
                elif context_pattern(text):
                    item = Evidence(i, i + n, text, context_pattern(text))
                if item is not None:
                    tail = scores[i + n]
                    score = (tail[0], tail[1] + n * n, tail[2] - 1)
                    if score > scores[i]:
                        scores[i], paths[i] = score, (item,) + paths[i + n]
        pending = None
        for item in paths[0]:
            if item.kind == 'unknown':
                if pending is None:
                    pending = item
                else:
                    pending = Evidence(pending.start, item.end, pending.text + item.text, 'unknown')
            else:
                if pending is not None:
                    yield pending
                    pending = None
                yield item
        if pending is not None:
            yield pending



def _dominant(votes):
    """The category (or None, for 暂未判断) that outweighs every other DOMINANCE times, else _UNDECIDED."""
    ranked = votes.most_common(2)
    if not ranked:
        return _UNDECIDED
    if len(ranked) == 2 and ranked[0][1] < DOMINANCE * ranked[1][1]:
        return _UNDECIDED
    return ranked[0][0]
