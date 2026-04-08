"""TSP Solver Service - orchestrates algorithm execution.

Architecture note (Phase 1 seam):
  - ``ExecutorProtocol`` is the single interface that separates *what* to run from *how*
    to run it.  ``TSPSolverService`` only orchestrates; it never calls analytics code
    directly.
  - ``LocalPythonExecutor`` is the concrete implementation that wraps the existing Python
    algorithms.  It is the only executor right now; future Go workers will implement the
    same protocol.
  - ``TSPSolverService`` holds *no* mutable graph state of its own.  Graph state is
    confined to a single request: ``load_graph_from_matrix`` returns a ``GraphContext``
    that is passed explicitly into ``solve``.  This makes the service safe for concurrent
    use and easy to test in isolation.
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Protocol, TypedDict

import networkx as nx
import numpy as np


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


class LocalPythonExecutor:
    """Runs TSP algorithms in-process using the Python analytics package.

    This executor is intentionally stateless: all per-request data arrives
    via ``SolveRequest``.  The ``PartialSolution.set_graph`` call (which
    mutates class-level state in the analytics layer) is scoped inside each
    ``execute`` call so that the mutation is as localised as possible.
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

        # Prepare per-request class-level analytics state.
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
        """Initialise the service.

        Args:
            media_path: Directory where visualisation images are saved.
            executor: Algorithm executor to use.  Defaults to
                :class:`LocalPythonExecutor` when *None*.
        """
        self.media_path = media_path
        self.media_path.mkdir(parents=True, exist_ok=True)
        self._executor: ExecutorProtocol = executor or LocalPythonExecutor()

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
