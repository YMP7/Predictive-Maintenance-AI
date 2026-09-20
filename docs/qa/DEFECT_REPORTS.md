# ATLAS Defect Reports

**Project:** ATLAS — An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems
**Document Type:** Structured Defect Log (As-Built, Retrospective)
**Date:** 2026-08-25

> [!NOTE]
> This defect log was compiled from the Architecture Decisions Log in
> [`ATLAS_PROJECT_CONTEXT.md`](../../../ATLAS_PROJECT_CONTEXT.md) §6b and verified against
> the git commit history. All defects listed were discovered and fixed during development.
> This project did not use a formal issue tracker; the Decisions Log served that role.

---

## Defect Register Summary

| ID | Defect | Month | Severity | Status |
|---|---|---|---|---|
| DEF-001 | Dead-gradient ReLU in RUL prediction head | 1 W3 | **Critical** | ✅ Fixed & verified |
| DEF-002 | Row-order silent corruption in preprocessing | 1 W2 | **High** | ✅ Fixed & verified |
| DEF-003 | Cosine distance/similarity inversion in explainability | 4 W2 | **High** | ✅ Fixed & verified |
| DEF-004 | Alphabetical tie-breaker safety risk in Decision Graph | 5 | **Critical** | ✅ Fixed & verified |
| DEF-005 | Fixed-cost blind spot in cost model ignoring urgency | 5 | **Critical** | ✅ Fixed & verified |
| DEF-006 | Padding-artifact NTI methodology flaw in Transfer Study | 7 W2 | **High** | ✅ Fixed & verified |
| DEF-007 | Laptop channel collapse in domain pre-training | 7 W2 | **Medium** | ✅ Fixed & verified |
| DEF-008 | Live API silently using zero-shot fallback instead of trained encoders | 7 W4 | **High** | ✅ Fixed & verified |
| DEF-009 | Confidence formula division-by-zero risk with zero-variance neighbors | 4 W1 | **High** | ✅ Fixed & verified |
| DEF-010 | Spearman rank correlation undefined for zero-variance ungrounded confidence | 7 W3 | **Medium** | ✅ Fixed & verified |
| DEF-011 | Unseeded PyTorch RNG state carry-over between domain training calls | 7 W2 | **Medium** | ✅ Fixed & verified |
| DEF-012 | Cross-fault ungrounded action justification in LLM work orders | 8 W4 | **Medium** | ✅ Fixed & verified (DEF-012a Closed; DEF-012b Residual bounded) |

All 12 defects have been resolved or verified with explicit boundary disclosures. Zero unmitigated defects remain.

### Near-Miss Registry

| ID | Near-Miss | Month | Mitigated By |
|---|---|---|---|
| NM-001 | InMemoryAMKB offline fallback could silently diverge from pgvector cosine distance | 8 W3 | Equivalence test proving < 10⁻⁵ drift (`tests/test_evaluation_cli.py`) |
| NM-002 | Plaintext MQTT development credentials tracked in git (`pwfile.raw`) | Phase 5 / 8 W4 | Untracked, gitignored, in-memory generator (`scripts/generate_mqtt_passwords.py`), standing pre-publication rewrite rule |

---

## DEF-001: Dead-Gradient ReLU in RUL Prediction Head

| Field | Detail |
|---|---|
| **ID** | DEF-001 |
| **Severity** | **Critical** — renders training completely non-functional in ~50% of random seeds |
| **Month** | 1 Week 3 |
| **File** | `server/atlas/world_model.py` |
| **Commit (fix)** | Part of Month 1 W3 deliverable |

### Description
The original `rul_head` architecture included `nn.ReLU()` as the final activation layer. When `Linear(16→1)` random initialization produces negative outputs (which occurs in approximately 50% of random seeds), the terminal ReLU clips every prediction to exactly `0.0` — resulting in zero standard deviation, zero gradient, and completely broken training that **appears to proceed normally** (loss plateaus at a constant value rather than diverging).

### Root Cause
Architectural design error — applying a non-negativity constraint as a final activation rather than as a post-inference clamp. MSE loss requires unrestricted gradients through the output layer to push raw outputs toward the correct sign.

### How Found
Multi-seed diagnostic (5 seeds without `manual_seed`): all seeds with negative initial weights produced identical zero-output predictions with zero variance across the entire batch.

### Fix Applied
Removed terminal `nn.ReLU()` from `rul_head`. Non-negativity is now enforced at inference time via `torch.clamp(min=0)` in the `predict()` method, which does not block training gradients.

