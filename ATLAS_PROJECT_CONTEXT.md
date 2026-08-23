# ATLAS — Project Context File
### For any AI agent, collaborator, or future-you picking this project up mid-stream
**Read this file first, in full, before touching code or making architectural suggestions.**

---

## 1. What This Project Is

**ATLAS** — *An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems* — is a B.Tech final-year AI/ML project (Domain: **Explainable AI for Predictive Maintenance and Decision Intelligence**).

**One-line identity (do not deviate from this framing):**
> ATLAS is a modular machine cognition platform that enables machines to observe, understand, remember, predict, simulate, reason, decide, explain, and continuously improve their operational behavior through adaptive intelligence — validated across real hardware from consumer to production-server scale.

It extends conventional predictive maintenance (which only estimates *when* something fails) by adding: a persistent machine memory, simulation-based decision recommendation, and auditable explainability — validated not on one dataset, but across multiple real machine domains of increasing scale.

---

## 2. Evolution History — Why the Project Looks Like This (read before suggesting changes)

This project went through 5 design iterations. **Do not reintroduce ideas that were deliberately cut** — they were cut for stated reasons, not by oversight. Summary:

| Version | What changed | Why |
|---|---|---|
| v1 (original) | 10-chapter platform vision: 8 cognition subsystems, 8 patent claims, 3 planned papers, hardcoded "Adaptive Machine Decision Intelligence Platform" | Rejected as-is: scoped like a 15–30 person company's product, not a solo 8–12 month student project |
| v2 | Rescoped to ONE domain (NASA C-MAPSS), introduced the hard **🟢 BUILD / 🔵 FUTURE WORK** split used ever since | This split is the project's core discipline — every feature must be labeled one or the other, explicitly, not implied |
| v3 | Adopted free renames (AMKB, Machine DNA redefinition, Confidence Engine folded into Decision Graph output); demoted Human Feedback Engine, trimmed 8→4 patent candidates, 3→1 paper | Renames cost nothing; the demoted items each needed a live pilot / real data partnership the project doesn't have |
| v4 | Added real small-hardware domains: Laptop + Mobile (via Termux:API) adapters, formalized the **"Domain Generalization by Construction"** argument (adapter interface is the only domain-specific code) | User wanted to start cheap/real (owned hardware) rather than buy anything |
| v5 (FINAL/FROZEN) | Added a real high-end domain: Cloud VM via free student credits (`ServerAdapter`); added 2 genuine differentiators: **Cross-Domain Machine DNA Transfer Study** + **open-source Cross-Domain Benchmark release** | Answers "does this generalize to high-end machines" with real evidence + architectural argument, not hardware purchase or hand-waving |
| **Sequencing decision (current)** | Build order changed: **C-MAPSS + AI core FIRST (Months 1–5), multi-domain adapters SECOND (Months 6–7)** | Originally adapters were Month 1–3. User correctly identified this as risky — debugging the ML core AND multi-adapter data quirks simultaneously is harder than proving the core on one clean benchmark first, then generalizing outward |

**Things explicitly rejected — do not re-propose without a stated reason why circumstances changed:**
- Human Feedback Engine (real accept/reject/modify loop) — needs a live multi-user pilot, doesn't exist
- Full 8-class Universal Machine Adapter (CNC, EV, industrial motor, robot, etc.) — needs real hardware/data partnerships
- Closed-loop/online reinforcement learning — biggest single scope-killer risk identified across all reviews
- Multi-machine fleet-level coordination
- 3 separate papers — 1 paper, 2 internal sections, is the committed plan
- 8-item patent list — trimmed to 4 argued candidates deliberately (more reads as unvetted, not stronger)
- iOS mobile support — no viable non-jailbreak telemetry path
- "Digital Twin" as a standalone named component — doesn't exist as a separate module; World Model + AMKB *jointly* provide digital-twin-style state representation. Never claim a separate Digital Twin module exists.
- "Continuous learning" — the Learning Engine does **periodic/batch retraining on logged outcomes**, not real-time/online learning. Never describe it as continuous or real-time.

---

## 3. Frozen Architecture (v5 — do not modify without explicit user approval)

```
        Mobile          Laptop         Cloud VM        C-MAPSS
      (Termux:API)     (psutil/       (SSH + psutil/    (public
                        smartctl)      nvidia-smi)       dataset)
           │                │               │                │
           └────────┬───────┴───────┬───────┴────────────────┘
                     ▼               ▼
              [ Machine Adapter Layer ]   ← ONLY domain-specific code;
                     │                       normalizes to one fixed schema
                     ▼
              [ World Model ]                 (LSTM encoder → state vector)
                     ▼
              [ AMKB ] ←→ [ Machine DNA ]      (vector-indexed memory + per-unit
                     │                          degradation-fingerprint embedding)
                     ▼
              [ Adaptive Context Engine ]
                     ▼
              [ Prediction Engine (RUL) ]
                     ▼
              [ Simulation Engine ]            (Monte Carlo over RUL uncertainty)
                     ▼
              [ Decision Graph ]               (cost-weighted ranking; outputs
                     │                          Confidence/Risk/Impact/Urgency)
                     ▼
              [ Explainability Engine ]        (feature attribution + AMKB-
                     │                          grounded trajectory citations)
                     ▼
              Dashboard (per-domain + cross-domain comparison view)
                     ▼
              [ Learning Engine ]              (BATCH/PERIODIC retraining only —
                                                  not online/real-time)
```

**The one rule that governs all extension work:** the Machine Adapter Layer is the *only* place domain-specific code is allowed to live. Every component below it must operate purely on the normalized schema the adapter produces (fixed-length feature vector + metadata: sampling rate, unit count, etc.). If you're ever tempted to write `if domain == "laptop":` logic inside the World Model, AMKB, Decision Graph, etc. — stop, that logic belongs in the adapter instead.

### Subsystem reference table

