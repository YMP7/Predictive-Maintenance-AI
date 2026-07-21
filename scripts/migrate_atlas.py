"""
ATLAS Database Migration Script
================================
Extends the existing TimescaleDB schema with pgvector-backed tables needed
by the ATLAS cognition subsystems (AMKB, Machine DNA, domain snapshots).

Designed to be run AFTER scripts/migrate.py (the existing base migration).
Safe to re-run — all statements use IF NOT EXISTS / CREATE EXTENSION IF NOT EXISTS.

Usage
-----
    python scripts/migrate_atlas.py

Prerequisites
-------------
    The existing TimescaleDB schema must already be initialized:
        python scripts/migrate.py
    The pgvector extension must be available in your TimescaleDB image.
    The timescale/timescaledb:latest-pg16 image includes pgvector.

Tables Created
--------------
    amkb_experiences     -- AMKB vector store (Month 2)
    machine_dna          -- per-unit DNA embeddings (Month 2)
    atlas_domain_snapshots -- per-domain status time-series (Month 1+)
    learning_events      -- retraining audit log (Month 5)
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ATLAS.migrate")


# ---------------------------------------------------------------------------
# Migration SQL
# ---------------------------------------------------------------------------

# Enable pgvector extension
ENABLE_PGVECTOR = """
CREATE EXTENSION IF NOT EXISTS vector;
"""

# AMKB experience store
# embedding dim = 64 (WorldModel hidden_size = state vector dim)
CREATE_AMKB_EXPERIENCES = """
CREATE TABLE IF NOT EXISTS amkb_experiences (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    domain          TEXT        NOT NULL,
    machine_id      TEXT        NOT NULL,
    cycle           INTEGER     NOT NULL DEFAULT 0,
    event_type      TEXT        NOT NULL,   -- 'normal' | 'fault' | 'rul_warning' | 'resolved'
    outcome         TEXT,                   -- 'maintenance_performed' | 'failure' | NULL
    health_index    FLOAT       NOT NULL,
    rul_cycles      FLOAT,
    embedding       vector(32),             -- WorldModel state vector (state_dim=32)
    metadata        JSONB       NOT NULL DEFAULT '{}'
);

-- Index for fast similarity search
CREATE INDEX IF NOT EXISTS amkb_embedding_idx
    ON amkb_experiences USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Index for time-range queries
CREATE INDEX IF NOT EXISTS amkb_domain_machine_idx
    ON amkb_experiences (domain, machine_id, created_at DESC);
"""

# Machine DNA table — per-unit compressed health fingerprint
# DNA embedding dim = 32 (compressed from 64 state vector)
CREATE_MACHINE_DNA = """
CREATE TABLE IF NOT EXISTS machine_dna (
    id              BIGSERIAL PRIMARY KEY,
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    domain          TEXT        NOT NULL,
    machine_id      TEXT        NOT NULL,
    dna_embedding   vector(32)  NOT NULL,   -- 32-dim compressed fingerprint
    components      JSONB       NOT NULL DEFAULT '{}',  -- health/thermal/power/failure components
    n_cycles_used   INTEGER     NOT NULL DEFAULT 0,
    UNIQUE (domain, machine_id)   -- one current DNA per unit (UPSERTED)
);

CREATE INDEX IF NOT EXISTS machine_dna_domain_idx
    ON machine_dna (domain, machine_id);
"""

# Per-domain status snapshots (hypertable for time-series queries)
CREATE_DOMAIN_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS atlas_domain_snapshots (
    time            TIMESTAMPTZ NOT NULL,
    domain          TEXT        NOT NULL,
    machine_id      TEXT        NOT NULL,
    health_index    FLOAT       NOT NULL,
    rul_cycles      FLOAT,
    rul_days        FLOAT,
    confidence      FLOAT,
    uncertainty     FLOAT,
    status          TEXT        NOT NULL,
    using_lstm      BOOLEAN     NOT NULL DEFAULT FALSE,
    decision_action TEXT,
    decision_urgency TEXT,
    metadata        JSONB       NOT NULL DEFAULT '{}'
);
"""

# Convert to hypertable (TimescaleDB)
CREATE_DOMAIN_SNAPSHOTS_HYPERTABLE = """
SELECT create_hypertable(
    'atlas_domain_snapshots', 'time',
    if_not_exists => TRUE,
    migrate_data => TRUE
);
"""

# Indexes for domain snapshot queries
CREATE_DOMAIN_SNAPSHOTS_IDX = """
CREATE INDEX IF NOT EXISTS atlas_snapshots_domain_machine_idx
    ON atlas_domain_snapshots (domain, machine_id, time DESC);
"""

# Learning engine audit log
CREATE_LEARNING_EVENTS = """
CREATE TABLE IF NOT EXISTS learning_events (
    id              BIGSERIAL PRIMARY KEY,
    triggered_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    domain          TEXT        NOT NULL,
    trigger_reason  TEXT        NOT NULL,   -- 'manual' | 'scheduled' | 'outcome_threshold'
    n_samples       INTEGER     NOT NULL DEFAULT 0,
    epochs_run      INTEGER     NOT NULL DEFAULT 0,
    rmse_before     FLOAT,
    rmse_after      FLOAT,
    checkpoint_path TEXT,
    success         BOOLEAN     NOT NULL DEFAULT TRUE,
    notes           TEXT
);
"""


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_migration() -> None:
    from server.database import pool

    steps = [
        ("Enable pgvector extension",               ENABLE_PGVECTOR),
        ("Create amkb_experiences table",            CREATE_AMKB_EXPERIENCES),
        ("Create machine_dna table",                 CREATE_MACHINE_DNA),
        ("Create atlas_domain_snapshots table",      CREATE_DOMAIN_SNAPSHOTS),
        ("Convert snapshots to hypertable",          CREATE_DOMAIN_SNAPSHOTS_HYPERTABLE),
        ("Create snapshots indexes",                 CREATE_DOMAIN_SNAPSHOTS_IDX),
        ("Create learning_events table",             CREATE_LEARNING_EVENTS),
    ]

    with pool.connection() as conn:
        for name, sql in steps:
            try:
                conn.execute(sql)
                conn.commit()
                logger.info(f"  ✓ {name}")
            except Exception as e:
                logger.error(f"  ✗ {name}: {e}")
                raise

    logger.info("\nATLAS database migration complete.")


if __name__ == "__main__":
    logger.info("Running ATLAS database migration...")
    run_migration()
