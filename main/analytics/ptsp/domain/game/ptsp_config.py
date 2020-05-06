import math

import numpy as np


class PTSPConfiguration:

    def __init__(self, dt=0.1, alpha=0.1, acc=1.0, slow=0.1, version=2005, r=0):
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
