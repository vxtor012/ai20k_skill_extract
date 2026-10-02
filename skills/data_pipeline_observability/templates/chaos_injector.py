"""Data Chaos Engineering & Fault Injection Suite.

Simulates real-world data corruption, schema drift, sensor anomalies, and scraper failures
to validate observability alerts, quality gates, and system recovery resilience.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable
import json
import logging
import random

import pandas as pd

logger = logging.getLogger("data_pipeline.chaos")


class CorruptionScenario(str, Enum):
    DROP_LATEST = "drop_latest_records"       # Ingestion failure: Missing recent stream
    BLANK_FIELD = "blank_mandatory_field"     # Extraction failure: Null or empty body
    INJECT_NOISE = "inject_text_noise"        # Scraping failure: Garbage tokens/encoding issues
    TRUNCATE_FIELD = "truncate_identifier"     # Parser failure: Truncated headers/titles
    STALE_TIMESTAMP = "stale_timestamp"       # Sync failure: Outdated timestamps
    DUPLICATE_ROWS = "duplicate_records"      # CDC failure: Duplicate replay


@dataclass
class CorruptionPlan:
    drop_ratio: float = 0.2
    blank_ratio: float = 0.15
    noise_ratio: float = 0.15
    truncate_ratio: float = 0.15
    stale_days_offset: int = 365
    stale_ratio: float = 0.25
    duplicate_ratio: float = 0.15
    seed: int = 42


@dataclass
class InjectedFault:
    scenario: CorruptionScenario
    affected_rows: int
    target_columns: list[str]
    details: str


@dataclass
class CorruptionReport:
    original_row_count: int
    corrupted_row_count: int
    injected_faults: list[InjectedFault]
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "executed_at": self.executed_at.isoformat(),
            "original_row_count": self.original_row_count,
            "corrupted_row_count": self.corrupted_row_count,
            "injected_faults": [
                {
                    "scenario": f.scenario.value,
                    "affected_rows": f.affected_rows,
                    "target_columns": f.target_columns,
                    "details": f.details,
                }
                for f in self.injected_faults
            ],
        }


class ChaosDataInjector:
    """Controlled Chaos Engine for Data Pipelines and RAG Systems."""

    def __init__(self, plan: CorruptionPlan | None = None):
        self.plan = plan or CorruptionPlan()

    def corrupt(
        self,
        df: pd.DataFrame,
        id_column: str = "id",
        text_column: str = "text",
        timestamp_column: str = "published",
        title_column: str | None = "title",
        rebuild_embedding_fn: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
    ) -> tuple[pd.DataFrame, CorruptionReport]:
        """Apply a battery of controlled corruption scenarios to the DataFrame."""
        random.seed(self.plan.seed)
        faults: list[InjectedFault] = []
        original_count = len(df)
        corrupted = df.copy()

        # 1. Drop Latest Records (Simulate missing stream)
        if timestamp_column in corrupted.columns and len(corrupted) > 4:
            sorted_df = corrupted.sort_values(by=timestamp_column, ascending=False)
            drop_k = max(1, int(len(corrupted) * self.plan.drop_ratio))
            corrupted = sorted_df.iloc[drop_k:].reset_index(drop=True)
            faults.append(
                InjectedFault(
                    scenario=CorruptionScenario.DROP_LATEST,
                    affected_rows=drop_k,
                    target_columns=[timestamp_column],
                    details=f"Dropped {drop_k} most recent records",
                )
            )

        # 2. Blank Mandatory Field (Summary / Body)
        if text_column in corrupted.columns and len(corrupted) > 0:
            sample_indices = corrupted.sample(frac=self.plan.blank_ratio, random_state=self.plan.seed).index
            corrupted.loc[sample_indices, text_column] = ""
            faults.append(
                InjectedFault(
                    scenario=CorruptionScenario.BLANK_FIELD,
                    affected_rows=len(sample_indices),
                    target_columns=[text_column],
                    details=f"Blanked {len(sample_indices)} records in column '{text_column}'",
                )
            )

        # 3. Inject Noise (Corrupted characters / malformed tokens)
        if text_column in corrupted.columns and len(corrupted) > 0:
            sample_indices = corrupted.sample(frac=self.plan.noise_ratio, random_state=self.plan.seed + 1).index
            noise_tokens = " [CORRUPTED_TOKEN_#@$% 0xDEADBEEF] "
            corrupted.loc[sample_indices, text_column] = corrupted.loc[sample_indices, text_column].apply(
                lambda val: f"{val}{noise_tokens * 3}" if isinstance(val, str) else noise_tokens
            )
            faults.append(
                InjectedFault(
                    scenario=CorruptionScenario.INJECT_NOISE,
                    affected_rows=len(sample_indices),
                    target_columns=[text_column],
                    details=f"Appended noisy artifacts to {len(sample_indices)} records",
                )
            )

        # 4. Truncate Title/Header
        if title_column and title_column in corrupted.columns and len(corrupted) > 0:
            sample_indices = corrupted.sample(frac=self.plan.truncate_ratio, random_state=self.plan.seed + 2).index
            corrupted.loc[sample_indices, title_column] = corrupted.loc[sample_indices, title_column].apply(
                lambda val: str(val)[:6] if val else "Trun"
            )
            faults.append(
                InjectedFault(
                    scenario=CorruptionScenario.TRUNCATE_FIELD,
                    affected_rows=len(sample_indices),
                    target_columns=[title_column],
                    details=f"Truncated title to 6 characters for {len(sample_indices)} rows",
                )
            )

        # 5. Stale Timestamps (Age tampering)
        if timestamp_column in corrupted.columns and len(corrupted) > 0:
            sample_indices = corrupted.sample(frac=self.plan.stale_ratio, random_state=self.plan.seed + 3).index
            shift = timedelta(days=self.plan.stale_days_offset)
            corrupted.loc[sample_indices, timestamp_column] = pd.to_datetime(
                corrupted.loc[sample_indices, timestamp_column], errors="coerce", utc=True
            ).apply(lambda dt: (dt - shift).strftime("%Y-%m-%d") if pd.notnull(dt) else dt)
            faults.append(
                InjectedFault(
                    scenario=CorruptionScenario.STALE_TIMESTAMP,
                    affected_rows=len(sample_indices),
                    target_columns=[timestamp_column],
                    details=f"Backdated timestamps by {self.plan.stale_days_offset} days for {len(sample_indices)} rows",
                )
            )

        # 6. Duplicate Rows (CDC deduplication failure)
        if len(corrupted) > 0:
            dup_sample = corrupted.sample(frac=self.plan.duplicate_ratio, random_state=self.plan.seed + 4)
            corrupted = pd.concat([corrupted, dup_sample], ignore_index=True)
            faults.append(
                InjectedFault(
                    scenario=CorruptionScenario.DUPLICATE_ROWS,
                    affected_rows=len(dup_sample),
                    target_columns=[id_column],
                    details=f"Duplicated {len(dup_sample)} records",
                )
            )

        # Re-derive downstream composite fields if function provided
        if rebuild_embedding_fn is not None:
            corrupted = rebuild_embedding_fn(corrupted)

        report = CorruptionReport(
            original_row_count=original_count,
            corrupted_row_count=len(corrupted),
            injected_faults=faults,
        )

        return corrupted, report
