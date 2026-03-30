"""Main Streamlit application for TSP/PTSP Solver."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

import streamlit as st
import pandas as pd

from frontend.api_client import APIClient
from frontend.visualizer import (
    create_graph_from_matrix,
    visualize_graph,
    visualize_solution,
)
from frontend.graph_generator import (
    generate_random_matrix,
    generate_euclidean_matrix,
    generate_circle_matrix,
    generate_grid_matrix,
)

if TYPE_CHECKING:
    pass


# Page config
st.set_page_config(
    page_title="TSP/PTSP Solver",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Styling
st.markdown(
    """
    <style>
    .main {
        padding: 0rem 0rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def main() -> None:
    """Main application function."""
    st.title("🗺️ TSP/PTSP Solver")
    st.markdown("Interactive visualization and solver for Traveling Salesman Problem")

    # Initialize session state
    if "api_client" not in st.session_state:
        # Use environment variable for API base URL (Docker-friendly)
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        st.session_state.api_client = APIClient(base_url=api_base_url)
        
    if "solution" not in st.session_state:
        st.session_state.solution = None
        
    if "matrix" not in st.session_state:
        st.session_state.matrix = None
        
    if "names" not in st.session_state:
        st.session_state.names = None

    api_client = st.session_state.api_client

    # Check API health
    with st.spinner("Checking API connection..."):
        if not api_client.check_health():
            st.error(
                "❌ Cannot connect to API server. Please make sure the FastAPI server is running "
                "on http://localhost:8000"
            )
            st.info("Run `docker-compose up` to start the server.")
            return

    st.success("✅ Connected to API")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        graph_source = st.radio(
            "Graph Source",
            ["Generate Sample", "Upload CSV", "Manual Input"],
            help="Choose how to provide the graph data",
        )

        st.divider()

        if graph_source == "Generate Sample":
            sample_type = st.selectbox(
                "Sample Type",
                ["Random", "Euclidean", "Circle", "Grid"],
                help="Type of sample graph to generate",
            )

            n_nodes = st.slider(
                "Number of Nodes",
                min_value=5,
                max_value=50,
                value=10,
                step=1,
                help="Number of cities/nodes in the graph",
            )

            if st.button("📊 Generate Graph", use_container_width=True):
                with st.spinner("Generating graph..."):
                    if sample_type == "Random":
                        matrix = generate_random_matrix(n_nodes, seed=42)
                        names = [f"City {i}" for i in range(n_nodes)]
                    elif sample_type == "Euclidean":
                        matrix, names = generate_euclidean_matrix(n_nodes, seed=42)
                    elif sample_type == "Circle":
                        matrix, names = generate_circle_matrix(n_nodes)
                    else:  # Grid
                        grid_size = int(n_nodes**0.5)
                        matrix, names = generate_grid_matrix(grid_size)

                    st.session_state.matrix = matrix
                    st.session_state.names = names
                    st.session_state.solution = None
                    st.success(f"✅ Generated {sample_type} graph with {len(matrix)} nodes")

        elif graph_source == "Upload CSV":
            uploaded_file = st.file_uploader("Upload adjacency matrix (CSV)", type="csv")
            if uploaded_file is not None:
                with st.spinner("Loading graph..."):
                    df = pd.read_csv(uploaded_file)
                    st.session_state.matrix = df.values.tolist()
                    st.session_state.names = [f"Node {i}" for i in range(len(df))]
                    st.session_state.solution = None
                    st.success(f"✅ Loaded graph with {len(df)} nodes")

        else:  # Manual Input
            st.info("Enter adjacency matrix manually or paste JSON format")
            n_nodes_manual = st.number_input(
                "Number of nodes",
                min_value=3,
                max_value=20,
                value=5,
                step=1,
            )

            if st.button("Create Empty Matrix", use_container_width=True):
                matrix = [[0.0] * n_nodes_manual for _ in range(n_nodes_manual)]
                st.session_state.matrix = matrix
                st.session_state.names = [f"City {i}" for i in range(n_nodes_manual)]
                st.session_state.solution = None

    # Main content
    col1, col2 = st.columns([1, 1])

    if st.session_state.matrix is None:
        st.info("👈 Select or generate a graph from the sidebar to get started")
        return

    # Display graph
    with col1:
        st.subheader("📍 Graph Visualization")
        G = create_graph_from_matrix(st.session_state.matrix, st.session_state.names)
        fig = visualize_graph(G, title="Original Graph")
        st.plotly_chart(fig, use_container_width=True)

    # Display matrix
    with col2:
        st.subheader("📊 Adjacency Matrix")
        df = pd.DataFrame(
            st.session_state.matrix,
            columns=[f"N{i}" for i in range(len(st.session_state.matrix))],
            index=[f"N{i}" for i in range(len(st.session_state.matrix))],
        )
        st.dataframe(df, use_container_width=True)

    st.divider()

    # Solver section
    st.subheader("🚀 Solve Problem")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        method = st.selectbox(
            "Algorithm",
            ["Random", "HC", "Genetic", "MCTS"],
            help="Select the solving algorithm",
        )

    with col2:
        time_limit = st.number_input(
            "Time Limit (s)",
            min_value=1.0,
            max_value=300.0,
            value=30.0,
            step=1.0,
            help="Maximum time to spend solving",
        )

    with col3:
        if method == "Genetic":
            population = st.number_input(
                "Population",
                min_value=10,
                max_value=200,
                value=50,
                step=10,
                help="Population size for genetic algorithm",
            )
        else:
            population = 50

    with col4:
        if method == "Genetic":
            mutate = st.checkbox("Mutation", value=True, help="Enable mutation in genetic algorithm")
        else:
            mutate = True

    solve_button = st.button("▶️ Solve", use_container_width=True, type="primary")

    if solve_button:
        with st.spinner("Solving..."):
            try:
                start = time.time()
                solution = api_client.solve_tsp(
                    matrix=st.session_state.matrix,
                    method=method,
                    time_limit=time_limit,
                    names=st.session_state.names,
                    population=population,
                    mutate=mutate,
                )
                st.session_state.solution = solution
                st.success(f"✅ Solution found in {solution['execution_time']:.2f}s")
            except Exception as e:
                st.error(f"❌ Error solving: {str(e)}")

    # Display solution
    if st.session_state.solution:
        st.divider()
        st.subheader("✨ Solution")

        solution = st.session_state.solution

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Cost", f"{solution['cost']:.2f}")
        with col2:
            st.metric("Tour Length", len(solution['tour']))
        with col3:
            st.metric("Execution Time", f"{solution['execution_time']:.3f}s")
        with col4:
            st.metric("Algorithm", solution['method'])

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("🎯 Tour Visualization")
            G = create_graph_from_matrix(st.session_state.matrix, st.session_state.names)
            fig = visualize_solution(
                G,
                tour=solution["tour"],
                names=st.session_state.names,
                title="Solution Tour",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("🔢 Tour Sequence")
            tour_display = " → ".join(str(n) for n in solution["tour"])
            st.code(tour_display, language="")

            st.subheader("📋 Tour Details")
            tour_df = pd.DataFrame({
                "Step": list(range(len(solution["tour"]) + 1)),
                "City": [st.session_state.names[n] if st.session_state.names else f"City {n}" 
                         for n in solution["tour"]] + [st.session_state.names[solution["tour"][0]] 
                                                       if st.session_state.names else f"City {solution['tour'][0]}"],
                "Node": solution["tour"] + [solution["tour"][0]],
            })
            st.dataframe(tour_df, use_container_width=True)

        # Export options
        st.subheader("💾 Export")
        col1, col2 = st.columns(2)

        with col1:
            tour_json = str(solution["tour"])
            st.download_button(
                label="Download Tour (TXT)",
                data=tour_json,
                file_name="tour.txt",
                mime="text/plain",
            )

        with col2:
            solution_json = str(solution)
            st.download_button(
                label="Download Full Solution (TXT)",
                data=solution_json,
                file_name="solution.txt",
                mime="text/plain",
            )


if __name__ == "__main__":
    main()
