---
title: "ATLAS: An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance"
---

::: {custom-style="Author"}
[Author Name], [Co-author / Mentor Name]  
[Department], [Institution], [City, Country]  
[email address]
:::

::: {custom-style="Abstract"}
***Abstract*—Predictive-maintenance (PdM) systems usually stop at estimating remaining useful life (RUL), leaving open what to do about the estimate and why an operator should trust it. We present ATLAS, a modular platform that couples RUL prediction with memory-grounded explanation and cost-aware decision support. One architecture is shared across machine types through a thin adapter layer, and each domain trains its own encoder. A recurrent world model with additive temporal attention encodes sensor windows into a 32-dimensional state; a vector-indexed memory of labeled run-to-failure experiences supplies neighbor citations and a dispersion-based confidence score; a Monte Carlo decision graph ranks four maintenance actions by expected cost under action-specific lead times. On NASA C-MAPSS FD001 the prediction engine reaches RMSE 15.22 ± 0.31 and PHM score 375.0 ± 21.9 over five seeds. The decision graph costs 47% less than a fixed 30-cycle threshold rule, but that gap comes from two units charged as lead-time failures. Against a three-threshold rule tuned on held-out training engines it costs 7.2% more on the ablation model (95% CI from 5.8% less to 24.3% more) and 7–216% more on each of five retrained models, and over a 30-setting cost sensitivity sweep it beats the tuned rule in 12 settings. Confidence correlates with absolute error at Spearman −0.51 (95% CI −0.66 to −0.33; −0.45 ± 0.04 over five retrained models), entirely through the spread of neighbor labels, and the Monte Carlo intervals are not calibrated. On simulated laptop, mobile and server telemetry, retrieval through another domain's encoder and memory inflates error 2.6–11.6×, so memory must stay partitioned by domain. End-to-end CPU latency is 21.8 ms per request. We also report the development defects we found and the regression guards that now prevent them.**

***Index Terms*—predictive maintenance, remaining useful life, explainable AI, decision support, maintenance cost, industrial IoT.**
:::

# Introduction

Unplanned equipment failure is costly, and most deployed PdM systems stop at an RUL estimate or a threshold alarm. Operators are left with two questions: what to do about the estimate, given its uncertainty and the cost of acting too early or too late, and why the estimate deserves trust. Published RUL work on benchmarks such as NASA C-MAPSS [1] concentrates on point-prediction accuracy [2]–[5]. Interpretable and decision-aware variants exist [6], [7], but they are typically evaluated on a single dataset and a single machine type, and they rarely tie explanations to verifiable historical evidence.

ATLAS addresses the gap between prediction and decision with one architecture that (i) predicts RUL, (ii) grounds each prediction in citations to labeled historical cases, (iii) ranks maintenance actions by simulated expected cost, and (iv) is shared across machine types through an adapter layer, with a per-domain encoder and memory. The contributions are:

1. An integrated pipeline (world model, memory, explanation, Monte Carlo decision graph) evaluated end to end on C-MAPSS FD001 with multi-seed statistics.
2. A memory-grounding rule with a circularity guard: explanations may cite only neighbors carrying ground-truth labels, never the model's own predictions.
3. A lead-time-aware decision model with a deterministic tie-break toward the safer action, evaluated against fixed, cascaded and tuned threshold rules with a full cost breakdown and a sensitivity sweep that shows where it helps and where a tuned rule is better.

We also report a bounded cross-domain retrieval diagnostic on simulated compute telemetry (Section V-D) and a catalogue of development defects with the guards that prevent them (Section V-F). We do not claim state-of-the-art RUL accuracy, a cost advantage over a tuned threshold rule, validation on real run-to-failure data outside C-MAPSS, or production readiness (Section VI).

# Literature Review

**RUL prediction.** C-MAPSS [1] is the standard turbofan degradation benchmark and defines the asymmetric prognostics and health management (PHM) score. Recurrent models set early baselines: a long short-term memory (LSTM) network reports a root-mean-square error (RMSE) of 16.14 on FD001 [2]. Attention-based approaches followed [3]; transformer architectures [4] and attention-LSTM variants with feature self-attention [5] report substantially lower RMSE on FD001 and FD003. These works optimise point accuracy; none connects the estimate to a maintenance action or to auditable evidence. Our prediction engine is deliberately simple (LSTM with additive attention [8]) because the contribution is the system around it.

