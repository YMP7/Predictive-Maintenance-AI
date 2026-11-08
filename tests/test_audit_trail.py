"""Audit trail (D4): hash chain, tamper detection, redaction, JSONL mirror, DB retry,
request middleware, auth events, client events and DB immutability."""

import json
import logging
import re
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from server import audit as A


def new_log(tmp_path, sink=None):
    return A.AuditLog(jsonl_dir=tmp_path, db_sink=sink, load_tail=False)


def record_n(log, n, **kw):
    for i in range(n):
        log.record(category="test", action=f"step-{i}", actor="tester", actor_type="system", **kw)
    log.flush()


# ---------------------------------------------------------------- chain


def test_canonical_json_ignores_key_order():
    a = {"b": 1, "a": [2, {"d": 1, "c": 2}]}
    b = {"a": [2, {"c": 2, "d": 1}], "b": 1}
    assert A.canonical_json(a) == A.canonical_json(b)


def test_chain_links_each_event_to_the_previous(tmp_path):
    log = new_log(tmp_path)
    record_n(log, 3)
    events = A.read_jsonl(tmp_path)
    assert [e["seq"] for e in events] == [1, 2, 3]
    assert events[0]["prev_hash"] == A.GENESIS_HASH
    assert events[1]["prev_hash"] == events[0]["hash"]
    assert events[2]["prev_hash"] == events[1]["hash"]
    result = A.verify_chain(events)
    assert result.ok, result.problems


def test_edited_event_breaks_the_chain(tmp_path):
    log = new_log(tmp_path)
    record_n(log, 3)
    events = A.read_jsonl(tmp_path)
    events[1]["details"] = {"tampered": True}
    result = A.verify_chain(events)
    assert not result.ok
    assert result.first_bad_seq == 2


def test_deleted_event_breaks_the_chain(tmp_path):
    log = new_log(tmp_path)
    record_n(log, 3)
    events = A.read_jsonl(tmp_path)
    del events[1]
    result = A.verify_chain(events)
    assert not result.ok
    assert result.first_bad_seq == 3


def test_chain_resumes_after_restart(tmp_path):
    first = new_log(tmp_path)
    record_n(first, 2)
    first.close()
    second = A.AuditLog(jsonl_dir=tmp_path, db_sink=None, load_tail=True)
    record_n(second, 1)
    events = A.read_jsonl(tmp_path)
    assert [e["seq"] for e in events] == [1, 2, 3]
    assert A.verify_chain(events).ok


def test_jsonl_file_is_named_by_utc_day(tmp_path):
    log = new_log(tmp_path)
    record_n(log, 1)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert (tmp_path / f"{day}.jsonl").exists()


def test_event_has_the_required_schema(tmp_path):
    log = new_log(tmp_path)
    log.record(category="auth", action="login", actor="alice", actor_type="user", role="admin",
               source_ip="127.0.0.1", target="session", outcome="success", latency_ms=1.5,
               details={"k": 1}, correlation_id="c-1")
    log.flush()
    ev = A.read_jsonl(tmp_path)[0]
    for key in ("event_id", "ts", "correlation_id", "actor", "actor_type", "role", "source_ip", "category",
                "action", "target", "outcome", "latency_ms", "details", "prev_hash", "hash", "seq"):
        assert key in ev, key
    assert ev["ts"].endswith("Z")


def test_db_outage_retries_in_order(tmp_path):
    inserted, failures = [], {"left": 2}

    def flaky_sink(row):
        if failures["left"] > 0:
            failures["left"] -= 1
            raise RuntimeError("database unavailable")
        inserted.append(row["seq"])

    log = new_log(tmp_path, sink=flaky_sink)
    record_n(log, 3)
    log.flush(retry=True)
    assert inserted == [1, 2, 3]
    assert log.pending_count() == 0
    # The mirror kept every event while the database was down.
    assert len(A.read_jsonl(tmp_path)) == 3


# ---------------------------------------------------------------- redaction


def test_redact_hides_secret_keys_and_token_values():
    out = A.redact({
        "password": "hunter2",
        "nested": {"Authorization": "Bearer abc.def"},
        "list": [{"api_key": "k-123"}, {"refresh_token": "r"}],
        "note": "header eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhIn0.c2ln was sent",
        "cmd": "login password=hunter2 user=alice",
        "fine": "pump P-101",
    })
    text = json.dumps(out)
    for secret in ("hunter2", "abc.def", "k-123", "eyJhbGciOiJIUzI1NiJ9"):
        assert secret not in text
    assert out["fine"] == "pump P-101"
    assert "user=alice" in out["cmd"]


