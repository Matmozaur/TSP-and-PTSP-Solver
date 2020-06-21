import copy
import math

from main.analytics.ptsp.domain.game.agent_2005 import Agent
from main.analytics.ptsp.domain.game.ptsp_config import PTSPConfiguration
from main.analytics.ptsp.domain.game.solution import Solution


def greedy_move(agent, pstp_map, next_point):
    x = agent.location[0]
    y = agent.location[1]
    v = agent.v
    a = pstp_map.cities[next_point][0] - x
    b = pstp_map.cities[next_point][1] - y
    b = b / abs(a)
    a = a / abs(a)
    f_min = float("inf")
    m_best = None
    for move in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        v1 = v[0] + move[0]
        v2 = v[1] + move[1]
        f = (a - v1) * (a - v1) + (b - v2) * (b - v2)
        if f < f_min:
            f_min = f
            m_best = move
    return m_best


def greedy_solution(pstp_map, config=None, order=None):
    if order is None:
        order = range(len(pstp_map.cities))
    if config is None:
        config = PTSPConfiguration()
    a = Agent(pstp_map, config)
    i = 0
    solution = Solution([], pstp_map, config)
    while 1:
        move = greedy_move(a, pstp_map, order[i])
        a.update(move)
        solution.moves.append(move)
        pstp_map.try_visit(a.location[0], a.location[1], 0)
        while pstp_map.visited[order[i]]:
            i += 1
            if all(pstp_map.visited):
                pstp_map.reset()
                return solution
    return solution


def check_n(start, v, dest, r, t, n):
    g = (math.pow(n, 2) * math.pow(t, 2)) / 2
    base_loc = (start[0] + n * t * v[0], start[1] + n * t * v[1])
    dist = abs(dest[0] - base_loc[0]) + abs(dest[1] - base_loc[1])
    return g >= dist - r


def number_of_moves(start, v, dest, r, t, upper=10000, lower=0):
    if lower == upper:
        return upper
    elif check_n(start, v, dest, r, t, int((upper + lower) / 2)):
        upper = int((upper + lower) / 2)
        return number_of_moves(start, v, dest, r, t, upper, lower)
    else:
        lower = int((upper + lower + 1) / 2)
        return number_of_moves(start, v, dest, r, t, upper, lower)


def local_next_city_first_h(start, v, dest, r, t, n):
    if n == 0:
        return []
    base_loc = (start[0] + n * t * v[0], start[1] + n * t * v[1])
    h = dest[0] - base_loc[0]
    w = dest[1] - base_loc[1]
    moves = []
    if h > 0:
        if w > 0:
            while n > 0:
                if (h - math.pow(t, 2) / 2 + n * math.pow(t, 2)) >= 0:
                    moves.append((1, 0))
                    h += math.pow(t, 2) / 2
                    h -= n * math.pow(t, 2)
                elif (w + math.pow(t, 2) / 2 - n * math.pow(t, 2)) >= 0:
                    moves.append((0, 1))
                    w += math.pow(t, 2) / 2
                    w -= n * math.pow(t, 2)
                else:
                    moves.append((0, 0))
                n -= 1
        else:
            while n > 0:
                if (h - math.pow(t, 2) / 2 + n * math.pow(t, 2)) >= 0:
                    moves.append((1, 0))
                    h += math.pow(t, 2) / 2
                    h -= n * math.pow(t, 2)
                elif (w - math.pow(t, 2) / 2 + n * math.pow(t, 2)) <= 0:
                    moves.append((0, -1))
                    w -= math.pow(t, 2) / 2
                    w += n * math.pow(t, 2)
                else:
                    moves.append((0, 0))
                n -= 1
    else:
        while n > 0:
            if w < 0:
                if (h - math.pow(t, 2) / 2 + n * math.pow(t, 2)) <= 0:
                    moves.append((-1, 0))
                    h -= math.pow(t, 2) / 2
                    h += n * math.pow(t, 2)
                elif (w - math.pow(t, 2) / 2 + n * math.pow(t, 2)) <= 0:
                    moves.append((0, -1))
                    w -= math.pow(t, 2) / 2
                    w += n * math.pow(t, 2)
                else:
                    moves.append((0, 0))
                n -= 1
            else:
                if (h - math.pow(t, 2) / 2 + n * math.pow(t, 2)) <= 0:
                    moves.append((-1, 0))
                    h -= math.pow(t, 2) / 2
                    h += n * math.pow(t, 2)
                elif (w - math.pow(t, 2) / 2 + n * math.pow(t, 2)) >= 0:
                    moves.append((0, 1))
                    w += math.pow(t, 2) / 2
                    w -= n * math.pow(t, 2)
                else:
                    moves.append((0, 0))
                n -= 1
    return moves


