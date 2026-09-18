"""Render lint results as human text or JSON."""

from __future__ import annotations

import json
import sys

from riff.engine import LintResult
from riff.rules.base import Finding

_COLOR = {"error": "\033[31m", "warning": "\033[33m", "info": "\033[36m"}
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _use_color(stream) -> bool:
    return stream.isatty() and "NO_COLOR" not in __import__("os").environ


def _fmt_location(f: Finding) -> str:
    return f"{f.label}" if f.label else f"{f.line}:{f.col}"


def _doc_type_line(result: LintResult, color: bool) -> str:
    dt = result.doc_type
    if dt.source == "forced":
        body = f"type: {dt.type} (forced)"
    elif dt.source == "classified" and dt.type:
        body = f"type: {dt.type} ({dt.confidence:.2f})"
    else:
        body = "type: unresolved (type-specific rules run everywhere)"
    return f"{_DIM if color else ''}{result.document.path}: {body}{_RESET if color else ''}"


def render_text(results: list[LintResult], stream=None, summary: bool = True) -> None:
    stream = stream or sys.stdout
    color = _use_color(stream)
    total = 0
    for result in results:
        if result.doc_type.source != "unresolved":
            print(_doc_type_line(result, color), file=stream)
        findings = result.sorted()
        total += len(findings)
        for f in findings:
            loc = _fmt_location(f)
            prob = f" p={f.probability:.2f}" if f.probability is not None else ""
            if color:
                sev = f"{_COLOR.get(f.severity, '')}{f.code}{_RESET}"
                head = f"{_BOLD}{f.path}{_RESET}:{loc}: {sev} {f.message}{_DIM}{prob}{_RESET}"
            else:
                head = f"{f.path}:{loc}: {f.code} {f.message}{prob}"
            print(head, file=stream)
            if f.snippet:
                print(f"    {_DIM if color else ''}{f.snippet}{_RESET if color else ''}", file=stream)
    if summary:
        _summary(results, total, stream, color)


def _summary(results: list[LintResult], total: int, stream, color: bool) -> None:
    files = len(results)
    errors = sum(r.jev_stats.get("errors", 0) for r in results if r.jev_stats)
    if total == 0:
        # Don't claim success when the lint was incomplete: an all-errored Jev run has zero findings.
        if errors:
            warn = f"No findings, but {errors} Jev request(s) failed, so this lint is incomplete."
            print(f"\n{_COLOR['error'] if color else ''}{warn}{_RESET if color else ''}", file=stream)
        else:
            msg = f"All checks passed on {files} file{'s' * (files != 1)}."
            print(f"\n{_COLOR['info'] if color else ''}{msg}{_RESET if color else ''}", file=stream)
        _jev_note(results, stream, color)
        return
    by_code: dict[str, int] = {}
    for r in results:
        for f in r.findings:
            by_code[f.code] = by_code.get(f.code, 0) + 1
    top = ", ".join(f"{c} ×{n}" for c, n in sorted(by_code.items(), key=lambda kv: -kv[1])[:6])
    bold = _BOLD if color else ""
    reset = _RESET if color else ""
    plural_f = "s" * (total != 1)
    plural_files = "s" * (files != 1)
    print(f"\n{bold}{total} finding{plural_f} in {files} file{plural_files}{reset} ({top}).", file=stream)
    _jev_note(results, stream, color)


def _jev_note(results: list[LintResult], stream, color: bool) -> None:
    stats = [r.jev_stats for r in results if r.jev_stats]
    if not stats:
        return
    calls = sum(s.get("calls", 0) for s in stats)
    toks = sum(s.get("input_tokens", 0) for s in stats)
    skipped = sum(s.get("skipped", 0) for s in stats)
    errors = sum(s.get("errors", 0) for s in stats)
    note = f"Jev: {calls} calls, {toks:,} input tokens (~${toks * 0.042 / 1e6:.4f})"
    if skipped:
        note += f", {skipped} block(s) skipped as too long"
    print(f"{_DIM if color else ''}{note}{_RESET if color else ''}", file=stream)
    if errors:
        warn = f"WARNING: {errors} Jev request(s) failed; this lint is incomplete."
        print(f"{_COLOR['error'] if color else ''}{warn}{_RESET if color else ''}", file=stream)


def render_json(results: list[LintResult], stream=None) -> None:
    stream = stream or sys.stdout
    payload = [
        {
            "path": r.document.path,
            "format": r.document.format,
            "doc_type": r.doc_type.type,
            "doc_type_confidence": r.doc_type.confidence,
            "doc_type_source": r.doc_type.source,
            "findings": [
                {
                    "code": f.code,
                    "message": f.message,
                    "line": f.line,
                    "col": f.col,
                    "label": f.label,
                    "severity": f.severity,
                    "probability": f.probability,
                    "snippet": f.snippet,
                }
                for f in r.sorted()
            ],
            "jev_stats": r.jev_stats,
        }
        for r in results
    ]
    json.dump(payload, stream, indent=2)
    stream.write("\n")
