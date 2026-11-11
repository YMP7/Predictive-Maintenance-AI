# Title justification

**ATLAS: An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems**

Each term of the title, what it claims, the code that implements it, where to see it in the running product, and the number that backs it. A cell that cannot be backed by evidence says **FUTURE-WORK**. The same matrix, with live numbers, is the product page `/about/evidence`.

Labels: **BUILD** means delivered and checked; **FUTURE-WORK** means not delivered and not claimed.

## Matrix

| Term | Claim | Implementing components | Live evidence in the product | Quantitative evidence |
|---|---|---|---|---|
| **Adaptive** | Adapts its estimate to the machine's context and to new machines | Adaptive Context Engine `server/atlas/adaptive_context.py`; Learning Engine (batch retrain for every domain, 3% validation gate) `server/atlas/learning_engine.py`; retrain history `scripts/run_retrain_history.py`; transfer study `server/atlas/transfer_study.py` | `/admin/cognition` panels 5 (Adaptive Context) and 10 (Learning Engine); `/admin/models` (retrain, versions) | Transfer study `data/transfer_study_results.json`: retrieval through C-MAPSS memory inflates error 8.3x (phone) and 7.1x (server) against within-domain memory, so per-domain adaptation is needed; laptop 0.89x. Retrain history `data/retrain_history.json`: **24 gated runs** across the five domains on scratch copies of the shipped models, 14 promoted and 10 rejected (C-MAPSS 6 of 8 promoted, with FD001 test RMSE between 14.89 and 15.45 across promoted models; laptop 1 of 4, phone 3 of 4, server 2 of 4, pump 2 of 4). Only the C-MAPSS runs use benchmark data; the other domains retrain on SIMULATED data. Retraining on failures recorded from real machines in service is **FUTURE-WORK** |
| **Machine Cognition** | Perceive, remember, predict, simulate, decide, explain, in one pipeline | World Model (Attention-LSTM, 32-dim state) `server/atlas/world_model.py`; AMKB `server/atlas/amkb.py`; Machine DNA (16-dim) `server/atlas/machine_dna.py`; RUL engine; Simulation `server/atlas/simulation.py`; Decision Graph `server/atlas/decision.py`; trace `server/cognition_trace.py` | `/admin/cognition`: all ten stages for any machine, with per-stage latency and replay of stored traces | End-to-end pipeline mean latency 21.8 ms (C-MAPSS), 6.7 ms (laptop), 6.8 ms (phone), 10.5 ms (server) `data/system_benchmark_results.json`. Ablations `data/ablation_results.json`: the full pipeline has 47.2% lower total maintenance cost than a RUL-threshold rule (3,440 to 1,817.5 cost units under the study's cost model, 0 missed failures each), at the price of 281 cycles of early replacement on 3 early-life units; AMKB grounding moves confidence from a constant 0.50 to a calibrated mean 0.035 (Spearman rho -0.509 against error) |
| **Platform** | Extensible to new machines, secured, deployable, auditable | Adapter SDK and conformance suite `docs/ADAPTER_SDK_SPEC.md`, `tests/test_adapter_conformance.py`; configurable adapter `server/adapters/configurable_adapter.py`; ingest (HTTP, WebSocket, MQTT, Modbus, CSV, manual) `server/ingest.py`, `server/platform_api.py`; RBAC; hash-chained audit `server/audit.py`; Docker `docker-compose.yml` | `/admin/onboarding` (seven-step wizard), `/admin/devices`, `/admin/users`, `/admin/diagnostics` | Adapter conformance suite **41/41 tests pass**, including the configurable adapter. pytest **455 pass**. Playwright flows 1-7 pass (`client/e2e/`), including onboarding a sensor and seeing pushed data on screen in 0.6 s. Audit chain verified intact in the database and the JSONL mirror (`scripts/audit_verify.py`) |
| **Explainable** | Every prediction comes with a reason a person can check | Explainability Engine (occlusion attribution for all five domains plus AMKB-grounded justification) `server/atlas/explain.py` | "Show why" in the 3D Asset View for any of the five machines, for example `/assets/cmapss/<unit>`; `/admin/cognition` panel 9; AMKB evidence in `/chat` | Attribution faithfulness, deletion test on 100 FD001 test units (`scripts/attribution_faithfulness.py`, `data/attribution_faithfulness.json`): masking the top-2 attributed sensors moves RUL by 35.4 cycles against 16.8 for 2 random sensors, and beats random in 90% of units (top-3: 42.4 vs 23.3, 94%). The same test on the other domains, all on SIMULATED data, top-2 against 2 random sensors: pump 29.7 vs 15.2 cycles (82% of 50 held-out simulated units); on the 0 to 1 output scale, laptop 0.141 vs 0.065 (73%), phone 0.060 vs 0.037 (69%), server 0.065 vs 0.044 (73%) of 100 held-out windows each. A check of the attribution against known fault causes on real machines is **FUTURE-WORK** |
| **Predictive Maintenance** | Forecasts remaining useful life and turns it into a maintenance action | RUL engine `server/atlas/rul_engine.py`; Decision Graph; work orders `server/operations_api.py`, `server/backend_api.py`; pump RUL trainer `server/atlas/train_pump_rul.py` on the simulated wear model `server/adapters/pump_degradation.py` | `/assets/cmapss/<unit>` (RUL band, recommended action, create work order); `/work-orders` (approve, assign, resolve); `/alarms` | NASA C-MAPSS FD001 test set, 100 units: **RMSE 15.42, MAE 11.81, PHM score 394.7** (`data/atlas_evaluation_summary.json`); five-seed mean RMSE 15.22 ± 0.30, PHM 375 ± 21.9; literature LSTM baseline (Zheng et al., 2017) RMSE 16.14, PHM 338. Motor-pump, **SIMULATED run-to-failure data only** (`data/pump_rul_evaluation.json`): 50 held-out simulated units, RMSE 7.72 cycles, MAE 5.52, PHM score 44.0; five seeds RMSE 7.71 ± 0.27; a constant guess scores RMSE 40.51. These pump numbers measure fit to the simulator, not to real pumps; validation on real pump failure data is **FUTURE-WORK** |
| **Heterogeneous Machine Systems** | One pipeline across unlike machines | Adapter Layer (`server/adapters/`: C-MAPSS, laptop, mobile, server, Modbus, configurable); normalised schema; asset profiles `server/adapters/asset_profiles.py` | `/cross-domain` (every asset on one normalised scale); `/assets` (five machines in 3D) | Five domains with trained World Models: C-MAPSS on the NASA benchmark; laptop, phone, server and the Modbus motor-pump on SIMULATED data. Validation on real hardware fleets is **FUTURE-WORK**. Per-domain transfer metrics in `data/transfer_study_results.json` (within-domain RMSE 0.096 laptop, 0.030 phone, 0.040 server on normalised RUL) |

## How to check each number

| Number | Command | Output |
|---|---|---|
| FD001 RMSE / PHM | `python scripts/evaluate_atlas.py` | `data/atlas_evaluation_summary.json` |
| Five-seed spread | `python scripts/evaluate_multiseed.py` | see `docs/REPRODUCIBILITY.md` |
| Ablations | `python scripts/run_ablations.py` | `data/ablation_results.json`, `docs/ABLATION_STUDY_RESULTS.md` |
| Transfer study | `python scripts/run_transfer_study.py` | `data/transfer_study_results.json`, `docs/TRANSFER_STUDY_RESULTS.md` |
| Latency | `python scripts/benchmark_system.py` | `data/system_benchmark_results.json`, `docs/ATLAS_BENCHMARK.md` |
| Attribution faithfulness (all five domains) | `python scripts/attribution_faithfulness.py` | `data/attribution_faithfulness.json` |
| Pump RUL (simulated) | `python -m server.atlas.train_pump_rul` | `data/pump_rul_evaluation.json`, `data/models/modbus_model_metadata.json` |
| Retrain history | `python scripts/run_retrain_history.py` | `data/retrain_history.json` |
| Conformance | `pytest tests/test_adapter_conformance.py` | 41 passed |
| Product flows | `cd client && npm run e2e` (stack running) | 15 passed (flows 1-7, Evidence links, accessibility, keyboard), MQTT leg skipped without broker credentials |
| Audit chain | `python scripts/audit_verify.py` | `RESULT: INTACT` |

## Screens

`docs/media/screens/`: Fleet `p4-fleet-*.png`, Asset Detail `p4-asset-detail-*.png`, 3D Asset View with Show why `p3-turbofan-why.png`, Cross-domain `p4-cross-domain-*.png`, Alarms `p4-alarms-*.png`, Work orders `p4-work-orders-*.png`, Onboarding `p4-onboarding-*.png`, Cognition `p5-cognition-*.png`, Model registry `p5-models-*.png`. Film: `docs/media/films/p3-asset-tour.mp4`.

## Limits, stated plainly

- The C-MAPSS data is NASA's simulated turbofan run-to-failure set; in the product it is replayed, not live. Laptop telemetry is live; phone and server run in simulation mode unless a device or SSH host is configured, and every such value carries a SIMULATED badge.
- Learning is batch retraining with a promotion gate, not continuous learning. The 24 recorded runs were made on scratch copies; the shipped checkpoints are unchanged.
- The pump RUL model, and the laptop, phone and server models, are trained on simulated data. Their numbers show the pipeline works on those machine types; they are not evidence of accuracy on real hardware.
- Occlusion masks a C-MAPSS sensor with 0.0 (as published) and any other domain's sensor with its population mean.
- The k = 1 row of the deletion test is true by construction (the top-ranked sensor is the one whose single masking moves RUL most); the evidence is the k ≥ 2 rows.
- The 3D Asset View is an explanatory model built from published proportions, not CAD.
- HTTPS deployment needs a domain and is FUTURE-WORK.
