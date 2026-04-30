"""Basic TSP solving algorithms."""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

import networkx as nx

from analytics.tsp.domain.solutions import ValidSolution

if TYPE_CHECKING:
    pass


def hill_climbing_multiple(graph: nx.Graph, max_time: float = 60) -> ValidSolution:
    """Run hill climbing algorithm multiple times and return best solution.

    Calls hill climbing algorithm repeatedly for the given time budget and returns
    the best solution found.

    Args:
        graph: NetworkX graph representing the TSP instance
        max_time: Maximum computation time in seconds

    Returns:
        Best ValidSolution found within the time limit
    """
    start_time: float = time.time()
    num_nodes = len(list(graph.nodes))

    # Initialize with random solution
    local_max: ValidSolution = ValidSolution(
        random.sample(range(num_nodes), num_nodes)
    )

    while True:
        remaining_time = max_time - (time.time() - start_time)
        if remaining_time < 0.002:
            break

        # Generate new random tour and apply hill climbing
        random_tour = random.sample(range(num_nodes), num_nodes)
        candidate = ValidSolution(random_tour).hill_climbing(remaining_time - 0.001)

        # Keep best solution
        if candidate.cost < local_max.cost:
            local_max = candidate

    return local_max
