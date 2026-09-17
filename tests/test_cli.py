"""CLI behavior: argument forms, exit codes, list/explain, and loud failure without a key.

Inputs are written into an isolated tmp dir (outside the repo) so config discovery finds no
riff.toml and the tests exercise the built-in defaults regardless of the repo's own config.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from riff.cli import main

SLOPPY = "# Understanding The Impact Of Technology\n\nThe flow is input \u2192 output here.\n"
CLEAN = "The service reads its configuration at startup and exits with an error when a variable is missing.\n"


@pytest.fixture
def sloppy(tmp_path) -> Path:
    p = tmp_path / "sloppy.md"
    p.write_text(SLOPPY)
    return p


@pytest.fixture
def clean(tmp_path) -> Path:
    p = tmp_path / "clean.md"
    p.write_text(CLEAN)
    return p


def test_positional_and_flag_forms_equivalent(capsys, clean):
    assert main([str(clean), "--no-jev"]) == 0
    capsys.readouterr()
    assert main(["-f", str(clean), "--no-jev"]) == 0


def test_findings_exit_code_1(capsys, sloppy):
    rc = main([str(sloppy), "--no-jev"])
    assert rc == 1
    assert "RIF002" in capsys.readouterr().out


def test_missing_file_exit_2():
    assert main(["does-not-exist.md", "--no-jev"]) == 2


def test_no_paths_exit_2():
    assert main(["--no-jev"]) == 2


def test_list_rules(capsys):
    assert main(["--list-rules"]) == 0
    out = capsys.readouterr().out
    assert "RIF001" in out and "JEV001" in out


def test_explain_known_and_unknown(capsys):
    assert main(["--explain", "JEV001"]) == 0
    assert "preamble" in capsys.readouterr().out.lower()
    assert main(["--explain", "ZZZ999"]) == 2


def test_json_format(capsys, sloppy):
    import json

    rc = main([str(sloppy), "--no-jev", "--format", "json"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["findings"][0]["code"]


def test_ignore_flag(capsys, sloppy):
    rc = main([str(sloppy), "--no-jev", "--ignore", "RIF002"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "RIF002" not in out
    assert "RIF001" in out


def test_jev_missing_key_fails_loudly(capsys, monkeypatch, sloppy):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    rc = main([str(sloppy), "--select", "JEV001"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "TYPESAFE_API_KEY" in err and "--no-jev" in err
