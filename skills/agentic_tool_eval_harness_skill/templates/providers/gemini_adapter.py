from __future__ import annotations

import os
from typing import Any

from ..core.types import ModelResponse, ToolCall


class GeminiProvider:
    """Google Gemini Provider supporting structured function calling."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "gemini-2.0-flash",
    ) -> None:
        from google import genai
        key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=key)
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
        from google.genai import types

        system_instruction = None
        contents: list[types.Content] = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = content
            elif role in ("user", "assistant"):
                g_role = "user" if role == "user" else "model"
                contents.append(
                    types.Content(
                        role=g_role,
                        parts=[types.Part.from_text(text=content)],
                    )
                )

        gemini_tools = None
        if tools:
            func_decls = []
            for t in tools:
                func_decls.append(
                    types.FunctionDeclaration(
                        name=t["name"],
                        description=t.get("description", ""),
                        parameters=t.get("parameters"),
                    )
                )
            gemini_tools = [types.Tool(function_declarations=func_decls)]

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            tools=gemini_tools,
        )

        res = self.client.models.generate_content(
            model=model or self.default_model,
            contents=contents,
            config=config,
        )

        parsed_calls: list[ToolCall] = []
        if getattr(res, "function_calls", None):
            for fc in res.function_calls:
                parsed_calls.append(
                    ToolCall(
                        name=fc.name,
                        args=dict(fc.args) if fc.args else {},
                    )
                )

        return ModelResponse(
            text=res.text if hasattr(res, "text") else None,
            tool_calls=parsed_calls,
            raw=res,
        )
