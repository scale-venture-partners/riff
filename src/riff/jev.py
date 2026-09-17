"""The Jev backend: turn selected semantic rules into one Noul call per prose block.

One call per block keeps localization exact (each finding has a real line) and Jev input is cheap.
The question text for the selected rules is identical on every call; a block's own text is the state.
Blocks whose token estimate would exceed Jev's per-request state budget are skipped with a note.
"""

from __future__ import annotations

import asyncio
import os

from riff.extract import Block, Document
from riff.rules.base import REGISTRY, Finding, Rule, snippet_of
from riff.settings import Settings
from riff.textutil import estimate_tokens

# Jev's documented budget is 32k tokens for state + longest question; stay well under with headroom for questions.
_MAX_STATE_TOKENS = 24_000
_MIN_WORDS = 8


def _is_link_list(text: str) -> bool:
    """A run of '·'-separated links or a citation dump is not prose; don't ask prose questions about it."""
    return text.count("·") >= 2 or text.count("](http") >= 2


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


async def run_jev(doc: Document, codes: list[str], settings: Settings, *, debug: bool = False) -> tuple[list[Finding], dict]:
    """Return (findings, stats). Raises JevUnavailable if the key is missing.

    Per-block API failures are counted in stats["errors"], never disguised as findings; the caller
    turns a nonzero count into a loud, non-zero exit. With debug=True, stats["probabilities"] holds
    every (line, code, probability) so a user tuning thresholds can see the full distribution.
    """
    from riff.rules import load_rules

    load_rules()
    jev_codes = [c for c in codes if REGISTRY[c].kind == "jev"]
    if not jev_codes:
        return [], {"blocks": 0, "calls": 0, "input_tokens": 0, "skipped": 0}
    _require_key()

    from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy, TypeSafeError

    block_codes = [c for c in jev_codes if REGISTRY[c].scope == "block"]
    doc_codes = [c for c in jev_codes if REGISTRY[c].scope == "document"]
    block_questions = build_questions(block_codes)
    targets = [b for b in doc.prose if b.word_count >= _MIN_WORDS and not _is_link_list(b.text)]
    stats = {"blocks": len(targets), "calls": 0, "input_tokens": 0, "skipped": 0, "errors": 0,
             "error_detail": [], "probabilities": []}
    findings: list[Finding] = []
    sem = asyncio.Semaphore(settings.jev_concurrency)

    async with AsyncTypeSafeClient(model=settings.model, timeout=60.0,
                                   retry=RetryPolicy(max_retries=3, timeout=90.0)) as client:

        async def one(block: Block) -> list[Finding]:
            if estimate_tokens(block.text) > _MAX_STATE_TOKENS:
                stats["skipped"] += 1
                return []
            async with sem:
                try:
                    resp = await client.system_one(block.text, block_questions)
                except TypeSafeError as exc:
                    stats["errors"] += 1
                    stats["error_detail"].append(f"{block.location()}: {type(exc).__name__}: {exc}")
                    return []
            stats["calls"] += 1
            stats["input_tokens"] += resp.usage.input_tokens
            if debug:
                for c in block_codes:
                    a = resp.answers.get(c)
                    if a is not None and hasattr(a, "noul"):
                        stats["probabilities"].append((block.line, c, round(float(a.noul), 3)))
            return _findings_for_block(doc, block, resp, block_codes, settings)

        tasks = [one(b) for b in targets]
        if doc_codes:
            tasks.append(_run_document_scope(client, doc, doc_codes, settings, stats, debug))
        for result in await asyncio.gather(*tasks):
            findings.extend(result)
    return findings, stats


async def _run_document_scope(client, doc: Document, codes: list[str], settings: Settings,
                              stats: dict, debug: bool) -> list[Finding]:
    """Ask document-scope rules once over the whole prose, anchoring findings at the first block."""
    from typesafe_sdk import TypeSafeError

    prose = [b for b in doc.prose if not _is_link_list(b.text)]
    text = "\n\n".join(b.text for b in prose).strip()
    anchor = prose[0] if prose else (doc.blocks[0] if doc.blocks else None)
    if not text or anchor is None or estimate_tokens(text) > _MAX_STATE_TOKENS:
        stats["skipped"] += 1
        return []
    try:
        resp = await client.system_one(text, build_questions(codes))
    except TypeSafeError as exc:
        stats["errors"] += 1
        stats["error_detail"].append(f"document: {type(exc).__name__}: {exc}")
        return []
    stats["calls"] += 1
    stats["input_tokens"] += resp.usage.input_tokens
    if debug:
        for c in codes:
            a = resp.answers.get(c)
            if a is not None and hasattr(a, "noul"):
                stats["probabilities"].append((anchor.line, c, round(float(a.noul), 3)))
    return _findings_for_block(doc, anchor, resp, codes, settings)


def _findings_for_block(doc: Document, block: Block, resp, codes: list[str], settings: Settings) -> list[Finding]:
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
                    snippet=snippet_of(block.text),
                    label=block.label,
                    probability=prob,
                    severity=rule.severity,
                )
            )
    return out