### Verification
Post-fix multi-seed diagnostic confirmed: all 5 seeds produced genuine nonzero standard deviation, values spanning both positive and negative ranges through the encoder, confirmed no init-dependent dead output. Tests in `test_rul_bounding.py` verify non-negative prediction output.

**Source:** `ATLAS_PROJECT_CONTEXT.md` §6b, Month 1 W3 entry (line 364)

---

## DEF-002: Row-Order Silent Corruption in Preprocessing

| Field | Detail |
|---|---|
| **ID** | DEF-002 |
| **Severity** | **High** — produces silently wrong training data; shape checks pass |
| **Month** | 1 Week 2 |
| **File** | `ml/preprocessing.py` |
| **Commit (fix)** | Part of Month 1 W2 deliverable |

### Description
Without explicit row ordering, the windowing pipeline would produce feature windows that are correct in shape `(30, 14)` but **silently wrong in temporal ordering** if the raw C-MAPSS file contains out-of-order rows. Standard shape validation (`assert X.shape == (N, 30, 14)`) would not catch this — the bug is invisible to all automated checks except manual inspection of window content.

### Root Cause
Missing assumption: the raw data files are not guaranteed to be sorted by `(unit_number, time_in_cycles)`.

### How Found
Code review during preprocessing pipeline construction.

### Fix Applied
Added `sort_values(["unit","cycle"]).reset_index(drop=True)` at the top of `compute_train_rul` in `ml/preprocessing.py`.

### Verification
Shape and content validation confirmed correct temporal ordering across all 100 C-MAPSS FD001 units. Resulting arrays have no NaN/Inf values and RUL labels are monotonically decreasing within each unit's window sequence.

**Source:** `ATLAS_PROJECT_CONTEXT.md` §6b, Month 1 W2 entry (line 363)

---

## DEF-003: Cosine Distance/Similarity Inversion in Explainability

| Field | Detail |
|---|---|
| **ID** | DEF-003 |
| **Severity** | **High** — inverts the confidence calibration signal |
| **Month** | 4 Week 2 |
| **File** | `server/atlas/explain.py` |
| **Commit (fix)** | `dee527d` — `fix: invert cosine distance to similarity and fix near-zero bounds` |

### Description
The explainability module was computing confidence using raw cosine **distance** (where higher = more different) instead of cosine **similarity** (where higher = more similar). This inverted the confidence calibration: units with near-identical AMKB neighbors received low confidence scores instead of high ones.

### Root Cause
Confusion between pgvector's `<=>` cosine distance operator (which returns `1.0 - cos(θ)`, so 0 = identical) and the desired confidence semantics (higher = more confident).

### How Found
Confidence calibration sanity check during Month 4 explainability development.

### Fix Applied
Inverted the distance-to-confidence mapping and fixed near-zero boundary handling in the confidence formula: `confidence = (1 / (1 + distance)) * (1 / (1 + variance))`.

### Verification
Post-fix Spearman rank correlation ($r_s = -0.5090$) confirms strong negative correlation between confidence and true prediction error — high confidence correctly aligns with low error.

**Source:** Git commit `dee527d`, `ATLAS_PROJECT_CONTEXT.md` §6b Month 4 arc

---

## DEF-004: Alphabetical Tie-Breaker Safety Risk in Decision Graph

| Field | Detail |
|---|---|
| **ID** | DEF-004 |
| **Severity** | **Critical** — silently favors inaction at near-failure |
| **Month** | 5 |
| **File** | `server/atlas/simulation.py` |
| **Commit (fix)** | Part of `9906fa0` |

### Description
The initial tie-breaker logic in the Decision Graph used Python's default string sort to break cost ties, which silently favored `CONTINUE_OPERATION` over `SCHEDULE_MAINTENANCE_*` actions (because 'C' < 'S' alphabetically). This created a dangerous default to inaction when expected costs were identical or near-identical.

### Root Cause
Implicit reliance on Python's `sort()` stability and string ordering for safety-critical action ranking.

### How Found
Safety verification testing during Month 5 Decision Graph development — borderline cases where multiple actions had similar expected costs.

### Fix Applied
Replaced alphabetical tie-breaking with a deterministic, safety-prioritizing cascade: `expected_cost → p_failure_before_action → cost_std → action_name`. This ensures that when costs are tied, the action with higher failure probability (i.e., the more urgent/safer intervention) wins.

### Verification
`test_decision.py` includes explicit tie-breaker ordering tests verifying that safety-prioritizing actions win under equal expected costs. Ablation 3 confirms 100% near-failure catch rate for both ATLAS and baseline pipelines.

