# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Raised the `JEV502` (vague-abstraction) threshold to 0.85. On a corpus of real professional
  documents it was the most-fired rule and flagged concrete text, so it now triggers only on
  strong cases; egregious vagueness still fires.

### Added
- Tuned rules from a full per-type dogfood: `JEV304` (promotional) skips ad-copy types where
  selling is the point; `JEV207` (boilerplate) and `JEV502` (abstraction) skip terse genres
  (notes, SMS, chat, script) and no longer flag conventional sign-offs or functional lines.
  Cleared the false positives this surfaced on riff's own README (35 to 1).
- Calibrated the documentation rules against riff's own README (dogfooding): `JEV601` and
  `JEV602` are now opt-in (they over-fired on real docs), `JEV001` skips `documentation`, and
  `samples/types/` now holds a neutral public example of every supported document type.
- Type-specific rules mined from seminal style texts (JEV601-JEV670): task orientation and
  undefined terms (docs), buried conclusion (report/memo), editorializing (news), feature-not-
  benefit (marketing), on-the-nose dialogue (script), forced rhyme (poem), vague changelog entry
  (release notes), and weak resume bullets. Each cites its source(s); the README maps sources by type.
- Document-type classification: riff detects the kind of writing (email, memo, SMS, essay,
  blog post, report, and ~20 more) with one Jev pass, and rules can gate on it via
  `applies_to` / `skip_for`. New `JEV112` flags a greeting or sign-off outside an email or
  letter. Force the type with `--type`, or turn classification off with `--no-classify`;
  custom rules can gate on type too.
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
