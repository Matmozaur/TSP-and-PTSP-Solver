"""Observability setup: structured logging, tracing, and Prometheus metrics."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import structlog
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from prometheus_client import Counter, Histogram, Info

if TYPE_CHECKING:
    from .config import Settings

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

APP_INFO = Info("tsp_solver", "TSP Solver application info")

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

TSP_JOBS_SUBMITTED = Counter(
    "tsp_jobs_submitted_total",
    "Total TSP jobs submitted",
    ["status"],
)

TSP_RUNS_COMPLETED = Counter(
    "tsp_runs_completed_total",
    "Total TSP algorithm runs completed",
    ["method", "status"],
)

TSP_SOLVE_DURATION_SECONDS = Histogram(
    "tsp_solve_duration_seconds",
    "TSP algorithm execution time in seconds",
    ["method"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)


# ---------------------------------------------------------------------------
# Structured logging setup
# ---------------------------------------------------------------------------


def setup_logging(settings: Settings) -> None:
    """Configure structlog with JSON or console rendering.

    Args:
        settings: Application settings providing log_level and log_format.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.otel_enabled:
        shared_processors.append(_add_trace_context)

    if settings.log_format == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quieten noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(log_level)


def _add_trace_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Inject OpenTelemetry trace/span IDs into every log record."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.is_valid:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


# ---------------------------------------------------------------------------
# OpenTelemetry tracing setup
# ---------------------------------------------------------------------------


def setup_tracing(settings: Settings) -> None:
    """Initialise OpenTelemetry tracing with OTLP exporter.

    A no-op if ``settings.otel_enabled`` is False.

    Args:
        settings: Application settings.
    """
    if not settings.otel_enabled:
        return

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": settings.app_version,
            "deployment.environment": settings.environment,
        }
    )

    provider = TracerProvider(resource=resource)

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        insecure = settings.environment in ("development", "test")
        exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_endpoint, insecure=insecure
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
    except Exception:
        _logger = structlog.stdlib.get_logger(__name__)
        _logger.warning("otlp_exporter_failed_falling_back_to_console", exc_info=True)
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)


def get_tracer(name: str = "tsp-solver") -> trace.Tracer:
    """Return a named tracer from the global provider."""
    return trace.get_tracer(name)


# ---------------------------------------------------------------------------
# Combined init
# ---------------------------------------------------------------------------


def init_observability(settings: Settings) -> None:
    """One-call initialisation for all observability subsystems.

    Args:
        settings: Application settings.
    """
    setup_logging(settings)
    setup_tracing(settings)
    APP_INFO.info(
        {
            "version": settings.app_version,
            "environment": settings.environment,
        }
    )
