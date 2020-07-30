import math

import numpy as np


class Agent12:

    def __init__(self, map_ptsp, config):
        self.previous_location = np.array([map_ptsp.width/2, map_ptsp.height/2])
        self.location = np.array([map_ptsp.width/2, map_ptsp.height/2])
        self.v = np.array([0, 0])
        self.d = np.array([0, 1])
        self.radious = config.r
        self.config = config

    def update(self, move):
        if move[0] == 1:
            self.d = self.config.a1.dot(self.d)
        elif move[0] == -1:
            self.d = self.config.a2.dot(self.d)
        self.v += self.d * move[1] * self.config.acc
        self.v *= self.config.slow
        self.previous_location = self.location
        self.location += self.v * self.config.dt
