"""Tests for FastAPI application."""

import json


def test_root(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["name"] == "TSP-PTSP Solver"


def test_health(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_api_docs(client):
    """Test OpenAPI documentation is available."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


def test_tsp_health(client):
    """Test TSP service health check."""
    response = client.get("/api/v1/tsp/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
