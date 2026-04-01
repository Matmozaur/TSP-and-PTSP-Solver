"""Pydantic schemas for request/response validation."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class GraphInput(BaseModel):
    """Input schema for graph data."""

    type: str = Field(..., description="Type of graph input (e.g., 'adjacency matrix')")
    graph: FullGraphData = Field(..., description="Graph data")


class FullGraphData(BaseModel):
    """Full graph data with matrix and optional node names."""

    matrix: list[list[float]] = Field(
        ..., description="Adjacency matrix representing the graph"
    )
    names: list[str] | None = Field(None, description="Optional node names")

    @field_validator("matrix")
    @classmethod
    def validate_matrix(cls, v: list[list[float]]) -> list[list[float]]:
        """Validate that matrix is square."""
        if not v:
            raise ValueError("Matrix cannot be empty")
        n = len(v)
        for row in v:
            if len(row) != n:
                raise ValueError("Matrix must be square")
        return v


class TSPSolutionRequest(BaseModel):
    """Request to solve TSP instance."""

    graph: FullGraphData = Field(..., description="Graph data")
    method: str = Field(..., description="Solving method: Random, HC, Genetic, MCTS")
    time_limit: float = Field(5.0, ge=0.1, description="Time limit in seconds")
    population: int | None = Field(50, ge=10, description="Population size for Genetic")
    mutate: bool = Field(True, description="Enable mutation in Genetic algorithm")
    simulation_type: str | None = Field("nearest", description="Simulation type for MCTS")

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate solving method."""
        valid_methods = ["Random", "HC", "Genetic", "MCTS"]
        if v not in valid_methods:
            raise ValueError(f"Method must be one of {valid_methods}")
        return v


class SolutionResponse(BaseModel):
    """Response containing a solution."""

    tour: list[int] = Field(..., description="Sequence of node indices in the tour")
    cost: float = Field(..., description="Total cost of the tour")
    method: str = Field(..., description="Method used to find the solution")
    execution_time: float = Field(..., description="Execution time in seconds")


class GraphImageResponse(BaseModel):
    """Response containing graph visualization info."""

    image_url: str = Field(..., description="URL to the generated graph image")
    width: int = Field(..., description="Image width")
    height: int = Field(..., description="Image height")


class StatusResponse(BaseModel):
    """Generic status response."""

    status: str = Field(..., description="Status message")
    message: str = Field(..., description="Additional message")
    version: str = Field(..., description="API version")