**Source:** `ATLAS_PROJECT_CONTEXT.md` §6b, Month 5 arc (line 318)

---

## DEF-005: Fixed-Cost Blind Spot in Cost Model Ignoring Urgency

| Field | Detail |
|---|---|
| **ID** | DEF-005 |
| **Severity** | **Critical** — CONTINUE_OPERATION falsely wins at near-failure |
| **Month** | 5 |
| **File** | `server/atlas/simulation.py` |
| **Commit (fix)** | Part of `9906fa0` |

### Description
The initial cost model evaluated maintenance interventions (`SCHEDULE_MAINTENANCE_SOON`, `NOW`, `REPLACE_IMMEDIATELY`) as fixed costs, while `CONTINUE_OPERATION` was evaluated dynamically with risk-adjusted expected failure cost. This structural asymmetry meant `CONTINUE_OPERATION` (dynamic cost, sometimes low) could falsely beat fixed-cost interventions even at near-failure, because the intervention costs didn't account for the risk-exposure time horizon.

### Root Cause
Missing concept: maintenance actions also have a risk-exposure window (the lead time during which failure can still occur before the action takes effect).

### How Found
Identified during cost model evaluation when near-failure units were being recommended `CONTINUE_OPERATION` despite imminent failure risk.

### Fix Applied
Introduced explicit `ACTION_LEAD_TIME` table: `CONTINUE_OPERATION` = 30 cycles, `SCHEDULE_MAINTENANCE_SOON` = 10 cycles, `SCHEDULE_MAINTENANCE_NOW` = 3 cycles, `REPLACE_IMMEDIATELY` = 0 cycles. All actions now face genuine risk-exposure horizons, and urgency strictly drives the ranking through piecewise cost calculation.

### Verification
Ablation 1 demonstrates that the full ATLAS pipeline with lead-time modeling achieves 47.17% lifecycle cost savings over naive thresholding, with zero missed imminent failures ($t_{\text{true}} \le 5$).

**Source:** `ATLAS_PROJECT_CONTEXT.md` §6b, Month 5 arc (line 317)

---

## DEF-006: Padding-Artifact NTI Methodology Flaw in Transfer Study

| Field | Detail |
|---|---|
| **ID** | DEF-006 |
| **Severity** | **High** — produces invalid transfer study metrics |
| **Month** | 7 Week 2 |
| **File** | `server/atlas/transfer_study.py` |
| **Commit (fix)** | `366dcbe` — `fix(atlas): refine transfer study with AMKB latent retrieval, deterministic seeds, and laptop asymmetry analysis` |

### Description
The initial transfer study implementation used **zero-padding** to match the 14-dimensional C-MAPSS feature space when evaluating cross-domain retrieval from 5-dimensional compute domain encoders. This introduced a padding artifact: the 9 zero-padded dimensions dominated the cosine distance calculation, producing artificially inflated NTI values that measured dimensional mismatch rather than genuine semantic transfer failure.

### Root Cause
Naive dimensional alignment — appending zeros to match vector dimensions instead of operating in the shared 32-dimensional latent space where all domain encoders produce comparable representations.

### How Found
Analysis of NTI results during Month 7 W2 revealed implausibly high and uniform cross-domain distances that correlated with the number of padded dimensions rather than with semantic content.

### Fix Applied
Replaced zero-padding with **AMKB 32-dimensional latent $k$-NN memory retrieval** — cross-domain transfer is now tested by querying one domain's AMKB using legitimate 32-dimensional state vectors extracted from another domain's encoder. This tests genuine semantic memory transfer without dimensional mismatch distortion.

### Verification
Post-fix NTI values show physically meaningful patterns: compute-to-C-MAPSS transfer shows 7.1×–8.3× RMSE inflation (genuine negative transfer), while within-domain retrieval shows minimal error (NTI ≈ 0). `test_transfer_study.py` validates NTI computation correctness.

**Source:** `ATLAS_PROJECT_CONTEXT.md` §6b, Month 7 W2 (line 289); Git commit `366dcbe`

---

## DEF-007: Laptop Channel Collapse in Domain Pre-Training

| Field | Detail |
|---|---|
| **ID** | DEF-007 |
| **Severity** | **Medium** — produces degenerate latent space for one domain |
| **Month** | 7 Week 2 |
| **File** | `server/atlas/pretrain_domain.py`, data generation code |
| **Commit (fix)** | `c94c625` (initial), refined in `366dcbe` |

