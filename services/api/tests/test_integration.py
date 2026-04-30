"""Integration tests for full stack: Go workers -> Python coordinator -> API.

These tests require Go workers to be running. Start with:
    docker compose up -d go-worker-random-hc go-worker-genetic go-worker-mcts

Run integration tests only:
    pytest -m integration

Skip integration tests:
    pytest -m "not integration"
"""

from __future__ import annotations

import time

import pytest

from tests.conftest_integration import (
    go_workers_available,
    integration_client,
    require_go_workers,
)


# Re-export fixtures so pytest can discover them
__all__ = ["go_workers_available", "integration_client", "require_go_workers"]


# ---------------------------------------------------------------------------
# Test matrices
# ---------------------------------------------------------------------------

MATRIX_4 = [
    [0, 10, 15, 20],
    [10, 0, 35, 25],
    [15, 35, 0, 30],
    [20, 25, 30, 0],
]

MATRIX_6 = [
    [0, 2, 9, 10, 6, 3],
    [2, 0, 6, 4, 3, 7],
    [9, 6, 0, 8, 5, 4],
    [10, 4, 8, 0, 2, 9],
    [6, 3, 5, 2, 0, 8],
    [3, 7, 4, 9, 8, 0],
]


def _is_valid_tour(tour: list[int], n: int) -> bool:
    """Return True iff *tour* is a permutation of [0, n-1]."""
    return sorted(tour) == list(range(n))


# ---------------------------------------------------------------------------
# Go Worker Health Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestGoWorkerHealth:
    """Test Go worker availability and health endpoints."""

    def test_random_hc_worker_ready(self, integration_client) -> None:
        """Random/HC Go worker should respond to ready check."""
        import httpx

        response = httpx.get("http://localhost:8080/ready", timeout=5.0)
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_genetic_worker_ready(self, integration_client) -> None:
        """Genetic Go worker should respond to ready check."""
        import httpx

        response = httpx.get("http://localhost:8081/ready", timeout=5.0)
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_mcts_worker_ready(self, integration_client) -> None:
        """MCTS Go worker should respond to ready check."""
        import httpx

        response = httpx.get("http://localhost:8082/ready", timeout=5.0)
        assert response.status_code == 200
        assert response.json()["status"] == "ready"


# ---------------------------------------------------------------------------
# End-to-End Algorithm Tests via Go Workers
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestGoWorkerExecution:
    """Test algorithm execution through Go workers (no Python fallback)."""

    @pytest.mark.parametrize("method", ["Random", "HC", "Genetic", "MCTS"])
    def test_solve_returns_valid_tour(self, method: str, integration_client) -> None:
        """All methods executed by Go workers should return valid tours."""
        payload = {
            "graph": {"matrix": MATRIX_4, "names": ["A", "B", "C", "D"]},
            "method": method,
            "time_limit": 1.0,
        }

        response = integration_client.post("/api/v1/tsp/solve", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert _is_valid_tour(data["tour"], 4)
        assert data["method"] == method
        assert data["cost"] > 0
        assert data["execution_time"] > 0

    @pytest.mark.parametrize("method", ["Random", "HC", "Genetic", "MCTS"])
    def test_solve_larger_graph(self, method: str, integration_client) -> None:
        """Go workers should handle larger graphs correctly."""
        payload = {
            "graph": {"matrix": MATRIX_6},
            "method": method,
            "time_limit": 2.0,
        }

        response = integration_client.post("/api/v1/tsp/solve", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert _is_valid_tour(data["tour"], 6)


# ---------------------------------------------------------------------------
# Async Job Tests via Go Workers
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestGoWorkerAsyncJobs:
    """Test async job execution through Go workers."""

    def test_submit_multi_algorithm_job(self, integration_client) -> None:
        """Submit job with multiple algorithms running via Go workers."""
        payload = {
            "graph": {"matrix": MATRIX_4},
            "runs": [
                {"method": "Random", "time_limit": 0.5},
                {"method": "HC", "time_limit": 0.5},
                {"method": "Genetic", "time_limit": 0.5},
                {"method": "MCTS", "time_limit": 0.5},
            ],
        }

        submit = integration_client.post("/api/v1/tsp/jobs", json=payload)
        assert submit.status_code == 202

        job_id = submit.json()["job_id"]
        assert submit.json()["run_count"] == 4

        # Wait for completion
        deadline = time.monotonic() + 30.0
        latest_status = None
        while time.monotonic() < deadline:
            status_resp = integration_client.get(f"/api/v1/tsp/jobs/{job_id}")
            assert status_resp.status_code == 200
            latest_status = status_resp.json()
            if latest_status["status"] in {"COMPLETED", "FAILED"}:
                break
            time.sleep(0.2)

        assert latest_status is not None
        assert latest_status["status"] == "COMPLETED"
        assert len(latest_status["runs"]) == 4

        # Verify all runs completed
        for run in latest_status["runs"]:
            assert run["status"] == "COMPLETED"

        # Get results
        result_resp = integration_client.get(f"/api/v1/tsp/jobs/{job_id}/result")
        assert result_resp.status_code == 200

        result_data = result_resp.json()
        methods_seen = set()
        for run in result_data["runs"]:
            assert run["result"] is not None
            assert _is_valid_tour(run["result"]["tour"], 4)
            methods_seen.add(run["method"])

        assert methods_seen == {"Random", "HC", "Genetic", "MCTS"}

    def test_job_progress_with_go_workers(self, integration_client) -> None:
        """Progress endpoint should capture telemetry from Go worker runs."""
        payload = {
            "graph": {"matrix": MATRIX_4},
            "runs": [
                {"method": "HC", "time_limit": 1.0},
            ],
        }

        submit = integration_client.post("/api/v1/tsp/jobs", json=payload)
        assert submit.status_code == 202
        job_id = submit.json()["job_id"]

        # Wait for completion
        time.sleep(3.0)

        progress_resp = integration_client.get(f"/api/v1/tsp/jobs/{job_id}/progress")
        assert progress_resp.status_code == 200

        body = progress_resp.json()
        assert body["job_id"] == job_id
        assert len(body["runs"]) == 1
        assert body["runs"][0]["method"] == "HC"
        # Should have at least one sample (the final one)
        assert len(body["runs"][0]["samples"]) >= 1


# ---------------------------------------------------------------------------
# API Readiness Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAPIReadiness:
    """Test API readiness with Go workers."""

    def test_tsp_ready_endpoint(self, integration_client) -> None:
        """TSP ready endpoint should return 200 when Go workers are available."""
        response = integration_client.get("/api/v1/tsp/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_tsp_health_endpoint(self, integration_client) -> None:
        """TSP health endpoint should return 200."""
        response = integration_client.get("/api/v1/tsp/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
