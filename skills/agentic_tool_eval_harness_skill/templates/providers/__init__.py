from __future__ import annotations

import os
from typing import Literal
from ..core.types import Provider
from .anthropic_adapter import AnthropicProvider
from .gemini_adapter import GeminiProvider
from .openai_adapter import OpenAIProvider


def make_provider(
    provider_type: Literal["openai", "anthropic", "gemini", "openrouter"] | str = "openai",
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> Provider:
    """Factory creating normalized provider instances."""
    p_lower = provider_type.lower()
    if p_lower == "openai":
        return OpenAIProvider(api_key=api_key, base_url=base_url, default_model=model or "gpt-4o-mini")
    elif p_lower == "openrouter":
        return OpenAIProvider(
            api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
            base_url=base_url or "https://openrouter.ai/api/v1",
            default_model=model or "anthropic/claude-3.5-sonnet",
        )
    elif p_lower == "anthropic":
        return AnthropicProvider(api_key=api_key, default_model=model or "claude-3-5-sonnet-latest")
    elif p_lower == "gemini":
        return GeminiProvider(api_key=api_key, default_model=model or "gemini-2.0-flash")
    raise ValueError(f"Unsupported provider type: {provider_type}")


__all__ = [
    "Provider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "make_provider",
]
