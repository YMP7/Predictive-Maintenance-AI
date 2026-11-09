"""
Platform migration (redesign P2): audit trail, sensor ingestion, device tokens, cognition traces,
and the non-owner application role.

Run as the database owner (the role in MIGRATION_DATABASE_URL, else DATABASE_URL). Safe to re-run.

Immutability of audit_events is enforced twice:
  1. a BEFORE UPDATE OR DELETE trigger that raises (also stops the owner by accident), and
  2. the application role `atlas_app`, which the API connects as, has only SELECT and INSERT on it.
     The owner keeps full rights for migrations; the API never uses the owner.

Set ATLAS_APP_DB_PASSWORD to give atlas_app a password (it cannot log in without one), then point
the API's DATABASE_URL at atlas_app (docker-compose does this when the variable is set).

Usage:
    python scripts/migrate_platform.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

import psycopg
from psycopg import sql

APP_ROLE = os.environ.get("ATLAS_APP_DB_USER", "atlas_app")

STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",
    # ---- audit trail
    """
    CREATE TABLE IF NOT EXISTS audit_events (
        seq            BIGINT      NOT NULL,
        event_id       UUID        NOT NULL,
        ts             TIMESTAMPTZ NOT NULL,
        correlation_id TEXT,
        actor          TEXT        NOT NULL,
        actor_type     TEXT        NOT NULL,
        role           TEXT,
        source_ip      TEXT,
        category       TEXT        NOT NULL,
        action         TEXT        NOT NULL,
        target         TEXT,
        outcome        TEXT        NOT NULL,
        latency_ms     DOUBLE PRECISION,
        details        JSONB       NOT NULL DEFAULT '{}',
        canon          TEXT        NOT NULL,
        prev_hash      TEXT        NOT NULL,
        hash           TEXT        NOT NULL,
        PRIMARY KEY (seq, ts)
    )
    """,
    "SELECT create_hypertable('audit_events', 'ts', if_not_exists => TRUE, migrate_data => TRUE)",
    "CREATE INDEX IF NOT EXISTS audit_events_category_ts ON audit_events (category, ts DESC)",
    "CREATE INDEX IF NOT EXISTS audit_events_correlation ON audit_events (correlation_id)",
    """
    CREATE OR REPLACE FUNCTION audit_events_block_mutation() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'audit_events is append-only: % is not allowed', TG_OP;
    END
    $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events",
    """
    CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_block_mutation()
    """,
    # ---- ingestion
    """
    CREATE TABLE IF NOT EXISTS sensor_profiles (
        machine_id  TEXT PRIMARY KEY,
        domain      TEXT        NOT NULL,
        profile     JSONB       NOT NULL,
        version     INTEGER     NOT NULL DEFAULT 1,
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_by  TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS devices (
        device_id   TEXT PRIMARY KEY,
        machine_id  TEXT        NOT NULL,
        protocol    TEXT        NOT NULL,
        token_hash  TEXT        NOT NULL UNIQUE,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        rotated_at  TIMESTAMPTZ,
        revoked_at  TIMESTAMPTZ,
        last_seen   TIMESTAMPTZ,
        msg_count   BIGINT      NOT NULL DEFAULT 0,
        err_count   BIGINT      NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sensor_readings (
        time        TIMESTAMPTZ      NOT NULL,
        machine_id  TEXT             NOT NULL,
        channel     TEXT             NOT NULL,
        value       DOUBLE PRECISION NOT NULL,
        unit        TEXT             NOT NULL,
        quality     TEXT             NOT NULL,
        batch_id    UUID             NOT NULL,
        source      TEXT             NOT NULL
    )
    """,
    "SELECT create_hypertable('sensor_readings', 'time', if_not_exists => TRUE, migrate_data => TRUE)",
    "CREATE INDEX IF NOT EXISTS sensor_readings_machine_time ON sensor_readings (machine_id, channel, time DESC)",
    # ---- cognition traces (replay)
    """
    CREATE TABLE IF NOT EXISTS cognition_traces (
        time        TIMESTAMPTZ NOT NULL,
        domain      TEXT        NOT NULL,
        machine_id  TEXT        NOT NULL,
        trace       JSONB       NOT NULL
    )
    """,
    "SELECT create_hypertable('cognition_traces', 'time', if_not_exists => TRUE, migrate_data => TRUE)",
    "CREATE INDEX IF NOT EXISTS cognition_traces_machine_time ON cognition_traces (domain, machine_id, time DESC)",
    # ---- P4: ISA-18.2 alarm states on the existing alerts table (created by scripts/migrate.py)
    "ALTER TABLE IF EXISTS alerts ADD COLUMN IF NOT EXISTS state VARCHAR(16) NOT NULL DEFAULT 'unack'",
    "ALTER TABLE IF EXISTS alerts ADD COLUMN IF NOT EXISTS state_by VARCHAR(100)",
    "ALTER TABLE IF EXISTS alerts ADD COLUMN IF NOT EXISTS state_at TIMESTAMPTZ",
    "ALTER TABLE IF EXISTS alerts ADD COLUMN IF NOT EXISTS state_reason TEXT",
    "ALTER TABLE IF EXISTS alerts ADD COLUMN IF NOT EXISTS shelved_until TIMESTAMPTZ",
    "DO $$ BEGIN IF to_regclass('alerts') IS NOT NULL THEN "
    "UPDATE alerts SET state = 'ack' WHERE acknowledged AND state = 'unack'; END IF; END $$",
    # ---- P4: work-order lifecycle; domain machine ids (unit_17, device names) exceed 10 characters
    "ALTER TABLE IF EXISTS work_orders ALTER COLUMN machine_id TYPE VARCHAR(64)",
    "ALTER TABLE IF EXISTS work_order_audit_log ALTER COLUMN machine_id TYPE VARCHAR(64)",
    "ALTER TABLE IF EXISTS work_orders ADD COLUMN IF NOT EXISTS assignee VARCHAR(100)",
    "ALTER TABLE IF EXISTS work_orders ADD COLUMN IF NOT EXISTS domain VARCHAR(32)",
    "ALTER TABLE IF EXISTS work_orders ADD COLUMN IF NOT EXISTS alarm_id INTEGER",
    "ALTER TABLE IF EXISTS work_orders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
]


