import copy
import time
import networkx as nx


class PartialSolution:
    HC: list
    Graph: nx.Graph = None
    n: int = 0

    @staticmethod
    def set_graph(g):
        """
        :type g: nx.Graph
        """
        PartialSolution.Graph = g
        PartialSolution.n = len(list(g.nodes))

    def __init__(self, hc: list):
        """
        :type hc: list
        """
        self.HC = hc

    @property
    def cost(self):
        """
        Returns cost of partial solution.
        """
        c: int = 0
        for i in range(len(self.HC) - 1):
            c = c + PartialSolution.Graph.get_edge_data(self.HC[i], self.HC[i + 1])['weight']
        return c


class ValidSolution(PartialSolution):

    @property
    def cost(self):
        """
        Return cost of solution.
        """
        c: int = 0
        for i in range(len(self.HC) - 1):
            c = c + PartialSolution.Graph.get_edge_data(self.HC[i], self.HC[i + 1])['weight']
        c = c + PartialSolution.Graph.get_edge_data(self.HC[len(self.HC) - 1], self.HC[0])['weight']
        return c

    def gain(self, i, j):
        """
        Return gain/loss after changing places of i-th ang j-th vertices in solution.
        """
        if i == j:
            return 0
        if i % PartialSolution.n == (j + 1) % PartialSolution.n:
            return \
                PartialSolution.Graph.get_edge_data(self.HC[i % PartialSolution.n],
                                                    self.HC[(i + 1) % PartialSolution.n])[
                    'weight'] + \
                PartialSolution.Graph.get_edge_data(self.HC[j % PartialSolution.n],
                                                    self.HC[(j - 1) % PartialSolution.n])[
                    'weight'] - \
                PartialSolution.Graph.get_edge_data(self.HC[i % PartialSolution.n],
                                                    self.HC[(j - 1) % PartialSolution.n])[
                    'weight'] - \
                PartialSolution.Graph.get_edge_data(self.HC[j % PartialSolution.n],
                                                    self.HC[(i + 1) % PartialSolution.n])[
                    'weight']
        if i % PartialSolution.n == (j - 1) % PartialSolution.n:
            return \
                PartialSolution.Graph.get_edge_data(self.HC[i % PartialSolution.n],
                                                    self.HC[(i - 1) % PartialSolution.n])[
                    'weight'] + \
                PartialSolution.Graph.get_edge_data(self.HC[j % PartialSolution.n],
                                                    self.HC[(j + 1) % PartialSolution.n])[
                    'weight'] - \
                PartialSolution.Graph.get_edge_data(self.HC[i % PartialSolution.n],
                                                    self.HC[(j + 1) % PartialSolution.n])[
                    'weight'] - \
                PartialSolution.Graph.get_edge_data(self.HC[j % PartialSolution.n],
                                                    self.HC[(i - 1) % PartialSolution.n])[
                    'weight']

        c = PartialSolution.Graph.get_edge_data(self.HC[i % PartialSolution.n], self.HC[(i + 1) % PartialSolution.n])[
                'weight'] + \
            PartialSolution.Graph.get_edge_data(self.HC[i % PartialSolution.n], self.HC[(i - 1) % PartialSolution.n])[
                'weight'] + \
            PartialSolution.Graph.get_edge_data(self.HC[j % PartialSolution.n], self.HC[(j + 1) % PartialSolution.n])[
                'weight'] + \
            PartialSolution.Graph.get_edge_data(self.HC[j % PartialSolution.n], self.HC[(j - 1) % PartialSolution.n])[
                'weight'] - \
            PartialSolution.Graph.get_edge_data(self.HC[(i - 1) % PartialSolution.n], self.HC[j] % PartialSolution.n)[
                'weight'] - \
            PartialSolution.Graph.get_edge_data(self.HC[j % PartialSolution.n], self.HC[(i + 1) % PartialSolution.n])[
                'weight'] - \
            PartialSolution.Graph.get_edge_data(self.HC[i % PartialSolution.n], self.HC[(j + 1) % PartialSolution.n])[
                'weight'] - \
            PartialSolution.Graph.get_edge_data(self.HC[i % PartialSolution.n], self.HC[(j - 1) % PartialSolution.n])[
                'weight']
        return c

    def hill_climbing(self, max_time=60):
        """
        Hill-climb algorithm using switching 2 vertices as moving to the neighbour.
        """
        start: float = time.time()
        local_max: ValidSolution = copy.deepcopy(self)
        x: list = local_max.HC
        done = False
        while not done:
            done = True
            g0 = 0
            i0 = 0
            j0 = 0
            for i in range(len(x)):
                for j in range(len(x)):
                    g = local_max.gain(i, j)
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
