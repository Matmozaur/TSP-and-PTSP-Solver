from __future__ import annotations


import networkx as nx
import numpy as np
import pytest

from analytics.tsp.domain.solutions import PartialSolution

# ---------------------------------------------------------------------------
# Shared test fixtures and graph corpus
# ---------------------------------------------------------------------------

# 4-city fully-connected graph used across most tests.
# Distances are asymmetric to ensure the cost function is exercised correctly.
MATRIX_4 = [
    [0, 10, 15, 20],
    [10, 0, 35, 25],
    [15, 35, 0, 30],
    [20, 25, 30, 0],
]

# 6-city fully-connected graph for slightly more complex testing.
MATRIX_6 = [
    [0, 2, 9, 10, 6, 3],
    [2, 0, 6, 4, 3, 7],
    [9, 6, 0, 8, 5, 4],
    [10, 4, 8, 0, 2, 9],
    [6, 3, 5, 2, 0, 8],
    [3, 7, 4, 9, 8, 0],
]

# Minimum graph size (2 cities) — edge case for all algorithms.
MATRIX_2 = [
    [0, 5],
    [5, 0],
]


def _make_graph(matrix: list[list[float]]) -> nx.Graph:
    """Build a NetworkX graph from an adjacency matrix and register it."""
    g = nx.from_numpy_array(np.array(matrix))
    PartialSolution.set_graph(g)
    return g


def _is_valid_tour(tour: list[int], n: int) -> bool:
    """Return True iff *tour* is a permutation of [0, n-1]."""
    return sorted(tour) == list(range(n))


