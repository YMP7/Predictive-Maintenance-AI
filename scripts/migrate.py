"""
Schema migration script for TimescaleDB.

Creates the users, telemetry (hypertable), and alerts (hypertable) tables.
Safe to run multiple times — all statements use IF NOT EXISTS.

Usage:
    python scripts/migrate.py
"""
import os
import sys

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import psycopg

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL is not set. Cannot run migration.")
        sys.exit(1)

    print(f"Connecting to database...")
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 1. Users table
            print("Creating users table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id          SERIAL PRIMARY KEY,
                    username    VARCHAR(100) UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role        VARCHAR(20) NOT NULL DEFAULT 'viewer',
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            # 2. Telemetry hypertable
            print("Creating telemetry table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    time          TIMESTAMPTZ NOT NULL,
                    machine_id    VARCHAR(10) NOT NULL,
                    vibration_x   DOUBLE PRECISION,
                    vibration_y   DOUBLE PRECISION,
                    vibration_z   DOUBLE PRECISION,
                    vibration_rms DOUBLE PRECISION,
                    temperature   DOUBLE PRECISION,
                    current_val   DOUBLE PRECISION,
                    status        VARCHAR(20)
                );
            """)
            print("Converting telemetry to hypertable...")
            cur.execute("""
                SELECT create_hypertable('telemetry', 'time', if_not_exists => TRUE);
            """)

            # 3. Alerts hypertable (ready for Phase 5)
            print("Creating alerts table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id           SERIAL,
                    time         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    machine_id   VARCHAR(10) NOT NULL,
                    type         VARCHAR(50),
                    severity     VARCHAR(20),
                    message      TEXT,
                    fault_type   VARCHAR(50),
                    acknowledged BOOLEAN NOT NULL DEFAULT FALSE
                );
            """)
            print("Converting alerts to hypertable...")
            cur.execute("""
                SELECT create_hypertable('alerts', 'time', if_not_exists => TRUE);
            """)

            # Phase 8 (Safeguards Fix): Add provenance source to alerts
            print("Adding source column to alerts table...")
            cur.execute("""
                ALTER TABLE alerts ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'unknown';
            """)
            cur.execute("""
                UPDATE alerts SET source = 'ai_pipeline' WHERE source = 'unknown' OR source IS NULL;
            """)

            # 4. Notifications sent hypertable (Phase 5 — debounce tracking)
            print("Creating notifications_sent table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notifications_sent (
                    id           SERIAL,
                    time         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    machine_id   VARCHAR(10) NOT NULL,
                    fault_type   VARCHAR(50) NOT NULL,
                    channel      VARCHAR(20) NOT NULL,
                    recipient    TEXT NOT NULL,
                    severity     VARCHAR(20),
                    message      TEXT
                );
            """)
            print("Converting notifications_sent to hypertable...")
            cur.execute("""
                SELECT create_hypertable('notifications_sent', 'time', if_not_exists => TRUE);
            """)

            # 5. Add email/phone columns to users table for recipient fan-out
            print("Adding email/phone columns to users table...")
            cur.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;
            """)
            cur.execute("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT;
            """)

            # 6. Create indexes for common query patterns
            print("Creating indexes...")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_telemetry_machine_time
                ON telemetry (machine_id, time DESC);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_machine_time
                ON alerts (machine_id, time DESC);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_notif_machine_fault_time
                ON notifications_sent (machine_id, fault_type, time DESC);
            """)

            # 7. Phase 8: agent_memory table (persistent LLM agent reasoning history)
            print("Creating agent_memory table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    memory_id    UUID PRIMARY KEY,
                    machine_id   VARCHAR(10) NOT NULL,
                    timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    user_message TEXT,
                    agent_response TEXT,
                    summary      TEXT,
                    tools_used   TEXT,
                    triggered_by VARCHAR(100)
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_memory_machine_time
                ON agent_memory (machine_id, timestamp DESC);
            """)

            # 8. Phase 8: work_orders table (autonomous maintenance scheduling)
            print("Creating work_orders table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS work_orders (
                    order_id     UUID PRIMARY KEY,
                    machine_id   VARCHAR(10) NOT NULL,
                    action       TEXT NOT NULL,
                    urgency      VARCHAR(20) NOT NULL DEFAULT 'Medium',
                    status       VARCHAR(20) NOT NULL DEFAULT 'Open',
                    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    resolved_at  TIMESTAMPTZ,
                    notes        TEXT,
                    created_by   VARCHAR(100) DEFAULT 'agent'
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_work_orders_machine
                ON work_orders (machine_id, created_at DESC);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_work_orders_status
                ON work_orders (status, urgency);
            """)

            # 9. Phase 8 (Safeguards): work_order_audit_log table
            print("Creating work_order_audit_log table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS work_order_audit_log (
                    id                 UUID PRIMARY KEY,
                    timestamp          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    machine_id         VARCHAR(10) NOT NULL,
                    action             TEXT NOT NULL,
                    urgency            VARCHAR(20) NOT NULL,
                    justification      TEXT,
                    validation_result  VARCHAR(50) NOT NULL,
                    real_data_snapshot TEXT
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_work_order_audit_machine_time
                ON work_order_audit_log (machine_id, timestamp DESC);
            """)

        conn.commit()
    print("Migration complete.")

if __name__ == "__main__":
    main()
