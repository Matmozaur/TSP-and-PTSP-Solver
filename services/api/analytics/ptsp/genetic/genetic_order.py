import random
import time
from typing import Set

from analytics.ptsp.domain.basic_solvers_2005.basic_order_solvers import hill_climbing_ptsp_local
from analytics.ptsp.domain.basic_solvers_2005.metrics import MetricOrder


class GeneticOrderSolver:

    def __init__(self, size, ptsp_map, config, mutation_metric='hc', population=None):
        """
        :type ptsp_map: Map
        :type population: list
        :type size: int
        """
        self.size = size
        self.ptsp_map = ptsp_map
        self.config = config
        self.mutation_metric = mutation_metric
        if population is not None:
            self.population = population
        else:
            self.population = [random.sample(range(len(ptsp_map.cities)),
                                             len(ptsp_map.cities)) for _ in range(size)]

    @staticmethod
    def crossover(x, y, h=None):
        """
        :type x: list
        :type y: list
        :type h: int
        """
        n = len(x)
        if h is None:
            h = random.randrange(int(n * 0.25), int(n * 0.75))
        j = random.randrange(n)
        T: Set[int] = set()
        d = [0] * n
        for i in range(h):
            d[i] = y[(i + j) % n]
            T.add(d[i])
        i = h
        for j in range(n):
            if x[j] not in T:
                d[i] = x[j]
                i = i + 1
        j = random.randrange(n)
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
        return c, d

    def mutation(self, x, alg='hc', max_time=0.01):
        """
        :type x: ValidSolution
        :type max_time: float
        :type alg: str
        """
        if alg == 'hc':
            return hill_climbing_ptsp_local(self.ptsp_map, max_time, x, self.config, metric=self.mutation_metric)
        else:
            return x

    def generate_new_generation(self, h=None, mut_args=None, mutate=False):
        """
        :type mut_args: dict
        :type mutate: bool
        :type h: int
        """
        if mut_args is None:
            mut_args = {'alg': 'hc', 'max_time': 0.05}
        random.shuffle(self.population)
        new_generation = []
        for X, Y in zip(self.population[::2], self.population[1::2]):
            c, d = self.crossover(X, Y, h)
            new_generation.append(c)
            new_generation.append(d)
        if mutate:
            new_generation = [self.mutation(a, mut_args['alg'], mut_args['max_time']) for a in new_generation]
        return new_generation

    def solve(self, metric_name=None, max_time=60, h=None, mutate=False, mut_args=None):
        """
        :param metric_name:
        :type h: int
        :type max_time: float
        :type mutate: bool
        :type mut_args: dict
        """
        if mut_args is None:
            mut_args = {'alg': 'hc', 'max_time': 0.05}
        start = time.time()
        metric = MetricOrder(self.ptsp_map, metric_name, self.config)
        self.population.sort(key=lambda a: metric.metric(a))
        xbest = self.population[0]
        cbest = metric.metric(self.population[0])
        while 1:
            self.population += self.generate_new_generation(h, mut_args, mutate)
            self.population.sort(key=lambda a: metric.metric(a))
            self.population = self.population[:self.size]
            ccurr = metric.metric(self.population[0])
            if ccurr < cbest:
                xbest = self.population[0]
                cbest = ccurr
            end = time.time()
            if end - start > max_time - 0.001:
                break
        return xbest
