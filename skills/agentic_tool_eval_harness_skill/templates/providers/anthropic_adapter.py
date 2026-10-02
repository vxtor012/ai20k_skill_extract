from __future__ import annotations

import os
from typing import Any

from ..core.types import ModelResponse, ToolCall
from .base import to_anthropic_tool_specs


class AnthropicProvider:
    """Anthropic Claude Provider supporting Tool Calling & System extraction."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "claude-3-5-sonnet-latest",
    ) -> None:
        import anthropic
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=key)
        self.default_model = default_model

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        tool_choice: Any | None = None,
        max_tokens: int | None = 2048,
    ) -> ModelResponse:
        system_content = ""
        conversation: list[dict[str, Any]] = []

        for m in messages:
            if m.get("role") == "system":
                system_content += ("\n\n" + m["content"] if system_content else m["content"])
            else:
                conversation.append({"role": m["role"], "content": m["content"]})

        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": conversation,
            "max_tokens": max_tokens or 2048,
            "temperature": temperature,
        }
        if system_content:
            kwargs["system"] = system_content
        if tools:
            kwargs["tools"] = to_anthropic_tool_specs(tools)
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

        res = self.client.messages.create(**kwargs)
        text_parts: list[str] = []
        parsed_calls: list[ToolCall] = []

        for block in res.content:
            if getattr(block, "type", "") == "text":
                text_parts.append(block.text)
            elif getattr(block, "type", "") == "tool_use":
                parsed_calls.append(
                    ToolCall(
                        name=block.name,
                        args=block.input if isinstance(block.input, dict) else {},
                        call_id=block.id,
                    )
                )

        return ModelResponse(
            text="".join(text_parts) if text_parts else None,
            tool_calls=parsed_calls,
            raw=res,
            finish_reason=res.stop_reason,
        )
