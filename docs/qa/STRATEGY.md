# ATLAS Project & Test Strategy Document

**Project:** ATLAS — An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems
**Document Type:** As-Built Project & Test Strategy (Retrospective)
**Date:** 2026-08-25
**Status:** Complete — all 8 months delivered and validated

> [!NOTE]
> This document is an as-built strategy retrospective compiled from the canonical project record
> ([`ATLAS_PROJECT_CONTEXT.md`](../../../ATLAS_PROJECT_CONTEXT.md)). It describes the strategy
> that was actually followed, not a forward-looking plan.

---

## 1. Project Objectives & Scope

**Source:** `ATLAS_PROJECT_CONTEXT.md` §1, §5

### Primary Objective
Build a modular machine cognition platform that enables machines to observe, understand, remember, predict, simulate, reason, decide, explain, and continuously improve their operational behavior through adaptive intelligence — validated across real hardware from consumer to production-server scale.

### Scope Definition
ATLAS extends conventional predictive maintenance (which only estimates *when* something fails) by adding:

1. **Persistent machine memory** (AMKB episodic vector store + Machine DNA fingerprints)
2. **Simulation-based decision recommendation** (Monte Carlo rollout + cost-weighted Decision Graph)
3. **Auditable explainability** (occlusion-based feature attribution + AMKB-grounded historical citations)
4. **Cross-domain validation** across 4 heterogeneous hardware tiers (not just one benchmark)

### Research Gap Addressed
No open, reproducible system integrates RUL prediction + simulation-based decision recommendation + memory-grounded explainability, evaluated across heterogeneous real machine domains.

*(Source: `ATLAS_PROJECT_CONTEXT.md` §5)*

---

## 2. Overall Technical Approach

**Source:** `ATLAS_PROJECT_CONTEXT.md` §3 (Frozen Architecture v5)

### Cognition Pipeline Architecture

```
Machine Adapter Layer (ONLY domain-specific code)
        ↓
World Model (Attention-LSTM → 32-dim state vector)
        ↓
AMKB ←→ Machine DNA (vector-indexed memory + per-unit fingerprint)
        ↓
Adaptive Context Engine
        ↓
Prediction Engine (RUL)
        ↓
Simulation Engine (1,000 Monte Carlo rollouts)
        ↓
Decision Graph (cost-weighted ranking)
        ↓
Explainability Engine (occlusion attribution + AMKB citations)
        ↓
Learning Engine (batch/periodic retraining, 3% epsilon gate)
```

### Core Architectural Constraint
The Machine Adapter Layer is the **only** location where domain-specific code is permitted. Every component below it operates purely on the normalized schema the adapter produces (fixed-length feature vector + metadata).

---

## 3. Validation Strategy & Domain Tiers

**Source:** `ATLAS_PROJECT_CONTEXT.md` §4

| Tier | Domain | Real Hardware? | Build Order |
|---|---|---|---|
| Industrial-scale (benchmark) | NASA C-MAPSS FD001 turbofan | Real data, not real hardware | **Months 1–5** (AI core proven here first) |
| Small — real, live | Laptop (psutil) | Real (owned) | Month 6 |
| Small — real, live | Mobile phone (Termux:API, Android) | Real (owned) | Month 6 |
| High-end — real, live | Cloud VM (SSH + psutil/nvidia-smi) | Real (simulation fallback) | Month 6 |

**"Domain Generalization by Construction"** argument: proven across 4 real/benchmark domains that the adapter interface holds; argued (explicitly labeled as argument, not proof) that it extends further.

**Stated limitation:** None of the 4 domains involve high-frequency/high-noise signals (kHz-range vibration/acoustic data common in real industrial motors) — this is named as future work, not glossed over.

---

## 4. Risk Approach — What Was Deliberately Scoped Out & Why

**Source:** `ATLAS_PROJECT_CONTEXT.md` §2 (rejection list)

| Rejected Feature | Reason for Rejection |
|---|---|
| Human Feedback Engine (real accept/reject/modify loop) | Needs a live multi-user pilot that doesn't exist |
| Full 8-class Universal Machine Adapter (CNC, EV, industrial motor, robot, etc.) | Needs real hardware/data partnerships |
| Closed-loop/online reinforcement learning | Identified as the single biggest scope-killer risk |
| Multi-machine fleet-level coordination | Beyond solo-student project scope |
| 3 separate papers | Reduced to 1 paper, 2 internal sections |
| 8-item patent list | Trimmed to 4 argued candidates (more reads as unvetted) |
| iOS mobile support | No viable non-jailbreak telemetry path |
| "Digital Twin" as standalone module | Doesn't exist as separate module; World Model + AMKB jointly provide state representation |
| "Continuous learning" | Learning Engine does periodic/batch retraining, not real-time/online learning |
| FD002–FD004 expansion | Single operating condition (FD001) sufficient for core validation |
| Real cloud VM credentials for Server tier | Runs in high-fidelity simulation fallback; SSH transport implemented and contract-tested but provisional |

---

## 5. Tools, Environments & Platforms

**Sources:** `requirements.txt`, `data/atlas_evaluation_summary.json` (hardware_context), `docs/ATLAS_BENCHMARK.md` §2

### Runtime Environment

