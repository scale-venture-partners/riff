"""Document-type gating: the pure rule_applies matrix, type validation, and result records."""

from __future__ import annotations

from dataclasses import replace

from riff.doctype import DOC_TYPES, TYPE_NAMES, UNRESOLVED, forced, is_valid_type
from riff.rules import load_rules
from riff.rules.base import REGISTRY, rule_applies

load_rules()


def _rule(**kw):
    base = REGISTRY["JEV001"]
    return replace(base, **kw)


def test_plain_rule_runs_for_any_type_and_unknown():
    r = _rule(applies_to=(), skip_for=())
    for t in ("email", "memo", "sms", None):
        assert rule_applies(r, t) is True


def test_skip_for_suppresses_only_listed_types():
    r = _rule(skip_for=("email", "letter"))
    assert rule_applies(r, "email") is False
    assert rule_applies(r, "letter") is False
    assert rule_applies(r, "memo") is True
    assert rule_applies(r, "sms") is True


def test_applies_to_restricts_to_listed_types():
    r = _rule(applies_to=("email",))
    assert rule_applies(r, "email") is True
    assert rule_applies(r, "memo") is False


def test_unknown_type_runs_everything_even_gated_rules():
    # No silent drop: an unresolved type runs applies_to and skip_for rules alike.
    assert rule_applies(_rule(applies_to=("email",)), None) is True
    assert rule_applies(_rule(skip_for=("email",)), None) is True


def test_skip_for_wins_over_applies_to():
    r = _rule(applies_to=("email", "memo"), skip_for=("memo",))
    assert rule_applies(r, "email") is True
    assert rule_applies(r, "memo") is False


def test_type_validation_and_names():
    assert is_valid_type("email")
    assert not is_valid_type("banana")
    assert "email" in TYPE_NAMES and "memo" in TYPE_NAMES
    assert set(TYPE_NAMES) == set(DOC_TYPES)


def test_doc_type_result_sources():
    assert UNRESOLVED.source == "unresolved" and UNRESOLVED.type is None
    f = forced("memo")
    assert f.type == "memo" and f.source == "forced" and f.confidence is None


def test_greeting_rule_is_type_gated():
    g = REGISTRY["JEV112"]
    assert g.skip_for == ("email", "letter")
    assert g.scope == "document"
    assert rule_applies(g, "email") is False
    assert rule_applies(g, "memo") is True


def test_report_shows_and_serializes_doc_type():
    import io
    import json

    from riff.doctype import DocTypeResult
    from riff.engine import LintResult
    from riff.extract import extract_markdown
    from riff.report import render_json, render_text

    doc = extract_markdown("Hi Sam, please ship it. Thanks, Alex.")
    forced_res = LintResult(document=doc, findings=[], jev_stats={}, doc_type=forced("memo"))
    buf = io.StringIO()
    render_text([forced_res], stream=buf)
    assert "type: memo (forced)" in buf.getvalue()

    classified = LintResult(document=doc, findings=[], jev_stats={},
                            doc_type=DocTypeResult(type="email", confidence=0.9, source="classified"))
    jbuf = io.StringIO()
    render_json([classified], stream=jbuf)
    payload = json.loads(jbuf.getvalue())
    assert payload[0]["doc_type"] == "email"
    assert payload[0]["doc_type_source"] == "classified"


def test_unresolved_type_not_printed():
    import io

    from riff.engine import LintResult
    from riff.extract import extract_markdown
    from riff.report import render_text

    doc = extract_markdown("Plain body text here.")
    buf = io.StringIO()
    render_text([LintResult(document=doc, findings=[])], stream=buf)  # default UNRESOLVED
    assert "type:" not in buf.getvalue()
