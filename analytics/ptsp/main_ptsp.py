from analytics.ptsp.domain.game.map import *
from analytics.ptsp.domain.game.agent_2005 import *
from analytics.ptsp.domain.game.ptsp_config import *
from analytics.ptsp.domain.game.solution import *
from analytics.ptsp.domain.basic_solvers_2005.basic_order_solvers import *
from analytics.ptsp.domain.basic_solvers_2005.basic_steering_solvers import *
from analytics.ptsp.genetic.genetic_order import *
from analytics.ptsp.mcts.mct_order import *
import matplotlib.pyplot as plt


class PTSPController:
    __instance = None

    @staticmethod
    def get_instance():
        if PTSPController.__instance is None:
            PTSPController()
        return PTSPController.__instance

    def __init__(self):
        self.config = None
        self.map = None
        if PTSPController.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            PTSPController.__instance = self

    def generate_map(self, file):
        if file is None:
            map_ptsp = Map(10, 320, 240, 5)
        else:
            map_ptsp = Map.load(file)
        self.map = map_ptsp
        return map_ptsp

    def generate_config(self, file):
        if file is None:
            config = PTSPConfiguration()
        else:
            config = PTSPConfiguration(file['dt'], file['alpha'], file['acc'], file['slow'], file['version'],
                                       file['r'], file['max_moves'], file['k1'], file['k2'])
        self.config = config
        return config

    def save_map_image(self, path):
        plt.figure()
        plt.style.use('dark_background')
        points = self.map.cities
        x_lim, y_lim = self.map.width, self.map.height
        plt.axis([0-x_lim/5, x_lim*1.2, 0-x_lim/5, y_lim*1.2])
        xs, ys = zip(*points)
        plt.plot(xs, ys, 'ro')
        plt.savefig(path)
        plt.clf()

    def save_sol_image(self, path, sol):
        plt.figure()
        plt.style.use('dark_background')
        points = self.map.cities
        x_lim, y_lim = self.map.width, self.map.height
        plt.axis([0-x_lim, x_lim*2, 0-x_lim, y_lim*2])
        xs, ys = zip(*points)
        plt.plot(xs, ys, 'ro')
        self.map.reset()
        a = Agent(self.map, self.config)
        p = []
        for move in sol.moves:
            p.append(copy.copy(a.location))
            a.update(move)
        xs, ys = zip(*p)
        self.map.reset()
        plt.plot(xs, ys, 'y-')
        plt.savefig(path)
        plt.clf()

    def get_hc_solution(self, max_time, sol_metric):
        o = hill_climbing_ptsp(self.map, max_time, self.config, sol_metric)
        solution = local_solution(self.map, self.config, o)
        return solution

    def get_genetic_solution(self, max_time, sol_metric, population):
        gs = GeneticOrderSolver(population, self.map, self.config)
        o = gs.solve(sol_metric, max_time)
        solution = local_solution(self.map, self.config, o)
        return solution

    def get_mcts_solution(self, max_time, sol_metric, lottery):
        mct = MCTOrder([], self.map, self.config, cost_function=sol_metric, lottery=lottery)
        mct.build_tree(max_time)
        o = mct.best_sol
        solution = local_solution(self.map, self.config, o)
        return solution
