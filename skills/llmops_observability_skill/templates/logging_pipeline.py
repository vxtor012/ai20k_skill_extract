"""
Standardized High-Performance Structlog Pipeline for LLM Applications.
Enforces defense-in-depth PII scrubbing, context isolation, standardized schema, and dual-output (stdout + JSONL).
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Set

import structlog
from structlog.contextvars import merge_contextvars

from .pii_scrubber import BasePIIScrubber, scrub_recursive


class JsonlFileProcessor:
    """
    Appends structured JSON log entries to an indexed file destination.
    Thread-safe in standard Python file append mode.
    """

    def __init__(self, file_path: str | Path = "data/logs.jsonl"):
        self.path = Path(file_path)

    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            rendered = structlog.processors.JSONRenderer()(logger, method_name, event_dict)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(rendered + "\n")
        except Exception as exc:  # pragma: no cover
            sys.stderr.write(f"[LOG_FALLBACK_ERR] Failed writing to {self.path}: {exc}\n")
        return event_dict


class PIIScrubbingProcessor:
    """
    In-pipeline Structlog processor that scrubs all dynamic payload values
    prior to serialization.
    """

    def __init__(self, scrubber: Optional[BasePIIScrubber] = None, excluded_keys: Optional[Set[str]] = None):
        self.scrubber = scrubber
        self.excluded_keys = excluded_keys or {
            "ts",
            "level",
            "service",
            "correlation_id",
            "user_id_hash",
            "session_id",
            "feature",
            "model",
            "env",
            "event",
        }

    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        return scrub_recursive(event_dict, excluded_keys=self.excluded_keys, scrubber=self.scrubber)


# Global instance for easy hookup
_DEFAULT_SCRUB_PROCESSOR = PIIScrubbingProcessor()


def scrub_event(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    return _DEFAULT_SCRUB_PROCESSOR(logger, method_name, event_dict)


def configure_structured_logging(
    log_path: str | Path = "data/logs.jsonl",
    log_level: str = "INFO",
    enable_console_json: bool = True,
    scrubber: Optional[BasePIIScrubber] = None,
) -> None:
    """
    Configures standard Structlog and standard library logging with security processors.
    """
    lvl = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", level=lvl, stream=sys.stdout)

    scrub_proc = PIIScrubbingProcessor(scrubber=scrubber) if scrubber else _DEFAULT_SCRUB_PROCESSOR

    processors = [
        merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
        scrub_proc,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        JsonlFileProcessor(file_path=log_path),
        structlog.processors.JSONRenderer() if enable_console_json else structlog.dev.ConsoleRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(lvl),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_structured_logger() -> structlog.typing.FilteringBoundLogger:
    """Convenience factory returning a typed bound logger."""
    return structlog.get_logger()
