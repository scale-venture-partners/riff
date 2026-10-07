"""The OpenAI Decisions API backend against a local `/v1/decisions` server, no network."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from riff.backend import BackendUnavailable, resolve_model
from riff.doctype import classify_document
from riff.extract import extract_markdown
from riff.jev import run_jev
from riff.openai_decisions import render_instructions
from riff.settings import Settings

PREAMBLE = "Before diving in, let me set up what follows and explain the shape of the argument."


class _Server(HTTPServer):
    requests: list[dict]
    auth: list[str]
    refuse: bool


def _handler(server: _Server):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            server.requests.append(body)
            server.auth.append(self.headers["Authorization"])
            answers = []
            for q in body["questions"]:
                if server.refuse:
                    answers.append({"type": "refusal", "name": q["name"]})
                elif q["type"] == "predicate":
                    answers.append({"type": "predicate", "name": q["name"],
                                    "probability": 0.95 if q["name"] == "JEV001" else 0.05})
                else:
                    values = [c["value"] for c in q["choices"]]
                    answers.append({"type": "choice", "name": q["name"], "choice": values[0], "confidence": 0.9,
                                    "probabilities": [{"value": v, "probability": 1 / len(values)} for v in values]})
            payload = json.dumps({"model": "gpt-6-luna", "answers": answers,
                                  "usage": {"input_tokens": 11}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

    return Handler


@pytest.fixture
def server(monkeypatch):
    srv = _Server(("127.0.0.1", 0), BaseHTTPRequestHandler)
    srv.RequestHandlerClass = _handler(srv)
    srv.requests, srv.auth, srv.refuse = [], [], False
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("OPENAI_BASE_URL", f"http://127.0.0.1:{srv.server_port}/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    yield srv
    srv.shutdown()
    srv.server_close()


def test_openai_prefix_resolves_to_the_decisions_model(server):
    model = resolve_model("openai:gpt-6-luna")
    assert (model.system, model.model_name) == ("openai", "gpt-6-luna")


def test_missing_key_names_the_fix(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(BackendUnavailable, match="OPENAI_API_KEY"):
        resolve_model("openai:gpt-6-luna")


def test_instructions_render_as_text():
    text = render_instructions({"question": "Is it?", "not_for": "Other things."})
    assert text == "Is it?\nNot for: Other things."


async def test_run_jev_flags_through_openai(server):
    doc = extract_markdown(PREAMBLE)
    findings, stats = await run_jev(doc, ["JEV001", "JEV002"], Settings(model="openai:gpt-6-luna"))
    assert [f.code for f in findings] == ["JEV001"]
    assert findings[0].probability == 0.95
    assert stats["calls"] == 1 and stats["input_tokens"] == 11 and stats["errors"] == 0
    assert stats["system"] == "openai"
    sent = server.requests[0]
    assert sent["model"] == "gpt-6-luna" and sent["input"] == PREAMBLE
    assert {q["name"]: q["type"] for q in sent["questions"]} == {"JEV001": "predicate", "JEV002": "predicate"}
    assert sent["questions"][0]["instructions"].startswith("Does this passage")
    assert server.auth == ["Bearer sk-test"]


async def test_refusal_is_counted_not_read_as_clean(server):
    server.refuse = True
    doc = extract_markdown(PREAMBLE)
    findings, stats = await run_jev(doc, ["JEV001"], Settings(model="openai:gpt-6-luna"))
    assert findings == [] and stats["errors"] == 1 and "refused" in stats["error_detail"][0]


async def test_document_classification_uses_a_choice_question(server):
    result = await classify_document("Dear Sam, thanks for the note.", 6, model="openai:gpt-6-luna")
    sent = server.requests[0]
    assert sent["questions"][0]["type"] == "choice"
    assert json.loads(sent["input"]) == {"word_count": 6, "text": "Dear Sam, thanks for the note."}
    assert result.source == "classified"
