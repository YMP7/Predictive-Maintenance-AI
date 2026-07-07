# AI Agent API Reference and Integration Guide
## Validated Prototype Contract

**Validated against:** `ai_agent.py`, `data_service.py`, `backend_api.py`, `alert_handler.py`, and the React client  
**Validation date:** June 21, 2026  
**API version:** 1.0.0

## 1. Scope

This document describes the API that is implemented in the current prototype. The active system provides:

- Rule-based fault detection using machine-specific thresholds
- Linear-trend Remaining Useful Life (RUL) estimation
- Alert generation, cooldown, localization, and severity-based routing
- SQLite persistence for telemetry and alerts
- FastAPI REST endpoints
- A React dashboard served by the integrated server
- Optional Twilio SMS/voice and SMTP email delivery

Trained ML models, Bhashini, Firebase, ROS2, and cloud synchronization are roadmap items and are not part of the current runtime API.

## 2. Sensor Reading Contract

The AI agent accepts this shape:

```json
{
  "machine_id": "M001",
  "timestamp": "2026-06-21T10:00:00Z",
  "vibration": {
    "x": 0.3,
    "y": 0.4,
    "z": 0.2,
    "rms": 0.54
  },
  "temperature": 50.0,
  "current": 2.5
}
```

`vibration.rms`, `temperature`, and `current` must be finite numbers. Invalid or missing values raise `ValueError` in the Python API.

## 3. Core Python API

### 3.1 `FaultDetector`

```python
from ai_agent import FaultDetector

detector = FaultDetector()
fault_type, issues = detector.detect_fault(reading)
```

`detect_fault(reading: Dict) -> Tuple[str, List[str]]`

Possible fault types:

- `Normal`
- `Misalignment`
- `Overheating`
- `Bearing Wear`
- `Electrical Fault`

Thresholds are loaded from `config/machines.json`. Unknown machine IDs use the M001-style default thresholds.

### 3.2 `RULEstimator`

```python
from ai_agent import RULEstimator

estimator = RULEstimator()
estimator.update_degradation("M001", reading)
rul = estimator.estimate_rul("M001")
```

Methods:

- `update_degradation(machine_id, reading) -> None`
- `estimate_rul(machine_id) -> Dict`

RUL response:

```json
{
  "rul_days": 14,
  "confidence": 0.85,
  "status": "Degrading"
}
```

Behavior:

- Fewer than 10 readings: `rul_days` is `null` and status is `Insufficient Data`
- Stable/non-increasing trend: prototype RUL is 100 days
- Current degradation at or above 0.8: RUL is 0 days
- History is bounded to the latest 1,000 degradation scores per machine

The day conversion is simulation-oriented, not a calibrated physical lifetime model.

### 3.3 `AlertGenerator`

```python
from ai_agent import AlertGenerator

generator = AlertGenerator()
alerts = generator.generate_alerts("M001", detector, estimator, reading)
```

Alert types:

- `Fault Detection`
- `RUL Warning`

RUL severity mapping:

| RUL | Severity |
|---|---|
| Under 3 days | Critical |
| 3-6 days | High |
| 7-9 days | Medium |
| 10 days or more | No RUL warning |

### 3.4 `AIAgent`

```python
from ai_agent import AIAgent

agent = AIAgent()
result = agent.process_reading(reading)
```

`process_reading(reading: Dict) -> Dict` returns:

```json
{
  "machine_id": "M001",
  "timestamp": "2026-06-21T10:00:00Z",
  "status": "Warning",
  "fault_type": "Misalignment",
  "detected_issues": ["Elevated Vibration (Warning)"],
  "rul_days": null,
  "rul_confidence": 0.0,
  "alerts": [],
  "recommendation": "Perform shaft alignment correction procedures."
}
```

Status is derived from detected issues:

- No issues: `Normal`
- One or more warning issues: `Warning`
- Any critical issue: `Critical`

Status retrieval methods:

- `get_machine_status(machine_id) -> Optional[Dict]`
- `get_all_machine_statuses() -> Dict[str, Dict]`

These methods return the latest analyses processed by that `AIAgent` instance.

## 4. Data Service API

Use the singleton service:

```python
from data_service import get_data_service

service = get_data_service()
```

Implemented methods:

