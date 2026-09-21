# ATLAS: AI-Powered Digital Twin & Predictive Maintenance System

> **An enterprise-grade, multi-agent digital twin platform for industrial predictive maintenance. ATLAS combines dual-timescale cognitive agents, real-time sensor fusion across 4 industrial domains, and strict execution safeguards for autonomous fault diagnosis and RUL estimation.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI Status](https://github.com/YMP7/Predictive-Maintenance-AI/actions/workflows/main.yml/badge.svg)](https://github.com/YMP7/Predictive-Maintenance-AI/actions)
[![Tests Passing](https://img.shields.io/badge/Tests-218%20Passed-brightgreen.svg)](tests/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2.0-20232a.svg?style=flat&logo=React)](https://react.dev/)
[![TimescaleDB](https://img.shields.io/badge/TimescaleDB-2.13.0-00b0f0.svg?style=flat&logo=PostgreSQL&logoColor=white)](https://www.timescale.com/)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-3c5280.svg?style=flat&logo=EclipseMosquitto)](https://mosquitto.org/)

---

## Architecture Overview

ATLAS organizes predictive maintenance into a **dual-timescale cognitive architecture**:

```
+-----------------------------------------------------------------------------------+
|                           ATLAS SYSTEM ARCHITECTURE                               |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [ INDUSTRIAL TELEMETRY SOURCES ]                                                 |
|  * C-MAPSS Turbofans (21 Sensors)   * Workstation Hardware Telemetry              |
|  * Mobile Edge Sensors (WiFi / USB)  * Server Nodes (Compute & Memory Load)       |
|                                                                                   |
|                                    │ (MQTT / TLS / ACLs)                          |
|                                    ▼                                              |
|  [ FASTAPI BACKEND & COGNITION ENGINE ]                                           |
|  ┌─────────────────────────────────────────────────────────────────────────────┐  |
|  │ FAST / REFLEX TIER (Sub-Second Ingestion & Anomaly Detection)               │  |
|  │ - Mosquitto ACL Broker Ingestion & Schema Bounds Checking                   │  |
|  │ - Streaming Exponential Moving Average (EMA) & Mahalanobis Metric Anomaly   │  |
|  │ - Stateful Anomaly Debouncing & Multi-Channel Alert Router (SMS/Voice/Mail) │  |
|  ├─────────────────────────────────────────────────────────────────────────────┤  |
|  │ DELIBERATIVE / STRATEGIC TIER (Deep RUL Forecasting & Knowledge Fusion)      │  |
|  │ - Hybrid Asymmetric CNN-BiLSTM-Attention RUL Estimation Engine              │  |
|  │ - Maximum Mean Discrepancy (MMD) Cross-Domain Feature Alignment            │  |
|  │ - Grounded Gemini LLM Agent with Provenance Isolation & Safety Safeguards   │  |
|  │ - Human-in-the-Loop Work Order Approval Gateway                             │  |
|  └─────────────────────────────────────────────────────────────────────────────┘  |
|                                    │                                              |
|                                    ▼                                              |
|  [ PERSISTENCE & ANALYTICS ]                 [ OPERATOR COCKPIT ]                 |
|  * PostgreSQL + TimescaleDB Hypertables      * React 18 + Vite + TypeScript       |
|  * Multi-Domain Knowledge Base (AMKB)        * 3D Canvas (React Three Fiber)      |
|  * Connection Pooling (psycopg3)             * Real-time Recharts & SSE Streaming|
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Key Innovations & Capabilities

### 1. Multi-Tier Cognitive Coordination
- **Reflex Agent**: Sub-second boundary checking and unsupervised statistical anomaly scoring to catch abrupt transient spikes.
- **Diagnostic Agent**: Attribution mapping and localized root-cause isolation across correlated sensor channels.
- **Strategic Agent**: Remaining Useful Life (RUL) regression utilizing asymmetric penalization ($\alpha = 10$, $\beta = 13$) to penalize late predictions far more heavily than early maintenance interventions.

### 2. Cross-Domain Transfer Learning
- Calibrated to generalize across **4 distinct operational domains**:
  1. **Turbofan Engines** (NASA C-MAPSS FD001–FD004)
  2. **Workstation Hardware** (CPU thermal margins, GPU load, storage IOPS)
  3. **Mobile Edge Devices** (Battery temperature, accelerometer, WiFi/USB streaming)
  4. **Industrial Server Nodes** (Compute virtualization, network bandwidth, memory pressure)
- Implements **Maximum Mean Discrepancy (MMD)** and latent manifold alignment to minimize negative transfer when adapting pre-trained weights to unseen equipment.

### 3. Grounded LLM Agent with Strict Safeguards
- Conversational diagnostics backed by Google Gemini.
- **Telemetry Grounding**: The LLM cannot invent or hallucinate alerts; every recommendation is cross-referenced against real-time database readings.
- **Provenance Isolation**: Work orders are blocked unless tied to verified, internal `ai_pipeline` alerts.
- **Rate-Capped Execution**: Maximum 3 work orders per machine per 24-hour cycle.
- **Role-Based Access Control (RBAC)**: Critical and high-urgency interventions require explicit human-in-the-loop authorization.

### 4. Comprehensive Documentation Suite
All research papers, empirical studies, and operational playbooks are indexed in the **[Documentation Navigation Hub](docs/README.md)**:
- [ATLAS Thesis Chapter](docs/ATLAS_THESIS_CHAPTER.md)
- [Viva Technical Defense Brief](docs/VIVA_TECHNICAL_DEFENSE_BRIEF.md)
- [Literature Mapping (32 Foundation Papers)](docs/LITERATURE_MAPPING.md)
- [Ablation Study Results](docs/ABLATION_STUDY_RESULTS.md)
- [System Architecture Document (SAD)](docs/System%20Architecture%20Document%20(SAD).md)

---

## Clean Repository Structure

```
.
├── client/                     # Frontend Application (React 18 + Vite + TypeScript)
│   ├── src/
│   │   ├── components/         # 3D Digital Twin (Three.js), Telemetry Charts, Alert Feed
│   │   └── pages/              # Domain Monitoring, Cognition, Diagnostics, Legacy IoT
│   └── package.json            # Frontend dependencies
├── config/                     # Machine profiles & industrial configuration matrices
├── data/                       # Database hypertable migrations & fine-tuning corpora
├── docs/                       # Complete 27-document academic & operational suite
│   ├── figures/                # Architectural schematics & cognitive diagrams
│   ├── research_papers/        # 32 foundation literature papers (PDF)
│   ├── screenshots/            # Chronological UI validation captures (01-42)
│   └── README.md               # Canonical documentation navigation hub
├── ml/                         # Machine learning architectures, weights, and embeddings
├── mosquitto/                  # Mosquitto broker config, access control lists (ACLs)
├── notebooks/                  # Interactive exploration and research validation notebooks
├── scripts/                    # Management, migration, evaluation, and benchmark tools
│   ├── benchmark_system.py     # Latency and throughput benchmark suite
│   ├── evaluate_atlas.py       # Multi-domain evaluation harness
│   ├── generate_mqtt_passwords.py # Secure in-memory PBKDF2 Mosquitto password generator
│   ├── migrate.py              # TimescaleDB schema migration utility
│   ├── seed_dev.py             # Development database seed script
│   ├── final_verification.sh   # Comprehensive end-to-end environment validation script
│   └── setup_monitoring.sh     # Production Docker/host monitoring daemon setup
├── server/                     # Backend API & Multi-Agent Cognition Engines
│   ├── atlas/                  # Reflex, Diagnostic, and Strategic agent implementations
│   ├── backend_api.py          # Primary FastAPI endpoints, CORS, and auth middleware
│   ├── data_service.py         # Telemetry ingestion, TimescaleDB pool, and anomaly scoring
│   ├── llm_agent.py            # Grounded Gemini diagnostic assistant
│   └── mqtt_client.py          # Strict-schema Mosquitto MQTT subscriber
├── tests/                      # 218-test automated verification suite
├── docker-compose.yml          # TimescaleDB and Mosquitto broker orchestrator
└── requirements.txt            # Python backend dependencies
```

---

## Quick Start

### 1. Provision Infrastructure
Launch the TimescaleDB database and Mosquitto MQTT broker:
```bash
docker-compose up -d
```

### 2. Configure Environment
Copy `.env.example` to `.env` and verify key configurations:
```bash
cp .env.example .env
```
Ensure you generate a secure 32-byte JWT secret:
```bash
openssl rand -hex 32
```

#### Required Environment Variables:
- `JWT_SECRET_KEY`: Server fails loud if missing or empty.
- `DATABASE_URL`: Connection URI to TimescaleDB (e.g. `postgresql://dtwin:your_secure_password@localhost:5433/digital_twin`).
- `ADMIN_PASSWORD_HASH` / `OPERATOR_PASSWORD_HASH`: Required for seeding development accounts.
- `GEMINI_API_KEY`: Required when `GEMINI_AGENT_ENABLED=true`.

### 3. Run Migrations & Seed Data
Initialize database tables, hypertables, and default roles:
```bash
python scripts/migrate.py
python scripts/seed_dev.py
```

### 4. Start the Backend
```bash
# On Windows PowerShell
$env:PYTHONPATH="."
python server/integrated_server.py
```

### 5. Launch the Frontend
```bash
cd client
npm install
npm run dev
```
Navigate to `http://localhost:5173` to access the interactive 3D digital twin cockpit.

---

## Verification & Testing

The system is validated by an automated **218-test test suite** covering API RBAC, MQTT boundary schemas, TimescaleDB connection pools, cognition engines, domain adaptation, and LLM safety safeguards:

```bash
# Run the complete test suite
python -m pytest tests/ -q
```

To run end-to-end environment verification:
```bash
bash scripts/final_verification.sh
```

---

## Security & Governance

- **Credential Hygiene**: MQTT broker credentials are generated using memory-only PBKDF2 hashing (`scripts/generate_mqtt_passwords.py`) without plaintext disk persistence.
- **Session Security**: HttpOnly, SameSite=Strict, Secure cookies with custom header anti-CSRF protections and `slowapi` rate limiting.
- **Network Boundaries**: Least-privilege MQTT access control lists (ACLs) enforce write-only topics for edge machinery.

See [SECURITY.md](SECURITY.md) for vulnerability reporting and compliance disclosures.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
