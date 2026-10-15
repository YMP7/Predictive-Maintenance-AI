# Mathematical Equations and Metrics Reference
### ATLAS: An Adaptive Machine Cognition Platform for Explainable Predictive Maintenance Across Heterogeneous Machine Systems

This document catalogs every core mathematical formulation, loss function, uncertainty metric, and decision equation implemented across the ATLAS platform. It follows the standard academic format with formal definitions, boxed equations, and term breakdowns.

---

## 1. World Model & Multitask Prognostic Inference

### 1. Recurrent Temporal State Encoding
Processes sequential multivariate sensor readings through a stacked 2-layer Long Short-Term Memory network to extract temporal degradation features.

$$\boxed{h_t, c_t = \text{LSTM}\left(x_t, (h_{t-1}, c_{t-1})\right)}$$

**Terms:**
- $x_t \in \mathbb{R}^D$: Multivariate sensor input vector at operational cycle $t$ ($D=14$ for C-MAPSS, $D=5$ for compute domains).
- $h_t \in \mathbb{R}^{64}$: Hidden state representation vector at cycle $t$.
- $c_t \in \mathbb{R}^{64}$: Cell memory state vector at cycle $t$.
- $t \in \{1, \dots, L\}$: Operational cycle index across the sequence window ($L = 30$).

---

### 2. Temporal Attention Alignment Energy
Quantifies the prognostic relevance of each operational cycle in the historical window.

$$\boxed{e_t = v_a^\top \tanh(W_a h_t + b_a)}$$

**Terms:**
- $e_t$: Scalar unnormalized alignment score for cycle $t$.
- $W_a \in \mathbb{R}^{64 \times 64}$: Learnable attention projection matrix.
- $b_a \in \mathbb{R}^{64}$: Attention bias vector.
- $v_a \in \mathbb{R}^{64}$: Learnable attention scoring vector.
- $\tanh(\cdot)$: Hyperbolic tangent activation function bounding latent energy to $(-1, 1)$.

---

### 3. Softmax Temporal Attention Distribution
Normalizes cycle alignment energies into a strictly positive probability distribution over time.

$$\boxed{\alpha_t = \frac{\exp(e_t)}{\sum_{j=1}^L \exp(e_j)}, \quad \sum_{t=1}^L \alpha_t = 1.0}$$

**Terms:**
- $\alpha_t$: Normalized attention weight assigned to cycle $t$.
- $\exp(\cdot)$: Natural exponential function ensuring strict positivity.
- $L$: Sequence history length ($L = 30$ timesteps).

---

### 4. Attention-Pooled Context Vector
Synthesizes a fixed-length operational summary vector dynamically weighted by cycle criticality.

$$\boxed{c_{\text{attn}} = \sum_{t=1}^L \alpha_t h_t}$$

**Terms:**
- $c_{\text{attn}} \in \mathbb{R}^{64}$: Attention-weighted temporal context representation.
- $\alpha_t$: Attention weight for cycle $t$.
- $h_t$: Hidden state vector at cycle $t$.

---

### 5. Latent Representation Projection (State Vector)
Compresses the temporal context into an invariant 32-dimensional manifold representation used for episodic memory indexing.

$$\boxed{z = \text{LayerNorm}(W_z c_{\text{attn}} + b_z)}$$

**Terms:**
- $z \in \mathbb{R}^{32}$: Canonical invariant latent state vector (stored in AMKB).
- $W_z \in \mathbb{R}^{32 \times 64}$: Linear projection weight matrix.
- $b_z \in \mathbb{R}^{32}$: Projection bias vector.
- $\text{LayerNorm}(\cdot)$: Normalizes activations to zero mean and unit variance for training stability.

---

### 6. Clamped RUL Prediction Head (Mish + Non-Negative Clamp)
Estimates Remaining Useful Life with non-linear activation and a safety clamp to eliminate unphysical negative predictions (DEF-001).

$$\boxed{\hat{y}_{\text{RUL}} = \max\left(0.0, \; W_2 \cdot \text{Mish}(W_1 z + b_1) + b_2\right)}$$

