import pytest
from fastapi.testclient import TestClient

from backend_api import app


client = TestClient(app)


def test_health_and_machine_listing():
    health = client.get("/health")
    machines = client.get("/api/machines")

    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert machines.status_code == 200
    assert len(machines.json()) == 4


@pytest.mark.parametrize(
    "path",
    [
        "/api/machines/UNKNOWN/status",
        "/api/machines/UNKNOWN/telemetry",
        "/api/machines/UNKNOWN/trends",
        "/api/alerts/machine/UNKNOWN",
    ],
)
def test_unknown_machine_returns_404(path):
    response = client.get(path)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/api/machines/M001/telemetry?limit=0",
        "/api/alerts/recent?limit=501",
        "/api/simulation/start?interval=0",
    ],
)
def test_invalid_numeric_parameters_return_422(path, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    response = client.post(path) if "simulation/start" in path else client.get(path)
    assert response.status_code == 422


def test_control_endpoint_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-secret")
    endpoint = "/api/machines/M001/fault"
    payload = {"fault_mode": "normal"}

    assert client.post(endpoint, json=payload).status_code == 401
    assert client.post(endpoint, json=payload, headers={"X-API-Key": "wrong"}).status_code == 401
    response = client.post(
        endpoint,
        json=payload,
        headers={"X-API-Key": "test-secret"},
    )

    assert response.status_code == 200
    assert response.json()["fault_mode"] == "normal"
