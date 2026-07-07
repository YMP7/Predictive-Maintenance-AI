# AI Agent Testing and Validation Document
## Verified Test Scope and Remaining Validation Work

**Validated against test files:** June 21, 2026  
**Current automated result:** 29 tests passed

## 1. Purpose

This document records what the repository actually tests. It separates passing automated validation from proposed future tests that require field data, external providers, physical hardware, or user studies.

## 2. Automated Test Inventory

| File | Scope |
|---|---|
| `test_suite.py` | Simulator, detector, RUL, alert severity, agent caching and validation |
| `test_integration.py` | DataService simulation lifecycle, telemetry, and machine status |
| `test_ai_pipeline.py` | Four-machine pipeline, result schema, alert schema, and <100 ms per reading |
| `test_performance.py` | Average/max processing latency and synthetic memory growth |
| `test_api.py` | Health, machine listing, 404, 422, and API-key contracts |

Run the full suite:

```bash
python -m pytest test_suite.py test_integration.py test_ai_pipeline.py test_performance.py test_api.py -q -p no:cacheprovider
```

Expected result at the validation date:

```text
29 passed
```

## 3. Unit Validation

### 3.1 Sensor Simulator

Verified:

- Machine ID and fault mode initialization
- Timestamp, vibration, temperature, current, and status fields
- Numeric temperature/current values and vibration RMS

### 3.2 Fault Detector

Verified:

- Normal readings return `Normal` and no issues
- Critical vibration creates a non-normal fault and critical issue
- Missing/non-numeric required values are rejected through the AI-agent path

Current expected normal result is `Normal`, not `Unknown`.

Additional detector cases should be added when thresholds or classification precedence change.

### 3.3 RUL Estimator

Verified:

- Fewer than 10 readings returns `Insufficient Data` and `None`
- Sufficient readings produce a numeric RUL
- History remains bounded at the configured maximum

The stable prototype result is 100 days, not 365 days. This value is a demonstration constant rather than a validated lifetime estimate.

### 3.4 Alert Generator

Verified RUL severity bands:

- 2 days -> Critical
- 5 days -> High
- 8 days -> Medium

Fault-alert severity is also exercised by the pipeline tests.

### 3.5 AI Agent

Verified:

- Component initialization
- Complete result fields
- Health status is derived from detected issues rather than trusted from input
- Latest status is cached and retrievable by machine ID
- All cached machine statuses can be retrieved
- Missing required sensor values raise `ValueError`

## 4. Integration Validation

`test_integration.py` verifies:

- Simulation starts and reports running state
- Telemetry is generated and cached
- Dashboard summary includes configured machines
- Machine status includes health, RUL, and metadata
- Simulation stops cleanly

`test_ai_pipeline.py` processes 50 iterations across four machines, for 200 total readings. It validates result and alert schemas and checks each processing call against the 100 ms budget.

## 5. REST API Validation

`test_api.py` uses FastAPI `TestClient`; it does not require a listening network port.

Verified:

- `/health` returns HTTP 200 and `healthy`
- `/api/machines` returns four configured machines
- Unknown machine status, telemetry, trends, and alerts return HTTP 404
- Invalid limits and simulation intervals return HTTP 422
- Control endpoints reject missing/wrong API keys when `API_KEY` is configured
- A valid `X-API-Key` allows fault injection

The deployed API listens on port 8000 by default, not 3000.

## 6. Performance Validation

Current automated thresholds:

| Metric | Automated threshold |
|---|---|
| Average processing latency over 100 readings | < 100 ms |
| Maximum processing latency over 100 readings | < 500 ms |
| Each pipeline reading | < 100 ms |
| Process memory growth over 4,000 synthetic readings | < 100 MB |

These are short synthetic benchmarks. They do not establish 24-hour memory stability, production throughput, or performance on an edge device.

## 7. Docker Validation

The production image and Compose deployment were manually verified on June 21, 2026:

- Image `ai-digital-twin:latest` built successfully
- Container reached Docker `healthy` state
- `/health` and `/dashboard` returned HTTP 200
- Simulation reported running
- SQLite telemetry persisted across container restart
- Runtime dependencies imported successfully
- Monitoring shell script passed Bash syntax validation

Repeat with:

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health
```

## 8. Frontend Validation

TypeScript validation:

```bash
cd client
node node_modules/typescript/bin/tsc -b
```

Production build:

```bash
node node_modules/vite/bin/vite.js build
```

The direct Node entrypoints avoid Windows command-shim issues caused by the `&` character in the workspace path.

## 9. Not Yet Validated

The following must not be reported as passing or production-ready:

- >90% fault-detection accuracy
- <5% false-positive rate
- <20% RUL MAPE
- Confidence correlation >0.8
- Raw-vibration FFT or feature-extraction correctness
- 100-machine stress testing
- 24-hour or longer endurance testing
- Physical sensor and ROS2 integration
- Bhashini translation quality
- Firebase/cloud synchronization
- Live Twilio and SMTP delivery using production credentials
- Operator UAT or satisfaction metrics
- Automatic model training, CI/CD, or coverage >80%

The repository has no labeled fault dataset or known-failure RUL dataset, so accuracy and MAPE cannot yet be calculated honestly.

## 10. Required Future Test Data

For fault-classification validation:

- Labeled normal, bearing, misalignment, overheating, and electrical samples
- Machine and operating-regime metadata
- Separate machines/time periods for train and test data
- Confirmed maintenance outcomes

For RUL validation:

- Run-to-failure or censored lifetime histories
- Sampling interval and operating load
- Component replacement timestamps
- Clear failure threshold and remaining-time ground truth

## 11. Recommended Next Tests

1. Add deterministic unit cases for all fault classes and every configured machine.
2. Add alert-handler tests for cooldown, bounded history, channel isolation, and localization.
3. Add temporary-database tests for restart persistence.
4. Add live-server HTTP tests against the Docker container.
5. Add a 1-24 hour endurance test with memory and database growth reporting.
6. Add provider sandbox tests for Twilio and SMTP only when test credentials are available.
7. Add accuracy tests only after versioned labeled datasets exist.

## 12. Test Quality Rules

- Tests must contain assertions and fail on incorrect behavior.
- Randomized simulator tests should assert stable contracts, not exact random values.
- Tests that start a service must stop it in cleanup.
- External provider tests must be marked and disabled by default.
- Performance tests should record platform details when used for acceptance decisions.
- Documentation metrics must link to a reproducible test command and dataset.

## 13. CI Status

No GitHub Actions or other CI workflow is currently present in the repository. The earlier sample workflow and `tests/unit`, `tests/integration`, and `tests/accuracy` directory structure were design proposals, not implemented assets.

A future CI workflow should run syntax checks, the five current test files, TypeScript compilation, and a Docker build.
