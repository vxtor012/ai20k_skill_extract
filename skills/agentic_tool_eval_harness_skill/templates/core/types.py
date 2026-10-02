from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Generic, Literal, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


class FailureType(str, Enum):
    WRONG_TOOL = "wrong_tool"
    WRONG_ARG_VALUE = "wrong_arg_value"
    WRONG_BOUNDARY = "wrong_boundary"
    UNNECESSARY_TOOL = "unnecessary_tool"
    OUT_OF_SCOPE = "out_of_scope"
    MISSING_INFO = "missing_info"
    SAFETY_VIOLATION = "safety_violation"
    EXECUTION_ERROR = "execution_error"


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict[str, Any]
    call_id: str | None = None


@dataclass
class ModelResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any | None = None
    finish_reason: str | None = None


@dataclass
class ToolResult:
    tool: str
    args: dict[str, Any]
    result: Any | None = None
    error: str | None = None
    is_clarification: bool = False
    awaiting_user: bool = False
    question: str | None = None


@dataclass
class AgentRun:
    status: Literal["answered", "waiting_for_user", "max_tool_rounds", "error"]
    assistant_text: str | None
    rounds: list[dict[str, Any]] = field(default_factory=list)
    tool_events: list[ToolResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArtifactManifest:
    version: str
    prompt_hash: str
    tools_hash: str
    timestamp: str
    extra_hashes: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class Provider(Protocol):
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
        """Execute completion and return standardized ModelResponse."""
        ...
