"""Offline unit tests for jev.py pure helpers (no network). The live model path is in test_jev_live."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from riff.extract import extract_markdown
from riff.jev import JevUnavailable, _findings_for_block, _is_link_list, build_questions, run_jev
from riff.rules import load_rules
from riff.settings import Settings

load_rules()


def test_is_link_list():
    assert _is_link_list("[a](http://x) · [b](http://y) · [c](http://z)")
    assert _is_link_list("see [one](http://a) and [two](http://b)")
    assert not _is_link_list("A normal sentence with no links at all.")


def test_build_questions_only_jev_with_questions():
    q = build_questions(["JEV001", "RIF001", "CLR001"])  # only JEV001 is a jev rule
    assert list(q.keys()) == ["JEV001"]


def test_findings_for_block_thresholds():
    doc = extract_markdown("A paragraph of text to anchor findings on.")
    block = doc.prose[0]
    answers = {
        "JEV001": SimpleNamespace(noul=0.95),  # above threshold -> fires
        "JEV002": SimpleNamespace(noul=0.10),  # below -> quiet
    }
    resp = SimpleNamespace(answers=answers)
    out = _findings_for_block(doc, block, resp, ["JEV001", "JEV002"], Settings())
    assert [f.code for f in out] == ["JEV001"]
    assert out[0].probability == 0.95


async def test_run_jev_no_jev_codes_returns_empty():
    doc = extract_markdown("Some prose here for the test.")
    findings, stats = await run_jev(doc, ["RIF001", "CLR001"], Settings())
    assert findings == [] and stats["calls"] == 0


async def test_run_jev_missing_key_raises(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    doc = extract_markdown("Some prose here for the test that has enough words to be a target.")
    with pytest.raises(JevUnavailable, match="TYPESAFE_API_KEY"):
        await run_jev(doc, ["JEV001"], Settings())
