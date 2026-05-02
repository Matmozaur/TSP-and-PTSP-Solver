"""TSP Solver Service - orchestrates algorithm execution.

Architecture note (Phase 9 - Go-only production):
  - ``ExecutorProtocol`` is the single interface that separates *what* to run from *how*
    to run it.  ``TSPSolverService`` only orchestrates; it never calls analytics code
    directly.
  - **Production execution** uses Go workers exclusively via ``RemoteGoExecutor``.  The
    executor mode is controlled by ``GO_WORKER_MODE`` environment variable:
      * ``strict`` (default in production): Go worker failures raise exceptions; no fallback.
      * ``fallback`` (for development/testing): Falls back to Python on Go worker errors.
  - ``LocalPythonExecutor`` wraps the existing Python algorithms and is kept **only as a
    reference implementation** for parity testing and research.  It is not used in the
    production execution path.
  - ``TSPSolverService`` holds *no* mutable graph state of its own.  Graph state is
    confined to a single request: ``load_graph_from_matrix`` returns a ``GraphContext``
    that is passed explicitly into ``solve``.  This makes the service safe for concurrent
    use and easy to test in isolation.
"""

from __future__ import annotations

import random
import threading
import time
from pathlib import Path
from typing import Protocol, TypedDict

import structlog

import httpx
import networkx as nx
import numpy as np

_logger = structlog.stdlib.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data-transfer types shared across the execution boundary
# ---------------------------------------------------------------------------


class SolveRequest(TypedDict):
    """All inputs needed to run one TSP algorithm against one graph."""

    method: str
    graph: nx.Graph
    max_time: float
    population_size: int
    mutate: bool
    simulation_type: str


class SolveResult(TypedDict):
    """Normalised output produced by any executor implementation."""

    tour: list[int]
    cost: float
    method: str
    execution_time: float


class GraphContext(TypedDict):
    """Per-request graph data returned by ``load_graph_from_matrix``."""

    graph: nx.Graph
    graph_display: nx.Graph
    nodes: list[int]
    edges: list[tuple[int, int]]
    node_count: int
    edge_count: int


# ---------------------------------------------------------------------------
# Executor protocol — the seam for future Go workers
# ---------------------------------------------------------------------------


class ExecutorProtocol(Protocol):
    """Interface that every algorithm executor must satisfy.

    Implementations must be stateless with respect to graph data; all
    information required to run the algorithm is carried in *request*.
    """

    def execute(self, request: SolveRequest) -> SolveResult:
        """Run the requested algorithm and return a normalised result."""
        ...


# ---------------------------------------------------------------------------
# Local Python executor — wraps the existing analytics implementations
# ---------------------------------------------------------------------------


# Module-level lock guarding PartialSolution.set_graph which mutates class-level
# analytics state.  All LocalPythonExecutor instances share this lock so that
# concurrent requests cannot race on the shared analytics graph reference.
_analytics_graph_lock = threading.Lock()


