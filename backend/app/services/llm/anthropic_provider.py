"""Anthropic implementation of the LLMProvider protocol (optional paid alt).

Not the default: the hosted demo runs on Gemini's free tier. This is the
"bring-your-own paid key" path for running real client data with a stronger
privacy posture. Kept as a second concrete provider to prove the adapter
abstraction is real (swapping providers = one class + a config flag).


"""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.core.config import get_settings
from app.services.llm.base import LLMResult, LLMUsage

T = TypeVar("T", bound=BaseModel)


_PRICE_TABLE: dict[str, tuple[float, float]] = {
    # model: (input_per_mtok, output_per_mtok)  -- placeholder defaults
    "claude-sonnet-5": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-opus-4-8": (15.0, 75.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    inp, out = _PRICE_TABLE.get(model, (0.0, 0.0))
    return round((input_tokens / 1e6) * inp + (output_tokens / 1e6) * out, 6)


class AnthropicProvider:
    """Thin wrapper around the official `anthropic` SDK.

    Kept intentionally small so the rest of the codebase never imports the SDK.
    """

    def __init__(self, api_key: str | None = None, default_model: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.anthropic_api_key
        self._default_model = default_model or settings.llm_model_planner
        self._client = None  # lazily constructed in Phase 3

    async def complete(
        self, *, system: str, prompt: str, model: str | None = None, max_tokens: int = 1024
    ) -> LLMResult:
        raise NotImplementedError("Wired in Phase 3 — see PROJECT_STATUS.md")

    async def complete_structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[T],
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> tuple[T, LLMUsage]:
        raise NotImplementedError("Wired in Phase 2/3 — see PROJECT_STATUS.md")
