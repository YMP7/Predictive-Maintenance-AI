"""Append-only, hash-chained audit trail (D4).

Every event is chained: hash = sha256(prev_hash + canonical_json(event)). Events are written
by one writer thread, mirrored to logs/audit/YYYY-MM-DD.jsonl (UTC) first, then inserted into the
`audit_events` table; if the database is down, rows wait in order and are retried.
Secrets are redacted before an event is hashed, so they never reach disk.

shortcut: one writer per process; with several API workers the chain would fork. Run one worker,
or move sequencing into the database, before scaling out.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import logging
import os
import queue
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("DigitalTwin.audit")

GENESIS_HASH = "0" * 64
HASHED_FIELDS = ("seq", "event_id", "ts", "correlation_id", "actor", "actor_type", "role", "source_ip",
                 "category", "action", "target", "outcome", "latency_ms", "details")

correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("atlas_correlation_id", default=None)
current_actor: contextvars.ContextVar[Optional[Dict[str, str]]] = contextvars.ContextVar("atlas_actor", default=None)

# ---------------------------------------------------------------- canonical form and redaction


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


_SECRET_KEY = re.compile(r"(pass(word)?|pwd|secret|token|authorization|cookie|api[_-]?key|jwt|credential|private[_-]?key)", re.I)
_JWT = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+")
_BEARER = re.compile(r"(?i)bearer\s+\S+")
_KV = re.compile(r"(?i)\b(pass(?:word)?|pwd|secret|token|api[_-]?key)=(\S+)")
REDACTED = "[REDACTED]"


def _redact_text(s: str) -> str:
    s = _JWT.sub(REDACTED, s)
    s = _BEARER.sub("Bearer " + REDACTED, s)
    return _KV.sub(lambda m: f"{m.group(1)}={REDACTED}", s)


def redact(value: Any) -> Any:
    """Recursively hide secret-named keys and token-shaped strings."""
    if isinstance(value, dict):
        return {k: (REDACTED if _SECRET_KEY.search(str(k)) else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


class RedactingFilter(logging.Filter):
    """Logging filter applying the same redaction to log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        record.msg, record.args = _redact_text(msg), ()
        return True


