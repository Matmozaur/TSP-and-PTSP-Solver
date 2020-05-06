import pickle

from main.analytics.ptsp.domain.game.agent_2005 import Agent
from main.analytics.ptsp.domain.game.agent_2012 import Agent12


class Solution:

    def __init__(self, moves, map_ptsp, config):
        self.moves = moves
        self.map_ptsp = map_ptsp
        self.config = config

    def save(self, path):
        with open(path, 'wb') as handle:
            pickle.dump(self, handle)

    @staticmethod
    def load(path):
        with open(path, 'rb') as handle:
            sol = pickle.load(handle)
        return sol

    def check_solution(self, map_ptsp=None, config=None):
        if map_ptsp is None:
            map_ptsp = self.map_ptsp
        if config is None:
            config = self.config
        map_ptsp.reset()
        if config.version == 2005:
            a = Agent(map_ptsp, config)
        elif config.version == 2012:
            a = Agent12(map_ptsp, config)
        else:
            return False
        for m in self.moves:
            a.update(m)
            map_ptsp.try_visit(a.location[0], a.location[1], a.radious)
        if all(map_ptsp.visited):
            return True
        else:
            return False
