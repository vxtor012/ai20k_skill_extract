from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

def get_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class ForensicAuditLogger:
    """Append-only structured audit logger for forensics and compliance."""

    def __init__(self, log_path: str | Path | None = None):
        self.log_path = Path(log_path) if log_path else Path("outputs/audit_log.json")
        self.records: List[Dict[str, Any]] = []
        self._pending_traces: Dict[str, Dict[str, Any]] = {}

    def start_trace(self, request_id: str, user_id: str, raw_input: str) -> None:
        self._pending_traces[request_id] = {
            "request_id": request_id,
            "user_id": user_id,
            "input": raw_input,
            "start_time": time.time(),
            "timestamp": get_utc_iso(),
        }

    def complete_trace(
        self,
        request_id: str,
        output_text: str,
        blocked: bool = False,
        blocked_by: str | None = None,
        hitl_action: str | None = None,
    ) -> Dict[str, Any]:
        trace = self._pending_traces.pop(request_id, None) or {
            "request_id": request_id,
            "user_id": "anonymous",
            "input": "",
            "start_time": time.time(),
            "timestamp": get_utc_iso(),
        }
        latency = round(time.time() - trace["start_time"], 4)
        
        record = {
            "timestamp": trace["timestamp"],
            "request_id": request_id,
            "user_id": trace["user_id"],
            "input": trace["input"],
            "output": output_text,
            "blocked": blocked,
            "blocked_by": blocked_by,
            "hitl_action": hitl_action,
            "latency_seconds": latency,
        }
        self.records.append(record)
        return record

    def export_json(self, destination: str | Path | None = None) -> None:
        target = Path(destination) if destination else self.log_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2, ensure_ascii=False)


@dataclass
class AnomalyAlert:
    metric_name: str
    current_value: float
    threshold: float
    message: str

@dataclass
class MetricAlerter:
    """Realtime anomaly counter and metric alerter."""
    block_rate_limit: float = 0.40
    total_calls: int = 0
    blocked_calls: int = 0
    alerts: List[AnomalyAlert] = field(default_factory=list)

    def record_call(self, is_blocked: bool) -> None:
        self.total_calls += 1
        if is_blocked:
            self.blocked_calls += 1

    def evaluate_anomalies(self) -> List[AnomalyAlert]:
        self.alerts.clear()
        if self.total_calls >= 5:
            current_rate = self.blocked_calls / self.total_calls
            if current_rate > self.block_rate_limit:
                self.alerts.append(
                    AnomalyAlert(
                        metric_name="block_rate",
                        current_value=round(current_rate, 4),
                        threshold=self.block_rate_limit,
                        message=f"Block rate {current_rate:.1%} exceeded safe boundary ({self.block_rate_limit:.1%})",
                    )
                )
        return self.alerts
