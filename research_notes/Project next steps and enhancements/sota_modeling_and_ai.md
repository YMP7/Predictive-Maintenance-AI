# SOTA (2024–2026) in AI predictive maintenance and industrial digital twins: enhancement ideas for ATLAS

Scope note: this extends `docs/research/LANDSCAPE_REPORT_2026-11.md` (worktree `github-access-question-a4103d`). That report already recommends: split-conformal intervals (now done in ATLAS), FD002–FD004 + protocol table, Backblaze for the server domain, a deterministic answer verifier, a frozen Chronos-2/TTM encoder experiment, an MCP server + AssetOpsBench run, an anomaly-first mode (PyOD/stumpy), ISO 281/Weibull pump wear, a ThingsBoard adapter, AAS export and an HF Space. Items below are additions or sharper versions of those, not repeats. Effort: S = 1–3 days, M = 1–2 weeks, L = 3+ weeks, for one researcher.

Date caveat: today is 2026-11-16. arXiv IDs of the form 26xx.xxxxx are 2026 preprints and are expected; the search tool flagged some as "unusual" only because of its own cutoff. Most findings below come from abstracts and search snippets, not full texts, unless stated.

## Q1. Modeling: TSFMs, physics-informed/hybrid, GNNs, UQ beyond conformal, few-shot/domain adaptation, federated learning

### Takeaway
The useful 2025–26 modeling moves for ATLAS are (a) TSFM embeddings in the *few-shot* regime (where they help most), (b) monotonicity/physics constraints combined with conformal calibration, (c) deep ensembles as the second UQ layer feeding the Monte Carlo cost step, and (d) test-time adaptation for new machines that have only normal data. GNNs and federated learning are real research lines but are higher effort with weaker MSME payoff.

