"""Sensor ingestion (D3): configurable adapter, quality flags, device tokens, push paths,
rate and size limits, CSV backfill, manual entry, MQTT routing and the live stream."""

import asyncio
import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from server import audit as A
from server.adapters.configurable_adapter import ConfigurableAdapter, SensorProfile
from server import ingest as I

PROFILE = {
    "machine_id": "pump_p101",
    "domain": "rotating_asset",
    "display_name": "Pump P-101",
    "channels": [
        # raw tenths of a degree -> kelvin: K = raw * 0.1 + 273.15
        {"channel": "bearing_temp", "feature": "bearing_temp", "unit": "K", "scale": 0.1, "offset": 273.15,
         "valid_min": 273.15, "valid_max": 393.15, "sampling_hz": 1.0, "health_weight": 1.0, "part": "bearing_de"},
        {"channel": "motor_current", "feature": "motor_current", "unit": "A", "valid_min": 0.0, "valid_max": 40.0,
         "sampling_hz": 1.0, "flatline_samples": 5, "part": "winding"},
    ],
}


def now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


@pytest.fixture
def adapter():
    a = ConfigurableAdapter(SensorProfile(**PROFILE))
    a.connect()
    yield a
    a.disconnect()


# ---------------------------------------------------------------- adapter


def test_scaling_and_normalisation(adapter):
    t = now()
    res = adapter.ingest([{"ts": iso(t), "values": {"bearing_temp": 600, "motor_current": 10}}], now=t)
    assert res.accepted_samples == 1 and not res.rejects
    rows = {r["channel"]: r for r in res.rows}
    assert rows["bearing_temp"]["value"] == pytest.approx(333.15)  # 60.0 degC in K
    assert rows["bearing_temp"]["unit"] == "K"
    reading = adapter.get_reading("pump_p101")
    assert reading.features["bearing_temp"] == pytest.approx(0.5)
    assert reading.features["motor_current"] == pytest.approx(0.25)
    assert reading.health_index == pytest.approx(0.5)  # only bearing_temp carries health weight


def test_out_of_range_is_flagged_not_dropped(adapter):
    t = now()
    res = adapter.ingest([{"ts": iso(t), "values": {"motor_current": 55}}], now=t)
    assert res.rows[0]["quality"] == "OUT_OF_RANGE"
    assert adapter.get_reading("pump_p101").features["motor_current"] == 1.0  # clipped for the model


def test_bad_values_and_channels_are_rejected_with_reasons(adapter):
    t = now()
    res = adapter.ingest([
        {"ts": iso(t), "values": {"motor_current": "NaN", "bearing_temp": 600}},
        {"ts": iso(t), "values": {"vibration": 1.2}},
        {"ts": "not-a-time", "values": {"motor_current": 3}},
        {"ts": iso(t + timedelta(minutes=10)), "values": {"motor_current": 3}},
    ], now=t)
    reasons = " | ".join(r.reason for r in res.rejects)
    assert "not a finite number" in reasons
    assert "unknown channel" in reasons
    assert "invalid timestamp" in reasons
    assert "in the future" in reasons
    assert res.accepted_samples == 1  # only the first sample's bearing_temp survives


def test_old_samples_are_rejected_on_push_but_allowed_for_backfill(adapter):
    t = now()
    old = {"ts": iso(t - timedelta(days=30)), "values": {"motor_current": 3}}
    assert adapter.ingest([old], now=t).rejects[0].reason.startswith("older than")
    assert adapter.ingest([old], now=t, max_age_s=None).accepted_samples == 1


def test_stale_flatline_and_missing_quality(adapter):
    t = now()
    for i in range(5):
        adapter.ingest([{"ts": iso(t + timedelta(seconds=i)), "values": {"motor_current": 7}}], now=t + timedelta(seconds=i))
    q = adapter.channel_quality(now=t + timedelta(seconds=5))
    assert q["motor_current"] == "FLATLINE"
    assert q["bearing_temp"] == "MISSING"
    assert adapter.channel_quality(now=t + timedelta(seconds=60))["motor_current"] == "STALE"  # > 3 x 1 s


def test_simulated_profile_marks_every_value(adapter):
    a = ConfigurableAdapter(SensorProfile(**{**PROFILE, "simulated": True}))
    a.connect()
    t = now()
    res = a.ingest([{"ts": iso(t), "values": {"motor_current": 3}}], now=t)
    assert res.rows[0]["quality"] == "SIMULATED"
    assert a.get_reading("pump_p101").adapter_status == "simulation"


