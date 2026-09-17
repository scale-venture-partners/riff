"""Config resolution and ruff-style select/ignore semantics."""

from __future__ import annotations

from riff.rules import load_rules
from riff.settings import Settings, load_settings

load_rules()


def test_defaults_enable_default_rules_only():
    active = set(Settings().active_codes())
    assert "RIF001" in active  # default on
    assert "CLR002" not in active  # default off


def test_select_by_prefix():
    active = set(Settings(select=("JEV",)).active_codes())
    assert active and all(c.startswith("JEV") for c in active)


def test_no_jev_drops_jev_rules():
    active = Settings(jev=False).active_codes()
    assert not any(c.startswith("JEV") for c in active)


def test_extend_select_adds_to_defaults():
    active = set(Settings(extend_select=("CLR002",)).active_codes())
    assert "CLR002" in active
    assert "RIF001" in active


def test_ignore_wins_over_select():
    active = set(Settings(select=("RIF",), ignore=("RIF002",)).active_codes())
    assert "RIF002" not in active
    assert "RIF001" in active


def test_threshold_override():
    s = Settings(thresholds={"JEV001": 0.9})
    assert s.threshold_for("JEV001") == 0.9
    from riff.rules.base import REGISTRY
    assert s.threshold_for("JEV002") == REGISTRY["JEV002"].threshold  # falls back to the rule default


def test_load_from_riff_toml(tmp_path):
    (tmp_path / "riff.toml").write_text(
        'select = ["RIF", "JEV3"]\nignore = ["RIF002"]\njev = false\nmax-sentence-words = 30\n'
        '[thresholds]\nJEV001 = 0.8\n'
    )
    s = load_settings(start=tmp_path)
    assert s.select == ("RIF", "JEV3")
    assert s.max_sentence_words == 30
    assert s.jev is False
    assert s.thresholds["JEV001"] == 0.8


def test_load_from_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[tool.riff]\nselect = ["JEV"]\nmodel = "jev-preview"\n')
    s = load_settings(start=tmp_path)
    assert s.select == ("JEV",)
    assert s.model == "jev-preview"
