"""
Automated Incident Debugger & Triad Correlator (Metrics -> Logs -> Traces).
Performs root-cause analysis by correlating telemetry anomalies with structured log events and distributed trace waterfalls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TriageResult:
    correlation_id: str
    timestamp: str
    event: str
    latency_ms: float
    error_type: Optional[str]
    culprit_span: Optional[str]
    culprit_duration_ms: Optional[float]
    culprit_percentage: Optional[float]
    root_cause_summary: str
    recommended_fix: List[str]


@dataclass
class IncidentReport:
    incident_id: str
    time_window: str
    symptoms: Dict[str, Any]
    affected_requests_count: int
    triaged_samples: List[TriageResult]
    systemic_root_cause: str
    remediation_steps: List[str]


class IncidentCorrelator:
    """
    Automated triage engine linking macro metrics degradation to micro trace spans.
    """

    def __init__(self, log_path: str | Path = "data/logs.jsonl"):
        self.log_path = Path(log_path)

    def load_logs(self, start_iso: Optional[str] = None, end_iso: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.log_path.exists():
            return []
        records = []
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = entry.get("ts", "")
                    if start_iso and ts < start_iso:
                        continue
                    if end_iso and ts > end_iso:
                        continue
                    records.append(entry)
                except json.JSONDecodeError:
                    continue
        return records

    def find_anomalous_requests(
        self,
        latency_threshold_ms: float = 3000.0,
        filter_errors: bool = True,
        records: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        entries = records if records is not None else self.load_logs()
        anomalies = []
        for r in entries:
            lat = r.get("latency_ms", 0)
            event = r.get("event", "")
            is_err = event == "request_failed" or "error_type" in r
            if (filter_errors and is_err) or (lat > latency_threshold_ms):
                anomalies.append(r)
        return anomalies

    def diagnose_trace_breakdown(
        self,
        total_latency_ms: float,
        span_durations_ms: Dict[str, float],
    ) -> tuple[str, float, float]:
        """
        Pinpoints the bottleneck span taking the highest ratio of total execution time.
        """
        if not span_durations_ms or total_latency_ms <= 0:
            return "unknown", 0.0, 0.0

        culprit = max(span_durations_ms.items(), key=lambda item: item[1])
        span_name, span_duration = culprit
        pct = round((span_duration / total_latency_ms) * 100.0, 1)
        return span_name, span_duration, pct

    def generate_incident_report(
        self,
        incident_id: str,
        time_window: str,
        latency_threshold_ms: float = 3000.0,
    ) -> IncidentReport:
        logs = self.load_logs()
        anomalies = self.find_anomalous_requests(latency_threshold_ms=latency_threshold_ms, records=logs)

        triaged: List[TriageResult] = []
        for req in anomalies[:5]:  # sample top 5
            cid = req.get("correlation_id", "unknown")
            ts = req.get("ts", "")
            event = req.get("event", "")
            lat = float(req.get("latency_ms", 0))
            err = req.get("error_type")

            # Heuristic simulation or trace-matched spans
            span_breakdown = req.get("payload", {}).get("spans", {})
            if not span_breakdown:
                # Default heuristic based on tool_name
                tool = req.get("tool_name", "retrieval")
                if lat > latency_threshold_ms:
                    span_breakdown = {tool: lat * 0.85, "generation": lat * 0.15}
                else:
                    span_breakdown = {"generation": lat * 0.9}

            culprit, dur, pct = self.diagnose_trace_breakdown(lat, span_breakdown)

            root_cause = (
                f"Span '{culprit}' absorbed {pct}% ({dur:.0f}ms) of total request time."
                if lat > latency_threshold_ms
                else f"Unhandled exception '{err}' encountered during request execution."
            )

            fixes = [
                f"Verify downstream health of '{culprit}' service/database.",
                "Enforce client-side timeout and circuit breaker policies.",
                "Review Langfuse trace waterfall with matching correlation_id.",
            ]

            triaged.append(
                TriageResult(
                    correlation_id=cid,
                    timestamp=ts,
                    event=event,
                    latency_ms=lat,
                    error_type=err,
                    culprit_span=culprit,
                    culprit_duration_ms=dur,
                    culprit_percentage=pct,
                    root_cause_summary=root_cause,
                    recommended_fix=fixes,
                )
            )

        systemic_cause = (
            f"Detected {len(anomalies)} requests violating latency threshold ({latency_threshold_ms}ms) or throwing 5xx errors."
            if anomalies
            else "No systemic anomalies detected within the specified criteria."
        )

        return IncidentReport(
            incident_id=incident_id,
            time_window=time_window,
            symptoms={"anomalous_requests_count": len(anomalies), "latency_threshold_ms": latency_threshold_ms},
            affected_requests_count=len(anomalies),
            triaged_samples=triaged,
            systemic_root_cause=systemic_cause,
            remediation_steps=[
                "1. Isolate degraded downstream dependencies via fallback mechanisms.",
                "2. Check error budget burn rate and halt risky production rollouts if exhausted.",
                "3. Rollback prompt label or model version if regression was caused by prompt change.",
                "4. Update alerting thresholds to prevent false positives/negatives.",
            ],
        )