| Subsystem | Definition | Status |
|---|---|---|
| Machine Adapter Layer | `CMAPSSAdapter`, `LaptopAdapter`, `MobileAdapter`, `ServerAdapter` — one shared interface | C-MAPSS: build-first (Month 1). Others: Month 6 |
| World Model | LSTM(hidden=64) → `to_state` Linear(64→32) → **32-dim state vector**. State vector is the primary output consumed by AMKB and Machine DNA downstream. | Month 1 |
| AMKB (Adaptive Machine Knowledge Base) | Vector-indexed store (FAISS/pgvector): experiences, failures, usage history, decisions. Embedding dim = **32** (matches state vector) | Month 2 |
| Machine DNA | Compressed per-unit embedding: health pattern, thermal profile, power signature, failure signature. Dim = **32** | Month 2 |
| Adaptive Context Engine | Domain-native context features; synthetic fields explicitly labeled where used | Rolled into relevant months |
| Prediction Engine (RUL) | Sequence model, scored with RMSE + C-MAPSS's standard asymmetric PHM scoring function | Month 3 |
| Simulation Engine | Monte Carlo rollout using RUL model's predictive uncertainty | Month 4 |
| Decision Graph | Cost-weighted candidate-action ranking; NOT a black-box learned policy — kept interpretable by design | Month 4 |
| Explainability Engine | Feature attribution + AMKB-retrieved-trajectory citations | Month 5 |
| Learning Engine | Batch retraining on logged outcomes only | Month 5 |

**Critical dimension note:** the canonical state vector dimension throughout ATLAS is **32**. AMKB experience embeddings are `vector(32)`. Machine DNA embeddings are `vector(32)`. WorldModel `to_state` output is 32-dim. This is fixed — do not change without updating all three subsystems simultaneously.

---

## 4. Validation Strategy (final)

| Tier | Domain | Real hardware? | Build order |
|---|---|---|---|
| Industrial-scale (benchmark) | NASA C-MAPSS turbofan dataset | Real data, not real hardware | **Built FIRST — Months 1–5, this is where the AI core is proven** |
| Small — real, live | Laptop | Real (owned) | Month 6 |
| Small — real, live | Mobile phone | Real (owned), via Termux:API (Android only, no root) | Month 6 |
| High-end — real, live | Cloud VM (free student credits: GitHub Student Pack → GCP/Azure) | Real | Month 6 |
| Bonus/reach (never load-bearing) | College HPC/server room; real industrial partner | Real, if access granted | Opportunistic, Months 1–2 onward |

**"Domain Generalization by Construction" argument:** proven across 4 real/benchmark domains that the adapter interface holds; argued (explicitly labeled as argument, not proof) that it extends further. Stated limitation, not hidden: none of the 4 domains involve high-frequency/high-noise signals (kHz-range vibration/acoustic data common in real industrial motors) — this is named future work, not glossed over.

---

## 5. Research, IP, and Publication Plan

- **Research gap:** No open, reproducible system integrates RUL prediction + simulation-based decision recommendation + memory-grounded explainability, evaluated across heterogeneous real machine domains (not just one benchmark).
- **One paper, two sections:** (A) RUL benchmarking vs. published C-MAPSS baselines. (B) Full pipeline decision-quality/explainability results + the Cross-Domain Machine DNA Transfer Study (the standout, most-citable result).
- **4 patent candidates** (labeled candidates for post-implementation evaluation, NOT filed claims): (1) simulation-coupled cost-weighted Decision Graph, (2) Machine DNA representation (pending prior-art search), (3) AMKB-grounded explainability method, (4) adapter-based cross-domain cognition pipeline.
- **Open-source release:** the ATLAS Cross-Domain Benchmark (normalized data from all 4 domains + eval scripts) as a standalone citable artifact.
- **Ablations planned (final list, 4):** RUL-alone vs. full pipeline · AMKB-grounded vs. ungrounded explainability · cost-weighted vs. naive-threshold Decision Graph · single-domain vs. cross-domain-informed World Model.
- **Academic Grounding & Literature Mapping:** All 36 core literature papers (Attention-LSTM RUL, AMKB dynamic memory, Monte Carlo decision optimization, XAI/digital twins, and domain adaptation) are formally mapped to codebase modules and thesis chapters in [`docs/LITERATURE_MAPPING.md`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/docs/LITERATURE_MAPPING.md).

---

## 6. Current Status
*(Update this section whenever real progress is made — this is the handoff source of truth)*

- **Current phase:** Month 7 (Learning Engine, Cross-Domain Transfer Study, and Full Pipeline Ablations)
- **Immediate Task:** Begin Month 7 Week 3: Full Pipeline Ablation Study & Empirical Evaluation Framework (`scripts/run_ablations.py`).

**Sequencing decision in effect:** AI core built first on C-MAPSS (Months 1–5); adapters for Laptop/Mobile/Server built and verified in Month 6; adaptive learning and cross-domain transfer verified in Month 7.

