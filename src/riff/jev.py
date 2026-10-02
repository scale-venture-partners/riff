"""The Jev backend: plan one Noul call per unit of the document, at every level a rule asks about.

riff reads a document as a hierarchy -- document > sections > titles and paragraphs > sentences --
and each Jev rule declares the level it judges (its scope). The plan groups the selected rules by
level and makes one call per unit at that level: per paragraph for most rules, per title, per
section with its title and body, or once for the whole document. Within a unit, every rule for that
level shares the call, since the questions are identical and the unit's text is the state.

Document-scope rules also choose a view: the prose ("text"), the outline of titles alone ("outline")
-- the way a reader skims a deck's titles to follow its argument -- or each section's title with its
opening line ("structure"), where eyebrows and lead-ins carry a document's stated order.

Units whose token estimate would exceed Jev's per-request state budget are skipped with a note.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from riff.extract import Block, Document, Section
from riff.rules.base import REGISTRY, Finding, Rule, snippet_of
from riff.settings import Settings
from riff.textutil import estimate_tokens, split_sentences, word_count

# Jev's documented budget is 32k tokens for state + longest question; stay well under with headroom for questions.
_MAX_STATE_TOKENS = 24_000
# Paragraph and sentence units under this many words are not asked about. Slide copy is short --
# three quarters of a typical deck's text blocks are under eight words -- so decks get a lower floor.
_MIN_WORDS = 8
_MIN_WORDS_BY_FORMAT = {"pptx": 4}
# Below this, a block is a fragment, and only rules marked `fragments` are asked about it.
DISCOURSE_MIN_WORDS = 8
# An outline needs a few titles to have a shape; a two-heading memo has no narrative to judge.
_MIN_OUTLINE_TITLES = 3


def _is_link_list(text: str) -> bool:
    """A run of '·'-separated links or a citation dump is not prose; don't ask prose questions about it."""
    return text.count("·") >= 2 or text.count("](http") >= 2


def min_words(doc: Document, settings: Settings) -> int:
    """The word floor for paragraph and sentence units: the setting, else the format's default."""
    if settings.jev_min_words is not None:
        return settings.jev_min_words
    return _MIN_WORDS_BY_FORMAT.get(doc.format, _MIN_WORDS)


class JevUnavailable(RuntimeError):
    """Raised when Jev rules are requested but the backend cannot run. Message names the fixes."""


def _require_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise JevUnavailable(
            "Jev rules are enabled but TYPESAFE_API_KEY is not set.\n"
            "  Fix: export TYPESAFE_API_KEY=... (create one at https://console.typesafe.ai/)\n"
            "  Or:  run with --no-jev to lint with static rules only."
        )
    return key


def build_questions(codes: list[str]):
    from typesafe_sdk import Noul

    questions = {}
    for code in codes:
        rule = REGISTRY[code]
        if rule.kind == "jev" and rule.question is not None:
            questions[code] = Noul(instructions=dict(rule.question))
    return questions


@dataclass
class Unit:
    """One Jev call: a piece of the document at one level, and the rules asked about it."""

    scope: str
    anchor: Block  # where findings are reported
    state: object  # the text, or a small dict of named parts, sent as Jev's state
    codes: list[str]
    snippet: str = ""  # what a finding shows; defaults to the anchor's text

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.state if isinstance(self.state, str) else str(self.state))


def _title_kind(doc: Document, section: Section) -> str:
    if doc.format == "pptx":
        return "slide title"
    return f"section heading (level {section.level})"


def _outline_text(doc: Document) -> str:
    unit = "Slide" if doc.format == "pptx" else "Section"
    lines = []
    for i, (level, label, title) in enumerate(doc.outline, start=1):
        indent = "  " * max(level - 1, 0)
        where = label if doc.format == "pptx" else f"{unit.lower()} {i}"
        lines.append(f"{indent}{i}. ({where}) {title}")
    return "\n".join(lines)


_OPENING_WORDS = 14


