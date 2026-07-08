"""Google Gemini implementation of the LLMProvider protocol ($0 free tier).

Structured generation uses Gemini's native structured output
(`responseMimeType="application/json"` + `responseSchema`), preserving decision
D5: planner/semantic outputs are schema-valid by construction, never regex-parsed.
Wired for real in Phase 2/3. A token-bucket queue + exponential backoff on 429s
and the semantic response cache (Phase 3) keep demo traffic inside free-tier
quota. Free-tier privacy caveat: inputs may be used to improve Google's models,
so the hosted demo runs on synthetic sample data only — see README §Privacy.
"""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.core.config import get_settings
from app.services.llm.base import LLMResult, LLMUsage

T = TypeVar("T", bound=BaseModel)

# Free tier = $0. These per-1M-token prices only matter on a bring-your-own paid
# key; verify current numbers in Google AI Studio before using for billing.
_PRICE_TABLE: dict[str, tuple[float, float]] = {
    "gemini-3-flash": (0.0, 0.0),
    "gemini-3.5-flash": (0.0, 0.0),
    "gemini-3.1-flash-lite": (0.0, 0.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    inp, out = _PRICE_TABLE.get(model, (0.0, 0.0))
    return round((input_tokens / 1e6) * inp + (output_tokens / 1e6) * out, 6)


class GeminiProvider:
    """Thin wrapper around the official `google-genai` SDK."""

    def __init__(self, api_key: str | None = None, default_model: str | None = None) -> None:
        s = get_settings()
        self._api_key = api_key or s.google_api_key
        self._default_model = default_model or s.llm_model_planner
        self._client = None

    def _get_client(self):  # pragma: no cover - needs a live key
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def complete(
        self, *, system: str, prompt: str, model: str | None = None, max_tokens: int = 1024
    ) -> LLMResult:
        import asyncio

        from google.genai import types

        def _call() -> LLMResult:  # pragma: no cover - needs a live key
            client = self._get_client()
            used = model or self._default_model
            resp = client.models.generate_content(
                model=used,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system, max_output_tokens=max_tokens
                ),
            )
            um = resp.usage_metadata
            return LLMResult(
                text=resp.text or "",
                usage=LLMUsage(
                    model=used,
                    input_tokens=um.prompt_token_count,
                    output_tokens=um.candidates_token_count,
                    cost_usd=estimate_cost(used, um.prompt_token_count, um.candidates_token_count),
                ),
            )

        return await asyncio.to_thread(_call)

    async def complete_structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[T],
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> tuple[T, LLMUsage]:
        import asyncio

        from google.genai import types

        def _call() -> tuple[T, LLMUsage]:  # pragma: no cover - needs a live key
            client = self._get_client()
            used = model or self._default_model
            # Structured output: constrain the model to the Pydantic schema.
            resp = client.models.generate_content(
                model=used,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=schema,
                    max_output_tokens=max_tokens,
                ),
            )
            parsed = getattr(resp, "parsed", None)
            data = parsed if isinstance(parsed, schema) else schema.model_validate_json(resp.text)
            um = resp.usage_metadata
            usage = LLMUsage(
                model=used,
                input_tokens=um.prompt_token_count,
                output_tokens=um.candidates_token_count,
                cost_usd=estimate_cost(used, um.prompt_token_count, um.candidates_token_count),
            )
            return data, usage

        return await asyncio.to_thread(_call)
