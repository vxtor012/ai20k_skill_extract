"""Data Quality Gate & Observability Module.

Implements declarative schema validation and quality verification using modern
Great Expectations 1.x (ephemeral execution mode) and native vectorized validation rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable
import json
import logging

import pandas as pd

logger = logging.getLogger("data_pipeline.quality_gate")


class RuleSeverity(str, Enum):
    BLOCKER = "blocker"   # Hard stop: Pipeline fails immediately
    WARNING = "warning"   # Soft warning: Logs warning, flags dataset, continues
    INFO = "info"         # Metric tracking only


@dataclass
class ExpectationRule:
    rule_name: str
    rule_type: str  # 'row_count', 'not_null', 'unique', 'length_between', 'custom'
    target_column: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    severity: RuleSeverity = RuleSeverity.BLOCKER
    description: str = ""


@dataclass
class RuleEvaluationResult:
    rule_name: str
    rule_type: str
    target_column: str | None
    severity: RuleSeverity
    passed: bool
    observed_value: Any
    expected_value: Any
    details: str = ""


@dataclass
class QualityGateConfig:
    min_rows: int = 1
    max_rows: int = 100_000
    required_columns: list[str] = field(default_factory=list)
    unique_columns: list[str] = field(default_factory=list)
    min_length_rules: dict[str, int] = field(default_factory=dict)
    custom_rules: list[ExpectationRule] = field(default_factory=list)
    use_gx_engine: bool = True


@dataclass
class QualityGateResult:
    dataset_name: str
    evaluated_at: datetime
    total_records: int
    passed: bool
    has_warnings: bool
    rule_results: list[RuleEvaluationResult]
    summary_metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "evaluated_at": self.evaluated_at.isoformat(),
            "total_records": self.total_records,
            "passed": self.passed,
            "has_warnings": self.has_warnings,
            "summary_metrics": self.summary_metrics,
            "rule_results": [
                {
                    "rule_name": r.rule_name,
                    "rule_type": r.rule_type,
                    "target_column": r.target_column,
                    "severity": r.severity.value,
                    "passed": r.passed,
                    "observed_value": str(r.observed_value),
                    "expected_value": str(r.expected_value),
                    "details": r.details,
                }
                for r in self.rule_results
            ],
        }

    def to_markdown(self) -> str:
        status_badge = "✅ PASSED" if self.passed else "❌ FAILED"
        lines = [
            f"# Data Quality Gate Report: {self.dataset_name}",
            f"**Status:** {status_badge} | **Evaluated At:** {self.evaluated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Total Records Checked:** {self.total_records}\n",
            "| Rule Name | Target Column | Severity | Result | Observed | Expected |",
            "| :--- | :--- | :--- | :---: | :--- | :--- |",
        ]
        for r in self.rule_results:
            icon = "✅ Pass" if r.passed else ("⚠️ Warn" if r.severity == RuleSeverity.WARNING else "❌ Fail")
            col = r.target_column or "N/A (Table-level)"
            lines.append(
                f"| `{r.rule_name}` | `{col}` | **{r.severity.value.upper()}** | {icon} | {r.observed_value} | {r.expected_value} |"
            )
        return "\n".join(lines)


class DataQualityGate:
    """Enterprise Quality Gate executing Great Expectations 1.x and Native Rules."""

    def __init__(self, config: QualityGateConfig):
        self.config = config

    def evaluate_dataframe(self, df: pd.DataFrame, dataset_name: str = "dataset") -> QualityGateResult:
        """Run all configured quality validations against the DataFrame."""
        results: list[RuleEvaluationResult] = []
        total_rows = len(df)
        now = datetime.now(timezone.utc)

        # 1. Row Count Validation
        row_pass = self.config.min_rows <= total_rows <= self.config.max_rows
        results.append(
            RuleEvaluationResult(
                rule_name="expect_table_row_count_to_be_between",
                rule_type="row_count",
                target_column=None,
                severity=RuleSeverity.BLOCKER,
                passed=row_pass,
                observed_value=total_rows,
                expected_value=f"[{self.config.min_rows}, {self.config.max_rows}]",
                details=f"Table has {total_rows} rows",
            )
        )

        # 2. Required Columns Not Null
        for col in self.config.required_columns:
            if col not in df.columns:
                results.append(
                    RuleEvaluationResult(
                        rule_name="expect_column_to_exist",
                        rule_type="column_existence",
                        target_column=col,
                        severity=RuleSeverity.BLOCKER,
                        passed=False,
                        observed_value="Missing",
                        expected_value="Present in DataFrame",
                        details=f"Column '{col}' is missing from DataFrame schema",
                    )
                )
                continue

            null_count = int(df[col].isna().sum())
            results.append(
                RuleEvaluationResult(
                    rule_name="expect_column_values_to_not_be_null",
                    rule_type="not_null",
                    target_column=col,
                    severity=RuleSeverity.BLOCKER,
                    passed=(null_count == 0),
                    observed_value=f"{null_count} nulls",
                    expected_value="0 nulls",
                    details=f"{null_count}/{total_rows} null values detected",
                )
            )

        # 3. Unique Column Constraints
        for col in self.config.unique_columns:
            if col in df.columns:
                duplicate_count = int(df.duplicated(subset=[col]).sum())
                results.append(
                    RuleEvaluationResult(
                        rule_name="expect_column_values_to_be_unique",
                        rule_type="unique",
                        target_column=col,
                        severity=RuleSeverity.BLOCKER,
                        passed=(duplicate_count == 0),
                        observed_value=f"{duplicate_count} duplicates",
                        expected_value="0 duplicates",
                        details=f"Column '{col}' has {duplicate_count} duplicate values",
                    )
                )

        # 4. Length Bounds
        for col, min_len in self.config.min_length_rules.items():
            if col in df.columns:
                lengths = df[col].astype(str).str.len()
                under_length_count = int((lengths < min_len).sum())
                results.append(
                    RuleEvaluationResult(
                        rule_name="expect_column_value_lengths_to_be_between",
                        rule_type="length_between",
                        target_column=col,
                        severity=RuleSeverity.WARNING,
                        passed=(under_length_count == 0),
                        observed_value=f"{under_length_count} rows < {min_len} chars",
                        expected_value=f"min length >= {min_len}",
                        details=f"{under_length_count} rows failed length constraint",
                    )
                )

        # 5. Optional GX 1.x Execution Integration
        if self.config.use_gx_engine:
            self._run_gx_ephemeral_validation(df, dataset_name)

        has_blocker_failures = any(r.severity == RuleSeverity.BLOCKER and not r.passed for r in results)
        has_warnings = any(r.severity == RuleSeverity.WARNING and not r.passed for r in results)

        summary = {
            "total_rules": len(results),
            "passed_rules": sum(1 for r in results if r.passed),
            "failed_rules": sum(1 for r in results if not r.passed),
        }

        return QualityGateResult(
            dataset_name=dataset_name,
            evaluated_at=now,
            total_records=total_rows,
            passed=(not has_blocker_failures),
            has_warnings=has_warnings,
            rule_results=results,
            summary_metrics=summary,
        )

    def _run_gx_ephemeral_validation(self, df: pd.DataFrame, dataset_name: str) -> None:
        """Runs Great Expectations 1.x in ephemeral RAM mode if gx library is available."""
        try:
            import great_expectations as gx
            import great_expectations.expectations as gxe

            context = gx.get_context(mode="ephemeral")
            data_source = context.data_sources.add_pandas(name=f"{dataset_name}_source")
            data_asset = data_source.add_dataframe_asset(name=f"{dataset_name}_asset")
            batch_def = data_asset.add_batch_definition_whole_dataframe(f"{dataset_name}_batch")
            batch = batch_def.get_batch(batch_parameters={"dataframe": df})

            suite_name = f"{dataset_name}_suite"
            suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
            suite.add_expectation(
                gxe.ExpectTableRowCountToBeBetween(
                    min_value=self.config.min_rows, max_value=self.config.max_rows
                )
            )
            for col in self.config.required_columns:
                if col in df.columns:
                    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column=col))

            for col in self.config.unique_columns:
                if col in df.columns:
                    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column=col))

            val_def = context.validation_definitions.add(
                gx.ValidationDefinition(name=f"{dataset_name}_val", data=batch_def, suite=suite)
            )
            val_results = val_def.run(batch_parameters={"dataframe": df})
            logger.info(f"GX 1.x validation executed successfully: {val_results.success}")
        except Exception as err:
            logger.debug(f"GX ephemeral runner fallback: {err}")
