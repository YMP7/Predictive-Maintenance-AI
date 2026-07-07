# AI Agent Implementation Guide
## Current Prototype and Extension Roadmap

**Validated against code:** June 21, 2026

## 1. Implementation Status

The current AI agent is a rule-based predictive-maintenance prototype. It processes simulated vibration, temperature, and current readings, classifies known fault patterns, estimates a simulation-oriented RUL, generates alerts, persists history in SQLite, and exposes the results through FastAPI and a React dashboard.

Implemented now:

- Four-machine sensor simulation
- Machine-specific threshold detection
- Pattern-based fault classification
- Linear-trend RUL estimation
- Alert cooldown, localization, routing, and provider hooks
- SQLite telemetry and alert persistence
- REST API and dashboard
- Docker deployment and health checks

Planned, not implemented:

- Trained Random Forest, Isolation Forest, or LSTM models
- FFT, kurtosis, skewness, and spectral feature extraction
- Bhashini translation
- Firebase/cloud synchronization
- ROS2 or physical sensor adapters
- Human feedback and automated model retraining

## 2. Runtime Components

| File | Responsibility |
|---|---|
| `sensor_simulator.py` | Generates normal and injected-fault readings |
| `ai_agent.py` | Detection, RUL, alerts, recommendations, latest-status cache |
| `alert_handler.py` | Cooldown, localization, channel routing, delivery |
| `data_service.py` | Simulation lifecycle, caches, SQLite, dashboard summaries |
| `backend_api.py` | FastAPI routes and optional API-key protection |
| `integrated_server.py` | Lifecycle management and React SPA serving |
| `data_sync.py` | In-process publish/subscribe utility; not a WebSocket service |
| `config/machines.json` | Machine metadata and warning/critical thresholds |

## 3. Processing Pipeline

```text
SensorSimulator
    -> AIAgent input validation
    -> FaultDetector
    -> RULEstimator history update
    -> AlertGenerator
    -> AIAgent latest-status cache
    -> DataService memory cache and SQLite
    -> AlertHandler
    -> REST API and dashboard
```

Required values are `vibration.rms`, `temperature`, and `current`. They must be finite numeric values.

## 4. Fault Detection

Thresholds come from `config/machines.json`. For each metric, values above the configured warning threshold create a warning issue, while values above the critical threshold create a critical issue.

Classification order:

1. No issues -> `Normal`
2. Vibration above warning and temperature below warning -> `Misalignment`
3. Temperature and current above warning with vibration below critical -> `Overheating`
4. Vibration and temperature above warning -> `Bearing Wear`
5. Current above warning -> `Electrical Fault`

Health status is separate from fault type:

- No detected issues -> `Normal`
- Warning issues only -> `Warning`
- Any critical issue -> `Critical`

This detector is deterministic and explainable, but it is not a trained statistical model and has no calibrated classification confidence.

## 5. RUL Estimation

The degradation score is:

```text
score = 0.5 * (vibration_rms / 5.0)
      + 0.3 * ((temperature - 45) / 30)
      + 0.2 * ((current - 2.5) / 2.0)
```

The score is clipped to `[0, 1]`. The latest 1,000 scores are retained per machine.

After at least 10 readings, NumPy linear regression estimates the degradation slope. The prototype then applies these rules:

- Degradation >= 0.8 -> RUL 0, confidence 0.95
- Non-positive slope -> RUL 100, confidence 0.80
- Positive slope -> extrapolate steps to 0.8 and multiply by 0.14 simulation days per step
- Confidence is bounded to 0.50-0.95 using trend R-squared

This scaling is for demonstration. Before field deployment, RUL must be calibrated against real elapsed time and known failures.

## 6. Alerts and Recommendations

Fault alerts are generated whenever the detector returns a non-normal fault. RUL warnings are generated below 10 days.

| Condition | Alert severity |
|---|---|
| Any critical sensor issue | Critical |
| Multiple warning issues | High |
| One warning issue | Medium |
| RUL under 3 days | Critical |
| RUL 3-6 days | High |
| RUL 7-9 days | Medium |

