# ATLAS Test Plan

**Project:** ATLAS — An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems
**Document Type:** As-Built Test Plan
**Date:** 2026-08-25
**Status:** Complete — 192 tests, 100% pass rate (confirmed live 2026-08-25)

---

## 1. Test Suite Evolution: 29 → 192

This project's test suite evolved alongside the codebase through two phases in the same repository:

### Phase A — Pre-ATLAS Prototype (commits `532615e` → `b85f427`)
The prototype-era test suite comprised **5 test files with 29 tests** covering the IoT infrastructure:
- `test_suite.py` (13 tests): Simulator, fault detector, RUL estimator, alert generator, AI agent
- `test_api.py` (10 tests): REST API endpoints, RBAC, rate limiting
- `test_integration.py` (2 tests): DataService simulation lifecycle
- `test_ai_pipeline.py` (1 test): Four-machine pipeline processing
- `test_performance.py` (2 tests): Latency and memory growth

These were later extended with `test_mqtt.py` (7 tests, Phase 5) and `test_notifications.py` (8 tests, Phase 5), bringing the pre-ATLAS total to **7 files, 43 test functions**.

> [!NOTE]
> **Import separation:** All 7 pre-ATLAS test files import exclusively from the prototype layer
> (`server.backend_api`, `server.ai_agent`, `server.sensor_simulator`, `server.data_service`,
> `server.mqtt_client`, `server.alert_handler`). None import `server.api` (the ATLAS cognition API)
> or any `server.atlas.*` module. They are a valid **regression baseline for Phase A infrastructure**
> (confirming that JWT auth, RBAC, MQTT ingestion, notification debounce, and the original AI agent
> still work), but they do not exercise any ATLAS-era cognition code paths. The ATLAS cognition
> layer (`server/api.py`, `server/atlas/*`) was extensively modified during Months 2–7 and is
> validated exclusively by the 22 ATLAS-era test files.

This phase is documented in [`AI Agent Testing and Validation Document.md`](../AI%20Agent%20Testing%20and%20Validation%20Document.md).

### Phase B — ATLAS Cognition Platform (commits `37bc4c5` → `1a53ff3`)
ATLAS added **22 new test files with 143 test functions**, bringing the total to **29 files, 186 test functions, 192 collected tests** (parametrization expands 6 additional test cases).

The pre-ATLAS tests were **carried forward unchanged** and continue to pass. They serve as a regression baseline for the underlying IoT/API infrastructure. `test_api.py` was last modified during pre-ATLAS Phase 5 (JWT/CSRF); no ATLAS-era commits touched it.

---

## 2. Test Categories & Scope

### 2.1 Unit Tests

Tests that exercise individual modules in isolation using mocks, stubs, or synthetic data:

| Test File | Tests | Subsystem | What It Validates |
|---|---|---|---|
| `test_suite.py` | 13 | Pre-ATLAS AI Agent | Simulator, fault detector, RUL estimator, alert severity, agent caching |
| `test_amkb.py` | 18 | AMKB Memory | Vector store/retrieve, cosine similarity, domain isolation, edge cases |
| `test_machine_dna.py` | 4 | Machine DNA Engine | Fingerprint computation, z-score normalization, storage/retrieval |
| `test_decision.py` | 6 | Decision Graph | Cost-weighted ranking, tie-breaker ordering, safety overrides |
| `test_explain.py` | 8 | Explainability Engine | Confidence calibration, occlusion attribution, citation grounding |
| `test_rul_bounding.py` | 7 | RUL Engine | Prediction bounds, EMA fallback, non-negativity clamp |
| `test_learning_engine.py` | 6 | Learning Engine | 3% epsilon gate, rollback invariance, audit logging |
| `test_work_order_safeguards.py` | 5 | Agent Safeguards | Volume caps, provenance checks, grounding validation |

### 2.2 Adapter Tests

Tests that verify the Machine Adapter Layer (the only domain-specific code):

| Test File | Tests | Adapter | What It Validates |
|---|---|---|---|
| `test_adapters.py` | 18 | All 4 adapters | NormalizedReading schema compliance, feature dimensions, health_index bounds |
| `test_laptop_adapter.py` | 2 | LaptopAdapter | Live psutil polling, stress score formula |
| `test_mobile_adapter.py` | 3 | MobileAdapter | Termux:API fallback, simulation mode |
| `test_server_adapter.py` | 5 | ServerAdapter | SSH transport contract, GPU/No-GPU weight sums, simulation fallback |

### 2.3 Integration Tests

Tests that exercise multi-component interactions with real or mocked services:

| Test File | Tests | Scope | What It Validates |
|---|---|---|---|
| `test_integration.py` | 2 | Pre-ATLAS DataService | Simulation lifecycle, telemetry caching |
| `test_adaptive_context.py` | 7 | Context Engine | Multi-domain WorldModel resolution, build_context end-to-end |
| `test_domain_pretraining.py` | 5 | Domain Pre-Training | Self-supervised training, non-collapse guards, deterministic seeds |
| `test_multi_domain_queries.py` | 3 | Cross-Domain API | Domain-parameterized query routing |
| `test_concurrency_ingest.py` | 2 | Concurrent Ingestion | Multi-threaded AMKB write safety |
| `test_db.py` | 6 | Database Layer | Connection pool management, schema migrations |

### 2.4 Evaluation & Regression Tests

Tests that validate empirical results, ablation correctness, and transfer study integrity:

