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

---

## 6. Current Status
*(Update this section whenever real progress is made — this is the handoff source of truth)*

- **Current phase:** Month 4 (Explainability Engine)
- **Immediate Task:** Begin designing and integrating the Explainability Engine, which surfaces AMKB nearest-neighbor logic (and Machine DNA) to make RUL predictions transparent to end users.

**Sequencing decision in effect:** AI core built first on C-MAPSS (Months 1–5); adapters for Laptop/Mobile/Server come in Month 6, not before.

**Completed so far (agent-built scaffolding):**
- [x] `server/adapters/base_adapter.py` — `NormalizedReading` schema + `MachineAdapter` ABC
- [x] `server/adapters/cmapss_adapter.py` — full C-MAPSS streamer, PHM scoring function
- [x] `server/atlas/world_model.py` — LSTM encoder (hidden=64 → `to_state` Linear → state_dim=32), save/load, stub fallback
- [x] `server/atlas/rul_engine.py` — LSTM primary path + EMA fallback, thread-safe
- [x] `server/atlas/train_rul.py` — training script with benchmarking + `--quick` mode
- [x] `server/atlas/domain_service.py` — background streaming + snapshot cache
- [x] `scripts/migrate_atlas.py` — pgvector + AMKB (vector(32)) + DNA + snapshots + learning_events tables
- [x] ATLAS API endpoints added to `server/backend_api.py`
- [x] `server/integrated_server.py` wired with ATLAS `DomainService`
- [x] `tests/test_adapters.py` — 29 passed, 1 skipped (integration gate on dataset presence)
- [x] `ml/preprocessing.py` — standalone preprocessing pipeline (windowing, normalization, RUL labeling)
- [x] `notebooks/week1_eda.ipynb` — exploratory data analysis scaffold

**Pending user actions (blocking):**
- [ ] Download C-MAPSS dataset → place `.txt` files in `data/cmapss/`
- [ ] Run: `python server/atlas/train_rul.py --quick` (smoke test after download)
- [ ] Run full training: `python server/atlas/train_rul.py --epochs 50`

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

**Weekly checklist (Month 3 - Prediction Engine):**
- [x] **Week 1 — DONE:** Architecture Refactor. Replaced static `Linear` head with `TemporalAttention` over LSTM. Re-wired API/routing payloads to accept a unified `PredictionOutput` format.
- [x] **Week 2 — DONE:** Single-seed Training & Sanity Check. Ran Attention-LSTM on `seed=42`, confirmed smooth loss curves, inspected non-degenerate attention weights, and firmly restored `strict=True` checkpoint loading safety.
- [x] **Week 3 — DONE:** Multi-Seed Apples-to-Apples Evaluation. Executed `evaluate_multiseed.py` across 5 seeds. Proven PHM standard deviation plummeted from 19.6% to 5.8%. Architecture definitively clears the <400 mean PHM validation gate (375.00 ± 21.93). Re-populated AMKB to align embeddings and cleared semantic test skips.
- [x] **Week 4 — DONE:** Decision & Documentation. Locked in Attention-LSTM as final Prediction Engine. Updated Project Context with the architectural arc log and citations.

**Next immediate step:** Month 4 — Explainability Engine.

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

| Date | File | Decision | Reason |
|---|---|---|---|
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