**Terms:**
- $\hat{y}_{\text{RUL}} \in \mathbb{R}^+$: Predicted Remaining Useful Life in operational cycles ($[0, 125]$ for C-MAPSS, $[0.0, 1.0]$ for compute).
- $\text{Mish}(u) = u \cdot \tanh(\ln(1 + e^u))$: Self-regularizing smooth activation function.
- $W_1 \in \mathbb{R}^{32 \times 32}, b_1 \in \mathbb{R}^{32}$: First dense layer parameters.
- $W_2 \in \mathbb{R}^{1 \times 32}, b_2 \in \mathbb{R}$: Final regression projection layer.
- $\max(0.0, \cdot)$: Enforces physical non-negativity constraint.

---

### 7. Sigmoid Health / Stress Degradation Head
Estimates physical wear (Category A) or instantaneous compute workload stress (Category B).

$$\boxed{h = \sigma(W_h z + b_h) = \frac{1}{1 + \exp(-(W_h z + b_h))}}$$

**Terms:**
- $h \in [0.0, 1.0]$: Health index ($h \to 0$ indicates imminent failure / acute operational stress).
- $\sigma(\cdot)$: Standard logistic sigmoid function bounding output to $(0, 1)$.
- $W_h \in \mathbb{R}^{1 \times 32}, b_h \in \mathbb{R}$: Health classification head parameters.

---

### 8. Non-Collapse Representation Variance Guard
Enforces that self-supervised domain encoders maintain non-degenerate embedding diversity.

$$\boxed{\sigma(z) = \sqrt{\frac{1}{32} \sum_{j=1}^{32} (z_j - \bar{z})^2} \ge 0.05}$$

**Terms:**
- $\sigma(z)$: Cross-dimensional standard deviation of latent state $z$.
- $\bar{z}$: Mean component value across the 32 latent dimensions.
- $0.05$: Minimum permissible latent dispersion threshold preventing state collapse.

---

## 2. Prognostics Benchmark & Evaluation Metrics

### 9. Root Mean Squared Error (RMSE)
Measures the standard deviation of prognostic residuals across test fleets.

$$\boxed{\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (\hat{y}_i - y_{\text{true}, i})^2}}$$

**Terms:**
- $\text{RMSE}$: Root Mean Squared Error in flight/operating cycles.
- $\hat{y}_i$: Model-predicted RUL for unit $i$.
- $y_{\text{true}, i}$: Ground-truth terminal RUL for unit $i$.
- $N$: Total number of evaluated machine units ($N = 100$ for C-MAPSS FD001).

---

### 10. Mean Absolute Error (MAE)
Quantifies average magnitude of prediction errors without quadratic scaling.

$$\boxed{\text{MAE} = \frac{1}{N} \sum_{i=1}^N |\hat{y}_i - y_{\text{true}, i}|}$$

**Terms:**
- $\text{MAE}$: Mean Absolute Error in cycles.
- $|\cdot|$: Absolute value operator.

---

### 11. NASA Asymmetric PHM Scoring Function
Penalizes late predictions ($\hat{y} > y_{\text{true}}$) exponentially more severely than early predictions ($\hat{y} < y_{\text{true}}$).

$$\boxed{S_{\text{PHM}} = \sum_{d_i < 0} \left(\exp\left(-\frac{d_i}{13}\right) - 1\right) + \sum_{d_i \ge 0} \left(\exp\left(\frac{d_i}{10}\right) - 1\right)}$$

$$\text{where } d_i = \hat{y}_i - y_{\text{true}, i}$$

**Terms:**
- $S_{\text{PHM}}$: Total asymmetric penalty score (lower is superior).
- $d_i$: Signed prediction error ($d_i > 0$ denotes dangerous late prediction).
- $10$: Asymmetric scaling divisor for late predictions (steep exponential growth).
- $13$: Asymmetric scaling divisor for early predictions (conservative growth).

---

## 3. AMKB Episodic Memory & Machine DNA

### 12. Angular Cosine Distance (pgvector `<=>` Operator)
Quantifies semantic operational separation between query and stored historical failure embeddings.

