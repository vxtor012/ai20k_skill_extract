"""Base Data Pipeline Orchestration Framework.

Provides generic, reusable Abstract Base Classes and protocols for building
production-grade, observable, resilient data pipelines for AI/RAG systems.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Generic, Protocol, Sequence, TypeVar
import json
import logging

logger = logging.getLogger("data_pipeline.base")


class StageStatus(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStageResult:
    """Standardized outcome for any executed pipeline stage."""
    stage_name: str
    status: StageStatus
    start_time: datetime
    end_time: datetime
    records_processed: int = 0
    records_failed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None

    @property
    def duration_seconds(self) -> float:
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": round(self.duration_seconds, 4),
            "records_processed": self.records_processed,
            "records_failed": self.records_failed,
            "metadata": self.metadata,
            "error_message": self.error_message,
        }


@dataclass
class PipelineContext:
    """Global execution context and path manager across pipeline stages."""
    pipeline_id: str
    run_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dry_run: bool = False
    strict_mode: bool = True
    workspace_dir: Path = field(default_factory=Path.cwd)
    artifacts_dir: Path = field(default_factory=lambda: Path.cwd() / "artifacts")
    custom_params: dict[str, Any] = field(default_factory=dict)

    def get_artifact_path(self, relative_path: str | Path) -> Path:
        target = (self.artifacts_dir / relative_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        return target


TRecord = TypeVar("TRecord")
TTransformed = TypeVar("TTransformed")


class BaseIngestionSource(ABC, Generic[TRecord]):
    """Abstract Ingestion component with Lineage / Raw Preservation guarantees."""

    @abstractmethod
    def fetch_records(self, context: PipelineContext) -> list[TRecord]:
        """Fetch raw records from primary source (API, DB, Stream, or File)."""
        pass

    @abstractmethod
    def preserve_raw(self, records: Sequence[TRecord], output_path: Path) -> Path:
        """Persist immutable snapshot for complete audit trail and idempotent replay."""
        pass

    @abstractmethod
    def load_cached_raw(self, input_path: Path) -> list[TRecord]:
        """Load from offline/cached snapshot in fallback scenarios."""
        pass


class BaseDataTransformer(ABC, Generic[TRecord, TTransformed]):
    """Abstract Transformation component for cleaning, normalizing, and feature prep."""

    @abstractmethod
    def transform(self, records: Sequence[TRecord], context: PipelineContext) -> TTransformed:
        """Clean, deduplicate, validate schema, compute freshness, and construct embedding text."""
        pass

    @abstractmethod
    def export(self, transformed_data: TTransformed, output_path: Path) -> Path:
        """Persist clean dataset in intermediate standard formats (CSV, Parquet, JSON)."""
        pass


class BaseVectorIndexer(ABC, Generic[TTransformed]):
    """Abstract Indexer component for embedding generation and Vector Database persistence."""

    @abstractmethod
    def build_index(self, data: TTransformed, collection_name: str, context: PipelineContext) -> dict[str, Any]:
        """Generate vectors and upsert documents + metadata into vector storage."""
        pass

    @abstractmethod
    def verify_index(self, collection_name: str, expected_count: int) -> bool:
        """Smoke-test vector collection availability and document count."""
        pass


class BasePipelineOrchestrator(ABC):
    """End-to-end Master Orchestrator binding all pipeline stages together."""

    def __init__(self, context: PipelineContext):
        self.context = context
        self.stage_results: list[PipelineStageResult] = []

    def log_stage(self, result: PipelineStageResult) -> None:
        self.stage_results.append(result)
        logger.info(
            f"Stage '{result.stage_name}' completed with status [{result.status.value}] "
            f"in {result.duration_seconds:.2f}s ({result.records_processed} processed)"
        )
        if result.status == StageStatus.FAILED and self.context.strict_mode:
            raise RuntimeError(f"Pipeline failed at stage '{result.stage_name}': {result.error_message}")

    @abstractmethod
    def run(self) -> dict[str, Any]:
        """Execute the full orchestrated pipeline workflow."""
        pass

    def export_audit_log(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "pipeline_id": self.context.pipeline_id,
            "run_timestamp": self.context.run_timestamp.isoformat(),
            "stages": [res.to_dict() for res in self.stage_results],
            "total_duration": sum(res.duration_seconds for res in self.stage_results),
            "overall_status": (
                StageStatus.FAILED.value
                if any(r.status == StageStatus.FAILED for r in self.stage_results)
                else StageStatus.SUCCESS.value
            ),
        }
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return output_path
