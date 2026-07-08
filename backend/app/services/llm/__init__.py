"""LLM provider factory. 'mock' keeps tests/CI free; 'gemini' is the $0 default."""
from __future__ import annotations

from app.core.config import get_settings
from app.services.llm.base import LLMProvider


def get_llm_provider() -> LLMProvider:
    provider = get_settings().llm_provider
    if provider == "gemini":
        from app.services.llm.gemini_provider import GeminiProvider

        return GeminiProvider()
    if provider == "anthropic":
        from app.services.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    from app.services.llm.mock_provider import MockProvider

    return MockProvider()