### Cited Findings
**Time-series foundation models (TSFMs) for RUL/anomaly**
- MOMENT embeddings + classical regressors for few-shot RUL on aircraft engines: better performance with only 10% of training data (Dintén & Zorrilla, CMES 144(1), 2025) — [TechScience](https://www.techscience.com/CMES/v144n1/63274)
- Frozen Chronos-2 + small regression head beats recurrent, convolutional, transformer and gradient-boosting baselines on two industrial device types (arXiv 2606.11990, June 2026) — [arXiv](https://arxiv.org/html/2606.11990v2)
- PHM Europe paper evaluates TSFM embeddings on full C-MAPSS and notes that an earlier study (Benzine et al., 2025) found Chronos struggled on C-MAPSS when used naively — [PHM Society](https://papers.phmsociety.org/index.php/phme/article/download/4906/2940)
- TSB-AD (NeurIPS 2024 D&B) is the reference anomaly-detection benchmark: ~1,000+ curated series from 40 datasets, 40 algorithms; the series count differs between versions (1070 vs 1020) — [arXiv 2506.21550](https://arxiv.org/pdf/2506.21550v2); [NeurIPS poster](https://neurips.cc/virtual/2024/poster/97690)
- TSB-AD-U leaderboard includes fine-tuned foundation-model entries (MOMENT_FT, TSPulse_FT, Time-RCD) alongside classic methods; VUS-PR is the headline metric — [arXiv 2609.21801](https://arxiv.org/pdf/2609.21801)
- Counter-evidence: TSB-AutoAD (VLDB) finds TSFMs "have yet to deliver" on one-size-fits-all anomaly detection; naive ensembling is accurate but expensive — [VLDB](https://vldb.org/pvldb/volumes/18/paper/TSB-AutoAD%3A%20Towards%20Automated%20Solutions%20for%20Time-Series%20Anomaly%20Detection%20%5BE%2C%20A%20%26%20B%5D)
- Zero-shot TSFM anomaly work warns that much of TSB-AD "univariate" data is decomposed multivariate data, which can inflate metrics — [arXiv 2509.21190](https://arxiv.org/pdf/2509.21190)

**Physics-informed / hybrid**
- PHM Europe paper: physics constraints added to a Transformer force predicted bearing RUL to be monotonic (data-driven models otherwise violate irreversible degradation), combined with post-hoc conformal calibration for finite-sample intervals; validated on XJTU-SY — [PHM Society](https://papers.phmsociety.org/index.php/phme/article/download/4902/2943)
- PG-SNGP / PG-SNER (Razzaq & Zhao, arXiv 2512.08499, Dec 2025): physics-guided networks with spectral normalization for distance-aware uncertainty, tested on PRONOSTIA, XJTU-SY and HUST — [arXiv](https://arxiv.org/abs/2512.08499)

**Graph neural networks**
- THGNN (Wen et al., IEEE TNNLS, accepted Nov 2025): each sensor is a node, edges from cosine similarity of GRU embeddings, FiLM for heterogeneous sensor types; up to 19.2% / 31.6% improvement on N-CMAPSS (DS02, 20 channels) — [arXiv 2405.04336](https://arxiv.org/html/2405.04336v3)
- Survey of GNNs for RUL (arXiv 2409.19629) covers graph construction and preprocessing for C-MAPSS/N-CMAPSS — [arXiv](https://arxiv.org/pdf/2409.19629)

**Uncertainty beyond conformal**
- Karlsson et al. (IFAC PapersOnLine, 2025, sparse-measurement RUL): MC dropout and deep ensembles both accurate; deep ensembles gave the best-calibrated uncertainty — [Chalmers](https://research.chalmers.se/publication/548776/file/548776_Fulltext.pdf)
- BatchEnsemble (arXiv 2601.21581, Jan 2026) matches deep-ensemble uncertainty at lower cost and clearly beats MC dropout; includes a GRU variant for time series — [arXiv](https://arxiv.org/html/2601.21581v1)
- Contradicting case: crash-simulation surrogate study found a 10-member ensemble overconfident (42.2% coverage at ±2σ) while MC dropout reached 100% — [arXiv 2607.18294](https://arxiv.org/pdf/2607.18294)
- Lee & Mitici (RESS, 2022/23; background): CNN + MC dropout RUL *distributions* fed to a DRL maintenance agent cut turbofan maintenance cost 29.3% vs replacing at mean RUL — [TU Delft](https://research.tudelft.nl/en/publications/deep-reinforcement-learning-for-predictive-aircraft-maintenance-u)

**Domain adaptation / few-shot / test-time adaptation**
- NC-TTDA (Sensors, Dec 2025): test-time domain adaptation using *normal-class data only*, e.g. a model from one machine adapted to another factory's machine — [MDPI](https://www.mdpi.com/1424-8220/25/24/7614)
- TARD (arXiv 2507.16354): unsupervised continual test-time adaptation for fault detection under evolving operating conditions — [arXiv](https://arxiv.org/html/2507.16354v1)
- TACDA (arXiv 2512.02610): cross-domain RUL that keeps target-specific information instead of only global adversarial alignment — [arXiv](https://arxiv.org/pdf/2512.02610)
- Eksploatacja i Niezawodność 2025 paper "Test-Time Adaptation for Cross Domain RUL Prediction: When Does..." exists; method not confirmed — [EIN](https://ein.org.pl/Test-Time-Adaptation-for-Cross-Domain-Remaining-Useful-Life-Prediction-When-Does,226057,0,2.html)

**Federated learning**
- Personalized federated RUL for fragmented out-of-distribution client data (Sun et al., RESS 2025, doi 10.1016/j.ress.2025.111094) — [IDEAS/RePEc](https://ideas.repec.org/a/eee/reensy/v261y2025ics0951832025002959.html)
- Ozdemir et al. (PHM Society 2025): bias from data partitioning and client selection in FL for aviation RUL — [PHM Society](https://papers.phmsociety.org/index.php/phme/article/download/4866/2961)
- Matched-neuron aggregation for heterogeneous clients reports up to 39.3% RUL gain (preprint of IEEE T-ASE paper) — [arXiv 2305.07854](https://arxiv.org/pdf/2305.07854v2.pdf)
- Common theme: FedAvg fails when clients degrade differently; fixes are personalization and client clustering — [heterogeneity-aware PFL summary](https://www.newx.sg/paper/detail/e5a1e02a-3dfb-11f1-b84c-00163e10baa7)

### Inferences
Enhancement ideas (what / why / plug-in / effort):
1. **TSFM few-shot curve** (S–M). Run frozen Chronos-2, TTM-r2 and MOMENT embeddings + MLP head at 5/10/25/100% of FD001 and FD002 training units, against the attention LSTM, 5 seeds. Why: the evidence says TSFMs help most when labels are scarce, which is exactly the MSME case; a full-data-only comparison would likely show little gain (Benzine et al.). Plug-in: a new encoder option in the world-model training script; results table in the evidence page. Extends LANDSCAPE rec #6 with the few-shot axis.
2. **TSFM anomaly scorer on TSB-AD-U/M subset + MetroPT-3** (M). Score ATLAS's anomaly detector against the public TSB-AD leaderboard using VUS-PR. Why: gives the anomaly module an external number, as AssetOpsBench does for the agent. Plug-in: `scripts/` benchmark runner; no runtime change.
3. **Monotone-RUL constraint** (S). Add a penalty on positive RUL increments between consecutive windows (or isotonic post-processing per unit) and report the fraction of non-monotone predictions before/after. Why: cheap physics prior; the PHM Europe paper shows it composes with conformal calibration, which ATLAS already has. Plug-in: loss term in training, or a post-processor before the conformal wrapper.
4. **Deep ensemble (or BatchEnsemble) as the RUL distribution for Monte Carlo cost simulation** (S–M). Train 5 members (ATLAS already trains 5 seeds), use the member spread as epistemic uncertainty, then conformalize. Why: Lee & Mitici show decisions built on RUL *distributions* beat mean-RUL thresholds; the Monte Carlo step currently needs a sampled distribution. Report PICP, interval width, and cost delta vs conformal-only.
5. **Normal-data-only test-time adaptation for a new machine** (M). Adapt BatchNorm/LayerNorm statistics or a small adapter on the target domain's healthy data (NC-TTDA idea). Why: ATLAS's transfer study shows turbofan memory inflates phone error 8.3x; TTA is the direct fix and needs no failure labels. Plug-in: an "onboard new asset" step in the continual retraining loop.
6. **Sensor-graph model (THGNN-style) as an ablation, not the main model** (M–L). Only worth it once N-CMAPSS is in. Lower priority for MSMEs, whose machines usually have few sensors.
7. **Simulated federated study across ATLAS's own domains/units** (M). Partition C-MAPSS engines (or pump simulator instances) into "factories", compare FedAvg vs FedProx vs per-client fine-tune using Flower. Why: the IIETA MSME review (cited in LANDSCAPE) names FL as an enabler; this is a cheap, honest simulation. Not a production feature.

### Gaps
- No head-to-head Chronos-2 vs TTM vs MOMENT on C-MAPSS under a leakage-controlled protocol was found (same gap as LANDSCAPE report).
- No RUL-specific benchmark comparing PICP/width across conformal, ensembles and MC dropout was found; only one 2025 RUL UQ study (Karlsson et al.).
- Full results tables of the PHM Europe physics-constrained paper and PG-SNGP were not read; numbers not verified.

## Q2. Datasets/benchmarks beyond C-MAPSS most relevant for MSME rotating equipment

### Takeaway
For an MSME/pump story the best additions are a bearing run-to-failure set (XJTU-SY or PRONOSTIA) for true RUL, MetroPT-3 for a real industrial compressor with maintenance-report ground truth (anomaly → failure prediction), and DCASE/MIMII machine sound for a cheap phone-microphone modality. N-CMAPSS stays the harder turbofan benchmark. CWRU and Paderborn are fault-classification sets and only fit a diagnosis add-on.

### Cited Findings
- **MetroPT-3**: real metro air-compressor data, 15 analogue/digital sensors, ~1.5M rows Feb–Aug 2020, air-leak failures Apr–Jul 2020 with dates from the operator's maintenance reports; CC BY 4.0; UCI suggests first month train, rest test. Sampling rate stated inconsistently (1 Hz vs 0.1 Hz) on UCI — [UCI](https://archive.ics.uci.edu/dataset/791/metropt+3+dataset); [Veloso et al. arXiv 2207.05466](https://arxiv.org/pdf/2207.05466)
- MetroPT student projects report near-perfect classifier scores that depend on resampling; weak evidence — [GitHub example](https://github.com/Masa-Tantawy/MetroPT-3-Predictive-Maintenance)
- **DCASE 2025 Task 2**: first-shot unsupervised anomalous sound detection under domain generalization; normal-only training data per machine; new evaluation recordings; AUC and pAUC — [arXiv 2506.10097](https://arxiv.org/html/2506.10097v2)
- DCASE 2025 submissions include a lightweight fine-tuned HuBERT + kNN system and an ASP + ArcFace system scoring 0.6132 vs baseline 0.5599 on the dev set — [Sera report](https://dcase.community/documents/challenge2025/technical_reports/DCASE2025_Sera_82_t2.pdf); [Kret report](https://dcase.community/documents/challenge2025/technical_reports/DCASE2025_Kret_63_t2.pdf)
- **N-CMAPSS** simulates full flights (climb, cruise, descent) unlike C-MAPSS's cruise-only conditions; THGNN uses DS02 with 20 channels and subsamples due to size — [GNN survey](https://arxiv.org/pdf/2409.19629); [THGNN](https://arxiv.org/html/2405.04336v3)
- **XJTU-SY / PRONOSTIA / HUST** are the standard bearing run-to-failure sets in 2025 physics-guided RUL work — [arXiv 2512.08499](https://arxiv.org/abs/2512.08499); [PHM Europe](https://papers.phmsociety.org/index.php/phme/article/download/4902/2943)
- SurvCF(t) uses a **Scania Component X** case study (real truck fleet, survival-style labels) together with C-MAPSS/N-CMAPSS — [arXiv 2607.16969](https://arxiv.org/pdf/2607.16969)

### Inferences
Dataset priority for ATLAS (relevance to MSME rotating equipment):
1. **XJTU-SY bearings → pump domain** (M). Real run-to-failure, vibration at high rate; replaces "simulated pump" with real bearing degradation. Needs a feature-extraction adapter (RMS, kurtosis, band energies per snapshot) so the existing RUL pipeline sees low-rate features.
2. **MetroPT-3 → "compressor" domain** (S–M). Real MSME-like asset (compressors are ubiquitous in small factories), real maintenance-report labels, CC BY 4.0. Best fit for the anomaly-first mode and lead-time evaluation ("hours of warning before the logged failure").
3. **DCASE/MIMII → phone-microphone acoustic adapter** (M). ATLAS already has a mobile-phone sensor adapter; a microphone channel + a normal-only anomaly scorer is a very cheap retrofit sensor for MSMEs. DCASE gives an external AUC.
4. **N-CMAPSS DS02** (M) as the harder turbofan benchmark (already in LANDSCAPE; repeated only for completeness).
5. **Scania Component X** (M) if a survival-analysis framing is added (pairs with counterfactual item in Q5).
6. CWRU / Paderborn: background only; fault-type classification, not RUL. Use only if a "diagnose fault type" head is added.
- Azure PdM (telemetry + errors + maintenance + failures, synthetic) was not re-checked this session; it is synthetic and adds little over the existing simulators.

### Gaps
- Licences for XJTU-SY, PRONOSTIA and MIMII/DCASE were not checked this session; check before redistributing derived data.
- MetroPT-3 sampling rate conflict (1 Hz vs 0.1 Hz) unresolved.
- No source compared these datasets specifically for MSME relevance; the ranking above is inference.

## Q3. Agentic/LLM: maintenance agents, industrial benchmarks, multimodal

### Takeaway
The field has two citable external yardsticks (AssetOpsBench for multi-agent task automation, FailureSensorIQ for sensor/failure-mode knowledge) and a growing set of RAG-over-manuals and work-order agents, most of them theses or industry papers without public scores. ATLAS can differentiate by scoring its agent on both benchmarks and by grounding work orders in its own evidence packet.

### Cited Findings
- **AssetOpsBench** (arXiv 2506.03828): four domain-specific agents (IoT, FMSR, TSFM, work-order) + 140+ human-authored queries; v1.0 has 141 scenarios; accepted at KDD 2026 D&B; tests plan-and-execute vs agents-as-tools orchestration — [arXiv](https://arxiv.org/html/2506.03828v3); [IBM blog](https://researchweb.draco.res.ibm.com/blog/asset-ops-benchmark); [project site](https://ibm.github.io/AssetOpsBench/)
- **FailureSensorIQ** (NeurIPS 2025 D&B, arXiv 2506.03278): multiple-choice QA on sensor ↔ failure-mode relationships for 10 industrial assets; over a dozen LLMs evaluated — [NeurIPS](https://papers.nips.cc/paper_files/paper/2025/hash/b7ba530076dee3b4f19847d8dce983da-Abstract-Datasets_and_Benchmarks_Track.html); [arXiv](https://arxiv.org/html/2506.03278v1)
- **MECHA** (AHFE 2025): multi-agent production-line maintenance system covering Q&A, multi-turn fault diagnosis and automated work-order completion — [AHFE](https://openaccess-api.cms-conferences.org/articles/download/978-1-964867-75-5_140)
- **PARAM** (arXiv, Aug 2025): RAG-based prescriptive maintenance agent validated on bearing vibration data — [aitopics](https://aitopics.org/doc/arxivorg:8A46E330)
- Löwenmark et al. (arXiv, Jun 2025): agent-based condition-monitoring assistant with multimodal industrial-database RAG, aimed at fewer false alarms and better fault-severity estimates — [aitopics](https://aitopics.org/doc/arxivorg:191987FC)
- PHM Society 2025 paper compares RAG configurations vs LLM-only and retrieval-only baselines on a troubleshooting task with structured fault codes from technical manuals — [PHM Society](https://papers.phmsociety.org/index.php/phmconf/article/download/4549/phmc_25_4549)
- MIT thesis (2025): multimodal RAG chatbot for root-cause diagnosis over manuals, maintenance records and knowledge bases; lists dynamic work-order generation as future work — [DSpace@MIT](https://dspace.mit.edu/handle/1721.1/163337)
- Multimodal RUL with layer-wise explanations (arXiv 2512.06708) evaluated on bearing data — [arXiv](https://arxiv.org/pdf/2512.06708)

### Inferences
1. **FailureSensorIQ score for the ATLAS agent's LLM** (S). Run the MCQA set through whatever LLM backs the chat (and the local Qwen3-4B LoRA noted in LANDSCAPE). Cheap, external, comparable to the paper's dozen LLMs. Plug-in: eval script only.
2. **Manual-grounded RAG with a fault-code eval** (M). Index pump/compressor manuals (public OEM PDFs) into the existing AMKB retrieval; build a 30–50 question troubleshooting set modelled on the PHM 2025 paper; report LLM-only vs retrieval-only vs RAG. Why: the PHM paper gives a ready experimental design; ATLAS has retrieval but no manual corpus.
3. **Evidence-grounded work-order draft** (S–M). Generate the work-order fields (asset, failure mode, top attributed sensors, RUL interval, recommended action, parts) from the deterministic engine outputs, LLM only writes the narrative, then the verifier (LANDSCAPE #5) checks fields. Why: MECHA and the MIT thesis show demand; none publishes a grounded, verified design. Plug-in: existing work-order module + agent chat.
4. **Root-cause dialogue as a tree over FMEA** (M). Encode a small FMEA table per domain (failure mode → symptoms → sensors → checks); agent asks the operator the next discriminating question. FailureSensorIQ's sensor↔failure-mode framing supplies the knowledge structure.
5. **Multimodal (vibration + audio + image) fusion** (L). Defer: an audio anomaly score (Q2 item 3) as one more input to the existing fusion is the cheap 80% version.

### Gaps
- No published AssetOpsBench or FailureSensorIQ leaderboard numbers were retrieved this session; per-model scores not verified.
- MECHA, PARAM, Löwenmark: only abstracts seen; no quantitative results verified.

## Q4. Digital-twin maturity: synchronization, what-if, prescriptive maintenance, scheduling, spare parts

### Takeaway
Prescriptive maintenance research in 2025 is converging on "decide from the latest RUL *distribution*, jointly with spare parts", with a credible skeptical strand preferring renewal-theory heuristics over black-box DRL. ATLAS's Monte Carlo cost simulation is the right base; the gaps are multi-asset scheduling and spare-parts lead time.

### Cited Findings
- arXiv 2509.20145 (Sep 2025): acknowledges DRL often reaches SOTA but proposes renewal theory + prognostics-based heuristics using the most recent RUL distribution for online decisions; notes most prior work fixes an a-priori threshold or inspection interval — [arXiv](https://arxiv.org/pdf/2509.20145)
- Komninos & Zarouchas (Array 27, 2025): DRL for post-prognosis decisions on multi-component systems with imperfect repair; Value of Information to decide when to acquire new data; splits epistemic/aleatoric uncertainty into action probabilities — [DOAJ](https://doaj.org/article/d6ea08bde5b24d67a8fbd780cf852e02)
- Lee & Mitici (background, RESS): DRL on RUL distributions cut turbofan maintenance cost 29.3% vs mean-RUL replacement — [TU Delft](https://research.tudelft.nl/en/publications/deep-reinforcement-learning-for-predictive-aircraft-maintenance-u)
- Joint maintenance + spare-parts: Nguyen, Do & Grall (PHM Society) use RUL + structural importance for multi-component maintenance, spare ordering and inspection — [PHM Society](https://papers.phmsociety.org/index.php/phme/article/view/1482)
- Zhu et al. (RESS 2025): dynamic PdM on hybrid RUL prediction with multi-state spare ordering, tested on turbofan data — [IDEAS/RePEc](https://ideas.repec.org/a/eee/reensy/v264y2025ipas0951832025004909.html)
- Distributionally robust joint CBM + spare provisioning where prognostics supply lifetime distributions (arXiv 2507.08174, Jul 2025) — [Emergent Mind](https://api.emergentmind.com/papers/2507.08174)
- SurvCF(t) is positioned as prescriptive: counterfactuals over controllable inputs for survival models — [arXiv 2607.16969](https://arxiv.org/pdf/2607.16969)

### Inferences
1. **Spare-parts lead time in the cost simulator** (S). Add part lead time L and holding cost to the Monte Carlo: order when P(RUL < L + slack) exceeds a threshold. Why: the joint-optimization papers show ordering is part of the decision; MSMEs often wait days for parts. Plug-in: decision-support module; new UI field per asset.
2. **Renewal-theory heuristic baseline vs current policy** (S). Implement the arXiv 2509.20145-style rule (decide on latest RUL distribution) as a baseline in the ablation, alongside the RUL-threshold rule ATLAS already beats by 47%. Cheaper and more defensible than adding DRL.
3. **Multi-asset maintenance scheduling with a small MILP** (M). Given per-asset RUL distributions, one technician crew, and shift windows, choose which assets to service this week (OR-Tools CP-SAT or PuLP). Why: a single-asset decision ignores shared crew capacity, the real MSME constraint. Plug-in: a "plan the week" endpoint reading existing RUL/cost outputs.
4. **What-if panel in the 3D twin** (M). Let the operator change load/duty cycle on the simulator-backed domains (pump, laptop, server) and re-run the simulator + RUL model forward, showing the RUL interval shift. Ties directly to counterfactuals (Q5). Real twins only for simulated domains, so label it.
5. **Value-of-information inspection prompt** (M). When RUL interval width is above a threshold, recommend an inspection/extra measurement instead of a repair (Komninos & Zarouchas idea). Simple rule version first.
6. DRL scheduler: defer (L); evidence of advantage over good heuristics is contested.
- Twin synchronization (state estimation, e.g. particle/Kalman filter aligning simulator to live telemetry): no 2024–26 source was gathered this session; see Gaps.

### Gaps
- No 2024–26 source on digital-twin synchronization/state estimation for small-factory twins was retrieved within the tool budget.
- Joint spare-parts papers seen only as abstracts; reported gains not verified.

## Q5. Explainability and trust: counterfactuals, human-in-the-loop, monitoring/drift

### Takeaway
Counterfactual RUL explanations have public code (Andringa et al.) and a 2026 survival-model extension (SurvCF(t)); drift detection has a label-efficient 2025 method (CDSeer). ATLAS can add a counterfactual "what extends RUL" view, operator feedback as labels, and drift-triggered (rather than scheduled) retraining.

### Cited Findings
- Andringa, Baptista & Santos (Information Fusion 118, 2025): RUL counterfactuals with a Bayesian LSTM on C-MAPSS; "uncertainty counterfactuals" as augmentation reduced RMSE from 9.56 to 8.47; code public — [TU Delft repository](https://repository.tudelft.nl/record/uuid:1dc6f636-29ab-49db-86a6-b630e60fd3a3)
- SurvCF(t) (arXiv 2607.16969): counterfactuals for survival models on multivariate time series, optimizing validity, proximity, sparsity and plausibility; tested on C-MAPSS, N-CMAPSS and Scania Component X — [arXiv](https://arxiv.org/pdf/2607.16969)
- Cummins et al. (arXiv 2408.11935): counterfactual what-if analysis for anomaly detection on PRONOSTIA with a TCN — [arXiv](https://arxiv.org/html/2408.11935v1)
- MOXAI (PHM Society): DiCE counterfactuals restricted to operator-controllable features (AI4I 2020, classification) — [PHM Society](https://papers.phmsociety.org/index.php/phme/article/download/4111/2446)
- CDSeer (ICSE 2025 SEIP, arXiv 2410.09190): model-agnostic concept-drift detection; authors report 57.1% better precision with 99% fewer labels than SOTA in an industrial deployment (self-reported) — [arXiv](https://arxiv.org/pdf/2410.09190)
- ADWIN-style windowed performance comparison is a standard post-deployment drift monitor — [USPTO patent text](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12530726)
- Zenisek et al. (2019, background): real-world PdM drift detection is rare due to scarce high-quality monitoring data — [Bohrium](https://www.bohrium.com/paper-details/machine-learning-based-concept-drift-detection-for-predictive-maintenance/812739029031190529-3899)

### Inferences
1. **Actionable counterfactual RUL view** (M). Restrict perturbations to controllable inputs (load, speed, duty cycle — MOXAI's idea), search minimal change that extends predicted RUL by N cycles, report validity/proximity/sparsity (SurvCF(t) metrics). Start from Andringa et al.'s code. Plug-in: explainability API next to occlusion attribution; feeds the what-if panel (Q4 item 4).
2. **Operator feedback as labels** (S–M). Add "confirm / false alarm / fixed: <failure mode>" on alarms and work orders; store as labelled events; use them as conformal recalibration data and as drift-detector labels. Why: closes the human-in-the-loop gap and is the realistic label source on MSME machines without run-to-failure history.
3. **Drift-triggered retraining** (S). Monitor (a) input drift per sensor (KS/PSI on adapter outputs), (b) conformal coverage on recent feedback-labelled events with ADWIN; trigger the existing per-domain retrain when either fires; log in the retrain history ATLAS already records. Why: ATLAS has continual retraining but a scheduled trigger is weaker evidence than a detected-drift trigger.
4. **Coverage-under-drift experiment** (S). Train on FD001, test conformal intervals on FD003 (new fault mode) and report coverage collapse and recovery after recalibration with a few labelled units. Cheap paper result linking UQ, drift and continual learning.

### Gaps
- No 2024–26 PdM-specific drift study on real plant data with reproducible results was found; CDSeer is general ML.
- Andringa et al. code URL not retrieved directly (only the repository record); verify before cloning.
