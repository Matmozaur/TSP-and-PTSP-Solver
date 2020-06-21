import copy
import math
import random

from main.analytics.ptsp.domain.game.agent_2005 import Agent
from main.analytics.ptsp.domain.game.solution import Solution
from main.analytics.tsp.domain.solutions import PartialSolution


def fitness(min_dists, partial, agent, f_max):
    f = 0
    for i in range(len(partial.map_ptsp.cities)):
        if partial.map_ptsp.visited[i]:
            f += f_max - f_max/(min_dists[i]-partial.map_ptsp.radius+2)
    return f


def dist(a, b):
    return math.sqrt(math.pow(a[0] - b[1], 2) + math.pow(a[1] - b[1], 2))


class Node:

    max_f = 1000

    def __init__(self, parent=None, m=None, config=None, root=False):
        self.parent = parent
        self.children = set()
        if root:
            self.agent = Agent(m, config)
            self.partial = Solution([], m, config)
            self.min_dists = [dist(self.agent.location, self.partial.map_ptsp.cities[i])
                              for i in range(len(self.partial.map_ptsp.cities))]
            Node.max_f = sum(self.min_dists)
        else:
            self.agent = copy.deepcopy(parent.agent)
            self.agent.update(m)
            self.partial = copy.deepcopy(parent.partial)
            self.partial.moves.append(m)
            self.partial.map_ptsp.try_visit(self.agent.location[0], self.agent.location[1], self.agent.config.r)
            self.min_dists = parent.min_dists
            for i in range(len(self.partial.map_ptsp.cities)):
                if self.partial.map_ptsp.visited[i]:
                    if self.min_dists[i] > dist(self.agent.location, self.partial.map_ptsp.cities[i]):
                        self.min_dists[i] = dist(self.agent.location, self.partial.map_ptsp.cities[i])
            fitness(self.min_dists, self.partial, self.agent, Node.max_f)
            self.visited = False
        self.mean = fitness
        self.visits = 0

    # HERE
    def find_children(self):
        nodes_left = set(PartialSolution.Graph.nodes).difference(set(self.partial.HC))
        return set([Node(self, x) for x in nodes_left])

    @property
    def is_terminal(self):
        if self.partial.valid:
            return True
        return False

    @property
    def is_leaf(self):
        return len(self.children) == 0

    def utc(self, all_visits, explore_scale):
        if self.visited:
            return self.mean - explore_scale * math.sqrt(math.log2(all_visits) / self.visits)
        else:
            return 0

    def random_child(self, lottery):
        if lottery == 'random':
            nodes_left = set(PartialSolution.Graph.nodes).difference(set(self.partial.HC))
            return Node(self, random.sample(nodes_left, 1)[0])
        elif lottery == 'nearest':
            nodes_left = set(PartialSolution.Graph.nodes).difference(set(self.partial.HC))
            return Node(self, min(nodes_left,
                                  key=lambda x: self.partial.Graph.get_edge_data(self.partial.HC[-1], x)['weight']))
        elif lottery == 'nearest lottery':
            nodes_left = list(set(PartialSolution.Graph.nodes).difference(set(self.partial.HC)))
            p = [self.partial.Graph.get_edge_data(self.partial.HC[-1], x)['weight'] for x in nodes_left]
            s = sum(p)
            p = [x / s for x in p]
            return Node(self, random.sample(nodes_left, 1, p=p)[0])
        else:
            raise ValueError

    def update(self, cost):
        self.mean = self.mean * self.visits
        self.visits += 1
        self.mean = (self.mean + cost) / self.visits
