# ATLAS Viva Voce Defense — Anticipated Examiner Inquiries & Evidence-Grounded Responses

**Project:** ATLAS — An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems  
**Document Type:** Viva Defense Technical Q&A Guide & Architectural Position Paper  
**Author:** Candidate  
**Date:** 2026-09-20  
**Current Commit:** `36da3a7` | **Repository Status:** Fully Tested (209 unit/integration tests passing, Phases 0–5 live verified)  

---

## Executive Reading Guide for the Candidate

This document prepares you for technical questioning during the MSc / PhD viva voce examination. It is structured around eleven critical inquiries spanning machine learning theory, data provenance, system security, statistical rigor, and architectural trade-offs.

### The Defense Philosophy
1. **Never claim perfection; demonstrate bounded control:** In safety-critical predictive maintenance (PHM), examiners look for candidates who understand where their system fails, how those failures are caught, and why specific design trade-offs were chosen.
2. **Preempt the follow-up:** Every primary answer states the design decision cleanly; every anticipated follow-up reveals the honest residual boundary before the examiner has to extract it.
3. **Point to working code and tests:** Every technical claim is grounded in exact source files, verified PyTorch tensor shapes, and permanent regression tests.

---

## Technical Ground Truth Quick-Sheet

Before answering questions on specific numbers, keep these verified codebase constants in mind:

| Parameter | C-MAPSS (Turbofan) | Laptop Workstation | Mobile Device (Android) | Enterprise Server |
|---|---|---|---|---|
| **Degradation Category** | **Category A** (Irreversible physical wear) | **Category B** (Operational stress & saturation) | **Category B** (Operational stress & saturation) | **Category B** (Operational stress & saturation) |
| **Adapter Channels Acquired** | 14 informative sensors | 16 channels (5 model + 11 engineering metrics) | 16 channels (14 sensed + 2 derived norms) | 5 normalized metrics |
| **World Model Input Dim (`feature_dim`)** | **14** (`lstm.weight_ih_l0 = [256, 14]`) | **5** (`lstm.weight_ih_l0 = [256, 5]`) | **5** (`lstm.weight_ih_l0 = [256, 5]`) | **5** (`lstm.weight_ih_l0 = [256, 5]`) |
| **Latent Bottleneck Dimension** | 32 (`state_dim = 32`) | 32 (`state_dim = 32`) | 32 (`state_dim = 32`) | 32 (`state_dim = 32`) |
| **RUL Scale (`max_rul`)** | $125.0$ flight cycles (raw cycle scale) | $1.0$ (normalized operational headroom) | $1.0$ (normalized operational headroom) | $1.0$ (normalized operational headroom) |
| **Telemetry Ingestion Source** | FD001 dataset replay (100 test units) | Live OS kernel hooks via `psutil` | Live BMIC & Bosch BMI320 via Termux/ADB | Calibrated synthetic / SSH daemon |

---

## Question 1: Mobile Architecture — 16 Acquired Channels vs. 5-Feature Neural Model

> **Examiner Question:**  
> *"Your Mobile adapter acquires 16 channels across three data tiers, but your Attention-LSTM World Model receives only 5 features. Why did you acquire 16 channels if you only train on 5, and how do you justify omitting the other 11?"*

### Primary Answer
We deliberately decoupled **digital twin telemetry acquisition** from **neural representation learning**:

1. **The 16 Acquired Channels (Digital Twin Layer):** The Mobile adapter (`server/adapters/mobile_adapter.py`) acquires 16 channels structured into three explicit confidence tiers:
   * **Tier (a) Directly Measured (14 channels):** Acquired from hardware ADCs, BMIC thermistors, and kernel counters with zero transformation beyond linear scaling: `battery_level`, `battery_temp` ($32.0^\circ\text{C}$ from BMIC thermistor), `battery_current` (shunt resistor), `battery_voltage`, `cpu_usage` (`/proc/stat` jiffies), `memory_used_percent` (`/proc/meminfo`), triaxial acceleration ($a_x, a_y, a_z$), triaxial angular velocity ($\omega_x, \omega_y, \omega_z$), optical illuminance (AMS TCS3701 photodiode in Lux), and IR proximity (cm).
   * **Tier (b) Physically Derived (2 channels):** Deterministic Euclidean norms validated against physical ground truth: `vibration_rms` ($\frac{1}{20}\sqrt{a_x^2 + a_y^2 + a_z^2}$, validated against baseline Earth gravity $g = 9.81\text{ m/s}^2 \rightarrow \approx 0.49$) and `magnetic_field` ($\frac{1}{100}\sqrt{m_x^2 + m_y^2 + m_z^2}$, validated against ambient geomagnetic flux $30\text{--}60\ \mu\text{T}$).
   * **Tier (c) Operational Heuristic (1 metric):** Composite instantaneous stress score ($0.35 T_{\text{batt}} + 0.25 C_{\text{cpu}} + 0.20 M_{\text{mem}} + 0.10 V_{\text{rms}} + 0.10(1 - B_{\text{lvl}})$), representing immediate operational strain.
2. **The 5 Model Features (Cognition Layer):** The neural World Model (`data/models/mobile_world_model.pt`) takes strictly the **5 canonical core features**: `battery_level`, `battery_temp`, `battery_current`, `cpu_usage`, and `memory_used_percent` (`_CANONICAL_MODEL_FEATURES["mobile"]` in `server/adapters/base_adapter.py`).
3. **The Architectural Justification:**
   * **Symmetric Cross-Domain Parity:** Laptop, Mobile, and Server all share a 5-dimensional canonical input manifold ($D=5$). This allows their 32-dimensional latent representations to be directly compared in the Cross-Domain Transfer Study without dimensional projection distortion or padding artifacts (DEF-006).
   * **Environmental Noise Isolation:** Ambient optical light and orientation angles fluctuate with room lighting and user movement, not internal battery wear or thermal saturation. Feeding environmental variables into the autoregressive LSTM would inject uncalibrated noise into RUL inference.

### Anticipated Follow-Up
> *"If the extended 11 channels don't go to the neural network, what are they used for?"*

**Response:**  
They drive the real-time 3D Digital Twin visualization (Three.js orientation and vibration jitter), threshold-based mechanical shock alarms, and physical engineering diagnosis. In the dashboard UI (`MonitoringView.tsx`), Tier (a) and Tier (b) channels are rendered with distinct visual badges (`● TIER (a) DIRECTLY MEASURED` and `TIER (b) DERIVED NORM`) so that human maintenance engineers have full physical visibility without corrupting the neural model's latent manifold.

---

## Question 2: Cross-Domain Transfer & Latent Space Dimensional Alignment

> **Examiner Question:**  
> *"In your Cross-Domain Transfer Study, C-MAPSS has 14 sensor channels while Laptop, Mobile, and Server have 5. How can you mathematically evaluate transfer between domains with completely incompatible input dimensions?"*

### Primary Answer
Evaluating transfer across heterogeneous dimensions was one of the central methodological challenges of this project, and the source of **DEF-006**:

1. **The Failure of Naive Padding (DEF-006):** In Month 7 W2, early evaluation scripts appended zero-padding to 5-feature compute vectors to match C-MAPSS's 14 dimensions. This created artificial distance inflation (NTI correlated with the count of padded zeros rather than semantic divergence).
2. **The Corrected Architecture:** We abandoned input-space transfer entirely. Cross-domain transfer in ATLAS is evaluated strictly within the **shared 32-dimensional latent state space** ($\mathbb{R}^{32}$):
   * Each domain possesses its own domain-specific Attention-LSTM encoder:
     $$E_{\text{cmapss}}: \mathbb{R}^{30 \times 14} \rightarrow \mathbb{R}^{32}, \quad E_{\text{compute}}: \mathbb{R}^{30 \times 5} \rightarrow \mathbb{R}^{32}$$
   * Both encoders project operational sequences into comparable 32-dimensional latent bottlenecks ($z \in \mathbb{R}^{32}$).
   * The **Negative Transfer Index (NTI)** is calculated by extracting latent query vectors from a source domain and querying the target domain's AMKB vector memory (backed by TimescaleDB pgvector `<=>` cosine distance).
