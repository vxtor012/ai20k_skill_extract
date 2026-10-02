"""Generalized Benchmark Runner, CI/CD Quality Gates, and Regression Testing."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from .evaluator_core import GenericRAGEvaluator
from .models import BenchmarkSummary, EvalResult, QAPair, RegressionReport


class GenericBenchmarkRunner:
    """
    Orchestrates end-to-end evaluation runs, report generation,
    and regression testing against baseline checkpoints.
    """

    def __init__(self, evaluator: GenericRAGEvaluator | None = None) -> None:
        self.evaluator = evaluator or GenericRAGEvaluator()

    def run_benchmark(
        self,
        qa_pairs: list[QAPair],
        inference_fn: Callable[[str], str | tuple[str, list[str]]],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[EvalResult]:
        """
        Execute evaluation against an inference target function.
        inference_fn can return either:
        - `actual_answer: str`
        - `(actual_answer: str, retrieved_contexts: list[str])`
        """
        results: list[EvalResult] = []
        total = len(qa_pairs)

        for idx, pair in enumerate(qa_pairs, start=1):
            if progress_callback:
                progress_callback(idx, total, pair.question)

            start_t = time.perf_counter()
            error_msg: str | None = None
            actual_answer = ""
            retrieved_contexts: list[str] | None = None

            try:
                raw_out = inference_fn(pair.question)
                if isinstance(raw_out, tuple):
                    actual_answer, retrieved_contexts = raw_out
                else:
                    actual_answer = str(raw_out)
            except Exception as exc:
                error_msg = str(exc)

            latency = round(time.perf_counter() - start_t, 3)

            eval_res = self.evaluator.evaluate_sample(
                qa_pair=pair,
                actual_answer=actual_answer,
                retrieved_contexts=retrieved_contexts,
                latency_seconds=latency,
                error_message=error_msg,
            )
            results.append(eval_res)

        return results

    def generate_summary(self, results: list[EvalResult]) -> BenchmarkSummary:
        """Aggregate evaluation results into summary metrics and difficulty breakdowns."""
        total = len(results)
        if total == 0:
            return BenchmarkSummary(
                total=0,
                passed=0,
                pass_rate=0.0,
                avg_faithfulness=0.0,
                avg_relevance=0.0,
                avg_completeness=0.0,
                avg_context_recall=None,
                avg_context_precision=None,
                overall_score=0.0,
                failure_types={},
                difficulty_breakdown={},
            )

        passed_count = sum(1 for r in results if r.passed)
        avg_f = sum(r.faithfulness for r in results) / total
        avg_r = sum(r.relevance for r in results) / total
        avg_c = sum(r.completeness for r in results) / total
        overall_score = (avg_f + avg_r + avg_c) / 3.0

        recalls = [r.context_recall for r in results if r.context_recall is not None]
        precisions = [r.context_precision for r in results if r.context_precision is not None]

        avg_recall = (sum(recalls) / len(recalls)) if recalls else None
        avg_precision = (sum(precisions) / len(precisions)) if precisions else None

        failure_types: dict[str, int] = {}
        diff_stats: dict[str, dict[str, Any]] = {}

        for r in results:
            if not r.passed and r.failure_type:
                ftype = str(r.failure_type.value if hasattr(r.failure_type, "value") else r.failure_type)
                failure_types[ftype] = failure_types.get(ftype, 0) + 1

            diff = str(r.qa_pair.difficulty or "medium").lower()
            if diff not in diff_stats:
                diff_stats[diff] = {"total": 0, "passed": 0, "scores": []}
            diff_stats[diff]["total"] += 1
            if r.passed:
                diff_stats[diff]["passed"] += 1
            diff_stats[diff]["scores"].append(r.overall_score())

        breakdown: dict[str, dict[str, float]] = {}
        for diff, stats in diff_stats.items():
            breakdown[diff] = {
                "total": stats["total"],
                "pass_rate": round(stats["passed"] / stats["total"], 3),
                "avg_score": round(sum(stats["scores"]) / stats["total"], 3),
            }

        return BenchmarkSummary(
            total=total,
            passed=passed_count,
            pass_rate=round(passed_count / total, 3),
            avg_faithfulness=round(avg_f, 3),
            avg_relevance=round(avg_r, 3),
            avg_completeness=round(avg_c, 3),
            avg_context_recall=round(avg_recall, 3) if avg_recall is not None else None,
            avg_context_precision=round(avg_precision, 3) if avg_precision is not None else None,
            overall_score=round(overall_score, 3),
            failure_types=failure_types,
            difficulty_breakdown=breakdown,
        )

    def check_quality_gate(
        self,
        summary: BenchmarkSummary,
        min_pass_rate: float = 0.80,
        min_faithfulness: float = 0.70,
        min_relevance: float = 0.70,
    ) -> tuple[bool, list[str]]:
        """Validate if evaluation summary satisfies deployment quality gate thresholds."""
        violations: list[str] = []
        if summary.pass_rate < min_pass_rate:
            violations.append(f"Pass rate {summary.pass_rate:.1%} is below minimum threshold {min_pass_rate:.1%}")
        if summary.avg_faithfulness < min_faithfulness:
            violations.append(f"Average Faithfulness {summary.avg_faithfulness:.3f} < {min_faithfulness:.3f}")
        if summary.avg_relevance < min_relevance:
            violations.append(f"Average Relevance {summary.avg_relevance:.3f} < {min_relevance:.3f}")

        return (len(violations) == 0, violations)

    def compare_regression(
        self,
        candidate_summary: BenchmarkSummary,
        baseline_summary: BenchmarkSummary,
        max_allowable_drop: float = 0.05,
    ) -> RegressionReport:
        """
        Compare candidate evaluation against baseline. Flag regression if any key metric
        degrades by more than max_allowable_drop.
        """
        regressions: list[str] = []
        deltas: dict[str, float] = {
            "pass_rate": round(candidate_summary.pass_rate - baseline_summary.pass_rate, 3),
            "faithfulness": round(candidate_summary.avg_faithfulness - baseline_summary.avg_faithfulness, 3),
            "relevance": round(candidate_summary.avg_relevance - baseline_summary.avg_relevance, 3),
            "completeness": round(candidate_summary.avg_completeness - baseline_summary.avg_completeness, 3),
            "overall_score": round(candidate_summary.overall_score - baseline_summary.overall_score, 3),
        }

        for metric_name, delta in deltas.items():
            if delta < -max_allowable_drop:
                regressions.append(f"{metric_name} dropped by {abs(delta):.3f} (tolerance: {max_allowable_drop})")

        return RegressionReport(
            passed=len(regressions) == 0,
            regressions=regressions,
            delta_metrics=deltas,
            candidate_summary=candidate_summary.__dict__,
            baseline_summary=baseline_summary.__dict__,
        )
