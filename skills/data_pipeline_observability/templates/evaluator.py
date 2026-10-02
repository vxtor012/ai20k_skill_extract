"""Multi-Tier Evaluation & Benchmark Module for RAG / AI Data Pipelines.

Implements standard IR and Generation metrics:
- Retrieval Hit Rate @ K (Document-level recall)
- Lexical Token F1 (Token overlap precision/recall/F1)
- LLM-as-a-Judge semantic accuracy & reasoning scoring
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, Sequence
import json
import logging
import re

logger = logging.getLogger("data_pipeline.evaluator")


@dataclass
class EvalTestCase:
    id: str
    question: str
    ground_truth_answer: str
    ground_truth_doc_ids: list[str]
    category: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalTestResult:
    test_id: str
    question: str
    ground_truth_answer: str
    predicted_answer: str
    retrieved_doc_ids: list[str]
    ground_truth_doc_ids: list[str]
    hit_rate: float
    token_f1: float
    judge_score: float | None = None
    judge_correct: bool | None = None
    judge_reasoning: str | None = None


@dataclass
class EvaluationMetric:
    name: str
    value: float
    description: str


@dataclass
class EvaluationReport:
    suite_name: str
    evaluated_at: datetime
    total_tests: int
    mean_hit_rate: float
    mean_token_f1: float
    mean_judge_score: float | None
    judge_accuracy: float | None
    results: list[EvalTestResult]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "evaluated_at": self.evaluated_at.isoformat(),
            "total_tests": self.total_tests,
            "metrics": {
                "mean_hit_rate": round(self.mean_hit_rate, 4),
                "mean_token_f1": round(self.mean_token_f1, 4),
                "mean_judge_score": round(self.mean_judge_score, 4) if self.mean_judge_score is not None else None,
                "judge_accuracy": round(self.judge_accuracy, 4) if self.judge_accuracy is not None else None,
            },
            "results": [
                {
                    "test_id": r.test_id,
                    "hit_rate": round(r.hit_rate, 4),
                    "token_f1": round(r.token_f1, 4),
                    "judge_score": r.judge_score,
                    "judge_correct": r.judge_correct,
                    "judge_reasoning": r.judge_reasoning,
                }
                for r in self.results
            ],
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Benchmark Evaluation Report: {self.suite_name}",
            f"**Evaluated At:** {self.evaluated_at.strftime('%Y-%m-%d %H:%M:%S UTC')} | **Total Questions:** {self.total_tests}\n",
            "### Summary Metrics",
            "| Metric | Score | Target |",
            "| :--- | :--- | :--- |",
            f"| **Retrieval Hit Rate** | `{self.mean_hit_rate:.4f}` ({self.mean_hit_rate*100:.1f}%) | `>= 0.80` |",
            f"| **Lexical Token F1** | `{self.mean_token_f1:.4f}` | `>= 0.60` |",
        ]
        if self.mean_judge_score is not None:
            lines.append(f"| **LLM Judge Score (1-5)** | `{self.mean_judge_score:.2f} / 5.0` | `>= 4.0` |")
        if self.judge_accuracy is not None:
            lines.append(f"| **Judge Accuracy** | `{self.judge_accuracy*100:.1f}%` | `>= 80%` |")

        lines.extend([
            "\n### Detailed Test Case Results",
            "| ID | Hit Rate | Token F1 | Judge Score | Correct |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ])
        for r in self.results:
            j_score = f"{r.judge_score:.1f}" if r.judge_score is not None else "N/A"
            j_corr = "✅" if r.judge_correct else ("❌" if r.judge_correct is False else "N/A")
            lines.append(f"| `{r.test_id}` | `{r.hit_rate:.2f}` | `{r.token_f1:.2f}` | `{j_score}` | {j_corr} |")

        return "\n".join(lines)


class TokenF1Calculator:
    """Calculates word-level precision, recall, and harmonic F1 score."""

    @staticmethod
    def normalize_text(text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        return " ".join(text.split())

    @classmethod
    def compute(cls, reference: str, prediction: str) -> float:
        ref_tokens = cls.normalize_text(reference).split()
        pred_tokens = cls.normalize_text(prediction).split()

        if not ref_tokens or not pred_tokens:
            return 0.0

        ref_set = set(ref_tokens)
        pred_set = set(pred_tokens)
        overlap = len(ref_set & pred_set)

        if overlap == 0:
            return 0.0

        precision = overlap / len(pred_tokens)
        recall = overlap / len(ref_tokens)
        return (2 * precision * recall) / (precision + recall)


class LLMJudgeEvaluator:
    """Evaluates semantic fidelity and correctness using an LLM evaluator."""

    def __init__(self, llm_callable: Any | None = None):
        self.llm_callable = llm_callable

    def evaluate(self, question: str, ground_truth: str, prediction: str) -> tuple[float, bool, str]:
        """Returns (score_1_to_5, is_correct, reasoning)."""
        if self.llm_callable is None:
            # Fallback heuristic judge when LLM is unavailable
            f1 = TokenF1Calculator.compute(ground_truth, prediction)
            score = 1.0 + min(4.0, f1 * 4.0)
            return score, f1 >= 0.5, f"Heuristic F1 estimate: {f1:.2f}"

        prompt = f"""You are an expert AI evaluator. Compare the predicted answer with the ground truth.