def test_recorded_details_are_redacted(tmp_path):
    log = new_log(tmp_path)
    log.record(category="auth", action="login", actor="alice", actor_type="user",
               details={"password": "hunter2", "device_token": "atl_secret"})
    log.flush()
    raw = "".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("*.jsonl"))
    assert "hunter2" not in raw and "atl_secret" not in raw


def test_logging_filter_redacts_messages(caplog):
    logger = logging.getLogger("atlas.test.redaction")
    logger.addFilter(A.RedactingFilter())
    with caplog.at_level(logging.INFO, logger="atlas.test.redaction"):
        logger.info("auth attempt password=%s token=%s", "hunter2", "eyJa1.eyJb2.c3")
    assert "hunter2" not in caplog.text
    assert "eyJa1" not in caplog.text


# ---------------------------------------------------------------- CLI tools


def test_audit_verify_cli_detects_an_edited_line(tmp_path, capsys):
    from scripts.audit_verify import main as verify

    log = new_log(tmp_path)
    record_n(log, 3)
    log.close()
    assert verify(["--source", "jsonl", "--dir", str(tmp_path)]) == 0
    path = next(tmp_path.glob("*.jsonl"))
    lines = path.read_text(encoding="utf-8").splitlines()
    ev = json.loads(lines[1])
    ev["actor"] = "mallory"
    lines[1] = json.dumps(ev)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert verify(["--source", "jsonl", "--dir", str(tmp_path)]) == 1
    assert "first bad seq 2" in capsys.readouterr().out


def test_audit_export_filters_by_category(tmp_path):
    import csv as csv_mod
    from scripts.audit_export import main as export

    log = new_log(tmp_path)
    log.record(category="auth", action="login", actor="a", actor_type="user")
    log.record(category="ingest", action="http.batch", actor="dev_1", actor_type="device")
    log.close()
    out = tmp_path / "out.csv"
    assert export(["--source", "jsonl", "--dir", str(tmp_path), "--category", "ingest", "--format", "csv",
                   "--out", str(out)]) == 0
    rows = list(csv_mod.DictReader(out.open(encoding="utf-8")))
    assert [r["category"] for r in rows] == ["ingest"]


# ---------------------------------------------------------------- API integration


@pytest.fixture
def audit_log(tmp_path, monkeypatch):
    log = new_log(tmp_path)
    monkeypatch.setattr(A, "_LOG", log)
    yield log
    log.close()


@pytest.fixture
def client():
    from server.backend_api import app
    return TestClient(app)


def events_of(log, category):
    log.flush()
    return [e for e in A.read_jsonl(log.jsonl_dir) if e["category"] == category]


def test_api_request_is_audited_with_correlation_id(audit_log, client):
    cid = "0b5c2f9e-3f1a-4c3e-9d2b-7a1e5c6d8f90"
    res = client.get("/api/ready", headers={"X-Correlation-ID": cid})
    assert res.status_code in (200, 503)
    assert res.headers["X-Correlation-ID"] == cid
    ev = [e for e in events_of(audit_log, "api") if e["action"] == "GET /api/ready"][-1]
    assert ev["correlation_id"] == cid
    assert ev["details"]["status"] == res.status_code
    assert ev["latency_ms"] >= 0
    assert ev["actor_type"] in ("user", "anonymous", "device", "system")


def test_unsafe_correlation_id_is_replaced(audit_log, client):
    res = client.get("/api/ready", headers={"X-Correlation-ID": "bad value with spaces"})
    assert re.fullmatch(r"[0-9a-f-]{36}", res.headers["X-Correlation-ID"])


def test_route_template_is_recorded_not_raw_path(audit_log, client, signed_in):
    client.get("/api/dna/cmapss/some_unit", headers={"X-API-Request": "true"})
    actions = [e["action"] for e in events_of(audit_log, "api")]
    assert "GET /api/dna/{domain}/{machine_id}" in actions


def test_failed_login_is_audited_without_the_password(audit_log, client):
    res = client.post("/api/auth/login", json={"username": "nobody_p2_test", "password": "wrong-pass-123"})
    assert res.status_code in (401, 429)
    if res.status_code == 429:
        pytest.skip("login rate limit hit by an earlier test")
    auth = events_of(audit_log, "auth")
    assert any(e["action"] == "login" and e["outcome"] == "failure" and e["actor"] == "nobody_p2_test" for e in auth)
    raw = "".join(p.read_text(encoding="utf-8") for p in audit_log.jsonl_dir.glob("*.jsonl"))
    assert "wrong-pass-123" not in raw