def test_profile_validation():
    with pytest.raises(ValueError):
        SensorProfile(**{**PROFILE, "channels": [{**PROFILE["channels"][0], "valid_min": 5, "valid_max": 1}]})
    with pytest.raises(ValueError):
        SensorProfile(**{**PROFILE, "machine_id": "../etc"})
    with pytest.raises(ValueError):
        SensorProfile(**{**PROFILE, "channels": [PROFILE["channels"][0], PROFILE["channels"][0]]})


def test_window_tracks_feature_vectors(adapter):
    t = now()
    for i in range(3):
        adapter.ingest([{"ts": iso(t + timedelta(seconds=i)), "values": {"bearing_temp": 600 + i, "motor_current": 10}}],
                       now=t + timedelta(seconds=i))
    w = adapter.window()
    assert len(w) == 3 and len(w[0]) == 2


# ---------------------------------------------------------------- service and HTTP


@pytest.fixture
def svc(tmp_path, monkeypatch):
    log = A.AuditLog(jsonl_dir=tmp_path, db_sink=None, load_tail=False)
    monkeypatch.setattr(A, "_LOG", log)
    s = I.IngestService(I.MemoryProfileStore(), I.MemoryDeviceStore(), I.MemoryReadingStore(), I.Broker(),
                        rate_per_s=5, burst=5)
    s.profiles.put(SensorProfile(**PROFILE), actor="test")
    device_id, token = s.devices.create("pump_p101", protocol="http")
    I.set_ingest_service(s)
    yield s, device_id, token, log
    I.set_ingest_service(None)
    log.close()


@pytest.fixture
def client():
    from server.backend_api import app
    yield TestClient(app)
    app.dependency_overrides.clear()


def as_role(role):
    from server.backend_api import app
    from server.auth import User, get_current_user
    app.dependency_overrides[get_current_user] = lambda: User(username=f"t_{role}", role=role)


def push(client, token, body, machine="pump_p101"):
    return client.post(f"/api/ingest/{machine}", json=body, headers={"Authorization": f"Bearer {token}"})


