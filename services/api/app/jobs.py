"""Phase 3 job coordination and persistence for async TSP execution."""

from __future__ import annotations

import copy
import json
import structlog
import threading
import time as _time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Protocol

from .monitoring import InMemoryProgressStore, ProgressStoreProtocol, RunTelemetrySampler
from .observability import TSP_JOBS_SUBMITTED, TSP_RUNS_COMPLETED, TSP_SOLVE_DURATION_SECONDS
from .services import TSPSolverService

_logger = structlog.stdlib.get_logger(__name__)


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class JobRepositoryProtocol(Protocol):
    """Storage interface for async jobs."""

    def upsert_job(self, job: dict[str, Any]) -> None:
        """Create or update a job record."""

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Return a job record by id if it exists."""


class InMemoryJobRepository:
    """Thread-safe in-memory job store (default/fallback)."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def upsert_job(self, job: dict[str, Any]) -> None:
        with self._lock:
            self._jobs[job["job_id"]] = copy.deepcopy(job)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            existing = self._jobs.get(job_id)
            return copy.deepcopy(existing) if existing else None


class PostgresJobRepository:
    """Postgres-backed job store for Timescale/Postgres deployments."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._init_schema()

    def _connect(self) -> Any:
        try:
            import psycopg  # pyright: ignore[reportMissingImports]
        except ModuleNotFoundError as exc:  # pragma: no cover - depends on runtime env
            raise RuntimeError(
                "Postgres job store requires psycopg. Install with: pip install psycopg[binary]"
            ) from exc
        return psycopg.connect(self._database_url)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tsp_jobs (
                        job_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )

    def upsert_job(self, job: dict[str, Any]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tsp_jobs (job_id, status, payload, created_at, updated_at)
                    VALUES (%s, %s, %s::jsonb, NOW(), NOW())
                    ON CONFLICT (job_id) DO UPDATE
                    SET status = EXCLUDED.status,
                        payload = EXCLUDED.payload,
                        updated_at = NOW()
                    """,
                    (job["job_id"], job["status"], json.dumps(job)),
                )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload FROM tsp_jobs WHERE job_id = %s", (job_id,))
                row = cur.fetchone()
                if not row:
                    return None
                payload = row[0]
                if isinstance(payload, str):
                    return json.loads(payload)
                return payload


def build_job_repository(database_url: str | None) -> JobRepositoryProtocol:
    """Build persistence backend, preferring Postgres when configured."""
    if database_url and database_url.startswith(("postgres://", "postgresql://")):
        try:
            return PostgresJobRepository(database_url)
        except Exception as exc:
            _logger.warning(
                "Postgres job store unavailable, falling back to in-memory: %s", exc
            )
            return InMemoryJobRepository()
    return InMemoryJobRepository()


_DEFAULT_MAX_WORKERS = 4

# If wall-clock execution exceeds this multiplier of the run's time_limit,
# a warning is logged.  The algorithms themselves enforce the deadline;
# this is a diagnostic aid.
_OVERRUN_WARN_FACTOR = 2.0


