"""Rule registry loader. Importing the rule modules registers every rule as a side effect."""

from __future__ import annotations

_LOADED = False


def load_rules() -> None:
    global _LOADED
    if _LOADED:
        return
    from riff.rules import jev_rules, static_rules  # noqa: F401  (import registers rules)

    _LOADED = True
