import copy
import math


def fitness(min_dists, partial, agent, f_max, K1=0, K2=0):
    f = 0
    for i in range(len(partial.map_ptsp.cities)):
        if not partial.map_ptsp.visited[i]:
            # f += f_max - f_max / (min_dists[i] - partial.map_ptsp.radius + 2)
            f += min_dists[i]
    # a1 = agent.location[0] - partial.map_ptsp.width
    # a2 = agent.location[1] - partial.map_ptsp.height
    # if a1 <= 0:
    #     a1 = 0
    # if a1 < -partial.map_ptsp.width:
    #     a1 = agent.location[0]
    # if a2 <= 0:
    #     a2 = 0
    # if a2 < -partial.map_ptsp.height:
    #     a2 = agent.location[1]
    # d = math.sqrt(math.pow(a1, 2) + math.pow(a2, 2))
    # f += K1*len(partial.moves) + K2*d
    return f


def dist(a, b):
    return math.sqrt(math.pow(a[0] - b[0], 2) + math.pow(a[1] - b[1], 2))


class NodeSterage:
    max_f = 10000000

    def __init__(self, parent=None, m=None, root=False, agent=None, solution=None):
        self.parent = parent
        self.children = set()
        if root:
            self.agent = agent
            self.partial = copy.deepcopy(solution)
            self.min_dists = [dist(self.agent.location, self.partial.map_ptsp.cities[i])
                              for i in range(len(self.partial.map_ptsp.cities))]
            NodeSterage.max_f = sum(self.min_dists)
        else:
            self.agent = copy.deepcopy(parent.agent)
            self.agent.update(m)
            self.partial = copy.deepcopy(parent.partial)
            self.partial.moves.append(m)
            self.partial.map_ptsp.try_visit(self.agent.location[0], self.agent.location[1], self.agent.config.r)
            self.min_dists = copy.deepcopy(parent.min_dists)
            for i in range(len(self.partial.map_ptsp.cities)):
                if not self.partial.map_ptsp.visited[i]:
                    if self.min_dists[i] > dist(self.agent.location, self.partial.map_ptsp.cities[i]):
                        self.min_dists[i] = dist(self.agent.location, self.partial.map_ptsp.cities[i])
            self.visited = False
        f = fitness(self.min_dists, self.partial, self.agent, NodeSterage.max_f, self.agent.config.K1, self.agent.config.K2)
        self.fitness = f
        self.mean = f
        self.visits = 0
        print(len(self.partial.moves))
        print(self.fitness)

    def find_children(self):
        return set([NodeSterage(self, x) for x in [(0, 1), (1, 0), (0, -1), (-1, 0), (0, 0)]])

    @property
    def is_terminal(self):
        if all(self.partial.map_ptsp.visited):
            return True
        return False

    @property
    def is_leaf(self):
        return len(self.children) == 0

    def utc(self, all_visits, explore_scale):
        if self.visited:
            return self.mean - explore_scale * math.sqrt(math.log2(all_visits) / self.visits)
        else:
            return self.mean - explore_scale * math.sqrt(math.log2(all_visits))

    def update(self, cost):
        # print(self.mean, cost)
        self.mean = self.mean * self.visits
        self.visits += 1
        self.mean = (self.mean + cost) / self.visits
        # print(self.mean)
        # if self.mean > cost:
        #     print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
        # print()
