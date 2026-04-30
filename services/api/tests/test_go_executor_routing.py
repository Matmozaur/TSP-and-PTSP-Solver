"""Tests for Go-worker routing in RemoteGoExecutor."""

from __future__ import annotations

import pytest
import networkx as nx

from app.services import GoWorkerError, RemoteGoExecutor


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict:
        return self._payload


class _CapturingClient:
    def __init__(self, response_payload: dict):
        self.calls: list[tuple[str, dict]] = []
        self._response_payload = response_payload

    def post(self, path: str, json: dict) -> _FakeResponse:
        self.calls.append((path, json))
        return _FakeResponse(self._response_payload)

    def close(self) -> None:
        return


class _FailingClient:
    def post(self, path: str, json: dict) -> _FakeResponse:
        raise RuntimeError("go worker unavailable")

    def close(self) -> None:
        return


class _FallbackExecutor:
    def __init__(self, result: dict):
        self.calls: list[dict] = []
        self._result = result

    def execute(self, request: dict) -> dict:
        self.calls.append(request)
        return self._result


def _build_graph() -> nx.Graph:
    graph = nx.Graph()
    graph.add_weighted_edges_from(
        [
            (0, 1, 10.0),
            (1, 2, 20.0),
            (2, 0, 15.0),
        ]
    )
    return graph


@pytest.mark.unit
def test_remote_executor_routes_genetic_and_includes_params() -> None:
    """Go worker receives correct payload when request succeeds (fallback mode)."""
    fallback = _FallbackExecutor(
        result={"tour": [0, 1, 2], "cost": 45.0, "method": "Genetic", "execution_time": 0.1}
    )
    executor = RemoteGoExecutor(
        base_url="http://example.invalid",
        timeout_seconds=5.0,
        fallback=fallback,
        strict=False,
    )
    client = _CapturingClient(
        response_payload={"tour": [2, 1, 0], "cost": 42.0, "method": "Genetic", "execution_time": 0.05}
    )
    executor._client = client
    executor._clients_by_base_url[executor._base_url] = client

    result = executor.execute(
        {
            "method": "Genetic",
            "graph": _build_graph(),
            "max_time": 1.5,
            "population_size": 80,
            "mutate": False,
            "simulation_type": "nearest",
        }
    )

    assert result["method"] == "Genetic"
    assert result["tour"] == [2, 1, 0]
    assert len(client.calls) == 1
    assert fallback.calls == []

    path, payload = client.calls[0]
    assert path == "/solve"
    assert payload["method"] == "Genetic"
    assert payload["population_size"] == 80
    assert payload["mutate"] is False
    assert payload["max_time"] == 1.5


@pytest.mark.unit
def test_remote_executor_falls_back_for_mcts_on_remote_error() -> None:
    """In fallback mode, Python executor is used when Go worker fails."""
    fallback_result = {
        "tour": [0, 2, 1],
        "cost": 45.0,
        "method": "MCTS",
        "execution_time": 0.2,
    }
    fallback = _FallbackExecutor(result=fallback_result)
    executor = RemoteGoExecutor(
        base_url="http://example.invalid",
        timeout_seconds=5.0,
        fallback=fallback,
        strict=False,
    )
    executor._client = _FailingClient()
    executor._clients_by_base_url[executor._base_url] = executor._client

    result = executor.execute(
        {
            "method": "MCTS",
            "graph": _build_graph(),
            "max_time": 1.0,
            "population_size": 50,
            "mutate": True,
            "simulation_type": "nearest lottery",
        }
    )

    assert result == fallback_result
    assert len(fallback.calls) == 1
    assert fallback.calls[0]["method"] == "MCTS"


@pytest.mark.unit
def test_strict_mode_raises_on_go_worker_error() -> None:
    """In strict mode, Go worker failure raises GoWorkerError (no fallback)."""
    executor = RemoteGoExecutor(
        base_url="http://example.invalid",
        timeout_seconds=5.0,
        fallback=None,
        strict=True,
    )
    executor._client = _FailingClient()
    executor._clients_by_base_url[executor._base_url] = executor._client

    with pytest.raises(GoWorkerError) as exc_info:
        executor.execute(
            {
                "method": "Random",
                "graph": _build_graph(),
                "max_time": 1.0,
                "population_size": 50,
                "mutate": True,
                "simulation_type": "nearest",
            }
        )

    assert exc_info.value.method == "Random"
    assert "example.invalid" in exc_info.value.url


@pytest.mark.unit
def test_strict_mode_succeeds_when_go_worker_responds() -> None:
    """In strict mode, successful Go worker response is returned normally."""
    executor = RemoteGoExecutor(
        base_url="http://example.invalid",
        timeout_seconds=5.0,
        fallback=None,
        strict=True,
    )
    client = _CapturingClient(
        response_payload={"tour": [1, 0, 2], "cost": 35.0, "method": "HC", "execution_time": 0.1}
    )
    executor._client = client
    executor._clients_by_base_url[executor._base_url] = client

    result = executor.execute(
        {
            "method": "HC",
            "graph": _build_graph(),
            "max_time": 2.0,
            "population_size": 50,
            "mutate": True,
            "simulation_type": "nearest",
        }
    )

    assert result["method"] == "HC"
    assert result["tour"] == [1, 0, 2]
    assert result["cost"] == 35.0