def test_http_push_accepts_flags_and_rejects(svc, client):
    s, _, token, log = svc
    t = now()
    res = push(client, token, {"samples": [
        {"ts": iso(t), "values": {"bearing_temp": 600, "motor_current": 10}},
        {"ts": iso(t), "values": {"motor_current": 55}},
        {"ts": iso(t), "values": {"vibration": 1}},
    ]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["accepted_samples"] == 2
    assert body["rejected"] == 1 and "unknown channel" in body["rejects"][0]["reason"]
    stored = s.readings.rows
    assert {r["quality"] for r in stored} == {"GOOD", "OUT_OF_RANGE"}
    assert all(r["batch_id"] == body["batch_id"] and r["source"] == "http" for r in stored)
    log.flush()
    ingest_events = [e for e in A.read_jsonl(log.jsonl_dir) if e["category"] == "ingest"]
    assert ingest_events and ingest_events[-1]["details"]["batch_id"] == body["batch_id"]
    assert "values" not in json.dumps(ingest_events[-1]["details"])  # references the batch, no raw values


def test_single_sample_body_is_accepted(svc, client):
    _, _, token, _ = svc
    res = push(client, token, {"values": {"motor_current": 3}})
    assert res.status_code == 200 and res.json()["accepted_samples"] == 1


def test_push_without_valid_token_is_401(svc, client):
    assert push(client, "atl_wrong", {"values": {"motor_current": 3}}).status_code == 401
    assert client.post("/api/ingest/pump_p101", json={"values": {}}).status_code == 401


def test_token_bound_to_another_machine_is_403(svc, client):
    s, _, _, _ = svc
    s.profiles.put(SensorProfile(**{**PROFILE, "machine_id": "pump_p102"}), actor="test")
    _, other = s.devices.create("pump_p102", protocol="http")
    assert push(client, other, {"values": {"motor_current": 3}}).status_code == 403


def test_tokens_are_hashed_at_rest_and_rotatable(svc, client):
    s, device_id, token, _ = svc
    stored = s.devices.rows[device_id]["token_hash"]
    assert token not in json.dumps(s.devices.rows)
    assert stored == hashlib.sha256(token.encode()).hexdigest()
    new_token = s.devices.rotate(device_id)
    assert push(client, token, {"values": {"motor_current": 3}}).status_code == 401
    assert push(client, new_token, {"values": {"motor_current": 3}}).status_code == 200


def test_per_device_rate_limit(svc, client):
    _, _, token, _ = svc
    codes = [push(client, token, {"values": {"motor_current": 3}}).status_code for _ in range(8)]
    assert codes.count(429) >= 1
    assert codes[0] == 200


def test_oversized_body_is_413(svc, client):
    _, _, token, _ = svc
    big = {"samples": [{"values": {"motor_current": 1}}] * 20000}
    assert push(client, token, big).status_code == 413


def test_csv_backfill_dry_run_then_commit(svc, client):
    s, _, _, _ = svc
    as_role("admin")
    t = now() - timedelta(days=40)
    csv_text = (
        "ts,bearing_temp,motor_current\n"
        f"{iso(t)},600,10\n"
        f"{iso(t + timedelta(seconds=1))},610,abc\n"
        f"{iso(t + timedelta(seconds=2))},620,12\n"
    )
    files = {"file": ("backfill.csv", csv_text, "text/csv")}
    dry = client.post("/api/admin/ingest/pump_p101/upload?dry_run=true", files=files, headers={"X-API-Request": "true"})
    assert dry.status_code == 200, dry.text
    report = dry.json()
    assert report["dry_run"] is True and report["rows"] == 3
    assert report["rejected"] == 1 and "not a finite number" in report["rejects"][0]["reason"]
    assert s.readings.rows == []
    commit = client.post("/api/admin/ingest/pump_p101/upload?dry_run=false", files=files, headers={"X-API-Request": "true"})
    assert commit.status_code == 200 and commit.json()["dry_run"] is False
    assert len(s.readings.rows) == 5  # 3 + 2 channel values; one bad value rejected
    assert {r["source"] for r in s.readings.rows} == {"csv"}


def test_manual_entry_needs_operator(svc, client):
    s, _, _, _ = svc
    as_role("viewer")
    body = {"values": {"motor_current": 4.2}, "note": "round 3"}
    assert client.post("/api/machines/pump_p101/manual-readings", json=body, headers={"X-API-Request": "true"}).status_code == 403
    as_role("operator")
    res = client.post("/api/machines/pump_p101/manual-readings", json=body, headers={"X-API-Request": "true"})
    assert res.status_code == 200, res.text
    assert s.readings.rows[-1]["source"] == "manual"


def test_unknown_machine_is_404(svc, client):
    _, _, token, _ = svc
    assert push(client, token, {"values": {"x": 1}}, machine="no_such_machine").status_code in (403, 404)


def test_mqtt_payload_for_profiled_machine_goes_through_the_adapter(svc):
    s, _, _, _ = svc
    from server.mqtt_client import route_to_ingest
    assert route_to_ingest("pump_p101", {"values": {"motor_current": 9}}) is True
    assert s.readings.rows[-1]["source"] == "mqtt"
    assert route_to_ingest("M001", {"vibration_x": 1}) is False  # legacy machines keep the old path


def test_websocket_push(svc, client):
    _, _, token, _ = svc
    with client.websocket_connect("/api/ingest/ws/pump_p101") as ws:
        ws.send_json({"token": token})
        assert ws.receive_json()["status"] == "authenticated"
        ws.send_json({"values": {"motor_current": 3}})
        ack = ws.receive_json()
        assert ack["accepted_samples"] == 1


def test_websocket_rejects_bad_token(svc, client):
    from starlette.websockets import WebSocketDisconnect
    with client.websocket_connect("/api/ingest/ws/pump_p101") as ws:
        ws.send_json({"token": "atl_wrong"})
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


# ---------------------------------------------------------------- live stream


def test_broker_delivers_events_published_from_another_thread():
    broker = I.Broker()

    async def main():
        q = broker.subscribe("pump_p101")
        threading.Thread(target=broker.publish, args=("pump_p101", {"kind": "reading", "n": 1})).start()
        event = await asyncio.wait_for(q.get(), timeout=2)
        broker.unsubscribe("pump_p101", q)
        return event

    assert asyncio.run(main())["n"] == 1


def test_sse_stream_sends_retry_heartbeat_and_readings():
    broker = I.Broker()

    class FakeRequest:
        calls = 0

        async def is_disconnected(self):
            FakeRequest.calls += 1
            return FakeRequest.calls > 3

    async def main():
        gen = I.sse_events(FakeRequest(), broker, "pump_p101", heartbeat_s=0.05, snapshot=None)
        first = await gen.__anext__()
        broker.publish("pump_p101", {"kind": "reading", "values": {"motor_current": 3}})
        rest = [chunk async for chunk in gen]
        return first, rest

    first, rest = asyncio.run(main())
    assert first.startswith("retry: ")
    joined = "".join(rest)
    assert "event: reading" in joined
    assert "event: heartbeat" in joined
