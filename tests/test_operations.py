"""P4 operations: ISA-18.2 alarm acknowledge/shelve/clear, the work-order lifecycle, users and roles.

Runs against the local TimescaleDB like the other DB tests. Rows it creates use machine id `T_P4` and
users `t_p4_*`, and are removed afterwards (alerts and work orders are not part of the immutable audit table).
"""

import pytest
from fastapi.testclient import TestClient

from server import audit as A
from server.auth import User, get_current_user
from server.backend_api import app
from server.database import pool
from server.operations_api import next_alarm_state

H = {"X-API-Request": "true"}
M = "T_P4"


@pytest.fixture(scope="module", autouse=True)
def migrated():
    from scripts.migrate_platform import migrate
    migrate()
    yield
    with pool.connection() as conn:
        conn.execute("DELETE FROM alerts WHERE machine_id = %s", (M,))
        conn.execute("DELETE FROM work_orders WHERE machine_id LIKE %s", (M + "%",))
        conn.execute("DELETE FROM work_order_audit_log WHERE machine_id LIKE %s", (M + "%",))
        conn.execute("DELETE FROM users WHERE username LIKE 't_p4_%%'")
        conn.commit()


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def as_role(role, name=None):
    app.dependency_overrides[get_current_user] = lambda: User(username=name or f"t_p4_{role}", role=role)


@pytest.fixture
def events(monkeypatch):
    seen = []
    real = A.audit

    def spy(**kw):
        seen.append(kw)
        return real(**kw)

    monkeypatch.setattr(A, "audit", spy)
    return seen


def raise_alarm(severity="High", message="Bearing temperature high"):
    with pool.connection() as conn:
        row = conn.execute(
            "INSERT INTO alerts (time, machine_id, type, severity, message, fault_type, source) "
            "VALUES (NOW(), %s, 'threshold', %s, %s, 'overheating', 'test') RETURNING id",
            (M, severity, message)).fetchone()
        conn.commit()
    return row[0]


def alarm(client, alarm_id):
    rows = client.get(f"/api/alarms?machine_id={M}", headers=H).json()["alarms"]
    return next(a for a in rows if a["id"] == alarm_id)


# ---------------------------------------------------------------- alarm state machine


@pytest.mark.parametrize("action,state,expected", [
    ("ack", "unack", "ack"),
    ("ack", "rtn_unack", "cleared"),
    ("ack", "ack", None),
    ("shelve", "unack", "shelved"),
    ("shelve", "ack", "shelved"),
    ("shelve", "shelved", None),
    ("unshelve", "shelved", "unack"),
    ("unshelve", "ack", None),
    ("clear", "ack", "cleared"),
    ("clear", "unack", None),
    ("clear", "cleared", None),
])
def test_alarm_transitions(action, state, expected):
    assert next_alarm_state(action, state) == expected


def test_alarm_list_shape_and_priority(client):
    as_role("viewer")
    alarm_id = raise_alarm("Critical")
    a = alarm(client, alarm_id)
    assert a["priority"] == "critical" and a["state"] == "unack"
    for key in ("raised_at", "machine_id", "message", "fault_type", "source", "state_by", "state_reason", "shelved_until"):
        assert key in a


def test_acknowledge_then_clear_with_reason_is_audited(client, events):
    as_role("operator")
    alarm_id = raise_alarm()
    res = client.post(f"/api/alarms/{alarm_id}/ack", json={}, headers=H)
    assert res.status_code == 200 and res.json()["state"] == "ack"
    assert alarm(client, alarm_id)["state_by"] == "t_p4_operator"
    # acknowledging twice is a conflict, not a silent success
    assert client.post(f"/api/alarms/{alarm_id}/ack", json={}, headers=H).status_code == 409
    assert client.post(f"/api/alarms/{alarm_id}/clear", json={}, headers=H).status_code == 422
    res = client.post(f"/api/alarms/{alarm_id}/clear", json={"reason": "Bearing greased, temperature back to 61 C"}, headers=H)
    assert res.status_code == 200 and alarm(client, alarm_id)["state"] == "cleared"
    acts = [(e["category"], e["action"]) for e in events if e.get("category") == "alarm"]
    assert ("alarm", "ack") in acts and ("alarm", "clear") in acts
    clear = next(e for e in events if e.get("action") == "clear")
    assert clear["details"]["reason"].startswith("Bearing greased") and clear["details"]["from"] == "ack"


def test_shelve_needs_reason_and_a_time_limit_and_expires(client):
    as_role("operator")
    alarm_id = raise_alarm()
    assert client.post(f"/api/alarms/{alarm_id}/shelve", json={"minutes": 30}, headers=H).status_code == 422
    assert client.post(f"/api/alarms/{alarm_id}/shelve", json={"reason": "Sensor swap", "minutes": 5000}, headers=H).status_code == 422
    res = client.post(f"/api/alarms/{alarm_id}/shelve", json={"reason": "Sensor swap in progress", "minutes": 30}, headers=H)
    assert res.status_code == 200
    a = alarm(client, alarm_id)
    assert a["state"] == "shelved" and a["shelved_until"]
    # an expired shelve returns the alarm to the operator unacknowledged
    with pool.connection() as conn:
        conn.execute("UPDATE alerts SET shelved_until = NOW() - INTERVAL '1 minute' WHERE id = %s", (alarm_id,))
        conn.commit()
    assert alarm(client, alarm_id)["state"] == "unack"


def test_viewer_cannot_change_alarms_and_unknown_alarm_is_404(client):
    alarm_id = raise_alarm()
    as_role("viewer")
    assert client.post(f"/api/alarms/{alarm_id}/ack", json={}, headers=H).status_code == 403
    as_role("operator")
    assert client.post("/api/alarms/999999999/ack", json={}, headers=H).status_code == 404


