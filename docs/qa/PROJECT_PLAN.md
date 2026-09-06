# ATLAS As-Built Project Plan (Retrospective)

**Project:** ATLAS — An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems
**Document Type:** As-Built Retrospective Project Plan
**Date:** 2026-08-25
**Status:** All 8 months fully completed & validated

> [!IMPORTANT]
> This is a **retrospective, as-built** project plan — not a forward-looking roadmap.
> All dates, deliverables, and milestones reflect what was actually built and committed,
> reconstructed from the canonical record in [`ATLAS_PROJECT_CONTEXT.md`](../../../ATLAS_PROJECT_CONTEXT.md)
> and verified against `git log`.

---

## 1. Project Evolution Context

This project exists within a single repository that evolved through two phases:

| Phase | Period | Description | Documentation |
|---|---|---|---|
| **Phase A (Prototype)** | Pre–July 2026 | IoT digital twin with SQLite, rule-based fault detection, sensor simulators, JWT auth, MQTT ingestion, Bhashini roadmap | [`Project Management and Execution Document.md`](../Project%20Management%20and%20Execution%20Document.md) |
| **Phase B (ATLAS)** | July–August 2026 | Cognition platform: Attention-LSTM, AMKB/pgvector, 4-domain adapters, Monte Carlo decisions, explainability, transfer study | **This document** |

The Phase A prototype (commits `532615e` → `b85f427`) established the IoT infrastructure (FastAPI server, React dashboard, TimescaleDB, MQTT ingestion, notification channels). Phase B (ATLAS, commits `37bc4c5` → `1a53ff3`) built the AI cognition pipeline on top of this infrastructure.

---

## 2. Sequencing Decision

**Source:** `ATLAS_PROJECT_CONTEXT.md` §2 (Sequencing decision)

The original plan had multi-domain adapters in Months 1–3. This was deliberately changed:

> **"C-MAPSS + AI core FIRST (Months 1–5), multi-domain adapters SECOND (Months 6–7)"**
> — User correctly identified that debugging the ML core AND multi-adapter data quirks simultaneously is harder than proving the core on one clean benchmark first, then generalizing outward.

---

## 3. Month-by-Month As-Built Timeline

### Month 1: C-MAPSS Pipeline & Baseline World Model

**Commit range:** `37bc4c5` (Week 4 checkpoint)

| Week | Deliverable | Key Files | Verification |
|---|---|---|---|
| W1 | FD001 data loaded, EDA complete, 7 constant sensors identified (s1,s5,s6,s10,s16,s18,s19), 14 informative retained | `notebooks/week1_eda.ipynb` | Variance discontinuity plot (1000× gap between constant and informative) |
| W2 | RUL labels computed + clipped (ceiling 125), normalization + windowing pipeline | `ml/preprocessing.py`, `data/processed/fd001_*.npz` | X_train: (20631, 30, 14), X_test: (100, 30, 14), no NaN/Inf, row-order fix applied |
| W3 | WorldModel forward pass verified on real windowed data | `server/atlas/world_model.py` | rul_pred: (32,1), state_vec: (32,32), multi-seed diagnostic confirmed nonzero std |
| W4 | End-to-end training loop, 80/20 train/val split, early stopping | `server/atlas/train_rul.py`, `data/models/cmapss_world_model.pt` | RMSE = 15.02, PHM = 383.19 (single representative run) |

**Bugs found:** Dead-gradient ReLU in rul_head (W3), row-order silent corruption risk (W2). *(See [DEFECT_REPORTS.md](DEFECT_REPORTS.md) DEF-001, DEF-002)*

---

### Month 2: AMKB Episodic Memory, Machine DNA & Adaptive Context Engine

**Commit:** `33162fd`

| Week | Deliverable | Key Files | Verification |
|---|---|---|---|
| W1 | AMKB core module: store_experience, retrieve_similar (cosine via `<=>`), get_unit_history | `server/atlas/amkb.py`, `tests/test_amkb.py` | 17 tests (11 unit + 6 integration) |
| W2 | Machine DNA Engine: 16-dim fingerprint, unclipped life_fraction_health, z-score normalization | `server/atlas/machine_dna.py`, `tests/test_machine_dna.py` | Health pattern, thermal profile, power signature, failure signature mapping |
| W3 | Full AMKB population pass (100 C-MAPSS training units) + near-failure retrieval sanity | `scripts/populate_amkb.py` | Healthy > 70 RUL, Near-Failure < 30 RUL retrieval verified |
| W4 | Adaptive Context Engine integration + API endpoints | `server/atlas/adaptive_context.py`, `server/api.py` | End-to-end context building verified |

**Architectural decisions:** true_rul / predicted_rul separation, RUL-Scale Canonical Policy (clipped for model, unclipped for DNA).

---

