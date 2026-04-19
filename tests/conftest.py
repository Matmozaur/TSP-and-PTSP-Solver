"""Pytest configuration."""

import pytest


@pytest.fixture(autouse=True)
def reset_route_singletons():
    """Reset module-level singletons in routes_tsp between tests.

    The FastAPI route module caches the coordinator and service as
    process-global singletons.  Resetting them ensures each test starts
    from a clean state and avoids cross-test thread / lock interactions.
    """
    import src.app.routes_tsp as routes

    routes._job_coordinator = None
    routes._tsp_service = None
    yield
    routes._job_coordinator = None
    routes._tsp_service = None


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from fastapi.testclient import TestClient

    from src.app.main import app

    with TestClient(app) as c:
        yield c
