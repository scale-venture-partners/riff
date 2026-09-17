# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
