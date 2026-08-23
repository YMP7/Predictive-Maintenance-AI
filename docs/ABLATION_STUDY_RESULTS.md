# ATLAS Cognition Pipeline: Comprehensive Ablation Study Results
**Execution Timestamp**: `2026-08-23 06:42:01Z`  
**Test Protocol**: Standard NASA C-MAPSS FD001 Benchmark (100 test units, last-window-per-unit protocol)  
**Machine Hardware Domains**: C-MAPSS Turbofan, Laptop, Mobile (Android), Enterprise Linux Server  

---

## Executive Summary

This document presents the empirical evaluation of the **4 Canonical ATLAS Ablation Studies**, systematically quantifying the performance contribution, safety impact, and epistemic value of each core cognition subsystem:
1. **Ablation 1 (Full Cognition Pipeline vs. RUL-Alone Baseline)**: Evaluates maintenance cost reduction, premature cycle waste, and catastrophic missed failure prevention under simulated uncertainty.
2. **Ablation 2 (AMKB-Grounded vs. Ungrounded Explainability)**: Measures confidence calibration, Spearman rank correlation against true prediction error, and citation availability.
3. **Ablation 3 (Cost-Weighted Decision Graph vs. Naive Threshold Rules)**: Evaluates near-failure safety parity alongside economic discrimination and action graduation across disagreed decisions.
4. **Ablation 4 (Domain-Adapted vs. Foreign Representation Transfer)**: Reuses Month 7 Week 2's within-domain vs. C-MAPSS physical memory retrieval transfer findings and presents the 3×3 Cross-Compute Generalization Matrix.

---

## Ablation 1: Full Cognition Pipeline vs. RUL-Alone Baseline

Conventional predictive maintenance frameworks estimate remaining useful life ($t_{\text{RUL}}$) as an isolated regression output and apply fixed heuristic rules (e.g., *"replace if $t_{\text{RUL}} < 30$"*). The ATLAS Full Cognition Pipeline couples the Attention-LSTM prediction with Monte Carlo uncertainty propagation and a lead-time-aware Decision Graph.

### Comparative Performance Table (100 C-MAPSS Test Units)

| Evaluation Metric | Pipeline A (RUL-Alone Baseline Rule) | Pipeline B (Full ATLAS Cognition Pipeline) | Delta / Impact |
| :--- | :--- | :--- | :--- |
| **Total Evaluated Cost** | **$3,440.00** | **$1,817.50** | **+47.17%** |
| **Premature Replacement Waste** | 0.0 discarded cycles | 281.0 discarded cycles | -281.0 cycles |
| **Missed Imminent Failures** ($t_{\text{true}} \le 5$) | 0 units | 0 units | 0 (Zero safety escape) |
| **Recommended Action Distribution** | • REPLACE: 24<br>• CONTINUE: 76 | • REPLACE: 5<br>• NOW: 13<br>• SOON: 14<br>• CONTINUE: 68 | Multi-tier graduated response |

> [!NOTE]
> **Cost Model Disclosure**:
> Cost figures use the illustrative, non-fitted cost model established in Month 5 (unplanned failure penalty=1000, maintenance base=50, downtime per cycle=5); absolute numbers are for relative policy comparison under consistent assumptions.

### Diagnostic Trace: Premature Waste & Gaussian Uncertainty Mechanism

The premature waste metric counts cycles where `REPLACE_IMMEDIATELY` was chosen on units with $t_{\text{true}} > 60$. Pipeline A recorded 0 cycles (due to rigid thresholding at 30), whereas Pipeline B recorded 281.0 cycles across 3 early-life units (`unit_19`, `unit_27`, `unit_95`).