### Description
Early synthetic laptop telemetry generation produced nearly static channels (`disk ≈ 0.58`, `mem ≈ 0.60` constant), allowing the self-supervised Attention-LSTM reconstruction loss to be minimized by ignoring dynamic CPU burst patterns. The resulting latent space showed near-zero directional separation (Cosine Distance = 0.0670, below the 0.20 non-collapse threshold), indicating that the encoder had collapsed to a trivial constant mapping.

### Root Cause
Synthetic data generation lacked multi-modal operating regimes — the laptop simulator produced homogeneous workload patterns insufficient to force the encoder to learn discriminative temporal features.

### How Found
Non-collapse guard check (`Cosine Dist ≥ 0.20`) failed during domain pre-training validation.

### Fix Applied
Refactored `generate_laptop_windows` into four realistic multi-modal regimes (idle, office, burst, compile) with distinct CPU/memory/disk/network signatures. Established strict non-collapse guards (Cosine Dist ≥ 0.20, Euclidean Dist ≥ 0.50) as hard requirements, reinforced by decoupled hardcoded regression tests in `test_domain_pretraining.py`.

### Verification
Post-fix laptop domain pre-training passes both collapse guards. `test_domain_pretraining.py` includes explicit non-collapse assertion tests with the 0.20/0.50 thresholds.

**Source:** `ATLAS_PROJECT_CONTEXT.md` §6b, Month 7 W2 (line 338)

---

## DEF-008: Live API Silently Using Zero-Shot Fallback Instead of Trained Encoders

| Field | Detail |
|---|---|
| **ID** | DEF-008 |
| **Severity** | **High** — live API returns degraded results without any error indication |
| **Month** | 7 Week 4 |
| **File** | `server/atlas/adaptive_context.py` |
| **Commit (fix)** | `cc6b951` — `fix(atlas): resolve multi-domain encoder routing, annotate learning audit trail, and verify evaluation suite` |

### Description
After domain-specific World Models were trained in Month 7 W2, the live API endpoints (`/api/context`, `/api/decide`, `/api/explain`) for laptop, mobile, and server domains were still routing through a zero-shot stub fallback instead of loading the actual pretrained Attention-LSTM checkpoints from disk. The API returned valid-looking responses (no errors), but the underlying state vectors were computed by an untrained model rather than the domain-adapted encoder.

### Root Cause
Missing model registry — `AdaptiveContextEngine` was initialized with only the C-MAPSS World Model path hardcoded at startup. No dynamic model resolution existed for compute domains.

### How Found
System audit during Month 7 W4 evaluation suite consolidation — cross-checking live API output quality against evaluation harness output revealed discrepancies.

### Fix Applied
Implemented multi-domain WorldModel registry with dynamic `get_world_model` disk resolution in `AdaptiveContextEngine`. Each domain query now resolves to the correct pretrained checkpoint (`laptop_world_model.pt`, `mobile_world_model.pt`, `server_world_model.pt`) at query time.

### Verification
`test_adaptive_context.py` includes multi-domain model resolution tests. The evaluation suite (`scripts/evaluate_atlas.py`) independently loads all 4 domain models and produces identical results to the live API path.

**Source:** `ATLAS_PROJECT_CONTEXT.md` §6b, Month 7 W4 (line 281); Git commit `cc6b951`


> [!IMPORTANT]
> **Defect pattern:** The most critical defects (DEF-001, DEF-004, DEF-005) all share a common
> characteristic: they produce **plausible-looking output** that passes basic sanity checks but
> is fundamentally wrong. This project's most valuable testing discipline has been multi-seed
> evaluation, boundary-case analysis, and cross-checking outputs against independent sources —
> not just "does it run without errors."

---

## DEF-009: Confidence Formula Division-by-Zero Risk with Zero-Variance Neighbors

| Field | Detail |
|---|---|
| **ID** | DEF-009 |
| **Severity** | **High** — produces infinity or NaN in confidence output |
| **Month** | 4 Week 1 |
| **File** | `server/atlas/explain.py` |
| **Commit (fix)** | `1ce90ab` |

### Description
The initial confidence formula design used naive inverse variance (`1 / variance`) to map AMKB neighbor RUL spread to a confidence score. When all k neighbors have identical RUL (variance = 0), this produces division by zero — resulting in `Inf` or `NaN` confidence that silently propagates through the decision pipeline.

### Root Cause
Missing epsilon guard in the mathematical formula specification.

### How Found
Design review during Month 4 Week 1 explainability planning — identified as a boundary case before implementation, not discovered in production.

### Fix Applied
Bounded the formula with epsilon guards: `confidence = (1 / (1 + distance)) * (1 / (1 + variance))`. Both terms are bounded to `(0, 1]` and never explode. Documented in the `ExplanationEngine` module docstring with the explicit rationale.

