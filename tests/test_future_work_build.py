"""The four items that were FUTURE-WORK on the title matrix: pump RUL (SIMULATED), attribution for every
domain, retraining for every domain with a recorded history, and the column order those models read."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from server import audit as A
from server import ingest as I
from server.adapters import pump_degradation as pd
from server.adapters.asset_profiles import ASSET_PROFILES, sensor_profile_template
from server.adapters.base_adapter import NormalizedReading
from server.adapters.configurable_adapter import SensorProfile
from server.adapters.domain_profile import DOMAIN_PROFILES, get_profile
from server.adapters.modbus_simulator import ModbusSimulator
from server.atlas.explain import ExplanationEngine, feature_layout
from server.atlas.learning_engine import LearningEngine
from server.atlas.profiled_inference import model_window
from server.atlas.world_model import MODELS_DIR, WorldModel

ROOT = Path(__file__).resolve().parent.parent
H = {"X-API-Request": "true"}


# ---------------------------------------------------------------- simulated pump wear


def test_wear_runs_from_the_simulators_nominal_state_to_its_degraded_state():
    quiet = SimpleNamespace(normal=lambda *a, **k: 0.0)  # no noise
    nominal, failed = pd.registers_at(0.0, 1.0, quiet), pd.registers_at(1.0, 1.0, quiet)
    assert nominal == [450, 1250, 142, 3600, 320, 88]
    assert failed == [780, 5650, 220, 3520, 180, 72]


def test_a_simulated_unit_is_a_run_to_failure_with_capped_labels():
    feats, rul = pd.simulate_unit(np.random.default_rng(0))
    assert feats.shape == (len(rul), 6) and pd.LIFE_RANGE[0] <= len(rul) <= pd.LIFE_RANGE[1]
    assert feats.min() >= 0.0 and feats.max() <= 1.0
    assert rul[0] == pd.MAX_RUL_CAP and rul[-1] == 0.0 and np.all(np.diff(rul) <= 0)
    vib = pd.FEATURES.index("vibration_mms")
    assert feats[-10:, vib].mean() > 3 * feats[:10, vib].mean()  # vibration climbs with wear


def test_simulator_run_to_failure_counts_down_and_restarts():
    sim = ModbusSimulator()
    sim.start_run_to_failure(seed=5, start_fraction=0.99)
    left = sim.true_rul
    assert 0 < left <= 4
    sim.step()
    assert sim.true_rul == left - 1 and sim._registers[1] > 4000  # near failure: vibration above 4 mm/s
    for _ in range(left):
        sim.step()
    assert sim.true_rul > 100  # a new unit started
    sim.set_state("nominal")
    assert sim.true_rul is None


# ---------------------------------------------------------------- pump RUL in the product


def pump_profile(**kw):
    p = sensor_profile_template("modbus", "pump_t1", simulated=True)
    p.update(kw)
    return SensorProfile(**p)


@pytest.fixture
def svc(tmp_path, monkeypatch):
    log = A.AuditLog(jsonl_dir=tmp_path, db_sink=None, load_tail=False)
    monkeypatch.setattr(A, "_LOG", log)
    s = I.IngestService(I.MemoryProfileStore(), I.MemoryDeviceStore(), I.MemoryReadingStore(), I.Broker())
    s.profiles.put(pump_profile(), actor="test")
    I.set_ingest_service(s)
    yield s
    I.set_ingest_service(None)
    log.close()


@pytest.fixture
def client():
    from server.auth import User, get_current_user
    from server.backend_api import app

    app.dependency_overrides[get_current_user] = lambda: User(username="t_viewer", role="viewer")
    yield TestClient(app)
    app.dependency_overrides.clear()


_T0 = datetime.now(timezone.utc) - timedelta(seconds=600)
_sent = iter(range(10_000))


def push(svc, wear_levels):
    """One sample per wear level, in engineering units, as scripts/modbus_bridge.py sends them."""
    from server.adapters.modbus_adapter import DEFAULT_REGISTER_MAP

    rng = np.random.default_rng(1)
    samples = []
    for d in wear_levels:
        regs = pd.registers_at(d, 1.0, rng)
        # strictly increasing times: an older sample never replaces the latest value
        samples.append({"ts": (_T0 + timedelta(milliseconds=50 * next(_sent))).isoformat().replace("+00:00", "Z"),
                        "values": {c.name: r * c.scale + c.offset for c, r in zip(DEFAULT_REGISTER_MAP, regs)}})
    svc.ingest("pump_t1", samples, source="test", actor="test")


def test_pump_frame_is_pending_until_thirty_readings_then_shows_rul(svc, client):
    push(svc, [0.02] * 10)
    f = client.get("/api/assets/pump_t1/frame?domain=modbus", headers=H).json()
    assert f["rul"] is None and f["rul_pending"] is True and f["rul_note"].startswith("Warming up: 10/30")
    assert client.get("/api/atlas/domain/modbus/machine/pump_t1/window", headers=H).status_code == 409

    push(svc, [0.02] * 30)
    healthy = client.get("/api/assets/pump_t1/frame?domain=modbus", headers=H).json()
    assert healthy["simulated"] is True and healthy["attribution"] is True and healthy["rul_note"] is None
    assert healthy["rul"]["unit"] == "cycles" and healthy["rul"]["provenance"] == "SIMULATED"
    assert healthy["rul"]["uncertainty"] > 0

    push(svc, list(np.linspace(0.75, 0.95, 30)))
    worn = client.get("/api/assets/pump_t1/frame?domain=modbus", headers=H).json()
    assert worn["rul"]["value"] < 30 < healthy["rul"]["value"]

    w = client.get("/api/atlas/domain/modbus/machine/pump_t1/window", headers=H).json()
    assert w["seq_len"] == 30 and w["feature_dim"] == 6
    assets = client.get("/api/assets", headers=H).json()["assets"]
    assert next(a for a in assets if a["machine_id"] == "pump_t1")["rul"]["value"] == pytest.approx(worn["rul"]["value"])


def test_a_profile_that_does_not_match_the_trained_layout_gets_no_prediction(svc):
    t = sensor_profile_template("modbus", "pump_t1", simulated=True)
    shuffled = pump_profile(channels=list(reversed(t["channels"])))
    svc.put_profile(shuffled, actor="test")
    push(svc, [0.5] * 30)
    window, reason = model_window(svc.adapter("pump_t1"))
    assert reason is None
    # columns come back in the trained order whatever order the profile lists them in
    temp = pd.FEATURES.index("temperature_c")
    assert window[-1][temp] == pytest.approx(svc.adapter("pump_t1").get_reading("pump_t1").features["temperature_c"])

    rescaled = [dict(c, valid_max=200.0) if c["feature"] == "temperature_c" else c for c in t["channels"]]
    svc.put_profile(pump_profile(channels=rescaled), actor="test")
    assert "scales temperature_c differently" in model_window(svc.adapter("pump_t1"))[1]

    svc.put_profile(pump_profile(channels=t["channels"][:3]), actor="test")
    assert "lacks channels" in model_window(svc.adapter("pump_t1"))[1]


def test_recorded_pump_evaluation_is_labelled_simulated_and_beats_a_constant_guess(client):
    res = client.get("/api/atlas/research/pump-rul", headers=H)
    assert res.status_code == 200
    r = res.json()
    assert r["provenance"] == "SIMULATED" and "No real pump failure data" in r["disclosure"]
    assert r["shipped_checkpoint"]["n_units"] == 50
    assert r["shipped_checkpoint"]["rmse"] < r["baseline_constant_mean"]["rmse"]
    assert json.loads((MODELS_DIR / "modbus_model_metadata.json").read_text())["provenance"] == "SIMULATED"


# ---------------------------------------------------------------- column order


def reading_with(domain, features):
    return NormalizedReading(domain=domain, machine_id="m", timestamp="2026-01-01T00:00:00Z", health_index=0.1,
                             cycle=0, rul_label=None, features=features, raw_features={}, operational_ctx={}, metadata={})


@pytest.mark.parametrize("domain", ["laptop", "mobile", "server"])
def test_live_feature_vector_uses_the_order_the_model_was_trained_on(domain):
    from server.atlas.pretrain_domain import DOMAIN_FEATURE_MAP

    trained = DOMAIN_FEATURE_MAP[domain]
    assert list(get_profile(domain).features) == trained
    reading = reading_with(domain, {f: i / 10 for i, f in enumerate(trained)})
    assert reading.feature_vector == [i / 10 for i in range(len(trained))]


def test_a_modbus_device_with_its_own_channel_names_keeps_its_own_layout():
    r = reading_with("modbus", {"b_flow": 0.2, "a_level": 0.7})
    assert r.feature_vector == [0.7, 0.2]


# ---------------------------------------------------------------- attribution for every domain


class Sum:
    """A model whose output is 10 * column 1 plus column 3, so the true drivers are known."""
    config = SimpleNamespace(seq_len=30)

    def predict(self, window):
        w = np.asarray(window).reshape(30, -1)
        return SimpleNamespace(rul_pred=float(10 * w[:, 1].mean() + w[:, 3].mean()))


@pytest.mark.parametrize("domain", [d for d in DOMAIN_PROFILES if d != "cmapss"])
def test_attribution_names_the_domains_own_sensors_and_ranks_the_true_driver_first(domain):
    features = get_profile(domain).features
    names, baseline = feature_layout(domain, len(features))
    assert [n.split(" ")[0] for n in names] == list(features)
    assert set(features) <= set(ASSET_PROFILES[domain].channels)   # so the 3D view can bind each one to a part
    assert all(0.0 < b < 1.0 for b in baseline)                    # a population mean, not the 0.0 extreme

    window = np.ones((30, len(features)), dtype=np.float32)
    ace = SimpleNamespace(get_world_model=lambda d, n: Sum())
    out, reason = ExplanationEngine().calculate_feature_attribution(window, ace, Sum().predict(window).rul_pred, domain)
    assert reason is None and len(out) == len(features)
    assert out[0]["sensor_name"] == names[1] and out[1]["sensor_name"] == names[3]
    assert out[0]["magnitude"] == pytest.approx(10 * (1.0 - baseline[1]), rel=1e-4)


def test_attribution_says_why_when_it_cannot_run():
    eng, ace = ExplanationEngine(), SimpleNamespace(get_world_model=lambda d, n: Sum())
    assert "No sensor layout" in eng.calculate_feature_attribution(np.ones((30, 4)), ace, 1.0, "laptop")[1]
    assert "No sensor layout" in eng.calculate_feature_attribution(np.ones((30, 5)), ace, 1.0, "unknown_domain")[1]
    assert "30 steps" in eng.calculate_feature_attribution(np.ones((12, 5)), ace, 1.0, "laptop")[1]
    none = SimpleNamespace(get_world_model=lambda d, n: None)
    assert "No trained World Model" in eng.calculate_feature_attribution(np.ones((30, 5)), none, 1.0, "laptop")[1]


def test_explanation_keeps_the_attribution_when_memory_has_no_ground_truth():
    from server.atlas.adaptive_context import AdaptiveContext, NeighborContext

    window = np.ones((30, 5), dtype=np.float32)
    ctx = AdaptiveContext(domain="laptop", machine_id="m", query_cycle=1, predicted_rul=Sum().predict(window).rul_pred,
                          average_neighbor_rul=0.0, machine_dna=None,
                          neighbors=[NeighborContext(machine_id="a", cycle=1, rul=None, distance=0.1)])
    ace = SimpleNamespace(get_world_model=lambda d, n: Sum())
    report = ExplanationEngine().explain(ctx, window=window, ace=ace)
    assert len(report.sensor_attributions) == 5 and report.top_contributors[0].startswith("memory_usage")
    assert "strongest driver" in report.primary_justification and "shorter RUL" not in report.primary_justification


def test_recorded_deletion_test_covers_every_domain(client):
    r = client.get("/api/atlas/research/attribution-faithfulness", headers=H).json()
    assert set(r["domains"]) == set(DOMAIN_PROFILES)
    assert r["domains"]["cmapss"]["summary"] == r["summary"]
    for domain, d in r["domains"].items():
        assert d["provenance"] == ("NASA benchmark" if domain == "cmapss" else "SIMULATED")
        k2 = d["summary"]["k2"]
        assert k2["mean_abs_delta_top"] > k2["mean_abs_delta_random"], domain


# ---------------------------------------------------------------- retraining for every domain


def test_every_domain_has_a_retraining_data_source():
    assert LearningEngine.data_source("cmapss") == "benchmark"
    assert LearningEngine.data_source("modbus") == "simulated_failure"
    assert {LearningEngine.data_source(d) for d in ("laptop", "mobile", "server")} == {"simulated_profile"}
    assert LearningEngine.data_source("unknown_domain") is None
    assert LearningEngine(log_events=False).retrain_domain(domain="unknown_domain").success is False


@pytest.mark.parametrize("domain", ["laptop", "modbus"])
def test_gate_promotes_and_rejects_on_the_domains_own_validation_data(domain, tmp_path):
    import shutil

    path = tmp_path / "model.pt"
    shutil.copy2(MODELS_DIR / get_profile(domain).checkpoints[-1], path)
    before = path.read_bytes()
    engine = LearningEngine(model_path=path, log_events=False)
    base = engine._validation_rmse(WorldModel.load(path), domain)
    assert 0 < base < (0.2 if domain == "laptop" else 30)  # the shipped model fits its own validation data

    rejected = engine.retrain_domain(domain=domain, epochs=1, forced_candidate_rmse=base * 1.5)
    assert rejected.success is False and "SIMULATED" in rejected.notes and path.read_bytes() == before
    promoted = engine.retrain_domain(domain=domain, epochs=1, forced_candidate_rmse=base * 0.9)
    assert promoted.success is True and promoted.rmse_before == pytest.approx(base)


def test_a_seeded_retraining_run_is_reproducible(tmp_path):
    import shutil

    results = []
    for i in range(2):
        path = tmp_path / f"m{i}.pt"
        shutil.copy2(MODELS_DIR / "laptop_world_model.pt", path)
        results.append(LearningEngine(model_path=path, log_events=False)
                       .retrain_domain(domain="laptop", epochs=1, lr=1e-4, seed=7).rmse_after)
    assert results[0] == pytest.approx(results[1], rel=1e-6)


def test_recorded_retrain_history_has_promotions_and_rejections_per_domain(client):
    res = client.get("/api/atlas/research/retrain-history", headers=H)
    assert res.status_code == 200
    r = res.json()
    assert r["total_runs"] == len(r["runs"]) >= 20 and r["promoted"] + r["rejected"] == r["total_runs"]
    assert set(r["by_domain"]) == set(DOMAIN_PROFILES)
    assert r["promoted"] > 0 and r["rejected"] > 0
    for run in r["runs"]:
        mine = [x for x in r["runs"] if x["domain"] == run["domain"]]
        best = min([x["val_rmse_after"] for x in mine if x["promoted"] and x["run"] < run["run"]]
                   + [mine[0]["val_rmse_before"]])
        # the gate as specified: promoted exactly when within 3% of the best so far
        assert run["promoted"] == (run["val_rmse_after"] <= best * 1.03 + 1e-4), run
