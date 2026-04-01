from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Body, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from .config import settings
from .schemas import (
    FullGraphData,
    GraphImageResponse,
    SolutionResponse,
    TSPSolutionRequest,
)
from .services import TSPSolverService

router = APIRouter(prefix="/tsp", tags=["TSP"])

# Initialize service
tsp_service = TSPSolverService(media_path=settings.media_path)


@router.post("/solve", response_model=SolutionResponse, status_code=status.HTTP_200_OK)
async def solve_tsp(request: TSPSolutionRequest) -> dict:
    """Solve TSP instance using specified algorithm.

    Args:
        request: TSP solution request with graph and parameters

    Returns:
        Solution with tour, cost, and execution time

    Raises:
        HTTPException: If graph loading or solving fails
    """
    try:
        # Load graph
        tsp_service.load_graph_from_matrix(request.graph.matrix, request.graph.names)

        # Solve
        result = tsp_service.solve(
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
) -> FileResponse:
    """Generate and return graph visualization.

    Args:
        graph_data: Graph data
        filename: Output filename

    Returns:
        Graph image file

    Raises:
        HTTPException: If visualization fails
    """
    try:
        tsp_service.load_graph_from_matrix(graph_data.matrix, graph_data.names)
        image_path = tsp_service.save_graph_visualization(filename)

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
) -> dict:
    """Upload JSON file with graph and solve.

    Args:
        file: JSON file with graph data
        method: Solving method
        time_limit: Maximum computation time

    Returns:
        Solution

    Raises:
        HTTPException: If file reading or solving fails
    """
    try:
        import json

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
        tsp_service.load_graph_from_matrix(graph_data.matrix, graph_data.names)

        result = tsp_service.solve(
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