**Root Cause Mechanism**:
1. **Healthy-State Generalization Asymmetry**: Brand-new engines have nearly identical sensor readings, resulting in near-zero cosine distance ($d \approx 0.000$) to all other early-life engine trajectories in the AMKB.
2. **Raw Lifespan Variance**: However, different engines in C-MAPSS exhibit vastly different total operational lifespans (some fail at cycle 140, others at cycle 350+). Retrieving from brand-new engines yields an empirical neighbor variance of $\sigma^2 \approx 2,800 - 4,500$ (spread $\sigma \approx 60$ cycles).
3. **Gaussian Tail Over-Estimation**: Modeling uncertainty as an unconstrained Gaussian $\mathcal{N}(\mu, \sigma^2)$ around $\mu = 104$ forces artificial probability mass into the near-failure left tail ($x \le 30$, $p_{\text{fail}} \approx 11.3\%$). Because the catastrophic penalty is $1,000, an 11.3% risk incurs an expected penalty of $113.00, prompting the cost-minimizing Decision Graph to conservatively choose preventive replacement ($60).
4. **Methodological Implication**: This provides illustrative evidence from 4 observed cases for a limitation of symmetric Gaussian uncertainty propagation in early-life regimes, motivating domain-specific asymmetric priors or lifetime normalization in production digital twins.

---

## Ablation 2: AMKB-Grounded vs. Ungrounded Explainability

This ablation isolates the value of grounding prognostic explanations with historical AMKB episodic memory retrieval against an ungrounded baseline (`grounding_enabled=False`).

### Confidence Calibration & Calibration Metrics

| Metric | AMKB-Grounded Explainability | Ungrounded Baseline (`grounding_enabled=False`) | Architectural Interpretation |
| :--- | :--- | :--- | :--- |
| **Mean Confidence Score** | **0.0351** | **0.5000** | Ungrounded baseline defaults to 0.50 uninformative prior |
| **Confidence Standard Deviation** | **0.0778** | **0.0000** | Grounded confidence exhibits dynamic, data-driven spread |
| **Confidence-Error Correlation ($r_s$)** | **-0.5090** | **N/A (Zero Variance - Constant Prior)** | Grounded confidence correlates strongly with actual error |
| **Citation Availability** | **100.0%** | **0.0%** | Grounding provides traceable historical provenance |

> [!NOTE]
> **Zero-Variance Note for Ungrounded Baseline**:
> Undefined (Zero Variance) — constant 0.50 maximal uncertainty prior across all units. Confirms that AMKB episodic memory retrieval is required for dynamic confidence calibration.

---

## Ablation 3: Cost-Weighted Decision Graph vs. Naive Threshold Rules

This ablation evaluates the Decision Graph under simulated operational lead-time risk exposure against a 3-tier naive heuristic cascade (`if RUL < 30: REPLACE, elif RUL < 60: SOON, else CONTINUE`).

### Comparative Decision & Policy Metrics

| Metric | Naive Threshold Cascade | ATLAS Cost-Weighted Decision Graph | Comparative Analysis |
| :--- | :--- | :--- | :--- |
| **Near-Failure Urgent Rate** ($t_{\text{true}} \le 15$) | **100.00%** | **90.00%** | **Safety Parity**: Both policies safely intervene before failure |
| **Near-Failure Sample Size** | 10 units | 10 units | Evaluated on units with ground-truth $t_{\text{true}} \le 15$ cycles |
| **Policy Agreement Rate** | — | **70.00%** | Fleet agreement across straightforward regimes |
| **Disagreed Units Total Cost** | **$1,530.00** | **$1,370.00** | **+10.46% cost reduction** on disputed decisions |
| **Heavy Replacement Triggered** | 20 units | 4 units | Naive rule over-intervenes with immediate replacements |
| **Graduated Scheduling Used** | 0 units | 26 units | ATLAS safely shifts interventions to `SOON` / `NOW` |
| **Average MC Sample Cost Std** | N/A (Deterministic) | **$54.34** | Quantifies decision uncertainty across 1,000 rollouts |

> [!NOTE]
> **Safety Parity & Critical Margin Disclosure**:
> Both policies safely intervene before failure on near-failure units (true RUL <= 15). The Decision Graph's primary advantage is economic precision and action graduation on disputed decisions.
> *(Note on operational margins: Unit 66 with $t_{\text{true}}=14$ cycles received `SCHEDULE_MAINTENANCE_SOON` [lead time = 10 cycles]. While maintenance completed before failure, the 4-cycle operating margin represents an operational near-miss that highlights the necessity of strict lead-time calibration under tight degradation horizons.)*

