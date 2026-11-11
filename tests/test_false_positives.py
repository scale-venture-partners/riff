"""The false-positive budget: clean prose must lint to zero with every offline rule enabled.

Two controls. tests/fixtures/human/ holds files named <doc-type>--<slug>.md (see its README). The other is
the Python standard library's own docstrings, generated at test time from the interpreter running the tests,
so no third-party prose is vendored into the repository.
"""

from __future__ import annotations

import ast
import sysconfig
from pathlib import Path

import pytest

from riff.engine import lint_document
from riff.extract import extract_markdown
from riff.rules import load_rules
from riff.rules.base import REGISTRY
from riff.settings import Settings

load_rules()

FIXTURES = Path(__file__).parent / "fixtures" / "human"
STATIC = tuple(code for code, rule in REGISTRY.items() if rule.kind == "static" and not rule.custom)


def _findings(text: str, doc_type: str, codes: tuple[str, ...] = STATIC) -> list[str]:
    settings = Settings(jev=False, select=codes, forced_type=doc_type)
    doc = extract_markdown(text, name="fixture.md")
    return [f"{f.code}:{f.line} {f.message}" for f in lint_document(doc, settings).findings]


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*--*.md")), ids=lambda p: p.stem)
def test_human_fixture_is_clean(path: Path):
    doc_type = path.stem.split("--", 1)[0]
    assert _findings(path.read_text(encoding="utf-8"), doc_type) == []


def _stdlib_docstrings(modules: tuple[str, ...]) -> str:
    lib = Path(sysconfig.get_paths()["stdlib"])
    paragraphs = []
    for name in modules:
        source = lib / f"{name}.py"
        if not source.exists():
            continue
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                for para in (doc or "").split("\n\n"):
                    para = " ".join(para.split())
                    if len(para.split()) >= 12 and not para.startswith(">>>"):
                        paragraphs.append(para)
    return "\n\n".join(paragraphs)


# The register rules: a vocabulary rate and an orthographic check, neither gated by type, so they must hold
# on human reference prose too. (The repetition rules skip documentation, which repeats its frames by design.)
REGISTER_STATIC = ("CLR013", "RIF010")


def test_stdlib_docstrings_stay_clean_on_register_rules():
    text = _stdlib_docstrings(("textwrap", "shutil", "argparse", "json/__init__", "subprocess", "functools"))
    assert len(text.split()) > 5000  # enough prose for a rate to mean something
    assert _findings(text, "documentation", REGISTER_STATIC) == []
