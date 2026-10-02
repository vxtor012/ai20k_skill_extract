"""Data Freshness & Stale Data SLA Monitoring Module.

Monitors temporal health, staleness drift, and compliance against configurable SLA thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import logging

import pandas as pd

logger = logging.getLogger("data_pipeline.freshness")


@dataclass
class FreshnessConfig:
    timestamp_column: str = "published"
    max_staleness_days: int = 180
    max_stale_percentage_threshold: float = 0.25  # 25% max allowed stale records
    datetime_format: str | None = None  # None for auto-parsing


@dataclass
class FreshnessReport:
    evaluated_at: datetime
    timestamp_column: str
    total_records: int
    stale_records_count: int
    stale_records_percentage: float
    max_staleness_days: int
    is_fresh: bool
    oldest_record_date: str | None
    newest_record_date: str | None
    median_age_days: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluated_at": self.evaluated_at.isoformat(),
            "timestamp_column": self.timestamp_column,
            "total_records": self.total_records,
            "stale_records_count": self.stale_records_count,
            "stale_records_percentage": round(self.stale_records_percentage, 4),
            "max_staleness_days": self.max_staleness_days,
            "is_fresh": self.is_fresh,
            "oldest_record_date": self.oldest_record_date,
            "newest_record_date": self.newest_record_date,
            "median_age_days": self.median_age_days,
        }

    def to_markdown(self) -> str:
        badge = "🟢 FRESH" if self.is_fresh else "🔴 STALE DRIFT DETECTED"
        return f"""# Data Freshness & SLA Report
**Overall Status:** {badge}
**Evaluation Timestamp:** {self.evaluated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

| Metric | Measured Value | SLA Target / Threshold | Status |
| :--- | :--- | :--- | :---: |
| **Total Records** | {self.total_records} | > 0 | {'✅' if self.total_records > 0 else '❌'} |
| **Oldest Record Date** | {self.oldest_record_date or 'N/A'} | N/A | ℹ️ |
| **Newest Record Date** | {self.newest_record_date or 'N/A'} | Recent | ℹ️ |
| **Median Data Age** | {self.median_age_days:.1f} days | < {self.max_staleness_days} days | {'✅' if (self.median_age_days or 0) <= self.max_staleness_days else '⚠️'} |
| **Stale Record Ratio** | {self.stale_records_percentage * 100:.2f}% ({self.stale_records_count}/{self.total_records}) | <= {self.max_staleness_days}d SLA | {'✅' if self.is_fresh else '❌'} |
"""


class FreshnessMonitor:
    """Calculates data freshness SLAs and flags temporal staleness drift."""

    def __init__(self, config: FreshnessConfig):
        self.config = config

    def evaluate(self, df: pd.DataFrame, reference_time: datetime | None = None) -> FreshnessReport:
        ref_time = reference_time or datetime.now(timezone.utc)
        col = self.config.timestamp_column

        if col not in df.columns or len(df) == 0:
            return FreshnessReport(
                evaluated_at=ref_time,
                timestamp_column=col,
                total_records=len(df),
                stale_records_count=len(df),
                stale_records_percentage=1.0 if len(df) > 0 else 0.0,
                max_staleness_days=self.config.max_staleness_days,
                is_fresh=False,
                oldest_record_date=None,
                newest_record_date=None,
                median_age_days=None,
            )

        # Parse timestamps safely
        parsed_dates = pd.to_datetime(df[col], format=self.config.datetime_format, errors="coerce", utc=True)
        valid_dates = parsed_dates.dropna()

        if len(valid_dates) == 0:
            return FreshnessReport(
                evaluated_at=ref_time,
                timestamp_column=col,
                total_records=len(df),
                stale_records_count=len(df),
                stale_records_percentage=1.0,
                max_staleness_days=self.config.max_staleness_days,
                is_fresh=False,
                oldest_record_date=None,
                newest_record_date=None,
                median_age_days=None,
            )

        # Calculate ages in days
        ages = (ref_time - valid_dates).dt.total_seconds() / 86400.0
        stale_mask = ages > self.config.max_staleness_days
        stale_count = int(stale_mask.sum())
        total_records = len(df)
        stale_ratio = stale_count / total_records

        is_fresh = stale_ratio <= self.config.max_stale_percentage_threshold

        return FreshnessReport(
            evaluated_at=ref_time,
            timestamp_column=col,
            total_records=total_records,
            stale_records_count=stale_count,
            stale_records_percentage=stale_ratio,
            max_staleness_days=self.config.max_staleness_days,
            is_fresh=is_fresh,
            oldest_record_date=valid_dates.min().isoformat(),
            newest_record_date=valid_dates.max().isoformat(),
            median_age_days=float(ages.median()),
        )

    def save_report(self, report: FreshnessReport, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        return output_path
