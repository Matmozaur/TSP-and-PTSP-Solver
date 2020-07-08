import random
import time

from main.analytics.ptsp.domain.basic_solvers_2005.metrics import MetricOrder
from main.analytics.ptsp.domain.game.solution import Solution
from .node_order import NodeOrder


def cost(solution, ptsp_map, config, cost_func):
    m_o = MetricOrder(ptsp_map, cost_func, config)
    return m_o.metric(solution)


class MCTOrder:

    def __init__(self, base, ptsp_map, config, metric='UTC', lottery='random', cost_function='local', save_sol=True, explore_scale=2):
        self.root = NodeOrder(parent=base, root=True, tree=self)
        self.metric = metric
        self.lottery = lottery
        self.save_sol = save_sol
        self.best_sol = None
        self.best_cost = float('inf')
        self.iteration = 0
        self.explore_scale = explore_scale
        self.cost_function = cost_function
        self.map = ptsp_map
        self.config = config
        NodeOrder.cities = self.map.cities
        NodeOrder.nodes = [i for i in range(len(self.map.cities))]

    def build_tree(self, max_time=60):
        start = time.time()
        while (time.time() - start) < (max_time - 0.001):
            self.iteration += 1
            leaf = self._traverse(self.root)
            if leaf.is_terminal:
                self._backpropagate(leaf, leaf.partial.cost)
                continue
            else:
                if leaf.visited:
                    leaf = self._rollout(leaf)
                else:
                    leaf.visited = True
                cost = self._simulate(leaf)
                self._backpropagate(leaf, cost)

    def _traverse(self, node):
        if node.is_leaf:
            return node
        else:
            node = self._choose_child(node)
            return self._traverse(node)

    def _backpropagate(self, node, cost):
        if node == self.root:
            return
        else:
            node.update(cost)
            self._backpropagate(node.parent, cost)

    @staticmethod
    def _rollout(leaf):
        leaf.children = leaf.find_children()
        return random.sample(leaf.children, 1)[0]

    def _simulate(self, leaf):
        if leaf.is_terminal:
            c = cost(leaf.partial, self.map, self.config, self.cost_function)
            if c < self.best_cost:
                self.best_cost = c
                self.best_sol = leaf.partial
            return c
        else:
            return self._simulate(leaf.random_child(self.lottery))

    def choose_next(self):
        child = min(self.root.children, key=lambda x: x.mean)
        return child.partial

    def choose_solution(self):
        return self.best_sol

    def _choose_child(self, node):
        # check
        if self.metric == 'UTC':
            return min(node.children, key=lambda x: x.utc(self.iteration, self.explore_scale))
        else:
            raise ValueError
