"""
LLMOps Observability & Diagnostic Engine Templates Package.
Provides generalized, vendor-agnostic modules for full-lifecycle LLM observability,
structured logging, distributed tracing, prompt management, and automated incident triage.
"""

from .config_schemas import AlertRule, DashboardPanelSpec, ObservabilityConfig, SLOConfig
from .incident_debugger import IncidentCorrelator, IncidentReport, TriageResult
from .logging_pipeline import JsonlFileProcessor, configure_structured_logging, get_structured_logger, scrub_event
from .metrics_evaluator import LatencyStats, MetricsEvaluator, SLOCalculator, TokenCostModel
from .middleware import CorrelationIdMiddleware
from .pii_scrubber import BasePIIScrubber, RegexPIIScrubber, hash_identifier, scrub_recursive
from .prompt_manager import PromptManager, PromptResolutionResult
from .tracer import BaseTracer, LangfuseTracer, NoOpTracer, create_tracer

__all__ = [
    "BasePIIScrubber",
    "RegexPIIScrubber",
    "scrub_recursive",
    "hash_identifier",
    "configure_structured_logging",
    "get_structured_logger",
    "scrub_event",
    "JsonlFileProcessor",
    "CorrelationIdMiddleware",
    "BaseTracer",
    "LangfuseTracer",
    "NoOpTracer",
    "create_tracer",
    "PromptManager",
    "PromptResolutionResult",
    "MetricsEvaluator",
    "SLOCalculator",
    "TokenCostModel",
    "LatencyStats",
    "IncidentCorrelator",
    "IncidentReport",
    "TriageResult",
    "ObservabilityConfig",
    "SLOConfig",
    "AlertRule",
    "DashboardPanelSpec",
]
