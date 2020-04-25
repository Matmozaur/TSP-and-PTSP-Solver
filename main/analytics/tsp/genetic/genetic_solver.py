import random
import time
import networkx as nx

from main.analytics.tsp.domain.solutions import ValidSolution


class GeneticSolver:

    @staticmethod
    def initialize_random_population(size, g):
        return [ValidSolution(random.sample(range(len(list(g.nodes))), len(list(g.nodes)))) for _ in range(size)]

    def __init__(self, size, g, population=None):
        """
        :type population: list
        :type size: int
        :type g: nx.Graph
        """
        self.size = size
        self.Graph = g
        if population is not None:
            self.population = population
        else:
            self.population = GeneticSolver.initialize_random_population(size, g)

    def crossover(self, x, y, h=None):
        """
        :type x: ValidSolution
        :type y: ValidSolution
        :type h: int
        """
        x = x.HC
        y = y.HC
        n = len(list(self.Graph.nodes))
        if h is None:
            h = random.randrange(int(n * 0.25), int(n * 0.75))
        j = random.randrange(n)
        T = set()
        d = [0] * n
        for i in range(h):
            d[i] = y[(i + j) % n]
            T.add(d[i])
        i = h
        for j in range(n):
            if x[j] not in T:
                d[i] = x[j]
                i = i + 1
        j = random.randrange(self.size)
        T = set()
        c = [0] * n
        for i in range(h):
            c[i] = x[(i + j) % n]
            T.add(c[i])
        i = h
        for j in range(n):
            if y[j] not in T:
                c[i] = y[j]
                i = i + 1
        c = ValidSolution(c)
        d = ValidSolution(d)
        return c, d

    @staticmethod
    def mutation(x, alg='hc', max_time=0.01):
        """
        :type x: ValidSolution
        :type max_time: float
        :type alg: str
        """
        if alg == 'hc':
            return x.hill_climbing(max_time)
        else:
            return x

    def generate_new_generation(self, h=None, mutate=True, mut_args=None):
        """
        :type mut_args: dict
        :type mutate: bool
        :type h: int
        """
        if mut_args is None:
            mut_args = {'alg': 'hc', 'max_time': 5}
        random.shuffle(self.population)
        new_generation = []
        for X, Y in zip(self.population[::2], self.population[1::2]):
            c, d = self.crossover(X, Y, h)
            new_generation.append(c)
            new_generation.append(d)
        if mutate:
            new_generation = [self.mutation(a, mut_args['alg'], mut_args['max_time']) for a in new_generation]
        return new_generation

    def solve(self, max_time=60, h=None, mutate=True, mut_args=None):
        """
        :type h: int
        :type max_time: float
        :type mutate: bool
        :type mut_args: dict
        """
        if mut_args is None:
            mut_args = {'alg': 'hc', 'max_time': 5}
        start = time.time()
        self.population.sort(key=lambda a: a.cost)
        xbest = self.population[0]
        cbest = self.population[0].cost
        while 1:
            self.population += self.generate_new_generation(h, mutate, mut_args)
            self.population.sort(key=lambda a: a.cost)
            self.population = self.population[:self.size]
            ccurr = self.population[0].cost
            if ccurr < cbest:
                xbest = self.population[0]
                cbest = ccurr
            end = time.time()
            if end - start > max_time - 0.001:
                break
        return xbest