**Completed so far (agent-built scaffolding):**
- [x] `server/adapters/base_adapter.py` — `NormalizedReading` schema + `MachineAdapter` ABC with canonical Category A/B health index taxonomy
- [x] `server/adapters/cmapss_adapter.py` — full C-MAPSS streamer, PHM scoring function
- [x] `server/adapters/laptop_adapter.py` — live host telemetry via `psutil` + Instantaneous Stress Score
- [x] `server/adapters/mobile_adapter.py` — Android device via Termux:API + simulation fallback
- [x] `server/adapters/server_adapter.py` — Linux enterprise server via Paramiko SSH + simulation fallback
- [x] `server/atlas/world_model.py` — Attention-LSTM encoder (hidden=64 → `TemporalAttention` → `to_state` Linear → state_dim=32), save/load, stub fallback
- [x] `server/atlas/rul_engine.py` — Attention-LSTM primary path + calibrated `_EMAFallback` (median filter window=5, alpha=0.15), thread-safe
- [x] `server/atlas/train_rul.py` — training script with benchmarking + `--quick` mode
- [x] `server/atlas/domain_service.py` — background multi-domain streaming + snapshot cache (`register_cmapss`, `register_laptop`, `register_mobile`, `register_server`)
- [x] `scripts/migrate_atlas.py` — pgvector + AMKB (vector(32)) + DNA + snapshots + learning_events tables
- [x] ATLAS API endpoints parameterized for multi-domain queries in `server/api.py`
- [x] `server/integrated_server.py` wired with ATLAS `DomainService`
- [x] `ml/preprocessing.py` — standalone preprocessing pipeline (windowing, normalization, RUL labeling)
- [x] `docs/LITERATURE_MAPPING.md` — formal academic mapping of all 36 research papers across codebase modules and thesis chapters

  - **Month 4 — DONE:** Explainability Engine fully built:
    - Phase 1: AMKB-grounded historical citations with bounded confidence scores `(avg_sim * (1 / (1 + variance)))` and strict `true_rul` citation enforcement.
    - Phase 2: Feature Attribution using 30-timestep column occlusion (baseline `0.0` population mean) with explicit `attribution_unavailable_reason` reporting for non-14 feature domains.
  - **Month 5 — DONE:** Simulation Engine & Decision Graph:
    - Monte Carlo rollout over prognostic uncertainty with `ACTION_LEAD_TIME` risk-exposure modeling.
    - Deterministic tie-breaking (`expected_cost → p_failure → cost_std → action_name`) and strict confidence reuse from `ExplanationReport`.
  - **Month 6 — DONE:** Heterogeneous Machine Adapters & Multi-Domain Generalization:
    - Built all 4 domain adapters (`cmapss`, `laptop`, `mobile`, `server`).
    - Consolidated canonical health index taxonomy (Category A: physical wear vs. Category B: operational stress).
    - Fully parameterized `AdaptiveContextEngine` and `api.py` for arbitrary 2D window shapes.
    - Verified AMKB domain isolation (17,731 C-MAPSS rows untouched under multi-domain writes).
  - **Month 7 Week 1 — DONE:** Learning Engine & Batch Retraining:
    - Built `LearningEngine` (`server/atlas/learning_engine.py`) with 3% epsilon promotion gate, rollback invariance, standard benchmark evaluation (15.42 cycles), and DB audit logging.
  - **Month 7 Week 2 — DONE:** Cross-Domain Transfer Study & Domain Pre-Training:
    - Built domain pre-training engine (`server/atlas/pretrain_domain.py`) with deterministic seeds (101, 102, 103) and strict non-collapse guards.
    - Built transfer diagnostics engine (`server/atlas/transfer_study.py`) and CLI runner (`scripts/run_transfer_study.py`).
    - Empirically validated 4x4 MMD divergence (~1.23 separation), latent orthogonality (cosine -0.22 to 0.15), and AMKB semantic retrieval negative transfer (7.1-8.3x RMSE inflation). Published `docs/TRANSFER_STUDY_RESULTS.md` and `data/transfer_study_results.json`.

**Weekly checklist (Month 1):**
- [x] **Week 1 — DONE:** FD001 downloaded, loaded, columns assigned, exploratory plots done, non-informative sensors identified
  - 7 constant sensors confirmed (s1, s5, s6, s10, s16, s18, s19); 14 informative sensors kept
  - ⭐ **Thesis note:** variance distribution shows a clean ~1000× discontinuity between s6 (≈1.9×10⁻⁶) and s15 (≈1.4×10⁻³) — the 7/14 split is not an arbitrary threshold but a genuinely unambiguous gap. Cite this in the EDA section: "the variance distribution shows a clear discontinuity between constant and informative sensors, confirming the 7/14 split is not an arbitrary threshold."
- [x] **Week 2 — DONE:** RUL labels computed + clipped (ceiling 125), normalization + windowing pipeline (`ml/preprocessing.py`) built and fully verified:
  - `X_train: (20631, 30, 14)  y_train: (20631,)` ✓
  - `X_test:  (100, 30, 14)   y_test:  (100,)` ✓ (100 test units = correct for FD001)
  - No NaNs or Infs in any array ✓
  - RUL ordering: no negatives, cap applied correctly ✓
  - Row-order fix applied: `sort_values(["unit","cycle"]).reset_index(drop=True)` added to `compute_train_rul` — shape was correct before but window values would have been silently wrong without this on out-of-order rows ✓
  - Processed tensors saved to `data/processed/fd001_train.npz` and `fd001_test.npz` (Week 3 loads directly from these — no pandas re-run) ✓
- [x] **Week 3 — DONE:** `WorldModel` forward pass verified on real windowed data:
  - `rul_pred: torch.Size([32, 1])` ✓ · `state_vec: torch.Size([32, 32])` ✓
  - Multi-seed diagnostic (5 seeds, no `manual_seed`): all trials produced genuine nonzero std, values spanning both positive and negative ranges — confirmed no init-dependent dead output ✓
  - **Architecture bug found and fixed:** original `rul_head` had `nn.ReLU()` as the final layer. When `Linear(16→1)` init weights produce negative outputs (which is ~50% of random seeds), ReLU clips everything to exactly `0.0` identically — zero std, zero gradient, broken training. Removed. See Architecture Decisions Log.
  - `state_vec std=0.085` across batch, LSTM hidden std=0.059 — signal healthy throughout encoder ✓
- [x] **Week 4 — DONE:** End-to-end training loop run, properly evaluated via 80/20 train/val split and early stopping.
  - **Final Benchmark:** RMSE = 15.02 cycles, PHM Score = 383.19. (Test set evaluated strictly once using the best validation checkpoint).
  - ⭐ **Methodology Note:** Early stopping on MSE (`val_loss`) selected Epoch 46. However, in this run, `val_phm` and `val_loss` showed divergence at times, suggesting MSE-based early stopping may not select the checkpoint that best minimizes late-prediction risk. This is consistent with the asymmetric nature of the PHM metric, though confirming this as a general pattern would require repeating across multiple seeds. This asymmetric error profile (over-predicting in the danger zone) is highlighted in the output scatter plot.
  - Plots generated: `FD001_loss_curve.png` (with train vs val lines) and `FD001_pred_vs_actual.png` (highlighting late vs early predictions in the RUL < 30 zone) saved to `docs/figures/`.
  - `cmapss_world_model.pt` checkpoint saved to `data/models/`.

**Pending user actions:**
- [x] Review the Week 4 plots in `docs/figures/`.
- [x] Run `python scripts/migrate_atlas.py` to enable pgvector tables for Month 2.

**Next immediate step:** Month 2 — AMKB + Machine DNA.