**Interpretable and decision-aware PdM.** Özcan [6] couples interpretable ensemble RUL prediction with dynamic maintenance scheduling on C-MAPSS, the closest work to our scope. Cummins *et al.* [7] survey explainable PdM and identify the lack of standardized evaluation of explanation quality as an open challenge. Kobayashi and Alam [9] study explainable, trustworthy AI for an intelligent digital twin on RUL, using attribution to build operator trust. Nguyen and Medjaher [10] turn LSTM prognostics into failure probabilities over several horizons that drive a dynamic maintenance-planning framework, and de Pater *et al.* [11] start maintenance scheduling for a fleet of C-MAPSS engines only when alarms fire on imperfect convolutional-network prognostics. These works optimise schedules over a horizon or a fleet; ATLAS makes a per-unit recommendation at each request and compares it with threshold rules. It also differs in grounding explanations in a labeled case memory. Attribution uses perturbation (occlusion [12]) rather than SHAP [13] to stay model-agnostic and cheap on CPU.

**Predictive uncertainty.** Monte Carlo dropout [14] is a standard way to obtain predictive uncertainty from a trained network. ATLAS instead uses the spread of the labels of retrieved neighbors; we do not compare the two (Section VI).

**Memory and retrieval.** Retrieval of similar historical trajectories has a long history in similarity-based prognostics [15], and retrieval-augmented models keep knowledge in an external, non-parametric store rather than only in their weights [16]. Our use differs in the labeling rule and in using retrieval for confidence and uncertainty, not only for prediction.

**Monte Carlo maintenance optimisation.** Monte Carlo simulation is an established tool for comparing maintenance policies of degrading systems under uncertain lifetimes [17]. ATLAS applies the idea at inference time: each recommendation is a Monte Carlo evaluation of four candidate actions with explicit lead times.

**Cross-domain transfer.** Domain adaptation for RUL is active: LAMA-Net [18] aligns latent representations with maximum mean discrepancy [19] and manifold learning across C-MAPSS subsets, and transfer-component approaches [20] learn domain-invariant features. These methods study adaptation among *similar* machines (turbofan to turbofan). ATLAS does not adapt across domains; it partitions memory by domain, and Section V-D checks that this is necessary. MetroPT [21] provides real compressor data and is a planned validation target.

**Research gap.** From this review: (1) RUL models are evaluated as regressors, with no integrated path to a cost-aware action; (2) explanations are rarely grounded in verifiable labeled precedent, and their quality is seldom measured against prediction error; and (3) systems are validated on one dataset, leaving the reuse of one architecture across machine types untested. ATLAS targets these with one architecture.

# Methodology and Architecture

Figure 1 shows the architecture. Data flows machine → adapter → world model → memory and Machine DNA → explanation → simulation → decision graph → (optional) agent safety gate, with a learning engine that retrains the world model offline.

