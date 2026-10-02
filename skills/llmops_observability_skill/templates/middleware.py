"""
FastAPI & Starlette Correlation ID & Context Isolation Middleware.
Guarantees zero-cross-contamination between async concurrent requests, binds request IDs,
and attaches execution metrics to HTTP response headers.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    HTTP Middleware that:
    1. Resets per-request context variables.
    2. Ingests or generates a high-entropy Correlation ID (e.g. `req-<8-hex>`).
    3. Injects the ID into structlog context & request.state.
    4. Computes execution duration and appends `x-request-id` and `x-response-time-ms` headers.
    """

    def __init__(
        self,
        app,
        header_name: str = "x-request-id",
        id_generator: Optional[Callable[[], str]] = None,
    ):
        super().__init__(app)
        self.header_name = header_name.lower()
        self.id_generator = id_generator or (lambda: f"req-{uuid.uuid4().hex[:8]}")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Step 1: Isolation - prevent thread/task context leakage
        clear_contextvars()

        # Step 2: Extract or generate correlation ID
        incoming_id = request.headers.get(self.header_name, "").strip()
        correlation_id = incoming_id if incoming_id else self.id_generator()

        # Step 3: Bind to logging context & request state
        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        # Step 4: Time execution
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

        # Step 5: Append propagation headers
        response.headers[self.header_name] = correlation_id
        response.headers["x-response-time-ms"] = f"{duration_ms:.2f}"

        return response
