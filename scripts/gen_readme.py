"""Generate README.md, building the rule table from the live registry so it cannot drift.

Run: uv run python scripts/gen_readme.py
"""

from __future__ import annotations

from pathlib import Path

from riff.rules import load_rules
from riff.rules.base import REGISTRY

ROOT = Path(__file__).resolve().parent.parent

PREFIX_TITLES = {
    "RIF": "Typography and structure (exact checks Jev can't see)",
    "CLR": "Clarity metrics (arithmetic Jev can't do)",
    "JEV": "Semantic rules (Jev model) — the bulk of the catalog",
}

HEAD = """\
# riff

[![CI](https://github.com/scale-venture-partners/riff/actions/workflows/ci.yml/badge.svg)](https://github.com/scale-venture-partners/riff/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A small, fast prose linter. It reads a document, flags the writing tells and clarity
problems it finds, and reports them with **ruff-style rule codes** you can select, ignore,
and configure. Static rules are pure Python and run in milliseconds; the semantic rules are
one call each to [TypeSafe's **Jev**](https://typesafe.ai) model, which returns a calibrated
probability per judgment instead of generated text.

```console
$ riff draft.md
draft.md:1:1: RIF002 heading is Title Case; use sentence case
    Understanding The Impact Of Modern Technology
draft.md:3:1: JEV001 Announces what it is about to say instead of saying it p=0.92
    Before we dive in, let me lay out what this section will cover.
draft.md:5:1: JEV301 Overused AI filler vocabulary used as filler p=0.88
    We leverage a robust, seamless framework to unlock value.
draft.md:9:1: JEV103 A standalone quotable line that carries no real information p=0.79
    Every metric that rewards volume punishes leverage.

12 findings in 1 file (JEV301 ×3, JEV001 ×2, RIF002 ×1).
Jev: 14 calls, 9,210 input tokens (~$0.0004)
```

## Install

riff is **not on PyPI yet**, so install it from source. It uses
[uv](https://docs.astral.sh/uv/).

**Clone and run:**

```console
git clone https://github.com/scale-venture-partners/riff
cd riff
uv sync
uv run riff --help
uv run riff draft.md
```

**Run directly from GitHub, no clone,** with uvx (the repo is private, so this uses
your existing GitHub credentials via git):

```console
uvx --from git+https://github.com/scale-venture-partners/riff riff draft.md
# SSH works too, if that's how you authenticate to GitHub:
uvx --from git+ssh://git@github.com/scale-venture-partners/riff riff draft.md
```

To install it as a persistent `riff` command on your PATH from the repo:

```console
uv tool install git+https://github.com/scale-venture-partners/riff
riff --help
```

When riff is published to PyPI, `uv tool install riff-lint` will install the same
`riff` command (the `riff` name itself is taken on PyPI).

## Usage

The examples below assume `riff` is on your PATH (via `uv tool install` above). From a
clone without installing, prefix each with `uv run` (e.g. `uv run riff draft.md`).

```console
riff draft.md                    # lint one file (positional)
riff -f report.docx              # or the -f/--file flag form
riff *.md notes.txt slides.pptx  # many files, mixed formats
riff draft.md --no-jev           # static rules only, no API key needed
riff draft.md --select JEV,RIF   # only these codes/prefixes
riff draft.md --ignore JEV002    # keep defaults, drop one rule
riff draft.md --debug-jev        # print every Jev probability, to tune thresholds
riff draft.md --format json      # machine-readable output
riff --list-rules                # the full catalog
riff --explain JEV001            # one rule in detail
```

**Supported formats:** Markdown (`.md`), plain text (`.txt`), HTML (`.html`), Word (`.docx`),
PowerPoint (`.pptx`). Findings report a line and column for text formats, and a paragraph or
slide label for Office formats.

**Exit codes:** `0` clean, `1` findings, `2` usage or file error.

## The Jev-backed rules

The semantic rules need a TypeSafe API key. Set `TYPESAFE_API_KEY` in the environment (create
one at <https://console.typesafe.ai/>). Without it, `--no-jev` runs the static rules alone; if
you select a Jev rule with no key, riff stops and tells you the two ways to fix it rather than
degrading silently.

Each Jev rule is one yes/no (Noul) question asked about a single paragraph, phrased so a high
probability means the tell is present. riff prints that probability (`p=0.93`) on every Jev
finding, and you can set a per-rule `threshold` to tune sensitivity against your own writing.
The document text is sent to the API as data; treat any content you lint accordingly.

## Configuration

riff reads `riff.toml` (or `.riff.toml`), or a `[tool.riff]` table in `pyproject.toml`, from the
file's directory upward. Command-line flags override the file. `select`/`ignore` take full codes
(`JEV001`) or prefixes (`JEV`, `RIF1`), with ruff's semantics.

```toml
# riff.toml
select = ["RIF", "CLR", "JEV"]          # omit to use every default-on rule
ignore = ["JEV002"]                      # drop reasoning-leak (noisy on reflective writing)
extend-select = ["JEV401"]               # turn on a default-off rule (passive voice)
jev = true                               # set false to skip semantic rules
model = "jev-latest"
max-sentence-words = 40                  # CLR001 threshold
max-reading-grade = 12                   # CLR002 threshold

[thresholds]                             # per-rule Jev sensitivity, 0..1
JEV001 = 0.7
JEV103 = 0.75
```

## Custom rules

The built-in rules are deliberately generic. Anything specific to your team,
house style, or domain you add in your own `riff.toml` with `[[custom_rules]]`. No
code changes, no fork. Two kinds:

```toml
# A Jev rule: a yes/no question asked about your text (needs TYPESAFE_API_KEY).
[[custom_rules]]
code = "TEAM001"
name = "no-competitor-names"
type = "jev"
summary = "Names a competitor"
question = "Does this passage name a specific competing product or company?"
threshold = 0.6
scope = "block"      # "block" (per paragraph) or "document" (once over the whole text)

# A phrase rule: literal strings flagged offline, no API key needed.
[[custom_rules]]
code = "TEAM002"
name = "house-style-bans"
type = "phrase"
summary = "House-style banned phrase"
phrases = ["circle back", "synergy", "leverage", "boil the ocean"]
```

Custom codes must not collide with a built-in code. They are enabled by default and
obey the same `select`/`ignore`/`threshold` controls as built-in rules, so
`--select TEAM` runs only yours and `--ignore TEAM002` drops one.

"""

