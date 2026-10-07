"""The decision-model backend: resolve a model name to a Pydantic AI DecisionModel and ask it questions.

riff needs a calibrated probability per judgment, which only decision models return. A bare name such
as `jev-latest` means TypeSafe's Jev; `typesafe:jev-latest` and `system-one:<name>` select a provider
explicitly. `openai:<name>` is OpenAI's Decisions API (OPENAI_API_KEY). `system-one:` covers any server
speaking `POST /v1/systemone` (set SYSTEM_ONE_BASE_URL and optionally SYSTEM_ONE_API_KEY), such as Laya,
Ollama's decision models, or OpenRouter.
"""

from __future__ import annotations

import asyncio
import re

from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError, UnexpectedModelBehavior, UserError
from pydantic_ai.models import infer_model
from pydantic_ai.models.decision import (
    DecisionModel,
    DecisionModelSettings,
    DecisionQuestion,
    DecisionRequest,
    DecisionResponse,
)

from riff.openai_decisions import OpenAIDecisionModel

DEFAULT_PROVIDER = "typesafe"
REQUEST_TIMEOUT = 60.0
_MAX_RETRIES = 3
_RETRYABLE_STATUS = {408, 409, 429}

# Ollama's wording when a prompt exceeds the model's context window.
_CONTEXT_OVERFLOW = re.compile(r"prompt \d+ has (\d+) tokens; expected 1[\u2013-](\d+)")


class ContextExceeded(Exception):
    """The request's prompt is longer than the model's context window, so the request did not run."""

    def __init__(self, tokens: int, limit: int):
        super().__init__(f"prompt has {tokens} tokens; the model's context is {limit}")
        self.tokens = tokens
        self.limit = limit


# Errors a single decision can raise; callers count them rather than abort the lint.
DecisionError = (ModelAPIError, UnexpectedModelBehavior, ContextExceeded)


class BackendUnavailable(RuntimeError):
    """Raised when decision rules are requested but no usable decision model is configured."""


def qualified_name(name: str) -> str:
    return name if ":" in name else f"{DEFAULT_PROVIDER}:{name}"


def resolve_model(name: str) -> DecisionModel:
    spec = qualified_name(name)
    try:
        # Pydantic AI maps `openai:` to OpenAI's language models, so the Decisions API is routed here.
        model = OpenAIDecisionModel(spec.removeprefix("openai:")) if spec.startswith("openai:") else infer_model(spec)
    except ImportError as exc:
        raise BackendUnavailable(f"Cannot use decision model {spec!r}: {exc}") from exc
    except UserError as exc:
        raise BackendUnavailable(
            f"Cannot use decision model {spec!r}: {str(exc).split(' To try')[0]}\n"
            "  Jev:   export TYPESAFE_API_KEY=... (create one at https://console.typesafe.ai/)\n"
            "  OpenAI: --model openai:gpt-6-luna with OPENAI_API_KEY set\n"
            "  Other: --model system-one:<name> with SYSTEM_ONE_BASE_URL set (and SYSTEM_ONE_API_KEY if it needs one)\n"
            "  Or:    run with --no-jev to lint with static rules only."
        ) from exc
    if not isinstance(model, DecisionModel):
        raise BackendUnavailable(
            f"{spec!r} is a language model. riff needs a decision model that returns calibrated probabilities "
            "(typesafe:, openai:gpt-6-luna, system-one:)."
        )
    return model


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, ModelHTTPError):
        return exc.status_code in _RETRYABLE_STATUS or exc.status_code >= 500
    return isinstance(exc, ModelAPIError)


async def decide(model: DecisionModel, state: object, questions: dict[str, DecisionQuestion]) -> DecisionResponse:
    """One decision request, retried on transient failures. Raises DecisionError once retries run out."""
    request = DecisionRequest(state=state, questions=questions)  # type: ignore[arg-type]
    settings = DecisionModelSettings(timeout=REQUEST_TIMEOUT)
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return await model.decide(request, settings)
        except ModelAPIError as exc:
            if isinstance(exc, ModelHTTPError) and exc.status_code == 400:
                if match := _CONTEXT_OVERFLOW.search(str(exc.body)):
                    raise ContextExceeded(int(match[1]), int(match[2])) from exc
            if attempt == _MAX_RETRIES or not _retryable(exc):
                raise
            await asyncio.sleep(2**attempt * 0.5)
    raise AssertionError("unreachable")
