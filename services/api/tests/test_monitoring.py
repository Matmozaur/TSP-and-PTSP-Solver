"""Tests for monitoring, observability, and progress endpoints."""

from __future__ import annotations

import time


# ---------------------------------------------------------------------------
# Existing Phase 7 progress tests
# ---------------------------------------------------------------------------


def test_job_progress_not_found(client) -> None:
    """Progress endpoint returns 404 for an unknown job id."""
    resp = client.get("/api/v1/tsp/jobs/nonexistent-id/progress")
    assert resp.status_code == 404


def test_job_progress_returns_samples_after_completion(client) -> None:
    """After a job finishes, at least one telemetry sample must exist."""
    resp = client.post(
        "/api/v1/tsp/jobs",
        json={
            "graph": {"matrix": [[0, 10, 15], [10, 0, 20], [15, 20, 0]]},
            "runs": [{"method": "Random", "time_limit": 0.1}],
        },
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    time.sleep(1.5)

    progress_resp = client.get(f"/api/v1/tsp/jobs/{job_id}/progress")
    assert progress_resp.status_code == 200

    body = progress_resp.json()
    assert body["job_id"] == job_id
    assert len(body["runs"]) == 1

    run = body["runs"][0]
    assert run["method"] == "Random"

    assert len(run["samples"]) >= 1

    final_sample = run["samples"][-1]
    assert "elapsed_seconds" in final_sample
    assert final_sample["best_cost"] is not None


def test_job_progress_sample_fields(client) -> None:
    """Every sample must contain the required fields with correct types."""
    resp = client.post(
        "/api/v1/tsp/jobs",
        json={
            "graph": {"matrix": [[0, 10, 15], [10, 0, 20], [15, 20, 0]]},
            "runs": [{"method": "HC", "time_limit": 0.1}],
        },
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    time.sleep(1.5)

    progress_resp = client.get(f"/api/v1/tsp/jobs/{job_id}/progress")
    assert progress_resp.status_code == 200

    body = progress_resp.json()
    for run in body["runs"]:
        for sample in run["samples"]:
            assert "run_id" in sample
            assert "sampled_at" in sample
            assert "elapsed_seconds" in sample
            assert "cpu_percent" in sample
            assert "memory_mb" in sample
            assert "best_cost" in sample


def test_multi_run_progress(client) -> None:
    """Progress endpoint groups samples correctly across multiple runs."""
    resp = client.post(
        "/api/v1/tsp/jobs",
        json={
            "graph": {
                "matrix": [
                    [0, 10, 15, 20],
                    [10, 0, 35, 25],
                    [15, 35, 0, 30],
                    [20, 25, 30, 0],
                ]
            },
            "runs": [
                {"method": "Random", "time_limit": 0.1},
                {"method": "HC", "time_limit": 0.3},
            ],
        },
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    time.sleep(2.0)

    progress_resp = client.get(f"/api/v1/tsp/jobs/{job_id}/progress")
    assert progress_resp.status_code == 200

    body = progress_resp.json()
    assert len(body["runs"]) == 2

    methods = {r["method"] for r in body["runs"]}
    assert methods == {"Random", "HC"}

    for run in body["runs"]:
        assert len(run["samples"]) >= 1


# ---------------------------------------------------------------------------
# Prometheus metrics tests
# ---------------------------------------------------------------------------


def test_metrics_endpoint_available(client) -> None:
    """Prometheus /metrics endpoint should be reachable."""
    resp = client.get("/metrics/")
    assert resp.status_code == 200
    body = resp.text
    # Verify Prometheus text format
    assert "http_requests_total" in body or "tsp_solver_info" in body


def test_metrics_include_app_info(client) -> None:
    """App info metric should be present after startup."""
    resp = client.get("/metrics/")
    assert resp.status_code == 200
    assert "tsp_solver_info" in resp.text


# ---------------------------------------------------------------------------
# Observability module unit tests
# ---------------------------------------------------------------------------


def test_observability_init_does_not_crash() -> None:
    """init_observability should be safe to call with default settings."""
    from app.config import Settings
    from app.observability import init_observability

    test_settings = Settings(
        otel_enabled=False,
        prometheus_enabled=True,
        log_format="console",
        log_level="WARNING",
    )
    # Should not raise
    init_observability(test_settings)


def test_normalize_path_collapses_uuids() -> None:
    """UUID segments in paths should be collapsed to {id}."""
    from app.middleware import _normalize_path

    path = "/api/v1/tsp/jobs/550e8400-e29b-41d4-a716-446655440000/progress"
    assert _normalize_path(path) == "/api/v1/tsp/jobs/{id}/progress"


def test_normalize_path_preserves_non_uuid() -> None:
    """Paths without UUIDs should be unchanged."""
    from app.middleware import _normalize_path

    path = "/api/v1/tsp/health"
    assert _normalize_path(path) == "/api/v1/tsp/health"
