# ATLAS: AI-Powered Digital Twin & Predictive Maintenance System

> A digital-twin platform for predictive maintenance: machine adapters feed normalized telemetry into an LSTM world model for remaining-useful-life (RUL) estimation, with an operator dashboard and an LLM assistant whose work orders require human approval.

[![CI](https://github.com/YMP7/Predictive-Maintenance-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/YMP7/Predictive-Maintenance-AI/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-%E2%89%A50.115-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-20232a.svg?style=flat&logo=React)](https://react.dev/)
[![TimescaleDB](https://img.shields.io/badge/TimescaleDB-pg16-00b0f0.svg?style=flat&logo=PostgreSQL&logoColor=white)](https://www.timescale.com/)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-3c5280.svg?style=flat&logo=EclipseMosquitto)](https://mosquitto.org/)

---

## Architecture Overview

```
+-----------------------------------------------------------------------------------+
|                           ATLAS SYSTEM ARCHITECTURE                               |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [ TELEMETRY SOURCES — MachineAdapter SDK ]                                       |
|  * NASA C-MAPSS turbofan dataset (replay)   * Laptop / workstation telemetry      |
|  * Android phone sensors (ADB / Termux)     * Linux servers (SSH)                 |
|  * Modbus TCP machines (read-only)                                                |
|                                    │ (MQTT / TLS / ACLs)                          |
|                                    ▼                                              |
|  [ FASTAPI BACKEND ]                                                              |
|  ┌─────────────────────────────────────────────────────────────────────────────┐  |
|  │ FAST TIER                                                                   │  |
|  │ - Schema-validated MQTT ingestion behind Mosquitto ACLs                     │  |
|  │ - Per-machine threshold fault detection and degradation-trend RUL estimate  │  |
|  │ - Debounced multi-channel alerting (SMS / voice / email)                    │  |
|  ├─────────────────────────────────────────────────────────────────────────────┤  |
|  │ MODEL TIER                                                                  │  |
|  │ - World model: 2-layer LSTM + additive temporal attention → 32-d state      │  |
|  │ - Per-domain checkpoints; untrained domains refuse inference                │  |
|  │ - Gemini LLM assistant; agent work orders need human approval               │  |
|  └─────────────────────────────────────────────────────────────────────────────┘  |
|                                    │                                              |
|                                    ▼                                              |
|  [ PERSISTENCE ]                              [ OPERATOR DASHBOARD ]              |
|  * PostgreSQL 16 + TimescaleDB hypertables    * React 19 + Vite + TypeScript      |
|  * pgvector state-vector memory               * 3D view (three.js), Recharts, SSE |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Capabilities

### RUL model
- **World model** (`server/atlas/world_model.py`): a unidirectional 2-layer LSTM (hidden size 64, dropout 0.2) over 30-cycle windows, followed by additive (Bahdanau-style, Linear–tanh–Linear) temporal attention that pools the sequence into a 32-dimensional state vector. A small MLP head predicts RUL, capped at 125 cycles.
- **Training** (`server/atlas/train_rul.py`): MSE loss. Evaluation reports RMSE and the asymmetric PHM'08 score, which penalizes late predictions more than early ones.
- **Untrained-model guard**: a domain without a trained checkpoint reports `is_trained=False` and raises `UntrainedModelError` instead of answering with random weights.

### Multiple machine domains
- Adapters for C-MAPSS (FD001–FD004), laptops, Android phones, Linux servers, and Modbus TCP devices, all producing the same `NormalizedReading` schema.
- A cross-domain transfer study (`server/atlas/transfer_study.py`) *measures* how well representations transfer between domains, using MMD and a negative-transfer index. It reports negative transfer between compute and turbofan domains; it does not align domains.

### Adapter SDK
- `MachineAdapter` base class plus a conformance suite (`tests/test_adapter_conformance.py`) that any new adapter must pass. Spec: [docs/ADAPTER_SDK_SPEC.md](docs/ADAPTER_SDK_SPEC.md).

### LLM assistant with human approval
- Conversational diagnostics backed by Google Gemini.
- Work orders created by the agent are validated server-side against recorded alerts and capped at 3 per machine per 24 hours.
- High and Critical work orders land in `Pending Approval` and need an authenticated operator or admin to approve them.

### Documentation
Indexed in the [Documentation Hub](docs/README.md), including the [System Architecture Document](docs/System%20Architecture%20Document%20(SAD).md), [Ablation Study Results](docs/ABLATION_STUDY_RESULTS.md) and [References](docs/REFERENCES.md).

---

## Repository Structure

```
.
├── client/                     # Frontend (React 19 + Vite + TypeScript)
├── config/                     # Machine profiles and configuration
├── data/                       # Datasets (C-MAPSS) and model checkpoints
├── docs/                       # Architecture, QA, and operations documentation
│   ├── figures/                # Architecture diagrams
│   ├── screenshots/            # UI verification captures
│   └── REFERENCES.md           # Bibliography with DOIs
├── ml/                         # Preprocessing and training utilities
├── mosquitto/                  # Mosquitto broker config and ACLs
├── notebooks/                  # Exploration notebooks
├── scripts/                    # Migration, evaluation, benchmark, and verification tools
├── server/
│   ├── adapters/               # MachineAdapter SDK and domain adapters
│   ├── atlas/                  # World model, RUL engine, and analysis modules
│   ├── backend_api.py          # FastAPI endpoints, CORS, auth middleware
│   ├── data_service.py         # Telemetry ingestion and TimescaleDB pool
│   ├── llm_agent.py            # Gemini assistant
│   └── mqtt_client.py          # MQTT subscriber with schema validation
├── tests/                      # pytest suite
├── docker-compose.yml          # TimescaleDB and Mosquitto for local development
└── requirements.txt            # Python dependencies (torch: requirements-ml.txt)
```

---

## Quick Start

### 1. Configure environment
```bash
cp .env.example .env
```
Generate a 32-byte JWT secret and put it in `.env`:
```bash
openssl rand -hex 32
```

Required variables:
- `JWT_SECRET_KEY`: the server refuses to start without it.
- `TSDB_PASSWORD` and `DATABASE_URL`: e.g. `postgresql://dtwin:<password>@localhost:5433/digital_twin`.
- `ADMIN_PASSWORD_HASH` / `OPERATOR_PASSWORD_HASH`: required by the development seed script.
- `GEMINI_API_KEY`: required when `GEMINI_AGENT_ENABLED=true`.

### 2. Start infrastructure
```bash
python scripts/generate_mqtt_passwords.py
docker compose up -d timescaledb mosquitto
```

### 3. Run migrations and seed development data
```bash
python scripts/migrate.py
python scripts/migrate_atlas.py
python scripts/seed_dev.py
```
`seed_dev.py` creates development accounts with publicly known passwords. Never run it against a deployed database.

### 4. Start the backend
```bash
pip install -r requirements.txt
pip install -r requirements-ml.txt --extra-index-url https://download.pytorch.org/whl/cpu
PYTHONPATH=. python server/integrated_server.py
```

### 5. Start the frontend
```bash
cd client
npm ci
npm run dev
```
Open the URL Vite prints (default `http://localhost:5173`).

---

## Testing

```bash
python -m pytest tests/ -q
```

The suite has **269 tests** on the v1.1 branch (218 on `main`, plus 51 from the adapter SDK and Modbus suites). Measured locally on 2026-10-08 (Windows 11, Python 3.13.5, **no database running**): 234 passed, 20 skipped, 15 failed. All 15 failures are database tests that time out without TimescaleDB. The full database-backed run is the `test-backend` job in [CI](.github/workflows/ci.yml).

Adapter conformance only, optionally for one adapter:
```bash
python -m pytest tests/test_adapter_conformance.py --adapter modbus
```

---

## Security

- MQTT credentials are hashed in memory by `scripts/generate_mqtt_passwords.py`; no plaintext password file is written.
- Session cookies are HttpOnly and SameSite=Lax, with an anti-CSRF header check and `slowapi` rate limiting. The `Secure` flag is set only when `ENVIRONMENT` is not `development` (the default), so set `ENVIRONMENT=production` for any HTTPS deployment.
- `CORS_ORIGINS=*` is rejected at startup.
- Mosquitto ACLs restrict edge devices to their own topics.

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

---

## License

The repository currently contains an MIT [LICENSE](LICENSE) file. Licensing is under review; see [docs/LICENSE_OPTIONS.md](docs/LICENSE_OPTIONS.md).
