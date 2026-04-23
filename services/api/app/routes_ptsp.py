"""FastAPI routes for PTSP (Physical TSP) solving."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from .schemas import StatusResponse

router = APIRouter(prefix="/ptsp", tags=["PTSP"])


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint for PTSP service.

    Returns:
        Health status
    """
    return {"status": "healthy", "service": "PTSP Solver"}


@router.get("/methods")
async def get_available_methods() -> dict:
    """Get available PTSP solving methods.

    Returns:
        List of available solving methods
    """
    return {
        "methods": [
            {
                "name": "Random",
                "description": "Random solution generation",
                "time_based": False,
            },
            {
                "name": "HC",
                "description": "Hill Climbing algorithm",
                "time_based": True,
            },
            {
                "name": "Genetic",
                "description": "Genetic Algorithm",
                "time_based": True,
            },
            {
                "name": "MCTS",
                "description": "Monte Carlo Tree Search",
                "time_based": True,
            },
        ]
    }
