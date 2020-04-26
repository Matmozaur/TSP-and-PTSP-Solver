import unittest
import networkx as nx
import numpy as np

from main.analytics.tsp.domain.solutions import PartialSolution, ValidSolution


class TestDomainMethods(unittest.TestCase):

    def setUp(self):
        A = np.asarray([[0, 1, 4, 3, 1, 2, 2, 8],
                        [1, 0, 1, 2, 1, 7, 1, 1],
                        [4, 1, 0, 1, 1, 1, 1, 1],
                        [3, 2, 1, 0, 1, 4, 1, 1],
                        [1, 1, 1, 1, 0, 6, 1, 3],
                        [2, 7, 1, 4, 6, 0, 1, 4],
                        [2, 1, 1, 1, 1, 1, 0, 5],
                        [8, 1, 1, 1, 3, 4, 5, 0]], dtype=np.float32)
        self.G = nx.from_numpy_matrix(A)
        PartialSolution.set_graph(self.G)
        self.partial_3 = PartialSolution([2, 4, 1])
        self.partial_0 = PartialSolution([])
        self.partial_full = PartialSolution([2, 3, 1, 0, 4, 5, 6, 7])
        self.valid_a = ValidSolution([3, 2, 1, 0, 4, 5, 6, 7])
        self.valid_b = ValidSolution([0, 1, 2, 3, 4, 5, 6, 7])
        self.valid_to_short = ValidSolution([0, 1, 2, 3, 4, 5, 6])
        self.valid_duplicate = ValidSolution([0, 1, 2, 3, 4, 7, 7, 7])
        self.valid_to_long = ValidSolution([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    def test_valid_a(self):
        self.assertTrue(self.valid_a.valid)

    def test_valid_full(self):
        self.assertTrue(self.partial_full.valid)

    def test_valid_to_short(self):
        self.assertFalse(self.valid_to_short.valid)

    def test_valid_to_long(self):
        self.assertFalse(self.valid_to_long.valid)

    def test_valid_duplicate(self):
        self.assertFalse(self.valid_duplicate.valid)

    def test_cost_a(self):
        self.assertEqual(self.valid_a.cost, 17)

    def test_cost_b(self):
        self.assertEqual(self.valid_b.cost, 24)

    def test_cost_partial_3(self):
        self.assertEqual(self.partial_3.cost, 2)

    def test_gain_a_2_3(self):
        self.assertEqual(self.valid_a._gain(2, 3), self.valid_a.cost - ValidSolution([3, 2, 0, 1, 4, 5, 6, 7]).cost)

    def test_gain_a_3_6(self):
        self.assertEqual(self.valid_a._gain(3, 6), self.valid_a.cost - ValidSolution([3, 2, 1, 6, 4, 5, 0, 7]).cost)

    def test_gain_b_0_5(self):
        self.assertEqual(self.valid_b._gain(0, 5), self.valid_b.cost - ValidSolution([5, 1, 2, 3, 4, 0, 6, 7]).cost)

if __name__ == '__main__':
    unittest.main()
