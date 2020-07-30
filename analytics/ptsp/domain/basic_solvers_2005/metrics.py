import math

from analytics.ptsp.domain.basic_solvers_2005.basic_steering_solvers import greedy_solution,\
    local_solution


class MetricOrder:

    def __init__(self, ptsp_map, name='dist', config=None):
        self.ptsp_map = ptsp_map
        self.config = config
        if name == 'dist':
            self.metric = self.dist_metric
        elif name == 'greedy':
            self.metric = self.greedy_metric
        elif name == 'angle':
            self.metric = self.angle_fitness_metric
        elif name == 'local':
            self.metric = self.local_metric

    def dist_metric(self, solution):
        sum_final = 0
        sum_final += (self.ptsp_map.width / 2 - self.ptsp_map.cities[solution[0]][0]) ** 2 \
            + (self.ptsp_map.height / 2 - self.ptsp_map.cities[solution[0]][1]) ** 2
        for i in range(len(solution) - 1):
            sum_final += (self.ptsp_map.cities[solution[i]][0] - self.ptsp_map.cities[solution[i]][0]) ** 2 \
                         + (self.ptsp_map.cities[solution[i + 1]][1] - self.ptsp_map.cities[solution[i + 1]][1]) ** 2
        return sum_final

    def greedy_metric(self, solution):
        g_s = greedy_solution(self.ptsp_map, self.config, solution)
        return len(g_s.moves)

    def local_metric(self, solution):
        g_s = local_solution(self.ptsp_map, self.config, solution)
        return len(g_s.moves)

    def angle_fitness_metric(self, solution):
        sum_final = 0

        def fitness(a, b, c):
            ab = math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
            bc = math.sqrt((b[0] - c[0]) ** 2 + (b[1] - c[1]) ** 2)
            ac2 = (a[0] - c[0]) ** 2 + (a[1] - c[1]) ** 2
            return (math.sqrt(ab) + math.sqrt(bc)) * (3.4 + (ab ** 2 + bc ** 2 - ac2) / (2 * ab * bc))

        sum_final += fitness([self.ptsp_map.width / 2, self.ptsp_map.height / 2],
                             self.ptsp_map.cities[solution[0]], self.ptsp_map.cities[solution[1]])
        for i in range(len(solution) - 2):
            sum_final += fitness(self.ptsp_map.cities[solution[i]], self.ptsp_map.cities[solution[i+1]],
                                 self.ptsp_map.cities[solution[i+2]])
        return sum_final