**Weekly checklist (Month 2):**
- [ ] **Week 1 — Plumbing complete, semantic validation pending Week 3:** AMKB core module built and verified against live pgvector DB.
  - `server/atlas/amkb.py`: `store_experience`, `retrieve_similar` (cosine distance via `<=>`), `get_unit_history`, `get_experience`, `count`
  - ⭐ **true_rul / predicted_rul separation**: `true_rul` (ground-truth C-MAPSS label) and `predicted_rul` (model estimate) are stored as independent nullable fields.
  - `ml/preprocessing.py`: `make_windows` and both pipeline methods now return `(X, y, unit_ids)` — closes the unit_id gap needed for AMKB population.
  - `tests/test_amkb.py`: 17 tests — 11 unit (no DB) + 6 integration (live pgvector) all pass under correct conda environment.
  - ⚠️ **Pending Week 3:** Full real-data population pass (run WorldModel over all C-MAPSS training windows) + `TestNearFailureRetrieval` full verification.
- [x] **Week 2 — DONE:** Machine DNA Engine (`server/atlas/machine_dna.py`) built and tested.
  - ⭐ 16-dim structure mapping: Health Pattern (Dims 0-2), Thermal Profile (Dims 3-5), Power Signature (Dims 6-7), Failure Signature (Dims 8-15).
  - ⭐ Unclipped `life_fraction_health` used for whole-life pattern dimensions to avoid length-of-life confounding.
  - ⭐ `z-score` normalization built transparently into storage and retrieval to enforce cross-dimensional numeric parity.
- [x] **Week 3 — DONE:** Full AMKB population pass + near-failure retrieval sanity check.
  - ⭐ Run `scripts/populate_amkb.py` on all 100 C-MAPSS training units.
  - ⭐ Test `TestNearFailureRetrieval` passes on real data (Healthy vectors retrieve >70 RUL; Near-Failure vectors retrieve <30 RUL).
- [x] **Week 4 — DONE:** Adaptive Context Engine integration + API endpoints (`server/atlas/adaptive_context.py` & `server/api.py`).

**Weekly checklist (Month 4 - Explainability Engine):**
- [x] **Week 1 — DONE:** Confidence Calibration & AMKB Epistemic Grounding (`server/atlas/explain.py`).
- [x] **Week 2 — DONE:** Occlusion Sensitivity & Feature Attribution per C-MAPSS sensor.
- [x] **Week 3 — DONE:** API Integration & Frontend Attribution payloads (`/api/explain`).
- [x] **Week 4 — DONE:** Grounding Verification & Citations sanity testing.

**Weekly checklist (Month 5 - Simulation Engine & Decision Graph):**
- [x] **Week 1 — DONE:** Decision Graph action ranking with lead-time modeling (`ACTION_LEAD_TIME`).
- [x] **Week 2 — DONE:** Monte Carlo uncertainty propagation via `SimulationEngine` (`server/atlas/simulation.py`).
- [x] **Week 3 — DONE:** API Endpoints (`/api/decide`, `/api/simulate`) and policy safety verification.
- [x] **Week 4 — DONE:** Cost model evaluation and safe tie-breaker integration.

**Weekly checklist (Month 6 - Heterogeneous Machine Adapters):**
- [x] **Week 1 — DONE:** Base Adapter schema & Laptop Adapter (`server/adapters/laptop_adapter.py`).
- [x] **Week 2 — DONE:** Mobile Android Adapter with Termux:API (`server/adapters/mobile_adapter.py`).
- [x] **Week 3 — DONE:** High-fidelity Linux Enterprise Server Adapter (`server/adapters/server_adapter.py`).
- [x] **Week 4 — DONE:** Heterogeneous streaming service & cross-domain background telemetry loop (`server/atlas/domain_service.py`).

**Weekly checklist (Month 7 - Continuous Learning, Cross-Domain Transfer & Ablations):**
- [x] **Week 1 — DONE:** `LearningEngine` periodic batch retraining pipeline with 3% epsilon promotion gate and PostgreSQL audit logging.
- [x] **Week 2 — DONE:** Cross-Domain Representation Discrepancy & Transfer Study (`TRANSFER_STUDY_RESULTS.md`) with non-collapse guards and AMKB latent retrieval transfer.
- [x] **Week 3 — DONE:** Full Cognition Pipeline Comprehensive Ablation Suite (`ABLATION_STUDY_RESULTS.md`), deterministic seeding (`seed=42`), and dual-axis evaluation.
- [ ] **Week 4 — Next immediate step:** Month 7 Wrap-up / Month 8 Preparation.

**Next immediate step:** Month 7 Week 4 / Month 8 — End-to-End System Benchmark & Thesis Synthesis.

---

