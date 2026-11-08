"""
Ingestion service (D3): every transport (HTTP, WebSocket, MQTT, CSV, manual entry) calls
IngestService.ingest(). Channel mapping and validation happen in the Adapter Layer
(server/adapters/configurable_adapter.py); this module only authenticates devices, rate-limits,
stores rows, publishes them to live subscribers and records one audit event per batch.

Device tokens are random 256-bit strings shown once; only their SHA-256 is stored, which is safe
for high-entropy secrets (no salt or slow hash needed) and allows an indexed lookup.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import threading
import time
import uuid
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from server.adapters.configurable_adapter import DEFAULT_MAX_AGE_S, ConfigurableAdapter, SensorProfile
from server.audit import audit


class IngestError(Exception):
    status = 400


class IngestAuthError(IngestError):
    status = 401


class IngestForbidden(IngestError):
    status = 403


class UnknownMachine(IngestError):
    status = 404


class IngestRateLimited(IngestError):
    status = 429


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- stores


class MemoryProfileStore:
    def __init__(self):
        self.profiles: Dict[str, SensorProfile] = {}

    def get(self, machine_id: str) -> Optional[SensorProfile]:
        return self.profiles.get(machine_id)

    def put(self, profile: SensorProfile, actor: str) -> Tuple[Optional[dict], dict]:
        before = self.profiles.get(profile.machine_id)
        self.profiles[profile.machine_id] = profile
        return (before.model_dump() if before else None), profile.model_dump()

    def list(self) -> List[SensorProfile]:
        return list(self.profiles.values())


class DbProfileStore:
    def _pool(self):
        from server.database import pool
        return pool

    def get(self, machine_id: str) -> Optional[SensorProfile]:
        with self._pool().connection() as conn:
            row = conn.execute("SELECT profile FROM sensor_profiles WHERE machine_id = %s", (machine_id,)).fetchone()
        return SensorProfile(**row[0]) if row else None

    def put(self, profile: SensorProfile, actor: str) -> Tuple[Optional[dict], dict]:
        before = self.get(profile.machine_id)
        after = profile.model_dump()
        with self._pool().connection() as conn:
            conn.execute(
                "INSERT INTO sensor_profiles (machine_id, domain, profile, updated_by) VALUES (%s, %s, %s::jsonb, %s) "
                "ON CONFLICT (machine_id) DO UPDATE SET domain = EXCLUDED.domain, profile = EXCLUDED.profile, "
                "version = sensor_profiles.version + 1, updated_at = now(), updated_by = EXCLUDED.updated_by",
                (profile.machine_id, profile.domain, json.dumps(after), actor),
            )
        return (before.model_dump() if before else None), after

    def list(self) -> List[SensorProfile]:
        with self._pool().connection() as conn:
            rows = conn.execute("SELECT profile FROM sensor_profiles ORDER BY machine_id").fetchall()
        return [SensorProfile(**r[0]) for r in rows]


_PUBLIC_DEVICE_FIELDS = ("device_id", "machine_id", "protocol", "created_at", "rotated_at", "revoked_at",
                         "last_seen", "msg_count", "err_count")


def _new_token() -> str:
    return "atl_" + secrets.token_urlsafe(32)


class MemoryDeviceStore:
    def __init__(self):
        self.rows: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, machine_id: str, protocol: str) -> Tuple[str, str]:
        device_id, token = "dev_" + secrets.token_hex(6), _new_token()
        with self._lock:
            self.rows[device_id] = {"device_id": device_id, "machine_id": machine_id, "protocol": protocol,
                                    "token_hash": hash_token(token), "created_at": _now(), "rotated_at": None,
                                    "revoked_at": None, "last_seen": None, "msg_count": 0, "err_count": 0}
        return device_id, token

    def verify(self, token: str) -> Optional[Dict[str, Any]]:
        h = hash_token(token)
        with self._lock:
            for row in self.rows.values():
                if secrets.compare_digest(row["token_hash"], h) and row["revoked_at"] is None:
                    return {k: row[k] for k in _PUBLIC_DEVICE_FIELDS}
        return None

    def rotate(self, device_id: str) -> Optional[str]:
        token = _new_token()
        with self._lock:
            row = self.rows.get(device_id)
            if not row or row["revoked_at"]:
                return None
            row.update(token_hash=hash_token(token), rotated_at=_now())
        return token

    def revoke(self, device_id: str) -> bool:
        with self._lock:
            row = self.rows.get(device_id)
            if not row or row["revoked_at"]:
                return False
            row["revoked_at"] = _now()
            return True

    def touch(self, device_id: str, ok: bool) -> None:
        with self._lock:
            row = self.rows.get(device_id)
            if row:
                row["last_seen"] = _now()
                row["msg_count" if ok else "err_count"] += 1

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{k: r[k] for k in _PUBLIC_DEVICE_FIELDS} for r in self.rows.values()]


class DbDeviceStore:
    def _pool(self):
        from server.database import pool
        return pool

    def create(self, machine_id: str, protocol: str) -> Tuple[str, str]:
        device_id, token = "dev_" + secrets.token_hex(6), _new_token()
        with self._pool().connection() as conn:
            conn.execute("INSERT INTO devices (device_id, machine_id, protocol, token_hash) VALUES (%s, %s, %s, %s)",
                         (device_id, machine_id, protocol, hash_token(token)))
        return device_id, token

    def verify(self, token: str) -> Optional[Dict[str, Any]]:
        cols = ", ".join(_PUBLIC_DEVICE_FIELDS)
        with self._pool().connection() as conn:
            row = conn.execute(f"SELECT {cols} FROM devices WHERE token_hash = %s AND revoked_at IS NULL",
                               (hash_token(token),)).fetchone()
        return dict(zip(_PUBLIC_DEVICE_FIELDS, row)) if row else None

    def rotate(self, device_id: str) -> Optional[str]:
        token = _new_token()
        with self._pool().connection() as conn:
            row = conn.execute("UPDATE devices SET token_hash = %s, rotated_at = now() WHERE device_id = %s "
                               "AND revoked_at IS NULL RETURNING device_id", (hash_token(token), device_id)).fetchone()
        return token if row else None

    def revoke(self, device_id: str) -> bool:
        with self._pool().connection() as conn:
            row = conn.execute("UPDATE devices SET revoked_at = now() WHERE device_id = %s AND revoked_at IS NULL "
                               "RETURNING device_id", (device_id,)).fetchone()
        return row is not None

    def touch(self, device_id: str, ok: bool) -> None:
        col = "msg_count" if ok else "err_count"
        with self._pool().connection() as conn:
            conn.execute(f"UPDATE devices SET last_seen = now(), {col} = {col} + 1 WHERE device_id = %s", (device_id,))

    def list(self) -> List[Dict[str, Any]]:
        cols = ", ".join(_PUBLIC_DEVICE_FIELDS)
        with self._pool().connection() as conn:
            rows = conn.execute(f"SELECT {cols} FROM devices ORDER BY created_at").fetchall()
        return [dict(zip(_PUBLIC_DEVICE_FIELDS, r)) for r in rows]


class MemoryReadingStore:
    def __init__(self):
        self.rows: List[Dict[str, Any]] = []

    def write(self, rows: List[Dict[str, Any]]) -> None:
        self.rows.extend(rows)


class DbReadingStore:
    def write(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        from server.database import pool
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO sensor_readings (time, machine_id, channel, value, unit, quality, batch_id, source) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    [(r["time"], r["machine_id"], r["channel"], r["value"], r["unit"], r["quality"], r["batch_id"],
                      r["source"]) for r in rows],
                )


# ---------------------------------------------------------------- rate limit and live fan-out


class TokenBucket:
    """Per-key token bucket: `rate` tokens per second, at most `burst` stored."""

    def __init__(self, rate: float, burst: float):
        self.rate, self.burst = rate, burst
        self._state: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            tokens, last = self._state.get(key, (self.burst, now))
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            ok = tokens >= 1.0
            self._state[key] = (tokens - 1.0 if ok else tokens, now)
            return ok


class Broker:
    """In-process pub/sub from ingest threads to SSE subscribers (asyncio queues).
    shortcut: single process only; use Redis or Postgres LISTEN/NOTIFY with several workers."""

    def __init__(self, maxsize: int = 200):
        self._subs: Dict[str, List[Tuple[asyncio.AbstractEventLoop, asyncio.Queue]]] = defaultdict(list)
        self._lock = threading.Lock()
        self._maxsize = maxsize

    def subscribe(self, machine_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self._maxsize)
        with self._lock:
            self._subs[machine_id].append((asyncio.get_running_loop(), q))
        return q

    def unsubscribe(self, machine_id: str, q: asyncio.Queue) -> None:
        with self._lock:
            self._subs[machine_id] = [(lp, x) for lp, x in self._subs[machine_id] if x is not q]

    def publish(self, machine_id: str, event: Dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subs.get(machine_id, []))
        for loop, q in subs:
            try:
                loop.call_soon_threadsafe(_offer, q, event)
            except RuntimeError:  # loop already closed
                self.unsubscribe(machine_id, q)

    def subscriber_count(self, machine_id: str) -> int:
        with self._lock:
            return len(self._subs.get(machine_id, []))


def _offer(q: asyncio.Queue, event: Dict[str, Any]) -> None:
    try:
        q.put_nowait(event)
    except asyncio.QueueFull:  # a slow client loses the oldest-pending updates, never blocks ingest
        pass


async def sse_events(request: Any, broker: Broker, machine_id: str, *, heartbeat_s: float = 15.0,
                     snapshot: Optional[Callable[[], Optional[Dict[str, Any]]]] = None):
    """Server-sent events: readings as they arrive, a heartbeat (plus a snapshot, if given) when quiet.
    The browser's EventSource reconnects on its own after `retry` ms."""
    q = broker.subscribe(machine_id)
    try:
        yield "retry: 3000\n\n"
        while not await request.is_disconnected():
            try:
                event = await asyncio.wait_for(q.get(), timeout=heartbeat_s)
                yield f"event: {event.get('kind', 'reading')}\ndata: {json.dumps(event, default=str)}\n\n"
            except asyncio.TimeoutError:
                yield f"event: heartbeat\ndata: {json.dumps({'ts': _now().isoformat()})}\n\n"
                snap = snapshot() if snapshot else None
                if snap:
                    yield f"event: snapshot\ndata: {json.dumps(snap, default=str)}\n\n"
    finally:
        broker.unsubscribe(machine_id, q)