class LocalPythonExecutor:
    """Runs TSP algorithms in-process using the Python analytics package.

    **This executor is kept as a REFERENCE IMPLEMENTATION only.**  Production
    traffic should use Go workers via ``RemoteGoExecutor``.  This class exists
    for parity testing, research comparison, and development fallback scenarios.

    This executor is intentionally stateless: all per-request data arrives
    via ``SolveRequest``.  The ``PartialSolution.set_graph`` call (which
    mutates class-level state in the analytics layer) is scoped inside each
    ``execute`` call so that the mutation is as localised as possible.

    All calls are serialised through ``_analytics_graph_lock`` so that
    concurrent requests cannot race on the shared analytics class state.
    """

    def execute(self, request: SolveRequest) -> SolveResult:
        """Execute *request* and return a :class:`SolveResult`.

        Args:
            request: Fully-populated solve request.

        Returns:
            Solution tour, cost, method label, and wall-clock execution time.

        Raises:
            ValueError: If *request['method']* is not a recognised algorithm.
        """
        # Import here so the rest of the module has no hard dependency on the
        # analytics package — easier to tree-shake when packaging Go workers.
        from analytics.tsp.domain.basic_solvers import hill_climbing_multiple
        from analytics.tsp.domain.solutions import PartialSolution, ValidSolution
        from analytics.tsp.genetic.genetic_solver import GeneticSolver
        from analytics.tsp.mcts.mct import MCT

        method = request["method"]
        graph = request["graph"]
        max_time = request["max_time"]

        # PartialSolution.set_graph stores the graph as a class-level attribute
        # used by the analytics layer.  The lock covers both the mutation *and*
        # the subsequent algorithm execution so that no concurrent thread can
        # overwrite the graph reference while an algorithm is reading it.
        with _analytics_graph_lock:
            PartialSolution.set_graph(graph)

            start = time.time()

            if method == "Random":
                tour = random.sample(list(graph.nodes()), graph.number_of_nodes())
                solution: ValidSolution = ValidSolution(tour)

            elif method == "HC":
                solution = hill_climbing_multiple(graph, max_time=max_time)

            elif method == "Genetic":
                solver = GeneticSolver(size=request["population_size"], g=graph)
                solution = solver.solve(max_time, mutate=request["mutate"])

            elif method == "MCTS":
                mct = MCT(PartialSolution([]), lottery=request["simulation_type"])
                mct.build_tree(max_time)
                solution = mct.choose_solution()

            else:
                raise ValueError(f"Unknown method: {method}")

            execution_time = time.time() - start

        return SolveResult(
            tour=list(solution.solution),
            cost=float(solution.cost),
            method=method,
            execution_time=execution_time,
        )


# ---------------------------------------------------------------------------
# Orchestration service — delegates execution, owns graph loading & I/O
# ---------------------------------------------------------------------------


class GoWorkerError(Exception):
    """Raised when a Go worker call fails and strict mode is enabled."""

    def __init__(self, method: str, url: str, cause: Exception | None = None) -> None:
        self.method = method
        self.url = url
        self.cause = cause
        super().__init__(f"Go worker call failed for method={method} at {url}")


class RemoteGoExecutor:
    """Delegates algorithm execution to Go workers.

    **Production executor** — all TSP algorithms are executed by Go workers.
    The ``strict`` parameter controls error handling:
      - ``strict=True`` (default): Go worker failures raise ``GoWorkerError``.
        This is the production mode; there is no fallback to Python.
      - ``strict=False``: Falls back to the provided fallback executor on error.
        This is for development and testing only.
    """

    _REMOTE_METHODS = {"Random", "HC", "Genetic", "MCTS"}

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 30.0,
        fallback: ExecutorProtocol | None = None,
        method_urls: dict[str, str] | None = None,
        *,
        strict: bool = True,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._fallback: ExecutorProtocol | None = fallback if not strict else None
        self._strict = strict
        self._method_urls = {
            method: url.rstrip("/")
            for method, url in (method_urls or {}).items()
            if method in self._REMOTE_METHODS and url
        }
        self._client = httpx.Client(base_url=self._base_url, timeout=self._timeout_seconds)
        self._clients_by_base_url: dict[str, httpx.Client] = {
            self._base_url: self._client,
        }
        self._closed = False

    # -- Resource management ------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client, releasing sockets."""
        if not self._closed:
            for client in self._clients_by_base_url.values():
                client.close()
            self._closed = True

    def __enter__(self) -> RemoteGoExecutor:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    # -- Execution ----------------------------------------------------------

    def execute(self, request: SolveRequest) -> SolveResult:
        method = request["method"]
        if method not in self._REMOTE_METHODS:
            # Non-remote methods (future expansion) — use fallback if available
            if self._fallback is not None:
                return self._fallback.execute(request)
            raise ValueError(f"Method {method!r} is not supported by Go workers")

        graph = request["graph"]
        matrix = nx.to_numpy_array(graph, dtype=float).tolist()

        payload = {
            "method": method,
            "matrix": matrix,
            "max_time": request["max_time"],
            "population_size": request["population_size"],
            "mutate": request["mutate"],
            "simulation_type": request["simulation_type"],
        }

        target_base_url = self._method_urls.get(method, self._base_url)
        client = self._clients_by_base_url.get(target_base_url)
        if client is None:
            client = httpx.Client(base_url=target_base_url, timeout=self._timeout_seconds)
            self._clients_by_base_url[target_base_url] = client

        try:
            response = client.post("/solve", json=payload)
            response.raise_for_status()
            data = response.json()

            return SolveResult(
                tour=[int(node) for node in data["tour"]],
                cost=float(data["cost"]),
                method=str(data.get("method", method)),
                execution_time=float(data["execution_time"]),
            )
        except Exception as exc:
            if self._strict:
                _logger.error(
                    "Go worker call failed for method=%s at %s (strict mode, no fallback)",
                    method,
                    target_base_url,
                    exc_info=True,
                )
                raise GoWorkerError(method, target_base_url, exc) from exc

            _logger.warning(
                "Go worker call failed for method=%s at %s, falling back to local executor",
                method,
                target_base_url,
                exc_info=True,
            )
            assert self._fallback is not None  # guaranteed by __init__ when strict=False
            return self._fallback.execute(request)