### Verification
`test_explain.py` includes an explicit all-neighbors-identical-RUL test case that exercises the variance=0 path.

**Source:** Git commit `1ce90ab` (verified: `feat: implement Explanation Engine Phase 1 with strict true_rul guarantees`, touches `server/atlas/explain.py`). The epsilon-guard design decision is documented in `ATLAS_PROJECT_CONTEXT.md` §6b Month 4 arc (line 312). This defect entry was reconstructed from user-provided design-review context during the QA documentation session; not independently located in a searchable project artifact prior to this retrospective.

---

## DEF-010: Spearman Rank Correlation Undefined for Zero-Variance Ungrounded Confidence

| Field | Detail |
|---|---|
| **ID** | DEF-010 |
| **Severity** | **Medium** — produces NaN in ablation results table if unhandled |
| **Month** | 7 Week 3 |
| **File** | `server/atlas/ablation_engine.py` |
| **Commit (fix)** | `f9aa8b1` |

### Description
Ablation 2 compares AMKB-grounded vs. ungrounded explainability. With `grounding_enabled=False`, the ExplanationEngine returns a hardcoded `0.50` (maximal uncertainty prior) for all 100 test units — zero variance. Spearman rank correlation is mathematically undefined when one variable has zero variance ($0/0$), and most implementations return `NaN` silently rather than erroring.

### Root Cause
The Spearman correlation was specified as the key Ablation 2 metric without considering the edge case where one experimental condition deliberately produces a constant output.

### How Found
Identified during ablation design review — the user explicitly flagged this as a foreseeable failure mode before implementation: *"the Spearman correlation for the ungrounded condition is mathematically undefined... most scipy/numpy implementations will return NaN rather than erroring."*

### Fix Applied
The ablation engine explicitly detects zero-variance confidence arrays and reports `"N/A (Zero Variance - Constant Prior)"` with an explanatory annotation in the results table, rather than propagating a bare `NaN`. The pure-NumPy Spearman implementation in `ablation_engine.py` includes the variance check.

### Verification
`test_ablations.py` validates that the ungrounded ablation path returns the explicit "N/A" label rather than NaN. `ABLATION_STUDY_RESULTS.md` Ablation 2 table carries the annotation.

**Source:** Git commit `f9aa8b1` (verified: `feat(atlas): complete Month 7 Week 3 cognition pipeline ablation study and deterministic evaluation suite`, touches `server/atlas/ablation_engine.py` and `tests/test_ablations.py`). The zero-variance edge case was flagged by the user during ablation design review and handled in this commit. This defect entry was reconstructed from user-provided design-review context during the QA documentation session; not independently located in a searchable project artifact prior to this retrospective.

---

## DEF-011: Unseeded PyTorch RNG State Carry-Over Between Domain Training Calls

| Field | Detail |
|---|---|
| **ID** | DEF-011 |
| **Severity** | **Medium** — produces non-reproducible latent spaces across runs |
| **Month** | 7 Week 2 |
| **File** | `server/atlas/pretrain_domain.py` |
| **Commit (fix)** | `c94c625` |

### Description
When training domain-specific World Models sequentially (laptop → mobile → server), the PyTorch global RNG state from the previous domain's training carried over into the next domain's initialization and training. This meant the server domain's latent space orientation depended on whether laptop training had run before it, producing non-reproducible cosine similarity matrices across independent runs.

### Root Cause
PyTorch's global `torch.manual_seed()` is process-wide. Sequential training calls without explicit re-seeding inherit the accumulated RNG state from all prior operations in the process.

### How Found
Discovered during transfer study development when cosine similarity matrices varied between independent executions despite identical data and architecture.

### Fix Applied
Explicit per-domain PRNG seeding: `laptop=101`, `mobile=102`, `server=103`. Each `pretrain_domain()` call resets the full PRNG state (`torch.manual_seed()`, `np.random.seed()`, `random.seed()`) before initialization and training.

### Verification
`test_domain_pretraining.py` validates deterministic latent space geometry (cosine/Euclidean distances match expected values within tolerance) across repeated runs with the fixed seeds.

**Source:** `ATLAS_PROJECT_CONTEXT.md` §6b Month 7 W2 (line 339); Git commit `c94c625`

---

## DEF-012: LLM Work Order Grounding Vulnerability — Cross-Fault Semantic Keyword Fragility

