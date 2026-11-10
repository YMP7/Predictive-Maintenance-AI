# Audit trail

**Label: BUILD.** ATLAS records every movement in an append-only, hash-chained log. The log is for
examiners, maintainers and incident review; it is **not shown in the UI**.

## What is recorded

| Category | Events |
|---|---|
| `api` | Every `/api` request: method + route template, status, latency, actor, role, IP, correlation ID |
| `auth` | Login success and failure (never the password), logout, token refresh |
| `ingest` | Every batch from HTTP, WebSocket, MQTT, CSV/Parquet and manual entry: source, device, counts, reject reasons, `batch_id`. Raw values stay in `sensor_readings`, linked by `batch_id` |
| `device` | WebSocket connect, disconnect and failed auth; MQTT broker connect and disconnect |
| `inference` | Every RUL prediction: model file + content hash (version), input-window hash, RUL mean, p10 and p90 |
| `simulation` | Every Monte Carlo run (seed, N, per-action summary); simulator start and stop; fault injection |
| `decision` | Every Decision Graph output: candidates with costs, chosen action, Confidence, Risk, Impact, Urgency |
| `explanation` | Top attributions, AMKB neighbour IDs, confidence |
| `cognition` | Admin cognition traces (window hash, RUL band, seed, per-stage latency) |
| `alarm` | Alarm raised. Acknowledge, shelve and clear are added with the Alarms page (P4) |
| `work_order` | Created (agent), approved, resolved |
| `admin` | Machine, sensor-profile and device changes, with `before` and `after` |
| `model`, `learning` | Model reload; batch retrain with its result (promoted or rejected) |
| `client` | Browser interactions sent in batches to `POST /api/audit/client-events`: page views, commands, 3D parts opened, filters, exports |
| `operator` | Notes attached to manual inspection readings |

## Event schema

`seq, event_id, ts (UTC, microseconds), correlation_id, actor, actor_type (user | device | system | anonymous), role,
source_ip, category, action, target, outcome (success | failure | partial | rejected), latency_ms, details (JSON),
prev_hash, hash`

`hash = sha256(prev_hash + canonical_json(event))`. Canonical JSON uses sorted keys, no spaces and UTF-8. The first
event's `prev_hash` is 64 zeros. In the database, the column `canon` stores the exact text that was hashed.

## How it is protected

1. **Hash chain.** Editing any event changes its hash. Deleting one leaves a gap in `seq` and a broken `prev_hash`.
2. **Trigger.** `audit_events_append_only` raises on any UPDATE or DELETE, even from the table owner.
3. **Separate database user.** The API connects as `atlas_app`. It has `SELECT` and `INSERT` on `audit_events` and
   nothing else on that table (no UPDATE, DELETE or TRUNCATE). Migrations run as the owner (`dtwin`), which the API
   never uses.
4. **Mirror.** Every event is written first to `logs/audit/YYYY-MM-DD.jsonl` (UTC day), then to the database. If the
   database is down, events wait in order and are retried, so the two copies end on the same tip.
5. **Redaction.** Keys that look like secrets (password, token, secret, authorization, cookie, api_key, jwt, private
   key) and token-shaped strings (JWTs, `Bearer …`, `password=…`) are replaced with `[REDACTED]` before hashing. The
   same filter is attached to the application logs.

Known limits (FUTURE-WORK): a database superuser can disable the trigger and drop the table, and a person who can
rewrite both copies can recompute the whole chain. Anchoring the latest hash outside the machine (for example,
printing it in the daily report) would close that gap. One writer per process: run the API with a single worker.

## Setting up the API user

```bash
# 1. Choose a password and add it to .env
ATLAS_APP_DB_PASSWORD=<a long random string>

# 2. Create tables, trigger and role (as the owner)
conda run -n myenv python scripts/migrate_platform.py

# 3. Point the API at atlas_app
#    local run (.env):
DATABASE_URL=postgresql://atlas_app:<password>@localhost:5433/digital_twin
MIGRATION_DATABASE_URL=postgresql://dtwin:<owner password>@localhost:5433/digital_twin
#    docker compose (.env): the app container uses API_DATABASE_URL when it is set
API_DATABASE_URL=postgresql://atlas_app:<password>@timescaledb:5432/digital_twin
```

## Tools

```bash
# Verify the chain in the database and the mirror, and cross-check them. Exit code 0 = intact, 1 = broken.
conda run -n myenv python scripts/audit_verify.py
conda run -n myenv python scripts/audit_verify.py --source jsonl --dir logs/audit

# Export by time range and category (CSV or JSONL)
conda run -n myenv python scripts/audit_export.py --from 2026-11-01 --to 2026-11-09 --category ingest --format csv --out ingest.csv
```

## Correlation IDs

The browser may send `X-Correlation-ID` (8–64 letters, digits or dashes). Otherwise the API creates a UUID. The ID is
returned in the response header and attached to every audit event raised while handling that request, including the
inference, simulation, decision and explanation events. Tests write to a temporary folder with `AUDIT_DB=0`, so test
runs never touch the real chain.