class TestAPIContract:
    """Freeze the HTTP API surface.  These assertions must remain green
    through every migration phase."""

    # --- /api/v1/tsp/solve ---------------------------------------------------

    VALID_PAYLOAD_4: dict = {
        "graph": {"matrix": MATRIX_4, "names": ["A", "B", "C", "D"]},
        "method": "Random",
        "time_limit": 1.0,
    }

    def test_solve_returns_200_for_valid_request(self, client) -> None:
        response = client.post("/api/v1/tsp/solve", json=self.VALID_PAYLOAD_4)
        assert response.status_code == 200

    def test_solve_response_contains_required_fields(self, client) -> None:
        response = client.post("/api/v1/tsp/solve", json=self.VALID_PAYLOAD_4)
        data = response.json()

        assert "tour" in data
        assert "cost" in data
        assert "method" in data
        assert "execution_time" in data

    def test_solve_response_types_are_correct(self, client) -> None:
        response = client.post("/api/v1/tsp/solve", json=self.VALID_PAYLOAD_4)
        data = response.json()

        assert isinstance(data["tour"], list)
        assert all(isinstance(n, int) for n in data["tour"])
        assert isinstance(data["cost"], float)
        assert isinstance(data["method"], str)
        assert isinstance(data["execution_time"], float)

    def test_solve_tour_length_matches_graph_size(self, client) -> None:
        response = client.post("/api/v1/tsp/solve", json=self.VALID_PAYLOAD_4)
        data = response.json()

        assert len(data["tour"]) == 4

    def test_solve_tour_is_valid_permutation(self, client) -> None:
        response = client.post("/api/v1/tsp/solve", json=self.VALID_PAYLOAD_4)
        data = response.json()

        assert _is_valid_tour(data["tour"], 4)

    def test_solve_method_field_echoes_request(self, client) -> None:
        response = client.post("/api/v1/tsp/solve", json=self.VALID_PAYLOAD_4)
        data = response.json()

        assert data["method"] == "Random"

    @pytest.mark.parametrize("method", ["Random", "HC", "Genetic", "MCTS"])
    def test_all_methods_return_200(self, method: str, client) -> None:
        payload = {**self.VALID_PAYLOAD_4, "method": method}
        response = client.post("/api/v1/tsp/solve", json=payload)
        assert response.status_code == 200

    @pytest.mark.parametrize("method", ["Random", "HC", "Genetic", "MCTS"])
    def test_all_methods_return_valid_tour(self, method: str, client) -> None:
        payload = {**self.VALID_PAYLOAD_4, "method": method}
        response = client.post("/api/v1/tsp/solve", json=payload)
        data = response.json()

        assert _is_valid_tour(data["tour"], 4)

    def test_invalid_method_returns_422(self, client) -> None:
        payload = {**self.VALID_PAYLOAD_4, "method": "BogusMethod"}
        response = client.post("/api/v1/tsp/solve", json=payload)
        assert response.status_code == 422

    def test_non_square_matrix_returns_400(self, client) -> None:
        payload = {
            "graph": {"matrix": [[0, 10], [10, 0], [5, 5]]},
            "method": "Random",
            "time_limit": 1.0,
        }
        response = client.post("/api/v1/tsp/solve", json=payload)
        assert response.status_code == 400 or response.status_code == 422

    def test_missing_method_returns_422(self, client) -> None:
        payload = {"graph": {"matrix": MATRIX_4}, "time_limit": 1.0}
        response = client.post("/api/v1/tsp/solve", json=payload)
        assert response.status_code == 422

    def test_time_limit_below_minimum_returns_422(self, client) -> None:
        payload = {**self.VALID_PAYLOAD_4, "time_limit": 0.0}
        response = client.post("/api/v1/tsp/solve", json=payload)
        assert response.status_code == 422

    # --- /api/v1/tsp/visualize -----------------------------------------------

    def test_visualize_returns_200_with_png_content_type(self, client) -> None:
        payload = {"matrix": MATRIX_4, "names": ["A", "B", "C", "D"]}
        response = client.post("/api/v1/tsp/visualize", json=payload)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_visualize_non_square_matrix_returns_error(self, client) -> None:
        payload = {"matrix": [[0, 10], [10, 0], [5, 5]]}
        response = client.post("/api/v1/tsp/visualize", json=payload)
        assert response.status_code in (400, 422)

    # --- /api/v1/tsp/health --------------------------------------------------

    def test_tsp_health_returns_200(self, client) -> None:
        response = client.get("/api/v1/tsp/health")
        assert response.status_code == 200

    def test_tsp_health_contains_status(self, client) -> None:
        response = client.get("/api/v1/tsp/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    # --- Root and /health ----------------------------------------------------

    def test_root_returns_api_name(self, client) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json().get("name") == "TSP-PTSP Solver"

    def test_health_returns_healthy(self, client) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json().get("status") == "healthy"


class TestSchemaValidation:
    """Test Pydantic schema rules that gate the API."""

    def test_valid_method_names_are_accepted(self) -> None:
        from src.app.schemas import TSPSolutionRequest

        for method in ["Random", "HC", "Genetic", "MCTS"]:
            req = TSPSolutionRequest(
                graph={"matrix": MATRIX_4},
                method=method,
                time_limit=1.0,
            )
            assert req.method == method

    def test_invalid_method_name_raises(self) -> None:
        from pydantic import ValidationError

        from src.app.schemas import TSPSolutionRequest

        with pytest.raises(ValidationError):
            TSPSolutionRequest(
                graph={"matrix": MATRIX_4},
                method="BadAlgorithm",
                time_limit=1.0,
            )

    def test_non_square_matrix_raises(self) -> None:
        from pydantic import ValidationError

        from src.app.schemas import FullGraphData

        with pytest.raises(ValidationError):
            FullGraphData(matrix=[[0, 1], [1, 0], [0, 0]])

    def test_empty_matrix_raises(self) -> None:
        from pydantic import ValidationError

        from src.app.schemas import FullGraphData

        with pytest.raises(ValidationError):
            FullGraphData(matrix=[])

    def test_default_time_limit_is_five_seconds(self) -> None:
        from src.app.schemas import TSPSolutionRequest

        req = TSPSolutionRequest(graph={"matrix": MATRIX_4}, method="Random")
        assert req.time_limit == 5.0

    def test_default_population_is_fifty(self) -> None:
        from src.app.schemas import TSPSolutionRequest

        req = TSPSolutionRequest(graph={"matrix": MATRIX_4}, method="Genetic")
        assert req.population == 50

    def test_default_mutate_is_true(self) -> None:
        from src.app.schemas import TSPSolutionRequest

        req = TSPSolutionRequest(graph={"matrix": MATRIX_4}, method="Genetic")
        assert req.mutate is True

    def test_default_simulation_type_is_nearest(self) -> None:
        from src.app.schemas import TSPSolutionRequest

        req = TSPSolutionRequest(graph={"matrix": MATRIX_4}, method="MCTS")
        assert req.simulation_type == "nearest"