| Field | Detail |
|---|---|
| **ID** | DEF-012 (Split: DEF-012a / DEF-012b) |
| **Severity** | **Medium** — integrity risk under adversarial or highly eloquent LLM generation |
| **Month** | 8 Week 4 (Pre-Deployment Hardening) |
| **File** | `server/agent_tools.py`, `tests/test_work_order_safeguards.py` |
| **Commit (fix)** | Pre-Deployment Security Hardening (Phase 8 Agentic Safeguards) |

### Description
The original telemetry grounding gate in `create_work_order()` verified only that *any* High or Critical alert existed for the machine in the last 24 hours. Because it never inspected the alert's fault type, an autonomous LLM agent could exploit a genuine vibration alert to justify an unrelated coolant flush or electrical repair order. Initial mitigation via free-text keyword matching closed accidental hallucination but left an adversarial phrasing gap: an eloquent agent could weave vibration keywords into a coolant justification to bypass the check.

### Resolution: Structural Split into DEF-012a and DEF-012b

#### DEF-012a (Closed & Formally Verified): Mandatory 3-Tier Alert Grounding Gate
1. **Provenance Derivation (`created_by`):** Set strictly server-side as `'agent:atlas'`, never accepted as a client/agent-supplied parameter. Human-initiated work orders follow an independent authenticated pipeline with human accountability.
2. **Mandatory Alert ID & Structured Enum:** For autonomous High/Critical work orders, `grounding_alert_id` and structured `fault_type` are mandatory. Rejection occurs immediately if missing or unrecognized. Free-text keyword correlation fallback is completely removed for agent work orders.
3. **Three-Tier Server-Side Gate:**
   - **Layer 1 (Provenance & Temporal Validity):** Queries database verifying `grounding_alert_id` exists for `machine_id` within the last 24 hours with `source = 'ai_pipeline'` and satisfies the severity floor (`Critical` for Critical, `High`/`Critical` for High).
   - **Layer 2 (Structured Fault-Type Exact Match):** Validates that declared `fault_type` strictly matches `alert.fault_type` (`norm_fault_type == alert_fault_type`).
   - **Layer 3 (Action Plausibility Allow-List):** Validates that the requested `action` string contains recognized corrective action vocabulary from `FAULT_TYPE_ALLOWED_ACTIONS[norm_fault_type]` (e.g., `vibration_high` permits rotor rebalancing, alignment, spindle bearings; rejects coolant loop flushes).
4. **Verification (Proving Both Directions in `tests/test_work_order_safeguards.py`):**
   - *Exploit rejection:* Attempting a coolant repair against a vibration alert ID is rejected at Layer 2 (mismatched enum) or Layer 3 (implausible action text despite matching enum).
   - *False-positive prevention:* Parametrized test across all 5 taxonomy fault types (`vibration_high`, `temp_high`, `current_overload`, `bearing_wear`, `coolant_pressure`) proves that genuine, legitimate corrective actions backed by verified alerts pass validation cleanly into `Pending Approval`.

#### DEF-012b (Residual Multi-Action Bundling Boundary guarded by Human Confirmation Gate)
- **Residual Risk:** An agent could construct a multi-action compound sentence that combines a legitimate corrective action with an unrelated action (e.g., *"Balance spindle and flush coolant loop"*). Because Layer 3 matches tokens in `action`, the presence of "balance spindle" satisfies the plausibility gate for `vibration_high`.
- **Architectural Boundary:** This residual risk is explicitly bounded and guarded by the **Human Confirmation Gate**. All High/Critical work orders created by `'agent:atlas'` land in `Pending Approval` (never `Open`), requiring an authenticated Operator or Admin (`require_operator_or_admin` via `/api/work-orders/{id}/approve`) to review and approve before any physical maintenance action is executed. Autonomous execution is physically blocked by the state machine.

---

## Near-Miss: NM-001 — InMemoryAMKB Offline Fallback Divergence Risk

| Field | Detail |
|---|---|
| **ID** | NM-001 |
| **Category** | Near-miss (preventive mitigation, not a discovered failure) |
| **Month** | 8 Week 3 |
| **File** | `scripts/evaluate_atlas.py`, `tests/test_evaluation_cli.py` |

### Description
The standalone evaluation CLI (`evaluate_atlas.py`) provides an `InMemoryAMKB` fallback for environments without PostgreSQL/pgvector. This fallback re-implements cosine k-NN retrieval in pure NumPy. Without formal verification, this path could silently compute different results from the real pgvector `<=>` operator — producing different confidence scores, different ablation metrics, and different benchmark numbers depending on which evaluation path a reviewer uses.