# ---------------------------------------------------------------- service


class IngestService:
    def __init__(self, profiles, devices, readings, broker: Broker, rate_per_s: float = 10.0, burst: float = 20.0):
        self.profiles, self.devices, self.readings, self.broker = profiles, devices, readings, broker
        self.bucket = TokenBucket(rate_per_s, burst)
        self._adapters: Dict[str, ConfigurableAdapter] = {}
        self._missing: Dict[str, float] = {}
        self._recent: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=10000))
        self._lock = threading.Lock()

    # ---- profiles and adapters
    def adapter(self, machine_id: str) -> ConfigurableAdapter:
        with self._lock:
            a = self._adapters.get(machine_id)
        if a is not None:
            return a
        profile = self.profiles.get(machine_id)
        if profile is None:
            raise UnknownMachine(f"No sensor profile for machine '{machine_id}'")
        a = ConfigurableAdapter(profile)
        a.connect()
        with self._lock:
            return self._adapters.setdefault(machine_id, a)

    def has_profile(self, machine_id: str) -> bool:
        now = time.monotonic()
        with self._lock:
            if machine_id in self._adapters:
                return True
            if self._missing.get(machine_id, 0) > now:  # MQTT asks per message; don't query the DB each time
                return False
        found = self.profiles.get(machine_id) is not None
        if not found:
            with self._lock:
                self._missing[machine_id] = now + 30.0
        return found

    def put_profile(self, profile: SensorProfile, actor: str) -> Tuple[Optional[dict], dict]:
        before, after = self.profiles.put(profile, actor)
        with self._lock:
            self._adapters.pop(profile.machine_id, None)  # rebuilt from the new mapping on next use
            self._missing.pop(profile.machine_id, None)
        return before, after

    def window(self, machine_id: str) -> List[List[float]]:
        return self.adapter(machine_id).window()

    # ---- devices
    def authenticate(self, token: Optional[str], machine_id: str) -> Dict[str, Any]:
        device = self.devices.verify(token) if token else None
        if device is None:
            raise IngestAuthError("Missing, invalid or revoked device token")
        if device["machine_id"] != machine_id:
            self.devices.touch(device["device_id"], ok=False)
            raise IngestForbidden("This token belongs to a different machine")
        if not self.bucket.allow(device["device_id"]):
            self.devices.touch(device["device_id"], ok=False)
            raise IngestRateLimited("Rate limit exceeded for this device")
        return device

    def device_health(self) -> List[Dict[str, Any]]:
        cutoff = time.monotonic() - 60
        out = []
        for d in self.devices.list():
            recent = self._recent.get(d["device_id"], ())
            total = (d.get("msg_count") or 0) + (d.get("err_count") or 0)
            out.append({**d, "messages_per_min": sum(1 for t in recent if t >= cutoff),
                        "error_rate": round((d.get("err_count") or 0) / total, 4) if total else 0.0,
                        "quality": self.adapter(d["machine_id"]).channel_quality() if self.has_profile(d["machine_id"]) else {}})
        return out

    # ---- the one ingest path
    def ingest(self, machine_id: str, samples: List[Any], *, source: str, actor: str, actor_type: str = "device",
               device_id: Optional[str] = None, max_age_s: Optional[float] = DEFAULT_MAX_AGE_S,
               dry_run: bool = False) -> Dict[str, Any]:
        live = self.adapter(machine_id)
        # A dry run validates against a fresh copy so it never changes live state.
        adapter = ConfigurableAdapter(live.profile) if dry_run else live
        if dry_run:
            adapter.connect()
        started = time.perf_counter()
        result = adapter.ingest(samples, max_age_s=max_age_s)
        batch_id = str(uuid.uuid4())
        rows = [{"time": r["ts"], "machine_id": machine_id, "channel": r["channel"], "value": r["value"],
                 "unit": r["unit"], "quality": r["quality"], "batch_id": batch_id, "source": source} for r in result.rows]
        if not dry_run:
            self.readings.write(rows)
            if device_id:
                self.devices.touch(device_id, ok=bool(rows))
                self._recent[device_id].append(time.monotonic())
            if rows:
                reading = adapter.get_reading(machine_id)
                self.broker.publish(machine_id, {
                    "kind": "reading", "machine_id": machine_id, "ts": reading.timestamp, "source": source,
                    "health_index": reading.health_index, "quality": reading.metadata["quality"],
                    "channels": {r["channel"]: {"value": r["value"], "unit": r["unit"], "quality": r["quality"]}
                                 for r in rows},
                })
        reasons = Counter(r.reason for r in result.rejects)
        times = [r["time"] for r in rows]
        summary = {
            "batch_id": batch_id, "machine_id": machine_id, "source": source, "dry_run": dry_run,
            "samples": len(samples), "accepted_samples": result.accepted_samples, "accepted_points": len(rows),
            "rejected": len(result.rejects), "rejects": [r.to_dict() for r in result.rejects[:100]],
            "quality_counts": dict(Counter(r["quality"] for r in rows)),
            "time_range": [min(times).isoformat(), max(times).isoformat()] if times else None,
        }
        audit(category="ingest", action=f"{source}.{'dry_run' if dry_run else 'batch'}", actor=actor,
              actor_type=actor_type, target=machine_id,
              outcome="success" if not result.rejects else ("partial" if rows else "rejected"),
              latency_ms=(time.perf_counter() - started) * 1000,
              # References the batch; raw sensor data stays in sensor_readings.
              details={"batch_id": batch_id, "source": source, "device_id": device_id, "samples": len(samples),
                       "accepted_samples": result.accepted_samples, "accepted_points": len(rows),
                       "rejected": len(result.rejects), "reject_reasons": dict(reasons), "dry_run": dry_run})
        return summary


_SERVICE: Optional[IngestService] = None
_SERVICE_LOCK = threading.Lock()


def get_ingest_service() -> IngestService:
    global _SERVICE
    with _SERVICE_LOCK:
        if _SERVICE is None:
            import os
            _SERVICE = IngestService(DbProfileStore(), DbDeviceStore(), DbReadingStore(), Broker(),
                                     rate_per_s=float(os.environ.get("INGEST_RATE_PER_S", 10)),
                                     burst=float(os.environ.get("INGEST_BURST", 20)))
        return _SERVICE


def set_ingest_service(service: Optional[IngestService]) -> None:
    """Tests swap in memory stores."""
    global _SERVICE
    with _SERVICE_LOCK:
        _SERVICE = service