SOURCES = """\
## Sources

The rule set draws on two catalogs of writing problems:

- **AI writing tells** from [tropes.fyi](https://tropes.fyi/tropes-md): negative parallelism,
  em-dash addiction, magic adverbs, signposted conclusions, and the rest.
- **Clarity and grace** from Joseph M. Williams, *Style: Lessons in Clarity and Grace*: wordy
  phrases, nominalizations, passive voice, sentence length, and readability.
- **The Elements of Style** by Strunk & White: put statements in positive form, use concrete
  language, cut weak intensifiers, avoid loose-sentence chains, and keep parallel form.

Almost every tell is a Jev judgment: pattern-matching misses paraphrases and fires on look-alikes,
so anything that depends on meaning or context is a model question, not a regex. Only what Jev
genuinely cannot do stays in code — exact glyphs it never sees (curly quotes, arrows), structural
facts in markup, cross-document duplicate detection, and arithmetic metrics (sentence length, grade).

## Development

```console
uv sync
uv run pytest            # static tests run offline; live Jev tests skip without a key
uv run ruff check src tests
uv run python scripts/gen_readme.py   # regenerate the rule table below
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for how rules work and how to add one.

## License

[MIT](LICENSE) © Scale Venture Partners.
"""


def rule_table() -> str:
    load_rules()
    lines = ["## Rules", "", f"{len(REGISTRY)} rules "
             f"({sum(r.kind == 'jev' for r in REGISTRY.values())} semantic, "
             f"{sum(r.kind == 'static' for r in REGISTRY.values())} static). "
             "A `·` means off by default; enable it with `--select` or `--extend-select`.", ""]
    by_prefix: dict[str, list] = {}
    for rule in REGISTRY.values():
        by_prefix.setdefault(rule.prefix, []).append(rule)
    for prefix in sorted(by_prefix):
        lines.append(f"### {prefix} — {PREFIX_TITLES.get(prefix, prefix)}")
        lines.append("")
        lines.append("| Code | Rule | On | Kind | What it flags | Source |")
        lines.append("|------|------|----|------|---------------|--------|")
        for rule in by_prefix[prefix]:
            on = " " if rule.default else "·"
            kind = "Jev" if rule.kind == "jev" else "static"
            if "tropes" in rule.source:
                src = "tropes.fyi"
            elif "Williams" in rule.source:
                src = "Williams"
            else:
                src = rule.source
            summary = rule.summary.replace("|", "\\|")
            lines.append(f"| `{rule.code}` | {rule.name} | {on} | {kind} | {summary} | {src} |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    readme = HEAD + rule_table() + "\n" + SOURCES
    (ROOT / "README.md").write_text(readme)
    print(f"wrote README.md ({len(readme)} bytes, {len(REGISTRY)} rules)")


if __name__ == "__main__":
    main()
