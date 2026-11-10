# Title justification

**ATLAS: An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems**

Each term of the title, what it claims, the code that implements it, where to see it in the running product, and the number that backs it. A cell that cannot be backed by evidence says **FUTURE-WORK**. The same matrix, with live numbers, is the product page `/about/evidence`.

Labels: **BUILD** means delivered and checked; **FUTURE-WORK** means not delivered and not claimed.

## Matrix

| Term | Claim | Implementing components | Live evidence in the product | Quantitative evidence |
|---|---|---|---|---|
| **Adaptive** | Adapts its estimate to the machine's context and to new machines | Adaptive Context Engine `server/atlas/adaptive_context.py`; Learning Engine (batch retrain with a 3% validation gate) `server/atlas/learning_engine.py`; transfer study `server/atlas/transfer_study.py` | `/admin/cognition` panels 5 (Adaptive Context) and 10 (Learning Engine); `/admin/models` (retrain, versions) | Transfer study `data/transfer_study_results.json`: retrieval through C-MAPSS memory inflates error 8.3x (phone) and 7.1x (server) against within-domain memory, so per-domain adaptation is needed; laptop 0.89x. Retrain deltas: **1 run recorded** (rejected by the gate, RMSE 15.42 to 59.14, production untouched); a richer retrain history is **FUTURE-WORK** |
| **Machine Cognition** | Perceive, remember, predict, simulate, decide, explain, in one pipeline | World Model (Attention-LSTM, 32-dim state) `server/atlas/world_model.py`; AMKB `server/atlas/amkb.py`; Machine DNA (16-dim) `server/atlas/machine_dna.py`; RUL engine; Simulation `server/atlas/simulation.py`; Decision Graph `server/atlas/decision.py`; trace `server/cognition_trace.py` | `/admin/cognition`: all ten stages for any machine, with per-stage latency and replay of stored traces | End-to-end pipeline mean latency 21.8 ms (C-MAPSS), 6.7 ms (laptop), 6.8 ms (phone), 10.5 ms (server) `data/system_benchmark_results.json`. Ablations `data/ablation_results.json`: the full pipeline has 47.2% lower total maintenance cost than a RUL-threshold rule (3,440 to 1,817.5 cost units under the study's cost model, 0 missed failures each), at the price of 281 cycles of early replacement on 3 early-life units; AMKB grounding moves confidence from a constant 0.50 to a calibrated mean 0.035 (Spearman rho -0.509 against error) |
| **Platform** | Extensible to new machines, secured, deployable, auditable | Adapter SDK and conformance suite `docs/ADAPTER_SDK_SPEC.md`, `tests/test_adapter_conformance.py`; configurable adapter `server/adapters/configurable_adapter.py`; ingest (HTTP, WebSocket, MQTT, Modbus, CSV, manual) `server/ingest.py`, `server/platform_api.py`; RBAC; hash-chained audit `server/audit.py`; Docker `docker-compose.yml` | `/admin/onboarding` (seven-step wizard), `/admin/devices`, `/admin/users`, `/admin/diagnostics` | Adapter conformance suite **41/41 tests pass**, including the configurable adapter. pytest **440 pass**. Playwright flows 1-6 pass (`client/e2e/`), including onboarding a sensor and seeing pushed data on screen in 0.6 s. Audit chain verified intact in the database and the JSONL mirror (`scripts/audit_verify.py`) |
| **Explainable** | Every prediction comes with a reason a person can check | Explainability Engine (occlusion attribution plus AMKB-grounded justification) `server/atlas/explain.py` | "Show why" in the 3D Asset View `/assets/cmapss/<unit>`; `/admin/cognition` panel 9; AMKB evidence in `/chat` | Attribution faithfulness, deletion test on 100 FD001 test units (`scripts/attribution_faithfulness.py`, `data/attribution_faithfulness.json`): masking the top-2 attributed sensors moves RUL by 35.4 cycles against 16.8 for 2 random sensors, and beats random in 90% of units (top-3: 42.4 vs 23.3, 94%). Per-sensor attribution exists only for the 14-feature C-MAPSS layout; for laptop, phone, server and Modbus it is **FUTURE-WORK** (they get the AMKB justification only) |
| **Predictive Maintenance** | Forecasts remaining useful life and turns it into a maintenance action | RUL engine `server/atlas/rul_engine.py`; Decision Graph; work orders `server/operations_api.py`, `server/backend_api.py` | `/assets/cmapss/<unit>` (RUL band, recommended action, create work order); `/work-orders` (approve, assign, resolve); `/alarms` | NASA C-MAPSS FD001 test set, 100 units: **RMSE 15.42, MAE 11.81, PHM score 394.7** (`data/atlas_evaluation_summary.json`); five-seed mean RMSE 15.22 ± 0.30, PHM 375 ± 21.9; literature LSTM baseline (Zheng et al., 2017) RMSE 16.14, PHM 338. RUL for the Modbus pump is **FUTURE-WORK** (no trained model) |
| **Heterogeneous Machine Systems** | One pipeline across unlike machines | Adapter Layer (`server/adapters/`: C-MAPSS, laptop, mobile, server, Modbus, configurable); normalised schema; asset profiles `server/adapters/asset_profiles.py` | `/cross-domain` (every asset on one normalised scale); `/assets` (five machines in 3D) | Four domains with trained World Models (C-MAPSS, laptop, phone, server) and a fifth (Modbus motor-pump) ingested and shown with health only. Per-domain transfer metrics in `data/transfer_study_results.json` (within-domain RMSE 0.096 laptop, 0.030 phone, 0.040 server on normalised RUL) |

## How to check each number

| Number | Command | Output |
|---|---|---|
| FD001 RMSE / PHM | `python scripts/evaluate_atlas.py` | `data/atlas_evaluation_summary.json` |
| Five-seed spread | `python scripts/evaluate_multiseed.py` | see `docs/REPRODUCIBILITY.md` |
| Ablations | `python scripts/run_ablations.py` | `data/ablation_results.json`, `docs/ABLATION_STUDY_RESULTS.md` |
| Transfer study | `python scripts/run_transfer_study.py` | `data/transfer_study_results.json`, `docs/TRANSFER_STUDY_RESULTS.md` |
| Latency | `python scripts/benchmark_system.py` | `data/system_benchmark_results.json`, `docs/ATLAS_BENCHMARK.md` |
| Attribution faithfulness | `python scripts/attribution_faithfulness.py` | `data/attribution_faithfulness.json` |
| Conformance | `pytest tests/test_adapter_conformance.py` | 41 passed |
| Product flows | `cd client && npm run e2e` (stack running) | 10 passed, MQTT leg skipped without broker credentials |
| Audit chain | `python scripts/audit_verify.py` | `RESULT: INTACT` |

## Screens

`docs/media/screens/`: Fleet `p4-fleet-*.png`, Asset Detail `p4-asset-detail-*.png`, 3D Asset View with Show why `p3-turbofan-why.png`, Cross-domain `p4-cross-domain-*.png`, Alarms `p4-alarms-*.png`, Work orders `p4-work-orders-*.png`, Onboarding `p4-onboarding-*.png`, Cognition `p5-cognition-*.png`, Model registry `p5-models-*.png`. Film: `docs/media/films/p3-asset-tour.mp4`.

## Limits, stated plainly

- The C-MAPSS data is NASA's simulated turbofan run-to-failure set; in the product it is replayed, not live. Laptop telemetry is live; phone and server run in simulation mode unless a device or SSH host is configured, and every such value carries a SIMULATED badge.
- Learning is batch retraining with a promotion gate, not continuous learning. One retraining run is on record.
- The k = 1 row of the deletion test is true by construction (the top-ranked sensor is the one whose single masking moves RUL most); the evidence is the k ≥ 2 rows.
- The 3D Asset View is an explanatory model built from published proportions, not CAD.
- HTTPS deployment needs a domain and is FUTURE-WORK.
