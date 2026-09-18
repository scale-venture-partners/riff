"""Drive a lint: classify the document, then run the selected static and Jev rules over it."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from riff.doctype import UNRESOLVED, DocTypeResult, classify_document, forced
from riff.extract import Document, extract
from riff.rules import load_rules
from riff.rules.base import REGISTRY, Finding, rule_applies
from riff.settings import Settings


@dataclass
class LintResult:
    document: Document
    findings: list[Finding]
    jev_stats: dict = field(default_factory=dict)
    doc_type: DocTypeResult = UNRESOLVED

    def sorted(self) -> list[Finding]:
        return sorted(self.findings, key=lambda f: f.sort_key())


def _resolve_doc_type(doc: Document, settings: Settings) -> DocTypeResult:
    if settings.forced_type:
        return forced(settings.forced_type)
    if settings.jev and settings.classify and doc.word_count > 0:
        return asyncio.run(classify_document(doc.text, doc.word_count, model=settings.model))
    return UNRESOLVED


def lint_document(doc: Document, settings: Settings, *, debug_jev: bool = False) -> LintResult:
    load_rules()
    doc_type = _resolve_doc_type(doc, settings)
    codes = [c for c in settings.active_codes() if rule_applies(REGISTRY[c], doc_type.type)]

    findings: list[Finding] = []
    for code in codes:
        rule = REGISTRY[code]
        if rule.kind == "static" and rule.check is not None:
            findings.extend(rule.check(doc, settings))

    jev_stats: dict = {}
    if settings.jev and any(REGISTRY[c].kind == "jev" for c in codes):
        from riff.jev import run_jev

        jev_findings, jev_stats = asyncio.run(run_jev(doc, codes, settings, debug=debug_jev))
        findings.extend(jev_findings)
    return LintResult(document=doc, findings=findings, jev_stats=jev_stats, doc_type=doc_type)


def lint_path(path: str, settings: Settings, *, debug_jev: bool = False) -> LintResult:
    return lint_document(extract(path), settings, debug_jev=debug_jev)
