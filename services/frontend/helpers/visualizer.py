"""Graph visualization utilities."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

import networkx as nx
import plotly.graph_objects as go

if TYPE_CHECKING:
    pass


COORDINATE_PATTERN = re.compile(r"\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)")


def _extract_positions(G: nx.Graph) -> dict[int, tuple[float, float]] | None:
    """Extract geometric positions from node labels when available."""
    positions: dict[int, tuple[float, float]] = {}

    for node, data in G.nodes(data=True):
        label = data.get("label")
        if not isinstance(label, str):
            return None

        match = COORDINATE_PATTERN.search(label)
        if match is None:
            return None

        positions[node] = (float(match.group(1)), float(match.group(2)))

    return positions if len(positions) == G.number_of_nodes() else None


def _is_circle_layout(pos: dict[int, tuple[float, float]]) -> bool:
    """Return whether positions resemble nodes placed on a circle."""
    if len(pos) < 5:
        return False

    xs = [x for x, _ in pos.values()]
    ys = [y for _, y in pos.values()]
    center_x = sum(xs) / len(xs)
    center_y = sum(ys) / len(ys)
    radii = [math.hypot(x - center_x, y - center_y) for x, y in pos.values()]

    mean_radius = sum(radii) / len(radii)
    if mean_radius == 0:
        return False

    variance = sum((radius - mean_radius) ** 2 for radius in radii) / len(radii)
    return math.sqrt(variance) / mean_radius < 0.12


def _is_grid_layout(pos: dict[int, tuple[float, float]]) -> bool:
    """Return whether positions resemble a grid."""
    if len(pos) < 4:
        return False

    rounded_x = {round(x, 6) for x, _ in pos.values()}
    rounded_y = {round(y, 6) for _, y in pos.values()}
    return len(rounded_x) > 1 and len(rounded_y) > 1 and len(rounded_x) * len(rounded_y) == len(pos)


def _sorted_circle_nodes(pos: dict[int, tuple[float, float]]) -> list[int]:
    """Return nodes sorted by angle around the centroid."""
    xs = [x for x, _ in pos.values()]
    ys = [y for _, y in pos.values()]
    center_x = sum(xs) / len(xs)
    center_y = sum(ys) / len(ys)

    return sorted(
        pos,
        key=lambda node: math.atan2(pos[node][1] - center_y, pos[node][0] - center_x),
    )


def _grid_step(values: list[float]) -> float | None:
    """Find the smallest positive spacing in a coordinate list."""
    unique_values = sorted({round(value, 6) for value in values})
    positive_steps = [
        unique_values[i + 1] - unique_values[i]
        for i in range(len(unique_values) - 1)
        if unique_values[i + 1] - unique_values[i] > 1e-6
    ]
    return min(positive_steps) if positive_steps else None


def _build_display_edges(
    G: nx.Graph,
    pos: dict[int, tuple[float, float]] | None,
) -> list[tuple[int, int]]:
    """Choose a readable subset of edges for visualization."""
    if pos is None or G.number_of_edges() <= max(3 * G.number_of_nodes(), 20):
        return list(G.edges())

    if _is_circle_layout(pos):
        ordered_nodes = _sorted_circle_nodes(pos)
        return [
            (ordered_nodes[i], ordered_nodes[(i + 1) % len(ordered_nodes)])
            for i in range(len(ordered_nodes))
        ]

    if _is_grid_layout(pos):
        x_step = _grid_step([x for x, _ in pos.values()])
        y_step = _grid_step([y for _, y in pos.values()])
        if x_step is not None and y_step is not None:
            edges: set[tuple[int, int]] = set()
            tolerance = min(x_step, y_step) / 10
            nodes = list(pos.keys())

            for i, u in enumerate(nodes):
                x0, y0 = pos[u]
                for v in nodes[i + 1 :]:
                    x1, y1 = pos[v]
                    same_row = abs(y0 - y1) <= tolerance and abs(abs(x0 - x1) - x_step) <= tolerance
                    same_column = abs(x0 - x1) <= tolerance and abs(abs(y0 - y1) - y_step) <= tolerance
                    if same_row or same_column:
                        edges.add((u, v))

            if edges:
                return sorted(edges)

    edges: set[tuple[int, int]] = set()
    nodes = list(pos.keys())
    k_nearest = min(3, max(len(nodes) - 1, 1))

    for node in nodes:
        x0, y0 = pos[node]
        neighbors = sorted(
            (
                (math.hypot(x0 - pos[other][0], y0 - pos[other][1]), other)
                for other in nodes
                if other != node
            ),
            key=lambda item: item[0],
        )
        for _, other in neighbors[:k_nearest]:
            edges.add((min(node, other), max(node, other)))

    return sorted(edges)


def _get_layout_positions(G: nx.Graph) -> dict[int, tuple[float, float]]:
    """Use embedded coordinates when possible, otherwise fall back to spring layout."""
    return _extract_positions(G) or nx.spring_layout(G, k=2, iterations=50, seed=42)


def _get_forced_layout_positions(
    G: nx.Graph,
    layout_hint: str | None,
) -> dict[int, tuple[float, float]] | None:
    """Get deterministic positions for explicit layout types."""
    if layout_hint is None:
        return None

    layout = layout_hint.lower()
    nodes = sorted(G.nodes())
    n = len(nodes)

    if layout == "circle":
        pos = nx.circular_layout(nodes)
        return {node: (float(pos[node][0]), float(pos[node][1])) for node in nodes}

    if layout == "grid":
        if n == 0:
            return {}
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        positions: dict[int, tuple[float, float]] = {}
        for index, node in enumerate(nodes):
            row = index // cols
            col = index % cols
            positions[node] = (float(col), float(-row))
        return positions

    return None


def _get_display_edges_for_layout(G: nx.Graph, layout_hint: str | None) -> list[tuple[int, int]] | None:
    """Build readable edge subsets for explicit layout types."""
    if layout_hint is None:
        return None

    layout = layout_hint.lower()
    nodes = sorted(G.nodes())
    n = len(nodes)

    if layout == "circle" and n >= 3:
        return [(nodes[i], nodes[(i + 1) % n]) for i in range(n)]

    if layout == "grid" and n >= 2:
        cols = math.ceil(math.sqrt(n))
        edges: list[tuple[int, int]] = []
        for index, node in enumerate(nodes):
            if (index + 1) % cols != 0 and index + 1 < n:
                edges.append((node, nodes[index + 1]))
            if index + cols < n:
                edges.append((node, nodes[index + cols]))
        return edges

    return None


def create_graph_from_matrix(
    matrix: list[list[float]], names: list[str] | None = None
) -> nx.Graph:
    """Create NetworkX graph from adjacency matrix.

    Args:
        matrix: Adjacency matrix
        names: Optional node names

    Returns:
        NetworkX graph
    """
    n = len(matrix)
    G = nx.Graph()

    # Add nodes
    if names and len(names) == n:
        G.add_nodes_from(range(n), label=names)
    else:
        G.add_nodes_from(range(n))

    # Add edges with weights
    for i in range(n):
        for j in range(i + 1, n):
            weight = matrix[i][j]
            if weight > 0:
                G.add_edge(i, j, weight=weight)

    return G


def visualize_graph(
    G: nx.Graph,
    title: str = "Graph Visualization",
    height: int = 600,
    width: int = 800,
    layout_hint: str | None = None,
) -> go.Figure:
    """Create interactive Plotly visualization of graph.

    Args:
        G: NetworkX graph
        title: Plot title
        height: Plot height in pixels
        width: Plot width in pixels

    Returns:
        Plotly figure
    """
    forced_pos = _get_forced_layout_positions(G, layout_hint)
    pos = forced_pos or _get_layout_positions(G)
    forced_edges = _get_display_edges_for_layout(G, layout_hint)
    display_edges = forced_edges or _build_display_edges(G, _extract_positions(G))

    # Create edge traces
    edge_x = []
    edge_y = []
    edge_text = []

    for u, v in display_edges:
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        weight = G.edges[u, v].get("weight", 1)
        edge_text.append(f"{weight:.1f}")

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1, color="#888"),
        hoverinfo="text",
        hovertext=edge_text,
        showlegend=False,
    )

    # Create node traces
    node_x = []
    node_y = []
    node_text = []
    node_color = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        label = G.nodes[node].get("label", str(node))
        node_text.append(f"Node {node}<br>{label}")
        node_color.append(len(list(G.neighbors(node))))

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=[str(i) for i in G.nodes()],
        textposition="top center",
        hoverinfo="text",
        hovertext=node_text,
        marker=dict(
            size=15,
            color=node_color,
            colorscale="YlGnBu",
            showscale=True,
            colorbar=dict(
                thickness=15,
                title=dict(text="Degree", side="right"),
                xanchor="left",
            ),
            line_width=2,
            line_color="white",
        ),
        showlegend=False,
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=title,
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, scaleanchor="x", scaleratio=1),
            plot_bgcolor="rgba(240, 240, 240, 0.5)",
            height=height,
            width=width,
        ),
    )

    return fig


def visualize_solution(
    G: nx.Graph,
    tour: list[int],
    names: list[str] | None = None,
    title: str = "TSP Solution",
    height: int = 600,
    width: int = 800,
    layout_hint: str | None = None,
) -> go.Figure:
    """Visualize TSP solution by highlighting the tour path.

    Args:
        G: NetworkX graph
        tour: Tour sequence (node indices)
        names: Optional node names
        title: Plot title
        height: Plot height in pixels
        width: Plot width in pixels

    Returns:
        Plotly figure with highlighted tour
    """
    forced_pos = _get_forced_layout_positions(G, layout_hint)
    pos = forced_pos or _get_layout_positions(G)
    forced_edges = _get_display_edges_for_layout(G, layout_hint)
    display_edges = forced_edges or _build_display_edges(G, _extract_positions(G))

    # Create tour path edges
    tour_x = []
    tour_y = []

    for i in range(len(tour)):
        x0, y0 = pos[tour[i]]
        x1, y1 = pos[tour[(i + 1) % len(tour)]]
        tour_x.extend([x0, x1, None])
        tour_y.extend([y0, y1, None])

    # Tour edges (highlighted)
    tour_trace = go.Scatter(
        x=tour_x,
        y=tour_y,
        mode="lines",
        line=dict(width=3, color="red"),
        hoverinfo="text",
        hovertext="Tour edge",
        name="Tour",
        showlegend=True,
    )

    # Regular edges (non-tour)
    edge_x = []
    edge_y = []

    tour_edges = set()
    for i in range(len(tour)):
        u, v = tour[i], tour[(i + 1) % len(tour)]
        tour_edges.add((min(u, v), max(u, v)))

    for edge in display_edges:
        u, v = min(edge[0], edge[1]), max(edge[0], edge[1])
        if (u, v) not in tour_edges:
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1, color="#aaa"),
        hoverinfo="skip",
        showlegend=False,
    )

    # Nodes
    node_x = []
    node_y = []
    node_text = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        label = names[node] if names and node < len(names) else str(node)
        node_text.append(f"Node {node}<br>{label}")

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=[str(i) for i in G.nodes()],
        textposition="top center",
        hoverinfo="text",
        hovertext=node_text,
        marker=dict(
            size=15,
            color="lightblue",
            line_width=2,
            line_color="darkblue",
        ),
        showlegend=False,
    )

    fig = go.Figure(
        data=[edge_trace, tour_trace, node_trace],
        layout=go.Layout(
            title=title,
            showlegend=True,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, scaleanchor="x", scaleratio=1),
            plot_bgcolor="rgba(240, 240, 240, 0.5)",
            height=height,
            width=width,
        ),
    )

    return fig