def _opening(section: Section, n: int = _OPENING_WORDS) -> str:
    """The first words of a section's body: a slide's eyebrow or kicker, a section's lead-in."""
    words = section.body_text.split()
    return " ".join(words[:n]) + (" ..." if len(words) > n else "")


def _structure_text(doc: Document) -> str:
    """Each titled section as its title plus its opening line.

    Order is often carried outside the titles -- a deck's eyebrows ("STEP 6: HOOKS"), a report's
    lead-ins -- so an outline of titles alone can't show that step 6 came before step 5. The whole
    prose buries it; title plus opening line is the part a reader uses to keep their place.
    """
    lines = []
    for i, s in enumerate((s for s in doc.walk_sections() if s.title is not None), start=1):
        where = s.label if doc.format == "pptx" else f"section {i}"
        opening = _opening(s)
        lines.append(f"{i}. ({where}) {s.title.text}" + (f" -- {opening}" if opening else ""))
    return "\n".join(lines)


def _prose_text(doc: Document) -> str:
    return "\n\n".join(b.text for b in doc.prose if not _is_link_list(b.text)).strip()


def plan_units(doc: Document, codes: list[str], settings: Settings) -> list[Unit]:
    """Every Jev call this lint will make, grouped by level."""
    jev = [c for c in codes if REGISTRY[c].kind == "jev"]
    by_scope: dict[tuple[str, str], list[str]] = {}
    for c in jev:
        rule = REGISTRY[c]
        by_scope.setdefault((rule.scope, rule.view), []).append(c)
    floor = min_words(doc, settings)
    units: list[Unit] = []

    if codes_ := by_scope.get(("block", "text")):
        fragment_codes = [c for c in codes_ if REGISTRY[c].fragments]
        for b in doc.prose:
            if b.word_count < floor or _is_link_list(b.text):
                continue
            asked = codes_ if b.word_count >= DISCOURSE_MIN_WORDS else fragment_codes
            if asked:
                units.append(Unit("block", b, b.text, asked))

    if codes_ := by_scope.get(("sentence", "text")):
        for b in doc.prose:
            if _is_link_list(b.text):
                continue
            for sent in split_sentences(b.text):
                if word_count(sent.text) >= floor:
                    units.append(Unit("sentence", b, sent.text, codes_, snippet=snippet_of(sent.text)))

    sections = list(doc.walk_sections())
    titled = [s for s in sections if s.title is not None]
    # Title and section rules judge claims and whether bodies deliver them; a divider has
    # neither. Positions still count every titled section, so "3 of 12" stays true.
    judged = [s for s in titled if not s.is_divider]

    if codes_ := by_scope.get(("title", "text")):
        # A title is judged with where it sits and what it heads: a cover, a divider and a closing
        # slide carry label-like titles by design, and only their place and body give that away.
        for i, s in enumerate(titled, start=1):
            if s in judged and word_count(s.title.text) >= 2:
                units.append(Unit("title", s.title, {
                    "kind": _title_kind(doc, s), "title": s.title.text,
                    "position": f"{i} of {len(titled)}",
                    "words_under_it": word_count(s.body_text), "opening": _opening(s)}, codes_))

    if codes_ := by_scope.get(("section", "text")):
        # A section is judged on its body against its title. Under a couple of lines -- a quote's
        # attribution, a divider's subtitle -- there is no body to deliver anything, so no question.
        for i, s in enumerate(titled, start=1):
            body = s.body_text
            if s in judged and word_count(body) >= 2 * floor:
                where = f"{'slide' if doc.format == 'pptx' else 'section'} {i} of {len(titled)}"
                state = {"position": where, "title": s.title.text, "body": body}
                if s.visuals:
                    state["charts_or_images"] = f"{s.visuals} (not shown; only the text is)"
                units.append(Unit("section", s.title, state, codes_))

    anchor = (doc.prose[0] if doc.prose else (doc.blocks[0] if doc.blocks else None))
    if anchor is not None:
        if (codes_ := by_scope.get(("document", "text"))) and (text := _prose_text(doc)):
            units.append(Unit("document", anchor, text, codes_))
        enough = len(doc.outline) >= _MIN_OUTLINE_TITLES
        kind = "slide deck" if doc.format == "pptx" else "document"
        if (codes_ := by_scope.get(("document", "outline"))) and enough:
            units.append(Unit("document", anchor, {"kind": kind, "outline": _outline_text(doc)}, codes_,
                              snippet="(the outline)"))
        if (codes_ := by_scope.get(("document", "structure"))) and enough:
            units.append(Unit("document", anchor, {"kind": kind, "sections": _structure_text(doc)}, codes_,
                              snippet="(the outline)"))
    return units


