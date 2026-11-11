"""Register rules: counting checks ported from the declauding skill (Austegard, MIT).

declauding's register catalogues the constructions that mark prose as model-written. Most of them are
judgments and live in jev_rules.py as questions. What stays here is what a per-paragraph question cannot
do: a vocabulary RATE over the whole document, repetition ACROSS sentences, and an orthographic property
(a hyphen) that is a fact about characters, not meaning.

All are off by default. Their thresholds come from declauding's own calibration (Python stdlib docstrings
and a human-written control text), not from riff's labelled corpus; run scripts/bench_structure.py over a
human/AI corpus before turning one on by default.

Codes: CLR013-015 rates and repetition, RIF010 typography.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING

from riff.extract import Block, Document
from riff.rules.base import Finding, finding, regex_matches, snippet_of, static_rule
from riff.textutil import split_sentences

if TYPE_CHECKING:
    from riff.settings import Settings

DECLAUDE = "declauding (Austegard, github.com/oaustegard/claude-skills)"
CORPUS = "Abraham, load-bearing PR-description corpus, via declauding references/corpus.md"

# Paragraph-shaped prose only: a list item, a table cell or a speaker note is not a run of sentences, and
# declauding's counts exclude bullets, headings and tables the same way.
_RUNNING_KINDS = frozenset({"paragraph"})


# Reference prose repeats its frames by design ("If X is true, ... If Y is true, ..."), verse and scripts use
# anaphora on purpose, and a deck or a list of notes is not running prose: the repetition rules skip them.
_NOT_RUNNING_PROSE = ("documentation", "release_notes", "notes", "resume", "presentation", "poem", "script")


def _running(doc: Document) -> list[Block]:
    return [b for b in doc.blocks if b.kind in _RUNNING_KINDS
            and b.text.count("·") < 2 and b.text.count("](http") < 2]


# ---------------------------------------------------------------- CLR013 corpus-register rate

# The 150 highest-lift words of the fastest-growing cluster in Louis Abraham's load-bearing corpus of GitHub
# pull request descriptions (analysis.js of 2026-08-28: 461,121 descriptions over 85 whole weeks; the cluster
# was 0.70% of the first eight weeks and 39.5% of the last four). Copied from declauding's CORPUS_LEAD. Used
# ONLY for a rate -- never as a blocklist: every word here is one a person writes.
CORPUS_LEAD = frozenset("""
admits alone argued armed arms asserted asserts asymmetry backstop bit-identical
bites byte-for-byte byte-identical carried carries carrying carve-out ceiling
cheap chokepoint cited cites contradicted contradicting decides declines defect
defects degrades deliberate deliberately died disagree disagreed disagreement
drains drifted eleven empirically escalates ever faithful falsified filed folded
folds forever genuine genuinely half halves handed held holds honest honestly
honoured indistinguishable inert judged landed lands legitimately lever
load-bearing loses loud loudly machinery mattered measured merely minted mints
mutation-checked mutation-tested mutation-verified never nine nobody nothing
nowhere obligation opposite outright owed parked plainly pre-fix precedent
precisely predates premise probed provably proven proves quietly re-derived
re-derives re-measured re-read re-verified reaches reaped reds refusal refusals
refused refuses refusing refuted remedy reproduces restated rests retires rides
ruling rung says seam self-heals settles short-circuits sitting spellings stamped
stamps standing stranded structurally survived survives surviving sweep symptom
thirteen throwaway told ungated unguarded vacuous vacuously walked wedge wedged
whoever whose worse
""".split())
_CORPUS_WORD = re.compile(r"[a-z0-9/_-]*[a-z][a-z0-9/_-]*")
# Measured by declauding: stdlib docstrings median 0.08 per 100 words (p90 0.17, max 0.32); a human-written
# control 0.34; load-bearing's own human-written README 1.51. So above 1.0 locates the register, and a person
# who writes in it scores there too.
_REGISTER_RATE, _REGISTER_MIN_WORDS = 1.0, 150


@static_rule("CLR013", "flat-certainty-register", "Prose is dense with the vocabulary of the flat-certainty register",
             category="Word Choice", source=f"{CORPUS}; {DECLAUDE}, entries 43-47", default=False, scope="document",
             explanation="The fastest-growing cluster of GitHub PR descriptions -- 0.70% of early 2025, 39.5% of "
             "August 2026 -- is written in flat, verdict-shaped prose whose highest-lift words are 'load-bearing', "
             "'plainly', 'quietly', 'refusal', 're-derived', 'nobody', 'genuinely', 'byte-identical'. This counts "
             "the cluster's top 150 words per 100 words of running prose and flags a rate above 1.0. It locates a "
             "REGISTER, not an author: a person who writes this way scores there too (load-bearing's own README "
             "scores 1.51). Treat it as a cue to read for JEV209-JEV212 and JEV309-JEV312, never as licence to cut "
             "'nothing' or 'measured' on sight.",
             examples=("The guard plainly refuses; nothing else reaches it, and the fix survived a re-derived check.",))
def flat_certainty_register(doc: Document, settings: Settings) -> list[Finding]:
    blocks = _running(doc)
    tokens = [w for b in blocks for w in _CORPUS_WORD.findall(b.text.lower())]
    if len(tokens) < _REGISTER_MIN_WORDS:
        return []
    hits = [w for w in tokens if w in CORPUS_LEAD]
    rate = 100 * len(hits) / len(tokens)
    if rate <= _REGISTER_RATE:
        return []
    counts: dict[str, int] = defaultdict(int)
    for w in hits:
        counts[w] += 1
    top = ", ".join(f"{w} x{n}" for w, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5])
    return [finding("CLR013", doc, blocks[0],
                    f"{rate:.2f} flat-certainty words per 100 ({len(hits)} of {len(tokens)}; {top}); "
                    "above 1.0 is the register, not proof of authorship")]


# ---------------------------------------------------------------- CLR014 echoed skeleton

_ECHO_WORD = re.compile(r"[a-z0-9’'-]+")
# A shared five-word run alone is an idiom ("is the same as using"); requiring it to cover half of the shorter
# sentence is what separates a filled template from two unalike sentences. declauding measured the gram test
# alone at 91 hits over 181,000 words of stdlib docstrings, and single figures with the share added.
_ECHO_MIN_RUN, _ECHO_MIN_SHARE, _ECHO_MIN_WORDS = 5, 0.5, 6


def _longest_run(a: list[str], b: list[str]) -> tuple[int, int]:
    """Length of the longest common contiguous run of words, and where it starts in `a`."""
    best, at = 0, 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best, at = cur[j], i - cur[j]
        prev = cur
    return best, at


@static_rule("CLR014", "echoed-skeleton", "Consecutive sentences built on the same word-for-word skeleton",
             category="Sentence Structure", source=f"{DECLAUDE}, entry 26 (forced triad, third shape)",
             default=False, scope="document", skip_for=_NOT_RUNNING_PROSE,
             explanation="'A shopping cart is an object in the system. A chat room is an object in the system.' "
             "A reader who has read the first has read the second. Flags two adjacent sentences in a paragraph "
             "that share a run of five or more words covering at least half of the shorter one -- a filled "
             "template rather than a shared idiom. Comparing sentences is cross-sentence counting, so it is code. "
             "Skipped for docs, release notes, notes, resumes, decks, poems and scripts, where repetition is "
             "the genre.",
             examples=("A shopping cart is an object in the system. A chat room is an object in the system.",))
def echoed_skeleton(doc: Document, settings: Settings) -> list[Finding]:
    out = []
    for block in _running(doc):
        sents = [s.text for s in split_sentences(block.text)]
        toks = [_ECHO_WORD.findall(s.lower()) for s in sents]
        for i in range(1, len(sents)):
            a, b = toks[i - 1], toks[i]
            shorter = min(len(a), len(b))
            if shorter < _ECHO_MIN_WORDS:
                continue
            run, at = _longest_run(a, b)
            if run >= _ECHO_MIN_RUN and run >= _ECHO_MIN_SHARE * shorter:
                out.append(finding("CLR014", doc, block,
                                   f"two sentences share '{' '.join(a[at:at + run])}' ({run / shorter:.0%} of the "
                                   "shorter); say the second thing differently or merge them",
                                   snippet=snippet_of(sents[i])))
                break  # one per paragraph: the template is the finding, not each repetition of it
    return out


# ---------------------------------------------------------------- CLR015 anaphora run

_RUN_OF = 3


def _opening(unit: str) -> str:
    return " ".join(unit.lower().split()[:2]).strip(",;:.\"'()“”‘’")


def _first_run(units: list[str]) -> int | None:
    """Index of the unit that completes the first run of three openings on the same two words.

    The first unit of a run may carry a lead-in before the repeated words -- "We wanted something to fix,
    something to ship, something to forget" -- so it counts when it contains them, not only when it opens
    with them.
    """
    keys = [_opening(u) for u in units]
    run = 1
    for i in range(1, len(keys)):
        if keys[i] and keys[i] == keys[i - 1]:
            run += 1
        elif keys[i] and f" {keys[i]} " in f" {units[i - 1].lower()} ":
            run = 2
        else:
            run = 1
        if run == _RUN_OF:
            return i
    return None


@static_rule("CLR015", "anaphora-run", "Three sentences or clauses in a row open on the same two words",
             category="Sentence Structure", source=f"{DECLAUDE}, entry 26 (forced triad, anaphora form)",
             default=False, scope="document", skip_for=_NOT_RUNNING_PROSE,
             explanation="'It was a message. It was a permission slip. It was an out.' Or, inside one sentence, "
             "'something to fix, something to ship, something to forget'. A forced triad carried by the opening "
             "words rather than by a comma list, so a tricolon question misses it. Three in a row is the "
             "pattern; two is ordinary parallelism. Comparing openings across sentences is counting, so it is code. "
             "Skipped for docs, release notes, notes, resumes, decks, poems and scripts, where repetition is "
             "the genre.",
             examples=("It was a message. It was a permission slip. It was an out.",))
def anaphora_run(doc: Document, settings: Settings) -> list[Finding]:
    out = []
    for block in _running(doc):
        sents = [s.text for s in split_sentences(block.text)]
        candidates = [("sentences", sents)]
        candidates += [("clauses", [c.strip() for c in re.split(r"[,;]\s+", s) if c.strip()]) for s in sents]
        for scope, units in candidates:
            i = _first_run(units)
            if i is not None:
                out.append(finding("CLR015", doc, block,
                                   f"three {scope} in a row open with '{_opening(units[i])}'",
                                   snippet=snippet_of(units[i - 2])))
                break
    return out


# ---------------------------------------------------------------- RIF010 predicate-position hyphen

# A compound modifier after a linking verb, ending the clause: "the team is cross-functional." Compounds that
# keep the hyphen everywhere (prefixes that always take one, dictionary forms) are excluded.
_LINKING = (r"(?:is|are|was|were|be|been|being|seems?|seemed|feels?|felt|looks?|looked|became|becomes?"
            r"|remains?|remained|stays?|stayed)")
_PREDICATE_HYPHEN = re.compile(
    r"\b" + _LINKING + r"\s+(?:(?:very|more|less|fully|mostly|entirely|highly|still|now|not)\s+)?"
    r"([a-z]+(?:-[a-z]+)+)(?=\s*(?:[.,;:!?)]|$|\s+(?:and|or|but|because|when|if|so)\b))",
    re.IGNORECASE | re.MULTILINE,
)
_ALWAYS_HYPHENATED = re.compile(
    r"^(?:self|ex|all|non|anti|pre|post|re|co|semi|quasi|pseudo|multi|sub|mid)-"
    r"|-(?:based|safe|free|wide|like|proof|sensitive|insensitive|aware|specific|friendly|only|to-date)$"
    r"|^(?:read-only|write-only|built-in|opt-in|opt-out|so-called|up-to-date|out-of-date|one-off|follow-up|"
    r"set-up|log-in|sign-in|check-in|add-on|plug-in|drop-in|in-house|on-premises|x-ray|e-mail|t-shirt)$",
    re.IGNORECASE,
)
_HYPHEN_CLUSTER = 2


@static_rule("RIF010", "predicate-hyphen", "Compound keeps its hyphen after the noun ('the team is cross-functional')",
             category="Formatting", source=f"{DECLAUDE}, entry 36; Chicago Manual of Style 7.85", default=False,
             scope="document",
             explanation="Writers hyphenate a compound before the noun ('a data-driven report') and mostly drop it "
             "after ('the report is data driven'). A model hyphenates the pair wherever it appears. One instance "
             "proves nothing, so this flags only when a document does it twice or more. Hyphenation is a fact "
             "about characters, so it is a code check. Compounds that keep the hyphen in every position "
             "(self-, all-, ex-; -safe, -free, -based, -sensitive; dictionary forms like 'read-only') are skipped.",
             examples=("The team is cross-functional and the report is data-driven.",))
def predicate_hyphen(doc: Document, settings: Settings) -> list[Finding]:
    hits = []
    for block in doc.prose:
        for m, line, col in regex_matches(block, _PREDICATE_HYPHEN):
            if _ALWAYS_HYPHENATED.search(m.group(1)):
                continue
            hits.append(finding("RIF010", doc, block,
                                f"'{m.group(1)}' after a linking verb; drop the hyphen "
                                f"('{m.group(1).replace('-', ' ')}')",
                                line=line, col=col, snippet=snippet_of(m.string, m.start())))
    return hits if len(hits) >= _HYPHEN_CLUSTER else []
