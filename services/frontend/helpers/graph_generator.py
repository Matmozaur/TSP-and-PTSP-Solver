"""Generate sample graphs for testing."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass


def generate_random_matrix(n_nodes: int, seed: int | None = None) -> list[list[float]]:
    """Generate random complete graph adjacency matrix.

    Args:
        n_nodes: Number of nodes
        seed: Random seed for reproducibility

    Returns:
        Square adjacency matrix with distances
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    # Generate random distances
    matrix = np.random.uniform(1, 100, size=(n_nodes, n_nodes))

    # Make it symmetric
    matrix = (matrix + matrix.T) / 2

    # Zero diagonal
    np.fill_diagonal(matrix, 0)

    return matrix.tolist()


def generate_euclidean_matrix(
    n_nodes: int, width: int = 100, height: int = 100, seed: int | None = None
) -> tuple[list[list[float]], list[str]]:
    """Generate Euclidean distance matrix from random 2D points.

    Args:
        n_nodes: Number of nodes
        width: Canvas width
        height: Canvas height
        seed: Random seed for reproducibility

    Returns:
        Tuple of (adjacency matrix, node names with coordinates)
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    # Generate random points
    points = np.random.uniform(0, 100, size=(n_nodes, 2))

    # Calculate euclidean distances
    matrix = np.zeros((n_nodes, n_nodes))
    for i in range(n_nodes):
        for j in range(n_nodes):
            if i != j:
                dist = np.sqrt((points[i][0] - points[j][0]) ** 2 + (points[i][1] - points[j][1]) ** 2)
                matrix[i][j] = dist

    # Create node names with coordinates
    names = [f"P{i}\n({points[i][0]:.1f}, {points[i][1]:.1f})" for i in range(n_nodes)]

    return matrix.tolist(), names


def generate_circle_matrix(n_nodes: int) -> tuple[list[list[float]], list[str]]:
    """Generate complete graph with nodes on a circle.

    Args:
        n_nodes: Number of nodes

    Returns:
        Tuple of (adjacency matrix, node names)
    """
    import math

    # Generate positions on circle
    radius = 50
    angles = [2 * math.pi * i / n_nodes for i in range(n_nodes)]
    points = [(radius * math.cos(a), radius * math.sin(a)) for a in angles]

    # Calculate euclidean distances
    matrix = np.zeros((n_nodes, n_nodes))
    for i in range(n_nodes):
        for j in range(n_nodes):
            if i != j:
                dist = math.sqrt(
                    (points[i][0] - points[j][0]) ** 2 + (points[i][1] - points[j][1]) ** 2
                )
                matrix[i][j] = dist

    names = [
        f"City {i}\n({points[i][0]:.1f}, {points[i][1]:.1f})"
        for i in range(n_nodes)
    ]

    return matrix.tolist(), names


def generate_grid_matrix(grid_size: int) -> tuple[list[list[float]], list[str]]:
    """Generate grid graph as adjacency matrix.

    Args:
        grid_size: Size of grid (grid_size x grid_size nodes)

    Returns:
        Tuple of (adjacency matrix, node names)
    """
    n_nodes = grid_size * grid_size

    # Generate grid positions
    points = []
    for i in range(grid_size):
        for j in range(grid_size):
            points.append((i * 10, j * 10))

    # Calculate euclidean distances
    matrix = np.zeros((n_nodes, n_nodes))
    for i in range(n_nodes):
        for j in range(n_nodes):
            if i != j:
                dist = np.sqrt((points[i][0] - points[j][0]) ** 2 + (points[i][1] - points[j][1]) ** 2)
                matrix[i][j] = dist

    names = [f"({i % grid_size}, {i // grid_size})" for i in range(n_nodes)]

    return matrix.tolist(), names