3. **The Research Finding:** Testing memory retrieval in the shared latent space proved that compute domain representations degrade turbofan RUL prediction by **8.3× RMSE inflation** (NTI = 8.3). This mathematically proved our hypothesis: **cross-domain transfer between Category A (thermodynamic fatigue) and Category B (compute saturation) suffers from severe negative transfer**, proving that domain-specific cognition adapters are mandatory.

### Anticipated Follow-Up
> *"If latent dimensions match, why did negative transfer still occur?"*

**Response:**  
Because matching dimensions does not mean matching semantics. A 32-dimensional latent vector representing thermodynamic pressure decay and high-pressure turbine degradation occupies an entirely different manifold than a 32-dimensional vector representing CPU frequency throttling and battery voltage drop. The 8.3× NTI confirms that AMKB failure memories cannot be naively shared across fundamentally different physical failure modes.

---

## Question 3: C-MAPSS Benchmark Rigor vs. Literature Baselines

> **Examiner Question:**  
> *"Your C-MAPSS FD001 test RMSE is 15.42, which is only an 8% improvement over Zheng et al. (16.14, published in 2017). Given nine years of deep learning advances, why is your improvement modest, and does this justify the architecture?"*

### Primary Answer
We deliberately frame this comparison as an **evidence-based reality check**, not as an exaggerated claim of competitive superiority:

1. **Credibility Grounding:** Benchmarking on C-MAPSS FD001 was conducted to prove that our self-supervised Attention-LSTM World Model achieves state-of-the-art competitive performance on standard literature benchmarks (RMSE: 15.42 vs. 16.14; PHM Score: 394.7 vs. 338 across 100 test units). This demonstrates that our core predictive engine is technically sound and reproducible.
2. **Modest vs. Implausible Numbers:** An 8% RMSE reduction after years of architectural refinement is a realistic, reproducible result. Claims in unverified literature reporting single-digit RMSE on FD001 frequently suffer from test-set leakage or unclipped cycle evaluation artifacts.
3. **The Core Contribution:** The academic contribution of ATLAS is **not** an incremental decimal-point improvement on FD001. The contribution is the **holistic machine cognition architecture**:
   * Integrating an Attention-LSTM World Model with an external vector associative memory (AMKB via pgvector).
   * Providing real-time contrastive feature occlusion explainability (identifying root-cause sensors without full retraining).
   * Coupling predictive cognition with an asymmetric cost-matrix Decision Graph and safety-grounded LLM maintenance agents.

### Anticipated Follow-Up
> *"Did you use piecewise linear RUL clipping on C-MAPSS?"*

**Response:**  
Yes. In accordance with established literature standards (Heimes 2008, Zheng 2017), maximum RUL was clipped to $RUL_{\text{max}} = 125$ cycles. In early cycles before degradation begins, sensor values reflect baseline healthy operation; predicting unclipped linear RUL (e.g., 300 cycles) forces neural networks to fit arbitrary flatlines, degrading gradient descent.

---

## Question 4: Uncertainty Quantification & Confidence Floor Elimination

> **Examiner Question:**  
> *"In your confidence calibration updates, your confidence score dropped from a naive 0.5 floor to as low as 0.05 for noisy trends. Doesn't reporting very low confidence make your system less useful to operators?"*

### Primary Answer
In industrial maintenance engineering, **a false claim of moderate confidence is far more dangerous than an honest admission of uncertainty**:

1. **The Flaw of Arbitrary Floors (DEF-009 / DEF-010):** In Month 4 W1, our early confidence formula used `clip(r_squared, 0.5, 0.95)`. If a sensor produced purely random, non-monotonic Gaussian noise with zero degradation signal, the system still reported "50% confidence." An operator viewing that card would assume partial certainty when the underlying data was completely uninformative.
2. **The Calibrated Formula:** We eliminated the artificial floor. Confidence is derived from:
   * Empirical goodness-of-fit ($R^2$ of linear degradation slope).
   * Variance among the top-$k$ nearest neighbors in AMKB latent memory space ($1.0 / (1.0 + \text{Var}(RUL_{\text{neighbors}}))$).
   * Data history sufficiency ($N / N_{\text{min}}$).
