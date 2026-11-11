"""Register rules ported from declauding: CLR013 vocabulary rate, CLR014-015 repetition, RIF010 hyphens."""

from __future__ import annotations

from pathlib import Path

from riff.engine import lint_document
from riff.extract import extract_markdown
from riff.rules import load_rules
from riff.rules.register_rules import CORPUS_LEAD, _longest_run
from riff.settings import Settings

load_rules()


def findings(text, code, doc_type="blog_post"):
    settings = Settings(jev=False, select=(code,), forced_type=doc_type)
    return [f for f in lint_document(extract_markdown(text), settings).findings if f.code == code]


PLAIN = ("The service reads its config from environment variables at startup and exits when one is missing. "
         "We deploy on Fridays when the on-call engineer approves, and a rollback takes about two minutes. ")


# ---------------------------------------------------------------- CLR013


def test_corpus_list_is_the_published_150():
    assert len(CORPUS_LEAD) == 150
    assert {"load-bearing", "plainly", "quietly", "refusal", "byte-identical"} <= CORPUS_LEAD


def test_flat_certainty_register_fires_above_one_per_hundred():
    flat = ("The guard plainly refuses the call, and nothing else reaches it. The fix survived a re-derived "
            "check and is byte-identical. Nobody quietly carries the premise; the ruling holds. ")
    out = findings((flat + PLAIN) * 6, "CLR013")
    assert len(out) == 1
    assert "per 100" in out[0].message and "not proof of authorship" in out[0].message
    assert "byte-identical x6" in out[0].message  # top five, ties broken alphabetically


def test_flat_certainty_register_quiet_on_plain_prose():
    assert findings(PLAIN * 10, "CLR013") == []


def test_flat_certainty_register_needs_enough_words():
    assert findings("The guard plainly refuses. Nothing else reaches it.", "CLR013") == []


def test_flat_certainty_register_ignores_lists_and_headings():
    md = "# Plainly nothing\n\n" + "\n".join("- plainly nothing nobody refuses" for _ in range(60)) + "\n\n" + PLAIN * 4
    assert findings(md, "CLR013") == []


# ---------------------------------------------------------------- CLR014


def test_longest_run():
    assert _longest_run("a b c d e".split(), "x b c d y".split()) == (3, 1)
    assert _longest_run(["a"], ["b"]) == (0, 0)


def test_echoed_skeleton_fires_on_a_filled_template():
    text = "A shopping cart is an object in the system. A chat room is an object in the system."
    out = findings(text, "CLR014")
    assert len(out) == 1 and "'is an object in the system'" in out[0].message


def test_echoed_skeleton_quiet_on_a_shared_idiom():
    # Shares "is the same as" but most of each sentence differs.
    text = ("The retry budget is the same as the timeout in the default profile for workers. "
            "Its effect on latency is the same as doubling the pool, which we measured last week in staging.")
    assert findings(text, "CLR014") == []


def test_echoed_skeleton_reports_once_per_paragraph():
    t = "A cart is an object in the system. A room is an object in the system. A user is an object in the system."
    assert len(findings(t, "CLR014")) == 1


def test_echoed_skeleton_skips_documentation():
    text = "A shopping cart is an object in the system. A chat room is an object in the system."
    assert findings(text, "CLR014", doc_type="documentation") == []


# ---------------------------------------------------------------- CLR015


def test_anaphora_run_sentences():
    out = findings("It was a message. It was a permission slip. It was an out.", "CLR015")
    assert len(out) == 1 and "three sentences" in out[0].message and "'it was'" in out[0].message


def test_anaphora_run_clauses():
    out = findings("We wanted something to fix, something to ship, something to forget by Friday.", "CLR015")
    assert len(out) == 1 and "three clauses" in out[0].message


def test_anaphora_two_is_ordinary_parallelism():
    assert findings("It was late. It was raining. Then the build finished.", "CLR015") == []


def test_anaphora_skips_poems():
    assert findings("It was a message. It was a permission slip. It was an out.", "CLR015", doc_type="poem") == []


# ---------------------------------------------------------------- RIF010


def test_predicate_hyphen_needs_a_cluster():
    assert findings("The team is cross-functional.", "RIF010") == []
    out = findings("The team is cross-functional and the report is data-driven.", "RIF010")
    assert [f.message.split("'")[1] for f in out] == ["cross-functional", "data-driven"]
    assert "('cross functional')" in out[0].message


def test_predicate_hyphen_leaves_attributive_compounds_alone():
    assert findings("A cross-functional team wrote a data-driven report on a long-term plan.", "RIF010") == []


def test_predicate_hyphen_skips_always_hyphenated_compounds():
    text = ("The file is read-only. The cache is thread-safe. The parser is self-contained. "
            "The index is zero-based. The match is case-sensitive. The docs are up-to-date.")
    assert findings(text, "RIF010") == []


def test_predicate_hyphen_allows_a_degree_word():
    out = findings("The plan is very long-term, and the work was fully end-to-end.", "RIF010")
    assert [f.message.split("'")[1] for f in out] == ["long-term", "end-to-end"]


# ---------------------------------------------------------------- the false-positive guard is not vacuous


def test_static_rules_do_fire_on_the_sloppy_sample():
    sloppy = (Path(__file__).parent.parent / "samples" / "sloppy.md").read_text(encoding="utf-8")
    settings = Settings(jev=False, forced_type="blog_post")
    assert lint_document(extract_markdown(sloppy), settings).findings
