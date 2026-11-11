"""Check that an edit kept every claim: `riff --compare SOURCE REWRITE`.

Acting on lint findings is a register edit: it should change how a draft sounds and nothing about what it
claims. The two ways it goes wrong -- a claim dropped, a fact invented -- both read fluently afterwards,
which is why a read-through misses them. This compares the two versions lexically and reports:

  LOST   a number, name, quotation, code span or link target that was in the source and is gone;
  ADDED  one of those that is in the rewrite and nowhere in the source (an invented specific);
  COUNT  fewer superlative, scope, negation or hedge constructions than the source had.

Deliberately lexical. An embedding of a faithful rewrite and of one that dropped a ranking word sit at
nearly the same cosine, because paraphrase invariance is what encoders are trained for. Constructions, not
tokens, are counted for the second group, because "the format that most invites X" rewritten as "more than
most formats do" keeps the token "most" and loses the ranking.

Ported from declauding's declaude_diff.py (Austegard, github.com/oaustegard/claude-skills, MIT).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from riff.textutil import split_sentences

# Spans a prose edit must leave alone; a change inside one is its own class, not a set of missing tokens.
_FENCED = re.compile(r"^```.*?^```", re.S | re.M)
_CODE_SPAN = re.compile(r"`[^`\n]+`|<code>.*?</code>", re.S | re.I)
_URL = re.compile(r"https?://[^\s)\"'<>\]]+")

_NUMBER = re.compile(r"(?<![\w.])[+−-]?\d[\d,]*(?:\.\d+)?%?(?!\w)")
_NUMBER_WORD = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
    "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19", "twenty": "20",
}

# A superlative ranks over a set; a comparative does not.
_SUPERLATIVE = re.compile(
    r"\bthe\s+(?:single\s+|very\s+)?(?:most|least|best|worst|first|last|only|"
    r"largest|smallest|highest|lowest|fastest|slowest|[a-z]{3,}est)\b"
    r"|\bmost\s+likely\s+to\b|\bby\s+far\b|\bof\s+(?:all|any)\b"
    r"|\bthe\s+\w+(?:\s+(?:that|which|who))?\s+(?:most|least)\s+\w+",
    re.I,
)
# Words that set a claim's scope: losing one turns a universal into an example, or the reverse.
_SCOPE = re.compile(
    r"\b(?:all|every|each|none|no|any|both|either|neither|only|solely|exclusively"
    r"|always|never|entirely|wholly|simultaneously|at\s+once|per|across)\b", re.I)
# A hedge with a condition attached is a real qualification; losing one may overstate the claim.
_HEDGE = re.compile(
    r"\b(?:roughly|approximately|about|around|nearly|almost|mostly|largely|generally|typically|usually|often|"
    r"sometimes|may|might|could|would|likely|probably|apparently|seems?|appears?|estimated?)\b", re.I)
_NEGATION = re.compile(r"\b(?:not|never|without|cannot|lacks?|absent|fails?\s+to)\b|n't\b", re.I)

_CAPITALIZED = re.compile(r"\b[A-Z][A-Za-z0-9]*(?:[-.][A-Za-z0-9]+)*\b")
_NOT_A_NAME = frozenset(
    "A An The I If In On At To Of For And But Or So It This That These Those We You They He She There Here "
    "When Where What Why How Not No Its His Her Their Our My Your".split())
_QUOTED = re.compile(r"[\"“]([^\"”\n]{3,120})[\"”]")

MEMBERSHIP = ("number", "name", "quoted", "verbatim")
COUNTED = ("superlative", "scope", "negation", "hedge")

NOTES = {
    "number": "a number in the source is not in the rewrite; every figure, date and version must survive",
    "name": "a name, product or identifier in the source is not in the rewrite",
    "quoted": "quoted material changed; an edit does not rewrite inside quotation marks",
    "verbatim": "code, a fenced block or a link target changed",
    "superlative": "a ranking construction was lost; a comparative is not a superlative",
    "scope": "a scope word was lost; a universal may have become an example, or the reverse",
    "negation": "a negation was lost; the claim may now say the opposite",
    "hedge": "a hedge was lost; check it was not carrying a real condition",
}
ADDED_NOTE = "in the rewrite and nowhere in the source; an edit must not invent a fact, name, number or citation"


@dataclass(frozen=True)
class Change:
    direction: str  # LOST, ADDED or COUNT
    kind: str
    token: str
    source: int
    rewrite: int
    note: str


def _hold_out(text: str) -> tuple[str, list[str]]:
    held: list[str] = []

    def take(m: re.Match[str]) -> str:
        held.append(m.group(0).strip())
        return " "

    for pattern in (_FENCED, _CODE_SPAN, _URL):
        text = pattern.sub(take, text)
    return text, held


def _numbers(text: str) -> Counter[str]:
    found = Counter(m.group(0).replace(",", "").lstrip("+") for m in _NUMBER.finditer(text))
    for word, digit in _NUMBER_WORD.items():
        n = len(re.findall(rf"\b{word}\b", text, re.I))
        if n:
            found[digit] += n
    return found


def _names(text: str) -> Counter[str]:
    """Capitalized tokens that do not open a sentence or a line: names, products, versions."""
    found: Counter[str] = Counter()
    for line in text.splitlines():
        for sentence in split_sentences(line.lstrip("#>-*+ \t")):
            for i, m in enumerate(_CAPITALIZED.finditer(sentence.text)):
                token = m.group(0)
                if (i == 0 and m.start() == 0) or token in _NOT_A_NAME:
                    continue
                found[token] += 1
    return found


def features(text: str) -> dict[str, Counter[str]]:
    body, held = _hold_out(text)
    return {
        "number": _numbers(body),
        "name": _names(body),
        "quoted": Counter(m.group(1).strip() for m in _QUOTED.finditer(body)),
        "verbatim": Counter(held),
        "superlative": Counter(m.group(0).lower() for m in _SUPERLATIVE.finditer(body)),
        "scope": Counter(" ".join(m.group(0).lower().split()) for m in _SCOPE.finditer(body)),
        "negation": Counter(m.group(0).lower() for m in _NEGATION.finditer(body)),
        "hedge": Counter(m.group(0).lower() for m in _HEDGE.finditer(body)),
    }


def compare(source: str, rewrite: str, waive: tuple[str, ...] = ()) -> list[Change]:
    """What the rewrite lost or invented relative to the source. Empty means every claim survived."""
    a, b = features(source), features(rewrite)
    waived = [w.lower() for w in waive]

    def ok(token: str) -> bool:
        return not any(w in token.lower() for w in waived)

    out: list[Change] = []
    # Presence, not frequency: a name used twelve times in the source and thirteen in the rewrite was not
    # invented. What matters is a token that was there and is gone, or one that was never there.
    for kind in MEMBERSHIP:
        for token, n in a[kind].items():
            if ok(token) and not b[kind].get(token):
                out.append(Change("LOST", kind, token, n, 0, NOTES[kind]))
        for token, n in b[kind].items():
            if ok(token) and not a[kind].get(token):
                out.append(Change("ADDED", kind, token, 0, n, ADDED_NOTE))
    # Counted, not matched: "the format that most invites X" -> "the format most likely to invite X" keeps
    # the ranking and changes every word of it, so only the total carries signal.
    for kind in COUNTED:
        na = sum(n for t, n in a[kind].items() if ok(t))
        nb = sum(n for t, n in b[kind].items() if ok(t))
        if nb < na:
            gone = sorted(set(a[kind]) - set(b[kind]))
            note = f"{na - nb} fewer; {NOTES[kind]}"
            if gone:
                note += f". Gone: {', '.join(repr(g) for g in gone[:4])}"
            out.append(Change("COUNT", kind, f"{kind} total", na, nb, note))
    order = {"LOST": 0, "ADDED": 1, "COUNT": 2}
    return sorted(out, key=lambda c: (order[c.direction], c.kind, c.token))


def read_for_compare(path: str) -> str:
    """Markdown and text are compared as written, so code spans and link targets survive; other formats
    are compared on the prose riff extracts from them."""
    p = Path(path)
    if p.suffix.lower() in (".md", ".markdown", ".txt", ".text", ""):
        return p.read_text(encoding="utf-8")
    from riff.extract import extract

    doc = extract(path)
    return "\n\n".join(b.text for b in doc.blocks)


def render(changes: list[Change], label: str) -> str:
    if not changes:
        return f"{label}: every claim survives, nothing invented"
    lines = [f"{label}: {len(changes)} finding(s)", ""]
    for c in changes:
        lines.append(f"  [{c.direction:5}] {c.kind:<11} {c.token[:60]!r}  source {c.source} -> rewrite {c.rewrite}")
        lines.append(f"          {c.note}")
    lines += ["", "A finding is a question, not a verdict: a claim the edit dropped, a fact it invented, or a",
              "rephrasing this check cannot see through. Pass --waive TOKEN for the rephrasings."]
    return "\n".join(lines)


def as_json(changes: list[Change], label: str) -> dict:
    return {"target": label, "findings": [asdict(c) for c in changes]}