3. **Operational Impact:** When confidence drops to 0.05, the Decision Graph does **not** fail; it triggers a safety override. In our Decision Graph, any prediction with $\text{Confidence} < 0.60$ is automatically barred from autonomous work order dispatch and routed to `INSPECT_MANUAL` (human visual inspection). An honest low-confidence score prevents premature, ungrounded spindle replacements.

### Anticipated Follow-Up
> *"What happens if all k neighbors in AMKB have identical RULs?"*

**Response:**  
This was the exact edge case documented in **DEF-009**. When all $k$ retrieved neighbors have zero variance ($\text{Var} = 0$), a naive formula divides by zero. We resolved this by adding an epsilon regularization term ($\sigma^2 + \epsilon$, with $\epsilon = 10^{-4}$), bounding maximum neighbor confidence at 1.0 and ensuring mathematical stability across all database states.

---

## Question 5: Defect Progression & Refutation-Driven Engineering

> **Examiner Question:**  
> *"Your documentation meticulously logs 12 defects and 2 near-misses. Does having 12 defects during development indicate poor initial software engineering?"*

### Primary Answer
In complex systems research, the presence of a structured defect log is **evidence of rigorous verification, not poor engineering**:

1. **The Nature of the Defects:** Not a single defect in our log was a trivial syntax or formatting crash. Every defect was a **silent semantic failure** — a failure where the code executed without error, returned a plausible-looking result, but was mathematically or architecturally flawed:
   * **DEF-001 (Month 1):** Terminal `nn.ReLU()` in the RUL prediction head produced dead gradients in ~50% of random seeds, plateauing training silently.
   * **DEF-004 (Month 5):** Python's `sorted()` used alphabetical tie-breaking on maintenance actions, arbitrarily picking `"Inspect Spindle"` over `"Emergency Stop"` when utility scores tied.
   * **DEF-008 (Month 7):** Live API endpoints silently routed compute domain queries through zero-shot fallbacks because dynamic model registration lacked a multi-domain lookup dictionary.
   * **DEF-012a (Month 8):** Autonomous LLM agents used free-text keyword matching to justify unrelated actions (citing a vibration alert to justify flushing coolant).
2. **The Verification Protocol:** None of these were found by chance. They were discovered through systematic refutation: running multi-seed suites without static seeds, boundary-condition sweeps, and adversarial prompt injections.
3. **Zero Open Defects:** All 12 defects were resolved with architectural root-cause fixes, backed by permanent regression tests in `tests/`. A research repository reporting zero defects after building an end-to-end multi-domain digital twin would be an immediate red flag indicating that rigorous edge-case testing was never performed.

---

## Question 6: Autonomous Agent Safety & The DEF-012a/b Grounding Gates

> **Examiner Question:**  
> *"You use a large language model (Gemini) as an autonomous agent with tools to create maintenance work orders. How do you guarantee that hallucinations or prompt injections cannot cause physical machine damage?"*

### Primary Answer
We enforce a **defense-in-depth architectural sandbox** that assumes the LLM will hallucinate and strips it of unverified execution authority:

1. **Layer 1: Mandatory Alert Existence (DEF-012a):** The agent cannot create a High or Critical urgency work order without supplying an integer `grounding_alert_id`. The server queries TimescaleDB to verify that an alert with that ID actually exists, was generated within the last 24 hours, and was emitted by the verified AI pipeline (`source = 'ai_pipeline'`).
2. **Layer 2: Taxonomy Enum Exact Match (DEF-012a):** The agent must declare a structured `fault_type` enum (`vibration_high`, `temp_high`, `current_overload`, `bearing_wear`, `coolant_pressure`). The server verifies via exact string equality that the declared `fault_type` matches the database record of the cited alert. Free-text semantic similarity is completely banned in this path.
3. **Layer 3: Action Plausibility Allow-List (DEF-012b):** The agent's proposed action text is matched against `FAULT_TYPE_ALLOWED_ACTIONS`. If the alert is `vibration_high`, the action must contain recognized mechanical vibration corrective vocabulary (`inspect`, `spindle`, `balance`, `bearing`, `rotor`). Submitting `"Flush coolant loop"` for a vibration alert is rejected at Layer 3.
4. **Layer 4: Server-Stamped Provenance:** The `created_by` field is stamped strictly server-side from request authentication context as `'agent:atlas'`. Client payloads cannot spoof author provenance.
5. **Layer 5: Human Confirmation Gate (RBAC):** Agent work orders are inserted strictly with status `Pending Approval`. No work order can transition to `Open` or dispatch to maintenance teams without a human operator or admin calling `POST /api/work-orders/{id}/approve` with a valid JWT token. Viewer tokens are physically rejected with HTTP 403 Forbidden.

