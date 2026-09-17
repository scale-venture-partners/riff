"""Extraction: every supported format yields prose blocks with usable locations."""

from __future__ import annotations

from pathlib import Path

import pytest

from riff.extract import extract, extract_html, extract_markdown, extract_text

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_markdown_headings_and_lists():
    doc = extract_markdown("# Title Here\n\nA paragraph of prose.\n\n- one item\n- two item\n")
    assert doc.format == "md"
    assert [b.kind for b in doc.blocks] == ["heading", "paragraph", "list_item", "list_item"]
    assert doc.headings[0].text == "Title Here"
    assert doc.blocks[1].line == 3


def test_markdown_strips_inline_and_code_fence():
    doc = extract_markdown("Use **bold** and `code` and [a link](http://x.com).\n\n```\nnot prose\n```\n")
    assert doc.prose[0].text == "Use bold and code and a link."
    assert all("not prose" not in b.text for b in doc.blocks)


def test_markdown_front_matter_skipped():
    doc = extract_markdown("---\ntitle: x\n---\n\nReal content.\n")
    assert doc.prose[0].text == "Real content."


def test_hard_wrapped_phrase_spans_lines():
    from riff.rules.base import phrase_pattern, regex_matches

    doc = extract_text("please do this in order\nto finish today")
    block = doc.blocks[0]
    hits = list(regex_matches(block, phrase_pattern(["in order to"])))
    assert len(hits) == 1, "phrase wrapped across a newline should still match"


def test_html_blocks_and_bold_lead():
    doc = extract_html("<h1>Head</h1><p>Body text.</p><ul><li><strong>Key</strong>: value</li></ul>")
    kinds = {b.kind for b in doc.blocks}
    assert "heading" in kinds and "list_item" in kinds
    li = next(b for b in doc.blocks if b.kind == "list_item")
    assert li.bold_lead


def test_text_paragraphs_split_on_blank_lines():
    doc = extract_text("para one\nstill one\n\npara two\n")
    assert len(doc.blocks) == 2
    assert doc.blocks[1].line == 4


@pytest.mark.parametrize("name", ["sloppy.md", "sloppy.txt", "sloppy.html", "sloppy.docx", "sloppy.pptx"])
def test_sample_files_extract(name):
    doc = extract(SAMPLES / name)
    assert doc.prose, f"{name} produced no prose blocks"
    assert doc.word_count > 5


def test_unsupported_extension():
    with pytest.raises(ValueError, match="unsupported"):
        extract(SAMPLES / "nope.pdf")
