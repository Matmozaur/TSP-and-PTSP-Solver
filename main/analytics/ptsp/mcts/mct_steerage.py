import random
import time

from main.analytics.ptsp.domain.game.agent_2005 import Agent
from main.analytics.ptsp.domain.game.map import Map
from main.analytics.ptsp.domain.game.ptsp_config import PTSPConfiguration
from main.analytics.ptsp.domain.game.solution import Solution
from main.analytics.ptsp.mcts.node_steerage import NodeSterage


class MCTSterage:

    def __init__(self, agent, solution, metric='UTC', lottery='random', save_sol=True, explore_scale=2):
        self.root = NodeSterage(agent=agent, solution=solution, root=True)
        self.metric = metric
        self.lottery = lottery
        self.save_sol = save_sol
        self.best_sol = None
        self.best_cost = float('inf')
        self.iteration = 0
        self.explore_scale = explore_scale

    def build_tree(self, max_time=60):
        start = time.time()
        while (time.time() - start) < (max_time - 0.001):
            self.iteration += 1
            leaf = self._traverse(self.root)
            if leaf.is_terminal:
                self._backpropagate(leaf, leaf.fitness)
                continue
            else:
                # if leaf.visits:
                leaf = self._rollout(leaf)
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
            self.root.visits += 1
        else:
            node.update(cost)
            self._backpropagate(node.parent, cost)

    @staticmethod
    def _rollout(leaf):
        leaf.children = leaf.find_children()
        return random.sample(leaf.children, 1)[0]

    def _simulate(self, leaf):
        return leaf.fitness
        # if leaf.is_terminal:
        #     c = leaf.partial.cost
        #     if c < self.best_cost:
        #         self.best_cost = c
        #         self.best_sol = leaf.partial
        #     return c
        # else:
        #     return self._simulate(leaf.random_child(self.lottery))

    def choose_next(self):
        for c in self.root.children:
            print(c.partial.moves[0], c.mean)
        child = min(self.root.children, key=lambda x: x.mean)
        return child.partial

    def choose_solution(self):
        return self.best_sol

    def _choose_child(self, node):
        # check
        if self.metric == 'UTC':
            # return min(node.children, key=lambda x: x.utc(self.iteration, self.explore_scale)*random.randint(1, 10)))
            # return min(node.children, key=lambda x: x.utc(self.iteration, self.explore_scale))
            return min(node.children, key=lambda x: x.mean)
        else:
            raise ValueError


# m = Map(1, 320, 240, 5)
# config = PTSPConfiguration()
# a = Agent(m, config)
# s = Solution([], m, config)
# mct = MCT(a, s)
# mct.build_tree(max_time=10)
# print(mct.root.children)
# print(mct.best_sol)
