"""Static rules are the code residue (glyphs, structure, metrics). Pure functions over a Document."""

from __future__ import annotations

from riff.engine import lint_document
from riff.extract import extract_markdown, extract_text
from riff.rules import load_rules
from riff.settings import Settings

load_rules()


def codes(text, **kw):
    settings = Settings(jev=False, **kw)
    doc = extract_markdown(text)
    return [f.code for f in lint_document(doc, settings).findings]


def test_decorative_unicode_arrow():
    assert "RIF001" in codes("The pipeline is input → output today.")


def test_decorative_unicode_smart_quote():
    assert "RIF001" in codes("He said “hello” to everyone.")


def test_endash_range_is_not_flagged():
    # A dash in a numeric range is correct typography; the dramatic-dash judgment lives in Jev, not here.
    assert "RIF001" not in codes("Revenue rose 65–70% this year across the board.")


def test_title_case_heading():
    assert "RIF002" in codes("# Understanding The Impact Of Technology\n\nbody text here.")


def test_sentence_case_heading_ok():
    assert "RIF002" not in codes("# Understanding the impact of technology\n\nbody text.")


def test_bold_first_bullets():
    md = "- **A**: one\n- **B**: two\n- **C**: three\n"
    assert "RIF003" in codes(md)


def test_long_sentence_respects_config():
    long = "word " * 60
    assert "CLR001" in codes(f"{long}.", max_sentence_words=45)
    assert "CLR001" not in codes(f"{long}.", max_sentence_words=100)


def test_long_sentence_skips_citation_lists():
    links = " · ".join(f"[Deal {i}](http://x.com/{i})" for i in range(12))
    assert "CLR001" not in codes(f"Acquisitions: {links}")


def test_duplicate_paragraph():
    md = ("This is a repeated paragraph of some length here now.\n\nDifferent text entirely in between.\n\n"
          "This is a repeated paragraph of some length here now.\n")
    assert "CLR003" in codes(md)


def test_clean_prose_has_no_static_findings():
    clean = "The service reads config at startup. It exits with an error when a variable is missing."
    assert codes(clean) == []


def test_default_off_reading_grade_needs_opt_in():
    dense = (
        "The utilization of heterogeneous computational infrastructure necessitates comprehensive "
        "reconfiguration of the orchestration subsystems that administrators maintain. Subsequently, "
        "operational personnel must accommodate substantial variability in concurrent workloads throughout "
        "the deployment lifecycle. Consequently, organizational complexity increases considerably across "
        "geographically distributed enterprise environments everywhere today."
    )
    assert "CLR002" not in codes(dense)
    settings = Settings(jev=False, extend_select=("CLR002",))
    doc = extract_text(dense)
    assert "CLR002" in [f.code for f in lint_document(doc, settings).findings]


def _revision_hits(text):
    doc = extract_markdown(text)
    return [(f.line, f.col, f.snippet) for f in lint_document(doc, Settings(jev=False)).findings if f.code == "RIF004"]


def test_revision_badge_flags_count_badge_in_heading():
    hits = _revision_hits("# Portfolio overview (+2 companies added)\n\nbody text here.")
    assert [(line, col) for line, col, _ in hits] == [(1, 22)]


def test_revision_badge_flags_short_bullets_and_asides():
    md = "- Zeta and Eta (added per your request)\n- Revenue by segment (updated to include Acme)\n- Note: as requested."
    assert [line for line, _, _ in _revision_hits(md)] == [1, 2, 3]


def test_revision_badge_flags_updated_prefix_line():
    assert [line for line, _, _ in _revision_hits("Updated: removed the pricing table.")] == [1]


def test_revision_badge_ignores_legitimate_parentheticals_and_stamps():
    ok = (
        "Revenue grew 14% (+3 pts vs. plan).\n\n"
        "Last updated: 2026-09-01.\n\n"
        "The API was updated in March to add pagination.\n\n"
        "We added two engineers to the platform team."
    )
    assert _revision_hits(ok) == []


def test_revision_badge_skipped_for_release_notes():
    settings = Settings(jev=False, forced_type="release_notes")
    doc = extract_markdown("- Search (added per your request)")
    assert "RIF004" not in [f.code for f in lint_document(doc, settings).findings]


def test_a_pull_quote_enclosing_its_block_is_not_decorative():
    # A layout that sets a statement in typographic quotes, as a slide library does.
    from riff.rules.base import REGISTRY

    check = REGISTRY["RIF001"].check
    assert check(extract_markdown("\u201cThe model is the same. What changes is the harness.\u201d"), Settings()) == []
    inline = check(extract_markdown("He said \u201chello\u201d and left."), Settings())
    assert len(inline) == 2, "quotes inside a sentence are still the tell"
    assert len(check(extract_markdown("\u201cAn opening quote that never closes"), Settings())) == 1
    assert check(extract_markdown("\u201c"), Settings()) == [], "a hanging quote set as its own box"