def ensure_app_role(cur, password: str | None) -> None:
    """Create the non-owner API role and give it data rights everywhere except changing audit history."""
    role = sql.Identifier(APP_ROLE)
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (APP_ROLE,))
    if cur.fetchone() is None:
        cur.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT").format(role))
    if password:
        cur.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(role, sql.Literal(password)))
    cur.execute("SELECT current_database()")
    db = cur.fetchone()[0]
    cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(db), role))
    cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
    cur.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}").format(role))
    cur.execute(sql.SQL("GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {}").format(role))
    cur.execute(sql.SQL("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {}").format(role))
    # Tables created by later migrations get the same rights.
    cur.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}").format(role))
    cur.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {}").format(role))
    # The audit trail: read and append only.
    cur.execute(sql.SQL("REVOKE ALL ON audit_events FROM {}").format(role))
    cur.execute(sql.SQL("GRANT SELECT, INSERT ON audit_events TO {}").format(role))
    cur.execute(sql.SQL("REVOKE ALL ON audit_events FROM PUBLIC"))


def migrate(db_url: str | None = None) -> None:
    db_url = db_url or os.environ.get("MIGRATION_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("MIGRATION_DATABASE_URL or DATABASE_URL must be set")
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            for stmt in STATEMENTS:
                cur.execute(stmt)
            ensure_app_role(cur, os.environ.get("ATLAS_APP_DB_PASSWORD") or None)


if __name__ == "__main__":
    migrate()
    print(f"Platform migration complete. API role: {APP_ROLE}"
          + ("" if os.environ.get("ATLAS_APP_DB_PASSWORD") else " (no password set: it cannot log in yet)"))