# ---------------------------------------------------------------- work orders


def create_order(client, **extra):
    body = {"machine_id": f"{M}_unit_17", "domain": "cmapss", "action": "Borescope the HPT stage", "urgency": "High", **extra}
    res = client.post("/api/work-orders", json=body, headers=H)
    assert res.status_code == 201, res.text
    return res.json()


def order(client, order_id):
    rows = client.get(f"/api/work-orders?machine_id={M}_unit_17&limit=200", headers=H).json()["work_orders"]
    return next(o for o in rows if o["order_id"] == order_id)


def test_work_order_full_lifecycle_with_assignment(client, events):
    as_role("operator")
    alarm_id = raise_alarm()
    wo = create_order(client, alarm_id=alarm_id, notes="Raised from the asset page")
    assert wo["status"] == "Pending Approval" and wo["created_by"] == "t_p4_operator"
    oid = wo["order_id"]
    assert client.post(f"/api/work-orders/{oid}/approve", headers=H).status_code == 200
    with pool.connection() as conn:
        conn.execute("INSERT INTO users (username, hashed_password, role) VALUES ('t_p4_tech', 'x', 'operator') "
                     "ON CONFLICT (username) DO NOTHING")
        conn.commit()
    assert client.patch(f"/api/work-orders/{oid}/assign", json={"assignee": "nobody_here"}, headers=H).status_code == 422
    assert client.patch(f"/api/work-orders/{oid}/assign", json={"assignee": "t_p4_tech"}, headers=H).status_code == 200
    assert client.post(f"/api/work-orders/{oid}/start", headers=H).status_code == 200
    assert order(client, oid)["status"] == "In Progress"
    assert client.patch(f"/api/work-orders/{oid}/resolve", headers=H).status_code == 200
    o = order(client, oid)
    assert o["status"] == "Resolved" and o["assignee"] == "t_p4_tech" and o["alarm_id"] == alarm_id and o["domain"] == "cmapss"
    acts = [e["action"] for e in events if e.get("category") == "work_order"]
    assert acts == ["created", "approved", "assign", "started", "resolved"]


def test_reject_needs_reason_and_closes_the_order(client):
    as_role("operator")
    oid = create_order(client)["order_id"]
    assert client.post(f"/api/work-orders/{oid}/reject", json={}, headers=H).status_code == 422
    assert client.post(f"/api/work-orders/{oid}/reject", json={"reason": "Duplicate of an open order"}, headers=H).status_code == 200
    o = order(client, oid)
    assert o["status"] == "Rejected" and "Duplicate" in o["notes"]
    assert client.post(f"/api/work-orders/{oid}/approve", headers=H).status_code == 404


def test_viewer_cannot_create_work_orders_and_bad_input_is_422(client):
    as_role("viewer")
    assert client.post("/api/work-orders", json={"machine_id": M, "action": "x" * 10, "urgency": "High"}, headers=H).status_code == 403
    as_role("operator")
    assert client.post("/api/work-orders", json={"machine_id": "../etc", "action": "Inspect", "urgency": "High"}, headers=H).status_code == 422
    assert client.post("/api/work-orders", json={"machine_id": M, "action": "Inspect", "urgency": "Whenever"}, headers=H).status_code == 422


def test_assignable_users_lists_operators_and_admins_only(client):
    with pool.connection() as conn:
        conn.execute("INSERT INTO users (username, hashed_password, role) VALUES ('t_p4_view', 'x', 'viewer') "
                     "ON CONFLICT (username) DO NOTHING")
        conn.commit()
    as_role("operator")
    users = client.get("/api/users/assignable", headers=H).json()
    assert all(u["role"] in ("operator", "admin") for u in users)
    assert "t_p4_view" not in [u["username"] for u in users]
    as_role("viewer")
    assert client.get("/api/users/assignable", headers=H).status_code == 403


# ---------------------------------------------------------------- users and roles (admin)


def test_admin_lists_users_without_secrets_and_changes_a_role(client, events):
    with pool.connection() as conn:
        conn.execute("INSERT INTO users (username, hashed_password, role) VALUES ('t_p4_role', 'secret-hash', 'viewer') "
                     "ON CONFLICT (username) DO UPDATE SET role = 'viewer'")
        conn.commit()
    as_role("admin", "t_p4_admin")
    users = client.get("/api/admin/users", headers=H).json()
    row = next(u for u in users if u["username"] == "t_p4_role")
    assert row["role"] == "viewer" and "hashed_password" not in row and "secret-hash" not in str(users)
    res = client.patch("/api/admin/users/t_p4_role", json={"role": "operator"}, headers=H)
    assert res.status_code == 200 and res.json()["role"] == "operator"
    change = next(e for e in events if e.get("action") == "user.role")
    assert change["details"] == {"before": {"role": "viewer"}, "after": {"role": "operator"}}
    assert client.patch("/api/admin/users/t_p4_role", json={"role": "superuser"}, headers=H).status_code == 422
    assert client.patch("/api/admin/users/no_such_user_p4", json={"role": "viewer"}, headers=H).status_code == 404


def test_admin_cannot_change_own_role(client):
    as_role("admin", "t_p4_self")
    with pool.connection() as conn:
        conn.execute("INSERT INTO users (username, hashed_password, role) VALUES ('t_p4_self', 'x', 'admin') "
                     "ON CONFLICT (username) DO NOTHING")
        conn.commit()
    assert client.patch("/api/admin/users/t_p4_self", json={"role": "viewer"}, headers=H).status_code == 409


def test_operator_cannot_list_users(client):
    as_role("operator")
    assert client.get("/api/admin/users", headers=H).status_code == 403
