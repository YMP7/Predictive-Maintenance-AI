"""Login guard on /api routes and admin device management (config/machines.json)."""
import json

import pytest
from fastapi.testclient import TestClient

from server import machine_registry
from server.auth import User, get_current_user
from server.backend_api import app, service

LIMITS = {
    "vibration": {"warning": 1.5, "critical": 3.0},
    "temperature": {"warning": 60, "critical": 75},
    "current": {"warning": 3.5, "critical": 4.5},
}
NEW = {"machine_id": "M900", "name": "Test Compressor", "type": "Compressor", "location": "Bay 9", "thresholds": LIMITS}


@pytest.fixture
def registry(tmp_path, monkeypatch):
    """Point the registry at a temp copy so tests never touch config/machines.json."""
    path = tmp_path / "machines.json"
    path.write_text(json.dumps({"machines": {"M001": {"name": "Lathe", "type": "Lathe", "location": "A", "thresholds": LIMITS}}}))
    monkeypatch.setattr(machine_registry, "REGISTRY_PATH", path)
    before = dict(service.machine_info)
    yield path
    service.apply_registry(before)


def as_role(role):
    app.dependency_overrides[get_current_user] = lambda: User(username=f"test_{role}", role=role)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("path", ["/api/machines", "/api/dashboard/summary", "/api/alerts/recent", "/api/atlas/cross-domain/comparison"])
def test_reads_require_login(path):
    client = TestClient(app)
    assert client.get(path, headers={"X-API-Request": "true"}).status_code == 401
    assert client.get(path).status_code == 403  # no CSRF header


def test_public_paths_stay_open():
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    # Reaches the login handler (401 for bad credentials), not the guard.
    res = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    assert res.status_code in (401, 429)
    # Phone bridge checks its own token instead of a session.
    assert client.post("/api/atlas/mobile/telemetry", json={}, headers={"X-Mobile-Bridge-Token": "wrong"}).status_code == 401


def test_admin_adds_updates_and_deletes_a_machine(registry):
    as_role("admin")
    client = TestClient(app)

    assert client.post("/api/admin/machines", json=NEW).status_code == 201
    assert "M900" in service.machine_info
    assert service.agent.fault_detector.thresholds["M900"]["temperature"]["warning"] == 60
    assert "M900" in json.loads(registry.read_text())["machines"]
    assert client.post("/api/admin/machines", json=NEW).status_code == 409

    edited = {k: v for k, v in NEW.items() if k != "machine_id"} | {"name": "Renamed"}
    assert client.put("/api/admin/machines/M900", json=edited).status_code == 200
    assert service.machine_info["M900"]["name"] == "Renamed"

    assert client.delete("/api/admin/machines/M900").status_code == 200
    assert "M900" not in service.machine_info
    assert "M900" not in json.loads(registry.read_text())["machines"]
    assert client.delete("/api/admin/machines/M900").status_code == 404


@pytest.mark.parametrize("role", ["viewer", "operator"])
def test_non_admins_cannot_change_devices(registry, role):
    as_role(role)
    client = TestClient(app)
    assert client.post("/api/admin/machines", json=NEW).status_code == 403
    assert client.delete("/api/admin/machines/M001").status_code == 403
    assert "M001" in json.loads(registry.read_text())["machines"]


@pytest.mark.parametrize("bad", [
    {"machine_id": "../etc"},
    {"machine_id": ""},
    {"name": ""},
    {"thresholds": {**LIMITS, "current": {"warning": 5, "critical": 4}}},
])
def test_invalid_device_is_rejected(registry, bad):
    as_role("admin")
    assert TestClient(app).post("/api/admin/machines", json=NEW | bad).status_code == 422
    assert set(json.loads(registry.read_text())["machines"]) == {"M001"}
