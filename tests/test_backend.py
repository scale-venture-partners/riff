"""The decision-model backend against a real local `/v1/systemone` server, no network.

The server speaks the System One wire format, so these tests exercise the real Pydantic AI
SystemOneModel, request building, response validation, retries and riff's finding logic together.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from riff.backend import BackendUnavailable, qualified_name, resolve_model
from riff.doctype import classify_document
from riff.extract import extract_markdown
from riff.jev import run_jev
from riff.settings import Settings

PREAMBLE = "Before diving in, let me set up what follows and explain the shape of the argument."


class _Server(HTTPServer):
    requests: list[dict]
    failures: list[int]  # statuses to return, in order, before answering normally
    overflow: bool  # answer 400 with Ollama's context-overflow wording
    hot: set[str]  # noul question names answered with a high probability


def _handler(server: _Server):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            server.requests.append(body)
            if server.overflow:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"error": "prompt 0 has 2868 tokens; expected 1\u20132050 (input is never truncated)"}).encode())
                return
            if server.failures:
                self.send_response(server.failures.pop(0))
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "boom"}')
                return
            answers = {}
            for name, q in body["questions"].items():
                if q["type"] == "noul":
                    answers[name] = {"type": "noul", "noul": 0.95 if name in server.hot else 0.05}
                else:
                    options = list(q["criteria"])
                    probs = {o: (0.9 if i == 0 else 0.1 / (len(options) - 1)) for i, o in enumerate(options)}
                    answers[name] = {"type": "choice", "choice": options[0], "confidence": 0.9,
                                     "probabilities": probs}
            payload = json.dumps({"model": "fake-1", "answers": answers,
                                  "usage": {"input_tokens": 7, "output_tokens": 0}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

    return Handler


@pytest.fixture
def server(monkeypatch):
    srv = _Server(("127.0.0.1", 0), BaseHTTPRequestHandler)
    srv.RequestHandlerClass = _handler(srv)
    srv.requests, srv.failures, srv.hot, srv.overflow = [], [], {"JEV001"}, False
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("SYSTEM_ONE_BASE_URL", f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.setattr("riff.backend.asyncio.sleep", _no_sleep)
    yield srv
    srv.shutdown()
    srv.server_close()


async def _no_sleep(_seconds):
    return None


def test_bare_name_means_jev():
    assert qualified_name("jev-latest") == "typesafe:jev-latest"
    assert qualified_name("system-one:laya") == "system-one:laya"


def test_language_model_is_rejected(monkeypatch):
    from pydantic_ai.models.test import TestModel

    monkeypatch.setattr("riff.backend.infer_model", lambda _spec: TestModel())
    with pytest.raises(BackendUnavailable, match="language model"):
        resolve_model("anthropic:claude-haiku-4-5")


def test_system_one_without_base_url_names_the_fix(monkeypatch):
    monkeypatch.delenv("SYSTEM_ONE_BASE_URL", raising=False)
    with pytest.raises(BackendUnavailable, match="SYSTEM_ONE_BASE_URL"):
        resolve_model("system-one:laya")


async def test_run_jev_flags_through_system_one(server):
    doc = extract_markdown(PREAMBLE)
    findings, stats = await run_jev(doc, ["JEV001", "JEV002"], Settings(model="system-one:fake"))
    assert [f.code for f in findings] == ["JEV001"]
    assert findings[0].probability == 0.95
    assert stats["calls"] == 1 and stats["input_tokens"] == 7 and stats["errors"] == 0
    assert stats["model"] == "fake-1" or stats["model"] == "fake"
    sent = server.requests[0]
    assert sent["model"] == "fake"
    assert set(sent["questions"]) == {"JEV001", "JEV002"}
    assert sent["questions"]["JEV001"]["instructions"]["question"].startswith("Does this passage")


async def test_transient_failure_is_retried(server):
    server.failures = [503, 429]
    doc = extract_markdown(PREAMBLE)
    findings, stats = await run_jev(doc, ["JEV001"], Settings(model="system-one:fake"))
    assert [f.code for f in findings] == ["JEV001"]
    assert stats["errors"] == 0 and len(server.requests) == 3


async def test_persistent_failure_is_counted_not_hidden(server):
    server.failures = [500] * 10
    doc = extract_markdown(PREAMBLE)
    findings, stats = await run_jev(doc, ["JEV001"], Settings(model="system-one:fake"))
    assert findings == []
    assert stats["errors"] == 1 and stats["calls"] == 0
    assert "ModelHTTPError" in stats["error_detail"][0]


async def test_client_error_is_not_retried(server):
    server.failures = [400]
    doc = extract_markdown(PREAMBLE)
    _, stats = await run_jev(doc, ["JEV001"], Settings(model="system-one:fake"))
    assert stats["errors"] == 1 and len(server.requests) == 1


async def test_classify_document_through_system_one(server):
    result = await classify_document("Dear Sam, thanks for the note.", 6, model="system-one:fake")
    assert result.source == "classified"
    assert result.type == "sms"  # the fake always picks the first option
    assert 0 < result.confidence <= 1


async def test_classify_document_unresolved_without_backend(monkeypatch):
    monkeypatch.delenv("SYSTEM_ONE_BASE_URL", raising=False)
    result = await classify_document("Some text.", 2, model="system-one:fake")
    assert result.source == "unresolved"


async def test_context_overflow_warns_without_failing(server):
    server.overflow = True
    doc = extract_markdown(PREAMBLE)
    findings, stats = await run_jev(doc, ["JEV001"], Settings(model="system-one:fake"))
    assert findings == []
    assert stats["context_exceeded"] == 1 and stats["errors"] == 0
    assert stats["context_tokens"] == 2868 and stats["context_limit"] == 2050
    assert len(server.requests) == 1  # not retried


def test_report_warns_on_context_overflow(monkeypatch):
    import io

    from riff.engine import LintResult
    from riff.report import render_text

    monkeypatch.setenv("NO_COLOR", "1")
    stats = {"calls": 0, "input_tokens": 0, "model": "tev1:4b", "system": "system-one",
             "context_exceeded": 4, "context_tokens": 4962, "context_limit": 2050}
    res = LintResult(document=extract_markdown("Body paragraph here for context."), findings=[], jev_stats=stats)
    buf = io.StringIO()
    render_text([res], stream=buf)
    out = buf.getvalue()
    assert "tev1:4b's context (2,050 tokens) is too small for 4 request(s)" in out
    assert "largest 4,962 tokens" in out and "incomplete" not in out
