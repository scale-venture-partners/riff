"""Rule and Finding models plus the global registry and static-rule helpers."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from riff.extract import Block, Document
from riff.textutil import split_sentences

if TYPE_CHECKING:
    from riff.settings import Settings

Kind = Literal["static", "jev"]
Scope = Literal["block", "document"]
Severity = Literal["error", "warning", "info"]

Checker = Callable[[Document, "Settings"], "list[Finding]"]


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    path: str
    line: int
    col: int
    snippet: str = ""
    label: str = ""
    probability: float | None = None
    severity: str = "warning"

    def sort_key(self) -> tuple:
        return (self.path, self.line, self.col, self.code)


@dataclass(frozen=True)
class Rule:
    code: str
    name: str
    summary: str
    category: str
    source: str
    kind: Kind
    scope: Scope = "block"
    explanation: str = ""
    examples: tuple[str, ...] = ()
    default: bool = True
    severity: Severity = "warning"
    # Jev rules: Noul instructions sent per block. Phrased so a high probability means the tell IS present.
    question: Mapping[str, Any] | None = None
    threshold: float = 0.6
    # Static rules: a checker over a Document and the active Settings.
    check: Checker | None = field(default=None, compare=False)
    # True for rules declared by a user in riff.toml, not shipped with riff.
    custom: bool = False

    @property
    def prefix(self) -> str:
        return re.match(r"[A-Z]+", self.code).group(0)


REGISTRY: dict[str, Rule] = {}


def register(rule: Rule) -> Rule:
    if rule.code in REGISTRY:
        raise ValueError(f"duplicate rule code {rule.code}")
    REGISTRY[rule.code] = rule
    return rule


def register_custom_rules(specs: list[Mapping[str, Any]]) -> list[str]:
    """Register user-defined rules from riff.toml [[custom_rules]]. Idempotent per code.

    Two kinds:
      type = "jev"     -> a Noul question (needs an API key at run time), with optional scope/threshold.
      type = "phrase"  -> literal phrases flagged offline, no key needed.
    A custom code must not collide with a built-in one.
    """
    added = []
    for spec in specs:
        code = str(spec.get("code", "")).strip()
        if not code:
            raise ValueError("custom rule is missing a 'code'")
        existing = REGISTRY.get(code)
        if existing is not None:
            if existing.custom:
                added.append(code)  # already registered from an earlier load; leave it
                continue
            raise ValueError(f"custom rule {code} collides with a built-in rule; choose another code")
        kind = str(spec.get("type", "jev")).lower()
        name = str(spec.get("name", code))
        summary = str(spec.get("summary", name))
        severity = str(spec.get("severity", "warning"))
        if kind == "phrase":
            phrases = spec.get("phrases") or []
            if not phrases:
                raise ValueError(f"custom phrase rule {code} needs a non-empty 'phrases' list")
            rule = Rule(
                code=code, name=name, summary=summary, category="Custom", source="custom (riff.toml)",
                kind="static", severity=severity, custom=True,
                check=phrase_check(code, phrase_pattern([str(p) for p in phrases]), summary + " ('{match}')"),
            )
        elif kind == "jev":
            question = spec.get("question")
            if not question:
                raise ValueError(f"custom jev rule {code} needs a 'question'")
            scope = str(spec.get("scope", "block"))
            rule = Rule(
                code=code, name=name, summary=summary, category="Custom", source="custom (riff.toml)",
                kind="jev", scope=scope, severity=severity, custom=True,
                question={"question": str(question)} if isinstance(question, str) else question,
                threshold=float(spec.get("threshold", 0.6)),
            )
        else:
            raise ValueError(f"custom rule {code}: unknown type {kind!r} (use 'jev' or 'phrase')")
        register(rule)
        added.append(code)
    return added


def jev_rule(
    code: str,
    name: str,
    summary: str,
    *,
    category: str,
    source: str,
    question: Mapping[str, Any],
    explanation: str = "",
    examples: tuple[str, ...] = (),
    scope: Scope = "block",
    default: bool = True,
    severity: Severity = "warning",
    threshold: float = 0.6,
) -> Rule:
    return register(
        Rule(
            code=code,
            name=name,
            summary=summary,
            category=category,
            source=source,
            kind="jev",
            scope=scope,
            explanation=explanation,
            examples=examples,
            default=default,
            severity=severity,
            question=question,
            threshold=threshold,
        )
    )


def static_rule(
    code: str,
    name: str,
    summary: str,
    *,
    category: str,
    source: str,
    explanation: str = "",
    examples: tuple[str, ...] = (),
    scope: Scope = "block",
    default: bool = True,
    severity: Severity = "warning",
) -> Callable[[Checker], Rule]:
    def deco(fn: Checker) -> Rule:
        return register(
            Rule(
                code=code,
                name=name,
                summary=summary,
                category=category,
                source=source,
                kind="static",
                scope=scope,
                explanation=explanation,
                examples=examples,
                default=default,
                severity=severity,
                check=fn,
            )
        )

    return deco


# ---------------------------------------------------------------- helpers for static checks


def snippet_of(text: str, start: int = 0, width: int = 90) -> str:
    s = text[max(0, start - 30) :].strip()
    if start > 30:
        s = "…" + s
    s = re.sub(r"\s+", " ", s)
    return s if len(s) <= width else s[: width - 1].rstrip() + "…"


def finding(rule_code: str, doc: Document, block: Block, message: str, *, line: int | None = None,
            col: int | None = None, snippet: str = "", probability: float | None = None) -> Finding:
    rule = REGISTRY[rule_code]
    return Finding(
        code=rule_code,
        message=message,
        path=doc.path,
        line=block.line if line is None else line,
        col=block.col if col is None else col,
        snippet=snippet or snippet_of(block.text),
        label=block.label,
        probability=probability,
        severity=rule.severity,
    )


def _joined(block: Block) -> tuple[str, list[tuple[int, int, int]]]:
    """Join a block's raw lines with newlines, plus an index of (abs_offset, line_no, indent) per line.

    Phrase patterns use `\\s+` between words, which matches across the newline, so a phrase
    hard-wrapped over two source lines is still found and still reports the line where it starts.
    """
    if not block.raw_lines:
        return block.text, [(0, block.line, 0)]
    parts, index, offset = [], [], 0
    for line_no, raw in block.raw_lines:
        index.append((offset, line_no or block.line, len(raw) - len(raw.lstrip())))
        parts.append(raw)
        offset += len(raw) + 1
    return "\n".join(parts), index


def _locate(index: list[tuple[int, int, int]], pos: int) -> tuple[int, int]:
    line_no, base = index[0][1], index[0][0]
    for off, ln, _ in index:
        if off > pos:
            break
        line_no, base = ln, off
    return line_no, pos - base + 1


def regex_matches(block: Block, pattern: re.Pattern[str]) -> Iterable[tuple[re.Match[str], int, int]]:
    """Yield (match, line, col) over the block's full text, mapping offsets back to source lines."""
    text, index = _joined(block)
    for m in pattern.finditer(text):
        line, col = _locate(index, m.start())
        yield m, line, col


