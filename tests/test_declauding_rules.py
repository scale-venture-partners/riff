"""The rules ported from the declauding register: where they sit, what they skip, and how Jev is asked.

These are offline checks of the catalog. The live model path for a few of them is in test_jev_live.py.
"""

from __future__ import annotations

from riff.doctype import TYPE_NAMES
from riff.extract import extract_markdown
from riff.jev import plan_units
from riff.rules import load_rules
from riff.rules.base import REGISTRY
from riff.settings import Settings

load_rules()

JEV_NEW = ("JEV012", "JEV014", "JEV113", "JEV114", "JEV115", "JEV209", "JEV210", "JEV211", "JEV212",
           "JEV309", "JEV310", "JEV311", "JEV312", "JEV405", "JEV406", "JEV407", "JEV408", "JEV603",
           "JEV704", "JEV705")
STATIC_NEW = ("CLR013", "CLR014", "CLR015", "RIF010")


def test_every_ported_rule_is_registered_and_off_by_default():
    # Off until probed against the live model (CONTRIBUTING, "Adding a Jev rule") or benched on a labelled
    # corpus (scripts/bench_structure.py); turning one on is a separate, measured change.
    for code in JEV_NEW + STATIC_NEW:
        assert code in REGISTRY, code
        assert not REGISTRY[code].default, code


def test_ported_jev_rules_carry_their_earned_case_and_source():
    for code in JEV_NEW:
        rule = REGISTRY[code]
        assert rule.kind == "jev", code
        assert set(rule.question) >= {"question", "not_for"}, code  # the register's "earned when" column
        assert rule.question["question"].rstrip().endswith("?"), code
        assert "declauding" in rule.source, code
        assert 0.6 <= rule.threshold <= 0.85, code


def test_gates_name_real_document_types():
    for code in JEV_NEW + STATIC_NEW:
        for name in REGISTRY[code].applies_to + REGISTRY[code].skip_for:
            assert name in TYPE_NAMES, (code, name)


def test_ported_rules_sit_at_their_levels():
    levels = {c: REGISTRY[c].scope for c in JEV_NEW}
    assert {c for c, s in levels.items() if s == "document"} == {"JEV012", "JEV014"}
    assert {c for c, s in levels.items() if s == "title"} == {"JEV704", "JEV705"}
    assert all(s == "block" for c, s in levels.items() if c not in {"JEV012", "JEV014", "JEV704", "JEV705"})


def test_heading_rules_leave_decks_to_jev701():
    # A slide title should be a claim (JEV701); a doc heading should be a plain label. The two must not both
    # run on a deck, or every good slide title is flagged as a verdict.
    assert REGISTRY["JEV704"].applies_to == ("documentation", "blog_post")
    assert "presentation" in REGISTRY["JEV705"].skip_for
    assert REGISTRY["JEV603"].applies_to == ("documentation",)


def test_word_choice_ports_read_fragments_and_discourse_ports_do_not():
    for code in ("JEV309", "JEV310", "JEV311", "JEV312", "JEV405"):
        assert REGISTRY[code].fragments, code
    for code in ("JEV113", "JEV114", "JEV209", "JEV210", "JEV211", "JEV407", "JEV408"):
        assert not REGISTRY[code].fragments, code


def test_flat_certainty_rules_are_told_apart_from_their_neighbours():
    # JEV302 inflates significance, JEV309 asserts certainty; JEV011 is about edits to the document, JEV603
    # about prose that leans on the previous version of the thing described.
    assert "JEV302" in REGISTRY["JEV309"].question["not_for"]
    assert "JEV011" in REGISTRY["JEV603"].explanation
    assert "JEV103" in REGISTRY["JEV114"].question["not_for"]
    assert "JEV704" in REGISTRY["JEV705"].explanation


def _plan(md: str, codes: list[str]) -> list:
    return plan_units(extract_markdown(md), codes, Settings(select=tuple(codes)))


def test_document_rules_share_one_call():
    md = "# Notes\n\nThe service reads its config at startup and exits when a variable is missing.\n"
    units = _plan(md, ["JEV012", "JEV014", "JEV010"])
    assert [(u.scope, sorted(u.codes)) for u in units] == [("document", ["JEV010", "JEV012", "JEV014"])]


def test_heading_rules_are_asked_once_per_heading():
    md = ("# Spawn availability\n\nBody text that is long enough to count as a body here.\n\n"
          "## Peer code review is dead\n\nAnother body that is long enough to count as one.\n")
    units = [u for u in _plan(md, ["JEV704", "JEV705"]) if u.scope == "title"]
    assert [u.state["title"] for u in units] == ["Spawn availability", "Peer code review is dead"]
    assert all(sorted(u.codes) == ["JEV704", "JEV705"] for u in units)
