"""Whole-document type classification.

Before the rules run, riff can classify what kind of document it is looking at (email, memo,
essay, ...) with one Jev Choice question over the whole text. Rules then opt in or out of types
(see Rule.applies_to / Rule.skip_for): a greeting is normal in an email but a tell in a memo.

The user can force the type with --type, which skips this call entirely and works without a key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# The type vocabulary. Keys are the stable identifiers used in rule `applies_to` / `skip_for`
# and in `--type`; values are the descriptions sent to the model.
DOC_TYPES: dict[str, object] = {
    "sms": "A text message, SMS, or instant/chat message: short and informal, to a person.",
    "email": {"what": "An email to one or more recipients, usually with a greeting and a sign-off."},
    "chat_message": "A message in a team chat tool (Slack, Teams, Discord): informal, conversational.",
    "memo": {"what": "An internal memo or briefing: informational, often with a subject line",
             "not_for": "A personal email addressed to someone with a greeting"},
    "letter": "A formal letter with an address, a salutation, and a formal closing.",
    "essay": {"what": "A structured argumentative or reflective piece that makes a case in prose",
              "not_for": "A short social post or status update"},
    "blog_post": "An informal-to-semiformal post with a title and sections for a public audience.",
    "article": "A news, magazine, or feature article reporting or explaining a subject.",
    "report": "A formal report or analysis with sections, findings, and recommendations.",
    "academic_paper": "A scholarly or research paper with formal structure and citations.",
    "book_chapter": "A chapter or excerpt from a book: long-form narrative or exposition.",
    "documentation": "Technical documentation, a README, a guide, or reference material.",
    "release_notes": "Release notes or a changelog listing changes between versions.",
    "marketing_copy": "Promotional or marketing copy that sells a product, service, or idea.",
    "social_post": {"what": "A standalone social media post (LinkedIn, X): self-contained and public",
                    "not_for": "An excerpt or paragraph taken from a longer piece such as an essay"},
    "product_description": "A product listing or description.",
    "review": "A review of a product, place, service, or work.",
    "press_release": "A press release announcing news in a formal, third-person style.",
    "resume": "A resume or CV listing experience, skills, and education.",
    "script": "A script or screenplay with dialogue and stage or scene directions.",
    "poem": "A poem or verse.",
    "notes": "Rough notes, an outline, or a bulleted list rather than finished prose.",
    "other": "None of the above kinds fit.",
}

TYPE_NAMES: tuple[str, ...] = tuple(DOC_TYPES)


@dataclass(frozen=True)
class DocTypeResult:
    type: str | None            # None means unresolved (no classification and no forced type)
    confidence: float | None
    source: str                 # "forced", "classified", or "unresolved"


UNRESOLVED = DocTypeResult(type=None, confidence=None, source="unresolved")


def forced(type_name: str) -> DocTypeResult:
    return DocTypeResult(type=type_name, confidence=None, source="forced")


def is_valid_type(name: str) -> bool:
    return name in DOC_TYPES


async def classify_document(text: str, word_count: int, *, model: str = "jev-latest") -> DocTypeResult:
    """Classify the whole document with one Jev Choice call. Requires TYPESAFE_API_KEY.

    Returns the top choice and its confidence. Confidence is recorded, not gated on: in practice
    it does not separate right from wrong classifications, so the escape hatch is --type, not a threshold.
    """
    if not os.environ.get("TYPESAFE_API_KEY"):
        return UNRESOLVED
    from typesafe_sdk import AsyncTypeSafeClient, Choice, RetryPolicy, TypeSafeError

    question = Choice(
        instructions={
            "question": "What kind of document or message is this whole piece?",
            "note": "`word_count` is provided; a very short piece is not automatically a social post or note.",
        },
        criteria=DOC_TYPES,
    )
    try:
        async with AsyncTypeSafeClient(model=model, timeout=60.0, retry=RetryPolicy(max_retries=3, timeout=90.0)) as c:
            resp = await c.system_one({"word_count": word_count, "text": text}, {"type": question})
    except TypeSafeError:
        return UNRESOLVED
    ans = resp.answers.get("type")
    if ans is None or not hasattr(ans, "choice"):
        return UNRESOLVED
    return DocTypeResult(type=ans.choice, confidence=float(ans.confidence), source="classified")