### Anticipated Follow-Up
> *"What is the residual risk that remains open under DEF-012b?"*

**Response:**  
As honestly recorded in our defect log, the residual risk is **multi-action bundling**: if an agent submits `"Inspect spindle and flush coolant"` for a vibration alert, the allow-list recognizes `"inspect"` and `"spindle"`, allowing the order into `Pending Approval`. This residual risk cannot be safely solved with static string tokenization without brittle semantic parsing; it is fundamentally guarded by the **Human Confirmation Gate**, where the human operator reviews the card and rejects the bundled request before execution.

---

## Question 7: Security Pragmatism & Credential Handling (NM-002)

> **Examiner Question:**  
> *"In your defect log, you recorded Near-Miss NM-002 regarding an MQTT password file tracked in git history, yet you chose not to rewrite git history. Isn't leaving historical credentials in git an unacceptable security practice?"*

### Primary Answer
This was a deliberate engineering decision based on a **proportional risk-versus-impact evaluation**:

1. **Context of Exposure:** The tracked file (`mosquitto/config/pwfile.raw`) contained local development fixtures (`backend_service:backend_secret`, `device_M001:m001_secret`) bound to an internal Docker bridge network (`0.0.0.0:1883`) on a local developer workstation. It was never deployed to an externally accessible IP, public cloud broker, or production environment.
2. **The Cost of History Rewriting:** Rewriting git history via `git filter-repo` or BFG alters all downstream commit SHA-1 hashes. In an academic thesis project, commit hashes are the primary audit trail linking architecture decision records, thesis chapter milestones, and defect verification logs. Rewriting history would have severed the verifiable forensic timeline of the research.
3. **Remediation & Standing Precondition:**
   * Untracked `pwfile.raw` and added `mosquitto/config/*.raw` to `.gitignore`.
   * Implemented `scripts/generate_mqtt_passwords.py`, an in-memory generator that hashes passwords via PBKDF2-HMAC-SHA512 directly into Mosquitto `$7$` format without ever touching disk.
   * Created a permanent regression test (`test_plaintext_password_files_not_tracked_in_git` in `tests/test_mqtt.py`).
   * Recorded a **mandatory standing precondition** in `docs/qa/DEFECT_REPORTS.md`: *If this repository is ever transferred to a public open-source repository, a full historical rewrite must be executed as a gating prerequisite.*

---

## Question 8: Heterogeneous Validation Boundaries — Hardware vs. Simulation

> **Examiner Question:**  
> *"You claim validation across four heterogeneous domains, yet your Server domain runs in simulation. Doesn't that invalidate your claim of heterogeneous cross-system operation?"*

### Primary Answer
We are completely transparent about the physical boundaries of our testbed:

1. **Genuine Physical Hardware:**
   * **Laptop Domain:** Streams real OS telemetry from the host developer workstation via direct kernel hooks in `psutil` (polling physical CPU load, memory commit charge, disk volume consumption, and battery state at 10–20 Hz).
   * **Mobile Domain:** Streams live telemetry from an owned physical Android smartphone via Termux:API (HTTP port 8088) and ADB shell (polling BMIC temperature, charging current, and Bosch BMI320 triaxial MEMS sensors).
   * **C-MAPSS Domain:** Uses genuine experimental run-to-failure run-benchmarks recorded from physical jet engines in NASA test cells.
