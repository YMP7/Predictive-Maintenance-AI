"""
Development-only seed script for user accounts.

Seeds the 5 known accounts (admin, operator, test_admin, test_operator, demo_viewer)
into the users table. This script is NEVER invoked by the application itself —
it is a standalone CLI tool for local development and CI.

Gating: Refuses to run if APP_ENV == "production".

Usage:
    python scripts/seed_dev.py
"""
import os
import sys

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

# --- Gating logic: refuse to run in production ---
APP_ENV = os.environ.get("APP_ENV", "development")
if APP_ENV == "production":
    print("ERROR: seed_dev.py must NOT be run in production (APP_ENV=production). Aborting.")
    sys.exit(1)

import psycopg
from server.auth import get_password_hash

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL is not set. Cannot seed users.")
        sys.exit(1)

    admin_hash = os.environ.get("ADMIN_PASSWORD_HASH")
    operator_hash = os.environ.get("OPERATOR_PASSWORD_HASH")
    if not admin_hash or not operator_hash:
        raise RuntimeError("FATAL: ADMIN_PASSWORD_HASH and OPERATOR_PASSWORD_HASH must be set in .env — no insecure fallback.")

    # These are the same accounts that were in fake_users_db.
    # Passwords for real accounts should be changed after first login.
    # Test/demo account passwords are intentionally public (see SECURITY.md).
    dev_users = [
        # Real accounts (passwords from .env / rotated secrets)
        ("admin",         admin_hash, "admin"),
        ("operator",      operator_hash, "operator"),
        # Test accounts (intentionally public passwords)
        ("test_admin",    get_password_hash("test_admin_public_pw_123"), "admin"),
        ("test_operator", get_password_hash("test_operator_public_pw_123"), "operator"),
        # Demo account (intentionally public password)
        ("demo_viewer",   get_password_hash("demo_viewer_public_pw_123"), "viewer"),
    ]

    print(f"Seeding {len(dev_users)} users into database (APP_ENV={APP_ENV})...")
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            for username, hashed_pw, role in dev_users:
                cur.execute("""
                    INSERT INTO users (username, hashed_password, role)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO UPDATE
                    SET hashed_password = EXCLUDED.hashed_password,
                        role = EXCLUDED.role;
                """, (username, hashed_pw, role))
                print(f"  Seeded user: {username} (role={role})")
        conn.commit()
    print("Seeding complete.")

if __name__ == "__main__":
    main()
