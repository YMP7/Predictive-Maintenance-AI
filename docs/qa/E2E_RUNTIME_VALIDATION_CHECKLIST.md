# ATLAS Live End-to-End Runtime Validation Checklist

**Project:** ATLAS — An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems  
**Document Type:** Live Operational Verification & Demo Protocol  
**Date:** 2026-09-20  
**Scope:** Bottom-up end-to-end runtime validation across infrastructure (L0), services (L1), 4 heterogeneous domains (L2), cognition pipeline (L3), agent safeguards & human confirmation gate (L4), and unified frontend UI (L5).

---

## Architecture Layer Progression

```
[ L5: Unified UI ]         Vite/React Dashboard (Port 3000) + Three.js 3D Digital Twin + Agent Chat
         ▲
[ L4: Safeguards & RBAC ]  DEF-012a 3-Tier Grounding Gate + Human Confirmation Gate (/approve)
         ▲
[ L3: Cognition & AMKB ]   Attention-LSTM RUL + pgvector AMKB Memory + Occlusion Explainability
         ▲
[ L2: 4-Domain Telemetry ] C-MAPSS (FD001) | Milling (M001-M004) | Laptop (psutil) | Mobile (3-Tier)
         ▲
[ L1: Unified Server ]     FastAPI Lifespan (Port 8000) + Background Ingestion & Dispatcher
         ▲
[ L0: Infrastructure ]     TimescaleDB (Port 5433) + Mosquitto MQTT (Port 1883) + Auth Fixtures
```

---

## Phase 0: Pre-Flight & Infrastructure Verification (L0)

| Step | Component | Verification Action | Expected Ground Truth | Pass Criteria |
|---|---|---|---|---|
| **0.1** | **TimescaleDB & pgvector** | `docker ps --filter "name=timescaledb"` | Container `timescaledb` status `healthy`, ports `0.0.0.0:5433->5432/tcp`. | Docker healthcheck passes. |
| **0.2** | **TimescaleDB Extensions** | Query via `python -c "from server.database import pool; ..."` | `timescaledb` and `vector` extensions loaded in `digital_twin` database. | No connection error; hypertable & vector index active. |
| **0.3** | **MQTT Broker (Mosquitto)** | Run broker container: `docker-compose up -d mosquitto` | Container starts, binds `0.0.0.0:1883`, loads hashed `pwfile`. | Port 1883 open; accepts auth from `backend_service:backend_secret`. |
| **0.4** | **MQTT Credential Guard** | Verify `.gitignore` and `tests/test_mqtt.py` | `pwfile.raw` untracked by git; PBKDF2 `$7$` password format. | `test_plaintext_password_files_not_tracked_in_git` PASS. |
| **0.5** | **Environment Configuration** | Inspect `.env` | `DATABASE_URL` pointing to `localhost:5433`, `JWT_SECRET_KEY` set, `GEMINI_API_KEY` loaded, `CORS_ORIGINS=http://localhost:3000`. | All required env vars non-empty. |

---

## Phase 1: Unified Server Boot & API Routing (L1)

| Step | Component | Verification Action | Expected Ground Truth | Pass Criteria |
|---|---|---|---|---|
| **1.1** | **FastAPI Lifespan Boot** | `python server/integrated_server.py` | Lifespan starts: initializes AMKB, World Models, Decision Graph, 4 adapters, and fleet simulator. | Logs: `[Lifespan] Started`, binds `http://0.0.0.0:8000`. |
| **1.2** | **Health Endpoint** | `curl -s http://localhost:8000/health` | `{"status": "healthy", ...}` | HTTP 200 within < 50ms. |
| **1.3** | **Unified API Domain Route Check (DEF-008 Guard)** | `curl -s http://localhost:8000/api/models/summary` | Lists all trained domain encoders: `cmapss`, `milling`, `laptop`, `mobile` (not zero-shot fallback). | HTTP 200; `is_trained: true` for active encoders. |
| **1.4** | **Frontend Dev Server** | `npm run dev` (in `client/`) | Vite starts on `http://localhost:3000`, proxy configured for `/api` $\rightarrow$ `8000`. | HTTP 200 on `http://localhost:3000`. |

---

## Phase 2: Telemetry Ingestion — Phase A IoT Fleet & Phase B 4 ATLAS Domains (L2)

### 2A. Phase A IoT Digital Twin Prototype Fleet (4 Physical Machines)
*Legacy operational baseline: 4 industrial machines simulated via internal DataService and ingested via MQTT topic `machines/{id}/telemetry`.*