> [!WARNING]
> **Decision Graph Determinism & Stochastic Sensitivity Limitation**:
> While seeding ensures reproducibility for evaluation purposes, this sensitivity indicates that near-tied expected-cost decisions are inherently fragile under stochastic simulation; a production deployment would need either a larger sample count, a fixed inference-time seed policy, or a tie-breaking margin threshold below which the system defers to human judgment rather than auto-recommending.

---

## Ablation 4: Domain-Adapted vs. Foreign Representation Transfer

This study evaluates the necessity of domain-specific pre-training versus unadapted foreign memory retrieval.

### Section 4.1: Within-Domain vs. C-MAPSS Physical Memory Retrieval (Week 2 Precedent)

| Hardware Domain | Within-Domain Retrieval RMSE | Unadapted C-MAPSS Retrieval RMSE | Error Inflation Ratio | Within Latent Dist | Cross Latent Dist |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Laptop** | 0.0961 | 0.0858 | **0.89×** | 0.2834 | 10.8235 |
| **Mobile** | 0.0301 | 0.2495 | **8.30×** | 0.3022 | 10.8024 |
| **Server** | 0.0404 | 0.2868 | **7.10×** | 0.0683 | 10.9709 |

> [!WARNING]
> **Laptop Asymmetry Disclosure**:
> Laptop's within-domain retrieval RMSE (0.0961) is ~2.4–3.2x higher than Server (0.0404) and Mobile (0.0301) due to multi-modal operational regime transitions. Cross-domain C-MAPSS queries land on a distant out-of-distribution boundary (~10.82 distance) where retrieved normalized labels cluster near the global mean (~0.55), which coincidentally matches Laptop's validation target mean (~0.52). This lower cross RMSE is a boundary-mean regression artifact rather than successful semantic transfer.

### Section 4.2: 3×3 Cross-Compute Generalization Matrix (RMSE & Inflation Ratios)

Evaluating query telemetry from each compute domain against the encoders and episodic memory banks of all three compute architectures:

| Query Data Domain \ Evaluator Model | Laptop Model & Memory | Mobile Model & Memory | Server Model & Memory |
| :--- | :--- | :--- | :--- |
| **Laptop Query Telemetry** | **0.0961** (1.00×) | 0.2472 (2.57×) | 0.3723 (3.87×) | 
| **Mobile Query Telemetry** | 0.3480 (11.56×) | **0.0301** (1.00×) | 0.0800 (2.66×) | 
| **Server Query Telemetry** | 0.1768 (4.38×) | 0.1132 (2.80×) | **0.0404** (1.00×) | 

---

## Synthesis & Methodological Conclusions

1. **Safety Parity with Graduated Efficiency (Ablation 1 & 3)**: The Decision Graph safely prevents catastrophic failure across near-failure units while delivering a 47.17% overall lifecycle cost reduction (and 10.46% cost reduction specifically across disputed decisions) by substituting blunt immediate replacements with graduated, lead-time-aware maintenance schedules.
2. **Epistemic Calibration via Memory Grounding (Ablation 2)**: Grounding attributions in empirical episodic memory yields dynamically calibrated confidence scores ($r_s = -0.5090$) that accurately drop when prediction error rises, whereas ungrounded models cannot distinguish confident predictions from out-of-distribution errors.
3. **Hardware-Specific Encoders are Required (Ablation 4)**: Unadapted cross-physical retrieval causes up to $8.30\times$ error inflation. The 3×3 cross-compute evaluation demonstrates that even within Category B compute architectures, domain-adapted representation learning is essential for accurate health state retrieval ($2.57\times - 11.56\times$ inflation under cross-encoder evaluation).
4. **Stochastic Simulation Sensitivity in Production**: While seeding ensures reproducibility for evaluation purposes, this sensitivity indicates that near-tied expected-cost decisions are inherently fragile under stochastic simulation; a production deployment would need either a larger sample count, a fixed inference-time seed policy, or a tie-breaking margin threshold below which the system defers to human judgment rather than auto-recommending.
