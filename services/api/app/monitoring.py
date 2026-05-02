"""Phase 7 — Run telemetry: resource sampling and progress storage."""

from __future__ import annotations

import copy
import threading
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

import structlog

_logger = structlog.stdlib.get_logger(__name__)

# ---------------------------------------------------------------------------
# Optional psutil dependency
# ---------------------------------------------------------------------------

try:
    import psutil as _psutil  # pyright: ignore[reportMissingImports]

    _HAS_PSUTIL = True
except ImportError:
    _psutil = None  # type: ignore[assignment]
    _HAS_PSUTIL = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()


def _sample_resources() -> tuple[float | None, float | None]:
    """Return (cpu_percent, memory_mb) for the current process.

    Both values are ``None`` when psutil is not installed.
    ``cpu_percent`` uses a 0-second interval (non-blocking; returns the value
    accumulated since the *previous* call or process start).

    Returns:
        Tuple of (cpu_percent, memory_mb).  Either may be None.
    """
    if not _HAS_PSUTIL:
        return None, None
    try:
        proc = _psutil.Process()
        cpu = proc.cpu_percent(interval=None)
        mem_mb = proc.memory_info().rss / (1024 * 1024)
        return cpu, mem_mb
    except Exception as exc:  # pragma: no cover
        _logger.debug("Resource sampling failed: %s", exc)
        return None, None


def _make_sample(
    run_id: str,
    elapsed_seconds: float | None,
    cpu_percent: float | None,
    memory_mb: float | None,
    best_cost: float | None = None,
) -> dict[str, Any]:
    """Build a telemetry sample dict.

    Args:
        run_id: Identifier of the run this sample belongs to.
        elapsed_seconds: Seconds since the run started.
        cpu_percent: CPU usage percentage (None when psutil unavailable).
        memory_mb: RSS memory in megabytes (None when psutil unavailable).
        best_cost: Best tour cost known at sample time (None during run).

    Returns:
        Sample dict with keys: run_id, sampled_at, elapsed_seconds,
        cpu_percent, memory_mb, best_cost.
    """
    return {
        "run_id": run_id,
        "sampled_at": _utc_now(),
        "elapsed_seconds": elapsed_seconds,
        "cpu_percent": cpu_percent,
        "memory_mb": memory_mb,
        "best_cost": best_cost,
    }


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ProgressStoreProtocol(Protocol):
    """Storage interface for telemetry progress samples."""

    def add_sample(self, job_id: str, sample: dict[str, Any]) -> None:
        """Persist a single telemetry sample for a job.

        Args:
            job_id: Job the sample belongs to.
            sample: Sample dict produced by :func:`_make_sample`.
        """
        ...

    def get_samples(self, job_id: str) -> list[dict[str, Any]]:
        """Return all samples for a job in insertion order.

        Args:
            job_id: Job identifier.

        Returns:
            List of sample dicts; empty list if no samples exist.
        """
        ...


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------


class InMemoryProgressStore:
    """Thread-safe in-memory telemetry store (default/fallback).

    Samples are stored as deep copies so callers cannot mutate stored state.
    """

    def __init__(self) -> None:
        self._samples: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def add_sample(self, job_id: str, sample: dict[str, Any]) -> None:
        """Append a deep copy of *sample* to the list for *job_id*."""
        with self._lock:
            if job_id not in self._samples:
                self._samples[job_id] = []
            self._samples[job_id].append(copy.deepcopy(sample))

    def get_samples(self, job_id: str) -> list[dict[str, Any]]:
        """Return a shallow copy of the sample list for *job_id*."""
        with self._lock:
            return list(self._samples.get(job_id, []))


# ---------------------------------------------------------------------------
# Postgres / TimescaleDB implementation
# ---------------------------------------------------------------------------