| Step | Machine ID | Machine Type | Sensor Channels | Ground Truth / Target | Pass Criteria |
|---|---|---|---|---|---|
| **2A.1** | **M001** | Lathe (Section A) | 4 channels: `vibration` (mm/s), `temperature` (°C), `current` (A), `acoustic` (dB) | Baseline telemetry stored at 1 Hz in TimescaleDB `sensor_readings`. | Active hypertable inserts; readings match physical limits. |
| **2A.2** | **M002** | Pump (Section B) | 4 channels: `vibration`, `temperature`, `current`, `acoustic` | Telemetry stored at 1 Hz; flow & pressure characteristics. | Active hypertable inserts. |
| **2A.3** | **M003** | Drill (Section C) | 4 channels: `vibration`, `temperature`, `current`, `acoustic` | Telemetry stored at 1 Hz; torque & rpm signatures. | Active hypertable inserts. |
| **2A.4** | **M004** | Furnace (Section D) | 4 channels: `vibration`, `temperature`, `current`, `acoustic` | Telemetry stored at 1 Hz; thermal dynamics & element current. | Active hypertable inserts. |

### 2B. Phase B ATLAS 4 Heterogeneous Cognition Domains
*ATLAS Cognition Layer: multi-domain adapters streaming NormalizedReadings through `DomainService`.*

| Step | Domain ID | Machine / Unit ID | Ingestion Mechanism | Feature Vector Architecture | Pass Criteria |
|---|---|---|---|---|---|
| **2B.1** | **`cmapss`** | `unit_1` ... `unit_20` | C-MAPSS FD001 dataset replay | **14 sensor channels** (`s2`, `s3`, `s4`, `s7`, `s8`, `s9`, `s11`, `s12`, `s13`, `s14`, `s15`, `s17`, `s20`, `s21`) | Monotonic cycle progression; valid degradation curve. |
| **2B.2** | **`laptop`** | `laptop_local` (LAPTOP-DEV) | Real-time local OS `psutil` adapter | **5 canonical model features** (`battery_percent`, `cpu_usage`, `disk_usage`, `is_charging`, `memory_usage`) | Live dynamic telemetry reflecting host workstation load. |
| **2B.3** | **`mobile`** | `mobile_device_1` (Wi-Fi), `mobile_device_2` (USB) | 3-Tier adapter (Termux HTTP $\rightarrow$ ADB USB $\rightarrow$ Synthetic) | **5 canonical model features** (`battery_current`, `battery_level`, `battery_temp`, `cpu_usage`, `memory_used_percent`) extracted from 16 raw/extended hardware sensors (IMU, gyro, light, prox, mag) | Clean tier resolution; 5-channel model vector in $[0.0, 1.0]$. |
| **2B.4** | **`server`** | `srv_node_01` | Cluster node SSH / simulation adapter | **5 canonical model features** (`cpu_usage`, `disk_usage`, `gpu_utilization`, `memory_usage`, `network_io_rate`) | Multi-tenant compute node telemetry stream active. |

---

## Phase 3: Machine Cognition, Anomaly Detection & Explainability (L3)

| Step | Component | Verification Action | Expected Output | Pass Criteria |
|---|---|---|---|---|
| **3.1** | **RUL Prediction (Attention-LSTM)** | Check `/api/machines/{id}/predictions` | Estimated Remaining Useful Life (cycles/hours) with non-negative clamp (`torch.clamp(min=0)` per DEF-001). | RUL $\ge 0.0$; confidence score in `[0.0, 1.0]`. |
| **3.2** | **AMKB Vector Retrieval** | Check `/api/atlas/amkb/{machine_id}/similar` | Top-$k$ nearest historical failure patterns retrieved from TimescaleDB pgvector using `<=>` cosine distance. | Cosine similarity scores calibrated between 0.0 and 1.0 (DEF-009/010). |
| **3.3** | **Explainability Attribution** | Check `/api/machines/{id}/explanation` | Occlusion-based feature attribution rankings (identifying root-cause sensor channel). | Ranked list of sensor contributions with delta-score. |
| **3.4** | **Decision Graph & Cost Matrix** | Trigger severe degradation reading | Cost-ranked maintenance actions (Inspect, Replace Spindle, Coolant Flush) with deterministic tie-breaker (DEF-004). | Highest utility action selected; safety overrides enforced. |

---

## Phase 4: Agent Safeguards, DEF-012a/b Security Gates & Human Approval (L4)

