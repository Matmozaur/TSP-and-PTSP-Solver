"""Main FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .config import settings
from .routes_ptsp import router as ptsp_router
from .routes_tsp import close_tsp_resources, router as tsp_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: clean up singletons on shutdown."""
    yield
    close_tsp_resources()


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

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_credentials,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
    )

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