### Month 3: Attention-LSTM Escalation & Multi-Seed Validation

**Commit range:** `82779bc` → `76bc43f`

| Week | Deliverable | Key Files | Verification |
|---|---|---|---|
| W1 | Temporal Attention mechanism integrated over LSTM outputs | `server/atlas/world_model.py` | TemporalAttention module, PredictionOutput dataclass |
| W2 | Single-seed training and sanity check | `server/atlas/train_rul.py` | Training convergence verified |
| W3 | 5-seed multi-seed apples-to-apples evaluation | Scripts + diagnostic output | Baseline LSTM+Linear: PHM 426±83.55 (FAILED < 400 gate) |
| W4 | Attention-LSTM locked as permanent Prediction Engine | `data/models/best_model.pt` | **RMSE 15.22 ± 0.30, PHM 375.00 ± 21.93** (PASSED) |

**Decision:** Basic LSTM rejected due to 19.6% PHM coefficient of variation. Attention-LSTM reduced PHM std to 5.8% of mean.

---

### Month 4: Grounded Occlusion-Based Explainability Engine

**Commit range:** `1ce90ab` → `add6c2e`

| Week | Deliverable | Key Files | Verification |
|---|---|---|---|
| W1 | Confidence calibration & AMKB epistemic grounding | `server/atlas/explain.py` | Bounded confidence formula, true_rul citation enforcement |
| W2 | Cosine distance-to-similarity inversion fix | `server/atlas/explain.py` | `dee527d` commit |
| W3–4 | Occlusion Sensitivity feature attribution (14 forward passes, baseline=0.0 population mean) | `server/atlas/explain.py`, API `/api/explain` | Physical C-MAPSS sensor name mapping, $r_s = -0.5090$ |

**Spearman rank correlation:** $r_s = -0.5090$ — grounded confidence correlates strongly with actual prediction error.

---

### Month 5: Monte Carlo Decision Graph & Lead-Time Cost Optimization

**Commit:** `9906fa0`

| Week | Deliverable | Key Files | Verification |
|---|---|---|---|
| W1 | Decision Graph action ranking with ACTION_LEAD_TIME modeling | `server/atlas/simulation.py` | 4-action space with explicit risk-exposure horizons |
| W2 | Monte Carlo uncertainty propagation (1,000 stochastic rollouts) | `server/atlas/simulation.py` | Deterministic seeding (seed=42) for reproducibility |
| W3 | API endpoints `/api/decide`, `/api/simulate` and safety verification | `server/api.py` | Safety override gates verified ($\hat{y} \le 10$ or $h(t) \le 0.20$) |
| W4 | Cost model evaluation and safe tie-breaker integration | `server/atlas/simulation.py` | **47.17% lifecycle savings** ($1,817.50 vs. $3,440.00) |

**Bugs found:** Alphabetical tie-breaker safety risk, fixed-cost blind spot. *(See [DEFECT_REPORTS.md](DEFECT_REPORTS.md) DEF-004, DEF-005)*

---

### Month 6: Heterogeneous Machine Adapter Layer

**Commit range:** `25ceb7f` → `8ad3907`

| Week | Deliverable | Key Files | Verification |
|---|---|---|---|
| W1 | Base Adapter schema + LaptopAdapter (live psutil) | `server/adapters/base_adapter.py`, `server/adapters/laptop_adapter.py` | Instantaneous Stress Score (0.7×cpu + 0.3×mem) |
| W2 | Multi-domain AMKB polling loop and isolation | `server/atlas/domain_service.py` | 17,731 C-MAPSS rows untouched under multi-domain writes |
| W3 | MobileAdapter (Termux:API) + 2D window query generalization | `server/adapters/mobile_adapter.py` | Simulation fallback, arbitrary (30, D) window shapes |
| W4 | ServerAdapter (SSH + simulation fallback) + Category A/B taxonomy | `server/adapters/server_adapter.py` | GPU/No-GPU stress weight verification (sums to 1.0) |

**Taxonomy:** Category A (C-MAPSS: physical degradation $h \in [0,1]$, $0$=fresh, $1$=failed) vs. Category B (Laptop/Mobile/Server: instantaneous operational stress $h \in [0,1]$).

---

### Month 7: Learning Engine, Cross-Domain Transfer Study & Ablation Suite

**Commit range:** `ef4ecbf` → `cc6b951`

