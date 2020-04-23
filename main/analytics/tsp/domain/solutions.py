import copy
import time
import networkx as nx


class PartialSolution:
    _HC: list
    _Graph: nx.Graph = None
    _n: int = 0

    @staticmethod
    def set_graph(g):
        """
        :type g: nx.Graph
        """
        PartialSolution._Graph = g
        PartialSolution._n = len(list(g.nodes))

    def __init__(self, hc: list):
        """
        :type hc: list
        """
        self._HC = hc

    @property
    def cost(self):
        """
        Returns cost of partial solution.
        """
        c: int = 0
        for i in range(len(self._HC) - 1):
            c = c + PartialSolution._Graph.get_edge_data(self._HC[i], self._HC[i + 1])['weight']
        if len(self._HC) == PartialSolution._n:
            c = c + PartialSolution._Graph.get_edge_data(self._HC[len(self._HC) - 1], self._HC[0])['weight']
        return c


class ValidSolution(PartialSolution):

    @property
    def cost(self):
        """
        Return cost of solution.
        """
        c: int = 0
        for i in range(len(self._HC) - 1):
            c = c + PartialSolution._Graph.get_edge_data(self._HC[i], self._HC[i + 1])['weight']
        c = c + PartialSolution._Graph.get_edge_data(self._HC[len(self._HC) - 1], self._HC[0])['weight']
        return c

    def _gain(self, i, j):
        """
        Return gain/loss after changing places of i-th ang j-th vertices in solution.
        """
        if i == j:
            return 0
        if i % PartialSolution._n == (j + 1) % PartialSolution._n:
            return \
                PartialSolution._Graph.get_edge_data(self._HC[i % PartialSolution._n],
                                                     self._HC[(i + 1) % PartialSolution._n])[
                    'weight'] + \
                PartialSolution._Graph.get_edge_data(self._HC[j % PartialSolution._n],
                                                     self._HC[(j - 1) % PartialSolution._n])[
                    'weight'] - \
                PartialSolution._Graph.get_edge_data(self._HC[i % PartialSolution._n],
                                                     self._HC[(j - 1) % PartialSolution._n])[
                    'weight'] - \
                PartialSolution._Graph.get_edge_data(self._HC[j % PartialSolution._n],
                                                     self._HC[(i + 1) % PartialSolution._n])[
                    'weight']
        if i % PartialSolution._n == (j - 1) % PartialSolution._n:
            return \
                PartialSolution._Graph.get_edge_data(self._HC[i % PartialSolution._n],
                                                     self._HC[(i - 1) % PartialSolution._n])[
                    'weight'] + \
                PartialSolution._Graph.get_edge_data(self._HC[j % PartialSolution._n],
                                                     self._HC[(j + 1) % PartialSolution._n])[
                    'weight'] - \
                PartialSolution._Graph.get_edge_data(self._HC[i % PartialSolution._n],
                                                     self._HC[(j + 1) % PartialSolution._n])[
                    'weight'] - \
                PartialSolution._Graph.get_edge_data(self._HC[j % PartialSolution._n],
                                                     self._HC[(i - 1) % PartialSolution._n])[
                    'weight']

        c = PartialSolution._Graph.get_edge_data(self._HC[i % PartialSolution._n], self._HC[(i + 1) % PartialSolution._n])[
                'weight'] + \
            PartialSolution._Graph.get_edge_data(self._HC[i % PartialSolution._n], self._HC[(i - 1) % PartialSolution._n])[
                'weight'] + \
            PartialSolution._Graph.get_edge_data(self._HC[j % PartialSolution._n], self._HC[(j + 1) % PartialSolution._n])[
                'weight'] + \
            PartialSolution._Graph.get_edge_data(self._HC[j % PartialSolution._n], self._HC[(j - 1) % PartialSolution._n])[
                'weight'] - \
            PartialSolution._Graph.get_edge_data(self._HC[(i - 1) % PartialSolution._n], self._HC[j] % PartialSolution._n)[
                'weight'] - \
            PartialSolution._Graph.get_edge_data(self._HC[j % PartialSolution._n], self._HC[(i + 1) % PartialSolution._n])[
                'weight'] - \
            PartialSolution._Graph.get_edge_data(self._HC[i % PartialSolution._n], self._HC[(j + 1) % PartialSolution._n])[
                'weight'] - \
            PartialSolution._Graph.get_edge_data(self._HC[i % PartialSolution._n], self._HC[(j - 1) % PartialSolution._n])[
                'weight']
        return c

    def hill_climbing(self, max_time=60):
        """
        Hill-climb algorithm using switching 2 vertices as moving to the neighbour.
        """
        start: float = time.time()
        local_max: ValidSolution = copy.deepcopy(self)
        x: list = local_max._HC
        done = False
        while not done:
            done = True
            g0 = 0
            i0 = 0
            j0 = 0
            for i in range(len(x)):
                for j in range(len(x)):
                    g = local_max._gain(i, j)
                    if g > g0:
                        g0 = g
                        i0 = i
                        j0 = j
            if g0 > 0:
                temp = x[i0]
                x[i0] = x[j0]
                x[j0] = temp
                done = False
            end = time.time()
            if end - start > max_time - 0.001:
                break
        return local_max

    def validate(self):
        if len(self._HC) == PartialSolution._n:
            if set(self._HC) == set(PartialSolution._Graph.nodes):
                return True
        return False
