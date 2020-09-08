import math
import random
import numpy as np


def dist_eu(a, b):
    return math.sqrt(math.pow(a[0] - b[0], 2) + math.pow(a[1] - b[1], 2))


class NodeOrder:
    nodes = []
    cities = []

    def __init__(self, parent=None, v=None, root=False, tree=None):
        self.parent = parent
        self.children = set()
        if root:
            self.partial = parent
            self.visited = True
            self.tree = tree
        else:
            self.tree = parent.tree
            self.partial = parent.partial + [v]
            self.visited = False
        self.mean = 0
        self.visits = 0

    def find_children(self):
        nodes_left = set(NodeOrder.nodes).difference(set(self.partial))
        return set([NodeOrder(self, x) for x in nodes_left])

    @property
    def is_terminal(self):
        if set(self.partial) == set(NodeOrder.nodes):
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
            nodes_left = set(NodeOrder.nodes).difference(set(self.partial))
            return NodeOrder(self, random.sample(nodes_left, 1)[0])
        elif lottery == 'nearest':
            nodes_left = set(NodeOrder.nodes).difference(set(self.partial))
            return NodeOrder(self, min(nodes_left,
                                       key=lambda x: dist_eu(self.cities[self.partial[-1]], self.cities[x])))
        elif lottery == 'lottery':
            pass
            nodes_left = list(set(NodeOrder.nodes).difference(set(self.partial)))
            p = [dist_eu(self.cities[self.partial[-1]], self.cities[x]) for x in nodes_left]
            s = sum(p)
            p = [x / s for x in p]
            return NodeOrder(self, np.random.choice(nodes_left, 1, p=p)[0])
        else:
            raise ValueError

    def update(self, cost):
        self.mean = self.mean * self.visits
        self.visits += 1
        self.mean = (self.mean + cost) / self.visits