class PostgresProgressStore:
    """Postgres-backed telemetry store with optional TimescaleDB hypertable.

    Table schema::

        tsp_run_progress(
            id          BIGSERIAL PRIMARY KEY,
            job_id      TEXT,
            run_id      TEXT,
            sampled_at  TIMESTAMPTZ,
            elapsed_seconds FLOAT8,
            cpu_percent FLOAT8,
            memory_mb   FLOAT8,
            best_cost   FLOAT8
        )

    After creating the table the constructor attempts to call
    ``create_hypertable`` so the table benefits from TimescaleDB when the
    extension is present.  The call is silently ignored on plain Postgres.
    """

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._init_schema()

    def _connect(self) -> Any:
        try:
            import psycopg  # pyright: ignore[reportMissingImports]
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError(
                "Postgres progress store requires psycopg. "
                "Install with: pip install psycopg[binary]"
            ) from exc
        return psycopg.connect(self._database_url)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tsp_run_progress (
                        id              BIGSERIAL PRIMARY KEY,
                        job_id          TEXT NOT NULL,
                        run_id          TEXT NOT NULL,
                        sampled_at      TIMESTAMPTZ NOT NULL,
                        elapsed_seconds FLOAT8,
                        cpu_percent     FLOAT8,
                        memory_mb       FLOAT8,
                        best_cost       FLOAT8
                    )
                    """
                )
                # Attempt to create a TimescaleDB hypertable.  This is a no-op
                # on plain Postgres and should never prevent table creation.
                try:
                    cur.execute(
                        "SELECT create_hypertable('tsp_run_progress', 'sampled_at', "
                        "if_not_exists => TRUE)"
                    )
                except Exception as exc:
                    _logger.debug(
                        "create_hypertable not available (plain Postgres?): %s", exc
                    )
                    conn.rollback()

    def add_sample(self, job_id: str, sample: dict[str, Any]) -> None:
        """Insert one sample row into ``tsp_run_progress``."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tsp_run_progress
                        (job_id, run_id, sampled_at, elapsed_seconds,
                         cpu_percent, memory_mb, best_cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        job_id,
                        sample["run_id"],
                        sample["sampled_at"],
                        sample.get("elapsed_seconds"),
                        sample.get("cpu_percent"),
                        sample.get("memory_mb"),
                        sample.get("best_cost"),
                    ),
                )

    def get_samples(self, job_id: str) -> list[dict[str, Any]]:
        """Return all samples for *job_id* ordered by insertion time."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT run_id, sampled_at, elapsed_seconds,
                           cpu_percent, memory_mb, best_cost
                    FROM tsp_run_progress
                    WHERE job_id = %s
                    ORDER BY id ASC
                    """,
                    (job_id,),
                )
                rows = cur.fetchall()
        return [
            {
                "run_id": row[0],
                "sampled_at": row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1]),
                "elapsed_seconds": row[2],
                "cpu_percent": row[3],
                "memory_mb": row[4],
                "best_cost": row[5],
            }
            for row in rows
        ]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_progress_store(database_url: str | None) -> ProgressStoreProtocol:
    """Build and return a :class:`ProgressStoreProtocol` implementation.

    Uses :class:`PostgresProgressStore` when *database_url* points at a
    Postgres/Timescale instance, otherwise falls back to
    :class:`InMemoryProgressStore`.

    Args:
        database_url: Optional Postgres connection string.

    Returns:
        A ready-to-use progress store.
    """
    if database_url and database_url.startswith(("postgres://", "postgresql://")):
        try:
            return PostgresProgressStore(database_url)
        except Exception as exc:
            _logger.warning(
                "Postgres progress store unavailable, falling back to in-memory: %s", exc
            )
    return InMemoryProgressStore()


# ---------------------------------------------------------------------------
# Background sampler
# ---------------------------------------------------------------------------


class RunTelemetrySampler:
    """Daemon thread that periodically records resource samples for one run.

    Usage::

        sampler = RunTelemetrySampler(job_id, run_id, store)
        sampler.start()
        try:
            result = solver.solve(...)
            best_cost = result.get("cost")
        except Exception:
            best_cost = None
            raise
        finally:
            sampler.stop(best_cost=best_cost)

    It also supports the context-manager protocol::

        with RunTelemetrySampler(job_id, run_id, store) as sampler:
            result = solver.solve(...)
    """

    def __init__(
        self,
        job_id: str,
        run_id: str,
        store: ProgressStoreProtocol,
        sample_interval: float = 1.0,
    ) -> None:
        self._job_id = job_id
        self._run_id = run_id
        self._store = store
        self._sample_interval = sample_interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_time: float | None = None

    # -- Context manager support -------------------------------------------

    def __enter__(self) -> RunTelemetrySampler:
        self.start()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.stop()

    # -- Public API --------------------------------------------------------

    def start(self) -> None:
        """Start the background sampling daemon thread."""
        import time as _time

        self._start_time = _time.monotonic()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._sample_loop,
            name=f"telemetry-{self._run_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self, best_cost: float | None = None) -> None:
        """Signal the sampler to stop and record a final sample.

        Args:
            best_cost: The best tour cost produced by the run, if available.
        """
        import time as _time

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._sample_interval + 2.0)

        # Record a final sample with the known best_cost.
        elapsed = (
            _time.monotonic() - self._start_time
            if self._start_time is not None
            else None
        )
        cpu, mem = _sample_resources()
        sample = _make_sample(
            run_id=self._run_id,
            elapsed_seconds=elapsed,
            cpu_percent=cpu,
            memory_mb=mem,
            best_cost=best_cost,
        )
        try:
            self._store.add_sample(self._job_id, sample)
        except Exception as exc:  # pragma: no cover
            _logger.debug("Failed to add final telemetry sample: %s", exc)

    # -- Internal ----------------------------------------------------------

    def _sample_loop(self) -> None:
        """Loop: wait for stop event or timeout, then record a sample."""
        import time as _time

        while not self._stop_event.wait(timeout=self._sample_interval):
            elapsed = (
                _time.monotonic() - self._start_time
                if self._start_time is not None
                else None
            )
            cpu, mem = _sample_resources()
            sample = _make_sample(
                run_id=self._run_id,
                elapsed_seconds=elapsed,
                cpu_percent=cpu,
                memory_mb=mem,
                best_cost=None,
            )
            try:
                self._store.add_sample(self._job_id, sample)
            except Exception as exc:  # pragma: no cover
                _logger.debug("Failed to add telemetry sample: %s", exc)
