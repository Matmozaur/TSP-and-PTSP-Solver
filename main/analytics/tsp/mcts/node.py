import math
import random

from main.analytics.tsp.domain.solutions import PartialSolution


class Node:

    def __init__(self, parent=None, v=None, root=False):
        self.parent = parent
        self.children = set()
        if root:
            self.partial = parent
            self.visited = True
        else:
            self.partial = PartialSolution(parent.partial.HC + [v])
            self.visited = False
        self.mean = 0
        self.visits = 0

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
            return Node(self, min(nodes_left, key=lambda x: self.partial.Graph.get_edge_data(self.partial.HC[-1], x)['weight']))
        elif lottery == 'nearest lottery':
            nodes_left = list(set(PartialSolution.Graph.nodes).difference(set(self.partial.HC)))
            p = [self.partial.Graph.get_edge_data(self.partial.HC[-1], x)['weight'] for x in nodes_left]
            s = sum(p)
            p = [x/s for x in p]
            return Node(self, random.sample(nodes_left, 1, p=p)[0])
        else:
            raise ValueError

    def update(self, cost):
        self.mean = self.mean*self.visits
        self.visits += 1
        self.mean = (self.mean + cost) / self.visits
