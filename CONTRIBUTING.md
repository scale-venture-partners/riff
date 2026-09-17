# Contributing to riff

Thanks for your interest. riff is a prose linter: it flags AI-writing tells and
clarity problems with ruff-style rule codes.

## Setup

riff uses [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/scale-venture-partners/riff
cd riff
uv sync
uv run riff --help
```

The semantic rules call [TypeSafe's Jev](https://typesafe.ai) model. Set
`TYPESAFE_API_KEY` in your environment to run them (create a key at
<https://console.typesafe.ai/>). Without a key, use `--no-jev` to run the
deterministic rules alone.

## Checks

```bash
uv run ruff check src tests scripts   # lint
uv run pytest                         # tests
```

The static tests run offline. The live Jev tests skip automatically when
`TYPESAFE_API_KEY` is unset, so a bare `pytest` is green without a key; set the
key to exercise the model path.

## How rules work

Each rule is registered in `src/riff/rules/` and has a stable code:

- **Jev rules** (`jev_rules.py`) are one `Noul` question asked about a paragraph,
  phrased so a high probability means the tell is present. This is where almost
  every rule lives — pattern matching misses paraphrases and fires on look-alikes,
  so anything that depends on meaning or context is a model question.
- **Code rules** (`static_rules.py`) are only for what Jev cannot do: exact glyphs
  it never sees (curly quotes, arrows), structural facts in markup, cross-document
  comparison, and arithmetic metrics (sentence length, reading grade).

### Adding a Jev rule

Add a `jev_rule(...)` call with a unique code, a clear `question` (use a `not_for`
field when it could be confused with a neighbouring rule), a `threshold`, and
`default=False` if it is noisy or niche. Then:

1. Probe it on a few positive and negative examples before committing, so it fires
   on real violations and stays quiet on good prose.
2. Add a case to the tests where practical.
3. Regenerate the rule table: `uv run python scripts/gen_readme.py`.

## Style

- Line length 120, ruff-formatted (`select = ["E", "F", "I", "UP", "B"]`).
- Comments state the constraint that makes the code correct, not change history.

## Pull requests

Keep changes focused. Run the checks above and regenerate the README rule table if
you touched the catalog. Describe what the rule flags and why in the PR.
