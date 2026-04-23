"""Pytest configuration."""

import pytest


def _teardown_singleton(routes) -> None:  # type: ignore[no-untyped-def]
    """Close resources held by route singletons before clearing them."""
    if routes._job_coordinator is not None:
        routes._job_coordinator.shutdown(wait=True)
        routes._job_coordinator = None

    if routes._tsp_service is not None:
        routes._tsp_service.close()
        routes._tsp_service = None


@pytest.fixture(autouse=True)
def reset_route_singletons():
    """Reset module-level singletons in routes_tsp between tests.

    The FastAPI route module caches the coordinator and service as
    process-global singletons.  Resetting them ensures each test starts
    from a clean state and avoids cross-test thread / lock interactions.
    """
    import app.routes_tsp as routes

    _teardown_singleton(routes)
    yield
    _teardown_singleton(routes)


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
