"""User-defined rules from riff.toml: registration, both kinds, collisions, and offline phrase linting."""

from __future__ import annotations

import pytest

from riff.engine import lint_document
from riff.extract import extract_markdown
from riff.rules import load_rules
from riff.rules.base import REGISTRY, register_custom_rules
from riff.settings import Settings, load_settings

load_rules()


def test_phrase_custom_rule_fires_offline():
    register_custom_rules([{"code": "TST100", "name": "banned", "type": "phrase",
                            "summary": "banned word", "phrases": ["circle back", "synergy"]}])
    assert REGISTRY["TST100"].kind == "static"
    assert REGISTRY["TST100"].custom
    doc = extract_markdown("Let's circle back on the synergy next week.")
    codes = [f.code for f in lint_document(doc, Settings(jev=False, select=("TST100",))).findings]
    assert codes.count("TST100") == 2


def test_jev_custom_rule_registers_with_scope():
    register_custom_rules([{"code": "TST101", "name": "competitor", "type": "jev",
                            "summary": "names a competitor", "question": "Does this name a competitor?",
                            "scope": "document", "threshold": 0.55}])
    r = REGISTRY["TST101"]
    assert r.kind == "jev" and r.scope == "document" and r.threshold == 0.55 and r.custom


def test_collision_with_builtin_raises():
    with pytest.raises(ValueError, match="collides with a built-in"):
        register_custom_rules([{"code": "JEV001", "type": "jev", "question": "x?"}])


def test_reload_is_idempotent():
    spec = [{"code": "TST102", "type": "phrase", "phrases": ["foo"], "summary": "s"}]
    register_custom_rules(spec)
    register_custom_rules(spec)  # must not raise
    assert REGISTRY["TST102"].custom


def test_unknown_type_raises():
    with pytest.raises(ValueError, match="unknown type"):
        register_custom_rules([{"code": "TST103", "type": "regexp", "question": "x?"}])


def test_phrase_rule_needs_phrases():
    with pytest.raises(ValueError, match="non-empty 'phrases'"):
        register_custom_rules([{"code": "TST104", "type": "phrase", "summary": "s"}])


def test_custom_rules_load_from_toml(tmp_path):
    (tmp_path / "riff.toml").write_text(
        '[[custom_rules]]\ncode = "TST200"\ntype = "phrase"\nsummary = "no jargon"\nphrases = ["leverage"]\n'
    )
    settings = load_settings(start=tmp_path)
    assert "TST200" in REGISTRY
    assert "TST200" in settings.active_codes()


def test_jev_custom_rule_all_fields_from_spec():
    register_custom_rules([{"code": "TST300", "name": "n", "type": "jev", "summary": "sum here",
                            "question": "Does it?", "threshold": 0.42, "scope": "document",
                            "severity": "error"}])
    r = REGISTRY["TST300"]
    assert r.kind == "jev"
    assert r.name == "n"
    assert r.summary == "sum here"
    assert r.threshold == 0.42
    assert r.scope == "document"
    assert r.severity == "error"
    assert r.category == "Custom"
    assert r.source == "custom (riff.toml)"
    assert r.question == {"question": "Does it?"}
    assert r.custom is True


def test_jev_custom_rule_preserves_dict_question():
    register_custom_rules([{"code": "TST301", "type": "jev",
                            "question": {"question": "Q?", "not_for": "X"}}])
    assert REGISTRY["TST301"].question == {"question": "Q?", "not_for": "X"}


def test_jev_custom_rule_defaults():
    register_custom_rules([{"code": "TST302", "type": "jev", "question": "Q?"}])
    r = REGISTRY["TST302"]
    assert r.threshold == 0.6      # default threshold
    assert r.scope == "block"      # default scope
    assert r.severity == "warning"


def test_phrase_custom_rule_message_uses_summary():
    register_custom_rules([{"code": "TST303", "type": "phrase", "summary": "avoid this",
                            "phrases": ["circle back"]}])
    doc = extract_markdown("Let's circle back later.")
    findings = lint_document(doc, Settings(jev=False, select=("TST303",))).findings
    assert findings and "avoid this" in findings[0].message