def _hash(prev_hash: str, event: Dict[str, Any]) -> str:
    body = canonical_json({k: event.get(k) for k in HASHED_FIELDS})
    return hashlib.sha256((prev_hash + body).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- verification


@dataclass
class VerifyResult:
    ok: bool
    checked: int
    first_bad_seq: Optional[int] = None
    problems: List[str] = field(default_factory=list)


def verify_chain(events: List[Dict[str, Any]], start_hash: str = GENESIS_HASH) -> VerifyResult:
    """Checks seq continuity, prev_hash links and every hash. Reports the first break."""
    prev, problems, first_bad = start_hash, [], None
    expected_seq = events[0]["seq"] if events else 1
    for ev in events:
        bad = []
        if ev.get("seq") != expected_seq:
            bad.append(f"seq {ev.get('seq')} where {expected_seq} expected (missing events)")
        if ev.get("prev_hash") != prev:
            bad.append(f"seq {ev.get('seq')}: prev_hash does not match the previous event")
        if _hash(ev.get("prev_hash", ""), ev) != ev.get("hash"):
            bad.append(f"seq {ev.get('seq')}: content does not match its hash (edited)")
        if bad:
            problems += bad
            first_bad = first_bad or ev.get("seq")
        prev, expected_seq = ev.get("hash"), (ev.get("seq") or expected_seq) + 1
    return VerifyResult(ok=not problems, checked=len(events), first_bad_seq=first_bad, problems=problems)


def read_jsonl(directory: Path | str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in sorted(Path(directory).glob("*.jsonl")):
        with p.open(encoding="utf-8") as f:
            out += [json.loads(line) for line in f if line.strip()]
    return sorted(out, key=lambda e: e["seq"])


# ---------------------------------------------------------------- writer


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class AuditLog:
    def __init__(self, jsonl_dir: Path | str = "logs/audit", db_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
                 load_tail: bool = True):
        self.jsonl_dir = Path(jsonl_dir)
        self.jsonl_dir.mkdir(parents=True, exist_ok=True)
        self._sink = db_sink
        self._q: "queue.Queue[Optional[Dict[str, Any]]]" = queue.Queue()
        self._pending: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._seq, self._prev = 0, GENESIS_HASH
        if load_tail:
            tail = read_jsonl(self.jsonl_dir)
            if tail:
                self._seq, self._prev = tail[-1]["seq"], tail[-1]["hash"]
        self._thread = threading.Thread(target=self._run, name="audit-writer", daemon=True)
        self._thread.start()

    def record(self, *, category: str, action: str, actor: Optional[str] = None, actor_type: Optional[str] = None,
               role: Optional[str] = None, source_ip: Optional[str] = None, target: Optional[str] = None,
               outcome: str = "success", latency_ms: Optional[float] = None, details: Optional[Dict[str, Any]] = None,
               correlation_id_: Optional[str] = None, correlation_id: Optional[str] = None) -> None:
        ctx_actor = current_actor.get() or {}
        self._q.put({
            "event_id": str(uuid.uuid4()),
            "ts": _utc_iso(datetime.now(timezone.utc)),
            "correlation_id": correlation_id or correlation_id_ or globals()["correlation_id"].get(),
            "actor": actor or ctx_actor.get("actor") or "system",
            "actor_type": actor_type or ctx_actor.get("actor_type") or "system",
            "role": role or ctx_actor.get("role"),
            "source_ip": source_ip,
            "category": category,
            "action": action,
            "target": target,
            "outcome": outcome,
            "latency_ms": None if latency_ms is None else round(float(latency_ms), 3),
            "details": redact(details or {}),
        })

    def _run(self) -> None:
        while True:
            ev = self._q.get()
            try:
                if ev is None:
                    return
                with self._lock:
                    self._seq += 1
                    ev["seq"], ev["prev_hash"] = self._seq, self._prev
                    ev["hash"] = _hash(self._prev, ev)
                    self._prev = ev["hash"]
                    day = ev["ts"][:10]
                    with (self.jsonl_dir / f"{day}.jsonl").open("a", encoding="utf-8") as f:
                        f.write(canonical_json(ev) + "\n")
                    self._pending.append(ev)
                    self._drain()
            except Exception:
                logger.exception("audit writer failed")
            finally:
                self._q.task_done()

    def _drain(self) -> None:
        """Insert pending rows in order; stop at the first failure and keep the rest."""
        if self._sink is None:
            self._pending.clear()
            return
        while self._pending:
            try:
                self._sink(self._pending[0])
            except Exception as e:
                logger.warning("audit DB insert deferred (%d pending): %s", len(self._pending), e)
                return
            self._pending.pop(0)

    def flush(self, retry: bool = False) -> None:
        self._q.join()
        if retry:
            with self._lock:
                for _ in range(5):
                    self._drain()
                    if not self._pending:
                        break

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def close(self) -> None:
        self.flush()
        self._q.put(None)
        self._thread.join(timeout=2)


# ---------------------------------------------------------------- process-wide log


_LOG: Optional[AuditLog] = None


def get_audit_log() -> AuditLog:
    global _LOG
    if _LOG is None:
        sink = None
        if os.environ.get("AUDIT_DB", "1") != "0":
            sink = _db_insert
        _LOG = AuditLog(jsonl_dir=os.environ.get("AUDIT_DIR", "logs/audit"), db_sink=sink)
    return _LOG


def audit(**kw: Any) -> None:
    """Record one audit event; never raises into the caller."""
    try:
        get_audit_log().record(**kw)
    except Exception:
        logger.exception("could not record audit event")


def _db_insert(ev: Dict[str, Any]) -> None:
    from server.database import pool  # lazy: tests and scripts may run without a database

    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO audit_events (seq, event_id, ts, correlation_id, actor, actor_type, role, source_ip, category, "
            "action, target, outcome, latency_ms, details, canon, prev_hash, hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,"
            "%s,%s,%s,%s,%s::jsonb,%s,%s,%s)",
            (ev["seq"], ev["event_id"], ev["ts"], ev["correlation_id"], ev["actor"], ev["actor_type"], ev["role"],
             ev["source_ip"], ev["category"], ev["action"], ev["target"], ev["outcome"], ev["latency_ms"],
             json.dumps(ev["details"]), canonical_json({k: ev.get(k) for k in HASHED_FIELDS}), ev["prev_hash"], ev["hash"]),
        )