### Mitigation
A formal equivalence test (`test_evaluation_cli.py`) mathematically proves that InMemoryAMKB and pgvector produce identical retrieval results within $< 10^{-5}$ tolerance. This test was written proactively during Month 8 W3 specifically to prevent this category of silent divergence.

### Why This Is a Near-Miss, Not a Defect
The divergence was identified as a **risk** and mitigated before it could produce incorrect results. No incorrect output was ever generated. However, the category is worth documenting because it represents the same class of failure as DEF-008 (silent fallback path computing different results) — and the formal equivalence test is the structural prevention.

**Source:** `ATLAS_PROJECT_CONTEXT.md` §6b Month 8 W3 (line 275); `tests/test_evaluation_cli.py`

---

## Near-Miss: NM-002 — Plaintext MQTT Development Credentials Tracked in Git

| Field | Detail |
|---|---|
| **ID** | NM-002 |
| **Category** | Security Hardening / Near-Miss |
| **Month** | Phase 5 (origin) / Month 8 Week 4 (remediation) |
| **File** | `mosquitto/config/pwfile.raw`, `mosquitto/config/pwfile` |

### Description
In Phase 5, the Docker compose initialization workflow for Eclipse Mosquitto relied on a plaintext password file (`mosquitto/config/pwfile.raw`) that was copied and hashed into `pwfile` at container startup via `mosquitto_passwd -U`. Because `pwfile.raw` was committed to git history, development credentials (`backend_service:backend_secret`, `device_M001:m001_secret`) remained visible in historical commit diffs (`git log -p`).

### Mitigation Applied
1. Untracked `mosquitto/config/pwfile.raw` from git tracking (`git rm --cached`).
2. Added `mosquitto/config/*.raw` and `mosquitto/config/pwfile.raw` to `.gitignore`.
3. Implemented a native in-memory PBKDF2-HMAC-SHA512 password generator (`scripts/generate_mqtt_passwords.py`) that hashes secrets directly in memory and writes the `$7$` formatted password file to disk without ever persisting plaintext.
4. Added a permanent regression test (`test_plaintext_password_files_not_tracked_in_git` in `tests/test_mqtt.py`) ensuring no `.raw` password files can be accidentally tracked.

### Deliberate Decision on Git History & Standing Precondition for Publication
> [!IMPORTANT]
> **Decision:** Git history was not rewritten, as the exposed credential is a non-production dev fixture. Should this repository ever be made public, a history rewrite (`git filter-repo` / BFG) **MUST** be performed first — this is a standing precondition for publication, not optional cleanup.

---

---

## Architectural Boundary Disclosure: 3-Tier Telemetry Classification (Mobile & Laptop)

To maintain rigorous transparency regarding telemetry provenance and prevent unvalidated claims, all telemetry channels across ATLAS domains are classified into three distinct confidence tiers:

### 1. Classification Taxonomy

1. **Tier (a) Directly Measured:** Acquired directly from hardware sensors, kernel accounting, or vendor driver APIs with zero mathematical transformation other than standard linear normalization into $[0.0, 1.0]$.
2. **Tier (b) Physically Derived (Validated):** Computed via deterministic physical laws or Euclidean norms from Tier (a) sensor vectors, with an empirical validation basis against physical ground truth (e.g. Earth gravitational acceleration $g = 9.81\text{ m/s}^2$ or ambient geomagnetic flux).
3. **Tier (c) Operational Heuristic Placeholders (Unvalidated):** Synthetic or weighted linear combinations of operating stress variables representing composite operational strain. These metrics **MUST NOT** be claimed as empirical degradation ground truth (such as battery capacity fade or structural crack growth).

---

### 2. Mobile Domain Channel Breakdown (16 Channels)

