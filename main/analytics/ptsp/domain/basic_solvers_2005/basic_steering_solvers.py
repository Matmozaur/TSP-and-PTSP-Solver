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
    for pstp_map in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        v1 = v[0] + pstp_map[0]
        v2 = v[1] + pstp_map[1]
        f = (a - v1) * (a - v1) + (b - v2) * (b - v2)
        if f < f_min:
            f_min = f
            m_best = pstp_map
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
