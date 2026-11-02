"""Structure rules: hierarchy norms, changelog shape, list hygiene, and size statistics."""

from __future__ import annotations

from riff.engine import lint_document
from riff.extract import extract_markdown
from riff.rules import load_rules
from riff.settings import Settings

load_rules()


def codes(text, *select):
    settings = Settings(jev=False, classify=False, select=tuple(select))
    return [f.code for f in lint_document(extract_markdown(text), settings).findings]


def test_skipped_heading_level():
    assert "RIF006" in codes("## Setup\n\nText here.\n\n#### Details\n\nMore text.", "RIF006")


def test_clean_hierarchy_ok():
    md = "# Title\n\nIntro.\n\n## A\n\nText.\n\n### A1\n\nText.\n\n### A2\n\nText.\n\n## B\n\nText."
    assert codes(md, "RIF006") == []


def test_second_h1():
    assert "RIF006" in codes("# One\n\nText.\n\n# Two\n\nText.", "RIF006")


def test_empty_section_and_lone_subsection():
    md = "# Title\n\nIntro.\n\n## A\n\n### Only child\n\nText."
    found = codes(md, "RIF006")
    assert found.count("RIF006") == 2  # A has no text before its subheading; A has one subsection


def test_h1_followed_by_h2_is_not_empty():
    assert codes("# Title\n\n## A\n\nText.\n\n## B\n\nText.", "RIF006") == []


def test_numbered_emoji_and_link_headings():
    md = "## 1. Getting started\n\nText.\n\n## 🚀 Quick start\n\nText.\n\n## See [docs](http://x.io)\n\nText."
    assert codes(md, "RIF007").count("RIF007") == 3


def test_plain_heading_ok():
    assert codes("## Getting started\n\nText.", "RIF007") == []


CHANGELOG = """# Changelog

## [Unreleased]

### Added
- A thing.

## [1.1.0] - 2026-02-01

### Fixed
- A bug.

## [1.0.0] - 2026-01-01

### Added
- First release.
"""


def test_good_changelog_is_clean():
    assert codes(CHANGELOG, "RIF008") == []


def test_changelog_order_date_group_and_empty():
    bad = CHANGELOG.replace("## [1.1.0] - 2026-02-01", "## [0.9.0] - Feb 1, 2026").replace(
        "### Fixed\n- A bug.", "### Stuff\n- A bug.\n\n### Removed")
    found = codes(bad, "RIF008")
    assert found.count("RIF008") >= 4  # order, date, group name, empty group


def test_changelog_needs_two_versions():
    assert codes("# Notes\n\n## 1.0.0 - January 5\n\n### Added\n- x", "RIF008") == []


def test_single_item_list():
    assert "RIF009" in codes("Intro text.\n\n- only one\n\nMore text.", "RIF009")


def test_two_item_list_ok():
    assert codes("Intro.\n\n- one\n- two\n\nMore.", "RIF009") == []


def _section(words):
    return "\n\n".join(f"## Section {i}\n\n" + " ".join(["word"] * n) + "." for i, n in enumerate(words))


def test_uniform_section_size_flagged():
    assert "CLR008" in codes("# T\n\n" + _section([150, 160, 140, 155]), "CLR008")


def test_lopsided_sections_ok():
    assert "CLR008" not in codes("# T\n\n" + _section([400, 60, 250, 30]), "CLR008")


def test_paragraph_too_long():
    long = " ".join(["Short sentence here."] * 10)
    assert "CLR009" in codes(long, "CLR009")
    assert codes("A short one. And another.", "CLR009") == []


def test_bold_density():
    bold = " ".join(["**very bold words here**"] * 150)
    assert "CLR010" in codes(bold, "CLR010")
    assert codes(" ".join(["plain words"] * 300) + " **one**", "CLR010") == []


def test_wall_of_text_only_without_structure():
    text = " ".join(["Plain sentence here."] * 150)
    assert "CLR011" in codes(text, "CLR011")
    assert codes("## Head\n\n" + text, "CLR011") == []
