"""Deterministic mock provider so the app + tests run with zero API cost."""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.services.llm.base import LLMResult, LLMUsage

T = TypeVar("T", bound=BaseModel)


class MockProvider:
    async def complete(
        self, *, system: str, prompt: str, model: str | None = None, max_tokens: int = 1024
    ) -> LLMResult:
        return LLMResult(
            text=f"[mock] {prompt[:64]}",
            usage=LLMUsage(
                model="mock", input_tokens=0, output_tokens=0, cost_usd=0.0, cache_hit=False
            ),
        )

    async def complete_structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[T],
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> tuple[T, LLMUsage]:
        raise NotImplementedError("Mock structured generation is added in Phase 2")
