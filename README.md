# AI-Powered Digital Twin & Predictive Maintenance System
> An AI-powered digital twin for predictive maintenance, designed to help MSMEs monitor assets, ingest telemetry securely, and triage mechanical failures using an agentic AI assistant with strict security safeguards.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI Status](https://github.com/YMP7/Predictive-Maintenance-AI/actions/workflows/main.yml/badge.svg)](https://github.com/YMP7/Predictive-Maintenance-AI/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2.0-20232a.svg?style=flat&logo=React)](https://react.dev/)
[![TimescaleDB](https://img.shields.io/badge/TimescaleDB-2.13.0-00b0f0.svg?style=flat&logo=PostgreSQL&logoColor=white)](https://www.timescale.com/)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-3c5280.svg?style=flat&logo=EclipseMosquitto)](https://mosquitto.org/)

---

## What's New & Evolution

The system has evolved through several developmental phases to become a secure, production-hardened platform:

*   **Auth & RBAC Hardening (Phase 6):** Upgraded session token storage from vulnerable `localStorage` to secure, HttpOnly, SameSite, and Secure cookies. Introduced custom request-header verification to mitigate CSRF, and rate-limited auth endpoints (`slowapi`) against brute-force attacks.
*   **MQTT Ingestion Security (Phase 5):** Reconfigured the Mosquitto broker to disable anonymous access. Enforced per-device ACLs restricting edge machines to write-only topics (`factory/{machine_id}/telemetry`). Telemetry payloads undergo strict schema boundaries and sanitation checks.
*   **TimescaleDB & Persistence (Phase 5):** Migrated the database layer to TimescaleDB for high-throughput time-series telemetry storage and persistent debounce tracking.
*   **Multi-Channel Notifications (Phase 5):** Persistent notification debouncing to prevent alert storms. Supports SMS, Voice (Twilio), and Email (SMTP) with fail-loud validation checks on startup.
*   **3D Landing Overhaul (Phase 7):** Rewrote the dashboard landing experience to include a 3D digital twin rendering of assets utilizing React Three Fiber, indicating physical health and anomaly states dynamically.
*   **Agentic AI Safeguards (Phase 8):** Implemented an LLM-based troubleshooting agent using Gemini. Hardened the tool execution layer against prompt injections by requiring telemetry-grounding validation (matching severity and recency in DB), a hard volume cap (3 work orders per machine/day), and a **provenance isolation check** restricting valid grounding alerts to those generated solely by the internal `ai_pipeline`.

---

## What's Inside

```
.
├── client/                     # React Single-Page Application (SPA)
│   ├── src/
│   │   ├── components/
│   │   │   └── MachineAnimation.tsx # 3D digital twin animation (normal/anomalous)
│   │   └── pages/
│   │       ├── Dashboard.tsx   # Live telemetry telemetry charts & AI chat panel
│   │       └── Login.tsx       # Rate-limited auth panel utilizing HttpOnly JWT cookies
│   └── package.json            # Frontend dependency definitions
├── server/                     # Python FastAPI Backend
│   ├── backend_api.py          # Main REST endpoints, router, and CORS configuration
│   ├── auth.py                 # JWT validation, role checking, & password hashing
│   ├── data_service.py         # Telemetry database ingestion & anomaly pipelines
│   ├── mqtt_client.py          # Secure MQTT subscriber with schema bounds validation
│   ├── llm_agent.py            # Agentic reasoning loop wrapping Gemini
│   ├── agent_tools.py          # Database-bound tools exposed to the agent
│   └── database.py             # TimescaleDB connection pool manager
├── tests/                      # Testing suites
│   ├── test_api.py             # REST API tests (RBAC validation, rate limiting)
│   ├── test_mqtt.py            # MQTT schema boundaries & TLS connection tests
│   └── test_work_order_safeguards.py # Grounding checks, daily cap, and provenance tests
├── scripts/                    # Management scripts
│   ├── migrate.py              # TimescaleDB schema initialization
│   └── seed_dev.py             # Development database seed utility
├── docker-compose.yml          # TimescaleDB and Mosquitto orchestrator
└── requirements.txt            # Python backend dependency definitions
```

---

## Quick Start

### 1. Provision Infrastructure
Start the TimescaleDB and Mosquitto broker services:
```bash
docker-compose up -d
```

### 2. Configure Environment
Copy `.env.example` to `.env` and fill in the required parameters:
```bash
cp .env.example .env
```
Ensure you generate a secure 32-byte JWT secret:
```bash
# On macOS/Linux/Git Bash
openssl rand -hex 32
```

#### Fail-Loud Environment Requirements:
*   `JWT_SECRET_KEY`: The application will crash on startup if this is missing.
*   `DATABASE_URL`: Connection string to TimescaleDB (e.g. `postgresql://dtwin:your_secure_password@localhost:5433/digital_twin`).
*   `NOTIFICATIONS_ENABLED`: If set to `true`, Twilio credentials (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`) and SMTP credentials (`SMTP_HOST`, `SMTP_FROM`) must be provided, or the server will fail to start.

### 3. Run Backend Migrations & Seed
Run database migrations to initialize tables and hyper-tables, then seed default development accounts:
```bash
python scripts/migrate.py
python scripts/seed_dev.py
```

### 4. Run the Integrated Server
Install Python dependencies and start the backend:
```bash
pip install -r requirements.txt
$env:PYTHONPATH="." # On Windows PowerShell
python server/integrated_server.py
```

### 5. Start the Frontend
Install Node packages and run the React frontend dev server:
```bash
cd client
npm install
npm run dev
```

---

## Component Reference

| I want to... | Use this | Notes |
| :--- | :--- | :--- |
| **Monitor live status** | [Dashboard](http://localhost:3000/dashboard) | Displays real-time charts & 3D digital twin states. |
| **Receive critical alerts** | Notification System | Relies on Twilio & SMTP; stateful debounce is active. |
| **Triage and query machines** | Agent Chat | Chat sidebar on the dashboard page. |
| **Inject test anomaly** | Fault Endpoint | `POST /api/machines/{id}/fault` (Requires **Admin** role). |

---

## Security & Limitations

Please read [SECURITY.md](SECURITY.md) for full compliance guidelines.

### Known Limitations:
1.  **Untested End-to-End SMS**: Twilio notification delivery has only been verified against the Twilio API sandbox.
2.  **No Deployed HTTPS**: Local execution relies on localhost. Production deployment requires Nginx + Let's Encrypt configurations.
3.  **No UI Resolve Flow**: While work orders are securely created and stored in the database, operators cannot currently transition them to "Closed" or "Resolved" via the UI dashboard.

---

## FAQ

#### Is this using real IoT hardware?
No. The system runs a local simulator that publishes synthetic sensor feeds to the MQTT broker, replicating a real physical machine. The MQTT client and database schema are fully compatible with real hardware.

#### Can the AI agent take real actions?
Yes. The LLM can invoke `create_work_order`. However, it cannot write to the database directly; it passes through a strict backend gateway enforcing a 3/machine/day volume cap and verifying that a corresponding `ai_pipeline`-generated alert is logged in the database within the last 24h.

#### How do I run tests?
Run the test suites with:
```bash
$env:PYTHONPATH="."; pytest -v
```