$$\boxed{\mathcal{D}_{\cos}(z_q, z_i) = 1.0 - \frac{z_q \cdot z_i}{\|z_q\|_2 \|z_i\|_2}}$$

**Terms:**
- $\mathcal{D}_{\cos} \in [0.0, 2.0]$: Angular cosine distance ($0.0$ indicates identical operating profile).
- $z_q \in \mathbb{R}^{32}$: Query machine latent state vector.
- $z_i \in \mathbb{R}^{32}$: Historical failure instance vector stored in pgvector table.
- $\|\cdot\|_2$: Euclidean $L_2$ vector norm.

---

### 13. Normalized Precedent Similarity
Transforms unbounded distance into a bounded similarity score in $(0, 1]$.

$$\boxed{s_i = \frac{1.0}{1.0 + \mathcal{D}_{\cos}(z_q, z_i)}}$$

**Terms:**
- $s_i \in (0.0, 1.0]$: Normalized similarity between query $z_q$ and precedent $z_i$.
- $\mathcal{D}_{\cos}(z_q, z_i)$: Pairwise cosine distance.

---

### 14. Mean Precedent Similarity
Calculates average representational alignment across the top-$k$ nearest neighbors.

$$\boxed{\bar{s} = \frac{1}{k} \sum_{i=1}^k s_i}$$

**Terms:**
- $\bar{s} \in (0.0, 1.0]$: Mean similarity across retrieved neighborhood.
- $k$: Number of retrieved historical precedents ($k = 5$).

---

### 15. Historical Trajectory Variance
Quantifies the empirical disagreement in outcome trajectories among retrieved historical cases.

$$\boxed{\sigma^2_{\text{AMKB}} = \frac{1}{k} \sum_{i=1}^k \left(y_{\text{true}, i} - \bar{y}_{\text{true}}\right)^2}$$

$$\text{where } \bar{y}_{\text{true}} = \frac{1}{k}\sum_{i=1}^k y_{\text{true}, i}$$

**Terms:**
- $\sigma^2_{\text{AMKB}}$: Empirical variance of ground-truth lifespans among historical neighbors.
- $y_{\text{true}, i}$: Observed failure lifespan of neighbor $i$ (strictly `true_rul`, non-circular).
- $\bar{y}_{\text{true}}$: Mean failure lifespan across the $k$ neighbors.

---

### 16. Machine DNA Standardized Feature Profiling
Establishes a z-score standardized operational envelope per physical machine unit.

$$\boxed{\mathbf{z}_{\text{DNA}} = \frac{\mathbf{x}_{\text{DNA}} - \boldsymbol{\mu}_{\text{DNA}}}{\boldsymbol{\sigma}_{\text{DNA}}}}$$

**Terms:**
- $\mathbf{z}_{\text{DNA}} \in \mathbb{R}^{16}$: Standardized Machine DNA fingerprint.
- $\mathbf{x}_{\text{DNA}}$: Raw multi-modal features (health pattern, thermal profile, power signature, fault history).
- $\boldsymbol{\mu}_{\text{DNA}}, \boldsymbol{\sigma}_{\text{DNA}}$: Fleet baseline mean and standard deviation scaling vectors.

---

## 4. Grounded Explainability Engine (XAI)

### 17. Contrastive Feature Occlusion Deviation
Measures output sensitivity by occluding individual sensor channels with baseline reference means.

$$\boxed{\Delta y_j = |f(X) - f(X_{\setminus j})|}$$

**Terms:**
- $\Delta y_j$: Absolute prediction change when sensor channel $j$ is neutralized.
- $f(X)$: Model inference on full multi-sensor window $X$.
- $f(X_{\setminus j})$: Model inference with sensor column $j$ replaced by domain nominal mean $\bar{x}_j$.

---

### 18. Normalized Percentage Feature Attribution
Converts absolute sensor deviations into an interpretable relative percentage contribution.

$$\boxed{\phi_j = \left(\frac{\Delta y_j}{\sum_{m=1}^D \Delta y_m}\right) \times 100\%}$$

