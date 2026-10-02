"""
Configuration and data contract schemas for LLMOps Observability.
Uses Pydantic v2 to enforce strict validation across logging, SLOs, metrics, and alerting.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class SLICondition(BaseModel):
    good_event: str = Field(..., description="Boolean Python expression defining a good event")
    total_event: str = Field(..., description="Boolean Python expression defining total valid events")


class PrimarySLO(BaseModel):
    name: str = Field(..., description="Identifier name of the SLO")
    window: str = Field(default="28d", description="Evaluation rolling window, e.g., '28d', '7d', '24h'")
    sli: SLICondition = Field(..., description="SLI conditions for good vs total events")
    target_percent: float = Field(default=99.5, ge=0.0, le=100.0, description="Target reliability percentage")
    error_budget_percent: float = Field(default=0.5, ge=0.0, le=100.0, description="Allowed error budget percentage")
    note: Optional[str] = Field(default=None, description="Operational notes and business justification")


class GuardrailsConfig(BaseModel):
    error_rate_pct_max: float = Field(default=2.0, ge=0.0, le=100.0)
    daily_cost_usd_max: float = Field(default=10.0, ge=0.0)
    quality_score_avg_min: float = Field(default=0.75, ge=0.0, le=1.0)
    retrieval_success_rate_pct_min: float = Field(default=90.0, ge=0.0, le=100.0)


class SLOConfig(BaseModel):
    service: str = Field(..., description="Service or application name")
    primary_slo: PrimarySLO
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)


class AlertRule(BaseModel):
    name: str = Field(..., description="Unique alert identifier")
    severity: Literal["info", "warning", "critical"] = Field(default="warning")
    condition: str = Field(..., description="Mathematical or logical condition triggering alert")
    duration: str = Field(default="5m", description="Duration before alert fires")
    type: Literal["symptom-based", "cause-based"] = Field(default="symptom-based")
    channel: str = Field(default="slack", description="Notification destination")
    owner: str = Field(default="oncall-team")
    runbook: str = Field(..., description="Markdown doc link or runbook anchor")


class DashboardPanelSpec(BaseModel):
    id: str
    title: str
    type: Literal["timeseries", "gauge", "table", "stat", "bar"]
    metric_keys: List[str]
    unit: str = ""
    thresholds: Optional[Dict[str, float]] = None
    description: Optional[str] = None


class ObservabilityConfig(BaseModel):
    service_name: str = Field(default="llm-service")
    environment: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    log_file_path: str = Field(default="data/logs.jsonl")
    tracing_enabled: bool = Field(default=True)
    tracing_backend: Literal["langfuse", "opentelemetry", "none"] = Field(default="langfuse")
    default_model_pricing: Dict[str, Dict[str, float]] = Field(
        default_factory=lambda: {
            "default": {"input_per_million": 3.0, "output_per_million": 15.0}
        }
    )
    pii_redaction_enabled: bool = Field(default=True)
    max_preview_length: int = Field(default=120)
