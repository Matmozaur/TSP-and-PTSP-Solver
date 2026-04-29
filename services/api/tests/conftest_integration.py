"""Integration test fixtures requiring Go workers to be running.

These fixtures check for Go worker availability and skip tests if workers
are not accessible. Use with @pytest.mark.integration decorator.
"""

from __future__ import annotations

import os

import httpx
import pytest


# URLs for Go workers - match docker-compose.yml
_GO_WORKER_URLS = {
    "random_hc": os.environ.get("GO_WORKER_URL_RANDOM_HC", "http://localhost:8080"),
    "genetic": os.environ.get("GO_WORKER_URL_GENETIC", "http://localhost:8081"),
    "mcts": os.environ.get("GO_WORKER_URL_MCTS", "http://localhost:8082"),
}


def _check_go_worker_available(url: str) -> bool:
    """Check if a Go worker is available at the given URL."""
    try:
        response = httpx.get(f"{url}/ready", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


def _all_go_workers_available() -> bool:
    """Check if all Go workers are available."""
    return all(_check_go_worker_available(url) for url in _GO_WORKER_URLS.values())


@pytest.fixture(scope="session")
def go_workers_available() -> bool:
    """Session-scoped fixture indicating whether Go workers are available."""
    return _all_go_workers_available()


@pytest.fixture
def require_go_workers(go_workers_available: bool) -> None:
    """Skip test if Go workers are not available."""
    if not go_workers_available:
        pytest.skip("Go workers not available - start with: docker compose up -d")


@pytest.fixture
def integration_client(require_go_workers):
    """Create test client with Go workers enabled in strict mode.

    This fixture ensures Go workers are available before creating the client
    and configures the app to use strict mode (no Python fallback).
    """
    import os

    # Set environment for Go worker integration
    os.environ["GO_WORKER_ENABLED"] = "true"
    os.environ["GO_WORKER_MODE"] = "strict"
    os.environ["GO_WORKER_URL"] = _GO_WORKER_URLS["random_hc"]
    os.environ["GO_WORKER_URL_RANDOM_HC"] = _GO_WORKER_URLS["random_hc"]
    os.environ["GO_WORKER_URL_GENETIC"] = _GO_WORKER_URLS["genetic"]
    os.environ["GO_WORKER_URL_MCTS"] = _GO_WORKER_URLS["mcts"]

    # Reset singletons to pick up new config
    import app.routes_tsp as routes

    if routes._job_coordinator is not None:
        routes._job_coordinator.shutdown(wait=True)
        routes._job_coordinator = None
    if routes._tsp_service is not None:
        routes._tsp_service.close()
        routes._tsp_service = None

    # Reload settings
    from app.config import Settings

    import app.config

    app.config.settings = Settings()

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c

    # Cleanup
    if routes._job_coordinator is not None:
        routes._job_coordinator.shutdown(wait=True)
        routes._job_coordinator = None
    if routes._tsp_service is not None:
        routes._tsp_service.close()
        routes._tsp_service = None
