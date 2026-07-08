"""Provider-agnostic LLM adapter interface.

Everything in InsightIQ talks to this Protocol, never to a vendor SDK directly.
Swapping providers = adding one implementation + a config flag. Structured
generation is first-class because the planner and semantic-layer generator must
return schema-valid JSON (constrained decoding), not free text we regex-parse.
"""
from __future__ import annotations

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMUsage(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cache_hit: bool = False


class LLMResult(BaseModel):
    text: str
    usage: LLMUsage


class StructuredResult(BaseModel):
    """Generic container; `.data` is validated against the caller's schema."""

    data: dict[str, Any]
    usage: LLMUsage


class LLMProvider(Protocol):
    """Minimal surface the rest of the app relies on."""

    async def complete(
        self, *, system: str, prompt: str, model: str | None = None, max_tokens: int = 1024
    ) -> LLMResult: ...

    async def complete_structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[T],
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> tuple[T, LLMUsage]:
        """Return a validated instance of `schema` using constrained decoding."""
        ...
