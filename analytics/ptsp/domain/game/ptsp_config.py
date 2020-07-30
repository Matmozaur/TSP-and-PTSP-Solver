import math

import numpy as np


class PTSPConfiguration:

    def __init__(self, dt=math.sqrt(0.1), alpha=0.1, acc=1.0, slow=0.1, version=2005, r=0, max_moves=10000,
                 k1=0.25, k2=0.0):
        self.dt = dt
        self.alpha = alpha
        self.acc = acc
        self.slow = slow
        self.a1 = np.array([[math.cos(alpha), -math.sin(alpha)],
                            [math.cos(alpha), math.cos(alpha)]])
        self.a2 = np.array([[math.cos(-alpha), -math.sin(-alpha)],
                            [math.cos(-alpha), math.cos(-alpha)]])
        # self.moves = [[0, 0], [1, 0], [-1, 0], [0, 1], [1, 1], [-1, 1]]
        self.moves = [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]]
        self.version = version
        self.r = r
        self.max_moves = max_moves
        self.K1 = k1
        self.K2 = k2