**Terms:**
- $\phi_j \in [0.0, 100.0]\%$: Relative contribution of sensor $j$ to the degradation diagnosis.
- $\sum_{m=1}^D \phi_j = 100.0\%$: Conservation of total attribution across all $D$ channels.

---

### 19. Variance-Penalized Epistemic Confidence Calibration
Calculates explanation trustworthiness by scaling neighborhood similarity inversely with trajectory divergence.

$$\boxed{\mathcal{C} = \bar{s} \times \left(\frac{1.0}{1.0 + \sigma^2_{\text{AMKB}} + \epsilon}\right)}$$

**Terms:**
- $\mathcal{C} \in (0.0, 1.0]$: Epistemic confidence score.
- $\bar{s}$: Mean similarity of retrieved AMKB historical cases.
- $\sigma^2_{\text{AMKB}}$: Outcome variance among retrieved cases.
- $\epsilon = 10^{-4}$: Numerical epsilon protecting against division-by-zero (DEF-009).

---

### 20. Grounding Correlation Metric (Spearman Rank Correlation)
Validates that explanation confidence faithfully reflects prognostic accuracy.

$$\boxed{r_s = 1 - \frac{6 \sum_{i=1}^n d_i^2}{n(n^2 - 1)}}$$

$$\text{where } d_i = \operatorname{rank}(\mathcal{C}_i) - \operatorname{rank}(|\hat{y}_i - y_{\text{true}, i}|)$$

**Terms:**
- $r_s \in [-1.0, 1.0]$: Spearman rank-order correlation coefficient (ATLAS achieves $r_s = -0.5090$).
- Negative correlation indicates high confidence reliably signifies lower prediction error.
- $n$: Number of evaluated test units.

---

## 5. Stochastic Simulation & Cost-Weighted Decision Graph

### 21. Monte Carlo Degradation Uncertainty Realizations
Propagates prognostic uncertainty by drawing stochastic lifecycle realizations from the empirical distribution.

$$\boxed{y^{(m)} \sim \mathcal{N}\left(\hat{y}, \; \max(\sigma^2_{\text{AMKB}}, 10^{-6})\right), \quad m \in \{1, \dots, N\}}$$

$$\text{clamped to } y^{(m)} \in [0.0, \; 125.0]$$

**Terms:**
- $y^{(m)}$: $m$-th simulated Remaining Useful Life realization.
- $\hat{y}$: World model point estimate.
- $\sigma^2_{\text{AMKB}}$: Empirical variance of nearest failure precedents.
- $N$: Number of Monte Carlo draws ($N = 1,000$).

---

### 22. Lead-Time Asymmetric Sample Cost Function
Evaluates economic loss per realization based on action execution horizons versus survival time.

$$\boxed{C(y^{(m)}, a) = \begin{cases} 
C_{\text{unplanned}}, & \text{if } y^{(m)} \le \tau(a) \\
0.0, & \text{if } y^{(m)} > \tau(a) \text{ and } a = \text{CONTINUE\_OPERATION} \\
C_{\text{base}} + C_{\text{downtime}} \cdot \mu_{\text{urgency}}(a), & \text{if } y^{(m)} > \tau(a) \text{ and } a \ne \text{CONTINUE\_OPERATION}
\end{cases}}$$

**Terms:**
- $C(y^{(m)}, a)$: Realized cost for candidate action $a$ under simulated lifespan $y^{(m)}$.
- $\tau(a)$: Action operational lead time ($\tau = 30$ for CONTINUE, $10$ for SOON, $3$ for NOW, $0$ for REPLACE).
- $C_{\text{unplanned}} = \$1,000.0$: Catastrophic failure penalty.
- $C_{\text{base}} = \$50.0$: Baseline scheduled maintenance cost.
- $C_{\text{downtime}} = \$5.0/\text{cycle}$: Production downtime penalty rate.
- $\mu_{\text{urgency}}(a)$: Action urgency multipliers ($\mu \in \{1.0, 1.5, 2.0\}$).

---

### 23. Expected Action Cost
Calculates the expected monetary expenditure of each maintenance candidate across all uncertainty draws.

