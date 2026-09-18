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
riff email.txt --type email      # force the document type (skips classification)
riff draft.md --no-classify      # don't classify; type-specific rules run everywhere
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

Each Jev rule is one yes/no (Noul) question asked about a single paragraph. It is phrased so a
high probability means the tell is present. riff prints that probability (`p=0.93`) on every Jev
finding, and you set a per-rule `threshold` to tune sensitivity. The document text is sent to the
API as data; treat any content you lint accordingly.

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
`press_release`, `resume`, `script`, `poem`, `notes`, `other`.

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
skip_for = ["email", "letter"]   # never run for these document types
# applies_to = ["memo", "report"]  # or: run ONLY for these types

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

## Rules

62 rules (56 semantic, 6 static). A `·` means off by default; enable it with `--select` or `--extend-select`.

### CLR — Clarity metrics (arithmetic Jev can't do)

| Code | Rule | On | Kind | What it flags | Source |
|------|------|----|------|---------------|--------|
| `CLR001` | long-sentence |   | static | Sentence longer than the configured word limit | Williams |
| `CLR002` | hard-to-read | · | static | Paragraph reading grade above the configured level | Williams |
| `CLR003` | duplicate-paragraph |   | static | Paragraph repeated near-verbatim elsewhere | tropes.fyi |

### JEV — Semantic rules (Jev model) — the bulk of the catalog

