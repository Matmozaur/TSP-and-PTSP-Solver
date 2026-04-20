"""API client for communicating with FastAPI backend."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_POLL_INTERVAL: float = 0.5
_DEFAULT_POLL_TIMEOUT: float = 600.0
_TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED", "CANCELLED"})


class APIClient:
    """Client for TSP/PTSP Solver API."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        """Initialize API client.

        Args:
            base_url: Base URL of the API
        """
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=120.0)

    def check_health(self) -> bool:
        """Check API health.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self.client.get("/api/v1/ptsp/health")
            return response.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Legacy synchronous solve (compatibility path)
    # ------------------------------------------------------------------

    def solve_tsp(
        self,
        matrix: list[list[float]],
        method: str,
        time_limit: float = 5.0,
        names: list[str] | None = None,
        population: int | None = 50,
        mutate: bool = True,
        simulation_type: str = "nearest",
    ) -> dict[str, Any]:
        """Solve TSP instance synchronously (legacy compatibility).

        Args:
            matrix: Adjacency matrix
            method: Solving method (Random, HC, Genetic, MCTS)
            time_limit: Time limit in seconds
            names: Optional node names
            population: Population size for genetic algorithm
            mutate: Enable mutation for genetic algorithm
            simulation_type: Simulation type for MCTS

        Returns:
            Solution response

        Raises:
            httpx.HTTPError: If request fails
        """
        request_body = {
            "graph": {"matrix": matrix, "names": names},
            "method": method,
            "time_limit": time_limit,
            "population": population,
            "mutate": mutate,
            "simulation_type": simulation_type,
        }

        response = self.client.post("/api/v1/tsp/solve", json=request_body)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Async job API (Phase 4)
    # ------------------------------------------------------------------

    def submit_job(
        self,
        matrix: list[list[float]],
        runs: list[dict[str, Any]],
        names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Submit an async TSP batch job.

        Args:
            matrix: Adjacency matrix.
            runs: List of algorithm run configurations, each containing
                ``method``, ``time_limit``, and optional ``population``,
                ``mutate``, ``simulation_type`` keys.
            names: Optional node names.

        Returns:
            Job submission response with ``job_id``, ``status``,
            ``run_count``, and ``created_at``.

        Raises:
            httpx.HTTPError: If submission fails.
        """
        request_body: dict[str, Any] = {
            "graph": {"matrix": matrix, "names": names},
            "runs": runs,
        }

        response = self.client.post("/api/v1/tsp/jobs", json=request_body)
        response.raise_for_status()
        return response.json()

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get current status for a submitted job.

        Args:
            job_id: Job identifier returned by :meth:`submit_job`.

        Returns:
            Job status payload including per-run statuses.

        Raises:
            httpx.HTTPError: If request fails.
        """
        response = self.client.get(f"/api/v1/tsp/jobs/{job_id}")
        response.raise_for_status()
        return response.json()

    def get_job_result(self, job_id: str) -> dict[str, Any]:
        """Get final or partial results for a submitted job.

        Args:
            job_id: Job identifier returned by :meth:`submit_job`.

        Returns:
            Job result payload including per-run results.

        Raises:
            httpx.HTTPError: If request fails.
        """
        response = self.client.get(f"/api/v1/tsp/jobs/{job_id}/result")
        response.raise_for_status()
        return response.json()

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Request cancellation of a submitted job.

        Args:
            job_id: Job identifier returned by :meth:`submit_job`.

        Returns:
            Cancellation acknowledgment payload.

        Raises:
            httpx.HTTPError: If request fails.
        """
        response = self.client.post(f"/api/v1/tsp/jobs/{job_id}/cancel")
        response.raise_for_status()
        return response.json()

    def poll_job_until_done(
        self,
        job_id: str,
        *,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
        timeout: float = _DEFAULT_POLL_TIMEOUT,
        on_status: Any | None = None,
    ) -> dict[str, Any]:
        """Poll a job until it reaches a terminal status.

        This is a convenience wrapper around :meth:`get_job_status` that
        retries at *poll_interval* until the job status is one of
        ``COMPLETED``, ``FAILED``, or ``CANCELLED``.

        Args:
            job_id: Job identifier.
            poll_interval: Seconds between polls.
            timeout: Maximum total seconds to wait before raising.
            on_status: Optional callback ``(status_dict) -> None`` invoked
                after every successful poll.  Can be used to update a
                progress indicator in the frontend.

        Returns:
            The final job-status payload.

        Raises:
            TimeoutError: If the job does not finish within *timeout*.
            httpx.HTTPError: If any individual poll request fails.
        """
        deadline = time.monotonic() + timeout

        while True:
            status = self.get_job_status(job_id)
            if on_status is not None:
                on_status(status)

            if status.get("status") in _TERMINAL_STATUSES:
                return status

            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Job {job_id} did not finish within {timeout}s "
                    f"(last status: {status.get('status')})"
                )

            time.sleep(poll_interval)

    # ------------------------------------------------------------------
    # Graph utilities
    # ------------------------------------------------------------------

    def visualize_graph(
        self,
        matrix: list[list[float]],
        names: list[str] | None = None,
        filename: str = "graph.png",
    ) -> bytes:
        """Get graph visualization.

        Args:
            matrix: Adjacency matrix
            names: Optional node names
            filename: Output filename

        Returns:
            Image bytes

        Raises:
            httpx.HTTPError: If request fails
        """
        request_body = {
            "matrix": matrix,
            "names": names,
        }

        response = self.client.post(
            "/api/v1/tsp/visualize",
            json=request_body,
            params={"filename": filename},
        )
        response.raise_for_status()
        return response.content

    def get_tsp_methods(self) -> list[str]:
        """Get available TSP solving methods.

        Returns:
            List of method names
        """
        try:
            response = self.client.get("/api/v1/ptsp/methods")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("methods", [])]
        except Exception:
            return ["Random", "HC", "Genetic", "MCTS"]

    def close(self) -> None:
        """Close the client."""
        self.client.close()
