"""Rule registry loader. Importing the rule modules registers every rule as a side effect."""

from __future__ import annotations

_LOADED = False


def load_rules() -> None:
    global _LOADED
    if _LOADED:
        return
    # Importing a rule module registers its rules.
    from riff.rules import jev_rules, register_rules, static_rules, structure_rules  # noqa: F401

    _LOADED = True
