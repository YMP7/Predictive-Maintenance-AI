import pytest
from fastapi.testclient import TestClient

from server.backend_api import app


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
    ],
)
def test_invalid_numeric_parameters_return_422(path):
    response = client.get(path)
    assert response.status_code == 422


def test_control_endpoint_jwt_auth():
    endpoint = "/api/machines/M001/fault"
    payload = {"fault_mode": "normal"}

    # 1. Unauthenticated request should fail
    assert client.post(endpoint, json=payload).status_code == 401

    # 2. Login to get token
    login_resp = client.post("/api/auth/login", json={"username": "test_admin", "password": "test_admin_public_pw_123"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # 3. Authenticated request should succeed
    response = client.post(
        endpoint,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["fault_mode"] == "normal"


def test_login_rate_limiting():
    """The 6th rapid login attempt within a minute should return 429."""
    from server.backend_api import limiter
    # Reset any existing rate limit state so this test is isolated
    limiter.reset()

    login_payload = {"username": "admin", "password": "pEwtQK_v9yoeFM5jD7zKuA"}

    # First 5 attempts should succeed (200) or fail auth (401) — not 429
    for i in range(5):
        resp = client.post("/api/auth/login", json=login_payload)
        assert resp.status_code in (200, 401), f"Attempt {i+1} returned {resp.status_code}"

    # 6th attempt should be rate-limited
    resp = client.post("/api/auth/login", json=login_payload)
    assert resp.status_code == 429, f"Expected 429 on 6th attempt, got {resp.status_code}"


def test_no_duplicate_password_hashes():
    """Ensure no two accounts share the same password/hash (prevents privilege escalation)."""
    from server.backend_api import fake_users_db
    
    seen_hashes = set()
    for username, data in fake_users_db.items():
        pwd_hash = data.get("hashed_password")
        assert pwd_hash not in seen_hashes, f"Duplicate hash found for user {username}! They share a password with another account."
        seen_hashes.add(pwd_hash)


def test_demo_viewer_privilege():
    """Verify demo_viewer can login but gets 403 on privileged endpoints."""
    # We use a mocked password for demo_viewer so we can test it
    from server.backend_api import fake_users_db
    from server import auth
    
    # Temporarily set demo_viewer's password to a known value for testing
    original_hash = fake_users_db["demo_viewer"]["hashed_password"]
    test_pw = "temp_test_pw_123"
    fake_users_db["demo_viewer"]["hashed_password"] = auth.get_password_hash(test_pw)
    
    try:
        from server.backend_api import limiter
        limiter.reset()
        
        # 1. Login
        login_resp = client.post("/api/auth/login", json={"username": "demo_viewer", "password": test_pw})
        assert login_resp.status_code == 200, "demo_viewer login failed"
        token = login_resp.json()["access_token"]
        assert login_resp.json()["role"] == "viewer"
        
        # 2. Try privileged action
        endpoint = "/api/machines/M001/fault"
        payload = {"fault_mode": "critical"}
        fault_resp = client.post(
            endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fault_resp.status_code == 403, "demo_viewer should be forbidden from fault endpoints"
    finally:
        # Restore
        fake_users_db["demo_viewer"]["hashed_password"] = original_hash