Default channel routing:

| Severity | Channels |
|---|---|
| Critical | Dashboard, log, SMS, email, voice |
| High | Dashboard, log, SMS, email |
| Medium | Dashboard, log, email |
| Low | Dashboard, log |

`ALERT_COOLDOWN` suppresses repeated alerts for the same machine and fault type. `ALERT_LANGUAGES` controls which built-in translation templates are attached to an alert.

Twilio and SMTP are optional. Without credentials, delivery is recorded as a simulation in logs.

## 7. Data Service and Persistence

`DataService` owns the simulator, AI agent, background thread, and current dashboard state.

Memory limits:

- Telemetry: 1,000 readings per machine
- Alerts: 500 recent alerts
- RUL history: 1,000 scores per machine
- Delivered alert history: 1,000 entries

SQLite tables:

- `telemetry`: timestamp, vibration axes/RMS, temperature, current, status
- `alerts`: timestamp, machine, type, severity, message, fault type

On startup, the service reloads up to 1,000 telemetry records per machine and 500 alerts. The RUL estimator does not currently rebuild its degradation history from SQLite, so RUL collection restarts after process restart.

## 8. API and Security

The FastAPI application provides health, status, dashboard, machine, telemetry, trends, alerts, simulation control, and fault injection routes.

Set a non-empty `API_KEY` to protect control routes with `X-API-Key`. Read endpoints remain public in the prototype.

Set `CORS_ORIGINS` to a comma-separated allowlist for a separately hosted frontend. With the default `*`, credentialed browser CORS is disabled.

Production security still requires:

- HTTPS through a reverse proxy or ingress
- Real identity and role-based authorization
- Secret storage outside source files
- Database backup and retention policy
- Network restrictions around control endpoints

## 9. Frontend Integration

The React client polls dashboard and machine endpoints. It uses same-origin API paths by default so the Docker deployment can serve UI and API on port 8000.

For separate development servers:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

Do not place production secrets in `VITE_*` variables because browser bundles expose them.

## 10. Configuration

Machine thresholds are configured in `config/machines.json`:

```json
{
  "machines": {
    "M001": {
      "name": "Lathe Machine",
      "type": "Lathe",
      "location": "Section A",
      "thresholds": {
        "vibration": {"warning": 1.5, "critical": 3.0},
        "temperature": {"warning": 60, "critical": 75},
        "current": {"warning": 3.5, "critical": 4.5}
      }
    }
  }
}
```

The runtime does not read `rul_model`, adaptive threshold, or model-file fields from this JSON.

Environment configuration:

```dotenv
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=
CORS_ORIGINS=*
SIMULATION_ENABLED=true
SIMULATION_INTERVAL=1
ALERT_COOLDOWN=300
ALERT_LANGUAGES=en,hi,te,ta,mr
LOG_LEVEL=INFO
LOG_FILE=./logs/agent.log
```

## 11. Local Operation

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Build the frontend:

```bash
cd client
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build
```

Run the integrated server:

```bash
python integrated_server.py
```

Open `http://localhost:8000`.

## 12. Docker Operation

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health
```

The Compose deployment provides persistent volumes for `/app/data` and `/app/logs`, a Docker health check, and `unless-stopped` restart behavior.

## 13. Validation

```bash
python -m pytest test_suite.py test_integration.py test_ai_pipeline.py test_performance.py test_api.py -q -p no:cacheprovider
```

Current automated validation covers component behavior, end-to-end simulation, API contracts, API-key enforcement, processing latency, memory growth, and status caching.

## 14. Recommended Extension Order

1. Collect labeled field data and define ground-truth failure events.
2. Add feature extraction and dataset versioning.
3. Establish baseline accuracy and RUL error metrics.
4. Train models behind the existing `AIAgent` interface.
5. Add model versioning and rule-based fallback.
6. Integrate physical sensors and operator feedback.
7. Add cloud synchronization only after local reliability is proven.
