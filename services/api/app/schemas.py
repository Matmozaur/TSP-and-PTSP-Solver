"""Pydantic schemas for request/response validation."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

_VALID_METHODS = ["Random", "HC", "Genetic", "MCTS"]


def _validate_method(v: str) -> str:
    """Shared method validator used by TSPSolutionRequest and AlgorithmRunRequest."""
    if v not in _VALID_METHODS:
        raise ValueError(f"Method must be one of {_VALID_METHODS}")
    return v


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
    time_limit: float = Field(5.0, ge=0.1, le=600.0, description="Time limit in seconds")
    population: int | None = Field(50, ge=10, description="Population size for Genetic")
    mutate: bool = Field(True, description="Enable mutation in Genetic algorithm")
    simulation_type: str | None = Field("nearest", description="Simulation type for MCTS")

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate solving method."""
        return _validate_method(v)


class AlgorithmRunRequest(BaseModel):
    """One algorithm run configuration within a batch job."""

    method: str = Field(..., description="Solving method: Random, HC, Genetic, MCTS")
    time_limit: float = Field(5.0, ge=0.1, le=600.0, description="Time limit in seconds")
    population: int = Field(50, ge=10, description="Population size for Genetic")
    mutate: bool = Field(True, description="Enable mutation in Genetic algorithm")
    simulation_type: str = Field("nearest", description="Simulation type for MCTS")

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate solving method."""
        return _validate_method(v)


class TSPBatchJobRequest(BaseModel):
    """Async batch solve request with one graph and multiple runs."""

    graph: FullGraphData = Field(..., description="Graph data")
    runs: list[AlgorithmRunRequest] = Field(
        ..., min_length=1, description="One or more algorithm runs"
    )


class SolutionResponse(BaseModel):
    """Response containing a solution."""

    tour: list[int] = Field(..., description="Sequence of node indices in the tour")
    cost: float = Field(..., description="Total cost of the tour")
    method: str = Field(..., description="Method used to find the solution")
    execution_time: float = Field(..., description="Execution time in seconds")


class RunStatusResponse(BaseModel):
    """Status information for one run inside a job."""

    run_id: str = Field(..., description="Run identifier")
    method: str = Field(..., description="Algorithm used")
    status: str = Field(..., description="Run status")
    error: str | None = Field(None, description="Run error if any")
    started_at: str | None = Field(None, description="Start time in UTC")
    finished_at: str | None = Field(None, description="Finish time in UTC")


class RunResultResponse(RunStatusResponse):
    """Result payload for one run inside a job."""

    result: SolutionResponse | None = Field(None, description="Run solution when completed")


class JobSubmitResponse(BaseModel):
    """Response returned when a job is submitted."""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current job status")
    run_count: int = Field(..., description="Number of requested runs")
    created_at: str = Field(..., description="Creation time in UTC")


class JobStatusResponse(BaseModel):
    """Current state for a submitted job."""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current job status")
    created_at: str = Field(..., description="Creation time in UTC")
    updated_at: str = Field(..., description="Last update time in UTC")
    runs: list[RunStatusResponse] = Field(..., description="Per-run statuses")


class JobResultResponse(BaseModel):
    """Final or partial results for a submitted job."""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current job status")
    runs: list[RunResultResponse] = Field(..., description="Per-run results")


class JobCancelResponse(BaseModel):
    """Response returned after a cancellation request."""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current job status")
    message: str = Field(..., description="Cancellation outcome")


class ProgressSampleResponse(BaseModel):
    """One telemetry sample recorded during a run."""

    run_id: str = Field(..., description="Run identifier this sample belongs to")
    sampled_at: str = Field(..., description="UTC timestamp of the sample")
    elapsed_seconds: float | None = Field(None, description="Seconds since run started")
    cpu_percent: float | None = Field(None, description="Process CPU usage %")
    memory_mb: float | None = Field(None, description="Process RSS memory in MB")
    best_cost: float | None = Field(None, description="Best tour cost at sample time")


class RunProgressResponse(BaseModel):
    """All telemetry samples for one algorithm run."""

    run_id: str = Field(..., description="Run identifier")
    method: str = Field(..., description="Algorithm used")
    samples: list[ProgressSampleResponse] = Field(
        ..., description="Time-ordered telemetry samples"
    )


class JobProgressResponse(BaseModel):
    """Telemetry progress for all runs in a job."""

    job_id: str = Field(..., description="Job identifier")
    runs: list[RunProgressResponse] = Field(..., description="Per-run progress data")


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
