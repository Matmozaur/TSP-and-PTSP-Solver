from __future__ import annotations

import json
import threading

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from .config import settings
from .jobs import TSPJobCoordinator, build_job_repository
from .monitoring import build_progress_store
from .schemas import (
    FullGraphData,
    JobCancelResponse,
    JobProgressResponse,
    JobResultResponse,
    JobStatusResponse,
    JobSubmitResponse,
    ProgressSampleResponse,
    RunProgressResponse,
    RunResultResponse,
    RunStatusResponse,
    SolutionResponse,
    TSPBatchJobRequest,
    TSPSolutionRequest,
)
from .services import TSPSolverService, build_executor

router = APIRouter(prefix="/tsp", tags=["TSP"])
_job_coordinator: TSPJobCoordinator | None = None
_coordinator_lock = threading.Lock()
_tsp_service: TSPSolverService | None = None
_tsp_service_lock = threading.Lock()


def close_tsp_resources() -> None:
    """Close long-lived resources held by route-level singletons.

    Called from the FastAPI lifespan shutdown hook so that httpx clients,
    thread pools, etc. are released cleanly.
    """
    global _job_coordinator, _tsp_service

    if _job_coordinator is not None:
        _job_coordinator.shutdown()
        _job_coordinator = None

    if _tsp_service is not None:
        _tsp_service.close()
        _tsp_service = None


# ---------------------------------------------------------------------------
# Dependency — singleton service shared across requests
# ---------------------------------------------------------------------------


def get_tsp_service() -> TSPSolverService:
    """FastAPI dependency providing a singleton :class:`TSPSolverService`.

    The executor (including any ``httpx.Client`` inside
    :class:`RemoteGoExecutor`) is shared across requests so that HTTP
    connections are reused and the client is not leaked.
    """
    global _tsp_service
    if _tsp_service is None:
        with _tsp_service_lock:
            if _tsp_service is None:
                executor = build_executor(
                    go_worker_enabled=settings.go_worker_enabled,
                    go_worker_url=settings.go_worker_url,
                    go_worker_url_random_hc=settings.go_worker_url_random_hc,
                    go_worker_url_genetic=settings.go_worker_url_genetic,
                    go_worker_url_mcts=settings.go_worker_url_mcts,
                    go_worker_timeout_seconds=settings.go_worker_timeout_seconds,
                )
                _tsp_service = TSPSolverService(
                    media_path=settings.media_path, executor=executor
                )
    return _tsp_service


