## Plan: Phased Python+Go Migration

This revision assumes all production algorithm services are written in Go, while the coordinator, monitoring, analytics/reference code, and frontend remain in Python. To keep the program usable after every milestone, the migration is phased around a stable Python coordinator: first preserve the current app, then introduce a coordinator abstraction, then progressively move execution from in-process Python to external Go workers. The frontend changes for larger graphs, concurrent algorithm runs, and Timescale-backed progress are introduced only when the backend can support them without breaking the existing flow.

**Phase 0 — Baseline and contracts**
- Freeze the current API and behavior in [src/app/schemas.py](src/app/schemas.py#L15-L61), [src/app/routes_tsp.py](src/app/routes_tsp.py#L18-L151), [frontend/api_client.py](frontend/api_client.py#L13-L120), and [streamlit_app.py](streamlit_app.py#L56-L285).
- Build regression/parity coverage around the current Python algorithms referenced from [src/app/services.py](src/app/services.py#L11-L14), especially `HC`, `Genetic`, and `MCTS`.
- Document the future internal worker contract and the public migration target in [README.md](README.md).

Working program after this phase:
- The existing app works exactly as today.
- There is a reliable benchmark and comparison baseline before any Go rewrite begins.

**Phase 1 — Python coordinator seam**
- Refactor [src/app/services.py](src/app/services.py#L20-L219) so `TSPSolverService` becomes an orchestration layer rather than the only execution engine.
- Introduce an internal execution interface for `solve`, with one implementation still calling the current Python algorithms from [analytics/tsp/domain/basic_solvers.py](analytics/tsp/domain/basic_solvers.py#L17-L39), [analytics/tsp/genetic/genetic_solver.py](analytics/tsp/genetic/genetic_solver.py#L8-L118), and [analytics/tsp/mcts/mct.py](analytics/tsp/mcts/mct.py#L7-L75).
- Remove reliance on mutable singleton request state from [src/app/routes_tsp.py](src/app/routes_tsp.py#L21) and [src/app/services.py](src/app/services.py#L24-L58) so later remote execution is safe.

Working program after this phase:
- Public API and frontend remain unchanged.
- The app still runs fully in Python, but the coordinator is now ready to delegate work to Go services.

**Phase 2 — First Go worker, no UX breakage**
- Add the first Go algorithm worker service and route only `Random` and `HC` through it; keep `Genetic` and `MCTS` local in Python.
- Keep the coordinator in Python in [src/app/main.py](src/app/main.py#L15-L81) and [src/app/routes_tsp.py](src/app/routes_tsp.py#L18-L151), and communicate with the Go worker over internal HTTP.
- Update [docker-compose.yml](docker-compose.yml) and [Dockerfile](Dockerfile) into separate Python and Go service images.

Working program after this phase:
- The full program still works from the current frontend.
- Some algorithms execute in Go, but the user experience remains the same and there is a Python fallback path.

**Phase 3 — Go batch execution foundation**
- Replace the single-method public request contract in [src/app/schemas.py](src/app/schemas.py#L36-L53) with a batch-job model that can describe several algorithm runs for one graph.
- Add async-first coordinator endpoints in [src/app/routes_tsp.py](src/app/routes_tsp.py#L18-L151): submit, status, result, cancel.
- Keep the old blocking solve path temporarily as a compatibility facade mapped onto one-job/one-algorithm execution.
- Introduce Timescale/Postgres persistence for jobs and run state from the Python coordinator.

Working program after this phase:
- The old UI still works through the compatibility path.
- A new async backend exists and can submit one or more runs, even if only `Random` and `HC` are in Go so far.

**Phase 4 — Frontend phase 1: larger graphs + async job flow**
- Raise the current frontend graph-size restrictions in [streamlit_app.py](streamlit_app.py#L112-L118) and [streamlit_app.py](streamlit_app.py#L157-L162), and add explicit large-graph UX safeguards instead of hard small limits.
- Update [frontend/api_client.py](frontend/api_client.py#L37-L74) and [streamlit_app.py](streamlit_app.py#L208-L255) to submit async jobs and poll status/results.
- Keep graph rendering based on [frontend/visualizer.py](frontend/visualizer.py#L206-L458), including dense-graph edge thinning from [frontend/visualizer.py](frontend/visualizer.py#L90-L141).

Working program after this phase:
- Users can generate bigger graphs and still solve them.
- The frontend uses the new job-based API, but initially may still show only final results rather than live progress.

**Phase 5 — Go `Genetic` worker**
- Port the GA execution path from [analytics/tsp/genetic/genetic_solver.py](analytics/tsp/genetic/genetic_solver.py#L8-L118) into a dedicated Go worker.
- Keep Python GA available only as a reference/parity implementation, not as the main production path.
- Extend the coordinator to route `Genetic` jobs to Go and to store richer run metadata in Timescale.

Working program after this phase:
- `Random`, `HC`, and `Genetic` run in Go.
- The coordinator, frontend, and data layer are already stable and usable.

**Phase 6 — Go `MCTS` worker**
- Port [analytics/tsp/mcts/mct.py](analytics/tsp/mcts/mct.py#L7-L75) and [analytics/tsp/mcts/node.py](analytics/tsp/mcts/node.py#L8-L60) into a Go worker.
- Standardize progress messages across all Go workers so the coordinator and monitoring path do not have algorithm-specific branching.
- Keep the Python MCTS implementation only for regression and research comparison.

Working program after this phase:
- All active TSP algorithms run in Go.
- Python remains responsible for coordination, monitoring, persistence, and research/reference only.

**Phase 7 — Monitoring + Timescale progress views**
- Add per-iteration progress and periodic CPU/memory telemetry persistence in Timescale/Postgres from the coordinator/monitoring path.
- Introduce monitoring/query endpoints from Python so the frontend can request progress-as-a-function-of-time and resource usage timelines.
- Store run status, best-so-far cost, elapsed time, and resource samples in a form optimized for comparison across algorithms.

Working program after this phase:
- The program is fully usable with Go execution services and Python coordination.
- Historical and live-enough progress data is saved and queryable.

**Phase 8 — Frontend phase 2: concurrent algorithms + progress dashboard**
- Replace the single algorithm selector in [streamlit_app.py](streamlit_app.py#L208-L211) with multi-select or repeatable algorithm configuration cards.
- Change frontend state from one `solution` object in [streamlit_app.py](streamlit_app.py#L61-L75) and [streamlit_app.py](streamlit_app.py#L257-L267) to one job containing multiple runs.
- Add comparison views using existing Plotly integration in [streamlit_app.py](streamlit_app.py#L188) and [streamlit_app.py](streamlit_app.py#L292): best cost over time, CPU/memory over time, current statuses, and final route comparison using [frontend/visualizer.py](frontend/visualizer.py#L340-L458).

Working program after this phase:
- Users can generate larger graphs, run several algorithms concurrently, and inspect progress/history from Timescale in the UI.
- This is the first phase that fully matches your target product behavior.

**Phase 9 — Cleanup and hard cutover**
- Remove production dependence on Python algorithm execution from [src/app/services.py](src/app/services.py#L20-L219); keep Python analytics only as reference code under [analytics](analytics).
- Finalize health checks, readiness checks, and compose topology in [docker-compose.yml](docker-compose.yml).
- Update tests in [tests/test_tsp.py](tests/test_tsp.py#L6-L68), [tests/test_app.py](tests/test_app.py#L6-L28), and new integration suites so the Go workers, Python coordinator, Timescale persistence, and frontend are all validated together.

Working program after this phase:
- The target architecture is complete: Go algorithm services, Python coordinator/monitoring/analysis, Timescale-backed progress, and a frontend that supports larger graphs and concurrent runs.

**Verification**
- Phase 0–2: confirm the current frontend still solves TSP correctly while selected methods are gradually redirected to Go.
- Phase 3–4: submit async jobs from the frontend and verify final results remain correct.
- Phase 5–6: compare Go worker quality/runtime against the Python reference implementations on a fixed corpus.
- Phase 7–8: verify that one job with GA + MCTS + HC produces separate progress/resource timelines in Timescale and visible comparison charts in the frontend.
- Phase 9: run the full stack via `docker compose up --build` and validate end-to-end operation without Python in the production execution path.

**Decisions**
- Algorithm execution services are Go-only in production.
- Coordinator, monitoring, persistence integration, frontend, and analytics/reference stay in Python.
- PTSP remains out of phase 1 scope and stays as research/reference unless later promoted to a product requirement.
- Every phase preserves a deployable, usable program rather than requiring a full big-bang rewrite.