| Code | Rule | On | Kind | What it flags | Source |
|------|------|----|------|---------------|--------|
| `JEV001` | preamble |   | Jev | Announces what it is about to say instead of saying it | tropes.fyi |
| `JEV002` | reasoning-leak |   | Jev | Narrates its own writing or thinking process | tropes.fyi |
| `JEV003` | premise-stacking | · | Jev | Makes its point only after a wall of its own evidence | tropes.fyi |
| `JEV004` | tie-back |   | Jev | Closes by restating the answer and looping back to the question | tropes.fyi |
| `JEV005` | belaboring | · | Jev | Defends a minor point against an objection nobody raised | tropes.fyi |
| `JEV006` | signposted-conclusion |   | Jev | Explicitly announces that it is concluding | tropes.fyi |
| `JEV007` | fractal-summary | · | Jev | Restates itself at the start or end of a section | tropes.fyi |
| `JEV008` | enumerated-prose |   | Jev | A listicle disguised as prose ("The first… The second…") | tropes.fyi |
| `JEV009` | never-ending-conclusion | · | Jev | The ending stacks clause after clause instead of stopping | tropes.fyi |
| `JEV010` | formulaic-structure |   | Jev | Follows a formulaic template, hitting every expected beat in order | tropes.fyi |
| `JEV101` | stakes-inflation |   | Jev | Inflates ordinary stakes to world-historical significance | tropes.fyi |
| `JEV102` | invented-concept-label |   | Jev | Coins an abstract term as if it were established | tropes.fyi |
| `JEV103` | quotable-bait |   | Jev | A standalone quotable line that carries no real information | tropes.fyi |
| `JEV104` | forced-figurative | · | Jev | A simile or metaphor reached for to sound clever, not to clarify | tropes.fyi |
| `JEV105` | false-vulnerability | · | Jev | Performative self-awareness or risk-free 'honesty' | tropes.fyi |
| `JEV106` | collaborative-we | · | Jev | Drifts into an unearned collective 'we' | tropes.fyi |
| `JEV107` | rule-of-three | · | Jev | Stacks parallel triples (tricolons) back to back | tropes.fyi |
| `JEV108` | false-suspense |   | Jev | A "here's the kicker" transition promising a revelation | tropes.fyi |
| `JEV109` | pedagogical-voice |   | Jev | A hand-holding, teacher-to-student voice | tropes.fyi |
| `JEV111` | formulaic-close |   | Jev | A canned, low-pressure sign-off | tropes.fyi |
| `JEV112` | misplaced-greeting |   | Jev | A personal greeting or sign-off where the format doesn't call for one | tropes.fyi |
| `JEV110` | futurist-invitation | · | Jev | "Imagine a world where…" salesmanship | tropes.fyi |
| `JEV201` | one-point-dilution | · | Jev | Restates one idea several ways without adding anything | tropes.fyi |
| `JEV202` | superficial-analysis |   | Jev | Attaches hollow significance to a mundane fact | tropes.fyi |
| `JEV203` | despite-challenges | · | Jev | Raises a problem only to immediately wave it away | tropes.fyi |
| `JEV204` | vague-attribution |   | Jev | Attributes a claim to an unnamed authority | tropes.fyi |
| `JEV205` | appeal-to-familiarity | · | Jev | Asserts canonical status without evidence | tropes.fyi |
| `JEV207` | generic-boilerplate |   | Jev | Interchangeable boilerplate that could describe almost anyone | tropes.fyi |
| `JEV208` | faux-personalization | · | Jev | Sprinkles specifics to seem researched without genuine detail | tropes.fyi |
| `JEV206` | rapid-fire-analogies | · | Jev | Lists historical companies or shifts to build false authority | tropes.fyi |
| `JEV301` | ai-vocabulary |   | Jev | Overused AI filler vocabulary used as filler | tropes.fyi |
| `JEV302` | magic-adverb |   | Jev | An adverb inflating significance ('quietly', 'fundamentally') | tropes.fyi |
| `JEV303` | ornate-noun |   | Jev | An ornate or grandiose noun where a plain word fits | tropes.fyi |
| `JEV304` | promotional-language |   | Jev | Reads like marketing copy rather than description | tropes.fyi |
| `JEV305` | empty-transition | · | Jev | A filler transition that connects nothing | tropes.fyi |
| `JEV306` | serves-as-dodge | · | Jev | A pompous copula ('serves as', 'stands as') instead of 'is' | tropes.fyi |
| `JEV307` | synonym-cycling | · | Jev | Cycles synonyms for one referent instead of repeating the word | tropes.fyi |
| `JEV308` | comma-clipped-tail | · | Jev | A short tail hung off a comma instead of landing the point | tropes.fyi |
| `JEV401` | passive-voice | · | Jev | Passive voice where the actor matters | Williams |
| `JEV402` | nominalization | · | Jev | The action is buried in an abstract noun | Williams |
| `JEV403` | wordy-phrase |   | Jev | A multi-word phrase where one word would do | Williams |
| `JEV404` | hedging | · | Jev | Vague hedging that weakens the claim without adding precision | Williams |
| `JEV501` | negative-statement |   | Jev | Says what something is not, instead of what it is | Strunk & White, The Elements of Style |
| `JEV502` | vague-abstraction |   | Jev | Abstract, general language where concrete detail would serve | Strunk & White, The Elements of Style |
| `JEV503` | weak-intensifier |   | Jev | Leans on 'very', 'rather', 'pretty', 'quite' for emphasis | Strunk & White, The Elements of Style |
| `JEV504` | loose-sentence-chain | · | Jev | Two or more clauses strung together with and / but / so / which | Strunk & White, The Elements of Style |
| `JEV505` | faulty-parallelism | · | Jev | Coordinate ideas in a series expressed in mismatched forms | Strunk & White, The Elements of Style |
| `JEV601` | not-task-oriented | · | Jev | Documentation that describes the thing instead of telling the reader how to use it | Hargis et al., Developing Quality Technical Information (IBM) |
| `JEV602` | undefined-term | · | Jev | An acronym or specialized term used without being defined on first use | Hargis et al., Developing Quality Technical Information (IBM); Microsoft Writing Style Guide |
| `JEV610` | buried-conclusion |   | Jev | Makes the reader work through context before stating the conclusion | Minto, The Pyramid Principle; Garner, HBR Guide to Better Business Writing |
| `JEV620` | editorializing |   | Jev | Opinion or loaded language inserted into what is presented as reporting | AP Stylebook; Kovach & Rosenstiel, The Elements of Journalism |
| `JEV630` | feature-not-benefit |   | Jev | Lists features without translating them into a benefit to the reader | Ogilvy, Ogilvy on Advertising; Bly, The Copywriter's Handbook |
| `JEV640` | on-the-nose-dialogue |   | Jev | Dialogue that states feelings or plot directly instead of implying them | McKee, Story; Field, Screenplay |
| `JEV650` | forced-rhyme |   | Jev | Rhyme that distorts word choice or syntax to hit the rhyme | Oliver, A Poetry Handbook; Fry, The Ode Less Travelled |
| `JEV660` | vague-changelog-entry |   | Jev | A release note that says nothing specific ('various improvements') | Keep a Changelog (keepachangelog.com) |
| `JEV670` | weak-resume-bullet |   | Jev | A resume entry with no strong action verb or concrete result | Resume conventions (strong action verbs, quantified results) |

