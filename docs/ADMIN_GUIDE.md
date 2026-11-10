# ATLAS administrator guide

For whoever installs and runs ATLAS: the database and its roles, connecting machines, users, models, the audit trail and health. Operators' tasks are in [USER_GUIDE.md](USER_GUIDE.md).

## 1. What runs where

| Piece | What it is | Default |
|---|---|---|
| API and web app | FastAPI (`server/integrated_server.py`), serves the built React app and `/api` | `http://localhost:8000` |
| Database | TimescaleDB (PostgreSQL 16) in Docker | port 5433 |
| Broker | Mosquitto, per-device accounts and ACLs (`mosquitto/config/`) | port 1883 |
| Dev web server | Vite, proxies `/api` to `ATLAS_API_TARGET` | `http://localhost:3000` |

Requirements: Python 3.11+ (3.13 tested), Node 20+, Docker. 8 GB RAM is enough; the models run on CPU.

## 2. Install

Follow the [README quick start](../README.md#quick-start): configure `.env`, start the database and broker, run the three migrations (`migrate.py`, `migrate_atlas.py`, `migrate_platform.py`), seed development accounts, start the API, build or serve the web app.

`scripts/migrate_platform.py` is safe to re-run. It creates the audit, ingest, device and trace tables and the alarm and work-order columns, and the role `atlas_app`.

### The application database role

The audit table can only be appended to. Two things enforce that:
- a trigger that refuses UPDATE and DELETE;
- the role `atlas_app`, which has only SELECT and INSERT on `audit_events`.

To use it:
1. Set `ATLAS_APP_DB_PASSWORD` in `.env` and re-run `python scripts/migrate_platform.py`.
2. Point the API at `atlas_app`: under Docker, set `API_DATABASE_URL`. For an API run directly, set its `DATABASE_URL` and keep the owner URL in `MIGRATION_DATABASE_URL` for migrations.

Until you do this, the API connects as the owner and only the trigger protects the audit table.

### On Windows

Paths that contain `&` (like this repository's) break npm's `.cmd` wrappers. The `client/package.json` scripts call Node directly (`npm run build`, `npm run dev`, `npm run e2e` all work); avoid `npx` in such paths.

## 3. Connect a machine (`/admin/onboarding`)

The wizard has seven steps:
1. Register the asset id (letters, digits, `_ . -`) and a display name.
2. Pick the machine type, which sets its 3D model. **Load the register map** fills the channels where ATLAS knows the device (Modbus today).
3. Pick the protocol and see an example payload.
4. Map channels: device name, feature name, SI unit, scale and offset, valid range, sampling rate, health weight. Out-of-range values are flagged, never clipped.
5. Save the profile and watch live samples. Send a test sample to see validation results.
6. Bind each channel to a 3D part.
7. Activate. ATLAS issues a device token and shows it **once**; only its SHA-256 hash is stored.

Protocols:

| Protocol | How the device sends | Auth |
|---|---|---|
| HTTP | `POST /api/ingest/<asset>` with `{"values": {...}}` or a batch of `samples` | `Authorization: Bearer <device token>` |
| WebSocket | `ws://<host>:8000/api/ingest/ws/<asset>`, first message `{"token": ...}` | device token |
| MQTT | topic `factory/<asset>/telemetry` | a broker account for that device in `mosquitto/config` (create it with `scripts/generate_mqtt_passwords.py`; the wizard does not) |
| Modbus TCP | `python scripts/modbus_bridge.py --machine-id <asset> --host <plc> --port 502` with `ATLAS_DEVICE_TOKEN` set; `--simulate` runs the bundled simulator | device token |
| CSV / Parquet | `POST /api/admin/ingest/<asset>/upload` (dry run first, then commit) | admin session |
| Manual | operators' inspection readings, `POST /api/machines/<asset>/manual-readings` | operator session |

Per-device limits: 10 messages per second sustained (burst 20) and 256 KB per push.

**Devices** (`/admin/devices`) shows last seen, messages per minute, error rate and channel quality. **Rotate** issues a new token (the old one stops at once). **Revoke** disconnects the device for good.

## 4. Users and roles (`/admin/users`)

Change a user's role here; you cannot change your own. New accounts are created with `scripts/seed_dev.py` for development, or directly in the `users` table with a bcrypt hash (`server.auth.get_password_hash`). Passwords never pass through the web app.

The server enforces roles:
- every `/api/admin/*` path is admin-only;
- writes to alarms and work orders need an operator or admin.

The web app hides what a role cannot use, but the API is the control.

## 5. Models (`/admin/models`, `/admin/cognition`)

- **Registry:** lists each domain's World Model versions with their metrics.
  - ATLAS archives a checkpoint under `data/models/registry/<domain>/` the first time it sees its content.
  - **Make active** swaps in an older (or newer) version and reloads it. A reason is required, and the current weights are archived first, so the change can be undone the same way.
- **Retrain:** runs the Learning Engine on the C-MAPSS training split. A candidate replaces the model only if its validation RMSE is within 3% of the best ever promoted; otherwise production is left alone.
- **Cognition:** shows the pipeline for any machine.
  - **Run live trace** stores a trace; the slider replays stored traces.
  - The drift monitor needs at least 9 stored traces for a machine.

## 6. The audit trail

Every API request, sign-in, ingest batch, inference, decision, alarm and work-order action, model change and UI command is recorded. Records go to `audit_events` (hash-chained) and to a daily JSONL mirror in `logs/audit/`. Details: [AUDIT_TRAIL.md](AUDIT_TRAIL.md).

```bash
python scripts/audit_verify.py
python scripts/audit_export.py --from 2026-11-01 --to 2026-11-10 --category alarm --format csv --out alarms.csv
```

`audit_verify.py` checks both copies and names the first broken record. Only one process can write an audit folder: a second one is refused at start-up (it would fork the chain). If lines must be set aside, move them to `logs/audit/quarantine/` with the original file and a note, and never delete them. On start-up the API re-inserts any mirror events the database missed.

## 7. Health

- **Readiness:** `GET /api/ready` is public; it returns 503 when degraded. It reports:
  - database connectivity;
  - MQTT state;
  - models loaded;
  - audit writes pending.
- **Status:** the header shows *Connected* or *API unreachable* from the same probe.
- **Diagnostics** (`/admin/diagnostics`): readiness, which RUL models are loaded and their benchmark, and recorded pipeline latency.

## 8. Docker

```bash
docker compose up -d --build
docker compose ps
```
The API and web app are served at `http://localhost:8000`. Set `ENVIRONMENT=production` behind HTTPS so cookies are marked Secure. HTTPS itself needs a domain and is not configured here.

## 9. Troubleshooting

| Symptom | Check |
|---|---|
| API will not start: `JWT_SECRET_KEY` | Set it in `.env` (`openssl rand -hex 32`) |
| Header says "API unreachable" | `curl http://localhost:8000/api/ready`; the database and broker containers (`docker compose ps`) |
| A device's pushes return 401 | Token rotated or revoked; issue a new one on Devices |
| A device's pushes return 429 | It sends faster than 10/s; batch samples instead |
| Machine shows "No data" | Devices page: last seen and error rate; the profile's channel names must match what the device sends |
| Sign-in returns "Too many sign-in attempts" | 5 attempts per minute per address; wait a minute |
| `audit_verify` reports BROKEN | It names the first bad record; see section 6 before touching any file |
