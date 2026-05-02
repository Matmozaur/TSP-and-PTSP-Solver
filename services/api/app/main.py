"""Main FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from . import __version__
from .config import settings
from .middleware import ObservabilityMiddleware
from .observability import init_observability
from .routes_ptsp import router as ptsp_router
from .routes_tsp import close_tsp_resources, router as tsp_router

logger = structlog.stdlib.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: init observability on startup, clean up on shutdown."""
    init_observability(settings)
    logger.info(
        "app_started",
        version=settings.app_version,
        environment=settings.environment,
        otel_enabled=settings.otel_enabled,
        prometheus_enabled=settings.prometheus_enabled,
    )
    yield
    close_tsp_resources()
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Observability middleware (runs after CORS)
    app.add_middleware(ObservabilityMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_credentials,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
    )

    # OpenTelemetry FastAPI auto-instrumentation
    if settings.otel_enabled:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
        except Exception:
            logger.warning("otel_fastapi_instrumentation_failed", exc_info=True)

    # Prometheus /metrics endpoint
    if settings.prometheus_enabled:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    # Root endpoint
    @app.get("/")
    async def root() -> dict:
        """Root endpoint with API information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "docs_url": "/docs",
            "openapi_url": "/openapi.json",
        }

    # Health check
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.app_version,
        }

    # Register routers
    app.include_router(
        tsp_router,
        prefix=settings.api_v1_prefix,
    )
    app.include_router(
        ptsp_router,
        prefix=settings.api_v1_prefix,
    )

    # 404 handler
    @app.exception_handler(404)
    async def not_found_handler(request, exc):  # type: ignore
        """Handle 404 errors."""
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found", "path": str(request.url.path)},
        )

    return app


# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