### RIF — Typography and structure (exact checks Jev can't see)

| Code | Rule | On | Kind | What it flags | Source |
|------|------|----|------|---------------|--------|
| `RIF001` | decorative-unicode |   | static | Curly quotes or arrows (glyphs Jev can't see) | tropes.fyi |
| `RIF002` | title-case-heading |   | static | Heading capitalizes every word | tropes.fyi |
| `RIF003` | bold-first-bullets |   | static | Most list items open with a bold lead-in | tropes.fyi |

## Sources

The rule set comes from tropes.fyi, Williams, and Strunk & White:

- AI writing tells, from [tropes.fyi](https://tropes.fyi/tropes-md): negative parallelism,
  em-dash addiction, magic adverbs, signposted conclusions, and the rest.
- Clarity and grace, from Joseph M. Williams, *Style: Lessons in Clarity and Grace*: wordy
  phrases, nominalizations, passive voice, sentence length, and readability.
- The Elements of Style, by Strunk & White: put statements in positive form, use concrete
  language, cut weak intensifiers, avoid loose-sentence chains, and keep parallel form.

Almost every tell is a Jev judgment: pattern-matching misses paraphrases and fires on look-alikes,
so anything that depends on meaning or context is a model question, not a regex. Only what Jev
genuinely cannot do stays in code — exact glyphs it never sees (curly quotes, arrows), structural
facts in markup, cross-document duplicate detection, and arithmetic metrics (sentence length, grade).

### Sources by document type

The type-specific rules are mined from a style text per document type — Minto for reports, Ogilvy
for marketing, Hargis for docs, and so on. Where a form has no single canonical work, we cite the recognized guide or
convention. A rule may cite more than one source, and these overlap with the general catalog above.

| Type | Source(s) mined |
|---|---|
| essay, book_chapter | Zinsser, *On Writing Well*; King, *On Writing* |
| article, press_release | *AP Stylebook*; Kovach & Rosenstiel, *The Elements of Journalism* |
| report, memo | Minto, *The Pyramid Principle*; Garner, *HBR Guide to Better Business Writing* |
| academic_paper | Sword, *Stylish Academic Writing*; Williams, *Style* |
| documentation | Hargis et al., *Developing Quality Technical Information* (IBM); Microsoft / Google style guides |
| marketing_copy, product_description | Ogilvy, *Ogilvy on Advertising*; Bly, *The Copywriter's Handbook* |
| script | McKee, *Story*; Field, *Screenplay* |
| poem | Oliver, *A Poetry Handbook*; Fry, *The Ode Less Travelled* |
| release_notes | *Keep a Changelog*; *Semantic Versioning* |
| email, letter | Shipley & Schwalbe, *Send*; Garner, *HBR Guide* |
| blog_post, social_post | Handley, *Everybody Writes* |
| review | Barnet, *A Short Guide to Writing About …* |
| sms, chat_message | Crystal, *Txtng: The Gr8 Db8*; McCulloch, *Because Internet* (descriptive, not prescriptive) |
| resume | conventions: strong action verbs, quantified results, no first person |

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
