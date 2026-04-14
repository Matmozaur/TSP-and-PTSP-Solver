from __future__ import annotations

import json

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from .config import settings
from .schemas import (
    FullGraphData,
    SolutionResponse,
    TSPSolutionRequest,
)
from .services import TSPSolverService, build_executor

router = APIRouter(prefix="/tsp", tags=["TSP"])


# ---------------------------------------------------------------------------
# Dependency — a fresh, stateless service instance per request
# ---------------------------------------------------------------------------


def get_tsp_service() -> TSPSolverService:
    """FastAPI dependency that provides a request-scoped :class:`TSPSolverService`.

    Each request receives its own instance so no mutable graph state is shared
    across concurrent requests.  Executor selection is configuration-driven:
    the Go worker handles ``Random``/``HC`` when enabled, with local Python
    fallback for resiliency and for all other methods.
    """
    executor = build_executor(
        go_worker_enabled=settings.go_worker_enabled,
        go_worker_url=settings.go_worker_url,
        go_worker_timeout_seconds=settings.go_worker_timeout_seconds,
    )
    return TSPSolverService(media_path=settings.media_path, executor=executor)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/solve", response_model=SolutionResponse, status_code=status.HTTP_200_OK)
async def solve_tsp(
    request: TSPSolutionRequest,
    service: TSPSolverService = Depends(get_tsp_service),
) -> dict:
    """Solve TSP instance using specified algorithm.

    Args:
        request: TSP solution request with graph and parameters.
        service: Request-scoped solver service (injected).

    Returns:
        Solution with tour, cost, and execution time.

    Raises:
        HTTPException: If graph loading or solving fails.
    """
    try:
        ctx = service.load_graph_from_matrix(request.graph.matrix, request.graph.names)

        result = service.solve(
            ctx=ctx,
            method=request.method,
            max_time=request.time_limit,
            population_size=request.population or 50,
            mutate=request.mutate,
            simulation_type=request.simulation_type or "nearest",
        )

        return SolutionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/visualize",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
)
async def visualize_graph(
    graph_data: FullGraphData = Body(...),
    filename: str = "graph.png",
    service: TSPSolverService = Depends(get_tsp_service),
) -> FileResponse:
    """Generate and return graph visualisation.

    Args:
        graph_data: Graph data.
        filename: Output filename.
        service: Request-scoped solver service (injected).

    Returns:
        Graph image file.

    Raises:
        HTTPException: If visualisation fails.
    """
    try:
        ctx = service.load_graph_from_matrix(graph_data.matrix, graph_data.names)
        image_path = service.save_graph_visualization(ctx, filename)

        return FileResponse(
            path=image_path,
            media_type="image/png",
            filename=filename,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/upload", response_model=SolutionResponse)
async def solve_from_file(
    file: UploadFile = File(...),
    method: str = "HC",
    time_limit: float = 5.0,
    service: TSPSolverService = Depends(get_tsp_service),
) -> dict:
    """Upload JSON file with graph and solve.

    Args:
        file: JSON file with graph data.
        method: Solving method.
        time_limit: Maximum computation time.
        service: Request-scoped solver service (injected).

    Returns:
        Solution.

    Raises:
        HTTPException: If file reading or solving fails.
    """
    try:
        if file.content_type != "application/json":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be JSON",
            )

        content = await file.read()
        graph_input = json.loads(content)

        if "graph" not in graph_input or "type" not in graph_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format. Expected 'graph' and 'type' fields.",
            )

        graph_data = FullGraphData(**graph_input["graph"])
        ctx = service.load_graph_from_matrix(graph_data.matrix, graph_data.names)

        result = service.solve(
            ctx=ctx,
            method=method,
            max_time=time_limit,
        )

        return SolutionResponse(**result)

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON: {e}")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status
    """
    return {"status": "healthy", "service": "TSP Solver"}

