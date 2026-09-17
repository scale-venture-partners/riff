"""Static rules — the residue that Jev genuinely cannot do.

Everything judgment-based lives in jev_rules.py. What stays here is only:
  - exact glyphs Jev never sees, because it is handed normalized text (curly quotes, arrows);
  - structural facts that live in markup, not prose (bold-first bullets);
  - capitalization, an exact character property (Title Case headings);
  - cross-block comparison Jev cannot do in a per-block question (duplicate paragraphs);
  - arithmetic Jev is documented not to do reliably (sentence length, reading grade).

These are exact or numeric, not fragile pattern-matching, so regex/parsing is the right tool.

Codes: RIF0xx typography/structure, CLR0xx clarity metrics.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from riff.extract import Document
from riff.rules.base import Finding, finding, regex_matches, snippet_of, static_rule
from riff.textutil import split_sentences, word_count, words

if TYPE_CHECKING:
    from riff.settings import Settings

TROPES = "tropes.fyi"
WILLIAMS = "Williams, Style: Lessons in Clarity and Grace"

# ---------------------------------------------------------------- typography / structure (RIF0xx)

# Arrows and smart quotes only; dashes are excluded because a dash's meaning (range vs dramatic pause)
# is a judgment, which belongs to Jev.
_DECORATIVE = re.compile(r"[‘’“”→←⇒⇨➡]")
_GLYPH_NAME = {
    "‘": "‘ curly quote", "’": "’ curly quote", "“": "“ curly quote", "”": "” curly quote",
    "→": "→ arrow", "←": "← arrow", "⇒": "⇒ arrow", "⇨": "⇨ arrow", "➡": "➡ arrow",
}


@static_rule("RIF001", "decorative-unicode", "Curly quotes or arrows (glyphs Jev can't see)",
             category="Formatting", source=TROPES,
             explanation="Typing in a plain editor produces straight quotes and ASCII arrows. Curly quotes and → are a tell. "
             "This is an exact glyph check because the model is given normalized text and never sees the character.",
             examples=("Input → Processing → Output", "“smart quotes”"))
def decorative_unicode(doc: Document, settings: Settings) -> list[Finding]:
    out = []
    for block in doc.prose + doc.headings:
        for m, line, col in regex_matches(block, _DECORATIVE):
            out.append(finding("RIF001", doc, block, f"decorative unicode ({_GLYPH_NAME.get(m.group(0), m.group(0))})",
                               line=line, col=col, snippet=snippet_of(m.string, m.start())))
    return out


@static_rule("RIF002", "title-case-heading", "Heading capitalizes every word",
             category="Formatting", source=TROPES,
             explanation="Capitalize only the first word and proper nouns. Title Case On Every Word is an AI tell. "
             "Capitalization is an exact character property, so it stays a code check.",
             examples=("Understanding The Impact Of Modern Technology",), scope="document")
def title_case(doc: Document, settings: Settings) -> list[Finding]:
    minor = {"a", "an", "the", "and", "or", "but", "for", "nor", "of", "to", "in", "on", "at", "by",
             "vs", "via", "with", "as", "is"}
    out = []
    for h in doc.headings:
        toks = words(h.text)
        lowerable = [t for t in toks if t.lower() not in minor and not t.isupper()]
        if len(toks) >= 4 and len(lowerable) >= 3 and all(t[:1].isupper() for t in lowerable):
            out.append(finding("RIF002", doc, h, "heading is Title Case; use sentence case"))
    return out


@static_rule("RIF003", "bold-first-bullets", "Most list items open with a bold lead-in",
             category="Formatting", source=TROPES,
             explanation="Bolding the first phrase of every bullet is a hallmark of AI docs. It lives in markup, "
             "which the model does not see, so it stays a structural check.",
             examples=("**Security**: environment-based config",), scope="document")
def bold_bullets(doc: Document, settings: Settings) -> list[Finding]:
    items = [b for b in doc.blocks if b.kind == "list_item"]
    bold = [b for b in items if b.bold_lead]
    if len(items) >= 3 and len(bold) / len(items) >= 0.6:
        return [finding("RIF003", doc, b, f"bold lead-in on {len(bold)}/{len(items)} list items") for b in bold]
    return []


# ---------------------------------------------------------------- clarity metrics (CLR0xx)


@static_rule("CLR001", "long-sentence", "Sentence longer than the configured word limit",
             category="Clarity", source=WILLIAMS,
             explanation="Williams, Lesson 9: long sentences lose the reader. Default limit 45 words (max_sentence_words). "
             "This is arithmetic, which the model does not do reliably, so it stays in code.",
             examples=(), scope="document")
def long_sentence(doc: Document, settings: Settings) -> list[Finding]:
    limit = settings.max_sentence_words
    out = []
    for block in doc.prose:
        # Skip citation/link dumps: a run of '·'-separated links is not a sentence.
        if block.text.count("·") >= 2 or block.text.count("](http") >= 2:
            continue
        for s in split_sentences(block.text):
            n = word_count(s.text)
            if n > limit:
                out.append(finding("CLR001", doc, block, f"sentence is {n} words (limit {limit})", snippet=snippet_of(s.text)))
    return out


@static_rule("CLR002", "hard-to-read", "Paragraph reading grade above the configured level",
             category="Clarity", source=WILLIAMS, default=False,
             explanation="Flesch–Kincaid grade over the limit (default 14, max_reading_grade). Arithmetic, so it stays in code.",
             examples=(), scope="document")
def hard_to_read(doc: Document, settings: Settings) -> list[Finding]:
    from riff.textutil import flesch_kincaid_grade

    limit = settings.max_reading_grade
    out = []
    for block in doc.prose:
        if block.word_count < 40 or block.text.count("·") >= 2:
            continue
        grade = flesch_kincaid_grade(block.text)
        if grade is not None and grade > limit:
            out.append(finding("CLR002", doc, block, f"reading grade {grade:.0f} (limit {limit:.0f})"))
    return out


@static_rule("CLR003", "duplicate-paragraph", "Paragraph repeated near-verbatim elsewhere",
             category="Composition", source=TROPES,
             explanation="Repeating whole paragraphs is a giveaway of unedited output. It needs comparison across the "
             "whole document, which a per-block model question cannot do, so it stays in code.",
             examples=(), scope="document")
def duplicate_paragraph(doc: Document, settings: Settings) -> list[Finding]:
    seen: dict[str, object] = {}
    out = []
    for block in doc.prose:
        if block.word_count < 8:
            continue
        key = " ".join(w.lower() for w in words(block.text))
        if key in seen:
            out.append(finding("CLR003", doc, block, f"duplicates the paragraph at {seen[key].location()}"))
        else:
            seen[key] = block
    return out