![**Fig. 1.** ATLAS architecture. Adapters normalize each machine's telemetry into a canonical window. The world model yields a 32-d state and RUL estimate; memory, Machine DNA and explainability ground the estimate; Monte Carlo simulation and the decision graph rank maintenance actions. The LLM agent can raise work orders only through the safety gate, and every order awaits human approval.](figure1.png){width=3.4in}

## Adapter Layer and Canonical Features

Every machine is reached through an adapter returning a normalized reading: domain, machine id, timestamp, a health index in [0,1], a feature dictionary, raw channels and an optional ground-truth RUL label. The adapter is the only place with domain-specific code; downstream components never branch on domain. Adapters exist for C-MAPSS (14 informative sensors after dropping 7 near-constant ones), laptop (psutil), Android mobile (Termux), server (SSH or simulation) and Modbus TCP; a conformance suite enforces the contract for any new adapter. The health index has two meanings: for C-MAPSS (Category A) it is degradation toward failure; for compute domains (Category B) it is instantaneous operational stress, not wear. For C-MAPSS the adapter computes it from the RUL label, as $1-\min(\mathrm{RUL},125)/125$, so it is used only for display and Machine DNA and enters no result reported here; a deployment without labels would need a health index computed from sensors.

## World Model

A window of $L=30$ steps with $D$ canonical features passes through a two-layer LSTM (hidden size 64) giving $h_1,\dots,h_L$. Additive attention [8] computes

$$e_t = v_a^{\top}\tanh(W_a h_t + b_a),\quad \alpha_t=\frac{\exp(e_t)}{\sum_{j=1}^{L}\exp(e_j)},\quad c=\sum_{t=1}^{L}\alpha_t h_t \qquad (1)$$

and a linear projection gives the 32-dimensional state

$$z = W_z c + b_z \in \mathbb{R}^{32}. \qquad (2)$$

A linear head yields the RUL estimate, clamped at inference for physical non-negativity:

$$\hat{y} = \max\!\big(0,\; w^{\top} z + b\big). \qquad (3)$$

RUL targets are clipped at 125 cycles. Training uses mean-squared error with Adam, a unit-level 80/20 split, early stopping, and a single evaluation on the official test set using the last window of each test unit.

## Adaptive Machine Knowledge Base (AMKB)

Experiences are stored in a pgvector index with domain, machine id, cycle, the 32-d state, the ground-truth RUL label and, separately, the model's predicted RUL. For a query state $z_q$ the cosine distance to a stored $z_i$ is

$$d(z_q,z_i)=1-\frac{z_q\cdot z_i}{\lVert z_q\rVert_2\,\lVert z_i\rVert_2}. \qquad (4)$$

At run time the $k=5$ nearest labeled neighbors are retrieved, excluding the query's own record. Only experiences with ground-truth labels may be cited (circularity guard). Retrieval is partitioned by domain key. In the ablations of Section V-B the memory holds the 20,631 windows of the 100 FD001 training engines, the queries are the last windows of the 100 test engines, a disjoint set of engines, and $k=10$; no test engine can therefore retrieve its own history.

## Machine DNA

A 16-d per-unit fingerprint summarizes degradation character (whole-life slopes of state norm and of the health index, thermal and speed sensor slopes, and terminal slopes over the last 20% of life). Each dimension is z-scored over the unit population, $\mathbf{z}_{\mathrm{DNA}}=(\mathbf{x}-\boldsymbol\mu)/\boldsymbol\sigma$, with persisted statistics applied identically to stored and query vectors. Machine DNA is not used in the reported ablations.

## Explainability

Let $d_1,\dots,d_k$ be the cosine distances to the retained neighbors, $\bar s=\frac1k\sum_i 1/(1+d_i)$ their mean similarity, and $\sigma^2$ the variance of their RUL labels. Confidence is

$$\mathcal{C}=\bar s\cdot\frac{1}{1+\sigma^{2}}, \qquad (5)$$

bounded in $(0,1]$ with no division-by-zero. Because $\sigma^2$ is in cycles² (typically $10^2$–$10^3$ here), $\mathcal C$ is small (mean 0.035 on the test set) and is in effect a decreasing function of neighbor label spread. It is a ranking score, not a probability; Section V-C shows that dividing $\sigma^2$ by $125^2$ leaves its ranking unchanged. Attribution replaces sensor channel $j$ over the whole window by a reference value, re-runs the model, and records the change $\Delta_j = f(X)-f(X_{\setminus j})$; channels are ranked by $|\Delta_j|$. Explanation text is template-based, not LLM-generated.

## Monte Carlo Simulation and Decision Graph

Given estimate $\hat y$ and neighbor variance $\sigma^2$, draw $M=1000$ samples $y^{(m)}\sim\mathcal N(\hat y,\sigma^2)$ clipped to $[0,125]$. Four actions $a\in\mathcal A$ are evaluated (continue, schedule soon, schedule now, replace immediately) with lead times $\tau(a)=30,10,3,0$ cycles. The sample cost is

$$C(y,a)=\begin{cases}C_{f}, & y\le\tau(a)\\ 0, & y>\tau(a),\ a=\text{continue}\\ C_{b}+C_{d}\,u(a), & \text{otherwise}\end{cases} \qquad (6)$$

with $C_f=1000$, $C_b=50$, $C_d=5$ and urgency multiplier $u(a)\in\{1,1.5,2\}$ (illustrative, not fitted to financial data). Expected cost, failure probability and cost dispersion are

$$\mathbb E[C(a)]=\tfrac1M\sum_m C(y^{(m)},a),\quad p_f(a)=\tfrac1M\sum_m \mathbb I\big(y^{(m)}\le\tau(a)\big),\qquad (7)$$

$$\sigma_C(a)=\sqrt{\tfrac1M\sum_m\big(C(y^{(m)},a)-\mathbb E[C(a)]\big)^2}.\qquad (8)$$

The recommendation is the lexicographic minimum

$$a^{*}=\arg\min_{a\in\mathcal A}\big(\mathbb E[C(a)],\,p_f(a),\,\sigma_C(a),\,\mathrm{name}(a)\big), \qquad (9)$$

so a cost tie favors the action with the lower failure probability. There is no separate hard safety override: Eq. (9) alone produces every recommendation reported here.

## Learning Engine and Agent Safety Gate

Retraining is periodic and batch, not online. A candidate model replaces the active checkpoint only if its held-out RMSE is within the 3% tolerance of the active model (reflecting the 2–4% seed variance we measured); promotion is an atomic file replacement and every run is audited. Because each comparison is against the current model, repeated promotions could drift upward in error by up to 3% each; comparing against a fixed reference or the best checkpoint would close this gap and is planned. A language-model assistant may propose work orders only through a structured tool requiring a live alert (under 24 h old, severity threshold), an exact fault-type match, an allowed action for that fault, and a server-stamped creator. Orders start as *Pending Approval* and become active only through a role-checked human approval; the agent has no function that actuates a machine.

# Experimental Setup

**Data.** C-MAPSS FD001 (100 training and 100 test engines, one operating condition, one fault mode) [1]. The laptop, mobile and server results use synthetic data only; no measured telemetry enters any reported number. For each domain a seeded generator produces 1,250 windows of 30 steps × 5 channels (laptop: CPU, memory, disk, battery level, charging; mobile: battery level and temperature, current, memory, CPU; server: CPU, memory, disk, network, GPU). The first 1,000 windows form the memory and the last 250 the queries. Each domain's encoder is pretrained by self-supervised next-step prediction on its own generator. The retrieval label is a per-domain stress composite in [0,1] (laptop $0.7\,\mathrm{cpu}+0.3\,\mathrm{mem}$; mobile $0.4\,\mathrm{temp}+0.3\,\mathrm{cpu}+0.2\,\mathrm{mem}+0.1(1-\mathrm{battery})$; server $0.45\,\mathrm{cpu}+0.35\,\mathrm{mem}+0.1\,\mathrm{disk}+0.1\,\mathrm{net}$), not a time to failure.

**Metrics.** RMSE and the asymmetric PHM score [1]:

$$S=\sum_{d_i<0}\big(e^{-d_i/13}-1\big)+\sum_{d_i\ge0}\big(e^{d_i/10}-1\big),\quad d_i=\hat y_i-y_i. \qquad (10)$$

Grounding quality is the Spearman correlation $r_s$ between $\mathcal C$ and $|\hat y-y|$, with a 95% bootstrap confidence interval (2,000 resamples of the 100 units). We also report how often the central intervals of $\mathcal N(\hat y,\sigma^2)$ contain the true RUL (on the clipped $[0,125]$ scale). For the compute domains, a query is predicted as the mean label of its $k=5$ Euclidean nearest neighbors in the latent space of the encoder under test, and the error inflation ratio is

$$\mathrm{EIR}=\frac{\mathrm{RMSE}_{\mathrm{cross}}}{\mathrm{RMSE}_{\mathrm{within}}}. \qquad (11)$$

**Decision baselines.** (i) A fixed rule replaces when $\hat y<30$ and otherwise continues. (ii) A cascade replaces below 30 and schedules soon below 60. (iii) A tuned rule uses three thresholds (replace < schedule now < schedule soon), each from $\{0,5,\dots,100\}$, chosen to minimise mean Eq. (6) cost over all windows of the checkpoint's 20 held-out validation engines (4,195 windows for the ablation checkpoint), so no test outcome is used. Every policy is charged by Eq. (6) against the true test RUL. A variant also charges discarded life, $C_\ell\,(y-\tau(a))$ for each executed maintenance, with $C_\ell=C_b/125=0.4$ per cycle. A sensitivity sweep covers $C_f\in\{250,500,1000,2000,4000\}$, $\tau(\text{continue})\in\{15,20,30\}$ and $C_\ell\in\{0,0.4\}$; the tuned rule and ATLAS are re-optimised for each setting. Savings carry a paired bootstrap 95% confidence interval over units.

**Protocol.** Five seeds (42–46), each with its own unit split and initialization; mean ± std is reported. The ablations use one checkpoint, trained with seed 46 (RMSE 15.42, PHM 394.7; Figs. 2–3); the grounding and decision analyses are repeated on five checkpoints retrained with seeds 42–46, of which the seed-46 retrain reproduces the ablation checkpoint's predictions exactly. Experiments ran CPU-only on one workstation (10 cores, 15.7 GB RAM, PyTorch 2.10 CPU). CPU training is not bit-reproducible; about ±0.3 RMSE should be expected on reruns.

# Results and Discussion

## RUL Prediction

Table I gives FD001 test-set accuracy.

: TABLE I. FD001 test-set accuracy.

| Model | RMSE | PHM score |
|:--|:--|:--|
| LSTM, linear head (5 seeds) | 15.34 ± 0.60 | 426.1 ± 83.6 |
| LSTM + attention (5 seeds) | 15.22 ± 0.31 | 375.0 ± 21.9 |
| LSTM from literature [2] | 16.14 | 338 |

Attention reduced the PHM coefficient of variation from 19.6% to 5.8% and slightly lowered RMSE. Our RMSE is lower than [2] but our PHM score is higher, meaning errors skew later; the comparison is directional, as implementations differ. More recent attention and transformer models [3]–[5] report lower RMSE, so we make no state-of-the-art claim: the prediction engine is intentionally a modest component. An earlier single run (RMSE 15.02) was a favorable seed, which is why multi-seed statistics are reported. Figures 2 and 3 show training loss and per-unit predictions.

![**Fig. 2.** Training and validation MSE on FD001 for the ablation checkpoint; the checkpoint at epoch 44 is kept.](figure2.png){width=3.2in}

![**Fig. 3.** Predicted versus true RUL for the 100 test units (ablation checkpoint: RMSE 15.42, PHM 394.7). Crosses mark units with true RUL ≤ 30 whose estimate is late.](figure4.png){width=3.2in}

## Decision Value

: TABLE II. Decision policies on 100 FD001 test units (ablation checkpoint). Actions: continue/soon/now/replace; Fail.: lead-time failures; Disc.: remaining-life cycles discarded by executed maintenance; costs in \$, by Eq. (6) and with a discarded-life charge.

| Policy | Actions | Fail. | Disc. | Cost | + life |
|:--|:--|:--|:--|:--|:--|
| Fixed (< 30) | 76/0/0/24 | 2 | 424 | 3,440 | 3,610 |
| Cascade (30/60) | 65/11/0/24 | 0 | 845 | 2,045 | 2,383 |
| Tuned (10/20/45) | 70/17/8/5 | 0 | 470 | 1,695 | 1,883 |
| ATLAS | 68/14/13/5 | 0 | 718 | 1,817.50 | 1,812.30 |

Table II gives the cost of each policy as counts times unit costs. The fixed rule's \$3,440 is 24 replacements at \$60 plus two \$1,000 lead-time failures: units with true RUL 28 and 29 that it continued, with $\tau(\text{continue})=30$. The 47% saving of ATLAS against this rule therefore rests on two units. The tuned rule, fixed before any test outcome was seen, is the strongest baseline: ATLAS costs 7.2% more than it (paired bootstrap 95% CI: from 5.8% less to 24.3% more). Neither policy has a lead-time failure; ATLAS schedules more units early and replaces 5 with 296 cycles of remaining life, three of them early-life units (true RUL > 60) where neighbor variance was large and the symmetric Gaussian placed tail mass near failure. Charging discarded life reverses the sign: ATLAS then costs 3.8% less (95% CI: from 0.9% more to 12.0% less), because the re-optimised decision graph replaces only 2 units (actions 71/14/13/2). Across the 30 sweep settings ATLAS beats the tuned rule in 12 (median difference −3.1%), the fixed rule in 18 and the cascade in 22 (Fig. 4b); with $\tau(\text{continue})\le20$ the fixed rule has no failures at all. Across the five retrained checkpoints ATLAS saves 25–73% against the fixed rule but costs 7–216% more than the tuned rule. For two of them it incurs lead-time failures itself (seed 44 continued three units with true RUL 21–29; seed 45 scheduled one unit soon at true RUL 10), while the tuned rule has none. We therefore claim no cost advantage over a well-tuned threshold rule. The practical difference is that the decision graph needs no labeled data to set thresholds, only costs and lead times, and re-optimises when they change; whether that matters needs real cost data.

On the 10 near-failure units (true RUL ≤ 15), ATLAS gave an urgent action to 9 and the cascade to 10; one unit (true RUL 14) was scheduled soon with only a 4-cycle margin. This is approximate safety parity, not a safety advantage. Near-tied expected costs remain sensitive to Monte Carlo sampling; a margin below which the system defers to a human is recommended.

![**Fig. 4.** Decision value. (a) Total cost of four policies under Eq. (6), and with a discarded-life charge of 0.4 per cycle (tuned rule and ATLAS re-optimised). (b) ATLAS saving relative to the tuned rule across failure cost $C_f$ and $\tau(\text{continue})$, without discarded-life cost; negative values mean ATLAS costs more.](figure5.png){width=3.4in}

## Grounding and Confidence

: TABLE III. Spearman $r_s$ between a score and absolute error (100 test units; 95% bootstrap CI).

| Score | Ablation checkpoint | Five retrained checkpoints |
|:--|:--|:--|
| $\mathcal C$, Eq. (5) | −0.51 [−0.66, −0.33] | −0.45 ± 0.04 |
| $\mathcal C$ with $\sigma^2/125^2$ | −0.51 [−0.66, −0.33] | −0.45 ± 0.04 |
| Neighbor label spread only ($-\sigma$) | −0.51 [−0.66, −0.33] | −0.45 ± 0.04 |
| Prediction only ($-\hat y$, no memory) | −0.45 [−0.61, −0.26] | −0.43 ± 0.04 |

Grounded confidence falls as error rises (Table III), but its ranking equals that of neighbor label spread alone, so the similarity term adds nothing measurable, and the prediction itself, with no memory, ranks errors almost as well (the intervals overlap). The ungrounded baseline, a constant 0.5, has no defined $r_s$ by construction. The central Monte Carlo intervals contain the true RUL for 63%, 85%, 87% and 91% of units at nominal 50%, 80%, 90% and 95%: too wide at low levels and too narrow at high levels (63 ± 3%, 84 ± 4%, 87 ± 3% and 90 ± 2% over the five retrained checkpoints). Neither $\mathcal C$ nor the intervals are calibrated; we use $\mathcal C$ only to rank predictions and the spread only to drive the simulation. Every grounded explanation cites labeled neighbors, which holds by construction and is not evidence of explanation quality.

## Cross-Domain Retrieval Diagnostic

This diagnostic asks one narrow question: can retrieval share memory across domains? It does not test maintenance prediction, since the compute domains have no failures and their labels measure stress, not wear. In each cell of a 3×3 matrix, query windows of one domain are encoded by a second domain's encoder and matched against that domain's memory and labels, so query and memory always share one latent space. Every domain is best on its own encoder and memory (within-domain RMSE 0.096 laptop, 0.030 mobile, 0.040 server); the other cells inflate error 2.57×–11.56× (Fig. 5). Because the foreign label is a different stress composite, part of this inflation is built in. The result confirms that memory must stay partitioned by domain, as ATLAS does; it does not show that the domains' representations are intrinsically different. An earlier draft also compared C-MAPSS and compute latents by maximum mean discrepancy, centroid cosine similarity and cross-domain retrieval. Those comparisons put vectors from independently trained encoders in one space, where the coordinates are not shared, so we removed them.

![**Fig. 5.** Retrieval error inflation (RMSE relative to the within-domain cell) for compute-domain queries (rows) evaluated with each domain's encoder, memory and stress labels (columns). Synthetic data; one encoder seed per domain.](figure6.png){width=3.0in}

## System Performance

: TABLE IV. CPU-only latency per request (mean over 100 trials).

| Stage / domain | Latency (ms) |
|:--|:--|
| World model (C-MAPSS) | 0.63 |
| pgvector retrieval (k=10, 17,737 vectors) | 1.18 |
| Machine DNA lookup | 0.96 |
| Occlusion attribution (14 passes) | 10.40 |
| Monte Carlo (1,000 rollouts) | 1.60 |
| End-to-end, C-MAPSS | 21.78 |
| End-to-end, laptop / mobile / server | 6.70 / 6.84 / 10.49 |

Occlusion attribution dominates; isolated stages sum to 14.8 ms and the remaining 7 ms is inter-stage overhead, chiefly checkouts from two separate database connection pools (a named optimization target). Context-endpoint throughput plateaued near 49 requests/s and the full decision endpoint peaked at 17.4 requests/s with no errors; isolated-process memory was about 282 MB (Fig. 6). Latency is far below standard industrial polling intervals (1–5 s).

![**Fig. 6.** System performance on CPU. (a) Per-stage latency, one C-MAPSS request. (b) Throughput versus concurrent clients.](figure8.png){width=3.3in}

## Development Defects and Guards

We logged 13 defects and 2 near-misses in a project register as they were found; the register is a record of practice, not a controlled study. Nearly all share one signature: a plausible result computed by the wrong method. Table V lists six, with how each was detected and the guard that now prevents it. Others include scoring all windows instead of the last per unit (which inflated a baseline RMSE to 48.8 against a true 15.4), mixing clipped and raw RUL scales between subsystems, and retrieval returning the query itself. Preparing this revision exposed one more instance of the signature: the manuscript described a safety override that the evaluated code does not contain (corrected in Section III). Practices that caught these defects: cross-checking against a second measurement, reading raw artifacts, one permanent regression test per defect, hard-coded test thresholds, a queryable trained-or-not flag per domain, and labeling data as simulated, replayed, estimated or measured. The adapter conformance suite applies these checks to any new machine type.

: TABLE V. Selected defects, how each was detected, and the guard that now prevents it.

| Defect | Detected by | Guard |
|:--|:--|:--|
| ReLU output head zeroed RUL for some initializations | Identical zero outputs across seeds | Multi-seed output-range test |
| Cosine distance used as similarity, inverting confidence | Confidence–error sanity check | Sign test; $r_s$ reported |
| Alphabetical tie-break favored inaction | Equal-cost borderline cases | Tie-break order test, Eq. (9) |
| Cross-domain distances tracked padded dimensions | Implausibly uniform distances | Transfer-study unit test |
| Live API used untrained fallback encoders | Live output vs. evaluation harness | Per-domain trained flag and test |
| Path traversal in static file serving | Independent security review | Traversal-payload test suite |

# Limitations and Threats to Validity

Only one benchmark subset (FD001) is used. The laptop, mobile and server results are on synthetic data with no failures, so claims for these domains concern the architecture, not field accuracy. The cost model, lead times and urgency multipliers are illustrative assumptions, not taken from a maintenance-planning source; savings are relative, not financial, and the decision graph does not beat a tuned threshold rule on balance. Confidence is dispersion-based and uncalibrated, and we do not compare it with Monte Carlo dropout or ensembles. The C-MAPSS health index is derived from labels, and no hard safety override is implemented. Repeated model promotions can drift (Section III-G). Domain encoders use one seed each, and the PHM score trails the cited baseline. Agent grounding validates structure, not the truth of free-text rationale; human approval remains the final barrier.

# Conclusion and Future Work

ATLAS shows that RUL prediction, memory-grounded explanation and cost-aware decisions can share one architecture across machine types when encoders and memory are kept per domain. Under illustrative costs its decision graph beats fixed and cascaded rules but not a tuned threshold rule, which costs less on all five retrained models; its confidence ranks errors without being calibrated; the main risks sit at the seams between components, which our verification practice targets. Future work: real cost and lead-time data, calibrated uncertainty (Monte Carlo dropout and ensembles), a sensor-based health index for C-MAPSS, multi-seed domain encoders, multi-condition C-MAPSS (FD002–FD004), a high-frequency vibration domain, validation on real industrial hardware and a cloud VM, and further protocol adapters (OPC-UA).

# Code and Data Availability {.unnumbered}

C-MAPSS is publicly available [1]. The ATLAS code, trained checkpoints and the scripts that regenerate Tables I–V are available from the authors on request.

# References {.unnumbered}

::: {custom-style="Reference"}
[1] A. Saxena, K. Goebel, D. Simon, and N. Eklund, "Damage propagation modeling for aircraft engine run-to-failure simulation," in *Proc. Int. Conf. Prognostics and Health Management*, 2008.

[2] S. Zheng, K. Ristovski, A. Farahat, and C. Gupta, "Long short-term memory network for remaining useful life estimation," in *Proc. IEEE ICPHM*, 2017, pp. 88–95.

[3] Z. Chen, M. Wu, R. Zhao, F. Guretno, R. Yan, and X. Li, "Machine remaining useful life prediction via an attention-based deep learning approach," *IEEE Trans. Ind. Electron.*, vol. 68, no. 3, pp. 2521–2531, 2021.

[4] Q. Ma, M. Zhang, Y. Xu, J. Song, and T. Zhang, "Remaining useful life estimation for turbofan engine with transformer-based deep architecture," in *Proc. Int. Conf. Automation and Computing (ICAC)*, 2021.

[5] M. Dida, A. Cheriet, and M. Belhadj, "Remaining useful life prediction using attention-LSTM neural network of aircraft engines," *Int. J. Prognostics and Health Management*, 2025.

[6] H. Özcan, "Interpretable ensemble RUL prediction enables dynamic maintenance scheduling for aircraft engines," *Sci. Rep.*, 2025, doi:10.1038/s41598-025-23473-2.

[7] L. Cummins, A. Sommers, S. B. Ramezani, S. Mittal, J. Jabour, M. Seale, and S. Rahimi, "Explainable predictive maintenance: A survey of current methods, challenges and opportunities," *IEEE Access*, vol. 12, pp. 57574–57602, 2024, doi:10.1109/ACCESS.2024.3391130.

[8] D. Bahdanau, K. Cho, and Y. Bengio, "Neural machine translation by jointly learning to align and translate," in *Proc. ICLR*, 2015.

[9] K. Kobayashi and S. B. Alam, "Explainable, interpretable and trustworthy AI for intelligent digital twin: Case study on remaining useful life," arXiv:2301.06676, 2023.

[10] K. T. P. Nguyen and K. Medjaher, "A new dynamic predictive maintenance framework using deep learning for failure prognostics," *Reliab. Eng. Syst. Saf.*, vol. 188, pp. 251–262, 2019, doi:10.1016/j.ress.2019.03.018.

[11] I. de Pater, A. Reijns, and M. Mitici, "Alarm-based predictive maintenance scheduling for aircraft engines with imperfect Remaining Useful Life prognostics," *Reliab. Eng. Syst. Saf.*, vol. 221, art. 108341, 2022, doi:10.1016/j.ress.2022.108341.

[12] M. D. Zeiler and R. Fergus, "Visualizing and understanding convolutional networks," in *Proc. ECCV*, 2014.

[13] S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions," in *Proc. NeurIPS*, 2017.

[14] Y. Gal and Z. Ghahramani, "Dropout as a Bayesian approximation: Representing model uncertainty in deep learning," in *Proc. ICML*, PMLR vol. 48, 2016, pp. 1050–1059.

[15] T. Wang, J. Yu, D. Siegel, and J. Lee, "A similarity-based prognostics approach for remaining useful life estimation of engineered systems," in *Proc. Int. Conf. PHM*, 2008.

[16] P. Lewis *et al.*, "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Proc. NeurIPS*, 2020.

[17] M. Marseguerra and E. Zio, "Optimizing maintenance and repair policies via a combination of genetic algorithms and Monte Carlo simulation," *Reliab. Eng. Syst. Saf.*, vol. 68, no. 1, pp. 69–83, 2000, doi:10.1016/S0951-8320(00)00007-7.

[18] M. Joseph and V. Lalwani, "LAMA-Net: Unsupervised domain adaptation via latent alignment and manifold learning for RUL prediction," arXiv:2208.08388, 2022.

[19] A. Gretton, K. M. Borgwardt, M. J. Rasch, B. Schölkopf, and A. Smola, "A kernel two-sample test," *J. Mach. Learn. Res.*, vol. 13, pp. 723–773, 2012.

[20] S. J. Pan, I. W. Tsang, J. T. Kwok, and Q. Yang, "Domain adaptation via transfer component analysis," *IEEE Trans. Neural Netw.*, vol. 22, no. 2, pp. 199–210, 2011.

[21] B. Veloso, R. P. Ribeiro, J. Gama, and P. M. Pereira, "The MetroPT dataset for predictive maintenance," *Sci. Data*, 2022, doi:10.1038/s41597-022-01877-3.
:::
