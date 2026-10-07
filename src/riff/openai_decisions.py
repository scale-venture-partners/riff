"""OpenAI's Decisions API (`POST /v1/decisions`) as a Pydantic AI DecisionModel.

The API takes a list of questions and returns a list of answers; Pydantic AI's decision protocol keys
both by name. A yes/no (`noul`) is OpenAI's `predicate`. Score questions are not supported: riff never
asks one.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import cast

import httpx2
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError, UnexpectedModelBehavior, UserError
from pydantic_ai.models.decision import (
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionAnswer,
    DecisionModel,
    DecisionModelSettings,
    DecisionQuestion,
    DecisionRequest,
    DecisionResponse,
    NoulAnswer,
    NoulQuestion,
)
from pydantic_ai.usage import RequestUsage

DEFAULT_BASE_URL = "https://api.openai.com/v1"


def render_instructions(instructions: object) -> str:
    """Flatten riff's structured instructions (question, includes, not_for, ...) into the one string OpenAI takes."""
    if isinstance(instructions, str):
        return instructions
    if isinstance(instructions, dict):
        parts = [str(instructions["question"])] if "question" in instructions else []
        parts += [
            f"{key.replace('_', ' ').capitalize()}: {value}" for key, value in instructions.items() if key != "question"
        ]
        return "\n".join(parts)
    return json.dumps(instructions)


def _wire_question(name: str, question: DecisionQuestion) -> dict[str, object]:
    instructions = render_instructions(question.instructions)
    if isinstance(question, NoulQuestion):
        if question.criteria is not None:
            instructions += f"\nYes means: {question.criteria.true}\nNo means: {question.criteria.false}"
        return {"type": "predicate", "name": name, "instructions": instructions}
    if isinstance(question, ChoiceQuestion):
        choices = [
            {"value": value, "description": render_instructions(desc)} for value, desc in question.criteria.items()
        ]
        return {"type": "choice", "name": name, "instructions": instructions, "choices": choices}
    raise UserError("The OpenAI Decisions backend supports yes/no and pick-one questions, not score questions.")


@dataclass(init=False)
class OpenAIDecisionModel(DecisionModel[httpx2.AsyncClient]):
    """`gpt-6-luna` and any other model served at `/v1/decisions`. Reads OPENAI_API_KEY and OPENAI_BASE_URL."""

    _model_name: str = field(repr=False)
    _base_url: str = field(repr=False)
    _api_key: str = field(repr=False)
    _client: httpx2.AsyncClient = field(repr=False)

    def __init__(self, model_name: str):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise UserError("Set the `OPENAI_API_KEY` environment variable to use the OpenAI Decisions API.")
        self._model_name = model_name
        self._api_key = api_key
        self._base_url = os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self._client = httpx2.AsyncClient()
        super().__init__()

    @property
    def client(self) -> httpx2.AsyncClient:
        return self._client

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def system(self) -> str:
        return "openai"

    async def decide(self, request: DecisionRequest, model_settings: DecisionModelSettings) -> DecisionResponse:
        state = request.state if isinstance(request.state, str) else json.dumps(request.state)
        body = {
            "model": self._model_name,
            "input": state,
            "questions": [_wire_question(name, q) for name, q in request.questions.items()],
        }
        timeout = model_settings.get("timeout")
        try:
            response = await self._client.post(
                f"{self._base_url}/decisions",
                json=body,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=httpx2.USE_CLIENT_DEFAULT if timeout is None else cast(float, timeout),
            )
        except httpx2.TransportError as exc:
            raise ModelAPIError(model_name=self._model_name, message=f"{type(exc).__name__}: {exc}") from exc
        if response.is_error:
            try:
                error_body: object = response.json()
            except ValueError:
                error_body = response.text
            raise ModelHTTPError(
                status_code=response.status_code, model_name=self._model_name, body=error_body,
                headers=dict(response.headers),
            )
        return self._parse(response, request.questions)

    def _parse(self, response: httpx2.Response, questions: dict[str, DecisionQuestion]) -> DecisionResponse:
        try:
            payload = response.json()
            answers = {a["name"]: _read_answer(a, questions[a["name"]]) for a in payload["answers"]}
        except (ValueError, KeyError, TypeError) as exc:
            raise UnexpectedModelBehavior(
                f"Invalid response from the OpenAI Decisions API: {exc!r}", response.text
            ) from exc
        if answers.keys() != questions.keys():
            raise UnexpectedModelBehavior(
                "Invalid response from the OpenAI Decisions API: answer names do not match the questions", response.text
            )
        usage = payload.get("usage") or {}
        return DecisionResponse(
            answers=answers,
            model_name=payload.get("model", self._model_name),
            usage=RequestUsage(input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0)),
        )


def _read_answer(raw: dict, question: DecisionQuestion) -> DecisionAnswer:
    kind = raw["type"]
    if kind == "refusal":
        raise UnexpectedModelBehavior(f"The OpenAI Decisions API refused question {raw.get('name')!r}: {raw!r}")
    if isinstance(question, NoulQuestion) and kind == "predicate":
        return NoulAnswer(noul=float(raw["probability"]))
    if isinstance(question, ChoiceQuestion) and kind == "choice":
        probabilities = {p["value"]: float(p["probability"]) for p in raw["probabilities"]}
        return ChoiceAnswer(choice=raw["choice"], confidence=float(raw["confidence"]), probabilities=probabilities)
    raise UnexpectedModelBehavior(f"Answer type {kind!r} does not match its {question.type!r} question")
