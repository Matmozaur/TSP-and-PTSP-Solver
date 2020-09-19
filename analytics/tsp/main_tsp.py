import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from analytics.tsp.genetic.genetic_solver import *
from analytics.tsp.mcts.mct import *
from analytics.tsp.domain.solutions import *
from analytics.tsp.domain.basic_solvers import *
import copy


class TSPController:
    __instance = None

    @staticmethod
    def get_instance():
        if TSPController.__instance is None:
            TSPController()
        return TSPController.__instance

    def __init__(self):
        self.graph = None
        self.graph_to_show = None
        if TSPController.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            TSPController.__instance = self

    def generate_graph(self, request):
        plt.style.use('default')
        try:
            if request['type'] == "adjacency matrix":
                m = np.matrix(request['graph']['matrix'])
                graph = nx.from_numpy_matrix(m)
                if request["graph"]['names'] is not None:
                    print(graph.nodes)
                    graph_to_show = copy.deepcopy(graph)
                    mapping = dict(
                        zip([i for i in range(len(request['graph']['matrix'][0]))], request['graph']['names']))
                    graph_to_show = nx.relabel_nodes(graph_to_show, mapping, copy=False)
                else:
                    graph_to_show = graph
                self.graph = graph
                self.graph_to_show = graph_to_show
                PartialSolution.set_graph(self.graph)
                return graph
            else:
                raise Exception('bad type')
        except:
            print("Bad json format!")

    def save_graph_image(self, path, graph=None, cycle=False):
        plt.style.use('default')
        if graph is None:
            graph = self.graph_to_show
        pos = nx.spectral_layout(graph, weight=None) if cycle else nx.circular_layout(graph)
        nx.draw_networkx(graph, pos, node_color='yellow')
        labels = nx.get_edge_attributes(graph, 'weight')
        nx.draw_networkx_edge_labels(graph, pos, edge_labels=labels)
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.clf()

    def get_random_solution(self):
        return ValidSolution(random.sample(range(len(list(self.graph.nodes))), len(list(self.graph.nodes))))

    def get_hc_solution(self, max_time):
        return hill_climbing_multiple(self.graph, max_time=max_time)

    def get_genetic_solution(self, max_time, population, mutate):
        gs = GeneticSolver(size=population, g=self.graph)
        return gs.solve(max_time, mutate=mutate)

    @staticmethod
    def get_mcts_solution(max_time, lottery):
        mct = MCT(PartialSolution([]), lottery=lottery)
        mct.build_tree(max_time)
        return mct.choose_solution()

    def relabel(self, graph):
        plt.style.use('default')
        mapping = dict(zip([i for i in range(len(self.graph_to_show.nodes))], self.graph_to_show.nodes))
        return nx.relabel_nodes(graph, mapping, copy=False)

    @staticmethod
    def get_solution_from_list(sol):
        return ValidSolution(sol)