| Component | Specification |
|---|---|
| **Operating System** | Windows 11 |
| **Processor** | Intel64 Family 6 Model 186 Stepping 2 (10 physical cores / 16 logical threads) |
| **System RAM** | 15.7 GB |
| **Python Runtime** | Python 3.13.5 (Anaconda distribution) |
| **PyTorch** | 2.10.0+cpu (CPU backend only, 10 threads) |
| **Database** | PostgreSQL / TimescaleDB with pgvector extension (vector dim = 32) |
| **Connection Pools** | psycopg 3.x with psycopg_pool (dual pools: AMKB + MachineDNAEngine, min_size=1, max_size=3) |
| **MQTT Broker** | Mosquitto (local, graceful fallback if offline) |
| **Version Control** | Git, local `main` branch (9 commits ahead of origin) |

### Key Python Dependencies

| Package | Purpose |
|---|---|
| `torch >= 2.2` (CPU) | Attention-LSTM World Model inference and training |
| `psycopg[binary] >= 3.1` + `psycopg_pool` | PostgreSQL / pgvector connection management |
| `pgvector >= 0.2` | 32-dimensional cosine similarity vector search |
| `scikit-learn >= 1.4` | Preprocessing, scaling, and evaluation utilities |
| `pandas >= 2.0` | C-MAPSS data loading and windowing |
| `numpy >= 1.26` | Numerical computation |
| `paramiko >= 3.4` | SSH transport for ServerAdapter |
| `fastapi >= 0.115` | REST API server |
| `faiss-cpu >= 1.8` | Alternative vector indexing (available but pgvector is primary) |

*(Full dependency list: [`requirements.txt`](../../../requirements.txt))*

### Model Checkpoint Integrity

| Checkpoint | SHA-256 | Parameters |
|---|---|---|
| C-MAPSS World Model (`best_model.pt`) | `bff76569...` | 60,609 |
| Laptop World Model (`laptop_world_model.pt`) | `053bd408...` | 58,305 |
| Mobile World Model (`mobile_world_model.pt`) | `782a5425...` | 58,305 |
| Server World Model (`server_world_model.pt`) | `856ebde3...` | 58,305 |
| Machine DNA Scaler (`machine_dna_scaler.json`) | `edcfc8f5...` | 6 features |

*(Full SHA-256 hashes: [`docs/REPRODUCIBILITY.md`](../REPRODUCIBILITY.md) §3)*

---

## 6. Success Criteria & Validation Gates

**Sources:** `ATLAS_PROJECT_CONTEXT.md` §6b, `docs/REPRODUCIBILITY.md` §2

### Prognostic Core Gates

| Gate | Threshold | Measured Result | Source |
|---|---|---|---|
| C-MAPSS FD001 RMSE | ≤ 16.0 cycles | 15.42 (deterministic checkpoint) / 15.22 ± 0.30 (multi-seed) | `data/atlas_evaluation_summary.json` |
| C-MAPSS FD001 PHM Score | ≤ 400.0 | 394.70 (deterministic) / 375.00 ± 21.93 (multi-seed) | `data/atlas_evaluation_summary.json` |
| Learning Engine promotion | RMSE_candidate ≤ 0.97 × RMSE_active | 3% epsilon gate enforced | `server/atlas/learning_engine.py` |

### Domain Pre-Training Non-Collapse Guards

| Guard | Threshold | Purpose |
|---|---|---|
| Cosine distance between latent centroids | ≥ 0.20 | Prevents dimensional collapse in self-supervised training |
| Euclidean distance between latent centroids | ≥ 0.50 | Secondary collapse guard |

### Explainability & Decision Quality Gates

| Gate | Threshold | Measured Result |
|---|---|---|
| Spearman rank correlation ($r_s$) | Negative (error decreases as confidence increases) | $r_s = -0.5090$ |
| Citation availability | 100% of grounded explanations include traceable AMKB citations | 100.0% |
| Near-failure safety catch rate | 100% of units with $t_{\text{true}} \le 15$ caught | 100% (both pipelines) |
| Fleet lifecycle cost reduction | > 0% vs. naive thresholding | 47.17% savings |

### System Performance Gates

| Gate | Threshold | Measured Result |
|---|---|---|
| End-to-end inference latency (C-MAPSS) | < 1000 ms (industrial polling interval) | 21.78 ms mean / 21.39 ms p₅₀ |
| Memory footprint (multi-domain) | < 1 GB | 281.7 MB RSS |
| Memory leak delta (100 cycles) | < 1 MB | 0.07 MB (zero progressive leakage) |
| InMemory vs. pgvector equivalence | < 10⁻⁵ tolerance | Verified in `tests/test_evaluation_cli.py` |

### Test Suite Gate

| Gate | Threshold | Measured Result |
|---|---|---|
| Full pytest pass rate | 100% | 192/192 passed (confirmed 2026-08-25) |

---

## 7. Relationship to Pre-ATLAS Prototype Documentation

This project evolved through two phases in the same repository:

- **Phase A (Prototype):** IoT digital twin with SQLite, rule-based fault detection, sensor simulators, Bhashini translation roadmap. Documented in [`Project Management and Execution Document.md`](../Project%20Management%20and%20Execution%20Document.md) and [`AI Agent Testing and Validation Document.md`](../AI%20Agent%20Testing%20and%20Validation%20Document.md) (29 tests, 5 test files).
- **Phase B (ATLAS):** Cognition platform with Attention-LSTM, pgvector AMKB, 4-domain adapters, Monte Carlo decisions. This document and all `docs/qa/` artifacts cover Phase B.

Phase A prototype tests (7 files, 43 functions) were **carried forward** into the ATLAS-era suite and still pass. They serve as a regression baseline for the underlying IoT infrastructure.