def local_next_city_first_v(start, v, dest, r, t, n):
    if n == 0:
        return []
    base_loc = (start[0] + n * t * v[0], start[1] + n * t * v[1])
    h = dest[0] - base_loc[0]
    w = dest[1] - base_loc[1]
    moves = []
    if h > 0:
        if w > 0:
            while n > 0:
                if (w + math.pow(t, 2) / 2 - n * math.pow(t, 2)) >= 0:
                    moves.append((0, 1))
                    w += math.pow(t, 2) / 2
                    w -= n * math.pow(t, 2)
                elif (h - math.pow(t, 2) / 2 + n * math.pow(t, 2)) >= 0:
                    moves.append((1, 0))
                    h += math.pow(t, 2) / 2
                    h -= n * math.pow(t, 2)
                else:
                    moves.append((0, 0))
                n -= 1
        else:
            while n > 0:
                if (w - math.pow(t, 2) / 2 + n * math.pow(t, 2)) <= 0:
                    moves.append((0, -1))
                    w -= math.pow(t, 2) / 2
                    w += n * math.pow(t, 2)
                elif (h - math.pow(t, 2) / 2 + n * math.pow(t, 2)) >= 0:
                    moves.append((1, 0))
                    h += math.pow(t, 2) / 2
                    h -= n * math.pow(t, 2)
                else:
                    moves.append((0, 0))
                n -= 1
    else:
        while n > 0:
            if w < 0:
                if (w - math.pow(t, 2) / 2 + n * math.pow(t, 2)) <= 0:
                    moves.append((0, -1))
                    w -= math.pow(t, 2) / 2
                    w += n * math.pow(t, 2)
                elif (h - math.pow(t, 2) / 2 + n * math.pow(t, 2)) <= 0:
                    moves.append((-1, 0))
                    h -= math.pow(t, 2) / 2
                    h += n * math.pow(t, 2)
                else:
                    moves.append((0, 0))
                n -= 1
            else:
                if (w - math.pow(t, 2) / 2 + n * math.pow(t, 2)) >= 0:
                    moves.append((0, 1))
                    w += math.pow(t, 2) / 2
                    w -= n * math.pow(t, 2)
                elif (h - math.pow(t, 2) / 2 + n * math.pow(t, 2)) <= 0:
                    moves.append((-1, 0))
                    h -= math.pow(t, 2) / 2
                    h += n * math.pow(t, 2)
                else:
                    moves.append((0, 0))
                n -= 1
    return moves


def hor_first(start, dest1, dest2):
    pass


def local_solution(pstp_map, config=None, order=None):
    if order is None:
        order = range(len(pstp_map.cities))
    if config is None:
        config = PTSPConfiguration()
    a = Agent(pstp_map, config)
    i = 0
    solution = Solution([], pstp_map, config)
    start = a.location
    while i < len(pstp_map.cities):
        n = number_of_moves(start, a.v, pstp_map.cities[order[i]], config.r + pstp_map.radius,
                            config.dt, upper=config.max_moves, lower=0)
        moves_h = local_next_city_first_h(start, a.v, pstp_map.cities[order[i]],
                                          config.r + pstp_map.radius, config.dt, n)
        moves_v = local_next_city_first_v(start, a.v, pstp_map.cities[order[i]],
                                          config.r + pstp_map.radius, config.dt, n)
        a1 = copy.deepcopy(a)
        a2 = copy.deepcopy(a)
        pstp_map1 = copy.deepcopy(pstp_map)
        pstp_map2 = copy.deepcopy(pstp_map)
        p1 = 0
        p2 = 0
        i1 = i
        i2 = i
        for move in moves_h:
            a1.update(move)
            start = a1.location
            pstp_map1.try_visit(a1.location[0], a.location[1], 0)
            if i1 < len(order):
                while pstp_map1.visited[order[i1]]:
                    i1 += 1
                    p1 -= 1000
                    if i1 >= len(order):
                        break
        if i1 < len(order):
            p1 += number_of_moves(a1.location, a1.v, pstp_map1.cities[order[i1]],
                                  config.r + pstp_map.radius, config.dt, upper=config.max_moves, lower=0)
        for move in moves_v:
            a2.update(move)
            start = a2.location
            pstp_map2.try_visit(a2.location[0], a2.location[1], 0)
            if i2 < len(order):
                while pstp_map2.visited[order[i2]]:
                    i2 += 1
                    p2 -= 1000
                    if i2 >= len(order):
                        break
        if i2 < len(order):
            p2 += number_of_moves(a2.location, a2.v, pstp_map2.cities[order[i2]],
                                  config.r + pstp_map.radius, config.dt, upper=config.max_moves, lower=0)
        if p1 < p2:
            moves = moves_h
        else:
            moves = moves_v
        for move in moves:
            a.update(move)
            start = a.location
            solution.moves.append(move)
            pstp_map.try_visit(a.location[0], a.location[1], 0)
            while pstp_map.visited[order[i]]:
                i += 1
                if all(pstp_map.visited):
                    pstp_map.reset()
                    return solution
    return solution
