from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from ..core.types import FailureType


@dataclass
class ExpectedToolCall:
    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class Turn:
    role: Literal["user", "assistant", "system"]
    content: str


@dataclass
class EvalCase:
    id: str
    phase: str
    failure_type: FailureType | str
    input: str | None = None
    turns: list[Turn] | list[dict[str, str]] | None = None
    expect_no_tool: bool = False
    expected_calls: list[ExpectedToolCall] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CaseEvalResult:
    case_id: str
    passed: bool
    routing_correct: bool
    args_correct: bool
    observed_mismatch: str | None
    failure_type: str | None
    failures: list[str] = field(default_factory=list)
    actual_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    actual_text: str | None = None


@dataclass
class SuiteMetrics:
    total_cases: int = 0
    passed_cases: int = 0
    pass_rate: float = 0.0
    routing_correct: int = 0
    routing_accuracy: float = 0.0
    args_correct: int = 0
    args_accuracy: float = 0.0
    extra_calls_cases: int = 0
    extra_calls_rate: float = 0.0
    failure_distribution: dict[str, int] = field(default_factory=dict)
