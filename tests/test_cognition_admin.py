"""P5 Cognition Dashboard backend: trace history with PCA and drift, fleet cognition health, the model registry
(archive and activate with audit), and a snapshot of the trace's per-stage schema."""

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from server import audit as A
from server import cognition_admin as C
from server import cognition_trace as T
from server.auth import User, get_current_user
from server.backend_api import _get_atlas, app, atlas_api_startup

H = {"X-API-Request": "true"}
SNAPSHOT = Path(__file__).parent / "snapshots" / "trace_schema.json"


@pytest.fixture(scope="module", autouse=True)
def engines():
    atlas_api_startup()


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: User(username="t_admin", role="admin")
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def store(monkeypatch):
    s = T.MemoryTraceStore()
    monkeypatch.setattr(T, "_STORE", s)
    return s


@pytest.fixture
def events(monkeypatch):
    seen = []
    monkeypatch.setattr(A, "audit", lambda **kw: seen.append(kw))
    return seen


def fake_trace(i, sv, rul, truth=None, feats=None, dna=None, machine="u1", domain="cmapss"):
    stages = {
        "adapter": {"normalized": feats or {"s2": 0.5, "s3": 0.5}, "window_hash": f"h{i}"},
        "world_model": {"state_vector": list(sv), "model": "best_model.pt", "version": "abc"},
        "machine_dna": {"dna": dna},
        "rul": {"mean": rul, "p10": rul - 5, "p90": rul + 5, "ground_truth": truth},
        "decision": {"recommended_action": "CONTINUE_OPERATION"},
    }
    return {"domain": domain, "machine_id": machine, "ts": f"2026-11-09T10:{i:02d}:00Z", "replayed": False,
            "total_latency_ms": 40.0 + i,
            "stages": [{"stage": s, "latency_ms": 1.0 + i, "output": stages.get(s, {})} for s in T.STAGES]}


# ---------------------------------------------------------------- pure helpers


def test_projection_is_2d_deterministic_and_explains_variance():
    rng = np.random.default_rng(0)
    base = rng.normal(size=(1, 32))
    vecs = [base[0] + t * np.ones(32) * 0.1 + rng.normal(scale=0.01, size=32) for t in range(20)]
    a, b = C.project_states(vecs), C.project_states(vecs)
    assert len(a["points"]) == 20 and all(len(p) == 2 for p in a["points"])
    assert a == b
    assert 0.9 < a["explained"][0] <= 1.0 and sum(a["explained"]) <= 1.0 + 1e-9
    assert C.project_states([vecs[0]])["points"] == [[0.0, 0.0]]
    assert C.project_states([])["points"] == []


def test_data_drift_ranks_the_shifted_feature_first():
    early = [{"s2": 0.5 + 0.01 * (i % 3), "s3": 0.2 + 0.01 * (i % 3)} for i in range(10)]
    late = [{"s2": 0.5 + 0.01 * (i % 3), "s3": 0.6 + 0.01 * (i % 3)} for i in range(10)]
    d = C.data_drift(early, late)
    assert d[0]["feature"] == "s3" and d[0]["shift_sd"] > 5
    assert abs([x for x in d if x["feature"] == "s2"][0]["shift_sd"]) < 1


def test_data_drift_needs_three_traces_a_side_and_floors_the_sd():
    one = [{"s2": 0.5}]
    assert C.data_drift(one, [{"s2": 0.50001}]) == []
    flat = [{"s2": 0.5}] * 3
    d = C.data_drift(flat, [{"s2": 0.505}] * 3)
    assert d[0]["shift_sd"] == pytest.approx(0.5)  # 0.005 / floor 0.01, not 0.005 / 1e-6


