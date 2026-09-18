"""riff command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from riff import __version__
from riff.doctype import TYPE_NAMES, is_valid_type
from riff.engine import lint_path
from riff.extract import SUPPORTED
from riff.jev import JevUnavailable
from riff.report import render_json, render_text
from riff.rules import load_rules
from riff.rules.base import REGISTRY
from riff.settings import Settings, find_config, load_settings


def _split_list(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="riff",
        description="A small, fast prose linter. Flags AI writing tells and clarity problems with "
        "ruff-style rule codes, backed by TypeSafe's Jev model for the semantic rules.",
        epilog="Examples:\n  riff doc.md\n  riff -f report.docx --no-jev\n  riff *.md --select JEV,RIF1 --format json\n"
        "  riff --list-rules\n  riff --explain JEV001",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("paths", nargs="*", help="files to lint (.md .txt .html .docx .pptx)")
    p.add_argument("-f", "--file", action="append", default=[], metavar="FILE",
                   help="a file to lint (repeatable); same as a positional path")
    p.add_argument("--select", type=_split_list, help="only these rule codes/prefixes (comma-separated)")
    p.add_argument("--ignore", type=_split_list, help="disable these rule codes/prefixes")
    p.add_argument("--extend-select", type=_split_list, help="enable these on top of the defaults/select")
    p.add_argument("--no-jev", action="store_true", help="skip semantic (Jev) rules; static rules only")
    p.add_argument("--type", dest="doc_type", metavar="TYPE",
                   help="force the document type (e.g. email, memo, sms); skips classification, works with --no-jev")
    p.add_argument("--no-classify", action="store_true",
                   help="do not classify the document type (type-specific rules then run everywhere)")
    p.add_argument("--model", help="Jev model id (default from config, else jev-latest)")
    p.add_argument("--max-sentence-words", type=int, help="word limit for CLR001 (default 45)")
    p.add_argument("--format", choices=("text", "json"), default="text", help="output format")
    p.add_argument("--config", type=Path, help="path to a riff.toml or pyproject.toml")
    p.add_argument("--debug-jev", action="store_true",
                   help="print every Jev probability per block (to tune thresholds), even below threshold")
    p.add_argument("--list-rules", action="store_true", help="print the rule catalog and exit")
    p.add_argument("--explain", metavar="CODE", help="print one rule's full explanation and exit")
    p.add_argument("--no-color", action="store_true", help="disable ANSI color")
    p.add_argument("-q", "--quiet", action="store_true", help="findings only, no summary line")
    p.add_argument("--version", action="version", version=f"riff {__version__}")
    return p


def _apply_overrides(settings: Settings, args: argparse.Namespace) -> Settings:
    if args.select:
        settings.select = args.select
    if args.ignore:
        settings.ignore = settings.ignore + args.ignore
    if args.extend_select:
        settings.extend_select = settings.extend_select + args.extend_select
    if args.no_jev:
        settings.jev = False
    if args.model:
        settings.model = args.model
    if args.max_sentence_words is not None:
        settings.max_sentence_words = args.max_sentence_words
    if args.no_classify:
        settings.classify = False
    if args.doc_type:
        settings.forced_type = args.doc_type
    return settings


def cmd_list_rules(stream=None) -> int:
    stream = stream or sys.stdout
    load_rules()
    by_prefix: dict[str, list] = {}
    for rule in REGISTRY.values():
        by_prefix.setdefault(rule.prefix, []).append(rule)
    for prefix in sorted(by_prefix):
        print(f"\n{prefix} rules", file=stream)
        for rule in by_prefix[prefix]:
            kind = "jev " if rule.kind == "jev" else "    "
            star = " " if rule.default else "·"
            print(f"  {star}{rule.code}  {kind} {rule.name:<26} {rule.summary}", file=stream)
    print("\n· = off by default (enable with --select or --extend-select). jev = needs TYPESAFE_API_KEY.", file=stream)
    return 0


def cmd_explain(code: str, stream=None) -> int:
    stream = stream or sys.stdout
    load_rules()
    rule = REGISTRY.get(code.upper())
    if rule is None:
        print(f"unknown rule {code!r}. Run `riff --list-rules` for the catalog.", file=sys.stderr)
        return 2
    print(f"{rule.code}  {rule.name}  [{rule.kind}, {rule.category}]", file=stream)
    print(f"source: {rule.source}", file=stream)
    print(f"default: {'on' if rule.default else 'off'}   severity: {rule.severity}", file=stream)
    if rule.kind == "jev":
        print(f"threshold: {rule.threshold}", file=stream)
    print(f"\n{rule.summary}", file=stream)
    if rule.explanation:
        print(f"\n{rule.explanation}", file=stream)
    if rule.examples:
        print("\nExamples of what it flags:", file=stream)
        for ex in rule.examples:
            print(f"  - {ex}", file=stream)
    if rule.kind == "jev" and rule.question:
        print("\nJev question:", file=stream)
        for k, v in rule.question.items():
            print(f"  {k}: {v}", file=stream)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_rules:
        return cmd_list_rules()
    if args.explain:
        return cmd_explain(args.explain)

    if args.no_color:
        import os

        os.environ["NO_COLOR"] = "1"

    if args.doc_type and not is_valid_type(args.doc_type):
        print(f"--type {args.doc_type!r} is not a known document type. Valid: {', '.join(TYPE_NAMES)}", file=sys.stderr)
        return 2

    paths = list(args.paths) + list(args.file)
    if not paths:
        print("no files given. Usage: riff FILE [FILE ...]  (see --help, --list-rules)", file=sys.stderr)
        return 2

    # Config is resolved from each file's own directory upward (ruff semantics), cached per config root,
    # unless --config names one explicitly.
    settings_cache: dict[object, Settings] = {}

    def settings_for(p: Path) -> Settings:
        key = args.config or find_config(p.resolve().parent)
        if key not in settings_cache:
            settings_cache[key] = _apply_overrides(load_settings(args.config, start=p.resolve().parent), args)
        return settings_cache[key]

    results = []
    any_error = False
    for path in paths:
        p = Path(path)
        if not p.exists():
            print(f"{path}: no such file", file=sys.stderr)
            any_error = True
            continue
        if p.suffix.lower() not in SUPPORTED:
            print(f"{path}: unsupported type {p.suffix!r} (supported: {', '.join(sorted(SUPPORTED))})", file=sys.stderr)
            any_error = True
            continue
        try:
            results.append(lint_path(str(p), settings_for(p), debug_jev=args.debug_jev))
        except JevUnavailable as exc:
            print(f"riff: {exc}", file=sys.stderr)
            return 2
        except Exception as exc:  # noqa: BLE001 - report the file that failed and keep going
            print(f"{path}: failed to lint: {type(exc).__name__}: {exc}", file=sys.stderr)
            any_error = True

    if not results:
        return 2

    if args.debug_jev:
        for r in results:
            for line, code, prob in r.jev_stats.get("probabilities", []):
                print(f"{r.document.path}:{line}: {code} p={prob}", file=sys.stderr)

    if args.format == "json":
        render_json(results)
    else:
        render_text(results, summary=not args.quiet)

    jev_errors = any(r.jev_stats.get("errors") for r in results)
    for r in results:
        for detail in r.jev_stats.get("error_detail", []):
            print(f"{r.document.path}:{detail}", file=sys.stderr)

    has_findings = any(r.findings for r in results)
    if any_error or jev_errors:
        return 2
    return 1 if has_findings else 0


if __name__ == "__main__":
    sys.exit(main())
