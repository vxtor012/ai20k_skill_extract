from __future__ import annotations

import json
import os
from typing import Any

from ..core.types import ModelResponse, ToolCall
from .base import to_openai_tool_specs


class OpenAIProvider:
    """Standard OpenAI and OpenAI-compatible API Provider (OpenRouter, Azure, Ollama, etc.)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "gpt-4o-mini",
    ) -> None:
        from openai import OpenAI
        key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.default_model = default_model

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        tool_choice: Any | None = None,
        max_tokens: int | None = None,
    ) -> ModelResponse:
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if tools:
            kwargs["tools"] = to_openai_tool_specs(tools)
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice

        res = self.client.chat.completions.create(**kwargs)
        choice = res.choices[0]
        msg = choice.message

        parsed_calls: list[ToolCall] = []
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                fn = tc.function
                try:
                    args = json.loads(fn.arguments) if fn.arguments else {}
                except json.JSONDecodeError:
                    args = {"_raw_arguments": fn.arguments}
                parsed_calls.append(ToolCall(name=fn.name, args=args, call_id=tc.id))

        return ModelResponse(
            text=msg.content,
            tool_calls=parsed_calls,
            raw=res,
            finish_reason=choice.finish_reason,
        )
