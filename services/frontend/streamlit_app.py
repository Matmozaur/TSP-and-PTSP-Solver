"""Main Streamlit application for TSP/PTSP Solver."""

from __future__ import annotations

import os
from typing import Any, TYPE_CHECKING

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from helpers.api_client import APIClient
from helpers.visualizer import (
    create_graph_from_matrix,
    visualize_graph,
    visualize_solution,
)
from helpers.graph_generator import (
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
st.markdown("""
<style>
.main { padding: 0rem 0rem; }
.metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

_ALL_METHODS = ["Random", "HC", "Genetic", "MCTS"]
_ALGORITHM_COLORS = {
    "Random": "#636EFA",
    "HC": "#EF553B",
    "Genetic": "#00CC96",
    "MCTS": "#AB63FA",
}


def _build_runs(
    methods: list[str],
    time_limit: float,
    population: int,
    mutate: bool,
    simulation_type: str,
) -> list[dict[str, Any]]:
    runs = []
    for method in methods:
        run: dict[str, Any] = {
            "method": method,
            "time_limit": time_limit,
            "population": population,
            "mutate": mutate,
            "simulation_type": simulation_type,
        }
        runs.append(run)
    return runs


def _render_comparison_tab(job_result: dict[str, Any], names: list[str] | None) -> None:
    runs = job_result.get("runs", [])
    completed = [r for r in runs if r.get("status") == "COMPLETED" and r.get("result")]

    # Summary table
    rows = []
    for r in runs:
        result = r.get("result") or {}
        rows.append({
            "Algorithm": r["method"],
            "Status": r["status"],
            "Cost": f"{result['cost']:.4f}" if result.get("cost") is not None else "—",
            "Time (s)": f"{result['execution_time']:.3f}" if result.get("execution_time") is not None else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if not completed:
        st.info("No completed runs to compare.")
        return

    # Cost comparison bar chart
    methods = [r["method"] for r in completed]
    costs = [r["result"]["cost"] for r in completed]
    colors = [_ALGORITHM_COLORS.get(m, "#888") for m in methods]

    fig = go.Figure(go.Bar(
        x=methods,
        y=costs,
        marker_color=colors,
        text=[f"{c:.2f}" for c in costs],
        textposition="auto",
    ))
    fig.update_layout(
        title="Cost Comparison",
        xaxis_title="Algorithm",
        yaxis_title="Tour Cost",
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_tours_tab(
    job_result: dict[str, Any],
    matrix: list[list[float]],
    names: list[str] | None,
    layout_hint: str | None,
) -> None:
    completed = [
        r for r in job_result.get("runs", [])
        if r.get("status") == "COMPLETED" and r.get("result")
    ]
    if not completed:
        st.info("No completed runs to visualize.")
        return

    G = create_graph_from_matrix(matrix, names)
    cols_per_row = 2
    for i in range(0, len(completed), cols_per_row):
        row_runs = completed[i:i + cols_per_row]
        cols = st.columns(len(row_runs))
        for col, run in zip(cols, row_runs):
            with col:
                result = run["result"]
                st.markdown(f"**{run['method']}** — cost: {result['cost']:.2f}")
                fig = visualize_solution(
                    G,
                    tour=result["tour"],
                    names=names,
                    title=f"{run['method']} Tour",
                    layout_hint=layout_hint,
                    height=400,
                )
                st.plotly_chart(fig, use_container_width=True)


def _render_progress_tab(
    api_client: APIClient,
    job_id: str,
    job_result: dict[str, Any],
) -> None:
    try:
        progress_data = api_client.get_job_progress(job_id)
    except Exception as exc:
        st.warning(f"Could not fetch progress data: {exc}")
        return

    runs_progress = progress_data.get("runs", [])
    if not any(r["samples"] for r in runs_progress):
        st.info("No telemetry samples available for this job.")
        return

    has_cpu = any(
        s.get("cpu_percent") is not None
        for r in runs_progress for s in r["samples"]
    )
    has_mem = any(
        s.get("memory_mb") is not None
        for r in runs_progress for s in r["samples"]
    )

    if has_cpu:
        fig_cpu = go.Figure()
        for run in runs_progress:
            xs = [s["elapsed_seconds"] for s in run["samples"] if s.get("elapsed_seconds") is not None]
            ys = [s["cpu_percent"] for s in run["samples"] if s.get("cpu_percent") is not None]
            if xs and ys:
                fig_cpu.add_trace(go.Scatter(
                    x=xs, y=ys, mode="lines+markers",
                    name=run["method"],
                    line=dict(color=_ALGORITHM_COLORS.get(run["method"], "#888")),
                ))
        fig_cpu.update_layout(
            title="CPU Usage Over Time",
            xaxis_title="Elapsed Seconds",
            yaxis_title="CPU %",
            height=300,
        )
        st.plotly_chart(fig_cpu, use_container_width=True)
    else:
        st.info("CPU telemetry not available (psutil not installed in this environment).")

    if has_mem:
        fig_mem = go.Figure()
        for run in runs_progress:
            xs = [s["elapsed_seconds"] for s in run["samples"] if s.get("elapsed_seconds") is not None]
            ys = [s["memory_mb"] for s in run["samples"] if s.get("memory_mb") is not None]
            if xs and ys:
                fig_mem.add_trace(go.Scatter(
                    x=xs, y=ys, mode="lines+markers",
                    name=run["method"],
                    line=dict(color=_ALGORITHM_COLORS.get(run["method"], "#888")),
                ))
        fig_mem.update_layout(
            title="Memory Usage Over Time",
            xaxis_title="Elapsed Seconds",
            yaxis_title="Memory (MB)",
            height=300,
        )
        st.plotly_chart(fig_mem, use_container_width=True)

    # Final costs from progress samples
    final_costs = {}
    for run in runs_progress:
        if run["samples"]:
            last = run["samples"][-1]
            if last.get("best_cost") is not None:
                final_costs[run["method"]] = last["best_cost"]
    if final_costs:
        st.markdown("**Final costs recorded in telemetry:**")
        for method, cost in final_costs.items():
            st.markdown(f"- **{method}**: {cost:.4f}")


def main() -> None:
    """Main application function."""
    st.title("🗺️ TSP/PTSP Solver")
    st.markdown("Interactive visualization and solver for Traveling Salesman Problem")

    # Initialize session state
    if "api_client" not in st.session_state:
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        st.session_state.api_client = APIClient(base_url=api_base_url)

    if "job_result" not in st.session_state:
        st.session_state.job_result = None

    if "job_id" not in st.session_state:
        st.session_state.job_id = None

    if "matrix" not in st.session_state:
        st.session_state.matrix = None

    if "names" not in st.session_state:
        st.session_state.names = None

    if "graph_layout" not in st.session_state:
        st.session_state.graph_layout = None

    if "active_job_id" not in st.session_state:
        st.session_state.active_job_id = None

    api_client = st.session_state.api_client

    with st.spinner("Checking API connection..."):
        if not api_client.check_health():
            st.error(
                "❌ Cannot connect to API server. Please make sure the FastAPI server is running "
                "on http://localhost:8000"
            )
            st.info("Run `docker-compose up` to start the server.")
            return

    st.success("✅ Connected to API")

    # ---- Sidebar: graph source ----
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
                "Number of Nodes", min_value=5, max_value=500, value=10, step=1,
                help="Number of cities/nodes in the graph",
            )
            if st.button("📊 Generate Graph", use_container_width=True):
                with st.spinner("Generating graph..."):
                    if sample_type == "Random":
                        matrix = generate_random_matrix(n_nodes, seed=42)
                        names = [f"City {i}" for i in range(n_nodes)]
                        layout_hint = "random"
                    elif sample_type == "Euclidean":
                        matrix, names = generate_euclidean_matrix(n_nodes, seed=42)
                        layout_hint = "euclidean"
                    elif sample_type == "Circle":
                        matrix, names = generate_circle_matrix(n_nodes)
                        layout_hint = "circle"
                    else:
                        grid_size = int(n_nodes**0.5)
                        matrix, names = generate_grid_matrix(grid_size)
                        layout_hint = "grid"

                    st.session_state.matrix = matrix
                    st.session_state.names = names
                    st.session_state.graph_layout = layout_hint
                    st.session_state.job_result = None
                    st.session_state.job_id = None
                    st.success(f"✅ Generated {sample_type} graph with {len(matrix)} nodes")

        elif graph_source == "Upload CSV":
            uploaded_file = st.file_uploader("Upload adjacency matrix (CSV)", type="csv")
            if uploaded_file is not None:
                with st.spinner("Loading graph..."):
                    df = pd.read_csv(uploaded_file)
                    st.session_state.matrix = df.values.tolist()
                    st.session_state.names = [f"Node {i}" for i in range(len(df))]
                    st.session_state.graph_layout = None
                    st.session_state.job_result = None
                    st.session_state.job_id = None
                    st.success(f"✅ Loaded graph with {len(df)} nodes")

        else:  # Manual Input
            st.info("Enter adjacency matrix manually or paste JSON format")
            n_nodes_manual = st.number_input(
                "Number of nodes", min_value=3, max_value=500, value=5, step=1,
            )
            if st.button("Create Empty Matrix", use_container_width=True):
                matrix = [[0.0] * n_nodes_manual for _ in range(n_nodes_manual)]
                st.session_state.matrix = matrix
                st.session_state.names = [f"City {i}" for i in range(n_nodes_manual)]
                st.session_state.graph_layout = None
                st.session_state.job_result = None
                st.session_state.job_id = None

    # ---- Main content ----
    col1, col2 = st.columns([1, 1])

    if st.session_state.matrix is None:
        st.info("👈 Select or generate a graph from the sidebar to get started")
        return

    with col1:
        st.subheader("📍 Graph Visualization")
        G = create_graph_from_matrix(st.session_state.matrix, st.session_state.names)
        fig = visualize_graph(
            G,
            title="Original Graph",
            layout_hint=st.session_state.graph_layout,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 Adjacency Matrix")
        df = pd.DataFrame(
            st.session_state.matrix,
            columns=[f"N{i}" for i in range(len(st.session_state.matrix))],
            index=[f"N{i}" for i in range(len(st.session_state.matrix))],
        )
        st.dataframe(df, use_container_width=True)

    st.divider()

    # ---- Solver section ----
    st.subheader("🚀 Solve Problem")

    # Multi-algorithm selection
    selected_methods = st.multiselect(
        "Algorithms to run",
        _ALL_METHODS,
        default=["HC"],
        help="Select one or more algorithms to run concurrently",
    )

    col1, col2 = st.columns(2)
    with col1:
        time_limit = st.number_input(
            "Time Limit per Algorithm (s)",
            min_value=1.0, max_value=300.0, value=5.0, step=1.0,
            help="Maximum time for each algorithm run",
        )

    with col2:
        n_nodes_current = len(st.session_state.matrix)
        if n_nodes_current > 200:
            st.info(f"📊 Graph has {n_nodes_current} nodes. Runs will execute asynchronously.")

    with st.expander("⚙️ Advanced Algorithm Options"):
        adv_col1, adv_col2, adv_col3 = st.columns(3)
        with adv_col1:
            population = st.number_input(
                "Genetic: Population", min_value=10, max_value=500, value=50, step=10,
            )
        with adv_col2:
            mutate = st.checkbox("Genetic: Mutation", value=True)
        with adv_col3:
            simulation_type = st.selectbox(
                "MCTS: Simulation Type", ["nearest", "lottery"],
            )

    col_solve, col_cancel = st.columns([3, 1])
    solve_button = col_solve.button(
        "▶️ Solve", use_container_width=True, type="primary",
        disabled=not selected_methods,
    )
    cancel_button = col_cancel.button(
        "⏹️ Cancel",
        use_container_width=True,
        disabled=st.session_state.get("active_job_id") is None,
    )

    if not selected_methods:
        st.warning("Select at least one algorithm to run.")

    if cancel_button and st.session_state.get("active_job_id"):
        try:
            api_client.cancel_job(st.session_state.active_job_id)
            st.warning("Cancellation requested.")
            st.session_state.active_job_id = None
        except Exception as e:
            st.error(f"❌ Cancel failed: {e}")

    if solve_button and selected_methods:
        runs = _build_runs(
            methods=selected_methods,
            time_limit=time_limit,
            population=int(population),
            mutate=mutate,
            simulation_type=simulation_type,
        )

        progress_bar = st.progress(0, text="Submitting job...")

        try:
            submit_resp = api_client.submit_job(
                matrix=st.session_state.matrix,
                runs=runs,
                names=st.session_state.names,
            )
            job_id = submit_resp["job_id"]
            st.session_state.active_job_id = job_id

            progress_bar.progress(10, text=f"Job submitted ({job_id[:8]}…). Waiting for results…")

            def _on_status(status_payload: dict) -> None:
                job_runs = status_payload.get("runs", [])
                total = max(len(job_runs), 1)
                done = sum(
                    1 for r in job_runs
                    if r.get("status") in {"COMPLETED", "FAILED", "CANCELLED"}
                )
                running = sum(1 for r in job_runs if r.get("status") == "RUNNING")
                pct = int(10 + 85 * done / total)
                label = f"Running… ({done}/{total} runs complete"
                if running:
                    label += f", {running} in progress"
                label += ")"
                progress_bar.progress(min(pct, 95), text=label)

            poll_timeout = max(time_limit * len(runs) * 3, 30.0)
            final_status = api_client.poll_job_until_done(
                job_id, poll_interval=0.5, timeout=poll_timeout, on_status=_on_status,
            )
            st.session_state.active_job_id = None

            if final_status["status"] == "CANCELLED":
                progress_bar.progress(100, text="Job cancelled.")
                st.warning("Job was cancelled.")
            elif final_status["status"] == "FAILED":
                progress_bar.progress(100, text="Job failed.")
                job_runs = final_status.get("runs", [])
                errors = [r.get("error") for r in job_runs if r.get("error")]
                detail = errors[0] if errors else "Unknown error"
                st.error(f"❌ Job failed: {detail}")
            else:
                progress_bar.progress(100, text="Done!")
                result_resp = api_client.get_job_result(job_id)
                st.session_state.job_result = result_resp
                st.session_state.job_id = job_id
                completed_count = sum(
                    1 for r in result_resp.get("runs", [])
                    if r.get("status") == "COMPLETED"
                )
                st.success(f"✅ {completed_count}/{len(runs)} runs completed")

        except TimeoutError:
            st.session_state.active_job_id = None
            progress_bar.progress(100, text="Timed out.")
            st.error("❌ Job timed out. Try increasing the time limit.")
        except Exception as e:
            st.session_state.active_job_id = None
            progress_bar.progress(100, text="Error.")
            st.error(f"❌ Error solving: {e}")

    # ---- Results ----
    if st.session_state.job_result:
        st.divider()
        st.subheader("✨ Results")

        tab_comparison, tab_tours, tab_progress = st.tabs(
            ["📊 Comparison", "🗺️ Tours", "📈 Progress"]
        )

        with tab_comparison:
            _render_comparison_tab(st.session_state.job_result, st.session_state.names)

        with tab_tours:
            _render_tours_tab(
                st.session_state.job_result,
                st.session_state.matrix,
                st.session_state.names,
                st.session_state.graph_layout,
            )

        with tab_progress:
            if st.session_state.job_id:
                _render_progress_tab(
                    api_client,
                    st.session_state.job_id,
                    st.session_state.job_result,
                )
            else:
                st.info("No job ID available for progress data.")

        # Export section
        st.subheader("💾 Export")
        completed_runs = [
            r for r in st.session_state.job_result.get("runs", [])
            if r.get("status") == "COMPLETED" and r.get("result")
        ]
        if completed_runs:
            import json as _json
            export_data = _json.dumps(
                [{"method": r["method"], "result": r["result"]} for r in completed_runs],
                indent=2,
            )
            st.download_button(
                label="Download Results (JSON)",
                data=export_data,
                file_name="tsp_results.json",
                mime="application/json",
            )


if __name__ == "__main__":
    main()



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

    if "graph_layout" not in st.session_state:
        st.session_state.graph_layout = None

    if "active_job_id" not in st.session_state:
        st.session_state.active_job_id = None

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
                max_value=500,
                value=10,
                step=1,
                help="Number of cities/nodes in the graph",
            )

            if st.button("📊 Generate Graph", use_container_width=True):
                with st.spinner("Generating graph..."):
                    if sample_type == "Random":
                        matrix = generate_random_matrix(n_nodes, seed=42)
                        names = [f"City {i}" for i in range(n_nodes)]
                        layout_hint = "random"
                    elif sample_type == "Euclidean":
                        matrix, names = generate_euclidean_matrix(n_nodes, seed=42)
                        layout_hint = "euclidean"
                    elif sample_type == "Circle":
                        matrix, names = generate_circle_matrix(n_nodes)
                        layout_hint = "circle"
                    else:  # Grid
                        grid_size = int(n_nodes**0.5)
                        matrix, names = generate_grid_matrix(grid_size)
                        layout_hint = "grid"

                    st.session_state.matrix = matrix
                    st.session_state.names = names
                    st.session_state.graph_layout = layout_hint
                    st.session_state.solution = None
                    st.success(f"✅ Generated {sample_type} graph with {len(matrix)} nodes")

        elif graph_source == "Upload CSV":
            uploaded_file = st.file_uploader("Upload adjacency matrix (CSV)", type="csv")
            if uploaded_file is not None:
                with st.spinner("Loading graph..."):
                    df = pd.read_csv(uploaded_file)
                    st.session_state.matrix = df.values.tolist()
                    st.session_state.names = [f"Node {i}" for i in range(len(df))]
                    st.session_state.graph_layout = None
                    st.session_state.solution = None
                    st.success(f"✅ Loaded graph with {len(df)} nodes")

        else:  # Manual Input
            st.info("Enter adjacency matrix manually or paste JSON format")
            n_nodes_manual = st.number_input(
                "Number of nodes",
                min_value=3,
                max_value=500,
                value=5,
                step=1,
            )

            if st.button("Create Empty Matrix", use_container_width=True):
                matrix = [[0.0] * n_nodes_manual for _ in range(n_nodes_manual)]
                st.session_state.matrix = matrix
                st.session_state.names = [f"City {i}" for i in range(n_nodes_manual)]
                st.session_state.graph_layout = None
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
        fig = visualize_graph(
            G,
            title="Original Graph",
            layout_hint=st.session_state.graph_layout,
        )
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

    n_nodes_current = len(st.session_state.matrix)

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
            value=5.0,
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

    if n_nodes_current > 200:
        st.info(
            f"📊 Graph has {n_nodes_current} nodes. The job will run asynchronously "
            "and progress will be displayed below."
        )

    col_solve, col_cancel = st.columns([3, 1])
    solve_button = col_solve.button("▶️ Solve", use_container_width=True, type="primary")
    cancel_button = col_cancel.button(
        "⏹️ Cancel",
        use_container_width=True,
        disabled=st.session_state.get("active_job_id") is None,
    )

    # Handle cancellation
    if cancel_button and st.session_state.get("active_job_id"):
        try:
            api_client.cancel_job(st.session_state.active_job_id)
            st.warning("Cancellation requested.")
            st.session_state.active_job_id = None
        except Exception as e:
            st.error(f"❌ Cancel failed: {e}")

    if solve_button:
        run_config: dict = {
            "method": method,
            "time_limit": time_limit,
            "population": population,
            "mutate": mutate,
            "simulation_type": "nearest",
        }

        progress_bar = st.progress(0, text="Submitting job...")

        try:
            # Submit as an async job
            submit_resp = api_client.submit_job(
                matrix=st.session_state.matrix,
                runs=[run_config],
                names=st.session_state.names,
            )
            job_id = submit_resp["job_id"]
            st.session_state.active_job_id = job_id

            progress_bar.progress(10, text=f"Job submitted ({job_id[:8]}…). Waiting for results…")

            # Poll until terminal
            def _on_status(status_payload: dict) -> None:
                """Update the progress bar based on run statuses."""
                runs = status_payload.get("runs", [])
                total = max(len(runs), 1)
                done = sum(
                    1 for r in runs if r.get("status") in {"COMPLETED", "FAILED", "CANCELLED"}
                )
                running = sum(1 for r in runs if r.get("status") == "RUNNING")
                pct = int(10 + 85 * done / total)  # 10-95% range
                label = f"Running… ({done}/{total} runs complete"
                if running:
                    label += f", {running} in progress"
                label += ")"
                progress_bar.progress(min(pct, 95), text=label)

            # Use a per-run timeout relative to the time limit
            poll_timeout = max(time_limit * 3, 30.0)

            final_status = api_client.poll_job_until_done(
                job_id,
                poll_interval=0.5,
                timeout=poll_timeout,
                on_status=_on_status,
            )

            st.session_state.active_job_id = None

            if final_status["status"] == "CANCELLED":
                progress_bar.progress(100, text="Job cancelled.")
                st.warning("Job was cancelled.")
            elif final_status["status"] == "FAILED":
                progress_bar.progress(100, text="Job failed.")
                # Show first error among runs
                runs = final_status.get("runs", [])
                errors = [r.get("error") for r in runs if r.get("error")]
                detail = errors[0] if errors else "Unknown error"
                st.error(f"❌ Job failed: {detail}")
            else:
                progress_bar.progress(100, text="Done!")
                # Fetch full result payload
                result_resp = api_client.get_job_result(job_id)
                runs = result_resp.get("runs", [])

                # For single-run compatibility, grab the first completed result
                completed_runs = [
                    r for r in runs
                    if r.get("status") == "COMPLETED" and r.get("result")
                ]
                if completed_runs:
                    solution = completed_runs[0]["result"]
                    st.session_state.solution = solution
                    st.success(f"✅ Solution found in {solution['execution_time']:.2f}s")
                else:
                    st.error("❌ No completed runs found in job result.")

        except TimeoutError:
            st.session_state.active_job_id = None
            progress_bar.progress(100, text="Timed out.")
            st.error("❌ Job timed out waiting for results. Try increasing the time limit.")
        except Exception as e:
            st.session_state.active_job_id = None
            progress_bar.progress(100, text="Error.")
            st.error(f"❌ Error solving: {e}")

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
                layout_hint=st.session_state.graph_layout,
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