| Method | Description |
|---|---|
| `start_simulation(interval=1.0)` | Starts the background simulation loop |
| `stop_simulation()` | Stops and joins the simulation thread |
| `get_machine_status(machine_id)` | Returns current/default machine status or `None` |
| `get_all_machines_status()` | Returns statuses for all configured machines |
| `get_all_machines_info()` | Returns configured machine metadata |
| `get_machine_telemetry(machine_id, limit=100)` | Returns recent cached telemetry |
| `get_machine_trends(machine_id)` | Returns vibration, temperature, and current summaries |
| `get_recent_alerts(limit=50)` | Returns recent alerts |
| `get_alerts_by_machine(machine_id, limit=20)` | Returns alerts for one machine |
| `get_dashboard_summary()` | Returns dashboard aggregates and machine statuses |

Telemetry is cached in memory up to 1,000 readings per machine and persisted in `data/digital_twin.db`. The in-memory alert list is capped at 500 entries; persisted alert history remains in SQLite.

## 5. REST API

Default local URL: `http://localhost:8000`

### 5.1 Health and System

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health, timestamp, and API version |
| GET | `/api/status` | Service and simulation status |

### 5.2 Dashboard and Machines

| Method | Path | Description |
|---|---|---|
| GET | `/api/dashboard/summary` | Dashboard aggregate |
| GET | `/api/machines` | Machine metadata |
| GET | `/api/machines/{machine_id}/status` | Current machine status |
| GET | `/api/machines/{machine_id}/telemetry?limit=100` | Telemetry, limit 1-1000 |
| GET | `/api/machines/{machine_id}/trends` | Recent trend statistics |

Unknown machines return HTTP 404.

### 5.3 Alerts

| Method | Path | Description |
|---|---|---|
| GET | `/api/alerts/recent?limit=50` | Recent alerts, limit 1-500 |
| GET | `/api/alerts/machine/{machine_id}?limit=20` | Machine alerts, limit 1-500 |

### 5.4 Control Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/simulation/start?interval=1.0` | Starts simulation; interval must be > 0 and <= 3600 |
| POST | `/api/simulation/stop` | Stops simulation |
| POST | `/api/machines/{machine_id}/fault` | Injects or resets a simulated fault |

Fault request body:

```json
{
  "fault_mode": "bearing_wear"
}
```

Valid modes: `normal`, `bearing_wear`, `misalignment`, `overheating`, and `electrical_fault`.

If `API_KEY` is non-empty, control endpoints require:

```http
X-API-Key: configured-value
```

### 5.5 HTTP Errors

| Status | Meaning |
|---|---|
| 400 | Invalid fault mode |
| 401 | Missing or invalid API key |
| 404 | Machine or API route not found |
| 422 | Invalid query parameter or request body |

## 6. Frontend Integration

The production frontend uses same-origin requests by default. For a separately hosted frontend, set:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

Example:

```javascript
const response = await fetch('/api/dashboard/summary');
if (!response.ok) throw new Error(`HTTP ${response.status}`);
const summary = await response.json();
```

Do not embed a production API secret in `VITE_*` variables because Vite exposes them to the browser.

## 7. Alert Delivery

`AlertHandler` supports:

- Dashboard and structured log delivery
- Thread-safe queueing
- A 1,000-entry delivered-alert history
- Cooldown by `(machine_id, fault_type)`
- Severity-based channel selection
- Local translation templates for `en`, `hi`, `te`, `ta`, and `mr`
- Twilio SMS/voice when credentials and the SDK are available
- SMTP email when credentials are available

Missing external credentials cause safe log-only simulation, not a process failure.

## 8. Configuration

Important environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `API_HOST` | `0.0.0.0` | Server bind address |
| `API_PORT` | `8000` | Server port |
| `API_KEY` | empty | Optional control-endpoint key |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `SIMULATION_ENABLED` | `true` | Start simulation with integrated server |
| `SIMULATION_INTERVAL` | `1` | Seconds between cycles |
| `ALERT_COOLDOWN` | `300` | Duplicate suppression period |
| `ALERT_LANGUAGES` | `en` | Comma-separated alert languages |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FILE` | `./logs/agent.log` | Log file path |

Twilio variables: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_TO_NUMBER`.

SMTP variables: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_SSL`, `SMTP_USE_TLS`, `ALERT_EMAIL_TO`.

## 9. Verified Commands

```bash
python -m pytest test_suite.py test_integration.py test_ai_pipeline.py test_performance.py test_api.py -q -p no:cacheprovider
```

```bash
docker compose up -d --build
curl http://localhost:8000/health
```

## 10. Current Limitations

- RUL is a simulation heuristic, not a field-calibrated prediction
- No trained fault-classification model is loaded
- No Bhashini, Firebase, ROS2, ONNX, TensorRT, or operator-feedback pipeline exists
- No HTTPS termination is included; use a reverse proxy in production
- Live Twilio/SMTP delivery requires external credentials and provider validation