Question: {question}
Ground Truth: {ground_truth}
Predicted Answer: {prediction}

Evaluate on:
1. Material factual accuracy
2. Completeness

Output format in JSON:
{{"score": 1-5, "correct": true/false, "reasoning": "short explanation"}}"""

        fallback_reason = "LLM judge returned an invalid response."
        try:
            raw_response = self.llm_callable(prompt)
            # Simple JSON parse or fallback
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return float(data.get("score", 3.0)), bool(data.get("correct", False)), str(data.get("reasoning", ""))
        except Exception as e:
            logger.warning(f"LLM Judge execution error: {e}")
            fallback_reason = f"LLM judge failed: {e}"

        f1 = TokenF1Calculator.compute(ground_truth, prediction)
        return 1.0 + f1 * 4.0, f1 >= 0.5, f"Fallback estimate: {fallback_reason}"


class PipelineEvaluator:
    """Master Evaluator executing full benchmark suite against RAG / QA systems."""

    def __init__(self, judge: LLMJudgeEvaluator | None = None):
        self.judge = judge or LLMJudgeEvaluator()

    def evaluate_suite(
        self,
        test_cases: Sequence[EvalTestCase],
        qa_system_fn: Any,  # Callable[[str], tuple[str, list[str]]] -> (answer, retrieved_ids)
        suite_name: str = "baseline_benchmark",
    ) -> EvaluationReport:
        results: list[EvalTestResult] = []

        for tc in test_cases:
            try:
                pred_answer, retrieved_ids = qa_system_fn(tc.question)
            except Exception as e:
                logger.error(f"Error evaluating test case {tc.id}: {e}")
                pred_answer, retrieved_ids = f"Error: {e}", []

            # 1. Retrieval Hit Rate (Recall@K)
            gt_set = set(tc.ground_truth_doc_ids)
            ret_set = set(retrieved_ids)
            hit = 1.0 if len(gt_set & ret_set) > 0 else 0.0

            # 2. Token F1
            f1 = TokenF1Calculator.compute(tc.ground_truth_answer, pred_answer)

            # 3. LLM Judge
            j_score, j_corr, j_reason = self.judge.evaluate(
                question=tc.question,
                ground_truth=tc.ground_truth_answer,
                prediction=pred_answer,
            )

            results.append(
                EvalTestResult(
                    test_id=tc.id,
                    question=tc.question,
                    ground_truth_answer=tc.ground_truth_answer,
                    predicted_answer=pred_answer,
                    retrieved_doc_ids=retrieved_ids,
                    ground_truth_doc_ids=tc.ground_truth_doc_ids,
                    hit_rate=hit,
                    token_f1=f1,
                    judge_score=j_score,
                    judge_correct=j_corr,
                    judge_reasoning=j_reason,
                )
            )

        mean_hit = sum(r.hit_rate for r in results) / len(results) if results else 0.0
        mean_f1 = sum(r.token_f1 for r in results) / len(results) if results else 0.0
        judge_scores = [r.judge_score for r in results if r.judge_score is not None]
        mean_judge = sum(judge_scores) / len(judge_scores) if judge_scores else None
        judge_corrects = [r.judge_correct for r in results if r.judge_correct is not None]
        judge_acc = sum(1 for c in judge_corrects if c) / len(judge_corrects) if judge_corrects else None

        return EvaluationReport(
            suite_name=suite_name,
            evaluated_at=datetime.now(timezone.utc),
            total_tests=len(results),
            mean_hit_rate=mean_hit,
            mean_token_f1=mean_f1,
            mean_judge_score=mean_judge,
            judge_accuracy=judge_acc,
            results=results,
        )
