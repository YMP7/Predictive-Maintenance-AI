"""
Export audit events by time range and category.

Usage:
    python scripts/audit_export.py --from 2026-11-01 --to 2026-11-08 --category ingest --format csv --out ingest.csv
    python scripts/audit_export.py --category auth --format jsonl            # to stdout
    python scripts/audit_export.py --source jsonl --dir logs/audit ...       # from the mirror instead of the DB

--from is inclusive, --to is exclusive; both are UTC dates or ISO times.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from server.audit import read_jsonl  # noqa: E402

FIELDS = ["seq", "event_id", "ts", "correlation_id", "actor", "actor_type", "role", "source_ip", "category", "action",
          "target", "outcome", "latency_ms", "details", "prev_hash", "hash"]


def _when(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def from_db(start, end, categories) -> List[Dict[str, Any]]:
    import psycopg

    where, params = [], []
    if start:
        where.append("ts >= %s")
        params.append(start)
    if end:
        where.append("ts < %s")
        params.append(end)
    if categories:
        where.append("category = ANY(%s)")
        params.append(categories)
    sql = f"SELECT {', '.join(FIELDS)} FROM audit_events" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY seq"
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(zip(FIELDS, r)) for r in rows]


def from_jsonl(directory, start, end, categories) -> List[Dict[str, Any]]:
    out = []
    for e in read_jsonl(directory):
        ts = _when(e["ts"])
        if (start and ts < start) or (end and ts >= end) or (categories and e["category"] not in categories):
            continue
        out.append(e)
    return out


def write(events: List[Dict[str, Any]], fmt: str, fh) -> None:
    if fmt == "jsonl":
        for e in events:
            fh.write(json.dumps({k: e.get(k) for k in FIELDS}, default=str, ensure_ascii=False) + "\n")
        return
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    for e in events:
        w.writerow({k: (json.dumps(e.get(k), ensure_ascii=False) if k == "details" else e.get(k)) for k in FIELDS})


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Export ATLAS audit events")
    ap.add_argument("--from", dest="start")
    ap.add_argument("--to", dest="end")
    ap.add_argument("--category", action="append", default=[], help="Repeatable, e.g. --category auth --category admin")
    ap.add_argument("--format", choices=("csv", "jsonl"), default="jsonl")
    ap.add_argument("--source", choices=("db", "jsonl"), default="db")
    ap.add_argument("--dir", default=os.environ.get("AUDIT_DIR", "logs/audit"))
    ap.add_argument("--out", help="File to write; stdout when omitted")
    args = ap.parse_args(argv)

    start, end = _when(args.start), _when(args.end)
    events = (from_db(start, end, args.category) if args.source == "db"
              else from_jsonl(args.dir, start, end, args.category))
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as fh:
            write(events, args.format, fh)
        print(f"Wrote {len(events)} events to {args.out}", file=sys.stderr)
    else:
        write(events, args.format, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