def get_tsp_job_coordinator() -> TSPJobCoordinator:
    """FastAPI dependency that provides the singleton async job coordinator."""
    global _job_coordinator
    if _job_coordinator is None:
        with _coordinator_lock:
            if _job_coordinator is None:
                executor = build_executor(
                    go_worker_enabled=settings.go_worker_enabled,
                    go_worker_url=settings.go_worker_url,
                    go_worker_url_random_hc=settings.go_worker_url_random_hc,
                    go_worker_url_genetic=settings.go_worker_url_genetic,
                    go_worker_url_mcts=settings.go_worker_url_mcts,
                    go_worker_timeout_seconds=settings.go_worker_timeout_seconds,
                )
                service = TSPSolverService(media_path=settings.media_path, executor=executor)
                repository = build_job_repository(settings.database_url)
                progress_store = build_progress_store(settings.database_url)
                _job_coordinator = TSPJobCoordinator(
                    solver=service,
                    repository=repository,
                    progress_store=progress_store,
                    sample_interval=settings.telemetry_sample_interval,
                )
    return _job_coordinator


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/solve", response_model=SolutionResponse, status_code=status.HTTP_200_OK)
async def solve_tsp(
    request: TSPSolutionRequest,
    coordinator: TSPJobCoordinator = Depends(get_tsp_job_coordinator),
) -> dict:
    """Compatibility solve facade mapped to a one-run job execution.

    Args:
        request: TSP solution request with graph and parameters.
        coordinator: Async job coordinator.

    Returns:
        Solution with tour, cost, and execution time.

    Raises:
        HTTPException: If graph loading or solving fails.
    """
    try:
        job = coordinator.run_job_sync(
            graph=request.graph.model_dump(),
            runs=[
                {
                    "method": request.method,
                    "time_limit": request.time_limit,
                    "population": request.population or 50,
                    "mutate": request.mutate,
                    "simulation_type": request.simulation_type or "nearest",
                }
            ],
        )

        run = job["runs"][0]
        result = run.get("result")
        if run.get("status") != "COMPLETED" or not result:
            error_message = run.get("error") or f"Run did not complete: {run.get('status')}"
            raise RuntimeError(error_message)

        return SolutionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/jobs",
    response_model=JobSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_tsp_job(
    request: TSPBatchJobRequest,
    coordinator: TSPJobCoordinator = Depends(get_tsp_job_coordinator),
) -> dict:
    """Submit an async TSP batch job."""
    try:
        return coordinator.submit_job(
            graph=request.graph.model_dump(),
            runs=[run.model_dump() for run in request.runs],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_tsp_job_status(
    job_id: str,
    coordinator: TSPJobCoordinator = Depends(get_tsp_job_coordinator),
) -> JobStatusResponse:
    """Return current status for a submitted job."""
    job = coordinator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        runs=[
            RunStatusResponse(
                run_id=run["run_id"],
                method=run["method"],
                status=run["status"],
                error=run.get("error"),
                started_at=run.get("started_at"),
                finished_at=run.get("finished_at"),
            )
            for run in job["runs"]
        ],
    )


@router.get("/jobs/{job_id}/result", response_model=JobResultResponse)
async def get_tsp_job_result(
    job_id: str,
    coordinator: TSPJobCoordinator = Depends(get_tsp_job_coordinator),
) -> JobResultResponse:
    """Return final or partial job results."""
    job = coordinator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return JobResultResponse(
        job_id=job["job_id"],
        status=job["status"],
        runs=[
            RunResultResponse(
                run_id=run["run_id"],
                method=run["method"],
                status=run["status"],
                error=run.get("error"),
                started_at=run.get("started_at"),
                finished_at=run.get("finished_at"),
                result=run.get("result"),
            )
            for run in job["runs"]
        ],
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobCancelResponse)
async def cancel_tsp_job(
    job_id: str,
    coordinator: TSPJobCoordinator = Depends(get_tsp_job_coordinator),
) -> JobCancelResponse:
    """Request cancellation for a submitted job."""
    job = coordinator.cancel_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return JobCancelResponse(
        job_id=job["job_id"],
        status=job["status"],
        message="Cancellation requested",
    )


@router.get("/jobs/{job_id}/progress", response_model=JobProgressResponse)
async def get_tsp_job_progress(
    job_id: str,
    coordinator: TSPJobCoordinator = Depends(get_tsp_job_coordinator),
) -> JobProgressResponse:
    """Return telemetry progress samples for all runs in a job.

    Args:
        job_id: Job identifier.
        coordinator: Async job coordinator.

    Returns:
        Per-run telemetry samples grouped by run_id.

    Raises:
        HTTPException: If the job is not found.
    """
    from collections import defaultdict

    job = coordinator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    samples = coordinator.get_progress(job_id)

    samples_by_run: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        samples_by_run[s["run_id"]].append(s)

    return JobProgressResponse(
        job_id=job_id,
        runs=[
            RunProgressResponse(
                run_id=run["run_id"],
                method=run["method"],
                samples=[
                    ProgressSampleResponse(**s)
                    for s in samples_by_run.get(run["run_id"], [])
                ],
            )
            for run in job["runs"]
        ],
    )


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


# NOTE: /upload intentionally bypasses the async job coordinator and calls the
# service directly.  It is a convenience endpoint for one-off file uploads and
# is not expected to participate in the batch job lifecycle.
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

