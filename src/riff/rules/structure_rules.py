"""Structure rules: the shape of a document (headings, lists, section and paragraph sizes).

Counting and hierarchy checks, so they live in code. Hierarchy norms (no skipped levels, no empty headings)
come from the Google and APA style guides; the size thresholds are calibrated on a human/AI corpus with
scripts/bench_structure.py.

Codes: RIF006-009 hard structural norms, CLR008-012 size and density statistics.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from riff.extract import Block, Document, Section
from riff.rules.base import Finding, finding, snippet_of, static_rule
from riff.textutil import split_sentences, word_count

if TYPE_CHECKING:
    from riff.settings import Settings

GOOGLE_HEADINGS = "Google developer documentation style guide: headings"
APA_HEADINGS = "APA Style: headings"
NO_DECKS = ("presentation",)
FORMAL_TYPES = ("documentation", "report", "memo", "academic_paper", "release_notes")


def _headings(doc: Document) -> list[Block]:
    return [b for b in doc.blocks if b.kind == "heading"] if doc.format != "pptx" else []


# ---------------------------------------------------------------- headings (RIF006, RIF007)


@static_rule("RIF006", "heading-hierarchy", "Heading levels skip, a section has one subsection, or h1 repeats",
             category="Structure", source=f"{GOOGLE_HEADINGS}; {APA_HEADINGS}", applies_to=FORMAL_TYPES,
             explanation="A heading level should not jump (h2 straight to h4), a section should not hold a single "
             "subsection, and a page has one h1. A style norm for docs and formal writing: 10 of 43 human technical "
             "blog posts break it, so it is gated to those types. Empty sections are not checked, because the "
             "extractor does not see code blocks or tables.",
             examples=("## Setup\n#### Details",), scope="document")
def heading_hierarchy(doc: Document, settings: Settings) -> list[Finding]:
    out = []
    heads = _headings(doc)
    previous: Block | None = None
    first_h1: Block | None = None
    for h in heads:
        if previous is not None and h.level > previous.level + 1:
            out.append(finding("RIF006", doc, h, f"h{h.level} follows h{previous.level}; do not skip levels",
                               snippet=snippet_of(h.text)))
        if h.level == 1:
            if first_h1 is not None:
                out.append(finding("RIF006", doc, h, "second h1; a page has one top-level heading",
                                   snippet=snippet_of(h.text)))
            first_h1 = first_h1 or h
        previous = h
    for section in doc.walk_sections():
        title = section.title
        if title is None or title.kind != "heading" or doc.format == "pptx":
            continue
        if len(section.children) == 1 and section.level > 1:
            out.append(finding("RIF006", doc, section.children[0].title,
                               f"only subsection under '{snippet_of(title.text)}'; add a sibling or fold it in",
                               snippet=snippet_of(section.children[0].title.text)))
    return out


_NUMBERED = re.compile(r"^\s*(?:step\s+)?\d+(?:\.\d+)*[.):]?\s+\S", re.I)
_LEADING_EMOJI = re.compile(r"^\s*[☀-➿\U0001f300-\U0001faff⭐⬆✅]")


@static_rule("RIF007", "heading-form", "Heading carries a number prefix, a link, or a leading emoji",
             category="Structure", source=f"{GOOGLE_HEADINGS}; Wikipedia, Signs of AI writing", skip_for=NO_DECKS,
             explanation="Google: do not number headings or put links in them. Wikipedia lists emoji at the start of "
             "headings as an AI tell.",
             examples=("## 1. Getting started", "## 🚀 Quick start"), scope="document")
def heading_form(doc: Document, settings: Settings) -> list[Finding]:
    out = []
    for h in _headings(doc):
        raw = h.raw_lines[0][1] if h.raw_lines else h.text
        if _NUMBERED.match(h.text):
            out.append(finding("RIF007", doc, h, "numbered heading", snippet=snippet_of(h.text)))
        elif _LEADING_EMOJI.match(h.text):
            out.append(finding("RIF007", doc, h, "emoji at the start of a heading", snippet=snippet_of(h.text)))
        elif "](" in raw:
            out.append(finding("RIF007", doc, h, "link inside a heading", snippet=snippet_of(h.text)))
    return out


# ---------------------------------------------------------------- changelog and lists (RIF008, RIF009)

_VERSION = re.compile(r"^\W*v?(\d+(?:\.\d+){1,3})\W*(?:[-–—:|]\s*(.+?))?\s*$", re.I)
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_GROUPS = {"added", "changed", "deprecated", "removed", "fixed", "security"}


def _heading_text(block: Block) -> str:
    raw = block.raw_lines[0][1] if block.raw_lines else block.text
    return raw.strip().lstrip("#").strip()


def _version_key(text: str) -> tuple[int, ...]:
    return tuple(int(p) for p in text.split("."))


@static_rule("RIF008", "changelog-shape", "Changelog departs from the Keep a Changelog layout",
             category="Structure", source="Keep a Changelog 1.1.0", applies_to=("release_notes",),
             explanation="Versions newest first, ISO 8601 dates, Unreleased at the top, changes grouped under Added, "
             "Changed, Deprecated, Removed, Fixed, Security, and no empty groups. Only checked when the document "
             "has two or more version headings.",
             examples=("## 1.0.0 - Jan 5, 2026",), scope="document")
def changelog_shape(doc: Document, settings: Settings) -> list[Finding]:
    releases: list[tuple[Section, tuple[int, ...] | None, str | None]] = []
    for section in doc.walk_sections():
        if section.title is None or section.title.kind != "heading":
            continue
        text = _heading_text(section.title)
        m = _VERSION.match(text)
        if m:
            releases.append((section, _version_key(m.group(1)), m.group(2)))
        elif "unreleased" in text.lower():
            releases.append((section, None, None))
    versions = [r for r in releases if r[1] is not None]
    if len(versions) < 2:
        return []
    out = []
    for i, (section, _, _) in enumerate(releases):
        if i > 0 and releases[i][1] is None:
            out.append(finding("RIF008", doc, section.title, "Unreleased belongs at the top",
                               snippet=snippet_of(section.title.text)))
    for (section, key, _date), (_, prev_key, _) in zip(versions[1:], versions, strict=False):
        if key > prev_key:
            out.append(finding("RIF008", doc, section.title, "versions should run newest first",
                               snippet=snippet_of(section.title.text)))
    for section, _, date in versions:
        if date and not _ISO_DATE.match(date.strip("() ")):
            out.append(finding("RIF008", doc, section.title, f"date '{date.strip()}' is not ISO 8601 (YYYY-MM-DD)",
                               snippet=snippet_of(section.title.text)))
    for section, _, _ in releases:
        for group in section.children:
            name = group.title.text.strip().lower()
            if name not in _GROUPS:
                out.append(finding("RIF008", doc, group.title,
                                   "group is not one of Added, Changed, Deprecated, Removed, Fixed, Security",
                                   snippet=snippet_of(group.title.text)))
            elif not group.blocks:
                out.append(finding("RIF008", doc, group.title, "empty group; omit it",
                                   snippet=snippet_of(group.title.text)))
    return out


@static_rule("RIF009", "single-item-list", "A list with one item",
             category="Structure", source="Google developer documentation style guide: lists",
             applies_to=("documentation", "release_notes", "product_description"),
             explanation="A list needs at least two items; one item is a sentence.",
             examples=("- Only item",), scope="document")
def single_item_list(doc: Document, settings: Settings) -> list[Finding]:
    out = []
    blocks = doc.blocks
    for i, b in enumerate(blocks):
        if b.kind != "list_item":
            continue
        before = blocks[i - 1].kind == "list_item" if i else False
        after = blocks[i + 1].kind == "list_item" if i + 1 < len(blocks) else False
        if not before and not after:
            out.append(finding("RIF009", doc, b, "list has a single item", snippet=snippet_of(b.text)))
    return out


# ---------------------------------------------------------------- size and density (CLR008-012)

_BOLD_SPAN = re.compile(r"(\*\*|__)(.+?)\1")

# Thresholds are set from the corpus benchmark (scripts/bench_structure.py); see the constants' comments.
_MIN_PEER_SECTIONS, _MIN_SECTION_CV, _MIN_STRUCTURE_WORDS = 4, 0.30, 500
_MAX_PARAGRAPH_SENTENCES = 8
_MAX_BOLD_SHARE = 0.30
_WALL_WORDS = 400
_MAX_SLIDE_WORDS, _MAX_SLIDE_BULLETS, _MIN_TITLE_WORDS, _MAX_TITLE_WORDS = 40, 5, 3, 20


def peer_sections(doc: Document) -> list[Section]:
    """Headed sections at the shallowest heading level that has enough of them to compare."""
    by_level: dict[int, list[Section]] = {}
    for s in doc.walk_sections():
        if s.title is not None and s.title.kind == "heading" and not s.is_divider:
            by_level.setdefault(s.level, []).append(s)
    for level in sorted(by_level):
        if len(by_level[level]) >= _MIN_PEER_SECTIONS:
            return by_level[level]
    return []


def section_words(section: Section) -> int:
    return sum(b.word_count for b in section.body if b.is_prose)


def _cv(values: list[int]) -> float:
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5 / mean


@static_rule("CLR008", "uniform-section-size", "Sections are all about the same length",
             category="Structure", source="Corpus calibration (human technical posts vs AI drafts)",
             default=False, skip_for=NO_DECKS + ("documentation", "release_notes", "resume", "poem", "script"),
             explanation="Human documents have a main section and a short one; generated drafts give every heading "
             "roughly equal weight. Flags a coefficient of variation of section length below 0.30 across 4+ "
             "sibling sections. Off by default: on 24 human and 16 AI documents the distributions overlap "
             "heavily (human 0.31-1.34, AI 0.22-0.77), so it is weak evidence.",
             examples=(), scope="document")
def uniform_section_size(doc: Document, settings: Settings) -> list[Finding]:
    peers = peer_sections(doc)
    sizes = [section_words(s) for s in peers]
    if len(peers) < _MIN_PEER_SECTIONS or sum(sizes) < _MIN_STRUCTURE_WORDS or min(sizes) == 0:
        return []
    cv = _cv(sizes)
    if cv >= _MIN_SECTION_CV:
        return []
    return [finding("CLR008", doc, peers[0].title,
                    f"{len(peers)} sections of {min(sizes)}-{max(sizes)} words (variation {cv:.2f}); "
                    "human documents are lopsided")]


@static_rule("CLR009", "paragraph-too-long", "Paragraph runs past the sentence limit",
             category="Structure", source="Google developer documentation style guide: paragraphs",
             default=False, skip_for=NO_DECKS + ("poem", "script", "resume", "academic_paper", "book_chapter"),
             explanation="Google: a paragraph longer than five or six sentences often tries to convey too much. "
             "Flags paragraphs over the limit (default 8). Off by default: 15 of 43 human posts trip it and no AI "
             "draft does, since AI paragraphs run short.",
             examples=(), scope="document")
def paragraph_too_long(doc: Document, settings: Settings) -> list[Finding]:
    out = []
    for b in doc.prose:
        if b.kind != "paragraph":
            continue
        n = len(split_sentences(b.text))
        if n > _MAX_PARAGRAPH_SENTENCES:
            out.append(finding("CLR009", doc, b, f"paragraph is {n} sentences (limit {_MAX_PARAGRAPH_SENTENCES})",
                               snippet=snippet_of(b.text)))
    return out


@static_rule("CLR010", "bold-density", "Too much of the prose is bold",
             category="Formatting", source="Nielsen Norman Group: formatting long-form content",
             skip_for=NO_DECKS,
             explanation="NN/g: bold or highlight should cover no more than about 30% of long-form text. Read from "
             "Markdown emphasis markers only.",
             examples=(), scope="document")
def bold_density(doc: Document, settings: Settings) -> list[Finding]:
    if doc.format != "md":
        return []
    bold = total = 0
    for b in doc.prose:
        raw = " ".join(line for _, line in b.raw_lines)
        bold += sum(word_count(m.group(2)) for m in _BOLD_SPAN.finditer(raw))
        total += b.word_count
    if total < _MIN_STRUCTURE_WORDS or bold / total <= _MAX_BOLD_SHARE:
        return []
    return [finding("CLR010", doc, doc.prose[0],
                    f"{bold / total:.0%} of the prose is bold (limit {_MAX_BOLD_SHARE:.0%})")]


@static_rule("CLR011", "wall-of-text", "A long document with no headings and no lists",
             category="Structure",
             source="Nielsen Norman Group: how users read on the web; Microsoft scannable content",
             applies_to=("documentation", "marketing_copy", "product_description"),
             explanation="Readers scan web and docs content; 400+ words with no heading or list gives them nothing to "
             "scan. Applies to documentation and promotional copy, not essays.",
             examples=(), scope="document")
def wall_of_text(doc: Document, settings: Settings) -> list[Finding]:
    if doc.word_count < _WALL_WORDS or any(b.kind in ("heading", "list_item") for b in doc.blocks):
        return []
    return [finding("CLR011", doc, doc.blocks[0], f"{doc.word_count} words with no heading or list to scan")]


@static_rule("CLR012", "slide-load", "A slide carries too many words or bullets, or its title is too short or long",
             category="Structure", source="Alley, The Craft of Scientific Presentations (assertion-evidence)",
             applies_to=NO_DECKS, default=False,
             explanation="Alley asks for a one- or two-line sentence headline (about 8-14 words) over visual "
             "evidence, not bullets. The word and bullet caps are uncalibrated, so the rule is off by default.",
             examples=(), scope="document")
def slide_load(doc: Document, settings: Settings) -> list[Finding]:
    out = []
    for s in doc.sections:
        if s.title is None:
            continue
        words = section_words(s)
        bullets = sum(1 for b in s.body if b.kind == "list_item")
        tw = word_count(s.title.text)
        if words > _MAX_SLIDE_WORDS:
            out.append(finding("CLR012", doc, s.title, f"{words} words on one slide (limit {_MAX_SLIDE_WORDS})"))
        elif bullets > _MAX_SLIDE_BULLETS:
            out.append(finding("CLR012", doc, s.title, f"{bullets} bullets on one slide (limit {_MAX_SLIDE_BULLETS})"))
        if tw and not _MIN_TITLE_WORDS <= tw <= _MAX_TITLE_WORDS:
            out.append(finding("CLR012", doc, s.title, f"slide title is {tw} words (aim for a one-line sentence)"))
    return out