$$\boxed{\mathbb{E}[C(a)] = \frac{1}{N} \sum_{m=1}^N C(y^{(m)}, a)}$$

**Terms:**
- $\mathbb{E}[C(a)]$: Expected monetary cost for action $a$.
- $N$: Total Monte Carlo iterations ($N = 1,000$).

---

### 24. Empirical Action Failure Probability
Calculates the probability that the unit fails before a scheduled action completes execution.

$$\boxed{p_{\text{fail}}(a) = \frac{1}{N} \sum_{m=1}^N \mathbb{I}\left(y^{(m)} \le \tau(a)\right)}$$

**Terms:**
- $p_{\text{fail}}(a) \in [0.0, 1.0]$: Failure probability under action $a$.
- $\mathbb{I}(\cdot)$: Indicator function returning $1$ if condition is true, $0$ otherwise.

---

### 25. Cost Uncertainty (Simulation Standard Deviation)
Quantifies economic outcome dispersion under prognostic variance.

$$\boxed{\sigma_C(a) = \sqrt{\frac{1}{N} \sum_{m=1}^N \left(C(y^{(m)}, a) - \mathbb{E}[C(a)]\right)^2}}$$

**Terms:**
- $\sigma_C(a)$: Standard deviation of simulated cost.

---

### 26. Operational Risk Score
Combines failure likelihood with economic uncertainty normalized by catastrophic breakdown cost.

$$\boxed{\text{Risk}(a^*) = p_{\text{fail}}(a^*) + \frac{\sigma_C(a^*)}{C_{\text{unplanned}}}}$$

**Terms:**
- $\text{Risk}(a^*) \in [0.0, 2.0]$: Operational composite risk metric.
- $a^*$: Selected optimal candidate action.

---

### 27. Economic Decision Impact
Measures the net financial savings of selecting the optimal intervention over the worst alternative.

$$\boxed{\text{Impact} = \max_{a \in \mathcal{A}} \mathbb{E}[C(a)] - \mathbb{E}[C(a^*)]}$$

**Terms:**
- $\text{Impact} \ge \$0.0$: Fleet capital preserved by the algorithmic recommendation.
- $\mathcal{A}$: Complete action space $\{\text{CONTINUE, SOON, NOW, REPLACE}\}$.

---

### 28. Action Urgency Index
Scales exponentially as RUL drops and empirical uncertainty widens.

$$\boxed{\text{Urgency} = \frac{100.0}{\hat{y} + \sigma^2_{\text{AMKB}} + 1.0}}$$

**Terms:**
- $\text{Urgency} \in (0.0, 100.0]$: Dimensionless priority index for work order dispatch.

---

### 29. Deterministic 4-Tier Safety Cascade (Tie-Breaker)
Eliminates alphabetical string tie-breaking by prioritizing safety during equal-cost dilemmas (DEF-004).

$$\boxed{\text{sort\_key}(a) = \Big(\mathbb{E}[C(a)], \; -p_{\text{fail}}(a), \; \sigma_C(a), \; \text{name}(a)\Big)}$$

$$\boxed{a^* = \arg\min_{a \in \mathcal{A}} \text{sort\_key}(a)}$$

**Terms:**
- Tier 1: $\mathbb{E}[C(a)]$ (Minimizes expected monetary cost).
- Tier 2: $-p_{\text{fail}}(a)$ (Favors safer, more urgent action on cost ties).
- Tier 3: $\sigma_C(a)$ (Favors lower financial variance).
- Tier 4: $\text{name}(a)$ (Deterministic alphabetical tie-breaker).

---

### 30. Near-Failure Zero-Miss Safety Parity Constraint (DEF-008)
Enforces mandatory mechanical replacement whenever predicted lifetime crosses critical hazard limits.

$$\boxed{\text{if } \hat{y} \le 10 \text{ cycles} \quad \text{or} \quad h \le 0.20 \implies a^* \leftarrow \text{REPLACE\_IMMEDIATELY}}$$

**Terms:**
- $10$ cycles: Critical failure boundary where maintenance lead times cannot guarantee safe survival.
- $0.20$: Catastrophic operational stress threshold.

