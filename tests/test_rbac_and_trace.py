"""RBAC (viewer / operator / admin) and the read-only cognition trace endpoint (D5 backend)."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from server.backend_api import app, atlas_api_startup, _get_atlas
from server.auth import User, get_current_user
from server import cognition_trace as T

H = {"X-API-Request": "true"}


@pytest.fixture(scope="module", autouse=True)
def engines():
    atlas_api_startup()


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def as_role(role):
    app.dependency_overrides[get_current_user] = lambda: User(username=f"t_{role}", role=role)


@pytest.mark.parametrize("path", [
    "/api/admin/cognition/unit_1/trace?domain=cmapss",
    "/api/admin/devices",
    "/api/admin/sensor-profiles",
    "/api/admin/anything-new",
])
def test_operator_gets_403_on_every_admin_path(client, path):
    as_role("operator")
    assert client.get(path, headers=H).status_code == 403


def test_viewer_can_read_but_not_write(client):
    as_role("viewer")
    assert client.get("/api/machines", headers=H).status_code == 200
    assert client.post("/api/simulation/start", headers=H).status_code == 403
    assert client.get("/api/admin/devices", headers=H).status_code == 403


def test_readiness_is_public_and_reports_dependencies(client):
    res = client.get("/api/ready")
    assert res.status_code in (200, 503)
    body = res.json()
    for key in ("database", "mqtt", "models", "audit"):
        assert key in body["checks"]


@pytest.fixture
def seeded_window():
    _get_atlas().ensure_registered("cmapss")
    engine = _get_atlas().get_engine("cmapss")
    rng = np.random.default_rng(7)
    with engine._lock:
        engine._windows["trace_test_unit"] = rng.normal(0, 1, size=(30, 14)).astype(float).tolist()
    yield "trace_test_unit"
    engine.clear_machine("trace_test_unit")


@pytest.fixture
def memory_traces(monkeypatch):
    store = T.MemoryTraceStore()
    monkeypatch.setattr(T, "_STORE", store)
    return store


def test_trace_returns_every_stage_in_order(client, seeded_window, memory_traces):
    as_role("admin")
    res = client.get(f"/api/admin/cognition/{seeded_window}/trace?domain=cmapss&k=5&seed=42", headers=H)
    assert res.status_code == 200, res.text
    trace = res.json()
    assert [s["stage"] for s in trace["stages"]] == T.STAGES
    for s in trace["stages"]:
        assert s["latency_ms"] >= 0
    by = {s["stage"]: s["output"] for s in trace["stages"]}

    assert len(by["adapter"]["window"]) == 30
    assert len(by["world_model"]["state_vector"]) == 32  # frozen dimension
    assert len(by["amkb"]["neighbors"]) <= 5
    assert "dna" in by["machine_dna"]  # None for a unit without stored DNA, 16 values otherwise
    if by["machine_dna"]["dna"] is not None:
        assert len(by["machine_dna"]["dna"]) == 16
    rul = by["rul"]
    assert rul["p10"] <= rul["mean"] <= rul["p90"]
    assert by["simulation"]["seed"] == 42 and by["simulation"]["n"] == 1000
    assert sum(by["simulation"]["histogram"]["counts"]) == 1000
    assert by["decision"]["recommended_action"]
    assert "citations" in by["explainability"] or "neighbor_citations" in by["explainability"]
    assert "history" in by["learning"]
    assert trace["total_latency_ms"] >= sum(s["latency_ms"] for s in trace["stages"]) * 0.5


def test_trace_is_deterministic_for_a_seed(client, seeded_window, memory_traces):
    as_role("admin")
    a = client.get(f"/api/admin/cognition/{seeded_window}/trace?domain=cmapss&seed=42", headers=H).json()
    b = client.get(f"/api/admin/cognition/{seeded_window}/trace?domain=cmapss&seed=42", headers=H).json()
    sa = {s["stage"]: s["output"] for s in a["stages"]}
    sb = {s["stage"]: s["output"] for s in b["stages"]}
    assert sa["simulation"] == sb["simulation"]
    assert sa["decision"]["recommended_action"] == sb["decision"]["recommended_action"]


def test_trace_replay_returns_the_stored_trace(client, seeded_window, memory_traces):
    as_role("admin")
    live = client.get(f"/api/admin/cognition/{seeded_window}/trace?domain=cmapss", headers=H).json()
    replay = client.get(f"/api/admin/cognition/{seeded_window}/trace?domain=cmapss&ts={live['ts']}", headers=H)
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True and replay.json()["ts"] == live["ts"]


def test_trace_for_machine_without_window_is_409(client, memory_traces):
    as_role("admin")
    res = client.get("/api/admin/cognition/never_seen_unit/trace?domain=cmapss", headers=H)
    assert res.status_code in (404, 409)


def test_trace_does_not_change_model_outputs(client, seeded_window, memory_traces):
    """The trace calls the same engines as /api/context; the RUL must agree."""
    as_role("admin")
    window = _get_atlas().get_engine("cmapss")._windows[seeded_window]
    ctx = client.post("/api/context", json={"domain": "cmapss", "machine_id": seeded_window, "cycle": 0,
                                            "window": window, "k": 5}, headers=H).json()
    trace = client.get(f"/api/admin/cognition/{seeded_window}/trace?domain=cmapss&k=5", headers=H).json()
    rul = {s["stage"]: s["output"] for s in trace["stages"]}["rul"]
    assert rul["mean"] == pytest.approx(ctx["predicted_rul"], rel=1e-5)
