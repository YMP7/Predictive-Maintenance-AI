"""
Tests for TimescaleDB integration layer.

These tests run against the real database (not mocks) to catch actual SQL errors.
Requires: TimescaleDB running, migration applied, seed_dev.py run.
"""
import pytest
from unittest.mock import patch
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()


def test_database_url_required():
    """App must crash if DATABASE_URL is unset."""
    with patch.dict('os.environ', {}, clear=True):
        import sys
        if 'server.database' in sys.modules:
            del sys.modules['server.database']
            
        with pytest.raises(RuntimeError) as exc_info:
            import server.database
            
        assert "FATAL: DATABASE_URL environment variable is not set" in str(exc_info.value)


def test_user_lookup_existing():
    """Verify get_user_from_db returns a valid user dict for a seeded account."""
    from server.backend_api import get_user_from_db
    
    user = get_user_from_db("test_admin")
    assert user is not None
    assert user["username"] == "test_admin"
    assert user["role"] == "admin"
    assert user["hashed_password"].startswith("$2b$")


def test_user_lookup_nonexistent():
    """Verify get_user_from_db returns None for unknown users."""
    from server.backend_api import get_user_from_db
    
    user = get_user_from_db("nonexistent_user_xyz")
    assert user is None


def test_user_lookup_all_seeded_accounts():
    """Verify all 5 seeded accounts exist with correct roles."""
    from server.backend_api import get_user_from_db
    
    expected = {
        "admin": "admin",
        "operator": "operator",
        "test_admin": "admin",
        "test_operator": "operator",
        "demo_viewer": "viewer",
    }
    for username, expected_role in expected.items():
        user = get_user_from_db(username)
        assert user is not None, f"User {username} not found in database"
        assert user["role"] == expected_role, f"User {username} has role {user['role']}, expected {expected_role}"


def test_telemetry_insert_and_read():
    """Insert a telemetry reading and verify it's queryable."""
    from server.database import pool
    from datetime import datetime, timezone

    test_time = datetime.now(timezone.utc)
    
    with pool.connection() as conn:
        # Insert
        conn.execute("""
            INSERT INTO telemetry (time, machine_id, vibration_x, vibration_y,
                vibration_z, vibration_rms, temperature, current_val, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (test_time, "TEST1", 0.1, 0.2, 0.3, 0.4, 55.0, 3.2, "Normal"))
        conn.commit()
        
        # Read back
        row = conn.execute("""
            SELECT machine_id, temperature, current_val, status
            FROM telemetry
            WHERE machine_id = 'TEST1' AND time = %s
        """, (test_time,)).fetchone()
        
        assert row is not None, "Inserted telemetry row not found"
        assert row[0] == "TEST1"
        assert row[1] == 55.0
        assert row[2] == 3.2
        assert row[3] == "Normal"
        
        # Cleanup
        conn.execute("DELETE FROM telemetry WHERE machine_id = 'TEST1'")
        conn.commit()


def test_alert_insert_and_read():
    """Insert an alert and verify it's queryable."""
    from server.database import pool

    test_time = datetime.now(timezone.utc)
    
    with pool.connection() as conn:
        conn.execute("""
            INSERT INTO alerts (time, machine_id, type, severity, message, fault_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (test_time, "TEST1", "RUL", "Critical", "Test alert", "bearing_wear"))
        conn.commit()
        
        row = conn.execute("""
            SELECT machine_id, severity, message
            FROM alerts
            WHERE machine_id = 'TEST1' AND time = %s
        """, (test_time,)).fetchone()
        
        assert row is not None, "Inserted alert row not found"
        assert row[0] == "TEST1"
        assert row[1] == "Critical"
        assert row[2] == "Test alert"
        
        # Cleanup
        conn.execute("DELETE FROM alerts WHERE machine_id = 'TEST1'")
        conn.commit()
