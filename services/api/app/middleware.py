"""Observability middleware for FastAPI: logging, metrics, tracing."""

from __future__ import annotations

import re
import time

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from .observability import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL

logger = structlog.stdlib.get_logger(__name__)

_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware that logs requests, records Prometheus metrics, and enriches structlog context."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        method = request.method
        path = request.url.path

        # Skip metrics/health spam
        if path in ("/health", "/metrics", "/ready", "/"):
            return await call_next(request)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            http_method=method,
            http_path=path,
        )

        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            logger.exception("unhandled_request_error", path=path, method=method)
            raise
        finally:
            duration = time.perf_counter() - start

            # Normalize path for cardinality control (collapse UUIDs)
            label_path = _normalize_path(path)

            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=label_path,
                status_code=str(status_code),
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=label_path,
            ).observe(duration)

            logger.info(
                "http_request",
                status_code=status_code,
                duration_ms=round(duration * 1000, 2),
            )


def _normalize_path(path: str) -> str:
    """Collapse UUID-like segments to {id} for Prometheus label cardinality control."""
    return _UUID_RE.sub("{id}", path)
