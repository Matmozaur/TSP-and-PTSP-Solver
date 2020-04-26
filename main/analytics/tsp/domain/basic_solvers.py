import random
import time
import networkx as nx

from main.analytics.tsp.domain.solutions import ValidSolution


def hill_climbing_multiple(g, max_time=60):
    """
    Calls out hill climbing algorithm as long as possible and returns found best solution.
    :type max_time: float
    :type g: nx.Graph
    """
    start: float = time.time()
    local_max: ValidSolution = ValidSolution(random.sample(range(len(list(g.nodes))), len(list(g.nodes))))
    while 1:
        rem_time = max_time - time.time() + start
        if rem_time < 0.002:
            break
        x = ValidSolution(random.sample(range(len(list(g.nodes))),
                                        len(list(g.nodes)))).hill_climbing(rem_time - 0.001)
        if x.cost < local_max.cost:
            local_max = x
    return local_max
