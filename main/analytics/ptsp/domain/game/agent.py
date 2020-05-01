import numpy as np


class Agent:

    def __init__(self, map_ptsp, r, config):
        self.previous_location = np.array([map_ptsp.width/2, map_ptsp.height/2])
        self.location = np.array([map_ptsp.width/2, map_ptsp.height/2])
        self.v = np.array([0, 0])
        self.radious = r
        self.config = config

    def update(self, move):
        self.previous_location = self.location
        self.location += self.v * self.config.dt

        tmp.set(v)
        tmp.mul(Run.dt)
        s.add(tmp)

        tmp.set(acc)
        tmp.mul(Run.t2)
        s.add(tmp)

        tmp.set(acc)
        tmp.mul(Run.a)
        v.add(tmp)


