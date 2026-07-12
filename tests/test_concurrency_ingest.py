"""
tests/test_concurrency_ingest.py

Phase 7 carry-over: Concurrency ingest test.

Sends real ISO-8601 string timestamps (matching sensor_simulator.py output format)
from multiple threads to DataService.ingest_telemetry() and validates:
1. Thread safety — no crashes under concurrent writes
2. Correct in-memory cache counts after all threads complete
3. Zero errors in all threads
"""
import sys
import threading
import time
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest


# Number of concurrent threads and payloads per thread
NUM_THREADS = 6
PAYLOADS_PER_THREAD = 10


def _make_iso_payload(machine_id: str, seq: int) -> dict:
    """Create a payload matching real sensor_simulator.py output format."""
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "machine_id": machine_id,
        "timestamp": ts,  # Real ISO-8601 string, not a float
        "vibration": {
            "x": 0.3 + seq * 0.01,
            "y": 0.4 + seq * 0.01,
            "z": 0.2 + seq * 0.01,
            "rms": 0.5 + seq * 0.02,
        },
        "temperature": 45.0 + seq * 0.1,
        "current": 2.4 + seq * 0.01,
    }


@pytest.fixture(autouse=True)
def _mock_database(monkeypatch):
    """Mock server.database before DataService is imported."""
    mock_db = MagicMock()
    mock_pool = MagicMock()
    mock_db.pool = mock_pool

    mock_conn = MagicMock()
    mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.fetchall.return_value = []

    monkeypatch.setitem(sys.modules, "server.database", mock_db)

    # Clear cached imports so they re-import with the mock
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("server.") and mod_name != "server.database":
            if mod_name in sys.modules:
                del sys.modules[mod_name]

    yield mock_conn


def test_concurrent_ingest_thread_safety(_mock_database):
    """
    Sends PAYLOADS_PER_THREAD payloads from each of NUM_THREADS threads
    concurrently into DataService.ingest_telemetry().
    Verifies zero errors, correct cache counts, and no deadlocks.
    """
    # Now import after mock is in place
    from server.data_service import DataService

    # Patch the MQTT client to avoid connection attempts
    with patch("server.data_service.MQTTClientManager"):
        service = DataService()

    machines = ["M001", "M002", "M003", "M004"]
    errors = []
    payloads_sent = {"count": 0}
    count_lock = threading.Lock()

    def _worker(thread_id: int):
        machine_id = machines[thread_id % len(machines)]
        for seq in range(PAYLOADS_PER_THREAD):
            payload = _make_iso_payload(machine_id, seq)
            try:
                service.ingest_telemetry(machine_id, payload)
                with count_lock:
                    payloads_sent["count"] += 1
            except Exception as e:
                errors.append((thread_id, seq, str(e)))

    # Record cache state before
    before_counts = {
        mid: len(service.telemetry_cache.get(mid, []))
        for mid in machines
    }

    # Launch threads
    threads = []
    for tid in range(NUM_THREADS):
        t = threading.Thread(target=_worker, args=(tid,), name=f"ingest-{tid}")
        threads.append(t)

    start_time = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    elapsed = time.time() - start_time

    # Record cache state after
    after_counts = {
        mid: len(service.telemetry_cache.get(mid, []))
        for mid in machines
    }

    # ---- Assertions ----

    # 1. Zero errors
    assert len(errors) == 0, f"Errors during concurrent ingest: {errors}"

    # 2. All payloads were sent
    total_expected = NUM_THREADS * PAYLOADS_PER_THREAD
    assert payloads_sent["count"] == total_expected, (
        f"Expected {total_expected} payloads, got {payloads_sent['count']}"
    )

    # 3. Total cache entries increased by exactly total_expected
    total_before = sum(before_counts.values())
    total_after = sum(after_counts.values())
    assert total_after - total_before == total_expected, (
        f"Cache growth mismatch: before={total_before}, after={total_after}, "
        f"expected growth={total_expected}"
    )

    # 4. Completed in reasonable time (no deadlock)
    assert elapsed < 30.0, f"Ingest took {elapsed:.1f}s — possible deadlock"

    # 5. No threads left alive
    for t in threads:
        assert not t.is_alive(), f"Thread {t.name} still alive after join"


def test_iso8601_timestamp_format():
    """Verify payloads use ISO-8601 string timestamps, not floats."""
    payload = _make_iso_payload("M001", 0)
    ts = payload["timestamp"]

    # Must be a string
    assert isinstance(ts, str), f"Timestamp should be string, got {type(ts)}"

    # Must end with 'Z' (UTC)
    assert ts.endswith("Z"), f"Timestamp should end with Z, got: {ts}"

    # Must be parseable as ISO-8601
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None, "Parsed timestamp should be timezone-aware"