def test_missing_code_raises():
    with pytest.raises(ValueError, match="missing a 'code'"):
        register_custom_rules([{"type": "jev", "question": "Q?"}])


def test_jev_custom_rule_needs_question():
    with pytest.raises(ValueError, match="needs a 'question'"):
        register_custom_rules([{"code": "TST304", "type": "jev"}])
def test_custom_rule_type_gating_fields():
    register_custom_rules([{"code": "TST400", "type": "jev", "question": "Q?",
                            "applies_to": ["memo", "report"], "skip_for": ["email"]}])
    r = REGISTRY["TST400"]
    assert r.applies_to == ("memo", "report")
    assert r.skip_for == ("email",)


# -- regex rules, case-sensitive phrases, and titles ------------------------------------------------

def _lint(md, *codes):
    return [f for f in lint_document(extract_markdown(md), Settings(jev=False, select=codes)).findings]


def test_regex_rule_flags_what_a_phrase_cannot():
    register_custom_rules([{"code": "TSTR00", "type": "regex", "summary": "Exclamation mark", "pattern": "!"}])
    (f,) = _lint("We shipped it! On time.", "TSTR00")
    assert f.message == "Exclamation mark ('!')"


def test_regex_rules_are_case_sensitive_unless_told():
    register_custom_rules([
        {"code": "TSTR01", "type": "regex", "summary": "Lowercase founders", "pattern": r"\bfounders?\b"},
        {"code": "TSTR02", "type": "regex", "summary": "Any founders", "pattern": r"\bfounders?\b", "ignore-case": True},
    ])
    text = "Founders build. Most founders ship."
    assert len(_lint(text, "TSTR01")) == 1 and len(_lint(text, "TSTR02")) == 2


def test_phrase_rules_can_be_case_sensitive():
    register_custom_rules([{"code": "TSTR03", "type": "phrase", "summary": "Write Founders", "phrases": ["founders"],
                            "case-sensitive": True}])
    assert [f.message for f in _lint("Founders and founders.", "TSTR03")] == ["Write Founders ('founders')"]


def test_offline_rules_read_titles_only_when_asked():
    register_custom_rules([
        {"code": "TSTR04", "type": "regex", "summary": "Bang", "pattern": "!"},
        {"code": "TSTR05", "type": "regex", "summary": "Bang anywhere", "pattern": "!", "blocks": "all"},
    ])
    md = "# Big news!\n\nA calm paragraph."
    assert _lint(md, "TSTR04") == [] and len(_lint(md, "TSTR05")) == 1


def test_bad_regex_rules_are_config_errors():
    with pytest.raises(ValueError, match="needs a 'pattern'"):
        register_custom_rules([{"code": "TSTR06", "type": "regex"}])
    with pytest.raises(ValueError, match="bad pattern"):
        register_custom_rules([{"code": "TSTR07", "type": "regex", "pattern": "("}])
    with pytest.raises(ValueError, match="blocks must be"):
        register_custom_rules([{"code": "TSTR08", "type": "regex", "pattern": "x", "blocks": "titles"}])
    with pytest.raises(ValueError, match="'jev', 'phrase' or 'regex'"):
        register_custom_rules([{"code": "TSTR09", "type": "glob"}])


def test_jev_custom_rules_take_any_level_and_a_view():
    register_custom_rules([
        {"code": "TSTR10", "type": "jev", "question": "q?", "scope": "paragraph", "fragments": True},
        {"code": "TSTR11", "type": "jev", "question": "q?", "scope": "document", "view": "outline"},
        {"code": "TSTR12", "type": "jev", "question": "q?", "scope": "title"},
    ])
    assert (REGISTRY["TSTR10"].scope, REGISTRY["TSTR10"].fragments) == ("block", True)
    assert (REGISTRY["TSTR11"].scope, REGISTRY["TSTR11"].view) == ("document", "outline")
    assert REGISTRY["TSTR12"].scope == "title"
    with pytest.raises(ValueError, match="unknown scope"):
        register_custom_rules([{"code": "TSTR13", "type": "jev", "question": "q?", "scope": "chapter"}])
