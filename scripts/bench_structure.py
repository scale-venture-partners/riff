"""Benchmark the structure and rhythm rules over a labelled corpus.

Usage: uv run python scripts/bench_structure.py CORPUS_DIR [RULE ...]

CORPUS_DIR holds human/ and ai/ subdirectories (kept outside the repo). Prints, per rule, how many documents
in each class it fires on, and per-document metrics for threshold tuning.
"""

from __future__ import annotations

import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

from riff.engine import lint_document
from riff.extract import extract
from riff.rules import load_rules
from riff.rules.structure_rules import peer_sections, section_words
from riff.settings import Settings

DEFAULT_RULES = ("CLR004", "CLR005", "CLR006", "CLR007", "RIF006", "RIF007", "RIF009", "CLR008", "CLR009", "CLR010")


def metrics(doc) -> dict[str, float]:
    peers = peer_sections(doc)
    sizes = [section_words(s) for s in peers]
    out = {"words": float(doc.word_count)}
    if len(sizes) >= 4 and min(sizes) > 0:
        out["section_cv"] = (sum((v - st.mean(sizes)) ** 2 for v in sizes) / len(sizes)) ** 0.5 / st.mean(sizes)
    return out


def main() -> None:
    root = Path(sys.argv[1])
    rules = tuple(sys.argv[2:]) or DEFAULT_RULES
    load_rules()
    settings = Settings(jev=False, classify=False, select=rules)
    fires: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    n = defaultdict(int)
    cvs: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for label in ("human", "ai"):
        for path in sorted((root / label).glob("*")):
            if path.suffix not in (".md", ".html", ".txt"):
                continue
            doc = extract(path)
            n[label] += 1
            for code in {f.code for f in lint_document(doc, settings).findings}:
                fires[code][label].append(path.name)
            m = metrics(doc)
            if "section_cv" in m:
                cvs[label].append((round(m["section_cv"], 2), path.name[:40]))
    print(f"documents: human={n['human']} ai={n['ai']}")
    print(f"{'rule':8} {'human':>10} {'ai':>10}")
    for code in rules:
        h, a = len(fires[code]["human"]), len(fires[code]["ai"])
        print(f"{code:8} {h:>4}/{n['human']:<5} {a:>4}/{n['ai']:<5}")
    for label in ("human", "ai"):
        vals = sorted(cvs[label])
        print(f"\nsection CV, {label} (n={len(vals)}): " + ", ".join(f"{v}" for v, _ in vals))
    for code in rules:
        if fires[code]["human"]:
            print(f"\n{code} fired on human: {', '.join(fires[code]['human'][:8])}")


if __name__ == "__main__":
    main()