| Channel Name | Provenance Tier | Acquisition / Derivation Method | Physical Ground Truth / Reference |
|---|---|---|---|
| `battery_level` | **Tier (a) Directly Measured** | Android BatteryManager / Termux `/battery` API | BMIC Coulomb-counter state of charge (0–100%) |
| `battery_temp` | **Tier (a) Directly Measured** | Android `dumpsys battery` thermistor (`temperature: 320` $\rightarrow$ 32.0°C) | BMIC internal NTC thermistor |
| `battery_current` | **Tier (a) Directly Measured** | Android `dumpsys battery` `Max charging current` / `current_now` | BMIC internal current shunt resistor (mA) |
| `battery_voltage` | **Tier (a) Directly Measured** | Android `dumpsys battery` `voltage` (mV) | BMIC terminal cell voltage |
| `cpu_usage` | **Tier (a) Directly Measured** | Linux `/proc/stat` total vs. idle jiffies delta | Kernel scheduler runtime accounting |
| `memory_used_percent` | **Tier (a) Directly Measured** | Linux `/proc/meminfo` (`MemTotal` - `MemAvailable`) / `MemTotal` | Kernel memory manager accounting |
| `accel_x`, `accel_y`, `accel_z` | **Tier (a) Directly Measured** | Bosch Sensortec BMI320 3-axis MEMS accelerometer via `dumpsys sensorservice` | Triaxial capacitive MEMS deflection ($\text{m/s}^2$) |
| `gyro_x`, `gyro_y`, `gyro_z` | **Tier (a) Directly Measured** | Bosch Sensortec BMI320 3-axis MEMS gyroscope via `dumpsys sensorservice` | Triaxial Coriolis force deflection (rad/s) |
| `ambient_light` | **Tier (a) Directly Measured** | AMS / TCS3701 ambient light sensor via `dumpsys sensorservice` | Photodiode optical illuminance (Lux) |
| `proximity` | **Tier (a) Directly Measured** | AMS / TCS3701 IR proximity sensor via `dumpsys sensorservice` | IR VCSEL time-of-flight / reflection distance (cm) |
| `vibration_rms` | **Tier (b) Physically Derived** | $\frac{1}{20}\sqrt{a_x^2 + a_y^2 + a_z^2}$ | Validated against static baseline Earth gravity ($g = 9.81\text{ m/s}^2 \rightarrow \approx 0.49$) |
| `magnetic_field` | **Tier (b) Physically Derived** | $\frac{1}{100}\sqrt{m_x^2 + m_y^2 + m_z^2}$ from QMC6308 3-axis AMR magnetometer | Validated against ambient geomagnetic field ($30\text{--}60\ \mu\text{T} \rightarrow 0.3\text{--}0.6$) |
| `stress_score` (`health_index`) | **Tier (c) Operational Heuristic** | $0.35 T_{\text{batt}} + 0.25 C_{\text{cpu}} + 0.20 M_{\text{mem}} + 0.10 V_{\text{rms}} + 0.10(1 - B_{\text{lvl}})$ | **Unvalidated heuristic placeholder**. Represents instantaneous operational workload, NOT physical battery degradation. |

> [!NOTE]
> **Clarification on `battery_temp` and `storage_io_rate`:**
> 1. **`battery_temp` is directly measured:** In the real hardware pipeline (ADB/Termux), battery temperature is directly read from the hardware BMIC thermistor. The "voltage sag under load" formulation exists exclusively in the synthetic simulation fallback (`_generate_simulation_reading`) and is never used when real hardware is connected.
> 2. **Mobile does NOT have `storage_io_rate`:** Android user-space and Termux permissions restrict `/proc/diskstats` access without root eBPF capabilities. Storage I/O metrics exist exclusively in Laptop (`psutil.disk_io_counters`) and Server (`/proc/diskstats`).
> 3. **Model Dimensional Isolation:** The Mobile Attention-LSTM World Model checkpoint (`data/models/mobile_world_model.pt`) was trained strictly on the **5 canonical features** (`battery_level`, `battery_temp`, `battery_current`, `cpu_usage`, `memory_used_percent`). The 11 extended hardware channels are ingested for high-fidelity digital twin monitoring and physical engineering analysis, but are decoupled from the 5-dimensional neural encoder input. The Cross-Domain Transfer Study (8.3× NTI) operates exclusively in the canonical 5-dimensional feature space and is completely unpolluted.

---

## Updated Defect Trend Analysis

| Month | Defects Found | Severity Breakdown | Notes |
|---|---|---|---|
| Month 1 | 2 | 1 Critical, 1 High | Foundational architecture and data pipeline |
| Month 2 | 0 | — | AMKB/DNA built without structural bugs |
| Month 3 | 0 | — | Attention-LSTM escalation driven by multi-seed validation, not a bug |
| Month 4 | 2 | 2 High | Confidence inversion and division-by-zero boundary |
| Month 5 | 2 | 2 Critical | Both related to cost model soundness |
| Month 6 | 0 | — | Adapter layer cleanly implemented |
| Month 7 | 5 | 2 High, 3 Medium | Transfer study methodology, collapse, seed isolation, Spearman edge case |
| Month 8 | 1 (+2 near-misses) | 1 Medium | DEF-012 LLM grounding; NM-001 AMKB equivalence; NM-002 MQTT credentials |
| **Total** | **12 (+2 near-misses)** | **3 Critical, 5 High, 4 Medium** | **100% resolved or mitigated with boundary disclosures** |

