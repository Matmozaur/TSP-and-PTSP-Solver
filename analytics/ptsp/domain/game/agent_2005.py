import numpy as np


class Agent:

    def __init__(self, map_ptsp, config):
        self.previous_location = np.array([map_ptsp.width/2, map_ptsp.height/2])
        self.location = np.array([map_ptsp.width/2, map_ptsp.height/2])
        self.v = np.array([0.0, 0.0])
        self.radious = config.r
        self.config = config

    def update(self, move):
        a = np.array([0.0, 0.0])
        a += move
        self.previous_location = self.location
        self.location += self.v*self.config.dt + a*self.config.dt*self.config.dt/2
        # self.v += self.a*self.config.dt wrong
        self.v += [move[0]*self.config.dt, move[1]*self.config.dt]
