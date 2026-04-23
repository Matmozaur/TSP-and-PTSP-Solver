"""Tests for PTSP endpoints."""


def test_ptsp_health(client):
    """Test PTSP service health check."""
    response = client.get("/api/v1/ptsp/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "PTSP Solver"


def test_ptsp_methods(client):
    """Test get available PTSP methods."""
    response = client.get("/api/v1/ptsp/methods")
    assert response.status_code == 200
    data = response.json()
    assert "methods" in data
    assert len(data["methods"]) > 0

    # Check for expected methods
    method_names = {m["name"] for m in data["methods"]}
    assert "Random" in method_names
    assert "HC" in method_names
    assert "Genetic" in method_names
    assert "MCTS" in method_names
