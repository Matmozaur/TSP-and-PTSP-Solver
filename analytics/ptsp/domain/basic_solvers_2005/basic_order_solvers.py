import copy
import random
import time

from analytics.ptsp.domain.basic_solvers_2005.metrics import MetricOrder


def hill_climbing_ptsp_local(ptsp_map, max_time, base, config, metric='dist'):
    metric = MetricOrder(ptsp_map, metric, config)
    start: float = time.time()
    local_max = copy.deepcopy(base)
    done = False
    g_start = metric.metric(local_max)
    while not done:
        done = True
        g0 = 0
        i0 = 0
        j0 = 0
        for i in range(len(local_max)):
            for j in range(len(local_max)):
                local = copy.deepcopy(local_max)
                local[i] = local_max[j]
                local[j] = local_max[i]
                g = metric.metric(local) - g_start
                if g > g0:
                    g0 = g
                    i0 = i
                    j0 = j
        if g0 > 0:
            temp = local_max[i0]
            local_max[i0] = local_max[j0]
            local_max[j0] = temp
            done = False
            g_start = metric.metric(local_max)
        end = time.time()
        if end - start > max_time - 0.001:
            break
    return local_max


def hill_climbing_ptsp(ptsp_map, max_time, config, metric_name='dist'):
    start: float = time.time()
    metric = MetricOrder(ptsp_map, metric_name, config)
    local_best = random.sample(range(len(ptsp_map.cities)),
                               len(ptsp_map.cities))
    while 1:
        rem_time = max_time - time.time() + start
        if rem_time < 0.002:
            break
        x = random.sample(range(len(ptsp_map.cities)),
                              len(ptsp_map.cities))
        x = hill_climbing_ptsp_local(ptsp_map, rem_time, x, metric_name)
        if metric.metric(x) < metric.metric(local_best):
            local_best = x
    return local_best
