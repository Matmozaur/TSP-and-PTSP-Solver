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
        if pstp_map.visited[order[i]]:
            i += 1
            if all(pstp_map.visited):
                pstp_map.reset()
                break
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


def local_next_city(start, v, dest, r, t, n):
    if n == 0:
        return []
    base_loc = (start[0] + n * t * v[0], start[1] + n * t * v[1])
    print(base_loc)
    h = dest[0] - base_loc[0]
    w = dest[1] - base_loc[1]
    moves = []
    if h > 0:
        if w > 0:
            while n > 0:
                if (h - math.pow(t, 2)/2 + n*math.pow(t, 2)) >= 0:
                    moves.append((1, 0))
                    h += math.pow(t, 2)/2
                    h -= n*math.pow(t, 2)
                elif (w - math.pow(t, 2)/2 + n*math.pow(t, 2)) >= 0:
                    moves.append((0, 1))
                    w += math.pow(t, 2)/2
                    w -= n*math.pow(t, 2)
                else:
                    moves.append((0, 0))
                n -= 1
        else:
            while n > 0:
                if (h - math.pow(t, 2)/2 + n*math.pow(t, 2)) >= 0:
                    moves.append((1, 0))
                    h -= math.pow(t, 2)/2
                    h -= (n-1)*math.pow(t, 2)
                elif (w + math.pow(t, 2)/2 - n*math.pow(t, 2)) >= 0:
                    moves.append((0, 1))
                    w += math.pow(t, 2)/2
                    w += (n-1)*math.pow(t, 2)
                else:
                    moves.append((0, 0))
                n -= 1
    else:
        while n > 0:
            if w < 0:
                if (h + math.pow(t, 2)/2 - n*math.pow(t, 2)) <= 0:
                    moves.append((-1, 0))
                    h += math.pow(t, 2)/2
                    h += (n-1)*math.pow(t, 2)
                elif (w + math.pow(t, 2)/2 - n*math.pow(t, 2)) >= 0:
                    moves.append((0, 1))
                    w += math.pow(t, 2)/2
                    w += (n-1)*math.pow(t, 2)
                else:
                    moves.append((0, 0))
                n -= 1
            else:
                if (h + math.pow(t, 2)/2 - n*math.pow(t, 2)) <= 0:
                    moves.append((-1, 0))
                    h += math.pow(t, 2)/2
                    h += (n-1)*math.pow(t, 2)
                elif (w - math.pow(t, 2)/2 + n*math.pow(t, 2)) >= 0:
                    moves.append((0, 1))
                    w -= math.pow(t, 2)/2
                    w -= (n-1)*math.pow(t, 2)
                else:
                    moves.append((0, 0))
                n -= 1
    return moves


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
        n = number_of_moves(start, a.v, pstp_map.cities[order[i]], pstp_map.radius, config.dt,
                            upper=config.max_moves, lower=0)

        moves = local_next_city(start, a.v, pstp_map.cities[order[i]], config.r, config.dt, n)
        print(n)
        for move in moves:
            print(a.location,a.v,pstp_map.cities[order[i]])
            a.update(move)
            start = a.location
            solution.moves.append(move)
            pstp_map.try_visit(a.location[0], a.location[1], 0)
            if pstp_map.visited[order[i]]:
                i += 1
                if all(pstp_map.visited):
                    pstp_map.reset()
                    break
    return solution
