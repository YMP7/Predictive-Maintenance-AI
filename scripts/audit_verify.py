"""
Verify the audit trail's hash chain and report the first break.

Checks, for the database and/or the daily JSONL mirror:
  - seq runs 1..N with no gaps (a gap means deleted events),
  - every prev_hash equals the previous event's hash,
  - every hash equals sha256(prev_hash + canonical event) (a mismatch means an edited event),
  - in the database, the queryable columns still match the hashed canonical record,
  - with --source both, the two copies end on the same seq and hash.

Exit code 0 = intact, 1 = broken, 2 = could not read a source.

Usage:
    python scripts/audit_verify.py                      # database and logs/audit, cross-checked
    python scripts/audit_verify.py --source jsonl --dir logs/audit
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from server.audit import GENESIS_HASH, HASHED_FIELDS, canonical_json, read_jsonl, verify_chain  # noqa: E402

COLUMN_CHECKS = ("seq", "event_id", "correlation_id", "actor", "actor_type", "role", "source_ip", "category", "action",
                 "target", "outcome")


def load_db() -> List[Dict[str, Any]]:
    import psycopg

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    cols = ("seq", "event_id", "ts", "correlation_id", "actor", "actor_type", "role", "source_ip", "category", "action",
            "target", "outcome", "latency_ms", "details", "canon", "prev_hash", "hash")
    with psycopg.connect(url) as conn:
        rows = conn.execute(f"SELECT {', '.join(cols)} FROM audit_events ORDER BY seq").fetchall()
    return [dict(zip(cols, r)) for r in rows]


def db_events(rows: List[Dict[str, Any]]) -> (List[Dict[str, Any]], List[str]):
    """Turn rows back into hashed events (from `canon`) and flag columns edited apart from it."""
    events, problems = [], []
    for r in rows:
        try:
            canon = json.loads(r["canon"])
        except (TypeError, ValueError):
            problems.append(f"seq {r['seq']}: canonical record is unreadable")
            continue
        for col in COLUMN_CHECKS:
            if str(canon.get(col)) != str(r[col]):
                problems.append(f"seq {r['seq']}: column {col} differs from the hashed record")
        if isinstance(r["ts"], datetime) and canon.get("ts"):
            if datetime.fromisoformat(canon["ts"].replace("Z", "+00:00")) != r["ts"]:
                problems.append(f"seq {r['seq']}: column ts differs from the hashed record")
        if canonical_json(r["details"] or {}) != canonical_json(canon.get("details") or {}):
            problems.append(f"seq {r['seq']}: column details differs from the hashed record")
        events.append({**{k: canon.get(k) for k in HASHED_FIELDS}, "prev_hash": r["prev_hash"], "hash": r["hash"]})
    return events, problems


def report(name: str, events: List[Dict[str, Any]], extra: Optional[List[str]] = None) -> bool:
    result = verify_chain(events, start_hash=GENESIS_HASH)
    problems = (extra or []) + result.problems
    tip = f"seq {events[-1]['seq']} {events[-1]['hash'][:16]}" if events else "empty"
    if problems:
        print(f"[{name}] BROKEN: {len(events)} events, first bad seq {result.first_bad_seq}, tip {tip}")
        for p in problems[:50]:
            print(f"  - {p}")
        if len(problems) > 50:
            print(f"  ... {len(problems) - 50} more")
        return False
    print(f"[{name}] intact: {len(events)} events, tip {tip}")
    return True


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--source", choices=("db", "jsonl", "both"), default="both")
    ap.add_argument("--dir", default=os.environ.get("AUDIT_DIR", "logs/audit"), help="JSONL mirror folder")
    args = ap.parse_args(argv)

    ok, tips = True, {}
    if args.source in ("jsonl", "both"):
        try:
            events = read_jsonl(args.dir)
        except Exception as e:
            print(f"[jsonl] could not read {args.dir}: {e}")
            return 2
        ok &= report("jsonl", events)
        tips["jsonl"] = (events[-1]["seq"], events[-1]["hash"]) if events else None
    if args.source in ("db", "both"):
        try:
            rows = load_db()
        except Exception as e:
            print(f"[db] could not read audit_events: {e}")
            return 2
        events, problems = db_events(rows)
        ok &= report("db", events, problems)
        tips["db"] = (events[-1]["seq"], events[-1]["hash"]) if events else None
    if args.source == "both" and tips.get("db") != tips.get("jsonl"):
        # The database can lag the mirror while it is down (rows are retried); anything else is a divergence.
        print(f"[both] tips differ: db {tips.get('db')} vs jsonl {tips.get('jsonl')}")
        db_tip, js_tip = tips.get("db"), tips.get("jsonl")
        if not (db_tip and js_tip and db_tip[0] < js_tip[0]):
            ok = False
        else:
            print("[both] database is behind the mirror (pending inserts); not a break")
    print("RESULT:", "INTACT" if ok else "BROKEN")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
