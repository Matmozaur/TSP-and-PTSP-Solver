"""Pytest configuration."""

import pytest


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from fastapi.testclient import TestClient

    from src.app.main import app

    return TestClient(app)
