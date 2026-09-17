"""Drive a lint: run the selected static rules and (optionally) the Jev rules over one document."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from riff.extract import Document, extract
from riff.rules import load_rules
from riff.rules.base import REGISTRY, Finding
from riff.settings import Settings


@dataclass
class LintResult:
    document: Document
    findings: list[Finding]
    jev_stats: dict = field(default_factory=dict)

    def sorted(self) -> list[Finding]:
        return sorted(self.findings, key=lambda f: f.sort_key())


def lint_document(doc: Document, settings: Settings, *, debug_jev: bool = False) -> LintResult:
    load_rules()
    codes = settings.active_codes()
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
    return LintResult(document=doc, findings=findings, jev_stats=jev_stats)


def lint_path(path: str, settings: Settings, *, debug_jev: bool = False) -> LintResult:
    return lint_document(extract(path), settings, debug_jev=debug_jev)