## 6b. Architecture Decisions Log
*(One entry per non-obvious decision or bug fix — so future agents and the thesis writeup don't rediscover these from scratch)*

- **Architecture Verification:** Cross-unit generalization tests definitively prove that embeddings for both healthy units and near-failure units accurately cluster and retrieve logically consistent nearest neighbors *across different physical engines* (avg ~123 RUL for healthy; ~4 RUL for near-failure queries).

### RUL-Scale Canonical Policy (Decisions Log)
Across Month 2, the handling of RUL limits encountered structural contradictions between World Model training, semantic retrieval, and long-term health metrics. The finalized canonical policy is:
1. **Model Output / Training Constraint:** The World Model is strictly trained against a **clipped RUL (max 125)** to stabilize early-life variance. All predictions (`predicted_rul`) inherently sit on this ~0-125 scale.
2. **AMKB Storage:** `amkb_experiences.rul_cycles` stores the **clipped RUL** (max 125). This ensures ACE neighbor aggregations share identical semantics with `predicted_rul`.
3. **Machine DNA Computation:** `amkb_experiences.metadata['raw_rul']` stores the true physical unclipped RUL. `MachineDNAEngine` prioritizes fetching this `raw_rul` during its health-pattern slope computation, guaranteeing that early-life variance isn't artificially flattened by the clipping artifact.

### Healthy vs. Near-Failure Generalization Asymmetry
Cross-unit semantic retrieval exhibits an expected asymmetry:
- **Near-Failure Clustering**: Retrieves multiple diverse units clustering tightly around 0-7 RUL (distances ~0.0001). This is strong, demanding evidence that the vector space successfully maps unit-independent degradation signatures.
- **Healthy-State Clustering**: Also retrieves logically healthy neighbors across multiple units, but with extremely small cosine distances (e.g., 2.18e-07). This is because early-life windows (e.g., cycle 30) for brand new engines operating under identical conditions (FD001) are naturally homogeneous. The lack of unit-specific degradation at start-of-life makes their embeddings nearly identical. Both work, but the near-failure result is the true citable proof of semantic generalization.

### Month 3 Architecture Arc (LSTM vs. Attention-LSTM)
During Month 3, the temporary linear RUL head (bolted on at the end of Month 1) was subjected to a rigorous 5-seed multi-seed evaluation. This revealed severe structural instability:
- **Baseline (LSTM+Linear):** Mean PHM 426.07 ± 83.55 (failed the strict <400 target; Std was 19.6% of mean).
- **Decision:** The basic LSTM was rejected due to this unacceptable run-to-run variability.
- **Replacement:** A standard Temporal Attention mechanism was integrated over the LSTM outputs (validated by Chen et al., 2020 and Ma et al., 2021). Rather than just relying on the final hidden state, the network dynamically pools degradation signals across the entire 30-cycle window.
- **Final Locked-in Results (Attention-LSTM):** RMSE 15.2152 ± 0.3074 | **PHM 375.00 ± 21.93**. The PHM standard deviation plummeted to 5.8% of the mean, and the architecture definitively cleared the <400 validation gate. This Attention-LSTM is now the permanently locked-in Prediction Engine.

### Month 4 Explainability Arc (Confidence & Feature Attribution)
During Month 4, the Explainability Engine was built and verified in two major phases to interpret the outputs of the Adaptive Context Engine and the Attention-LSTM World Model.
- **Phase 1 (Confidence & Citations):** We finalized the similarity-to-confidence formula explicitly to prevent division-by-zero, bounding confidence by trajectory variance: `confidence = (1 / (1 + distance)) * (1 / (1 + variance))`. We also rigorously enforced the `true_rul` separation rule, explicitly asserting that AMKB citations never circularly depend on `predicted_rul`.
- **Phase 2 (Feature Attribution):** We selected an Occlusion Sensitivity approach over gradient-based methods (like Captum) to ensure compatibility with both PyTorch and STUB fallbacks. The baseline was specifically set to `0.0` to respect the population mean of our z-score normalization. Granularity was kept coarse (whole 30-cycle columns per sensor) to directly map back to Machine DNA structures. Finally, we mapped `sensor_index` directly to actual physical C-MAPSS naming strings (e.g. "s3 (T30 (Total temperature at HPC outlet))") to prevent interpretability disconnects when analyzing outputs against Machine DNA sub-signatures.

### Month 5 Simulation Engine & Decision Graph Arc
During Month 5, we integrated Monte Carlo Simulation with a Decision Graph to map RUL uncertainties onto concrete maintenance action recommendations.
- **Cost Model Assumptions & Lead Times:** The cost model is explicitly synthetic and illustrative. We uncovered a critical structural bug where interventions (`SCHEDULE_MAINTENANCE_SOON`, `NOW`, `REPLACE_IMMEDIATELY`) were evaluated as fixed costs, meaning `CONTINUE_OPERATION` (evaluated dynamically) could falsely win at near-failure. We fixed this by introducing an explicit `ACTION_LEAD_TIME` table (e.g., 30 cycles for `CONTINUE_OPERATION`, 10 for `SOON`, 3 for `NOW`, 0 for `REPLACE_IMMEDIATELY`). This ensures all actions face a genuine risk-exposure horizon, and urgency strictly drives the ranking.
- **Tie-Breaker Bug:** The initial tie-breaker logic silently favored alphabetical sorting (`CONTINUE_OPERATION` > `SCHEDULE...`), creating a dangerous default to inaction. We corrected this to firmly prioritize stringently safer actions: `expected_cost → p_failure_before_action → cost_std → action_name`. 
- **Confidence Reuse Architecture Rule:** We mandated that `DecisionGraph` confidence must be exclusively fetched from the `ExplanationReport` (`confidence_score`). It is structurally forbidden to recompute confidence independently inside the decision layer to prevent metric drift.

### Month 6 Heterogeneous Machine Adapters & Cross-Domain Taxonomy Arc
During Month 6, we expanded the Machine Adapter Layer to 4 distinct hardware tiers and generalized the query/decision pipeline across multi-dimensional operational spaces.
- **Canonical Health Index Taxonomy:** We formalized a clean two-tier taxonomy in `base_adapter.py`:
  1. *Category A (Benchmark Ground Truth, C-MAPSS):* Physical structural degradation toward failure ($[0.0, 1.0]$ where $0.0 = \text{fresh}$, $1.0 = \text{failed}$).
  2. *Category B (Live Heterogeneous Hardware: Laptop, Mobile, Server):* Instantaneous Operational Stress / Saturation Index ($[0.0, 1.0]$ composite load score). Live continuous machines lack fixed failure points; `health_index` represents real-time workload intensity rather than structural degradation.
- **Dual-Mode Connection & Resilience:** Built non-blocking fault tolerance into `MobileAdapter` (Termux:API) and `ServerAdapter` (Paramiko SSH). If endpoints are offline, credentials unconfigured, or SSH drops mid-poll, the adapter cleanly auto-transitions to `SIMULATION` fallback without throwing exceptions or halting background polling threads.
- **High-End Server Tier Honesty Framing:** The `ServerAdapter` runs in high-fidelity Linux enterprise server simulation by default. While real Paramiko SSH transport is implemented and contract-tested, it is explicitly documented as provisional/simulated until live cloud VM credentials (e.g. GitHub Student Pack / GCP) are configured.
- **Query-Time Pipeline Parameterization:** We parameterized `AdaptiveContextEngine`, `server/api.py`, and `server/atlas/explain.py` to handle arbitrary 2D window dimensions (e.g. `(30, 5)` for laptop/mobile/server alongside `(30, 14)` for C-MAPSS). When non-14 feature windows are passed, `explain.py` returns a machine-readable `attribution_unavailable_reason` field to prevent silent capability gaps.

### Month 7 Learning Engine, Cross-Domain Transfer & Representation Discrepancy Arc
During Month 7, we built the periodic batch retraining pipeline (`LearningEngine`) and executed the headline **Cross-Domain Representation Discrepancy & Transfer Study** across all four hardware domains.
- **Week 1: Learning Engine & 3% Promotion Gate:**
  - Built `LearningEngine` (`server/atlas/learning_engine.py`) to periodically retrain the World Model against newly logged operational outcomes stored in PostgreSQL/TimescaleDB.
  - Formulated a strict 3% epsilon promotion gate: candidate models are promoted to production if and only if $\text{RMSE}_{\text{candidate}} \le \text{RMSE}_{\text{active}} \times 0.97$. If the candidate fails or regresses, the active model is restored untouched (rollback invariance) and an immutable audit record is logged to the `learning_events` table.
  - Aligned baseline evaluation protocol to standard last-window-per-unit benchmarking (15.42 cycles), ensuring retraining decisions are judged against the validated C-MAPSS benchmark range.
- **Week 2: Step 1 Domain Pre-Training & Non-Collapse Sanity Guards:**
  - *Hard Structural Guard:* Added code-level guards refusing to execute transfer studies on untrained zero-shot projections. Each compute domain (`laptop`, `mobile`, `server`) was trained with self-supervised Attention-LSTM autoregression and operational stress mapping.
  - *Collapse Discovery & Multi-Modal Generation:* Identified that early synthetic laptop generation had static channels (`disk ~0.58`, `mem ~0.60`), allowing reconstruction loss to ignore dynamic CPU bursts and yielding near-zero directional separation (`Cosine Dist = 0.0670 < 0.20`). Refactored `generate_laptop_windows` into four realistic multi-modal regimes (idle, office, burst, compile) and established strict non-collapse guards (`Cosine Dist >= 0.20`, `Euclidean Dist >= 0.50`), reinforced by decoupled hardcoded regression testing.
  - *Deterministic PRNG Seeding:* Isolated domain training with explicit seeds (`laptop`: 101, `mobile`: 102, `server`: 103) to ensure reproducible coordinate basis orientations in $\mathbb{R}^{32}$.
- **Week 2: Representation Geometry (MMD vs. Orthogonal Cosine Alignment):**
  - *MMD Domain Divergence:* Empirically proved that physical turbofan degradation (Category A) occupies a distinct manifold from compute operational stress (Category B) with uniform $\text{MMD} \approx 1.23$. Compute domains exhibit internal distributional proximity ($\text{MMD} = 0.90 - 0.93$).
- **Week 3: Cognition Pipeline Comprehensive Ablation Suite & Deterministic Seeding:**
  - *Ablation 1 (Full Cognition Pipeline vs. RUL-Alone Baseline):* Delivered a **47.17% lifecycle cost reduction** ($1,817.50 vs. $3,440.00) across 100 C-MAPSS test units. Dissected premature replacement waste (281.0 cycles across 3 early-life units: `unit_19`, `unit_27`, `unit_95`) and connected it to Month 2's finding on early-life embedding degeneracy: brand-new engines have near-zero cosine distances ($d \approx 0.000$) but high raw lifespan variance in AMKB retrieval ($\sigma^2 \approx 3,000 - 4,500$), causing symmetric Gaussian Monte Carlo uncertainty ($\sigma \approx 60$) to inflate tail failure probability ($p_{\text{fail}} \approx 11.3\%$) and prompt risk-averse preventive replacement ($60 vs. $113 expected failure cost).
  - *Ablation 2 (AMKB-Grounded vs. Ungrounded Explainability):* Demonstrated strong negative error correlation ($r_s = -0.5090$) for grounded confidence against true prediction error, whereas ungrounded models collapse to an uninformative 0.50 maximal uncertainty prior ($r_s = \text{Undefined}$) with 0% citation traceability.
  - *Ablation 3 (Cost-Weighted Decision Graph vs. Naive Rules):* Established a two-dimensional evaluation: (1) Safety parity baseline where both policies safely catch 100% of critical near-failure units ($t_{\text{true}} \le 15$), with Unit 66's 4-cycle margin ($t_{\text{true}}=14$, lead time=10) honestly disclosed as an operational near-miss; and (2) Economic and operational discrimination on the 30 disagreed units ($1,370.00 vs. $1,530.00, +10.46% savings), safely converting 26 units to graduated scheduling (`SOON`/`NOW`) instead of naive blunt immediate replacement (20 units).
  - *Ablation 4 (Domain-Adapted vs. Foreign Representation Transfer):* Reused Week 2's within vs. cross-physical retrieval findings (Laptop 0.89x, Mobile 8.30x, Server 7.10x) and demonstrated on the new 3×3 Cross-Compute Generalization Matrix that every domain achieves minimal retrieval RMSE on its own encoder (1.00x on diagonal, $2.57\times - 11.56\times$ cross-inflation).
  - *Decision Graph Determinism & Stochastic Simulation Limitation:* Documented that while seeding (`seed=42`) ensures exact reproducibility for evaluation benchmarks, near-tied expected-cost decisions (within 1-3% of each other on high-variance early-life units) are inherently sensitive under stochastic Monte Carlo simulation. Formally noted for production deployment that systems require larger sample counts, inference-time seed policies, or tie-breaking margin thresholds below which the system defers to human judgment rather than auto-recommending.

| Date | File | Decision | Reason |
|---|---|---|---|
| Month 7 W3 | `server/atlas/ablation_engine.py` | 4 Canonical Ablation evaluations + pure-NumPy Spearman rank correlation | Provides standardized, C-extension-safe ablation metrics across full ATLAS pipeline |
| Month 7 W3 | `server/atlas/simulation.py` | Deterministic RNG seeding (`seed=42`) in Monte Carlo simulation | Locks stochastic sample draws across borderline high-variance units for reproducible evaluation |
| Month 7 W3 | `docs/ABLATION_STUDY_RESULTS.md` | Dual-axis Ablation 3 framing + Gaussian early-life tail limitation disclosure | Evaluates economic discrimination on disputed units and documents stochastic sensitivity in production |
| Month 7 W1 | `server/atlas/learning_engine.py` | 3% epsilon promotion gate (`RMSE_cand <= 0.97 * RMSE_active`) with DB audit | Protects production checkpoint from regressions; logs all promote/rollback events |
| Month 7 W2 | `server/atlas/pretrain_domain.py` | Self-supervised Attention-LSTM domain pre-training + non-collapse guard | Produces legitimate 32-dim latent spaces for compute domains prior to transfer study |
| Month 7 W2 | `server/atlas/transfer_study.py` | Replaced zero-padding with AMKB 32-dim latent $k$-NN memory retrieval | Tests genuine semantic memory transfer without dimensional mismatch distortion |
| Month 7 W2 | `docs/TRANSFER_STUDY_RESULTS.md` | Formal literature grounding (MMD, TCA, NTI) + Laptop asymmetry disclosure | Thesis-ready research report with honest, mathematically sound boundary analysis |
| Month 6 W1 | `server/adapters/laptop_adapter.py` | `health_index` defined as Instantaneous Stress Score (`0.7*cpu + 0.3*mem`) | Laptops lack labeled failure points; load is a stress proxy, not structural failure |
| Month 6 W2 | `server/atlas/domain_service.py` | Standalone polling loop streams laptop readings into AMKB (`true_rul=None`) | Partitions live experiences into `domain='laptop'` without contaminating C-MAPSS rows |
| Month 6 W3 | `server/atlas/adaptive_context.py` | Relaxed hardcoded `(30, 14)` check; dynamic shape handling with zero-shot fallback | Enables `/api/context`, `/api/explain`, and `/api/decide` to serve non-CMAPSS domains |
| Month 6 W4 | `server/adapters/server_adapter.py` | Mathematical weight verification for GPU (`0.35/0.25/0.20/0.10/0.10`) & No-GPU (`0.45/0.35/0.10/0.10`) | Guarantees stress formulas strictly sum to 1.0 under all hardware configurations |
| Month 1 W1 | `server/adapters/base_adapter.py` | State vector dimension fixed at **32** throughout (AMKB, DNA, WorldModel `to_state` output all `vector(32)`) | Canonical dimension must be consistent across all three subsystems simultaneously — do not change one without the others |
| Month 1 W2 | `ml/preprocessing.py` | Added `sort_values(["unit","cycle"]).reset_index(drop=True)` at the top of `compute_train_rul` | Without this, windowed features are correct in shape but silently wrong in ordering if the raw file has out-of-order rows — shape checks don't catch this |
| Month 1 W3 | `server/atlas/world_model.py` | **Removed terminal `nn.ReLU()` from `rul_head`** — non-negativity enforced at inference via `torch.clamp(min=0)` in `predict()` instead | Terminal ReLU on output layer causes init-dependent dead outputs: when random init produces negative `Linear(16→1)` outputs (~50% of seeds), ReLU collapses every prediction to exactly `0.0` identically — zero std, zero gradient, training appears stuck with no error. Fix: remove the ReLU so MSE loss can push raw outputs toward the correct sign via unblocked gradient; non-negativity is then enforced separately at inference via `clamp(min=0)`. MSE does not enforce non-negativity — it just stops being blocked from doing its job. |
| Month 1 W4 | `server/atlas/train_rul.py` | **`val_phm` monitoring scale** — `val_phm` is computed across *all* windows per validation unit during training | The massive scale of `val_phm` (up to 1.4M) vs final PHM score (383) is because the final benchmark strictly uses the standard **last-window-per-unit** protocol. `val_phm` tracks all windows (including noisy early-life predictions) as a monitoring signal and is not directly comparable in scale to the final benchmark. |
| Month 1 W4 | `server/atlas/train_rul.py` | **Training Non-Determinism** — Acknowledged run-to-run variability in final metrics despite random seeding | Even with `random.seed(42)`, LSTM training on CPU multi-threading isn't perfectly bitwise-reproducible. The reported RMSE=15.02 / PHM=383.19 is a representative run. A formal multi-seed evaluation (mean ± std) is planned for the Month 9-10 ablation phase to cleanly separate structural findings from run variance. |

---

## 7. Repository Structure (target — build toward this)

```
atlas/
├── data/
│   ├── cmapss/              # raw FD001-FD004 .txt files + README.md
│   └── models/              # trained checkpoints (cmapss_world_model.pt, etc.)
├── ml/
│   ├── preprocessing.py     # Week 2 deliverable — reusable preprocessing pipeline
│   ├── training/
│   ├── evaluation/          # benchmark comparison, ablation scripts
│   └── checkpoints/
├── notebooks/
│   └── week1_eda.ipynb      # Week 1 EDA — sensor plots, variance analysis
├── server/
│   ├── adapters/            # Machine Adapter Layer (ONLY domain-specific code)
│   │   ├── base_adapter.py  # NormalizedReading schema + MachineAdapter ABC
│   │   ├── cmapss_adapter.py
│   │   ├── laptop_adapter.py    # Month 6
│   │   ├── mobile_adapter.py    # Month 6
│   │   └── server_adapter.py    # Month 6
│   ├── atlas/               # ATLAS cognition core (domain-agnostic)
│   │   ├── world_model.py
│   │   ├── rul_engine.py
│   │   ├── train_rul.py
│   │   ├── domain_service.py
│   │   ├── amkb.py              # Month 2
│   │   ├── machine_dna.py       # Month 2
│   │   ├── simulation_engine.py # Month 4
│   │   ├── decision_graph.py    # Month 4
│   │   ├── explainability.py    # Month 5
│   │   └── learning_engine.py   # Month 5
│   ├── backend_api.py
│   ├── integrated_server.py
│   └── ...
├── scripts/
│   ├── migrate.py           # base TimescaleDB schema
│   ├── migrate_atlas.py     # pgvector + AMKB + DNA tables
│   ├── run_transfer_study.py    # Month 7
│   └── run_ablations.py         # Month 7
├── tests/
│   ├── test_adapters.py
│   └── ...
├── docs/
│   ├── ATLAS_BENCHMARK.md       # Month 8
│   └── ...
└── ATLAS_PROJECT_CONTEXT.md     # THIS FILE — keep at repo root, update as truth
```

---

## 8. Ground Rules for Any Agent Extending This Project

1. **Never silently reintroduce a demoted feature** (Section 2's rejection list) — if it seems newly relevant, say so explicitly and ask the user, don't just add it back.
2. **Never claim a component exists that isn't in the Section 3 table** — especially "Digital Twin" as standalone, or "continuous/real-time learning."
3. **Respect the current build sequencing** — C-MAPSS/AI core (Months 1–5) before adapters (Month 6), unless the user explicitly changes this again.
4. **The Machine Adapter Layer is the only place domain-specific code belongs** — flag any violation of this during code review.
5. **Keep the BUILD/FUTURE-WORK label on every feature discussion** — this labeling discipline is the single thing that has made this project defensible across every review so far; don't drop it for convenience.
6. **Update Section 6 (Current Status) whenever real progress happens** — this file is meant to be a living source of truth, not a one-time snapshot.
7. **State vector dimension is 32 throughout** — WorldModel `to_state` output, AMKB embeddings, Machine DNA embeddings are all `vector(32)`. Any change requires simultaneous update to all three.

---

## 9. Month 1 Weekly Breakdown (canonical reference)

### Week 1 — Get the data, understand it, set up environment

Dataset: NASA C-MAPSS Turbofan Engine Degradation Simulation. Download from the NASA Prognostics Data Repository or the mirrored version on Kaggle ("NASA Turbofan Jet Engine Data Set").

Structure to know cold before writing any code:
- 4 sub-datasets: FD001–FD004. **Start with FD001 only.**
- Columns: `unit_number, time_in_cycles, 3 operational_settings, 21 sensor_measurements`. No headers in raw files — assign column names manually.
- Train: each unit runs healthy → failure. RUL = cycles remaining until end of file, per unit.
- Test: units cut off before failure — predict RUL for those from `RUL_FD001.txt`.

**Week 1 deliverable:** `notebooks/week1_eda.ipynb` — loads FD001, assigns column names, basic exploratory plots (sensor readings over cycles for sample units). Build intuition for which sensors show degradation trends vs. which are near-constant (7 of 21 in FD001 are non-informative).

### Week 2 — Preprocessing pipeline

- Compute RUL labels: for each unit, `RUL_at_cycle_t = max_cycle_for_that_unit - t`
- Clip RUL at ceiling of **125** (standard literature practice — cite when writing up)
- Drop non-informative sensors (identified in Week 1)
- Normalize remaining sensors (z-score or min-max; **fit on train, apply to test — no test leakage**)
- Windowing: fixed-length sliding windows of **30 cycles** → input shape `(30, num_sensors)`

**Week 2 deliverable:** `ml/preprocessing.py` — reusable pipeline, raw C-MAPSS files in → windowed/normalized tensors out.

### Week 3 — World Model architecture

The canonical architecture (do not change without reason):

```python
import torch.nn as nn

class WorldModel(nn.Module):
    def __init__(self, num_sensors, hidden_dim=64, state_dim=32):
        super().__init__()
        self.lstm = nn.LSTM(input_size=num_sensors, hidden_size=hidden_dim,
                             num_layers=2, batch_first=True, dropout=0.2)
        self.to_state = nn.Linear(hidden_dim, state_dim)

    def forward(self, x):              # x: (batch, window_len, num_sensors)
        _, (h_n, _) = self.lstm(x)
        state_vector = self.to_state(h_n[-1])  # (batch, 32)
        return state_vector
```

`state_dim=32` output is what AMKB (Month 2) and Machine DNA (Month 2) will consume. Keep it simple — attention variants are a legitimate ablation for Month 9–10, not a Week 3 concern.

**Week 3 deliverable:** `WorldModel` class defined, forward pass tested on a batch of real windowed data.

### Week 4 — First training loop + sanity check

Temporary throwaway RUL head to confirm state vector is learning:

```python
class TempRULHead(nn.Module):
    def __init__(self, state_dim):
        super().__init__()
        self.fc = nn.Linear(state_dim, 1)
    def forward(self, state_vector):
        return self.fc(state_vector).squeeze(-1)

# Training loop: MSE loss, modest epochs, plot loss curve
```

This is **not the final RUL model** — that's Month 3. This is purely a sanity check.

**Week 4 deliverable:** training script + loss curve + scatter plot of predicted vs. actual RUL on a validation split. **Keep this plot — it's your first real result and belongs in the thesis.**

---

## Pending Actions — Known Hardcoded C-MAPSS Assumptions

**Context:** Audited during Month 6 Week 2 planning. These four locations assume the C-MAPSS domain's specific dimensions. They do NOT block storing laptop data into AMKB (storage is fully domain-parameterized). They MUST be resolved before the laptop domain can be *queried* through the API or context engines.

| # | File | Line(s) | What's hardcoded | Severity |
|---|------|---------|-------------------|----------|
| 1 | `server/api.py` | 42 | Single hardcoded WorldModel path (`cmapss_world_model.pt`). No laptop model loaded at startup. | 🔴 Blocks `/api/context`, `/api/decide` for laptop |
| 2 | `server/api.py` | 77–81 | Window validation hardcoded to `len(row) != 14`. Laptop's 5-feature window rejected with HTTP 400. | 🔴 Blocks laptop API queries |
| 3 | `server/atlas/adaptive_context.py` | 49 | `if current_window.shape != (30, 14): raise ValueError` inside `build_context()`. | 🔴 Blocks laptop context building |
| 4 | `server/atlas/explain.py` | 180–202 | `calculate_feature_attribution` imports `INFORMATIVE_SENSORS` from `cmapss_adapter`, loops `range(14)`. Returns `[]` for non-(30,14) windows with no indication this is a known limitation. | 🟡 Non-fatal but silently returns empty attributions |

**Status:** Not blocking Month 6 Week 2 (storage-only polling loop). **MUST resolve before Week 3/4 laptop query support.**

**Fix approach:** Make `AdaptiveContextEngine` read `feature_dim` and `seq_len` from the domain's `WorldModelConfig` instead of hardcoding `(30, 14)`. For explain.py, add domain-aware sensor name lookup or return an explicit `attribution_unavailable_reason` field.

