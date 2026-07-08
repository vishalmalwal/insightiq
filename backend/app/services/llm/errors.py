"""LLM-layer errors."""
from __future__ import annotations

from app.core.errors import AppError


class LLMError(AppError):
    code = "llm_error"


class RateLimitError(LLMError):
    status_code = 429
    code = "rate_limited"
