"""Configuration: defaults, riff.toml / pyproject [tool.riff], and ruff-style select/ignore.

Precedence, low to high: built-in defaults, config file, command-line overrides.
`select`/`ignore`/`extend_select`/`extend_ignore` accept full codes (JEV001) or prefixes (JEV, RIF1).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from riff.rules import load_rules
from riff.rules.base import REGISTRY

CONFIG_NAMES = ("riff.toml", ".riff.toml")


@dataclass
class Settings:
    select: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()
    extend_select: tuple[str, ...] = ()
    extend_ignore: tuple[str, ...] = ()
    jev: bool = True
    model: str = "jev-latest"
    max_sentence_words: int = 45
    max_reading_grade: float = 14.0
    thresholds: dict[str, float] = field(default_factory=dict)
    jev_concurrency: int = 8
    source: str = "defaults"

    def threshold_for(self, code: str) -> float:
        if code in self.thresholds:
            return self.thresholds[code]
        return REGISTRY[code].threshold

    def _selected_by_default(self, code: str) -> bool:
        return REGISTRY[code].default

    def _matches(self, code: str, patterns: tuple[str, ...]) -> bool:
        return any(code == p or code.startswith(p) for p in patterns)

    def active_codes(self) -> list[str]:
        """Apply ruff-style select/ignore semantics to the registry, returning enabled codes in order."""
        load_rules()
        chosen = []
        for code, rule in REGISTRY.items():
            if self.select:
                enabled = self._matches(code, self.select)
            else:
                enabled = rule.default
            if self.extend_select and self._matches(code, self.extend_select):
                enabled = True
            if (self.ignore and self._matches(code, self.ignore)) or (
                self.extend_ignore and self._matches(code, self.extend_ignore)
            ):
                enabled = False
            if enabled and not self.jev and rule.kind == "jev":
                enabled = False
            if enabled:
                chosen.append(code)
        return chosen


def _as_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(v) for v in value)


def find_config(start: Path) -> Path | None:
    start = start.resolve()
    for directory in (start, *start.parents):
        for name in CONFIG_NAMES:
            candidate = directory / name
            if candidate.is_file():
                return candidate
        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            try:
                data = tomllib.loads(pyproject.read_text())
            except tomllib.TOMLDecodeError:
                continue
            if "riff" in data.get("tool", {}):
                return pyproject
    return None


def load_settings(explicit: Path | None = None, start: Path | None = None) -> Settings:
    path = explicit or find_config(start or Path.cwd())
    if path is None:
        return Settings()
    data = tomllib.loads(path.read_text())
    table = data.get("tool", {}).get("riff", data) if path.name == "pyproject.toml" else data.get("tool", {}).get("riff", data)
    thresholds = {str(k): float(v) for k, v in (table.get("thresholds") or {}).items()}
    return Settings(
        select=_as_tuple(table.get("select")),
        ignore=_as_tuple(table.get("ignore")),
        extend_select=_as_tuple(table.get("extend-select") or table.get("extend_select")),
        extend_ignore=_as_tuple(table.get("extend-ignore") or table.get("extend_ignore")),
        jev=bool(table.get("jev", True)),
        model=str(table.get("model", "jev-latest")),
        max_sentence_words=int(table.get("max-sentence-words", table.get("max_sentence_words", 45))),
        max_reading_grade=float(table.get("max-reading-grade", table.get("max_reading_grade", 14.0))),
        thresholds=thresholds,
        jev_concurrency=int(table.get("jev-concurrency", table.get("jev_concurrency", 8))),
        source=str(path),
    )
