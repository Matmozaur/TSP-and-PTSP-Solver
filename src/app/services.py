"""TSP Solver Service - orchestrates algorithm execution."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

import networkx as nx
import numpy as np
from analytics.tsp.domain.basic_solvers import hill_climbing_multiple
from analytics.tsp.domain.solutions import PartialSolution, ValidSolution
from analytics.tsp.genetic.genetic_solver import GeneticSolver
from analytics.tsp.mcts.mct import MCT

if TYPE_CHECKING:
    pass


class TSPSolverService:
    """Service for solving Traveling Salesman Problem using various algorithms."""

    def __init__(self, media_path: Path) -> None:
        """Initialize TSP solver service.

        Args:
            media_path: Path where to save generated images
        """
        self.graph: nx.Graph | None = None
        self.graph_display: nx.Graph | None = None
        self.media_path = media_path
        self.media_path.mkdir(parents=True, exist_ok=True)

    def load_graph_from_matrix(
        self, matrix: list[list[float]], node_names: list[str] | None = None
    ) -> dict:
        """Load graph from adjacency matrix.

        Args:
            matrix: Adjacency matrix
            node_names: Optional node labels

        Returns:
            Graph metadata
        """
        m = np.array(matrix)
        self.graph = nx.from_numpy_array(m)

        # Create display graph with optional labels
        self.graph_display = self.graph.copy()
        if node_names:
            mapping = {i: name for i, name in enumerate(node_names)}
            self.graph_display = nx.relabel_nodes(self.graph_display, mapping, copy=True)

        # Set graph for PartialSolution
        PartialSolution.set_graph(self.graph)

        return {
            "nodes": list(self.graph.nodes()),
            "edges": list(self.graph.edges()),
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
        }

    def solve_random(self) -> ValidSolution:
        """Generate random solution.

        Returns:
            Random TSP solution

        Raises:
            RuntimeError: If no graph is loaded
        """
        if self.graph is None:
            raise RuntimeError("No graph loaded. Call load_graph_from_matrix first.")

        import random

        tour = random.sample(range(len(list(self.graph.nodes))), len(list(self.graph.nodes)))
        return ValidSolution(tour)

    def solve_hill_climbing(self, max_time: float) -> ValidSolution:
        """Solve using Hill Climbing algorithm.

        Args:
            max_time: Maximum computation time in seconds

        Returns:
            Best TSP solution found

        Raises:
            RuntimeError: If no graph is loaded
        """
        if self.graph is None:
            raise RuntimeError("No graph loaded. Call load_graph_from_matrix first.")

        return hill_climbing_multiple(self.graph, max_time=max_time)

    def solve_genetic(self, max_time: float, population_size: int, mutate: bool) -> ValidSolution:
        """Solve using Genetic Algorithm.

        Args:
            max_time: Maximum computation time
            population_size: Population size for GA
            mutate: Whether to enable mutation

        Returns:
            Best TSP solution found

        Raises:
            RuntimeError: If no graph is loaded
        """
        if self.graph is None:
            raise RuntimeError("No graph loaded. Call load_graph_from_matrix first.")

        solver = GeneticSolver(size=population_size, g=self.graph)
        return solver.solve(max_time, mutate=mutate)

    def solve_mcts(self, max_time: float, simulation_type: str = "nearest") -> ValidSolution:
        """Solve using Monte Carlo Tree Search.

        Args:
            max_time: Maximum computation time
            simulation_type: Type of simulation (nearest, lottery)

        Returns:
            Best TSP solution found

        Raises:
            RuntimeError: If no graph is loaded
        """
        if self.graph is None:
            raise RuntimeError("No graph loaded. Call load_graph_from_matrix first.")

        mct = MCT(PartialSolution([]), lottery=simulation_type)
        mct.build_tree(max_time)
        return mct.choose_solution()

    def solve(
        self,
        method: str,
        max_time: float,
        population_size: int = 50,
        mutate: bool = True,
        simulation_type: str = "nearest",
    ) -> dict:
        """Main solve method that dispatches to appropriate algorithm.

        Args:
            method: Algorithm to use (Random, HC, Genetic, MCTS)
            max_time: Maximum computation time
            population_size: Population size for GA
            mutate: Enable mutation for GA
            simulation_type: Simulation type for MCTS

        Returns:
            Solution with metadata and execution time

        Raises:
            ValueError: If method is invalid
            RuntimeError: If no graph is loaded
        """
        if method not in ["Random", "HC", "Genetic", "MCTS"]:
            raise ValueError(f"Unknown method: {method}")

        start_time = time.time()

        if method == "Random":
            solution = self.solve_random()
        elif method == "HC":
            solution = self.solve_hill_climbing(max_time)
        elif method == "Genetic":
            solution = self.solve_genetic(max_time, population_size, mutate)
        else:  # MCTS
            solution = self.solve_mcts(max_time, simulation_type)

        execution_time = time.time() - start_time

        return {
            "tour": list(solution.solution),
            "cost": float(solution.cost),
            "method": method,
            "execution_time": execution_time,
        }

    def save_graph_visualization(self, filename: str = "graph.png") -> Path:
        """Save graph visualization to file.

        Args:
            filename: Output filename

        Returns:
            Path to saved image

        Raises:
            RuntimeError: If no graph is loaded
        """
        if self.graph_display is None:
            raise RuntimeError("No graph loaded. Call load_graph_from_matrix first.")

        import matplotlib.pyplot as plt

        output_path = self.media_path / filename

        pos = nx.circular_layout(self.graph_display)
        nx.draw_networkx(self.graph_display, pos)

        # Add edge labels with weights
        labels = nx.get_edge_attributes(self.graph_display, "weight")
        if labels:
            nx.draw_networkx_edge_labels(self.graph_display, pos, edge_labels=labels)

        try:
            plt.savefig(str(output_path), dpi=300, bbox_inches="tight")
        except PermissionError:
            import tempfile

            stem = Path(filename).stem or "graph"
            suffix = Path(filename).suffix or ".png"
            fallback_dir = Path(tempfile.gettempdir()) / "tsp-ptsp-media"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            output_path = fallback_dir / f"{stem}_{int(time.time() * 1000)}{suffix}"
            plt.savefig(str(output_path), dpi=300, bbox_inches="tight")
        finally:
            plt.close()

        return output_path
