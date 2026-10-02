"""
Agentic Tool Evaluation Harness Templates Package
Reusable, production-ready modules for building, evaluating, and securing tool-calling agents.
"""

from .core import GenericToolOrchestrator, AgentRun, ArtifactManifest, FailureType, Provider, ToolCall, ToolResult
from .evaluation import SuiteEvaluator, EvalCase, CaseEvalResult, SuiteMetrics
from .guardrails import DualLayerSafetyValidator, InjectionDetector
from .providers import make_provider
from .tools import BaseTool, ToolRegistry

__all__ = [
    "GenericToolOrchestrator",
    "AgentRun",
    "ArtifactManifest",
    "FailureType",
    "Provider",
    "ToolCall",
    "ToolResult",
    "SuiteEvaluator",
    "EvalCase",
    "CaseEvalResult",
    "SuiteMetrics",
    "DualLayerSafetyValidator",
    "InjectionDetector",
    "make_provider",
    "BaseTool",
    "ToolRegistry",
]
