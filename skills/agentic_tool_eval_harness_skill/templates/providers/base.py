from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from ..core.types import ModelResponse, Provider, ToolCall


def to_openai_tool_specs(declarations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert clean parameter schemas into OpenAI function-tool specification format."""
    specs = []
    for decl in declarations:
        specs.append({
            "type": "function",
            "function": {
                "name": decl["name"],
                "description": decl.get("description", ""),
                "parameters": decl.get("parameters", {"type": "object", "properties": {}}),
            },
        })
    return specs


def to_anthropic_tool_specs(declarations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert clean parameter schemas into Anthropic tool specification format."""
    specs = []
    for decl in declarations:
        specs.append({
            "name": decl["name"],
            "description": decl.get("description", ""),
            "input_schema": decl.get("parameters", {"type": "object", "properties": {}}),
        })
    return specs