def test_history_caps_ground_truth_at_the_training_cap(client, store):
    """C-MAPSS labels run to 270+ cycles; the model is trained on RUL capped at 125, so error uses the cap."""
    for i in range(4):
        store.save(fake_trace(i, np.zeros(32) + i, 120.0, truth=270.0, machine="capped"))
    h = client.get("/api/admin/cognition/capped/history?domain=cmapss", headers=H).json()
    assert h["truth_cap"] == 125.0
    assert h["points"][0]["ground_truth"] == 125.0
    assert h["drift"]["model"]["mae_recent"] == pytest.approx(5.0)


def test_model_drift_compares_early_and_recent_error():
    pairs = [(100.0, 98.0)] * 5 + [(60.0, 80.0)] * 5  # (prediction, ground truth)
    m = C.model_drift(pairs)
    assert m == {"n": 10, "mae_early": 2.0, "mae_recent": 20.0}
    assert C.model_drift([]) == {"n": 0, "mae_early": None, "mae_recent": None}


def test_dna_drift_is_zero_for_the_same_fingerprint():
    v = list(np.linspace(0.1, 1.6, 16))
    assert C.dna_drift(v, v) == {"l2": 0.0, "cosine": 0.0}
    assert C.dna_drift(v, [x * 2 for x in v])["cosine"] == pytest.approx(0.0, abs=1e-9)
    assert C.dna_drift(None, v) is None


# ---------------------------------------------------------------- history and health


def test_history_returns_rul_band_projection_and_drift(client, store):
    rng = np.random.default_rng(1)
    for i in range(12):
        store.save(fake_trace(i, rng.normal(size=32) + i * 0.2, 120 - i * 5, truth=118 - i * 5,
                              feats={"s2": 0.5, "s3": 0.2 + 0.05 * i}, dna=list(np.linspace(0.1, 1.6, 16) + i * 0.01)))
    store.save(fake_trace(13, rng.normal(size=32), 50, machine="other"))
    res = client.get("/api/admin/cognition/u1/history?domain=cmapss&limit=50", headers=H)
    assert res.status_code == 200, res.text
    h = res.json()
    assert len(h["points"]) == 12 and h["points"][0]["ts"] < h["points"][-1]["ts"]
    p = h["points"][0]
    assert {"ts", "rul_mean", "rul_p10", "rul_p90", "ground_truth", "total_latency_ms", "stage_latency_ms"} <= set(p)
    assert len(h["projection"]["points"]) == 12
    assert h["drift"]["data"][0]["feature"] == "s3"
    assert h["drift"]["model"]["n"] == 12
    assert h["drift"]["dna"]["baseline_ts"] == "2026-11-09T10:00:00Z" and h["drift"]["dna"]["l2"] > 0
    assert set(h["stage_latency_ms"]) == set(T.STAGES)


def test_history_without_traces_is_empty_not_an_error(client, store):
    h = client.get("/api/admin/cognition/nobody/history?domain=cmapss", headers=H).json()
    assert h["points"] == [] and h["projection"]["points"] == []


def test_fleet_health_summarises_traces_per_domain(client, store):
    for i in range(3):
        store.save(fake_trace(i, np.zeros(32), 100, machine=f"u{i}"))
    res = client.get("/api/admin/cognition/health", headers=H)
    assert res.status_code == 200
    rows = {r["domain"]: r for r in res.json()["domains"]}
    assert rows["cmapss"]["traces"] == 3 and rows["cmapss"]["machines"] == 3
    assert rows["cmapss"]["mean_latency_ms"] == pytest.approx(41.0)
    assert {"model_loaded", "using_lstm", "last_trace"} <= set(rows["cmapss"])


def test_cognition_admin_is_admin_only(store):
    app.dependency_overrides[get_current_user] = lambda: User(username="t_op", role="operator")
    try:
        c = TestClient(app)
        assert c.get("/api/admin/cognition/health", headers=H).status_code == 403
        assert c.get("/api/admin/models/registry", headers=H).status_code == 403
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------- model registry