def build_executor(
    *,
    go_worker_enabled: bool,
    go_worker_url: str,
    go_worker_url_random_hc: str,
    go_worker_url_genetic: str,
    go_worker_url_mcts: str,
    go_worker_timeout_seconds: float,
    go_worker_mode: str = "strict",
) -> ExecutorProtocol:
    """Construct the algorithm executor based on runtime configuration.

    Args:
        go_worker_enabled: Whether to use Go workers at all.
        go_worker_url: Default Go worker URL.
        go_worker_url_random_hc: URL for Random/HC worker.
        go_worker_url_genetic: URL for Genetic worker.
        go_worker_url_mcts: URL for MCTS worker.
        go_worker_timeout_seconds: HTTP timeout for Go worker calls.
        go_worker_mode: Execution mode — ``"strict"`` (production, no fallback)
            or ``"fallback"`` (development, uses Python on Go errors).

    Returns:
        Configured executor implementing :class:`ExecutorProtocol`.
    """
    local_executor = LocalPythonExecutor()
    if not go_worker_enabled:
        return local_executor

    strict = go_worker_mode.lower() == "strict"

    return RemoteGoExecutor(
        base_url=go_worker_url,
        timeout_seconds=go_worker_timeout_seconds,
        fallback=local_executor if not strict else None,
        method_urls={
            "Random": go_worker_url_random_hc,
            "HC": go_worker_url_random_hc,
            "Genetic": go_worker_url_genetic,
            "MCTS": go_worker_url_mcts,
        },
        strict=strict,
    )


