"""Tests for Phase 7 monitoring / progress endpoint."""

from __future__ import annotations

import time


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

    # Wait long enough for the run to complete and for at least one sample to
    # be captured by the background sampler thread.
    time.sleep(1.5)

    progress_resp = client.get(f"/api/v1/tsp/jobs/{job_id}/progress")
    assert progress_resp.status_code == 200

    body = progress_resp.json()
    assert body["job_id"] == job_id
    assert len(body["runs"]) == 1

    run = body["runs"][0]
    assert run["method"] == "Random"

    # The stop() call always records a final sample, so there must be at least
    # one entry even if the run finishes before the periodic loop fires.
    assert len(run["samples"]) >= 1

    # The final sample must carry the best_cost from the completed solve.
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
            # elapsed_seconds may be None for edge cases but key must exist
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

    # Each run should have at least the final stop() sample.
    for run in body["runs"]:
        assert len(run["samples"]) >= 1
