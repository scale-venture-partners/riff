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