class TSPSolverService:
    """Orchestration layer for TSP solving.

    Responsibilities:
    - Load graph data from various input formats (:meth:`load_graph_from_matrix`).
    - Delegate algorithm execution to an injected :class:`ExecutorProtocol`.
    - Manage visualisation artefacts.

    This class holds **no mutable graph state** between calls.  Routes must
    pass the :class:`GraphContext` returned by :meth:`load_graph_from_matrix`
    into :meth:`solve` explicitly.  This makes each request fully independent
    and safe for concurrent use.
    """

    def __init__(
        self,
        media_path: Path,
        executor: ExecutorProtocol | None = None,
    ) -> None:
        # NOTE: close() is defined below — call it during app shutdown.
        """Initialise the service.

        Args:
            media_path: Directory where visualisation images are saved.
            executor: Algorithm executor to use.  Defaults to
                :class:`LocalPythonExecutor` when *None*.
        """
        self.media_path = media_path
        self.media_path.mkdir(parents=True, exist_ok=True)
        self._executor: ExecutorProtocol = executor or LocalPythonExecutor()

    def close(self) -> None:
        """Release resources held by the underlying executor."""
        if hasattr(self._executor, "close") and callable(self._executor.close):
            self._executor.close()

    # ------------------------------------------------------------------
    # Graph loading
    # ------------------------------------------------------------------

    def load_graph_from_matrix(
        self, matrix: list[list[float]], node_names: list[str] | None = None
    ) -> GraphContext:
        """Build a NetworkX graph from an adjacency matrix.

        Args:
            matrix: Square adjacency matrix.
            node_names: Optional display labels for nodes.

        Returns:
            :class:`GraphContext` carrying the graph objects and metadata.
                Pass this into :meth:`solve` or :meth:`save_graph_visualization`.
        """
        m = np.array(matrix)
        graph: nx.Graph = nx.from_numpy_array(m)

        graph_display: nx.Graph = graph.copy()
        if node_names:
            mapping = {i: name for i, name in enumerate(node_names)}
            graph_display = nx.relabel_nodes(graph_display, mapping, copy=True)

        return GraphContext(
            graph=graph,
            graph_display=graph_display,
            nodes=list(graph.nodes()),
            edges=list(graph.edges()),
            node_count=graph.number_of_nodes(),
            edge_count=graph.number_of_edges(),
        )

    # ------------------------------------------------------------------
    # Solving
    # ------------------------------------------------------------------

    def solve(
        self,
        ctx: GraphContext,
        method: str,
        max_time: float,
        population_size: int = 50,
        mutate: bool = True,
        simulation_type: str = "nearest",
    ) -> dict:
        """Dispatch a solve request to the configured executor.

        Args:
            ctx: Graph context produced by :meth:`load_graph_from_matrix`.
            method: Algorithm label — one of ``Random``, ``HC``, ``Genetic``,
                ``MCTS``.
            max_time: Wall-clock budget in seconds.
            population_size: GA population size.
            mutate: Enable mutation step in GA.
            simulation_type: Rollout strategy for MCTS
                (``nearest`` or ``lottery``).

        Returns:
            Dict with ``tour``, ``cost``, ``method``, and ``execution_time``.

        Raises:
            ValueError: If *method* is not recognised.
        """
        valid_methods = {"Random", "HC", "Genetic", "MCTS"}
        if method not in valid_methods:
            raise ValueError(f"Unknown method: {method!r}. Valid: {sorted(valid_methods)}")

        request = SolveRequest(
            method=method,
            graph=ctx["graph"],
            max_time=max_time,
            population_size=population_size,
            mutate=mutate,
            simulation_type=simulation_type,
        )
        return dict(self._executor.execute(request))

    def save_graph_visualization(
        self, ctx: GraphContext, filename: str = "graph.png"
    ) -> Path:
        """Save graph visualisation to file.

        Args:
            ctx: Graph context produced by :meth:`load_graph_from_matrix`.
            filename: Output filename.

        Returns:
            Path to the saved image.
        """
        import time as _time

        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        graph_display: nx.Graph = ctx["graph_display"]
        output_path = self.media_path / filename

        pos = nx.circular_layout(graph_display)
        nx.draw_networkx(graph_display, pos)

        # Add edge labels with weights
        labels = nx.get_edge_attributes(graph_display, "weight")
        if labels:
            nx.draw_networkx_edge_labels(graph_display, pos, edge_labels=labels)

        try:
            plt.savefig(str(output_path), dpi=300, bbox_inches="tight")
        except PermissionError:
            import tempfile

            stem = Path(filename).stem or "graph"
            suffix = Path(filename).suffix or ".png"
            fallback_dir = Path(tempfile.gettempdir()) / "tsp-ptsp-media"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            output_path = fallback_dir / f"{stem}_{int(_time.time() * 1000)}{suffix}"
            plt.savefig(str(output_path), dpi=300, bbox_inches="tight")
        finally:
            plt.close()

        return output_path
