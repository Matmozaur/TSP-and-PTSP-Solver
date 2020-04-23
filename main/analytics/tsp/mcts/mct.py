import time

from numba import Integer

from .node import Node


class MCT:
    """Monte Carlo tree searcher. First rollout the tree then choose a move."""

    def __init__(self, state, metric=Node.utc):
        """
        :type node: Node
        """
        self.root = Node(state)
        self.root.unvisited = False
        self.metric = metric

    def build_tree(self, max_time=60):
        start = time.time()
        while (time.time() - start) < (max_time - 0.001):
            leaf = self._traverse(self.root)
            if leaf.is_terminated():
                self._backpropagate(leaf, leaf.cost())
                continue
            else:
                if leaf.visited:
                    leaf = self._rollout(leaf)
                cost = self._simulate(leaf)
                self._backpropagate(leaf, leaf.cost())

    def _traverse(self, node):
        if node.is_leaf:
            return node
        else:
            node = self._choose_child(node)
            return self._traverse(node)

    def _backpropagate(self, node, cost):
        pass

    def _rollout(self, leaf):
        pass

    def _simulate(self, leaf):
        pass

    def choose_next(self):
        pass

    def choose_solution(self):
        pass

    def _choose_child(self, node):
        return min(node.children, key=lambda x: x.self.metric() + Integer.MAX_VALUE * int(x.unvisited))
