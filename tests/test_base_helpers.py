"""Unit tests for rule-registry helpers: register, phrase_pattern, sentence_check."""

from __future__ import annotations

import pytest

from riff.extract import extract_markdown
from riff.rules import load_rules
from riff.rules.base import REGISTRY, Rule, phrase_pattern, register, sentence_check
from riff.settings import Settings

load_rules()


def test_register_rejects_duplicate():
    with pytest.raises(ValueError, match="duplicate rule code"):
        register(REGISTRY["JEV001"])


def test_phrase_pattern_matches_across_whitespace_and_apostrophes():
    pat = phrase_pattern(["in order to", "it's"])
    assert pat.search("we did this in order\nto win")
    assert pat.search("it’s fine")  # curly apostrophe
    assert not pat.search("disorder tolerance")  # word-boundary guarded


def test_sentence_check_runs_predicate():
    def pred(s: str) -> str | None:
        return "has TODO" if "TODO" in s else None

    checker = sentence_check("ZZZ900", pred)
    REGISTRY["ZZZ900"] = Rule(code="ZZZ900", name="t", summary="t", category="c", source="s",
                              kind="static", check=checker)
    doc = extract_markdown("This is fine. This has a TODO in it. Also fine.")
    out = checker(doc, Settings())
    assert len(out) == 1 and out[0].code == "ZZZ900"


def test_snippet_of_short_text_unchanged():
    from riff.rules.base import snippet_of

    assert snippet_of("A short line.") == "A short line."


def test_snippet_of_collapses_whitespace():
    from riff.rules.base import snippet_of

    assert snippet_of("a   b\t c\nd") == "a b c d"


def test_snippet_of_truncates_with_ellipsis():
    from riff.rules.base import snippet_of

    out = snippet_of("word " * 40, width=20)
    assert len(out) == 20
    assert out.endswith("…")


def test_snippet_of_leading_ellipsis_when_offset_past_window():
    from riff.rules.base import snippet_of

    text = "x" * 50 + " target here"
    out = snippet_of(text, start=45)
    assert out.startswith("…")
    assert "target here" in out


def test_snippet_of_no_leading_ellipsis_at_start():
    from riff.rules.base import snippet_of

    assert not snippet_of("hello world", start=0).startswith("…")


def test_regex_matches_reports_exact_line_and_col():
    import re

    from riff.extract import extract_text
    from riff.rules.base import regex_matches

    doc = extract_text("alpha beta\ngamma DELTA epsilon")
    block = doc.blocks[0]
    hits = list(regex_matches(block, re.compile("DELTA")))
    assert len(hits) == 1
    _, line, col = hits[0]
    assert line == 2
    assert col == 7  # 1-indexed column within the second source line


def test_builtin_rule_factory_metadata():
    # Pins the values the jev_rule/static_rule factories pass through, so mutating those defaults is caught.
    jev = REGISTRY["JEV001"]
    assert jev.kind == "jev"
    assert jev.default is True
    assert jev.scope == "block"
    assert jev.severity == "warning"
    assert jev.threshold == 0.65
    assert jev.source == "tropes.fyi"

    doc_rule = REGISTRY["JEV010"]
    assert doc_rule.scope == "document"

    static = REGISTRY["CLR002"]
    assert static.kind == "static"
    assert static.default is False   # off by default
    assert static.check is not None