---

## 6. Cross-Domain Transferability & Discrepancy Diagnostics

### 31. Maximum Mean Discrepancy (MMD)
Measures statistical manifold divergence between domain distributions in a Reproducing Kernel Hilbert Space (RKHS).

$$\boxed{\text{MMD}^2(P, Q) = \frac{1}{N^2}\sum_{i,j=1}^N k(x_i, x_j) - \frac{2}{NM}\sum_{i=1}^N\sum_{j=1}^M k(x_i, y_j) + \frac{1}{M^2}\sum_{i,j=1}^M k(y_i, y_j)}$$

$$\text{with multi-scale RBF kernel } k(x, y) = \sum_{\gamma \in \Gamma} \exp\left(-\gamma \|x - y\|^2\right)$$

**Terms:**
- $\text{MMD}(P, Q)$: Non-parametric distribution distance ($0.0$ for identical domains; $\approx 1.23$ between compute and C-MAPSS).
- $P, Q$: Source (e.g. C-MAPSS) and Target (e.g. Mobile, Server) operational distributions.
- $\Gamma = \{10^{-3}, 10^{-2}, 10^{-1}, 1, 10, 10^2\}$: Multi-scale kernel bandwidths.

---

### 32. Cross-Domain Error Inflation Ratio (EIR)
Quantifies the direct degradation in prognosis accuracy when querying cross-domain memory directly.

$$\boxed{\text{EIR} = \frac{\text{RMSE}_{\text{cross}}}{\text{RMSE}_{\text{within}}}}$$

**Terms:**
- $\text{EIR}$: Error Inflation Ratio ($\text{EIR} > 1.0$ indicates negative transfer; Mobile exhibits $8.30\times$, Server $7.10\times$).
- $\text{RMSE}_{\text{cross}}$: Prognostic error querying unadapted C-MAPSS memory.
- $\text{RMSE}_{\text{within}}$: Prognostic error querying within-domain memory.

---

### 33. Negative Transfer Index (NTI)
Quantifies loss of representational discriminability caused by query distribution collapse.

$$\boxed{\text{NTI} = \frac{\operatorname{Var}(\hat{\mathbf{y}}_{\text{cross}}) - \operatorname{Var}(\hat{\mathbf{y}}_{\text{within}})}{\operatorname{Var}(\hat{\mathbf{y}}_{\text{within}}) + 1.0}}$$

**Terms:**
- $\text{NTI} < 0$: Severe negative transfer (unadapted latent vectors land outside manifold support).
- $\operatorname{Var}(\hat{\mathbf{y}}_{\text{cross}})$: Variance of cross-domain predictions (collapses to $\approx 0.00008$).
- $\operatorname{Var}(\hat{\mathbf{y}}_{\text{within}})$: Variance of within-domain predictions ($\approx 0.00603$).

---

## 7. Continuous Learning & Retraining Promotion Gate

### 34. $\epsilon$-Guarded Retraining Promotion Criterion
Ensures candidate models achieve a minimum 3% relative accuracy improvement before atomic deployment.

$$\boxed{\text{RMSE}(\theta_{\text{cand}}) \le (1.0 - \epsilon) \cdot \text{RMSE}(\theta_{\text{active}}) = 0.97 \cdot \text{RMSE}(\theta_{\text{active}})}$$

**Terms:**
- $\theta_{\text{cand}}$: Newly trained candidate model weights.
- $\theta_{\text{active}}$: Active production model weights.
- $\epsilon = 0.03$: Mandatory 3% minimum improvement safety margin preventing regression.

---

### 35. Relative Validation Improvement Margin
Calculates the exact percentage accuracy gain logged to the immutable PostgreSQL audit table.

$$\boxed{\Delta_{\text{rel}} = \left(\frac{\text{RMSE}_{\text{active}} - \text{RMSE}_{\text{cand}}}{\text{RMSE}_{\text{active}}}\right) \times 100\%}$$

**Terms:**
- $\Delta_{\text{rel}}$: Percentage error reduction ($\Delta_{\text{rel}} \ge 3.0\%$ triggers promotion).
