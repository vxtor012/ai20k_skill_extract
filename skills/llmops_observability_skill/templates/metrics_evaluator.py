"""
Comprehensive LLM Metrics, Percentiles, Token Cost Calculator & SLO Evaluator.
Computes latency distributions (P50, P90, P95, P99), TTFT, token usage economics, and SLI/SLO error budgets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LatencyStats:
    count: int
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    max_ms: float


class TokenCostModel:
    """
    Computes precise USD monetary costs across heterogeneous LLM providers and models.
    """

    PRICING_CATALOG: Dict[str, Dict[str, float]] = {
        "gpt-4o": {"input_per_million": 2.50, "output_per_million": 10.00},
        "gpt-4o-mini": {"input_per_million": 0.15, "output_per_million": 0.60},
        "claude-3-5-sonnet": {"input_per_million": 3.00, "output_per_million": 15.00},
        "claude-3-haiku": {"input_per_million": 0.25, "output_per_million": 1.25},
        "gemini-1.5-pro": {"input_per_million": 3.50, "output_per_million": 10.50},
        "gemini-1.5-flash": {"input_per_million": 0.075, "output_per_million": 0.30},
        "default": {"input_per_million": 3.00, "output_per_million": 15.00},
    }

    def __init__(self, custom_pricing: Optional[Dict[str, Dict[str, float]]] = None):
        self.pricing = {**self.PRICING_CATALOG, **(custom_pricing or {})}

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        rate = self.pricing.get(model, self.pricing["default"])
        input_cost = (input_tokens / 1_000_000.0) * rate["input_per_million"]
        output_cost = (output_tokens / 1_000_000.0) * rate["output_per_million"]
        return round(input_cost + output_cost, 6)


class MetricsEvaluator:
    """
    Statistical aggregator for latency, quality, error rate, and throughput.
    """

    @staticmethod
    def calculate_percentiles(values: List[float | int]) -> LatencyStats:
        if not values:
            return LatencyStats(count=0, p50_ms=0, p90_ms=0, p95_ms=0, p99_ms=0, mean_ms=0, max_ms=0)
        
        sorted_vals = sorted(values)
        n = len(sorted_vals)

        def _get_p(p: float) -> float:
            k = (n - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return float(sorted_vals[int(k)])
            d0 = sorted_vals[int(f)] * (c - k)
            d1 = sorted_vals[int(c)] * (k - f)
            return float(d0 + d1)

        return LatencyStats(
            count=n,
            p50_ms=round(_get_p(0.50), 2),
            p90_ms=round(_get_p(0.90), 2),
            p95_ms=round(_get_p(0.95), 2),
            p99_ms=round(_get_p(0.99), 2),
            mean_ms=round(sum(sorted_vals) / n, 2),
            max_ms=float(sorted_vals[-1]),
        )


class SLOCalculator:
    """
    Evaluates SLO compliance and computes Error Budget burn rate.
    """

    def __init__(self, target_percent: float = 99.5, total_window_budget_units: int = 100_000):
        self.target_percent = target_percent
        self.allowed_error_fraction = (100.0 - target_percent) / 100.0
        self.total_budget_units = total_window_budget_units

    def compute_slo(self, good_events_count: int, total_events_count: int) -> Dict[str, Any]:
        if total_events_count == 0:
            return {
                "achieved_sli_percent": 100.0,
                "target_percent": self.target_percent,
                "slo_met": True,
                "error_budget_total": 0,
                "error_budget_consumed": 0,
                "error_budget_remaining": 0,
                "burn_rate": 0.0,
            }

        sli_percent = (good_events_count / total_events_count) * 100.0
        bad_events = total_events_count - good_events_count
        max_allowed_bad = int(total_events_count * self.allowed_error_fraction)
        
        remaining_budget = max(0, max_allowed_bad - bad_events)
        burn_rate = (bad_events / max_allowed_bad) if max_allowed_bad > 0 else (1.0 if bad_events > 0 else 0.0)

        return {
            "achieved_sli_percent": round(sli_percent, 3),
            "target_percent": self.target_percent,
            "slo_met": sli_percent >= self.target_percent,
            "total_events": total_events_count,
            "bad_events": bad_events,
            "allowed_bad_events": max_allowed_bad,
            "error_budget_remaining": remaining_budget,
            "burn_rate": round(burn_rate, 2),
        }