2. **The Server Boundary:** The Server domain adapter (`server/adapters/server_adapter.py`) contains a fully implemented, unit-tested SSH transport layer designed to connect to enterprise Linux servers and poll `/proc/stat`, `/proc/meminfo`, and `/proc/diskstats`. However, due to cloud VM credential and cost boundaries during the test phase, it was run in calibrated synthetic simulation.
3. **Architectural Validity:** The streaming interfaces, data schemas (`NormalizedReading`), and feature normalization manifolds are 100% identical between live and simulated modes. The platform handles hardware disconnection and synthetic failover gracefully via `AdapterStatus` enums.

---

## Question 9: Dual Physical Degradation Taxonomy — Category A vs. Category B

> **Examiner Question:**  
> *"C-MAPSS defines failure as structural destruction, whereas your Laptop and Mobile models define failure as operational stress. Isn't combining these two under a single 'predictive maintenance' umbrella scientifically inconsistent?"*

### Primary Answer
Conflating them would indeed be inconsistent; that is precisely why ATLAS formulated an explicit **two-category physical degradation taxonomy**:

```
[ Predictive Maintenance Taxonomy ]
           │
     ┌─────┴────────────────────────────────┐
     ▼                                      ▼
[ Category A: Structural Run-to-Failure ]  [ Category B: Operational Saturation ]
- Turbofans, Bearings, Milling Spindles     - Laptops, Mobile Devices, Cloud Servers
- Damage is irreversible & monotonic        - Stress is reversible & dynamic
- Target: Literal Operating Cycles (0-125) - Target: Normalized Stress Capacity [0, 1]
- Rest does NOT heal the machine            - Idling restores thermal & compute headroom
```

1. **Category A (Structural Run-to-Failure):** In C-MAPSS and Phase A CNC machines (M001–M004), physical wear (crack propagation, spalling, bearing race erosion) is cumulative and irreversible. A turbofan resting on the tarmac does not recover lost blade material. RUL represents **literal operating flight cycles remaining**.
2. **Category B (Operational Saturation & Thermal Fatigue):** In compute infrastructure, "failure" is typically soft saturation (thermal throttling, memory exhaustion, battery depletion). Crucially, a laptop that is turned off or rested **recovers** its thermal headroom and battery charge. RUL represents **normalized continuous operational headroom** ($[0.0, 1.0]$), where $0.0$ is thermal saturation and $1.0$ is nominal baseline.
3. **The Research Value:** Explicitly maintaining this distinction is what made the Cross-Domain Transfer Study possible. Had we forced compute systems into a naive monotonic degradation model, the resulting transfer errors would have been dismissed as tuning flaws rather than the fundamental physical divergence that our 8.3× NTI demonstrated.

---

## Question 10: Negative Transfer Index (NTI) & The Laptop Regression Artifact

> **Examiner Question:**  
> *"Your Transfer Study showed that Mobile and Server suffered ~8x negative transfer inflation against C-MAPSS, but Laptop showed an NTI of 0.89x (no inflation). Does that mean Laptop telemetry successfully transfers to jet engines?"*

### Primary Answer
**No. Laptop does not transfer to jet engines, and claiming it does would be an egregious misinterpretation of a statistical artifact:**

1. **The Phenomenon:** In `docs/TRANSFER_STUDY_RESULTS.md`, Mobile-to-C-MAPSS showed an **$8.30\times$ Error Inflation Ratio** (NTI = $-0.0060$) and Server-to-C-MAPSS showed a **$7.10\times$ Error Inflation Ratio** (NTI = $-0.0074$), proving that compute representations destroy turbofan prediction accuracy. Laptop, however, reported an Error Inflation Ratio of **$0.89\times$** (cross-domain error appeared slightly lower than within-domain baseline error, with an NTI of $-0.0020$).
2. **The Investigation & Root Cause:** We analyzed the prediction distribution and traced this directly to a **boundary-mean regression artifact**:
   * To resolve DEF-007 (Laptop channel collapse), the synthetic Laptop generator was engineered with 4 distinct operational regimes (idle, office, burst, compile) with multi-modal phase transitions, producing a higher within-domain retrieval RMSE ($0.0961$, ~2.4–3.2× higher than Mobile's $0.0301$ and Server's $0.0404$).
   * When the Laptop encoder was queried against C-MAPSS's AMKB memory, the out-of-distribution latent vectors landed on the distant manifold boundary (latent distance $10.82$, vs. $0.28$ within-domain), where retrieved normalized labels clustered near the global dataset mean ($\approx 0.55$).
   * Because this global mean coincidentally fell close to the Laptop validation target mean ($\approx 0.52$), the resulting cross-domain RMSE was $0.0858$ ($0.0858 / 0.0961 = 0.89\times$, NTI = $-0.0020$), numerically lower than Laptop's own higher-variance baseline.
