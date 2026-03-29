"""Tests for TSP solving endpoints."""

import json


def test_tsp_solve_with_small_graph(client):
    """Test basic TSP solving with small graph."""
    payload = {
        "graph": {
            "matrix": [
                [0, 10, 15, 20],
                [10, 0, 35, 25],
                [15, 35, 0, 30],
                [20, 25, 30, 0],
            ],
            "names": ["A", "B", "C", "D"],
        },
        "method": "Random",
        "time_limit": 1.0,
    }

    response = client.post("/api/v1/tsp/solve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "tour" in data
    assert "cost" in data
    assert "method" in data
    assert data["method"] == "Random"
    assert len(data["tour"]) == 4


def test_tsp_solve_invalid_method(client):
    """Test TSP solving with invalid method."""
    payload = {
        "graph": {
            "matrix": [[0, 10], [10, 0]],
        },
        "method": "InvalidMethod",
        "time_limit": 1.0,
    }

    response = client.post("/api/v1/tsp/solve", json=payload)
    assert response.status_code == 400


def test_tsp_solve_invalid_matrix(client):
    """Test TSP solving with invalid matrix."""
    payload = {
        "graph": {
            "matrix": [[0, 10], [10, 0], [5, 5]],  # Non-square matrix
        },
        "method": "Random",
        "time_limit": 1.0,
    }

    response = client.post("/api/v1/tsp/solve", json=payload)
    assert response.status_code == 400


def test_tsp_visualize(client):
    """Test graph visualization endpoint."""
    payload = {
        "matrix": [
            [0, 10, 15],
            [10, 0, 35],
            [15, 35, 0],
        ],
        "names": ["A", "B", "C"],
    }

    response = client.post("/api/v1/tsp/visualize", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