async def run_jev(doc: Document, codes: list[str], settings: Settings, *, debug: bool = False) -> tuple[list[Finding], dict]:
    """Return (findings, stats). Raises JevUnavailable if the key is missing.

    Per-unit API failures are counted in stats["errors"], never disguised as findings; the caller
    turns a nonzero count into a loud, non-zero exit. With debug=True, stats["probabilities"] holds
    every (line, code, probability) so a user tuning thresholds can see the full distribution.
    """
    from riff.rules import load_rules

    load_rules()
    if not [c for c in codes if REGISTRY[c].kind == "jev"]:
        return [], {"blocks": 0, "calls": 0, "input_tokens": 0, "skipped": 0}
    _require_key()

    from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy, TypeSafeError

    units = plan_units(doc, codes, settings)
    per_scope: dict[str, int] = {}
    for u in units:
        per_scope[u.scope] = per_scope.get(u.scope, 0) + 1
    stats = {"blocks": per_scope.get("block", 0), "units": per_scope, "min_words": min_words(doc, settings),
             "calls": 0, "input_tokens": 0, "skipped": 0, "errors": 0, "error_detail": [], "probabilities": []}
    findings: list[Finding] = []
    sem = asyncio.Semaphore(settings.jev_concurrency)
    questions = {}

    async with AsyncTypeSafeClient(model=settings.model, timeout=60.0,
                                   retry=RetryPolicy(max_retries=3, timeout=90.0)) as client:

        async def one(unit: Unit) -> list[Finding]:
            if unit.tokens > _MAX_STATE_TOKENS:
                stats["skipped"] += 1
                return []
            key = tuple(unit.codes)
            if key not in questions:
                questions[key] = build_questions(unit.codes)
            async with sem:
                try:
                    resp = await client.system_one(unit.state, questions[key])
                except TypeSafeError as exc:
                    stats["errors"] += 1
                    stats["error_detail"].append(f"{unit.scope} {unit.anchor.location()} {type(exc).__name__}: {exc}")
                    return []
            stats["calls"] += 1
            stats["input_tokens"] += resp.usage.input_tokens
            if debug:
                for c in unit.codes:
                    a = resp.answers.get(c)
                    if a is not None and hasattr(a, "noul"):
                        stats["probabilities"].append((unit.anchor.line, c, round(float(a.noul), 3)))
            return _findings_for_block(doc, unit.anchor, resp, unit.codes, settings, snippet=unit.snippet)

        for result in await asyncio.gather(*(one(u) for u in units)):
            findings.extend(result)
    return findings, stats


def _findings_for_block(doc: Document, block: Block, resp, codes: list[str], settings: Settings,
                        snippet: str = "") -> list[Finding]:
    out = []
    answers = resp.answers
    for code in codes:
        ans = answers.get(code)
        if ans is None or not hasattr(ans, "noul"):
            continue
        prob = float(ans.noul)
        if prob >= settings.threshold_for(code):
            rule: Rule = REGISTRY[code]
            out.append(
                Finding(
                    code=code,
                    message=rule.summary.rstrip("."),
                    path=doc.path,
                    line=block.line,
                    col=block.col,
                    snippet=snippet or snippet_of(block.text),
                    label=block.label,
                    probability=prob,
                    severity=rule.severity,
                )
            )
    return out

