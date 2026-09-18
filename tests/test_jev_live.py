"""Live Jev test against the real API. Skipped unless TYPESAFE_API_KEY is set.

Per project convention, the model path is exercised against the real stack rather than mocked.
Run in CI only where the key is available; it is a couple of cheap calls.
"""

from __future__ import annotations

import os

import pytest

from riff.extract import extract_markdown
from riff.jev import run_jev
from riff.settings import Settings

pytestmark = pytest.mark.skipif(
    not os.environ.get("TYPESAFE_API_KEY"), reason="TYPESAFE_API_KEY not set; live Jev test skipped"
)


async def test_preamble_detected_live():
    doc = extract_markdown(
        "Before diving in, let me set up what follows and explain the shape of the argument."
    )
    settings = Settings(select=("JEV001",))
    findings, stats = await run_jev(doc, ["JEV001"], settings)
    assert stats["calls"] >= 1
    codes = {f.code for f in findings}
    assert "JEV001" in codes
    assert all(0.0 <= f.probability <= 1.0 for f in findings)


async def test_clean_prose_stays_quiet_live():
    doc = extract_markdown(
        "The service reads its configuration at startup and exits with an error when a variable is missing."
    )
    settings = Settings(select=("JEV001", "JEV101"))
    findings, _ = await run_jev(doc, ["JEV001", "JEV101"], settings)
    assert findings == [] or all(f.probability < 0.9 for f in findings)


async def test_strunk_white_rule_detected_live():
    doc = extract_markdown("The situation developed in an unsatisfactory manner over the relevant period.")
    settings = Settings(select=("JEV502",))
    findings, stats = await run_jev(doc, ["JEV502"], settings)
    assert stats["calls"] >= 1
    assert "JEV502" in {f.code for f in findings}


async def test_document_scope_rule_runs_once_live():
    doc = extract_markdown(
        "Hi there! I lead growth at Acme and noticed your team is scaling fast. "
        "We help companies streamline onboarding. About us: 500+ customers and a Series A. "
        "Would you be open to a quick chat next week?"
    )
    settings = Settings(select=("JEV010",))
    findings, stats = await run_jev(doc, ["JEV010"], settings)
    assert stats["calls"] == 1  # one call over the whole document, not per block
    assert "JEV010" in {f.code for f in findings}


async def test_formulaic_close_detected_live():
    doc = extract_markdown("Let me know if that works, and no worries if now is not the right time.")
    settings = Settings(select=("JEV111",))
    findings, _ = await run_jev(doc, ["JEV111"], settings)
    assert "JEV111" in {f.code for f in findings}


async def test_classifies_email_live():
    from riff.doctype import classify_document

    text = ("Hi Jordan, nice to meet you. I lead AI investing at the firm and wanted to reach out. "
            "Would you be up for a coffee sometime next week? Thanks, Alex")
    result = await classify_document(text, len(text.split()))
    assert result.source == "classified"
    assert result.type in {"email", "letter"}


async def test_form_specific_rule_fires_for_its_type_live():
    from riff.settings import Settings

    doc = extract_markdown("## v2.3.0\n\nVarious improvements and bug fixes. Minor changes throughout.")
    settings = Settings(select=("JEV660",), forced_type="release_notes")
    findings, _ = await run_jev(doc, ["JEV660"], settings)
    assert "JEV660" in {f.code for f in findings}
