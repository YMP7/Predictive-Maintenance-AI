"""
Database connection pool for TimescaleDB.

Follows the same fail-loudly pattern as JWT_SECRET_KEY and MQTT credentials:
the app crashes on import if DATABASE_URL is not set.
"""
import os
import logging
from psycopg_pool import ConnectionPool

logger = logging.getLogger("DigitalTwin")

_db_url = os.environ.get("DATABASE_URL")
if not _db_url:
    raise RuntimeError(
        "FATAL: DATABASE_URL environment variable is not set. "
        "Set it in your .env file, e.g.: "
        "DATABASE_URL=postgresql://dtwin:secret@localhost:5432/digital_twin"
    )

pool = ConnectionPool(conninfo=_db_url, min_size=2, max_size=10)

logger.info("Database connection pool initialized.")
