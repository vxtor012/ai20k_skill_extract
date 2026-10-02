"""Generic Data Models for AI & RAG Evaluation Pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    ADVERSARIAL = "adversarial"


class FailureType(str, Enum):
    HALLUCINATION = "hallucination"
    IRRELEVANT = "irrelevant"
    INCOMPLETE = "incomplete"
    OFF_TOPIC = "off_topic"
    REFUSAL = "refusal"
    TIMEOUT_OR_ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class EvidenceContext:
    """Represents a piece of evidence supporting ground truth or retrieval."""
    source_doc: str
    text: str
    score: float | None = None
    rank: int | None = None


@dataclass
class QAPair:
    """A standardized Question-Answer test case in a Golden Benchmark Dataset."""
    question: str
    expected_answer: str
    context: str | None = ""
    id: str | None = None
    difficulty: str | DifficultyLevel = DifficultyLevel.MEDIUM
    attack_type: str | None = None
    contexts: list[EvidenceContext] = field(default_factory=list)
    retrieved_contexts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """Comprehensive evaluation result for a single evaluation unit."""
    qa_pair: QAPair
    actual_answer: str
    faithfulness: float
    relevance: float
    completeness: float
    passed: bool
    failure_type: str | FailureType | None = None
    context_precision: float | None = None
    context_recall: float | None = None
    judge_scores: dict[str, float] = field(default_factory=dict)
    judge_reasoning: str | None = None
    latency_seconds: float | None = None
    error_message: str | None = None

    def overall_score(self) -> float:
        """Compute the composite generation quality score (mean of answer-side metrics)."""
        return (self.faithfulness + self.relevance + self.completeness) / 3.0


@dataclass
class BenchmarkSummary:
    """Aggregated metrics across a benchmark evaluation suite."""
    total: int
    passed: int
    pass_rate: float
    avg_faithfulness: float
    avg_relevance: float
    avg_completeness: float
    avg_context_recall: float | None
    avg_context_precision: float | None
    overall_score: float
    failure_types: dict[str, int] = field(default_factory=dict)
    difficulty_breakdown: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class RegressionReport:
    """Comparative report between a candidate run and a baseline checkpoint."""
    passed: bool
    regressions: list[str]
    delta_metrics: dict[str, float]
    candidate_summary: dict[str, Any]
    baseline_summary: dict[str, Any]
