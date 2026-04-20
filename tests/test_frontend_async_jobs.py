"""Tests for Phase 4 frontend async job flow via APIClient."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from frontend.api_client import APIClient


_SMALL_MATRIX = [
    [0, 10, 15, 20],
    [10, 0, 35, 25],
    [15, 35, 0, 30],
    [20, 25, 30, 0],
]


@pytest.fixture()
def api_client(client: TestClient) -> APIClient:
    """APIClient wired to the FastAPI TestClient transport."""
    api = APIClient.__new__(APIClient)
    api.base_url = "http://testserver"
    api.client = client  # type: ignore[assignment]
    return api


# ------------------------------------------------------------------
# submit_job / get_job_status / get_job_result
# ------------------------------------------------------------------


def test_submit_job_returns_job_id(api_client: APIClient) -> None:
    resp = api_client.submit_job(
        matrix=_SMALL_MATRIX,
        runs=[{"method": "Random", "time_limit": 0.1}],
        names=["A", "B", "C", "D"],
    )
    assert "job_id" in resp
    assert resp["status"] == "QUEUED"
    assert resp["run_count"] == 1


def test_get_job_status(api_client: APIClient) -> None:
    submit = api_client.submit_job(
        matrix=_SMALL_MATRIX,
        runs=[{"method": "Random", "time_limit": 0.1}],
    )
    job_id = submit["job_id"]
    # Allow job to finish
    time.sleep(1.0)

    status = api_client.get_job_status(job_id)
    assert status["job_id"] == job_id
    assert "runs" in status


def test_get_job_result_after_completion(api_client: APIClient) -> None:
    submit = api_client.submit_job(
        matrix=_SMALL_MATRIX,
        runs=[{"method": "HC", "time_limit": 0.5}],
    )
    job_id = submit["job_id"]
    time.sleep(2.0)

    result = api_client.get_job_result(job_id)
    assert result["job_id"] == job_id
    assert len(result["runs"]) == 1
    run = result["runs"][0]
    assert run["status"] == "COMPLETED"
    assert run["result"] is not None
    assert "tour" in run["result"]
    assert "cost" in run["result"]


# ------------------------------------------------------------------
# poll_job_until_done
# ------------------------------------------------------------------


def test_poll_job_until_done(api_client: APIClient) -> None:
    submit = api_client.submit_job(
        matrix=_SMALL_MATRIX,
        runs=[{"method": "Random", "time_limit": 0.1}],
    )
    job_id = submit["job_id"]

    statuses_seen: list[str] = []

    def _on_status(payload: dict) -> None:
        statuses_seen.append(payload["status"])

    final = api_client.poll_job_until_done(
        job_id, poll_interval=0.2, timeout=10.0, on_status=_on_status,
    )

    assert final["status"] in {"COMPLETED", "FAILED"}
    assert len(statuses_seen) >= 1


def test_poll_job_timeout_raises(api_client: APIClient) -> None:
    """Submitting a long job with a tiny poll timeout should raise TimeoutError."""
    submit = api_client.submit_job(
        matrix=_SMALL_MATRIX,
        runs=[{"method": "Genetic", "time_limit": 1.0}],
    )
    job_id = submit["job_id"]

    with pytest.raises(TimeoutError, match="did not finish"):
        api_client.poll_job_until_done(job_id, poll_interval=0.05, timeout=0.1)


# ------------------------------------------------------------------
# cancel_job via APIClient
# ------------------------------------------------------------------


def test_cancel_job(api_client: APIClient) -> None:
    submit = api_client.submit_job(
        matrix=_SMALL_MATRIX,
        runs=[{"method": "MCTS", "time_limit": 1.0}],
    )
    job_id = submit["job_id"]

    cancel = api_client.cancel_job(job_id)
    assert cancel["job_id"] == job_id
    assert cancel["message"] == "Cancellation requested"


# ------------------------------------------------------------------
# Multi-run job
# ------------------------------------------------------------------


def test_multi_run_job(api_client: APIClient) -> None:
    submit = api_client.submit_job(
        matrix=_SMALL_MATRIX,
        runs=[
            {"method": "Random", "time_limit": 0.1},
            {"method": "HC", "time_limit": 0.5},
        ],
        names=["A", "B", "C", "D"],
    )
    assert submit["run_count"] == 2

    final = api_client.poll_job_until_done(
        submit["job_id"], poll_interval=0.2, timeout=15.0,
    )
    assert final["status"] in {"COMPLETED", "FAILED"}

    result = api_client.get_job_result(submit["job_id"])
    assert len(result["runs"]) == 2