@pytest.fixture
def registry(tmp_path, monkeypatch):
    models, reg = tmp_path / "models", tmp_path / "registry"
    models.mkdir()
    (models / "laptop_world_model.pt").write_bytes(b"weights-v1")
    (models / "laptop_model_metadata.json").write_text(json.dumps({"final_val_loss": 0.5, "epochs": 30}))
    refreshed = []
    monkeypatch.setattr(C, "_dirs", lambda: (models, reg))
    monkeypatch.setattr(C, "_refresh", lambda d: refreshed.append(d) or True)
    return models, reg, refreshed


def test_registry_archives_the_active_checkpoint_once(client, registry):
    models, reg, _ = registry
    r1 = client.get("/api/admin/models/registry", headers=H).json()
    r2 = client.get("/api/admin/models/registry", headers=H).json()
    lap = {d["domain"]: d for d in r2["domains"]}["laptop"]
    assert len(lap["versions"]) == 1 and lap["versions"][0]["active"] is True
    assert lap["active"]["version"] == lap["versions"][0]["version"]
    assert lap["versions"][0]["metrics"]["final_val_loss"] == 0.5
    assert r1["domains"] and len(list((reg / "laptop").glob("*.pt"))) == 1


def test_activate_swaps_weights_reloads_and_audits(client, registry, events):
    models, reg, refreshed = registry
    v1 = {d["domain"]: d for d in client.get("/api/admin/models/registry", headers=H).json()["domains"]}["laptop"]["active"]["version"]
    (models / "laptop_world_model.pt").write_bytes(b"weights-v2")  # a retrain promoted new weights
    v2 = {d["domain"]: d for d in client.get("/api/admin/models/registry", headers=H).json()["domains"]}["laptop"]["active"]["version"]
    assert v1 != v2

    assert client.post("/api/admin/models/laptop/activate", json={"version": v1}, headers=H).status_code == 422
    res = client.post("/api/admin/models/laptop/activate", json={"version": v1, "reason": "v2 drifts on site data"}, headers=H)
    assert res.status_code == 200, res.text
    assert (models / "laptop_world_model.pt").read_bytes() == b"weights-v1"
    assert refreshed == ["laptop"]
    ev = next(e for e in events if e.get("action") == "activate")
    assert ev["category"] == "model" and ev["details"]["before"]["version"] == v2 and ev["details"]["after"]["version"] == v1
    assert ev["details"]["reason"] == "v2 drifts on site data"
    # v2 is still archived, so the rollback itself can be undone
    lap = {d["domain"]: d for d in client.get("/api/admin/models/registry", headers=H).json()["domains"]}["laptop"]
    assert {v["version"] for v in lap["versions"]} == {v1, v2}


def test_activate_unknown_version_or_domain_is_404(client, registry):
    assert client.post("/api/admin/models/laptop/activate", json={"version": "deadbeef0000", "reason": "test it"}, headers=H).status_code == 404
    assert client.post("/api/admin/models/nope/activate", json={"version": "deadbeef0000", "reason": "test it"}, headers=H).status_code == 404


# ---------------------------------------------------------------- trace schema snapshot


@pytest.fixture
def seeded_window():
    _get_atlas().ensure_registered("cmapss")
    engine = _get_atlas().get_engine("cmapss")
    with engine._lock:
        engine._windows["snapshot_unit"] = np.random.default_rng(3).normal(0, 1, size=(30, 14)).astype(float).tolist()
    yield "snapshot_unit"
    engine.clear_machine("snapshot_unit")


def test_trace_schema_matches_the_snapshot(client, store, seeded_window):
    """The dashboard reads these keys. A change to the trace shape must update the snapshot on purpose."""
    trace = client.get(f"/api/admin/cognition/{seeded_window}/trace?domain=cmapss&k=5&seed=42", headers=H).json()
    schema = {s["stage"]: sorted(s["output"]) for s in trace["stages"]}
    schema["_trace"] = sorted(k for k in trace if k != "stages")
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert schema == expected