| Week | Deliverable | Key Files | Verification |
|---|---|---|---|
| W1 | LearningEngine with 3% epsilon promotion gate | `server/atlas/learning_engine.py` | Rollback invariance, DB audit logging |
| W2 | Domain pre-training + cross-domain transfer study | `server/atlas/pretrain_domain.py`, `server/atlas/transfer_study.py`, `docs/TRANSFER_STUDY_RESULTS.md` | MMD ≈ 1.23 (A vs B), NTI verified, non-collapse guards |
| W3 | 4-part cognition pipeline ablation suite | `server/atlas/ablation_engine.py`, `docs/ABLATION_STUDY_RESULTS.md` | Deterministic seeding, dual-axis evaluation |
| W4 | System audit, encoder routing fix, evaluation suite consolidation | `server/atlas/adaptive_context.py`, `scripts/evaluate_atlas.py` | Multi-domain WorldModel registry + dynamic resolution |

**Bugs found:** Padding-artifact NTI flaw (W2), RMSE-48 inflated baseline (W1), encoder routing bug (W4). *(See [DEFECT_REPORTS.md](DEFECT_REPORTS.md) DEF-006 through DEF-008)*

---

### Month 8: Performance Benchmarking, Resource Profiling & Final Thesis Synthesis

**Commit range:** `2a19fa8` → `1a53ff3`

| Week | Deliverable | Key Files | Verification |
|---|---|---|---|
| W1 | End-to-end latency & throughput benchmark | `scripts/benchmark_system.py`, `docs/ATLAS_BENCHMARK.md` | C-MAPSS e2e: 21.78 ms mean, compute: 6.70 ms |
| W2 | Resource profiling, memory footprint & concurrent load testing | `scripts/profile_resources.py`, `docs/ATLAS_RESOURCE_PROFILE.md` | 281.7 MB RSS, 0.07 MB leak delta, 49.5 req/s peak |
| W3 | Standalone evaluation CLI + InMemoryAMKB equivalence + Reproducibility guide | `scripts/evaluate_atlas.py`, `docs/REPRODUCIBILITY.md`, `tests/test_evaluation_cli.py` | < 10⁻⁵ pgvector equivalence, SHA-256 manifest |
| W4 | Final thesis chapter synthesis (Sections A, B, C) | `docs/ATLAS_THESIS_CHAPTER.md` | 192/192 tests passing, all figures cross-referenced |

---

## 4. Deliverables Summary

### Core Source Files

| Subsystem | Primary File(s) | Month |
|---|---|---|
| Preprocessing | `ml/preprocessing.py` | 1 |
| World Model | `server/atlas/world_model.py` | 1, 3 |
| RUL Engine | `server/atlas/rul_engine.py` | 1, 3 |
| AMKB | `server/atlas/amkb.py` | 2 |
| Machine DNA | `server/atlas/machine_dna.py` | 2 |
| Adaptive Context | `server/atlas/adaptive_context.py` | 2, 6 |
| Explainability | `server/atlas/explain.py` | 4 |
| Simulation & Decision | `server/atlas/simulation.py` | 5 |
| Adapters (4 domains) | `server/adapters/*.py` | 1, 6 |
| Domain Service | `server/atlas/domain_service.py` | 6 |
| Learning Engine | `server/atlas/learning_engine.py` | 7 |
| Transfer Study | `server/atlas/transfer_study.py` | 7 |
| Ablation Engine | `server/atlas/ablation_engine.py` | 7 |
| Domain Pre-Training | `server/atlas/pretrain_domain.py` | 7 |

### Documentation Deliverables

| Document | Path | Month |
|---|---|---|
| Project Context (SoT) | `ATLAS_PROJECT_CONTEXT.md` | 1–8 (living) |
| Literature Mapping | `docs/LITERATURE_MAPPING.md` | 6 |
| Transfer Study Results | `docs/TRANSFER_STUDY_RESULTS.md` | 7 |
| Ablation Study Results | `docs/ABLATION_STUDY_RESULTS.md` | 7 |
| System Benchmark | `docs/ATLAS_BENCHMARK.md` | 8 |
| Resource Profile | `docs/ATLAS_RESOURCE_PROFILE.md` | 8 |
| Reproducibility Guide | `docs/REPRODUCIBILITY.md` | 8 |
| Thesis Chapter | `docs/ATLAS_THESIS_CHAPTER.md` | 8 |

### Evaluation Artifacts

| Artifact | Path | Content |
|---|---|---|
| Evaluation Summary | `data/atlas_evaluation_summary.json` | Master scorecard (all metrics) |
| Ablation Results | `data/ablation_results.json` | 4-ablation raw results |
| Transfer Study Results | `data/transfer_study_results.json` | MMD, NTI, cosine matrices |
| System Benchmark | `data/system_benchmark_results.json` | Stage latencies, throughput |
| Resource Profile | `data/system_resource_profile.json` | RSS, concurrency, leak test |

---

## 5. Git Commit History (ATLAS Phase)

Total ATLAS-phase commits: 30 (from `37bc4c5` to `1a53ff3`)
Status: 9 commits ahead of `origin/main` (remote push held per user instruction)

*(Full commit log available via `git log --oneline 37bc4c5..HEAD`)*
