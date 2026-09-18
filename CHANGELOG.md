# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Test-quality pass: broader unit coverage (extraction for every format, reporter,
  text metrics, rule-registry helpers, and offline `jev` helpers), a 90% coverage
  floor enforced in CI, and a mutmut mutation-testing setup with docs.

### Fixed
- The summary no longer reports "All checks passed" when Jev requests failed; a
  keyless-or-errored run with zero findings is now flagged as incomplete.

### Added
- Generic message-level rules: `JEV010` formulaic (template) structure, `JEV111`
  canned low-pressure sign-off, `JEV207` interchangeable boilerplate, and `JEV208`
  faux-personalization. These catch AI-shaped outreach that is clean sentence by
  sentence.
- Document-scope Jev rules: a rule can be asked once over the whole text (`scope =
  "document"`), not just per paragraph.
- Custom rules: define your own `[[custom_rules]]` in `riff.toml` (a Jev question or
  a list of banned phrases) without touching the codebase. Firm- or domain-specific
  checks live here; the built-in rules stay generic.
- Initial release: a prose linter with ruff-style rule codes over Markdown, plain
  text, HTML, Word (`.docx`), and PowerPoint (`.pptx`).
- 48 rules: 42 semantic rules answered by TypeSafe's Jev model and 6 deterministic
  code rules (glyphs, structure, and clarity metrics).
- Rule sources: [tropes.fyi](https://tropes.fyi/tropes-md) AI-writing tells,
  Williams' *Style: Lessons in Clarity and Grace*, and Strunk & White's
  *The Elements of Style*.
- Configuration via `riff.toml` or `[tool.riff]` with ruff-style
  `select`/`ignore`/`extend-select`, per-rule Jev thresholds, and metric limits.
- CLI: `--list-rules`, `--explain CODE`, `--no-jev`, `--format json`,
  `--debug-jev`, and both `riff FILE` and `riff -f FILE` forms.