class TSPJobCoordinator:
    """Coordinator that executes one or more algorithm runs per submitted job.

    Jobs are dispatched to a bounded :class:`~concurrent.futures.ThreadPoolExecutor`
    so that concurrency stays controllable under load.
    """

    def __init__(
        self,
        solver: TSPSolverService,
        repository: JobRepositoryProtocol,
        max_workers: int = _DEFAULT_MAX_WORKERS,
        progress_store: ProgressStoreProtocol | None = None,
        sample_interval: float = 1.0,
    ) -> None:
        self._solver = solver
        self._repository = repository
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tsp-job")
        self._progress_store: ProgressStoreProtocol = (
            progress_store if progress_store is not None else InMemoryProgressStore()
        )
        self._sample_interval = sample_interval

    # -- Lifecycle ----------------------------------------------------------

    def shutdown(self, wait: bool = False) -> None:
        """Shut down the worker pool, optionally waiting for in-flight jobs."""
        self._pool.shutdown(wait=wait)

    # -- Public API ---------------------------------------------------------

    def submit_job(self, graph: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
        """Persist and enqueue an async batch job."""
        job = self._create_job(graph=graph, runs=runs)
        self._repository.upsert_job(job)
        TSP_JOBS_SUBMITTED.labels(status="submitted").inc()

        self._pool.submit(self._run_job, job["job_id"])

        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "run_count": len(job["runs"]),
            "created_at": job["created_at"],
        }

    def run_job_sync(self, graph: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
        """Execute a batch request synchronously and return the completed job.

        Used by the ``/solve`` compatibility facade so the HTTP response is
        returned only after all runs finish.
        """
        job = self._create_job(graph=graph, runs=runs)
        self._repository.upsert_job(job)
        self._run_job(job["job_id"])

        completed = self._repository.get_job(job["job_id"])
        if not completed:
            raise RuntimeError("Job disappeared during execution")
        return completed

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self._repository.get_job(job_id)

    def cancel_job(self, job_id: str) -> dict[str, Any] | None:
        job = self._repository.get_job(job_id)
        if not job:
            return None

        if job["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
            return job

        job["cancel_requested"] = True
        if job["status"] == "QUEUED":
            job["status"] = "CANCELLED"
            for run in job["runs"]:
                if run["status"] == "QUEUED":
                    run["status"] = "CANCELLED"
                    run["finished_at"] = _utc_now()

        job["updated_at"] = _utc_now()
        self._repository.upsert_job(job)
        return job

    def get_progress(self, job_id: str) -> list[dict[str, Any]]:
        """Return all telemetry samples collected for a job.

        Args:
            job_id: Job identifier.

        Returns:
            List of sample dicts in insertion order; empty if none exist.
        """
        return self._progress_store.get_samples(job_id)

    def _create_job(self, graph: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
        """Build a fresh job record in QUEUED state without persisting it."""
        now = _utc_now()
        job_id = str(uuid.uuid4())

        run_records: list[dict[str, Any]] = []
        for index, run in enumerate(runs, start=1):
            run_records.append(
                {
                    "run_id": f"{job_id}-run-{index}",
                    "method": run["method"],
                    "time_limit": float(run.get("time_limit", 5.0)),
                    "population": int(run.get("population", 50)),
                    "mutate": bool(run.get("mutate", True)),
                    "simulation_type": str(run.get("simulation_type", "nearest")),
                    "status": "QUEUED",
                    "result": None,
                    "error": None,
                    "started_at": None,
                    "finished_at": None,
                }
            )

        return {
            "job_id": job_id,
            "status": "QUEUED",
            "created_at": now,
            "updated_at": now,
            "graph": graph,
            "runs": run_records,
            "cancel_requested": False,
            "error": None,
        }

    def _run_job(self, job_id: str) -> None:
        """Worker method executed in a background thread for each submitted job."""
        # Re-fetch to pick up any cancel that arrived between submit and thread start.
        job = self._repository.get_job(job_id)
        if not job or job["status"] == "CANCELLED" or job.get("cancel_requested"):
            return

        try:
            job["status"] = "RUNNING"
            job["updated_at"] = _utc_now()
            self._repository.upsert_job(job)

            graph = job["graph"]
            try:
                ctx = self._solver.load_graph_from_matrix(
                    matrix=graph["matrix"],
                    node_names=graph.get("names"),
                )
            except Exception as exc:
                # Graph loading failed — mark every queued run as failed up-front.
                now = _utc_now()
                for run in job["runs"]:
                    if run["status"] == "QUEUED":
                        run["status"] = "FAILED"
                        run["error"] = f"Graph load error: {exc}"
                        run["started_at"] = now
                        run["finished_at"] = now
                job["status"] = "FAILED"
                job["error"] = str(exc)
                job["updated_at"] = now
                self._repository.upsert_job(job)
                return

            for index in range(len(job["runs"])):
                refreshed = self._repository.get_job(job_id)
                if refreshed is None:
                    return
                if refreshed.get("cancel_requested"):
                    job["cancel_requested"] = True

                current_run = job["runs"][index]

                if job.get("cancel_requested"):
                    current_run["status"] = "CANCELLED"
                    current_run["finished_at"] = _utc_now()
                    job["updated_at"] = _utc_now()
                    self._repository.upsert_job(job)
                    continue

                current_run["status"] = "RUNNING"
                current_run["started_at"] = _utc_now()
                job["updated_at"] = _utc_now()
                self._repository.upsert_job(job)

                best_cost: float | None = None
                sampler = RunTelemetrySampler(
                    job["job_id"],
                    current_run["run_id"],
                    self._progress_store,
                    self._sample_interval,
                )
                sampler.start()
                try:
                    t0 = _time.monotonic()
                    result = self._solver.solve(
                        ctx=ctx,
                        method=current_run["method"],
                        max_time=current_run["time_limit"],
                        population_size=current_run["population"],
                        mutate=current_run["mutate"],
                        simulation_type=current_run["simulation_type"],
                    )
                    elapsed = _time.monotonic() - t0
                    if elapsed > current_run["time_limit"] * _OVERRUN_WARN_FACTOR:
                        _logger.warning(
                            "Run %s method=%s overran time limit "
                            "(limit=%.1fs, actual=%.1fs)",
                            current_run["run_id"],
                            current_run["method"],
                            current_run["time_limit"],
                            elapsed,
                        )
                    current_run["result"] = result
                    current_run["status"] = "COMPLETED"
                    best_cost = result.get("cost")
                    TSP_RUNS_COMPLETED.labels(method=current_run["method"], status="completed").inc()
                    TSP_SOLVE_DURATION_SECONDS.labels(method=current_run["method"]).observe(elapsed)
                except Exception as exc:
                    current_run["error"] = str(exc)
                    current_run["status"] = "FAILED"
                    best_cost = None
                    TSP_RUNS_COMPLETED.labels(method=current_run["method"], status="failed").inc()
                finally:
                    sampler.stop(best_cost=best_cost)

                current_run["finished_at"] = _utc_now()
                job["updated_at"] = _utc_now()
                self._repository.upsert_job(job)

            statuses = {run["status"] for run in job["runs"]}
            if job.get("cancel_requested") and statuses <= {"CANCELLED", "COMPLETED"}:
                job["status"] = "CANCELLED"
            elif "FAILED" in statuses:
                job["status"] = "FAILED"
            elif statuses <= {"COMPLETED"}:
                job["status"] = "COMPLETED"
            elif "RUNNING" in statuses or "QUEUED" in statuses:
                job["status"] = "RUNNING"
            else:
                job["status"] = "FAILED"

            job["updated_at"] = _utc_now()
            self._repository.upsert_job(job)

        except Exception as exc:
            job = self._repository.get_job(job_id)
            if not job:
                return
            job["status"] = "FAILED"
            job["error"] = str(exc)
            job["updated_at"] = _utc_now()
            self._repository.upsert_job(job)
