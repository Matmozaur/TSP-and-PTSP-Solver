import random


class Map:

    def __init__(self, ncities, width=320, height=240, r=1):
        self.width = width
        self.height = height
        self.ncities = ncities
        self.cities = []
        self.radius = 1
        self.randomise()
        self.visited = [False for _ in range(ncities)]

    def try_visit(self, x, y, r):
        for i in range(self.ncities):
            if not self.visited[i]:
                if self.vicinity(self.cities[i], x, y, r):
                    self.visited[i] = True
                    return True
        return False

    def check_visit(self, x, y, r):
        for i in range(self.ncities):
            if not self.visited[i]:
                if self.vicinity(self.cities[i], x, y, r):
                    self.visited[i] = True
                    return True
        return False

    def vicinity(self, city, x, y, r):
        xd = city[0] - x
        yd = city[1] - y
        return xd*xd + yd*yd < self.radius*self.radius + r*r

    def reset(self):
        self.visited = [False for _ in range(self.ncities)]

    def randomise(self):
        cur = 0
        while cur < self.ncities:
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            if not self.check_visit(x, y, self.radius):
                self.cities.append((x, y))
                cur += 1
