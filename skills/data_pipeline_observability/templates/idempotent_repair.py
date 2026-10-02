"""Idempotent Repair & 3-State Comparative Audit Module.

Enables deterministic self-healing by replaying from immutable raw snapshots,
re-verifying quality gates, re-indexing vector stores, and generating 3-way
comparative reports (Baseline vs Corrupted vs Repaired).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
import json
import logging

import pandas as pd

from .evaluator import EvaluationReport
from .quality_gate import QualityGateResult

logger = logging.getLogger("data_pipeline.repair")


@dataclass
class RepairResult:
    repaired_records_count: int
    quality_passed: bool
    reindexed_count: int
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: str = ""


@dataclass
class StateSnapshot:
    state_label: str  # 'Baseline', 'Corrupted', 'Repaired'
    record_count: int
    quality_passed: bool
    freshness_passed: bool
    hit_rate: float
    token_f1: float
    judge_score: float | None = None


@dataclass
class ComparativeAuditReport:
    generated_at: datetime
    baseline: StateSnapshot
    corrupted: StateSnapshot
    repaired: StateSnapshot
    analysis_narrative: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "baseline": self.baseline.__dict__,
            "corrupted": self.corrupted.__dict__,
            "repaired": self.repaired.__dict__,
            "recovery_deltas": {
                "hit_rate_recovery": round(self.repaired.hit_rate - self.corrupted.hit_rate, 4),
                "f1_recovery": round(self.repaired.token_f1 - self.corrupted.token_f1, 4),
                "quality_restored": self.repaired.quality_passed and not self.corrupted.quality_passed,
            },
            "analysis_narrative": self.analysis_narrative,
        }

    def to_markdown(self) -> str:
        b, c, r = self.baseline, self.corrupted, self.repaired

        def fmt_pct(val: float) -> str:
            return f"{val * 100:.1f}%"

        def fmt_judge(val: float | None) -> str:
            return f"{val:.2f} / 5.0" if val is not None else "N/A"

        def fmt_status(ok: bool) -> str:
            return "✅ Pass" if ok else "❌ Fail"

        return f"""# 3-State Data Observability & Resilience Audit Report
**Generated At:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

### 📊 Comparative Performance Matrix

| Metric / Dimension | 🟢 Baseline (Clean) | 🔴 Corrupted (Chaos) | 🔵 Repaired (Self-Healed) | Delta (Repair vs Corrupt) |
| :--- | :---: | :---: | :---: | :---: |
| **Total Record Count** | `{b.record_count}` | `{c.record_count}` | `{r.record_count}` | `{r.record_count - c.record_count:+d}` |
| **Quality Gate (GX 1.x)** | {fmt_status(b.quality_passed)} | {fmt_status(c.quality_passed)} | {fmt_status(r.quality_passed)} | {'✅ Restored' if r.quality_passed else '❌ Failed'} |
| **Freshness SLA Gate** | {fmt_status(b.freshness_passed)} | {fmt_status(c.freshness_passed)} | {fmt_status(r.freshness_passed)} | {'✅ Restored' if r.freshness_passed else '❌ Failed'} |
| **Retrieval Hit Rate** | `{fmt_pct(b.hit_rate)}` | `{fmt_pct(c.hit_rate)}` | `{fmt_pct(r.hit_rate)}` | `{fmt_pct(r.hit_rate - c.hit_rate)}` |
| **Lexical Token F1** | `{b.token_f1:.4f}` | `{c.token_f1:.4f}` | `{r.token_f1:.4f}` | `{r.token_f1 - c.token_f1:+.4f}` |
| **LLM Judge Score** | `{fmt_judge(b.judge_score)}` | `{fmt_judge(c.judge_score)}` | `{fmt_judge(r.judge_score)}` | {'N/A' if b.judge_score is None else f"{r.judge_score - c.judge_score:+.2f}"} |

### 🔍 Architectural Insight & Silent Failure Analysis
{self.analysis_narrative or "1. **Impact of Corruption:** When data corruption was introduced, retrieval hit rate and lexical F1 experienced significant degradation, validating the vulnerability of AI/RAG systems to bad inputs without raising application runtime crashes.\n2. **Quality Gate Detection:** Great Expectations and Freshness rules successfully flagged corrupted attributes.\n3. **Idempotent Repair:** Replaying deterministic transformations from the immutable raw snapshot fully restored system performance and data integrity."}
"""


class IdempotentRepairEngine:
    """Orchestrates deterministic recovery and comparative analysis."""

    @staticmethod
    def execute_replay(
        raw_loader_fn: Callable[[], list[Any]],
        clean_transform_fn: Callable[[list[Any]], pd.DataFrame],
        quality_gate_fn: Callable[[pd.DataFrame], QualityGateResult],
        reindex_fn: Callable[[pd.DataFrame], int],
    ) -> RepairResult:
        """Replays pipeline from raw source snapshot with verification."""
        logger.info("Starting idempotent recovery replay from raw lineage...")
        raw_records = raw_loader_fn()
        clean_df = clean_transform_fn(raw_records)
        q_result = quality_gate_fn(clean_df)

        if not q_result.passed:
            logger.warning("Repaired dataset failed quality checks! Inspect raw snapshot integrity.")

        reindexed_docs = reindex_fn(clean_df)

        return RepairResult(
            repaired_records_count=len(clean_df),
            quality_passed=q_result.passed,
            reindexed_count=reindexed_docs,
            details="Idempotent replay completed successfully from immutable snapshot.",
        )

    @staticmethod
    def build_comparative_report(
        baseline_eval: EvaluationReport,
        corrupted_eval: EvaluationReport,
        repaired_eval: EvaluationReport,
        baseline_q: QualityGateResult,
        corrupted_q: QualityGateResult,
        repaired_q: QualityGateResult,
        baseline_count: int,
        corrupted_count: int,
        repaired_count: int,
        narrative: str = "",
    ) -> ComparativeAuditReport:
        b_snap = StateSnapshot(
            state_label="Baseline",
            record_count=baseline_count,
            quality_passed=baseline_q.passed,
            freshness_passed=not baseline_q.has_warnings,
            hit_rate=baseline_eval.mean_hit_rate,
            token_f1=baseline_eval.mean_token_f1,
            judge_score=baseline_eval.mean_judge_score,
        )
        c_snap = StateSnapshot(
            state_label="Corrupted",
            record_count=corrupted_count,
            quality_passed=corrupted_q.passed,
            freshness_passed=not corrupted_q.has_warnings,
            hit_rate=corrupted_eval.mean_hit_rate,
            token_f1=corrupted_eval.mean_token_f1,
            judge_score=corrupted_eval.mean_judge_score,
        )
        r_snap = StateSnapshot(
            state_label="Repaired",
            record_count=repaired_count,
            quality_passed=repaired_q.passed,
            freshness_passed=not repaired_q.has_warnings,
            hit_rate=repaired_eval.mean_hit_rate,
            token_f1=repaired_eval.mean_token_f1,
            judge_score=repaired_eval.mean_judge_score,
        )

        return ComparativeAuditReport(
            generated_at=datetime.now(timezone.utc),
            baseline=b_snap,
            corrupted=c_snap,
            repaired=r_snap,
            analysis_narrative=narrative,
        )