def test_client_events_are_recorded(audit_log, client, signed_in):
    batch = {"events": [
        {"type": "page_view", "path": "/fleet", "ts": "2026-11-08T06:30:00Z"},
        {"type": "command", "name": "Open alarms", "path": "/fleet", "ts": "2026-11-08T06:30:02Z"},
    ]}
    res = client.post("/api/audit/client-events", json=batch, headers={"X-API-Request": "true"})
    assert res.status_code == 202
    actions = [e["action"] for e in events_of(audit_log, "client")]
    assert "page_view" in actions and "command" in actions


def test_client_events_batch_is_bounded(audit_log, client, signed_in):
    batch = {"events": [{"type": "page_view", "path": "/x", "ts": "2026-11-08T06:30:00Z"}] * 201}
    res = client.post("/api/audit/client-events", json=batch, headers={"X-API-Request": "true"})
    assert res.status_code == 422


def test_client_events_need_a_session(audit_log, client):
    res = client.post("/api/audit/client-events", json={"events": []}, headers={"X-API-Request": "true"})
    assert res.status_code == 401


# ---------------------------------------------------------------- database immutability


@pytest.fixture(scope="module")
def migrated():
    try:
        from scripts.migrate_platform import migrate
        migrate()
    except Exception as e:  # no database in this environment
        pytest.skip(f"database unavailable: {e}")


def test_audit_table_blocks_update_and_delete(migrated):
    import psycopg
    from server.database import pool

    with pool.connection() as conn:
        names = {r[0] for r in conn.execute(
            "SELECT tgname FROM pg_trigger WHERE tgrelid = 'audit_events'::regclass AND NOT tgisinternal").fetchall()}
        assert "audit_events_append_only" in names

        # Exercise the same trigger function on a temporary copy so the real chain stays clean.
        with conn.transaction():
            conn.execute("CREATE TEMP TABLE audit_copy (LIKE audit_events) ON COMMIT DROP")
            conn.execute("CREATE TRIGGER copy_append_only BEFORE UPDATE OR DELETE ON audit_copy "
                         "FOR EACH ROW EXECUTE FUNCTION audit_events_block_mutation()")
            conn.execute("INSERT INTO audit_copy (seq, event_id, ts, actor, actor_type, category, action, outcome, "
                         "details, canon, prev_hash, hash) VALUES (1, gen_random_uuid(), now(), 'a', 'system', 't', "
                         "'t', 'success', '{}', '{}', 'p', 'h')")
            with pytest.raises(psycopg.errors.RaiseException):
                with conn.transaction():
                    conn.execute("UPDATE audit_copy SET actor = 'mallory'")
            with pytest.raises(psycopg.errors.RaiseException):
                with conn.transaction():
                    conn.execute("DELETE FROM audit_copy")


def test_app_role_can_append_but_not_change_audit_history(migrated):
    """The API's own database user has SELECT and INSERT only; the owner keeps the rest for migrations."""
    import psycopg
    from server.database import pool
    from scripts.migrate_platform import APP_ROLE

    with pool.connection() as conn:
        privs = conn.execute(
            "SELECT has_table_privilege(%s, 'audit_events', 'INSERT'), has_table_privilege(%s, 'audit_events', 'UPDATE'), "
            "has_table_privilege(%s, 'audit_events', 'DELETE'), has_table_privilege(%s, 'audit_events', 'TRUNCATE'), "
            "has_table_privilege(%s, 'sensor_readings', 'INSERT')",
            (APP_ROLE,) * 5,
        ).fetchone()
        assert privs == (True, False, False, False, True)

        # Prove it with the role itself (no-op statements; the privilege check runs before any row is touched).
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with conn.transaction():
                conn.execute(f'SET LOCAL ROLE "{APP_ROLE}"')
                conn.execute("UPDATE audit_events SET actor = actor WHERE false")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with conn.transaction():
                conn.execute(f'SET LOCAL ROLE "{APP_ROLE}"')
                conn.execute("DELETE FROM audit_events WHERE false")


def test_migration_is_rerunnable(migrated):
    from scripts.migrate_platform import migrate
    migrate()