| Step | Security Boundary | Verification Trigger | Observable Response | Pass Criteria |
|---|---|---|---|---|
| **4.1** | **LLM Agent Diagnostics** | Chat prompt: *"Analyze M001 health and telemetry"* | Gemini agent calls `query_telemetry` and `get_recent_alerts`; returns domain-restricted diagnostic response. | Tool round completes $\le 3$ iterations; output restricted to maintenance domain. |
| **4.2** | **DEF-012a (Taxonomy Enum Exact-Match Gate)** | Agent attempts `create_work_order` citing real vibration alert ID with mismatched `fault_type="coolant_pressure"` | Intercepted at Layer 2: `"Rejected: Grounding check failed. Declared fault_type 'coolant_pressure' does not match grounding alert fault_type 'vibration_high'."` | Rejection error returned; logged to `work_order_audit_log`; 0 rows inserted into `work_orders`. |
| **4.3** | **DEF-012b (Action Plausibility Allow-List Gate)** | Agent attempts `create_work_order` declaring `fault_type="vibration_high"` (matching alert), but with implausible action `"Flush coolant loop and replace valve"` | Intercepted at Layer 3: `"Rejected: Plausibility check failed. Work order action 'Flush coolant loop and replace valve' does not contain recognized corrective action vocabulary for fault_type 'vibration_high'."` | Rejection error returned; logged to `work_order_audit_log`; 0 rows inserted into `work_orders`. |
| **4.4** | **Legitimate Grounded Work Order** | Agent calls `create_work_order` with valid alert ID + `fault_type="vibration_high"` + action `"Inspect and balance spindle rotor"` | Accepted; status set to `Pending Approval`; `created_by` stamped strictly server-side as `'agent:atlas'`. | Stored in DB with status `Pending Approval`; audit log success. |
| **4.5** | **Human Confirmation Gate (RBAC Dual-Direction)** | Call `POST /api/work-orders/{id}/approve` | **Viewer Token:** `403 Forbidden`.<br>**Operator/Admin Token:** `200 OK`, transitions status from `Pending Approval` to `Open`. | Both directions proven: unauthorized roles physically blocked; authorized roles succeed. |

---

## Phase 5: Unified Frontend UI & 3D Digital Twin (L5)

| Step | Component | Verification Action | Expected Visual & Functional Behavior | Pass Criteria |
|---|---|---|---|---|
| **5.1** | **Unified Shell & Dashboard** | Open `http://localhost:3000` | Dark-mode industrial interface loads with zero console errors; status badges show "Live". | No React render errors or 404 assets. |
| **5.2** | **Domain Ticker Bar** | Click between 4 tabs: Turbofan, Milling, Laptop, Mobile | Smooth transition; header stats and domain parameters update instantaneously. | Active domain switches without state bleed. |
| **5.3** | **3D Digital Twin Canvas** | View 3D Milling / Spindle Model (Three.js) | Interactive 3D machine renders with lighting, rotation, and dynamic vibration/thermal heatmap overlay. | 60 FPS WebGL rendering; responds to drag/zoom. |
| **5.4** | **Real-Time Telemetry Charts** | Observe live chart cards | Recharts time-series streams continuously appending points every interval (1–2s). | Smooth streaming without memory accumulation. |
| **5.5** | **AMKB Explainability Drawer** | Click "Explain Diagnosis" on an alert | Radar/bar chart showing feature attributions; top-3 AMKB neighbor case citations displayed. | Grounded citations match active anomaly. |
| **5.6** | **Agent Chat & Work Order Card** | View work orders tab / chat interface | Pending Approval work order displayed as an interactive card with "Approve" (Operator only) and "Reject" buttons. | Clicking "Approve" triggers API call and marks order as `Open`. |

---

## Verification Execution Summary Table

| Phase | Description | Key Artifact / Endpoint | Status |
|---|---|---|---|
| **Phase 0** | Infrastructure & Auth | TimescaleDB (5433), Mosquitto (1883), `.env` | Ready for run |
| **Phase 1** | Server Boot & Routing | `server/integrated_server.py`, `localhost:8000/health` | Ready for run |
| **Phase 2** | 4-Domain Telemetry | C-MAPSS, Fleet M001-M004, Laptop, Mobile | Ready for run |
| **Phase 3** | Cognition & Explainability | Attention-LSTM RUL, AMKB pgvector, Occlusion | Ready for run |
| **Phase 4** | Agent & Security Gates | DEF-012a 3-tier validation, `/approve` RBAC | Ready for run |
| **Phase 5** | Frontend & 3D Twin | `http://localhost:3000`, Three.js canvas, Chat | Ready for run |