| Test File | Tests | Scope | What It Validates |
|---|---|---|---|
| `test_ablations.py` | 5 | Ablation Suite | All 4 ablations produce valid, consistent results |
| `test_transfer_study.py` | 9 | Transfer Study | MMD computation, NTI calculation, pairwise cosine matrices |
| `test_evaluation_cli.py` | 7 | Evaluation Harness | InMemoryAMKB ↔ pgvector equivalence (< 10⁻⁵), scorecard generation |

### 2.5 API & System Tests

| Test File | Tests | Scope | What It Validates |
|---|---|---|---|
| `test_api.py` | 10 | REST API | Health, machine listing, 404/422, JWT auth, CSRF |
| `test_phase8_agent.py` | 10 | Agentic AI | Tool execution, prompt injection resistance, provenance isolation |
| `test_mqtt.py` | 7 | MQTT Ingestion | Schema validation, ACL enforcement |
| `test_notifications.py` | 8 | Alert Handler | Debounce, fan-out, fail-loud credentials |

### 2.6 Performance & Resource Tests

| Test File | Tests | Scope | What It Validates |
|---|---|---|---|
| `test_performance.py` | 2 | Pre-ATLAS Latency | < 100 ms processing, < 100 MB memory growth |
| `test_ai_pipeline.py` | 1 | Pre-ATLAS Pipeline | 200 readings across 4 machines in < 100 ms each |
| `test_benchmark.py` | 3 | ATLAS Benchmark | Stage timing, throughput thresholds |
| `test_resource_profile.py` | 4 | ATLAS Resources | RSS footprint, leak detection, concurrency metrics |

---

## 3. Entry & Exit Criteria

### Entry Criteria
- All source code changes committed to local `main` branch
- PostgreSQL / TimescaleDB / pgvector service running
- AMKB populated with C-MAPSS training data (17,731+ experiences)
- All 4 domain World Model checkpoints present in `data/models/`
- Python 3.13+ with all `requirements.txt` dependencies installed

### Exit Criteria (Pass)
- **192/192 tests pass** with `python -m pytest tests/ -v`
- **Zero failures**, zero errors (warnings are acceptable)
- All validation gates in [STRATEGY.md §6](STRATEGY.md) are satisfied

### Exit Criteria (Fail)
- Any test failure blocks release
- Any validation gate violation requires investigation before proceeding
- Connection pool thread warnings at shutdown are a known non-blocking issue (psycopg pool cleanup race)

---

## 4. Tolerance Thresholds Used in Tests

**Source:** `ATLAS_PROJECT_CONTEXT.md` §6b, `docs/REPRODUCIBILITY.md` §2

| Threshold | Value | Where Used | Purpose |
|---|---|---|---|
| RMSE validation range | [14.0, 16.5] cycles | `test_evaluation_cli.py` | Checkpoint prediction accuracy |
| PHM Score validation | ≤ 400.0 | `test_evaluation_cli.py` | Asymmetric late-prediction penalty |
| InMemory ↔ pgvector tolerance | < 10⁻⁵ | `test_evaluation_cli.py` | Zero-drift fallback equivalence |
| Cosine non-collapse guard | ≥ 0.20 | `test_domain_pretraining.py` | Self-supervised latent space quality |
| Euclidean non-collapse guard | ≥ 0.50 | `test_domain_pretraining.py` | Secondary collapse detection |
| Learning Engine epsilon | ≤ 0.97 × RMSE_active | `test_learning_engine.py` | 3% improvement promotion gate |
| Processing latency (pre-ATLAS) | < 100 ms per reading | `test_performance.py`, `test_ai_pipeline.py` | Real-time feasibility |
| Memory growth (pre-ATLAS) | < 100 MB over 4,000 readings | `test_performance.py` | Memory stability |

---

## 5. What Is Explicitly NOT Covered by Testing

The following items are **not tested** and are explicitly disclosed as limitations:

| Item | Reason |
|---|---|
| Real hardware Server-tier SSH path | ServerAdapter runs in simulation fallback; Paramiko SSH transport is implemented and contract-tested but not exercised against a live remote VM |
| Real Termux:API HTTP transport | MobileAdapter runs in simulation fallback when Termux is unavailable |
| Live Twilio/SMTP notification delivery | Test credentials not configured; notification tests use mock/log mode |
| Bhashini translation API | Pre-ATLAS roadmap item; no integration exists |
| FD002–FD004 C-MAPSS sub-datasets | Deliberately scoped to FD001 only |
| kHz-range vibration/acoustic signal processing | No high-frequency sensor domain in current adapter set |
| Multi-machine fleet-level coordination | Rejected scope item |
| Browser/UI end-to-end testing | React frontend tested via TypeScript compilation only; no Selenium/Playwright coverage |
| CI/CD pipeline execution | GitHub Actions workflow exists but is not actively exercised; all testing is local |
| Load testing beyond C=64 | Concurrency profiling stops at 64 concurrent clients |

---

## 6. Test Execution Instructions

### Full Suite
```bash
python -m pytest tests/ -v
```
Expected: 192 passed (execution time ~750s due to database integration tests)

### Quick Smoke Test (no DB-dependent tests)
```bash
python -m pytest tests/test_suite.py tests/test_adapters.py tests/test_decision.py -v
```

### ATLAS Evaluation Harness (separate from pytest)
```bash
python scripts/evaluate_atlas.py all --quick    # < 10 seconds
python scripts/evaluate_atlas.py all            # Full multi-trial
```

---

## 7. Test Responsibilities

| Role | Responsibility |
|---|---|
| Developer (solo project) | Writing tests, running full suite before each commit, maintaining pass rate |
| Evaluation Harness (`evaluate_atlas.py`) | Automated benchmark reproduction for peer reviewers and examiners |
| Future CI (not yet active) | GitHub Actions workflow defined but not exercised; manual local testing is the current process |
