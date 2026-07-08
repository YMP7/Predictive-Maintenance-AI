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

            # 4. Create indexes for common query patterns
            print("Creating indexes...")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_telemetry_machine_time
                ON telemetry (machine_id, time DESC);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_machine_time
                ON alerts (machine_id, time DESC);
            """)

        conn.commit()
    print("Migration complete.")

if __name__ == "__main__":
    main()