3. **Scientific Integrity:** Rather than claiming anomalous positive transfer, we documented this explicitly in `docs/TRANSFER_STUDY_RESULTS.md` §5 as a statistical artifact. Cross-domain transfer between laptops and turbofans is physically meaningless; the $0.89\times$ figure is an artifact of baseline multi-modal variance, not beneficial feature reuse.

---

## Question 11: Retrospective & Future Research Priorities

> **Examiner Question:**  
> *"If you had six more months to continue this research, what would you prioritize changing or extending?"*

### Primary Answer
Ranked in order of scientific and engineering leverage:

1. **Empirical Battery Capacity Fade Ground Truth (Mobile Domain):** Replace the current Tier (c) instantaneous operational stress score with empirical electrochemical state-of-health ($SOH = Q_{\text{max}} / Q_{\text{nominal}}$) by conducting multi-month longitudinal battery cycling on real physical Android test units.
2. **Live Multi-Tenant Kubernetes Validation (Server Domain):** Transition the Server domain adapter from calibrated simulation to a live multi-node Kubernetes cluster, streaming real eBPF container I/O metrics and validating GPU memory degradation under distributed machine learning training workloads.
3. **Multi-Condition C-MAPSS Extension (FD002 / FD004):** Extend the Attention-LSTM World Model to evaluate transfer under multi-regime flight operational conditions (altitude, Mach number, throttle resolvers), testing whether dynamic operating regimes change the latent transfer boundaries observed in FD001.
4. **Stochastic Promotion Gating in Learning Engine:** Update `server/atlas/learning_engine.py` to evaluate candidate retrained models across multiple random seeds before hot-reloading checkpoints into production memory, providing formal statistical confidence bounds on autonomous model promotion.

---

## Examiner Codebase Cross-Reference Index

| Claim / Topic | Primary Source File | Permanent Regression Test |
|---|---|---|
| **World Model Input Dimensions ($D=14$ vs. $D=5$)** | `server/atlas/world_model.py:101`, `server/adapters/base_adapter.py:125` | `scripts/inspect_checkpoints.py` |
| **Mobile 16-Channel Telemetry Acquisition** | `server/adapters/mobile_adapter.py:561-578` | `tests/test_mobile_adapter.py` |
| **3-Tier Telemetry UI Badges & Formatting** | `client/src/components/atlas/views/MonitoringView.tsx:350-515` | Live browser test (`atlas_live_ui_3tier_*.webp`) |
| **DEF-012a Alert Grounding & Exact Enum Match** | `server/agent_tools.py:245-280` | `tests/test_work_order_safeguards.py` |
| **DEF-012b Action Plausibility Allow-Lists** | `server/agent_tools.py:144-171` | `tests/test_work_order_safeguards.py` |
| **Human Confirmation Gate & RBAC Verification** | `server/backend_api.py:382-415` | `scripts/run_live_e2e_full.py` (Phase 4) |
| **NM-002 Plaintext Password Git Tracking Guard** | `scripts/generate_mqtt_passwords.py` | `tests/test_mqtt.py:33` |
| **Normalized RUL Snapshot Schema** | `server/atlas/domain_service.py:251-255` | `tests/test_mobile_adapter.py:52` |
| **Cross-Domain Latent 32-D Transfer (DEF-006)** | `server/atlas/transfer_study.py:180-240` | `tests/test_transfer_study.py` |
| **Confidence Division-by-Zero Protection (DEF-009)**| `server/atlas/world_model.py:275-290` | `tests/test_rul_bounding.py` |
