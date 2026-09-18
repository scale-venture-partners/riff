"""Reporter output: text (plain), summary, and JSON shapes."""

from __future__ import annotations

import io
import json

from riff.engine import lint_document
from riff.extract import extract_markdown
from riff.report import render_json, render_text
from riff.rules import load_rules
from riff.settings import Settings

load_rules()


def _result():
    doc = extract_markdown("# Understanding The Impact Of Modern Systems\n\nThe flow is input → output.\n")
    return lint_document(doc, Settings(jev=False))


def test_render_text_plain_and_summary(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    buf = io.StringIO()
    render_text([_result()], stream=buf)
    out = buf.getvalue()
    assert "RIF002" in out
    assert "finding" in out.lower()


def test_render_text_quiet_omits_summary(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    buf = io.StringIO()
    render_text([_result()], stream=buf, summary=False)
    out = buf.getvalue()
    assert "RIF002" in out
    assert "finding" not in out.lower().split("rif002")[-1] or "findings in" not in out


def test_render_json_shape():
    buf = io.StringIO()
    render_json([_result()], stream=buf)
    payload = json.loads(buf.getvalue())
    assert payload[0]["format"] == "md"
    assert any(f["code"] == "RIF002" for f in payload[0]["findings"])


def test_render_text_all_clean(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    doc = extract_markdown("The service reads config at startup and exits on a missing variable.")
    buf = io.StringIO()
    render_text([lint_document(doc, Settings(jev=False))], stream=buf)
    assert "All checks passed" in buf.getvalue()


class _FakeTTY(io.StringIO):
    def isatty(self):
        return True


def test_render_text_color_path(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    buf = _FakeTTY()
    render_text([_result()], stream=buf)
    assert "\033[" in buf.getvalue()  # ANSI codes emitted


def test_render_text_jev_stats_and_errors(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    from riff.engine import LintResult

    doc = extract_markdown("Body paragraph here for context.")
    res = LintResult(document=doc, findings=[], jev_stats={"calls": 3, "input_tokens": 12000,
                                                           "skipped": 1, "errors": 2})
    buf = io.StringIO()
    render_text([res], stream=buf)
    out = buf.getvalue()
    assert "Jev: 3 calls" in out
    assert "skipped" in out
    assert "WARNING" in out and "incomplete" in out
