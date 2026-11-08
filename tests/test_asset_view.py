"""3D Asset View backend (D2): asset profiles, part bindings and the TwinFrame."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from server import asset_view as V
from server import audit as A
from server import ingest as I
from server.adapters.asset_profiles import ASSET_PROFILES
from server.adapters.cmapss_adapter import SENSOR_DESCRIPTIONS
from server.adapters.configurable_adapter import SensorProfile
from server.adapters.modbus_adapter import DEFAULT_REGISTER_MAP

H = {"X-API-Request": "true"}
NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


@pytest.mark.parametrize("domain", list(ASSET_PROFILES))
def test_every_binding_points_at_a_real_part(domain):
    p = ASSET_PROFILES[domain]
    ids = [x.id for x in p.parts]
    assert len(ids) == len(set(ids))
    assert all(b.part in ids for b in p.channels.values())
    assert p.spin is None or p.spin in p.channels


def test_bindings_cover_the_adapters_channels():
    # every C-MAPSS model feature and every Modbus register is bound to a part
    assert set(ASSET_PROFILES["cmapss"].channels) == set(SENSOR_DESCRIPTIONS)
    assert {c.name for c in DEFAULT_REGISTER_MAP} == set(ASSET_PROFILES["modbus"].channels)


def test_load_follows_direction_and_neutral_is_ignored():
    assert V.channel_load(0.8, 1) == 0.8
    assert V.channel_load(0.8, -1) == pytest.approx(0.2)
    assert V.channel_load(0.8, 0) is None
    assert V.channel_load(1.7, 1) == 1.0
    assert V.part_state(0.95, True) == "high"
    assert V.part_state(0.8, True) == "elevated"
    assert V.part_state(0.1, True) == "normal"
    assert V.part_state(None, True) == "nodata"
    assert V.part_state(None, True, has_values=True) == "normal"  # neutral channels with readings
    assert V.part_state(None, False) == "unmonitored"


def snapshot(**kw):
    s = {"domain": "cmapss", "machine_id": "unit_1", "timestamp": iso(NOW - timedelta(seconds=2)),
         "health_index": 0.4, "status": "Degrading", "rul_cycles": 61.5, "uncertainty": 9.0, "normalized_rul": 0.49,
         "confidence": 0.8, "using_lstm": True, "adapter_status": "streaming",
         "features": {"s2": 0.95, "s7": 0.9, "s8": 0.3, "s12": 0.2}, "raw_features": {"s2": 643.2, "s8": 2388.1}}
    s.update(kw)
    return s


def test_frame_from_snapshot_binds_parts_and_units():
    f = V.frame_from_snapshot("cmapss", "unit_1", ASSET_PROFILES["cmapss"], snapshot(), NOW)
    assert f["kind"] == "turbofan" and f["attribution"] is True
    ch = {c["feature"]: c for c in f["channels"]}
    assert ch["s2"]["part"] == "lpc" and ch["s2"]["raw"] == 643.2 and ch["s2"]["unit"] == "°R"
    assert ch["s2"]["quality"] == "GOOD"
    assert ch["s3"]["quality"] == "MISSING" and ch["s3"]["load"] is None
    parts = {p["id"]: p for p in f["parts"]}
    assert parts["lpc"]["state"] == "high"            # s2 at 0.95, rises with wear
    assert parts["combustor"]["state"] == "elevated"  # s12 at 0.2, falls with wear: load 0.8
    assert parts["nozzle"]["state"] == "unmonitored"
    assert f["rul"]["value"] == 61.5 and f["rul"]["unit"] == "cycles"
    assert f["spin"] == 0.3


def test_old_snapshot_is_stale_and_simulation_is_flagged():
    old = V.frame_from_snapshot("cmapss", "u", ASSET_PROFILES["cmapss"],
                                snapshot(timestamp=iso(NOW - timedelta(minutes=5))), NOW)
    assert {c["quality"] for c in old["channels"] if c["value"] is not None} == {"STALE"}
    sim = V.frame_from_snapshot("server", "s", ASSET_PROFILES["server"],
                                snapshot(adapter_status="simulation", features={"cpu_usage": 0.5}), NOW)
    assert sim["simulated"] is True
    assert {c["quality"] for c in sim["channels"] if c["value"] is not None} == {"SIMULATED"}
    assert sim["rul"]["unit"] == "steps"


MODBUS_PROFILE = {
    "machine_id": "pump_m1",
    "domain": "modbus",
    "display_name": "Pump M-1",
    "simulated": True,
    "channels": [
        {"channel": "hr_temp", "feature": "temperature_c", "unit": "°C", "valid_min": 0, "valid_max": 120,
         "sampling_hz": 1.0, "health_weight": 1.0},
        {"channel": "hr_vib", "feature": "vibration_mms", "unit": "mm/s", "valid_min": 0, "valid_max": 20,
         "sampling_hz": 1.0, "health_weight": 1.0, "part": "bearing_nde"},
    ],
}


@pytest.fixture
def svc(tmp_path, monkeypatch):
    log = A.AuditLog(jsonl_dir=tmp_path, db_sink=None, load_tail=False)
    monkeypatch.setattr(A, "_LOG", log)
    s = I.IngestService(I.MemoryProfileStore(), I.MemoryDeviceStore(), I.MemoryReadingStore(), I.Broker())
    s.profiles.put(SensorProfile(**MODBUS_PROFILE), actor="test")
    I.set_ingest_service(s)
    yield s
    I.set_ingest_service(None)
    log.close()


@pytest.fixture
def client():
    from server.backend_api import app
    from server.auth import User, get_current_user
    app.dependency_overrides[get_current_user] = lambda: User(username="t_viewer", role="viewer")
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_profiled_machine_frame_uses_the_sensor_profile(svc, client):
    svc.ingest("pump_m1", [{"ts": iso(datetime.now(timezone.utc)), "values": {"hr_temp": 96.0, "hr_vib": 4.0}}],
               source="test", actor="test")
    res = client.get("/api/assets/pump_m1/frame?domain=modbus", headers=H)
    assert res.status_code == 200, res.text
    f = res.json()
    assert f["kind"] == "motor_pump" and f["simulated"] is True and f["rul"] is None and f["rul_note"]
    ch = {c["feature"]: c for c in f["channels"]}
    assert ch["temperature_c"]["raw"] == 96.0 and ch["temperature_c"]["quality"] == "SIMULATED"
    assert ch["vibration_mms"]["part"] == "bearing_nde"  # the profile's part overrides the default binding
    assert ch["current_a"]["quality"] == "MISSING"
    states = {p["id"]: p["state"] for p in f["parts"]}
    assert states["stator"] == "elevated"  # 96 / 120 = 0.8
    assert states["coupling"] == "nodata"  # speed bound but never sent


def test_asset_list_and_profile_endpoints(svc, client):
    assets = client.get("/api/assets", headers=H).json()["assets"]
    pump = next(a for a in assets if a["machine_id"] == "pump_m1")
    assert pump["domain"] == "modbus" and pump["kind"] == "motor_pump" and pump["simulated"] is True
    prof = client.get("/api/atlas/domain/cmapss/profile", headers=H).json()
    assert prof["kind"] == "turbofan" and prof["channels"]["s8"]["part"] == "fan"
    assert client.get("/api/atlas/domain/nope/profile", headers=H).status_code == 404


def test_unknown_asset_is_404_and_bad_domain_is_422(svc, client):
    assert client.get("/api/assets/ghost/frame?domain=modbus", headers=H).status_code == 404
    assert client.get("/api/assets/pump_m1/frame?domain=cmapss", headers=H).status_code == 404
    assert client.get("/api/assets/pump_m1/frame?domain=bad%20domain", headers=H).status_code == 422


def test_frame_needs_a_session():
    from server.backend_api import app
    assert TestClient(app).get("/api/assets/unit_1/frame?domain=cmapss", headers=H).status_code == 401


def test_modbus_bridge_profile_is_valid_and_bound():
    from scripts.modbus_bridge import sensor_profile
    sp = SensorProfile(**sensor_profile("pump_m1", simulated=True))
    assert sp.simulated and sp.domain == "modbus"
    assert {c.feature for c in sp.channels} == set(ASSET_PROFILES["modbus"].channels)
