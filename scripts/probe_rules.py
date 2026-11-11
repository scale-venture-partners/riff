"""Probe Jev rules on their own examples before turning them on (CONTRIBUTING, "Adding a Jev rule").

Usage: uv run python scripts/probe_rules.py [CODE ...]        (needs TYPESAFE_API_KEY or another backend)

For each rule, asks Jev the rule's question about every example in its catalog entry (each should fire) and
about a plain control passage (it should not), and prints the probabilities next to the rule's threshold.
With no codes, probes every off-by-default Jev rule. A rule is ready to be on by default when its examples
clear the threshold, the control does not, and a run over a human/AI corpus (scripts/bench_structure.py)
agrees.
"""

from __future__ import annotations

import asyncio
import sys

from riff.extract import extract_markdown
from riff.jev import JevUnavailable, run_jev
from riff.rules import load_rules
from riff.rules.base import REGISTRY
from riff.settings import Settings

# Plain, specific prose that names its actors and numbers; no rule in the catalog should fire on it.
CONTROL = (
    "# Rotating the signing key\n\n"
    "The service reads its signing key from the KMS alias at startup. To rotate it, create a new key version, "
    "point the alias at it, and restart the three API pods; requests signed with the old version keep "
    "verifying for 24 hours, after which the verifier rejects them with a 401.\n"
)


def _doc_for(code: str, text: str) -> str:
    rule = REGISTRY[code]
    if rule.scope == "title":
        return f"# {text}\n\nThe body of this section describes the setup in a few plain sentences.\n"
    return text


async def probe(code: str) -> list[tuple[str, float | None]]:
    rule = REGISTRY[code]
    settings = Settings(select=(code,), classify=False, jev_min_words=1)
    rows = []
    for label, text in [("example", ex) for ex in rule.examples] + [("control", CONTROL)]:
        doc = extract_markdown(text if label == "control" else _doc_for(code, text))
        _, stats = await run_jev(doc, [code], settings, debug=True)
        probs = [p for _, c, p in stats.get("probabilities", []) if c == code]
        rows.append((f"{label}: {text.splitlines()[0][:70]}", max(probs) if probs else None))
    return rows


async def main(codes: list[str]) -> int:
    load_rules()
    codes = codes or [c for c, r in REGISTRY.items() if r.kind == "jev" and not r.default and not r.custom]
    for code in codes:
        rule = REGISTRY[code]
        print(f"\n{code} {rule.name} (threshold {rule.threshold})")
        for label, p in await probe(code):
            mark = "-" if p is None else ("FIRES" if p >= rule.threshold else "quiet")
            print(f"  {'n/a' if p is None else f'{p:.2f}':>5} {mark:<5} {label}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main([a.upper() for a in sys.argv[1:]])))
    except JevUnavailable as exc:
        print(f"probe_rules: {exc}", file=sys.stderr)
        sys.exit(2)
