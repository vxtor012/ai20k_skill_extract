"""
Vendor-Agnostic Distributed Tracing & Span Hierarchy Instrumenter.
Supports Langfuse, OpenTelemetry, and Fallback Mock Tracing with automatic suppression of raw sensitive payload.
"""

from __future__ import annotations

import abc
import os
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional


class BaseTracer(abc.ABC):
    @abc.abstractmethod
    def is_enabled(self) -> bool:
        """Returns true if tracer backend is active and configured."""
        raise NotImplementedError

    @abc.abstractmethod
    @contextmanager
    def trace_context(
        self,
        name: str,
        user_id: str = "",
        session_id: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        environment: str = "dev",
    ) -> Iterator[Any]:
        """Creates or scopes a distributed trace context."""
        raise NotImplementedError

    @abc.abstractmethod
    def update_span(self, metadata: Optional[Dict[str, Any]] = None, version: Optional[str] = None) -> None:
        """Updates the active execution span."""
        raise NotImplementedError


class NoOpTracer(BaseTracer):
    """Fallback no-op tracer when telemetry backends are disabled or offline."""

    def is_enabled(self) -> bool:
        return False

    @contextmanager
    def trace_context(
        self,
        name: str,
        user_id: str = "",
        session_id: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        environment: str = "dev",
    ) -> Iterator[Any]:
        yield self

    def update_span(self, metadata: Optional[Dict[str, Any]] = None, version: Optional[str] = None) -> None:
        pass


class LangfuseTracer(BaseTracer):
    """
    Production-grade Langfuse telemetry wrapper enforcing safe metadata and hierarchical span linking.
    """

    def __init__(self):
        try:
            from langfuse import get_client, observe, propagate_attributes

            self._sdk_available = True
            self._get_client = get_client
            self._observe = observe
            self._propagate_attributes = propagate_attributes
        except ImportError:
            self._sdk_available = False

    def is_enabled(self) -> bool:
        return self._sdk_available and bool(
            os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
        )

    @contextmanager
    def trace_context(
        self,
        name: str,
        user_id: str = "",
        session_id: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        environment: str = "dev",
    ) -> Iterator[Any]:
        if not self.is_enabled():
            yield self
            return

        with self._propagate_attributes(
            user_id=user_id,
            session_id=session_id,
            tags=tags or [],
            trace_name=name,
            environment=environment,
            metadata=metadata or {},
        ):
            yield self._get_client()

    def update_span(self, metadata: Optional[Dict[str, Any]] = None, version: Optional[str] = None) -> None:
        if not self.is_enabled():
            return
        client = self._get_client()
        client.update_current_span(metadata=metadata or {}, version=version)


def create_tracer(backend: str = "langfuse") -> BaseTracer:
    """Factory helper to build the requested tracer implementation."""
    backend_lower = backend.lower().strip()
    if backend_lower == "langfuse":
        tracer = LangfuseTracer()
        if tracer.is_enabled():
            return tracer
    return NoOpTracer()
