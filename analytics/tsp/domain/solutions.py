"""TSP Solution classes representing partial and complete solutions."""

from __future__ import annotations

import copy
import time
from typing import TYPE_CHECKING, ClassVar

import networkx as nx

if TYPE_CHECKING:
    pass


class PartialSolution:
    """Represents a partial TSP solution."""

    Graph: ClassVar[nx.Graph | None] = None
    _n: ClassVar[int] = 0

    def __init__(self, tour: list[int]) -> None:
        """Initialize partial solution.

        Args:
            tour: Partial tour as list of node indices
        """
        self.solution = tour

    @classmethod
    def set_graph(cls, graph: nx.Graph) -> None:
        """Set the graph for all solutions to use.

        Args:
            graph: NetworkX graph representing the TSP instance
        """
        cls.Graph = graph
        cls._n = len(list(graph.nodes))

    @property
    def cost(self) -> float:
        """Calculate cost of partial solution.

        Returns:
            Total edge weight cost for the tour
        """
        if not self.solution or self.Graph is None:
            return 0

        total_cost: float = 0
        for i in range(len(self.solution) - 1):
            edge_data = self.Graph.get_edge_data(self.solution[i], self.solution[i + 1])
            if edge_data:
                total_cost += edge_data["weight"]

        # Add cost of returning to start if it's a complete tour
        if len(self.solution) == self._n:
            edge_data = self.Graph.get_edge_data(self.solution[-1], self.solution[0])
            if edge_data:
                total_cost += edge_data["weight"]

        return total_cost

    @property
    def valid(self) -> bool:
        """Check if this is a valid complete solution.

        Returns:
            True if solution visits all nodes exactly once
        """
        if len(self.solution) != self._n:
            return False
        if self.Graph is None:
            return False
        return set(self.solution) == set(self.Graph.nodes)


class ValidSolution(PartialSolution):
    """Represents a valid complete TSP solution."""

    @property
    def cost(self) -> float:
        """Calculate cost of valid solution.

        Returns:
            Total edge weight cost for the complete tour
        """
        if not self.solution or self.Graph is None or len(self.solution) != self._n:
            return float("inf")

        total_cost: float = 0

        # Add cost of all edges in the tour
        for i in range(len(self.solution) - 1):
            edge_data = self.Graph.get_edge_data(self.solution[i], self.solution[i + 1])
            if edge_data:
                total_cost += edge_data["weight"]

        # Add cost of returning to start
        edge_data = self.Graph.get_edge_data(self.solution[-1], self.solution[0])
        if edge_data:
            total_cost += edge_data["weight"]

        return total_cost

    def _get_edge_weight(self, u: int, v: int) -> float:
        """Get weight of edge between two nodes.

        Args:
            u: First node
            v: Second node

        Returns:
            Edge weight or infinity if edge doesn't exist
        """
        if self.Graph is None:
            return float("inf")
        edge_data = self.Graph.get_edge_data(u, v)
        return edge_data["weight"] if edge_data else float("inf")

    def _calculate_gain(self, i: int, j: int) -> float:
        """Calculate gain/loss from swapping positions i and j in the tour.

        Args:
            i: First position index
            j: Second position index

        Returns:
            Cost difference if swap is performed (positive = improvement)
        """
        if i == j or self.Graph is None:
            return 0

        # Normalize indices
        i_mod = i % self._n
        j_mod = j % self._n

        # Handle adjacent nodes in tour
        if i_mod == (j_mod + 1) % self._n:
            old_cost = (
                self._get_edge_weight(self.solution[i_mod], self.solution[(i_mod + 1) % self._n])
                + self._get_edge_weight(
                    self.solution[j_mod], self.solution[(j_mod - 1) % self._n]
                )
            )
            new_cost = (
                self._get_edge_weight(self.solution[i_mod], self.solution[(j_mod - 1) % self._n])
                + self._get_edge_weight(
                    self.solution[j_mod], self.solution[(i_mod + 1) % self._n]
                )
            )
            return old_cost - new_cost

        if i_mod == (j_mod - 1) % self._n:
            old_cost = (
                self._get_edge_weight(
                    self.solution[i_mod], self.solution[(i_mod - 1) % self._n]
                )
                + self._get_edge_weight(
                    self.solution[j_mod], self.solution[(j_mod + 1) % self._n]
                )
            )
            new_cost = (
                self._get_edge_weight(
                    self.solution[i_mod], self.solution[(j_mod + 1) % self._n]
                )
                + self._get_edge_weight(
                    self.solution[j_mod], self.solution[(i_mod - 1) % self._n]
                )
            )
            return old_cost - new_cost

        # General case for non-adjacent nodes
        old_cost = (
            self._get_edge_weight(self.solution[i_mod], self.solution[(i_mod + 1) % self._n])
            + self._get_edge_weight(self.solution[i_mod], self.solution[(i_mod - 1) % self._n])
            + self._get_edge_weight(self.solution[j_mod], self.solution[(j_mod + 1) % self._n])
            + self._get_edge_weight(self.solution[j_mod], self.solution[(j_mod - 1) % self._n])
        )

        new_cost = (
            self._get_edge_weight(self.solution[(i_mod - 1) % self._n], self.solution[j_mod])
            + self._get_edge_weight(
                self.solution[j_mod], self.solution[(i_mod + 1) % self._n]
            )
            + self._get_edge_weight(self.solution[i_mod], self.solution[(j_mod + 1) % self._n])
            + self._get_edge_weight(
                self.solution[i_mod], self.solution[(j_mod - 1) % self._n]
            )
        )

        return old_cost - new_cost

    def hill_climbing(self, max_time: float = 60) -> ValidSolution:
        """Apply hill-climbing optimization using 2-opt swaps.

        Improves solution by swapping pairs of nodes until no improvement found
        or time budget exceeded.

        Args:
            max_time: Maximum computation time in seconds

        Returns:
            Improved ValidSolution
        """
        start_time: float = time.time()
        local_max: ValidSolution = copy.deepcopy(self)
        tour = local_max.solution

        improved = True
        while improved:
            improved = False
            best_gain = 0
            best_i = 0
            best_j = 0

            # Find best swap
            for i in range(len(tour)):
                for j in range(len(tour)):
                    gain = local_max._calculate_gain(i, j)
                    if gain > best_gain:
                        best_gain = gain
                        best_i = i
                        best_j = j

            # Apply best swap if found
            if best_gain > 0:
                tour[best_i], tour[best_j] = tour[best_j], tour[best_i]
                improved = True

            # Check time limit
            if time.time() - start_time > max_time - 0.001:
                break

        return local_max