def phrase_pattern(phrases: Iterable[str]) -> re.Pattern[str]:
    """Case-insensitive alternation; internal whitespace matches across wraps, apostrophes match either glyph."""
    alts = []
    for p in sorted(set(phrases), key=len, reverse=True):
        tokens = [re.escape(tok).replace("'", "['’]") for tok in p.split()]
        alts.append(r"\s+".join(tokens))
    return re.compile(r"(?<![\w-])(?:" + "|".join(alts) + r")(?![\w-])", re.IGNORECASE)


def phrase_check(code: str, pattern: re.Pattern[str], message: str, *, kinds: frozenset[str] | None = None,
                 replacements: Mapping[str, str] | None = None) -> Checker:
    """Flag every occurrence of a phrase pattern in prose (and optionally other) blocks."""

    def check(doc: Document, settings: Settings) -> list[Finding]:
        out = []
        for block in doc.blocks:
            if kinds is None and not block.is_prose:
                continue
            if kinds is not None and block.kind not in kinds:
                continue
            for m, line, col in regex_matches(block, pattern):
                hit = m.group(0)
                msg = message.format(match=re.sub(r"\s+", " ", hit))
                if replacements:
                    key = re.sub(r"\s+", " ", hit.lower())
                    if key in replacements and replacements[key]:
                        msg = f"{msg}; try '{replacements[key]}'"
                out.append(finding(code, doc, block, msg, line=line, col=col, snippet=snippet_of(m.string, m.start())))
        return out

    return check


def sentence_check(code: str, predicate: Callable[[str], str | None]) -> Checker:
    """Run `predicate(sentence) -> message | None` over every sentence of every prose block."""

    def check(doc: Document, settings: Settings) -> list[Finding]:
        out = []
        for block in doc.prose:
            for s in split_sentences(block.text):
                msg = predicate(s.text)
                if msg:
                    out.append(finding(code, doc, block, msg, snippet=snippet_of(s.text)))
        return out

    return check
