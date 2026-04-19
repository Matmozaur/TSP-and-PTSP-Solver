"""Tests for TSP solving endpoints."""

import time


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
    assert response.status_code == 422


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
    assert response.status_code == 422


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


def test_tsp_submit_job_status_and_result(client):
    """Test async submit/status/result flow for a multi-run job."""
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
        "runs": [
            {"method": "Random", "time_limit": 1.0},
            {"method": "HC", "time_limit": 1.0},
        ],
    }

    submit = client.post("/api/v1/tsp/jobs", json=payload)
    assert submit.status_code == 202
    submit_data = submit.json()
    assert "job_id" in submit_data
    job_id = submit_data["job_id"]

    latest_status = None
    timeout_seconds = 8.0
    poll_interval = 0.02
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status_resp = client.get(f"/api/v1/tsp/jobs/{job_id}")
        assert status_resp.status_code == 200
        latest_status = status_resp.json()
        if latest_status["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
            break
        time.sleep(poll_interval)

    assert latest_status is not None
    assert latest_status["status"] in {"COMPLETED", "FAILED", "CANCELLED"}
    assert len(latest_status["runs"]) == 2

    result_resp = client.get(f"/api/v1/tsp/jobs/{job_id}/result")
    assert result_resp.status_code == 200
    result_data = result_resp.json()
    assert result_data["job_id"] == job_id
    assert len(result_data["runs"]) == 2


def test_tsp_job_cancel(client):
    """Test cancellation endpoint for an async job."""
    payload = {
        "graph": {
            "matrix": [
                [0, 10, 15, 20],
                [10, 0, 35, 25],
                [15, 35, 0, 30],
                [20, 25, 30, 0],
            ],
        },
        "runs": [
            {"method": "MCTS", "time_limit": 2.0},
            {"method": "Genetic", "time_limit": 2.0},
        ],
    }

    submit = client.post("/api/v1/tsp/jobs", json=payload)
    assert submit.status_code == 202
    job_id = submit.json()["job_id"]

    cancel = client.post(f"/api/v1/tsp/jobs/{job_id}/cancel")
    assert cancel.status_code == 200
    cancel_data = cancel.json()
    assert cancel_data["job_id"] == job_id
    assert cancel_data["status"] in {"QUEUED", "RUNNING", "CANCELLED", "FAILED", "COMPLETED"}
    assert cancel_data["message"] == "Cancellation requested"
