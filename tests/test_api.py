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

    # 1. Unauthenticated request should fail (401 because CSRF header is present, but no token)
    assert client.post(endpoint, json=payload, headers={"X-API-Request": "true"}).status_code == 401

    # 2. Login to get token
    login_resp = client.post("/api/auth/login", json={"username": "test_admin", "password": "test_admin_public_pw_123"})
    assert login_resp.status_code == 200
    token = login_resp.cookies.get("access_token")
    assert token is not None

    # 3. Authenticated request should succeed
    response = client.post(
        endpoint,
        json=payload,
        cookies={"access_token": token},
        headers={"X-API-Request": "true"},
    )
    assert response.status_code == 200
    assert response.json()["fault_mode"] == "normal"


def test_login_rate_limiting():
    """The 6th rapid login attempt within a minute should return 429."""
    from server.backend_api import limiter
    # Reset any existing rate limit state so this test is isolated
    limiter.reset()

    login_payload = {"username": "admin", "password": "wrong_password"}

    # First 5 attempts should succeed (200) or fail auth (401) — not 429
    for i in range(5):
        resp = client.post("/api/auth/login", json=login_payload)
        assert resp.status_code in (200, 401), f"Attempt {i+1} returned {resp.status_code}"

    # 6th attempt should be rate-limited
    resp = client.post("/api/auth/login", json=login_payload)
    assert resp.status_code == 429, f"Expected 429 on 6th attempt, got {resp.status_code}"
    assert "retry-after" in resp.headers.keys() or "Retry-After" in resp.headers.keys(), "Missing Retry-After header on 429"


def test_no_duplicate_password_hashes():
    """Ensure no two accounts share the same password/hash (prevents privilege escalation)."""
    from server.database import pool
    
    with pool.connection() as conn:
        rows = conn.execute("SELECT username, hashed_password FROM users").fetchall()
    
    seen_hashes = set()
    for username, pwd_hash in rows:
        assert pwd_hash not in seen_hashes, f"Duplicate hash found for user {username}! They share a password with another account."
        seen_hashes.add(pwd_hash)


def test_demo_viewer_privilege():
    """Verify demo_viewer can login but gets 403 on privileged endpoints."""
    from server.backend_api import limiter
    limiter.reset()
    
    # 1. Login
    login_resp = client.post("/api/auth/login", json={"username": "demo_viewer", "password": "demo_viewer_public_pw_123"})
    assert login_resp.status_code == 200, "demo_viewer login failed"
    token = login_resp.cookies.get("access_token")
    assert token is not None
    assert login_resp.json()["role"] == "viewer"
    
    # 2. Try privileged action
    endpoint = "/api/machines/M001/fault"
    payload = {"fault_mode": "critical"}
    fault_resp = client.post(
        endpoint,
        json=payload,
        cookies={"access_token": token},
        headers={"X-API-Request": "true"},
    )
    assert fault_resp.status_code == 403, "demo_viewer should be forbidden from fault endpoints"


def test_operator_privilege():
    """Verify operator can control simulation but gets 403 on fault endpoints."""
    # Login as test_operator
    login_resp = client.post("/api/auth/login", json={"username": "test_operator", "password": "test_operator_public_pw_123"})
    assert login_resp.status_code == 200, "test_operator login failed"
    token = login_resp.cookies.get("access_token")
    assert token is not None
    
    # 1. Can operator start simulation? Yes.
    sim_resp = client.post(
        "/api/simulation/start?interval=1.0",
        cookies={"access_token": token},
        headers={"X-API-Request": "true"},
    )
    assert sim_resp.status_code == 200, "Operator should be able to start simulation"
    
    # 2. Can operator inject faults? No.
    fault_resp = client.post(
        "/api/machines/M001/fault",
        json={"fault_mode": "overheating"},
        cookies={"access_token": token},
        headers={"X-API-Request": "true"},
    )
    assert fault_resp.status_code == 403, "Operator should be forbidden from fault injection"

def test_csrf_protection_rejects_missing_header():
    """Verify that requests missing the X-API-Request header are rejected even with a valid cookie."""
    login_resp = client.post("/api/auth/login", json={"username": "test_admin", "password": "test_admin_public_pw_123"})
    token = login_resp.cookies.get("access_token")
    
    # Try to access protected route without X-API-Request header
    response = client.post(
        "/api/machines/M001/fault",
        json={"fault_mode": "normal"},
        cookies={"access_token": token},
        # No X-API-Request header
    )
    assert response.status_code == 403
    assert "Missing CSRF protection header" in response.json()["detail"]

def test_logout_clears_cookies():
    """Verify logout endpoint clears auth cookies."""
    # Start fresh client to test cookie jar behavior
    with TestClient(app) as test_client:
        test_client.post("/api/auth/login", json={"username": "test_admin", "password": "test_admin_public_pw_123"})
        assert "access_token" in test_client.cookies
        assert "auth_status" in test_client.cookies
        
        logout_resp = test_client.post("/api/auth/logout")
        assert logout_resp.status_code == 200
        
        # Check Set-Cookie headers for cleared values (max-age=0 or expires in past, or missing from client jar)
        # TestClient automatically removes cookies if they are expired/deleted by the server
        assert "access_token" not in test_client.cookies
        assert "auth_status" not in test_client.cookies
