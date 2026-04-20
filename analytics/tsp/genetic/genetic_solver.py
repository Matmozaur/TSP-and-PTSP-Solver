import random
import time
import networkx as nx

from analytics.tsp.domain.solutions import ValidSolution


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

    @staticmethod
    def crossover(x, y, h=None):
        """
        :type x: ValidSolution
        :type y: ValidSolution
        :type h: int
        """
        g = x.Graph
        x = x.solution
        y = y.solution
        n = len(list(g.nodes))
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

    def generate_new_generation(self, h=None, mutate=True, mut_args=None, deadline=None):
        """
        :type mut_args: dict
        :type mutate: bool
        :type h: int
        :type deadline: float | None
        """
        if mut_args is None:
            mut_args = {'alg': 'hc', 'max_time': 0.05}
        random.shuffle(self.population)
        new_generation = []
        for X, Y in zip(self.population[::2], self.population[1::2]):
            if deadline is not None and time.time() >= deadline:
                break
            c, d = self.crossover(X, Y, h)
            new_generation.append(c)
            new_generation.append(d)
        if mutate:
            mutated = []
            for a in new_generation:
                if deadline is not None and time.time() >= deadline:
                    mutated.append(a)
                    continue
                # Cap per-individual mutation time to remaining budget
                if deadline is not None:
                    remaining = deadline - time.time()
                    mt = min(mut_args['max_time'], max(remaining * 0.5, 0.001))
                else:
                    mt = mut_args['max_time']
                mutated.append(self.mutation(a, mut_args['alg'], mt))
            new_generation = mutated
        return new_generation

    def solve(self, max_time=60, h=None, mutate=True, mut_args=None):
        """
        :type h: int
        :type max_time: float
        :type mutate: bool
        :type mut_args: dict
        """
        start = time.time()
        deadline = start + max_time
        self.population.sort(key=lambda a: a.cost)
        xbest = self.population[0]
        cbest = self.population[0].cost
        while True:
            remaining = deadline - time.time()
            if remaining <= 0.001:
                break
            # Budget mutation time: share remaining time across the population
            per_individual = min(remaining / max(self.size, 1), 0.5)
            alg = 'hc'
            if mut_args is not None:
                alg = mut_args.get('alg', 'hc')
            gen_mut_args = {'alg': alg, 'max_time': per_individual}
            self.population += self.generate_new_generation(h, mutate, gen_mut_args, deadline)
            self.population.sort(key=lambda a: a.cost)
            self.population = self.population[:self.size]
            ccurr = self.population[0].cost
            if ccurr < cbest:
                xbest = self.population[0]
                cbest = ccurr
        return xbest
