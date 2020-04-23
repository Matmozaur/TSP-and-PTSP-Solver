from main.analytics.tsp.domain.solutions import PartialSolution


class Node:

    def __init__(self, parent, v):
        self.parent = parent
        self.children = set()
        self.partial = PartialSolution(parent.partial + [v])
        self.mean = 0
        self.visits = 0
        self.unvisited = True

    def find_children(self):
        """
        All possible successors of this board state
        """
        return set()

    def is_terminal(self):
        """
        Returns True if the node has no children
        """
        return True

    def cost(self):
        pass

    @property
    def is_leaf(self):
        return len(self.children) == 0

    def utc(self, all_visits):
        return self.mean - self.visits/all_visits
