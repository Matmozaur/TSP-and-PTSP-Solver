"""API client for communicating with FastAPI backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from typing import Any


class APIClient:
    """Client for TSP/PTSP Solver API."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        """Initialize API client.

        Args:
            base_url: Base URL of the API
        """
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=120.0)

    def check_health(self) -> bool:
        """Check API health.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self.client.get("/api/v1/ptsp/health")
            return response.status_code == 200
        except Exception:
            return False

    def solve_tsp(
        self,
        matrix: list[list[float]],
        method: str,
        time_limit: float = 5.0,
        names: list[str] | None = None,
        population: int | None = 50,
        mutate: bool = True,
        simulation_type: str = "nearest",
    ) -> dict[str, Any]:
        """Solve TSP instance.

        Args:
            matrix: Adjacency matrix
            method: Solving method (Random, HC, Genetic, MCTS)
            time_limit: Time limit in seconds
            names: Optional node names
            population: Population size for genetic algorithm
            mutate: Enable mutation for genetic algorithm
            simulation_type: Simulation type for MCTS

        Returns:
            Solution response

        Raises:
            httpx.HTTPError: If request fails
        """
        request_body = {
            "graph": {"matrix": matrix, "names": names},
            "method": method,
            "time_limit": time_limit,
            "population": population,
            "mutate": mutate,
            "simulation_type": simulation_type,
        }

        response = self.client.post("/api/v1/tsp/solve", json=request_body)
        response.raise_for_status()
        return response.json()

    def visualize_graph(
        self,
        matrix: list[list[float]],
        names: list[str] | None = None,
        filename: str = "graph.png",
    ) -> bytes:
        """Get graph visualization.

        Args:
            matrix: Adjacency matrix
            names: Optional node names
            filename: Output filename

        Returns:
            Image bytes

        Raises:
            httpx.HTTPError: If request fails
        """
        request_body = {
            "matrix": matrix,
            "names": names,
        }

        response = self.client.post(
            "/api/v1/tsp/visualize",
            json=request_body,
            params={"filename": filename},
        )
        response.raise_for_status()
        return response.content

    def get_tsp_methods(self) -> list[str]:
        """Get available TSP solving methods.

        Returns:
            List of method names
        """
        try:
            response = self.client.get("/api/v1/ptsp/methods")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("methods", [])]
        except Exception:
            return ["Random", "HC", "Genetic", "MCTS"]

    def close(self) -> None:
        """Close the client."""
        self.client.close()
