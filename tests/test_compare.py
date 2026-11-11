"""`riff --compare SOURCE REWRITE`: what an edit lost or invented."""

from __future__ import annotations

import json

from riff.cli import main
from riff.compare import compare, features, read_for_compare, render


def kinds(src: str, dst: str, **kw) -> set[tuple[str, str]]:
    return {(c.direction, c.kind) for c in compare(src, dst, **kw)}


def test_identical_text_has_no_findings():
    text = "The single most important build is v4.2, released on 12 March by Acme. It never retries."
    assert compare(text, text) == []
    assert "every claim survives" in render([], "a -> b")


def test_a_dropped_number_and_an_invented_name():
    out = compare("Released on 12 March by Acme.", "Released in March by Acme and Initech.")
    assert [(c.direction, c.kind, c.token) for c in out] == [
        ("LOST", "number", "12"), ("ADDED", "name", "Initech")]


def test_spelled_numbers_match_digits():
    assert compare("It took three retries.", "It took 3 retries.") == []


def test_sentence_initial_capitals_are_not_names():
    assert features("Then it failed. Afterwards Acme fixed it.")["name"] == {"Acme": 1}


def test_a_superlative_rewritten_as_a_comparative_is_lost():
    out = compare("This is the format that most invites staged reveals.",
                  "This format invites staged reveals more than most formats do.")
    assert ("COUNT", "superlative") in {(c.direction, c.kind) for c in out}


def test_a_rephrased_superlative_survives():
    assert ("COUNT", "superlative") not in kinds("the format that most invites reveals",
                                                 "the format most likely to invite reveals")


def test_lost_scope_negation_and_hedge_are_counted():
    found = kinds("Every request is never retried and roughly half time out.", "Requests are retried and half time out.")
    assert {("COUNT", "scope"), ("COUNT", "negation"), ("COUNT", "hedge")} <= found


def test_code_links_and_quotes_are_held_verbatim():
    src = 'Run `make all`, see https://example.com/a, and note "the cache is warm" here.'
    dst = 'Run `make`, see https://example.com/b, and note "the cache is hot" here.'
    found = kinds(src, dst)
    assert {("LOST", "verbatim"), ("ADDED", "verbatim"), ("LOST", "quoted"), ("ADDED", "quoted")} <= found


def test_presence_not_frequency():
    assert compare("Acme shipped. Acme shipped again.", "Acme shipped once more.") == []


def test_waive_drops_matching_findings():
    assert compare("Released on 12 March.", "Released in March.", waive=("12",)) == []


def test_render_lists_each_finding():
    text = render(compare("Released on 12 March.", "Released in March."), "a -> b")
    assert "1 finding(s)" in text and "[LOST ] number" in text and "--waive" in text


def test_read_for_compare_keeps_markdown_raw_and_extracts_docx(tmp_path):
    md = tmp_path / "a.md"
    md.write_text("Run `make all`.\n")
    assert "`make all`" in read_for_compare(str(md))
    import docx

    d = docx.Document()
    d.add_paragraph("Acme shipped v4.2 on 12 March.")
    path = tmp_path / "a.docx"
    d.save(path)
    assert "Acme shipped v4.2" in read_for_compare(str(path))


def test_cli_exit_codes_and_json(tmp_path, capsys):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("Released on 12 March by Acme.\n")
    b.write_text("Released in March by Acme.\n")
    assert main(["--compare", str(a), str(a)]) == 0
    assert "every claim survives" in capsys.readouterr().out
    assert main(["--compare", str(a), str(b)]) == 1
    assert "[LOST ] number" in capsys.readouterr().out
    assert main(["--compare", str(a), str(b), "--waive", "12"]) == 0
    capsys.readouterr()
    assert main(["--compare", str(a), str(b), "--format", "json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"][0] == {"direction": "LOST", "kind": "number", "token": "12", "source": 1,
                                      "rewrite": 0, "note": payload["findings"][0]["note"]}


def test_cli_missing_file_exits_2(tmp_path, capsys):
    a = tmp_path / "a.md"
    a.write_text("text\n")
    assert main(["--compare", str(a), str(tmp_path / "missing.md")]) == 2
    assert "riff --compare" in capsys.readouterr().err
