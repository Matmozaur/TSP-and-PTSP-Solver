"""Graph visualization utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx
import plotly.graph_objects as go
import plotly.express as px

if TYPE_CHECKING:
    pass


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
    # Use spring layout for better visualization
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    # Create edge traces
    edge_x = []
    edge_y = []
    edge_text = []

    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        weight = edge[2].get("weight", 1)
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
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
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
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

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

    for edge in G.edges():
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
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="rgba(240, 240, 240, 0.5)",
            height=height,
            width=width,
        ),
    )

    return fig
