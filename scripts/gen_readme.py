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
[![PyPI](https://img.shields.io/pypi/v/riff-lint.svg)](https://pypi.org/project/riff-lint/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A small, fast prose linter. It reads a document, flags the writing tells and clarity
problems it finds, and reports them with **ruff-style rule codes** you can select, ignore,
and configure. Static rules are pure Python and run in milliseconds. The semantic rules are yes/no
questions for [TypeSafe's **Jev**](https://typesafe.ai), a decision model that returns a calibrated
probability per judgment instead of generated text; every rule asked about the same paragraph (or
section, or document) shares one call.

```console
$ riff draft.md
draft.md: type: blog_post (0.91)
draft.md:1:1: RIF002 heading is Title Case; use sentence case
    Understanding The Impact Of Modern Technology
draft.md:3:1: JEV001 Announces what it is about to say instead of saying it p=0.92
    Before we dive in, let me lay out what this section will cover.
draft.md:5:1: JEV301 Overused AI filler vocabulary used as filler p=0.88
    We leverage a robust, seamless framework to unlock value.
draft.md:9:1: JEV103 A standalone quotable line that carries no real information p=0.79
    Every metric that rewards volume punishes leverage.

4 findings in 1 file (RIF002 ×1, JEV001 ×1, JEV301 ×1, JEV103 ×1).
jev-latest: 14 calls, 9,210 input tokens (~$0.0004)
```

## Install

riff is on PyPI as [`riff-lint`](https://pypi.org/project/riff-lint/) (the name `riff` was taken)
and installs a `riff` command. It needs Python 3.11 or later.

```console
uv tool install riff-lint     # or: pipx install riff-lint, or pip install riff-lint
riff --help
uvx --from riff-lint riff draft.md   # run once without installing
```

The PyPI release can lag `main`; compare `riff --version` with the [changelog](CHANGELOG.md). To
run the latest code from GitHub:

```console
uv tool install git+https://github.com/scale-venture-partners/riff
uvx --from git+https://github.com/scale-venture-partners/riff riff draft.md
```

To work on riff itself, clone it and use [uv](https://docs.astral.sh/uv/):

```console
git clone https://github.com/scale-venture-partners/riff
cd riff
uv sync
uv run riff draft.md
```

## Usage

The examples below assume `riff` is on your PATH. From a clone, prefix each with `uv run`
(`uv run riff draft.md`).

```console
riff draft.md                    # lint one file (positional)
riff -f report.docx              # or the -f/--file flag form
riff *.md notes.txt slides.pptx  # many files, mixed formats
riff https://example.com/blog/post  # fetch a web page and lint just its article body
riff draft.md --no-jev           # static rules only, no API key needed
riff draft.md --select JEV,RIF   # only these codes/prefixes
riff draft.md --ignore JEV002    # keep defaults, drop one rule
riff draft.md --extend-select JEV401  # keep defaults, add an off-by-default rule
riff draft.md --debug-jev        # print every Jev probability, to tune thresholds
riff email.txt --type email      # force the document type (skips classification)
riff draft.md --no-classify      # don't classify; type-specific rules run everywhere
riff draft.md --model openai:gpt-6-luna  # another decision model (see below)
riff draft.md --format json      # machine-readable output
riff draft.md -q                 # findings only, no summary line
riff draft.md --config ci/riff.toml  # use this config instead of discovering one
riff --outline deck.pptx         # print the sections, titles and blocks riff reads, and exit
riff --list-rules                # the full catalog
riff --explain JEV001            # one rule in detail
riff --compare draft.md edited.md  # check an edit kept every claim
```

`riff --help` lists every flag. Color is on in a terminal; `--no-color` or `NO_COLOR=1` turns it off.

**Supported formats:** Markdown (`.md`, `.markdown`), plain text (`.txt`, `.text`), HTML (`.html`,
`.htm`), Word (`.docx`), PowerPoint (`.pptx`). Findings report a line and column for text formats,
and a paragraph or slide label for Office formats.

**URLs:** pass an `http(s)` URL to fetch the page and lint only its article body. riff picks the
largest `<article>`, else `<main>`, else `<body>`, drops navigation, headers, footers, and sidebars,
and narrows to the block that holds most of the paragraph text. Findings are labelled `block N`
(position in the extracted body), since fetched HTML is often minified onto one line.

**Exit codes:** `0` clean, `1` findings, `2` a usage or file error, a missing API key, or a Jev
request that failed (a lint with failed requests is incomplete, so it is never reported as clean).
`--compare` uses the same codes: `1` means the rewrite lost or added something.

### Checking an edit

Fixing what riff flags is an edit to how a draft sounds, and it should not change what the draft claims.
The two ways that goes wrong, a claim dropped or a fact invented, both read fluently afterwards.
`riff --compare SOURCE REWRITE` compares the two versions and reports every number, name, quotation, code
span and link target the rewrite lost or added, plus any drop in superlative ("the single most"), scope
("every", "only"), negation and hedge ("roughly") constructions. It exits `1` when it finds something;
`--waive TOKEN` silences a finding that is a rephrasing, and `--format json` gives machine-readable output.
It is lexical on purpose: an embedding scores a rewrite that dropped a ranking word as nearly identical to
the source. Ported from the [declauding](https://github.com/oaustegard/claude-skills) skill's
`declaude_diff.py`.

## The Jev-backed rules

The semantic rules, and the document-type classifier, need a decision model. The default is Jev: set
`TYPESAFE_API_KEY` in the environment (create one at <https://console.typesafe.ai/>). Without a key,
`riff draft.md` stops with exit code `2` and says how to fix it, rather than quietly running fewer
rules; `riff draft.md --no-jev` runs the static rules alone, and `--type` sets the document type
without a classification call.

### Other decision models

Jev is the default, but riff runs on any *decision model*: one that returns a calibrated
probability per yes/no question instead of generated text. Chat and completion models (GPT, Claude,
and the like) are not decision models, and riff rejects them. riff talks to decision models through
[Pydantic AI's decision models](https://pydantic.dev/docs/ai/models/decision/), plus OpenAI's
Decisions API directly:

```console
riff draft.md                                  # Jev, TYPESAFE_API_KEY
riff draft.md --model typesafe:jev-latest      # the same, spelled out
riff draft.md --model openai:gpt-6-luna        # OpenAI's Decisions API, OPENAI_API_KEY
export SYSTEM_ONE_BASE_URL=http://localhost:8000   # any server that speaks POST /v1/systemone
riff draft.md --model system-one:laya          # Laya, CLM, an Ollama decision model...
```

`OPENAI_BASE_URL` overrides the OpenAI host, and `SYSTEM_ONE_API_KEY` is sent if a System One
server needs one. Set the model for a project with `model = "openai:gpt-6-luna"` in `riff.toml`.

**Thresholds are tuned to Jev.** Another model's probabilities sit on a different scale, so check
its findings with `--debug-jev` and set `[thresholds]` for it before trusting the output.
Small-context models (Ollama's `tev1` reads about 2,000 tokens) cannot hold riff's full rule set;
riff warns when a prompt overflows, and `--select` asks fewer rules per run.

Each Jev rule is one yes/no (Noul) question asked about one part of the document: a paragraph for
most rules, or a sentence, a title, a section, or the whole document (see below). It is phrased so a
high probability means the tell is present. riff prints that probability (`p=0.93`) on every Jev
finding, and you set a per-rule `threshold` to tune sensitivity. The document text is sent to the
API as data; treat any content you lint accordingly.

## How riff reads a document

riff reads every file as a hierarchy, and every rule declares the level it judges:

```
document            the whole piece -- its text, or its outline of titles read in order
└─ section          a heading and everything under it; in a deck, one slide
   ├─ title         a heading or a slide title
   └─ block         a paragraph, list item, table cell, or speaker notes
      └─ sentence   one sentence
```

Most rules read a **block**. Sentence-length (`CLR001`) reads **sentences**. Rules that ask about
narrative sit higher: whether a slide title states a claim reads a **title** (`JEV701`), whether a
section's body delivers its title reads a **section** (`JEV702`), and whether a deck's titles tell its
argument on their own reads the **document** through its outline (`JEV711`). One Jev call is made per
unit at each level, so a section rule costs one call per section, not per paragraph.

A document-scope rule also chooses what it is shown: the prose (`text`, the default), the titles in
order (`outline`), or each section's title with its opening line (`structure`). The outline view is how
a reader skims a deck or a report's headings to follow the argument, so that is what narrative rules
read.

Markdown, HTML and Word headings nest into sections by level; text before the first heading is an
untitled lead section. A deck's slides are its sections, its slide titles their titles, and a slide's
speaker notes belong to it. `riff --outline FILE` prints the hierarchy as riff reads it.

## Slide decks

A `.pptx` is linted as a **presentation**: the type comes from the file format, not from
classifying the text, so the conventions of a deck -- a cover with a presenter and date, an agenda
that announces what's coming, a closing "Thank you" -- are not read as a letter's sign-off or an
essay's preamble (`--type` still overrides).

- **Short copy is covered.** Most slide text is a label or a short line; three quarters of a typical
  deck's blocks are under eight words. Decks use a 4-word floor for Jev (8 for prose formats;
  `jev-min-words` / `--jev-min-words` to change it). Under eight words, a block is asked only the rules
  that can judge a fragment -- word choice, inflated stakes, vague abstraction -- not the discourse
  rules (preamble, quotable line, tie-back) that need sentences around them.
- **Titles are found in decks built from text boxes.** A deck generated by a slide library often has
  no title placeholders; riff takes the largest type on the slide (20pt or more, at least two words,
  not a display figure like `$2.4B`) as its title, so heading and title rules see it.
- **Narrative rules.** `JEV701` flags topic-label titles ("Market overview") where a claim belongs;
  `JEV702` a slide or section whose body doesn't support its title; `JEV711` an outline whose titles,
  read alone, don't tell the argument (the consultant's ghost-deck test); `RIF005` a numbered step or
  part that comes after a later one; and `JEV703` (opt-in) a slide making two points.
- **Charts are acknowledged, not read.** riff reads text only. A slide whose evidence is a chart or
  picture tells the section rules so, rather than looking unsupported.

## Configuration

riff reads `riff.toml` (or `.riff.toml`), or a `[tool.riff]` table in `pyproject.toml`, from the
file's directory upward. Command-line flags override the file. `select`/`ignore` take full codes
(`JEV001`) or prefixes (`JEV`, `RIF1`), with ruff's semantics.

```toml
# riff.toml
select = ["RIF", "CLR", "JEV"]          # omit to use every default-on rule
ignore = ["JEV002"]                      # drop reasoning-leak (noisy on reflective writing)
extend-select = ["JEV401"]               # turn on a default-off rule (passive voice)
extend-ignore = ["CLR001"]               # drop a rule on top of `select`/`ignore`
jev = true                               # set false to skip semantic rules
model = "jev-latest"                     # or "openai:gpt-6-luna", "system-one:<name>"
classify = true                          # set false to skip document-type classification
# type = "memo"                          # force the document type for every file under this config
jev-concurrency = 8                      # Jev requests in flight at once
max-sentence-words = 40                  # CLR001 threshold
max-reading-grade = 12                   # CLR002 threshold
jev-min-words = 4                        # shortest paragraph or sentence sent to Jev (default 8; 4 for .pptx)

[thresholds]                             # per-rule Jev sensitivity, 0..1
JEV001 = 0.7
JEV103 = 0.75
```

## Document types

Before the rules run, riff classifies the whole document with one Jev question: is it an
email, a memo, an SMS, an essay, a blog post, a report, and so on. The detected type prints
above the findings (`type: email (0.88)`).

Types let a rule apply to some kinds of writing and not others. A greeting and sign-off are
normal in an **email** but a tell in a **memo** or **SMS**, so the built-in `JEV112` rule skips
`email` and `letter` and flags a greeting anywhere else.

- Force the type with `--type email` (or any type below). This skips classification, so it
  needs no API key and is the escape hatch when the classifier is wrong or the input is a short
  excerpt.
- Turn classification off with `--no-classify`. Type-specific rules then run everywhere,
  since the type is unresolved. An unresolved type never silently drops a rule.

The type identifiers are: `sms`, `email`, `chat_message`, `memo`, `letter`, `essay`,
`blog_post`, `article`, `report`, `academic_paper`, `book_chapter`, `documentation`,
`release_notes`, `marketing_copy`, `social_post`, `product_description`, `review`,
`press_release`, `resume`, `script`, `poem`, `notes`, `presentation`, `other`. A `.pptx` is a
`presentation` from its format, without a classification call.

## Custom rules

The built-in rules are deliberately generic. Anything specific to your team,
house style, or domain you add in your own `riff.toml` with `[[custom_rules]]`. No
code changes, no fork. Three kinds: `jev` (a question for the model), `phrase` (literal strings,
offline) and `regex` (a pattern, offline).

```toml
# A Jev rule: a yes/no question asked about your text (needs a decision model, as above).
[[custom_rules]]
code = "TEAM001"
name = "no-competitor-names"
type = "jev"
summary = "Names a competitor"
question = "Does this passage name a specific competing product or company?"
threshold = 0.6
scope = "block"      # the level it judges: "sentence", "block" (a paragraph), "title", "section", or "document"
# view = "outline"   # document scope only: "text" (default), "outline" (titles in order), "structure"
# fragments = true   # block scope: also ask about blocks under eight words (labels, slide bullets)
skip_for = ["email", "letter"]   # never run for these document types
# applies_to = ["memo", "report"]  # or: run ONLY for these types

# A phrase rule: literal strings flagged offline, no API key needed.
[[custom_rules]]
code = "TEAM002"
name = "house-style-bans"
type = "phrase"
summary = "House-style banned phrase"
phrases = ["circle back", "synergy", "leverage", "boil the ocean"]

# A case-sensitive phrase: "Founders", capitalized, is house style.
[[custom_rules]]
code = "TEAM003"
name = "lowercase-founders"
type = "phrase"
summary = "Founders is capitalized"
phrases = ["founder", "founders"]
case-sensitive = true

# A regex rule, for what a phrase can't express: a punctuation mark, an emoji range.
# Case-sensitive unless ignore-case = true. blocks = "all" also checks titles and headings,
# where a deck carries much of its copy (the default, "prose", checks paragraphs and lists).
[[custom_rules]]
code = "TEAM004"
name = "no-exclamations"
type = "regex"
summary = "Exclamation mark or emoji"
pattern = "!|[\\U0001F300-\\U0001FAFF]"
blocks = "all"
```

Custom codes must not collide with a built-in code. They are enabled by default and
obey the same `select`/`ignore`/`threshold` controls as built-in rules, so
`--select TEAM` runs only yours and `--ignore TEAM002` drops one.

"""

SOURCES = """\
## Sources

The general catalog draws on:

- AI writing tells from [tropes.fyi](https://tropes.fyi/tropes-md) and Wikipedia's
  [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing): negative
  parallelism, magic adverbs, signposted conclusions, and the rest.
- Joseph M. Williams, *Style: Lessons in Clarity and Grace*: wordy phrases, nominalizations, passive
  voice, sentence length, and readability.
- Strunk & White, *The Elements of Style*: positive form, concrete language, weak intensifiers,
  loose-sentence chains, and parallel form.
- The [declauding](https://github.com/oaustegard/claude-skills) register (Oskar Austegard, MIT):
  flat certainty, compressed syntax, staged closers, and doc headings; with the corpus figures it
  cites from Louis Abraham's [load-bearing](https://github.com/louisabraham/load-bearing) study of
  GitHub pull request descriptions, and Clark, Martin & Mahowald (arXiv 2610.29162) on compressed
  syntax in model output.
- Stylometry for the rhythm rules: Desaire et al. 2023 on sentence- and paragraph-length variation,
  with thresholds calibrated on public human technical posts.
- Structure norms from the Google developer documentation style guide, APA Style, Nielsen Norman
  Group, and Keep a Changelog.

Almost every tell is a Jev judgment: pattern-matching misses paraphrases and fires on look-alikes,
so anything that depends on meaning or context is a model question, not a regex. Only what Jev
cannot do stays in code: exact glyphs it never sees (curly quotes, arrows), structural facts in
markup, comparison across paragraphs, and arithmetic (sentence length, reading grade, rates).

### Rules by document type

Rules gated to particular kinds of writing, and the sources they cite (generated from the catalog).
Every other rule runs on every type, apart from types it explicitly skips.

"""


DEV = """\
## Development

```console
uv sync
uv run ruff check src tests scripts   # lint, as CI runs it
uv run pytest --cov                   # tests; coverage floor 90%. Live Jev tests skip without a key
uv run python scripts/gen_readme.py   # regenerate this README from the rule catalog
uv run python scripts/probe_rules.py JEV123         # a Jev rule's probability on its own examples
uv run python scripts/bench_structure.py CORPUS_DIR # offline rules over a human/AI corpus
```

Edit `scripts/gen_readme.py`, not `README.md`: the README is generated, so a hand edit is
overwritten on the next run.

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
        lines.append("| Code | Rule | On | Kind | Level | What it flags | Source |")
        lines.append("|------|------|----|------|-------|---------------|--------|")
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
            level = rule.scope + (f" ({rule.view})" if rule.view != "text" else "")
            lines.append(f"| `{rule.code}` | {rule.name} | {on} | {kind} | {level} | {summary} | {src} |")
        lines.append("")
    return "\n".join(lines)


def type_table() -> str:
    """Each type's gated rules and their sources, so the table cannot claim a source no rule cites."""
    from riff.doctype import TYPE_NAMES

    load_rules()
    lines = ["| Type | Rules | Sources |", "|---|---|---|"]
    for name in TYPE_NAMES:
        rules = [r for r in REGISTRY.values() if name in r.applies_to and not r.custom]
        if not rules:
            continue
        sources: list[str] = []
        for r in rules:
            for part in r.source.split(";"):
                part = part.strip()
                if part and part not in sources:
                    sources.append(part)
        codes = ", ".join(f"`{r.code}`" for r in rules)
        lines.append(f"| {name} | {codes} | {'; '.join(sources)} |")
    return "\n".join(lines) + "\n\n"


def main() -> None:
    readme = HEAD + rule_table() + "\n" + SOURCES + type_table() + DEV
    (ROOT / "README.md").write_text(readme)
    print(f"wrote README.md ({len(readme)} bytes, {len(REGISTRY)} rules)")


if __name__ == "__main__":
    main()
