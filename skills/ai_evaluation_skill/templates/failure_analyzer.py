"""Generalized Failure Analyzer, Root Cause Diagnostics, and Improvement Tracking."""

from __future__ import annotations

from typing import Any

from .models import EvalResult, FailureType


class GenericFailureAnalyzer:
    """
    Automates post-evaluation triage:
    - Clusters failures by taxonomy (Hallucination, Irrelevance, Incompleteness, Off-topic, Refusal).
    - Performs automated root cause analysis via score degradation patterns.
    - Generates actionable, prioritized engineering remediation plans.
    - Produces formatted Markdown & CI/CD audit logs.
    """

    def categorize_failures(self, failures: list[EvalResult]) -> dict[str, int]:
        """Aggregate failure counts grouped by failure taxonomy type."""
        summary: dict[str, int] = {}
        for f in failures:
            ftype = str(f.failure_type.value if isinstance(f.failure_type, FailureType) else (f.failure_type or "unknown"))
            summary[ftype] = summary.get(ftype, 0) + 1
        return summary

    def diagnose_root_cause(self, failure: EvalResult) -> str:
        """
        Diagnose the technical root cause of a single evaluation failure
        based on retrieval and generation score vectors.
        """
        if failure.error_message:
            return f"Runtime or provider error: {failure.error_message}"

        f = failure.faithfulness
        r = failure.relevance
        c = failure.completeness

        # Check retrieval-side causes first if metrics are available
        if failure.context_recall is not None and failure.context_recall < 0.3:
            return "Retriever recall failure: Context missed essential ground truth evidence."
        if failure.context_precision is not None and failure.context_precision < 0.2:
            return "Retriever ranking noise: Relevant chunks buried beneath irrelevant context."

        min_val = min(f, r, c)
        lowest_ties = sum(1 for v in [f, r, c] if abs(v - min_val) < 1e-4)
        if lowest_ties > 1:
            return "Compound pipeline breakdown: Multiple generation dimensions degraded simultaneously."

        if abs(f - min_val) < 1e-4:
            return "Groundedness failure (Hallucination): Generator invented facts unverified by context."
        elif abs(r - min_val) < 1e-4:
            return "Relevance failure (Off-topic/Misalignment): Response failed to target question intent."
        else:
            return "Completeness failure (Information Gap): Generator missed critical required points."

    def generate_remediation_actions(self, failures: list[EvalResult]) -> list[str]:
        """Generate a prioritized list of concrete engineering recommendations."""
        if not failures:
            return ["Pipeline healthy. No remediation required."]

        categories = self.categorize_failures(failures)
        actions: list[str] = []

        if categories.get(FailureType.HALLUCINATION.value, 0) > 0 or categories.get("hallucination", 0) > 0:
            actions.append(
                "High Priority: Implement Factual Consistency Guardrail / Strict Context Grounding Prompt constraint."
            )
        if categories.get(FailureType.INCOMPLETE.value, 0) > 0 or categories.get("incomplete", 0) > 0:
            actions.append(
                "High Priority: Increase retrieval top-k window, enrich chunk overlap, and add structured few-shot examples."
            )
        if categories.get(FailureType.IRRELEVANT.value, 0) > 0 or categories.get("irrelevant", 0) > 0:
            actions.append(
                "Medium Priority: Refine query reformulation / intent routing step to preserve core user constraints."
            )
        if categories.get(FailureType.OFF_TOPIC.value, 0) > 0 or categories.get("off_topic", 0) > 0:
            actions.append(
                "Medium Priority: Implement system prompt boundary enforcement and out-of-scope intent classifier."
            )

        # Baseline fallback remediations
        default_remediations = [
            "Audit corpus document parsing for table and list truncation.",
            "Incorporate cross-encoder reranking to improve Context Precision AP@K.",
            "Tune system prompt temperature to <= 0.2 for deterministic adherence.",
        ]
        for item in default_remediations:
            if item not in actions and len(actions) < 4:
                actions.append(item)

        return actions

    def generate_improvement_log_markdown(
        self,
        failures: list[EvalResult],
        remediations: list[str] | None = None,
    ) -> str:
        """Generate a GitHub Markdown audit table for failure tracking."""
        remediations = remediations or self.generate_remediation_actions(failures)
        headers = [
            "| Failure ID | Sample ID | Type | Root Cause Diagnosis | Recommended Fix | Status |",
            "|:-----------|:----------|:-----|:---------------------|:----------------|:-------|",
        ]
        rows: list[str] = []
        for idx, failure in enumerate(failures, start=1):
            fid = f"F{idx:03d}"
            sid = failure.qa_pair.id or f"Q{idx:02d}"
            ftype = str(failure.failure_type.value if isinstance(failure.failure_type, FailureType) else (failure.failure_type or "Failed"))
            cause = self.diagnose_root_cause(failure)
            fix = remediations[idx - 1] if idx - 1 < len(remediations) else (remediations[0] if remediations else "Investigate")
            rows.append(f"| {fid} | {sid} | `{ftype}` | {cause} | {fix} | Open |")

        return "\n".join(headers + rows)
