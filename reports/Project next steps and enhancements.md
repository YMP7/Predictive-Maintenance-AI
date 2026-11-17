# Finish the evidence, then earn real data

ATLAS's next steps are mostly finishing work, not new features. The code is in good shape: there are no TODO or FIXME markers, CI is green on main, and all five domains have trained checkpoints. What remains falls into three groups: (a) evidence the paper already promises but does not fully deliver, such as multi-seed variance beyond C-MAPSS, FD002 to FD004, and the PR #14 conformal result written into the paper; (b) documentation that has drifted from the code, such as legacy SRS/SAD docs that still describe a SQLite prototype with 29 tests, stale checklist items, and a thesis chapter with no pump content; and (c) launch blockers that need decisions only you can make: a domain, Privacy and Terms pages, HTTPS, the `atlas_app` database password, and the "ATLAS" name collision with Atlas CMMS. Two housekeeping facts come first. **This worktree is one PR behind `origin/main`**: PR #14, which adds the split-conformal 90% RUL interval, was merged on 2026-11-16 and is missing here. **A full local test run needs Docker Desktop running**, because without TimescaleDB every database test waits 30 s and then fails. Patent items in the checklist are moot: you are the sole IP owner and decided that no filing is needed. For future enhancements, the 2025–26 literature points to cheap wins that reuse what ATLAS already has. The five seeds it already trains can serve as a deep ensemble. Its Monte Carlo cost step can take spare-parts lead time. ISO 20816 severity zones work on day one, before any history exists. Real compressor and bearing datasets can replace simulated pump data. The prior landscape report (`.claude/worktrees/github-access-question-a4103d/docs/research/LANDSCAPE_REPORT_2026-11.md`) already ranked conformal intervals, FD002 to FD004, Backblaze, an answer verifier, TSFM encoders, MCP plus AssetOpsBench, an anomaly-first mode, ISO 281 pump wear, ThingsBoard, AAS export and an HF Space. This report extends that list and does not re-argue it.

## Part 1. Prioritized checklist: 9 "Now" items clear the way for everything else

The sources are the codebase audit of this worktree (base `ee52006`, 2026-11-11), the master checklist `ATLAS Master Checklist v1-v5 Design and Project Status.md` (L-numbers are its line numbers), and `docs/paper/ieee/paper.md`. Each item names its evidence and a "done when" test.

### Now (this week; unblocks everything else)

#### Repo and environment
- [ ] **Sync this worktree with `origin/main`** (PR #14, conformal RUL, merged 2026-11-16, commit `46577b9`). Evidence: `git log origin/main -3`. `server/atlas/rul_engine.py` conformal changes, `scripts/conformal_rul.py`, `tests/test_conformal_rul.py` and `docs/research/LANDSCAPE_REPORT_2026-11.md` are all missing locally. **Done when** `git log -1` shows `46577b9` or later and `scripts/conformal_rul.py` exists.
- [ ] **Start Docker Desktop and TimescaleDB, then run the full suite.** Evidence: a local run on 2026-11-16 gave 83 passed, 14 skipped and 1 failed (`test_api.py::test_control_endpoint_jwt_auth`, `PoolTimeout`), because `docker ps` could not reach the engine. A run without `-x` hit a 590 s timeout. The last recorded full count is 455 (`docs/redesign/CHANGELOG.md:12`). **Done when** `conda run -n myenv python -m pytest -q` finishes with no failures and the new count is recorded in the changelog.

#### Docs hygiene (cheapest, highest-credibility fixes)
- [ ] **Tick stale checklist items.** Evidence: paper sections A/B/C (L127-129) now exist (`paper.md:126-178`). "UI flow to resolve work orders (not built)" (L191) is already built (`client/src/pages/ops/WorkOrdersPage.tsx:22-27`). **Done when** both are ticked with a pointer to the file.
- [ ] **Close the four patent candidates (L135-138) as "dropped".** Evidence: your decision of 2026-11-08 (sole IP owner, no filing). **Done when** the items read "dropped, no IP filing" and the `ip/zero-energy-gate` branch is deleted.
- [ ] **Remove the v0.2 IP placeholder.** Evidence: `docs/paper/ATLAS_research_paper_v0.2.md:188` says "to be filled in after IP clearance". **Done when** the placeholder is replaced with the Apache-2.0 statement, or the file is marked superseded by the IEEE paper.
- [ ] **Add a "LEGACY prototype" banner to the old docs.** Evidence: the SRS (`:5-7`), the SAD (`:4-8`), the Quick Start Checklist, the Step-by-Step Procedure, the Testing doc and the Project Management doc still describe SQLite, rule-based detection and "29 tests". Test counts conflict across the docs: 29, 69, 290, 378 and 455. The SRS promises Bhashini, OPC-UA and FFT edge processing, none of which exists in code. This covers L195 and L197. **Done when** each file starts with a banner pointing to the current docs, and only one test count remains in the live docs.
- [ ] **Refresh `ATLAS_PROJECT_CONTEXT.md` Section 6** (L122/L198). It was last edited 2026-11-10, before the pump, retraining and conformal work. Line 205 still has an unticked "Month 2 Week 1" box. **Done when** Section 6 lists PR #12 to #14 and line 205 is resolved.

#### Paper
- [ ] **Write the PR #14 conformal result into the paper.** Evidence: `paper.md:209-211` still lists "confidence uncalibrated" as a limitation. Conformal coverage exists only for C-MAPSS. **Done when** Results reports the empirical coverage and width of the 90% interval, and Limitations says it covers C-MAPSS only.
- [ ] **Update the availability statement** (`paper.md:219`, "available from the authors on request") to point to the public Apache-2.0 repo (`LICENSE:2`). **Done when** the statement names the repo URL and the license.

### Next (2–6 weeks; closes the paper and thesis)

#### Evaluation
- [ ] **Multi-seed mean ± std for every headline number** (L75, L140). Evidence: only C-MAPSS has 5 seeds (`atlas_evaluation_summary.json`), and each domain encoder has one seed (`paper.md` Limitations). **Done when** every headline table cell is mean ± std over 5 seeds.
- [ ] **FD002 to FD004 results plus a protocol table.** Evidence: the paper's future work (`paper.md:213-215`) and landscape rec #3. **Done when** RMSE and PHM score for all four subsets appear next to a protocol table (window, RUL cap, normalization, split).
- [ ] **Extend conformal intervals beyond C-MAPSS** (pump, then the compute domains), using the PR #14 code. **Done when** each domain with RUL labels reports coverage and width.
- [ ] **Run the original Ablation 4** (single-domain vs cross-domain-informed world model), **or formally drop it** (L133). **Done when** there is a result row, or a documented reason it was dropped.
- [ ] **Coverage-under-drift experiment**: calibrate on FD001, test on FD003, then recalibrate on a few FD003 units. Source: the SOTA notes (Q5 item 4). **Done when** the paper reports coverage before drift, after drift and after recalibration.

#### Code
- [ ] **Hard safety override and defer-to-human tie margin** in the decision graph. Evidence: both are marked FUTURE (checklist §8), and "no hard safety override" is listed in `paper.md:209-211`. **Done when** a test shows a near-tie or a safety-critical asset routes to the human approval queue.
- [ ] **Learning Engine promote/rollback `learning_events` rows** (L178). There is only 1 row in the database today. **Done when** a promote and a rollback each leave a row, and the test asserts both.
- [ ] **Switch the API to the `atlas_app` database role** (L205; `scripts/migrate_platform.py`, `API_DATABASE_URL`). This needs your password choice. **Done when** the API connects as `atlas_app` and CI runs with it.

#### CI and quality
- [ ] **Align Python versions.** CI uses 3.10 (`.github/workflows/ci.yml`) while the Dockerfile uses 3.12. **Done when** CI tests the same interpreter that ships.
- [ ] **Add a Playwright e2e job and a Docker image build to CI.** Evidence: CI has neither, and e2e and axe run only locally (`client/package.json` `e2e`). **Done when** both jobs are green on a PR.
- [ ] **Open the 10 items in `docs/GOOD_FIRST_ISSUES.md` as GitHub issues.** `gh issue list` is empty. **Done when** the issues exist and are labelled.

#### Paper and thesis
- [ ] **Update the thesis chapter** (`docs/ATLAS_THESIS_CHAPTER.md`, last edited 2026-11-07). It has zero mentions of pump or Modbus, and its "## 6. Continuous Learning Engine & Promotion Gate" heading (`:257`) breaks the batch-only wording rule. This covers L121. **Done when** the chapter covers the Modbus/pump domain, retrain history, attribution for all domains and conformal intervals, and the heading says "batch retraining".
- [ ] **Release the ATLAS Cross-Domain Benchmark** (data and eval scripts, L139). **Done when** a tagged release or an HF dataset exists and the paper cites it.
- [ ] **Choose a venue and submit.** Round-1 internal review and response already exist (`docs/paper/ieee/review/`). **Done when** a submission ID exists. Also check that the `.docx` builds match the markdown (not audited).

### Later (needs hardware, money or launch decisions)

#### Deployment and launch (your launch rules: domain, favicon, privacy, terms)
- [ ] **Resolve the "ATLAS" vs Atlas CMMS name collision** before any public launch (landscape rec #1). **Done when** you have recorded a naming decision.
- [ ] **Custom domain plus HTTPS** (Nginx or Caddy with Let's Encrypt; L188). There is no deploy directory, `README.md:133` says HTTPS is not set up, and CORS is `http://localhost:3000`. **Done when** the site serves over HTTPS on your domain and `CORS_ORIGINS` is set to it.
- [ ] **Privacy Policy and Terms pages.** Neither route exists (`client/src/app/routes.tsx:32-97`). **Done when** both routes render and are linked in the footer. The favicon (`client/public/favicon.svg`) and "no Made with AI tag" rules are already met.
- [ ] **Production cache headers.** `client/index.html:9-11` sets no-cache on every load. **Done when** hashed assets are cached long-term and only `index.html` is no-cache.
- [ ] **Twilio live delivery** (L189; `SECURITY.md:66`). It runs in sandbox only today. **Done when** an alert reaches a real phone.
- [ ] **Operations basics** from the deployment guide: NTP, backups, monitoring and a 48-hour baseline (`docs/AI Agent Deployment and Operations Guide.md:72-94`). **Done when** each one is configured and documented.

#### Hardware-bound validation
- [ ] **Server adapter on a real cloud VM** (L61). It falls back to simulation without `SSH_SERVER_HOST` (`server/adapters/server_adapter.py:102`). **Done when** a recorded run uses real SSH metrics.
- [ ] **Mobile adapter on a real device** (L62). **Done when** a recorded run comes from a phone.
- [ ] **Real pump or bearing validation.** Pump RUL RMSE of 7.72 cycles was measured on simulated units only (checklist §11). **Done when** results exist on real run-to-failure data (XJTU-SY as a stopgap; see Part 2).
- [ ] **Record the demo video** (`docs/DEMO_VIDEO_SCRIPT.md` exists; no recording found). **Done when** the video is linked from the README.

#### Housekeeping
- [ ] **Clean up branches**: about 20 local `claude/*` branches; `database` (1 commit, 2026-07-09, stale); `origin/devin/1789800814-review-fixes` (not examined). **Done when** merged branches are deleted and the two unexamined branches are either merged or closed.
- [ ] **Local client typecheck.** `client/node_modules` is absent, so `npm ci && npm run build` was not run locally (CI builds it). **Done when** the build passes locally.
- [ ] **Bonus tier** (HPC or industrial partner; L63). This stays FUTURE.

## Part 2. Future enhancements: what ATLAS can borrow from 2025–26 work

Effort: S = 1–3 days, M = 1–2 weeks, L = 3+ weeks, for one researcher. "(unverified)" means the notes saw only an abstract or snippet, or the source is vendor or self-reported. Items already ranked in the landscape report appear only as one-line pointers (marked LR#n).

### Modelling: the evidence favours few-shot TSFMs and ensembles over bigger models

TSFMs help most when labels are scarce. MOMENT embeddings beat baselines using **only 10% of C-MAPSS training data** ([TechScience](https://www.techscience.com/CMES/v144n1/63274)), while naive Chronos struggled on full C-MAPSS ([PHM Society](https://papers.phmsociety.org/index.php/phme/article/download/4906/2940)). The useful experiment is therefore a few-shot curve, not a full-data contest. For uncertainty, **deep ensembles gave the best-calibrated RUL uncertainty** in a 2025 sparse-measurement study ([Chalmers](https://research.chalmers.se/publication/548776/file/548776_Fulltext.pdf)). One crash-surrogate study found the opposite (an ensemble at 42% coverage) ([arXiv 2607.18294](https://arxiv.org/pdf/2607.18294)), so ATLAS should conformalize the ensemble, not trust it raw.

| Enhancement | Effort | Why it matters | Source | Plugs into ATLAS |
|---|---|---|---|---|
| TSFM few-shot curve (Chronos-2, TTM, MOMENT at 5/10/25/100% of FD001/FD002, 5 seeds) | S–M | Tests TSFMs where MSMEs actually are, with scarce labels; extends LR#6 | [TechScience](https://www.techscience.com/CMES/v144n1/63274), [arXiv 2606.11990](https://arxiv.org/html/2606.11990v2) (unverified) | New encoder option in the world-model training script; evidence page |
| Monotone-RUL constraint (loss penalty or isotonic post-processing) | S | A cheap physics prior that composes with conformal calibration | [PHM Society](https://papers.phmsociety.org/index.php/phme/article/download/4902/2943) (unverified numbers) | `server/atlas/train_rul.py`, applied before the conformal wrapper |
| Deep ensemble or BatchEnsemble from the existing 5 seeds as the RUL distribution | S–M | Decisions on RUL *distributions* cut turbofan maintenance cost **29.3%** vs mean-RUL replacement | [TU Delft](https://research.tudelft.nl/en/publications/deep-reinforcement-learning-for-predictive-aircraft-maintenance-u), [arXiv 2601.21581](https://arxiv.org/html/2601.21581v1) | `rul_engine.py` feeding `simulation.py` |
| Normal-data-only test-time adaptation for a new machine | M | Fixes the transfer study's 8.3x phone error without failure labels | [MDPI Sensors](https://www.mdpi.com/1424-8220/25/24/7614), [arXiv 2507.16354](https://arxiv.org/html/2507.16354v1) | `transfer_study.py`; onboarding step in `learning_engine.py` |
| Simulated federated study (FedAvg vs FedProx vs per-client fine-tune via Flower) | M | FedAvg fails when clients degrade differently; an honest simulation, not a product feature | [RePEc](https://ideas.repec.org/a/eee/reensy/v261y2025ics0951832025002959.html), [PHM Society](https://papers.phmsociety.org/index.php/phme/article/download/4866/2961) | C-MAPSS units split into "factories" in a new script |
| Sensor-graph ablation (THGNN-style) | M–L | Up to 19–32% gains on N-CMAPSS, but MSME machines have few sensors | [arXiv 2405.04336](https://arxiv.org/html/2405.04336v3) | Ablation only, after N-CMAPSS is in |

### Datasets and evaluation: three real datasets retire the "simulated" objection

The biggest weakness reviewers will hit is still simulated data. **MetroPT-3** is a real metro air compressor with 15 sensors, ~1.5M rows and air-leak failures dated from the operator's maintenance reports, under CC BY 4.0 ([UCI](https://archive.ics.uci.edu/dataset/791/metropt+3+dataset)). Its sampling rate is stated inconsistently (1 Hz vs 0.1 Hz). Compressors are everywhere in small factories, which makes MetroPT-3 the closest public analogue to an MSME asset.

| Enhancement | Effort | Why it matters | Source | Plugs into ATLAS |
|---|---|---|---|---|
| MetroPT-3 as a "compressor" domain (anomaly lead time before logged failures) | S–M | Real labels from maintenance logs, for an MSME-typical asset | [UCI](https://archive.ics.uci.edu/dataset/791/metropt+3+dataset), [arXiv 2207.05466](https://arxiv.org/pdf/2207.05466) | New `ConfigurableAdapter` profile in `server/adapters/domain_profile.py` |
| XJTU-SY bearings for the pump domain (RMS, kurtosis, band-energy features) | M | Replaces the simulated pump with real run-to-failure bearing data; licence not yet checked | [arXiv 2512.08499](https://arxiv.org/abs/2512.08499) | `train_pump_rul.py` plus a feature-extraction step in `modbus_adapter.py` |
| DCASE 2025 / MIMII phone-microphone acoustic anomaly | M | A free retrofit sensor; normal-only training gives an external AUC | [arXiv 2506.10097](https://arxiv.org/html/2506.10097v2) | `mobile_adapter.py` microphone channel |
| TSB-AD-U/M plus MetroPT-3 anomaly benchmark using VUS-PR | M | Gives the anomaly module an external number. Caveat: TSFMs "have yet to deliver" on AD | [arXiv 2506.21550](https://arxiv.org/pdf/2506.21550v2), [VLDB](https://vldb.org/pvldb/volumes/18/paper/TSB-AutoAD%3A%20Towards%20Automated%20Solutions%20for%20Time-Series%20Anomaly%20Detection%20%5BE%2C%20A%20%26%20B%5D) | Runner in `scripts/`; no runtime change |
| Scania Component X (survival framing) | M | Real truck fleet; pairs with counterfactuals | [arXiv 2607.16969](https://arxiv.org/pdf/2607.16969) | Only if a survival head is added |
| Already ranked: N-CMAPSS DS02, Backblaze for the server domain (LR#4), NASA/CALCE batteries | M | See landscape report | LR §4 | Existing adapters |

### Agent and LLM: two citable benchmarks the chat agent has not faced

**FailureSensorIQ** (NeurIPS 2025 D&B) tests sensor-to-failure-mode knowledge across 10 industrial assets, with over a dozen LLMs evaluated ([arXiv](https://arxiv.org/html/2506.03278v1)). Running it is an eval script, not a feature. **AssetOpsBench** (141 scenarios, KDD 2026 D&B) remains the agent-level yardstick ([project site](https://ibm.github.io/AssetOpsBench/), LR#7). Leaderboard scores for both were not retrieved (unverified).

| Enhancement | Effort | Why it matters | Source | Plugs into ATLAS |
|---|---|---|---|---|
| FailureSensorIQ score for the chat LLM | S | External, comparable number at near-zero cost | [NeurIPS](https://papers.nips.cc/paper_files/paper/2025/hash/b7ba530076dee3b4f19847d8dce983da-Abstract-Datasets_and_Benchmarks_Track.html) | Eval script around `server/llm_agent.py` |
| Evidence-grounded work-order draft (engine fills the fields, LLM writes only the narrative, verifier checks it) | S–M | MECHA and an MIT thesis want this; none publishes a verified design | [AHFE](https://openaccess-api.cms-conferences.org/articles/download/978-1-964867-75-5_140), [DSpace@MIT](https://dspace.mit.edu/handle/1721.1/163337) | `server/agent_tools.py` work-order tool plus the LR#5 verifier |
| Manual-grounded RAG with a 30–50 question fault-code eval (LLM-only vs retrieval-only vs RAG) | M | A ready experimental design from PHM 2025 | [PHM Society](https://papers.phmsociety.org/index.php/phmconf/article/download/4549/phmc_25_4549) | `server/atlas/amkb.py` retrieval plus a manuals corpus |
| FMEA-tree root-cause dialogue (the agent asks the next discriminating question) | M | Turns chat into guided diagnosis | [arXiv 2506.03278](https://arxiv.org/html/2506.03278v1) | Per-domain FMEA table plus `llm_agent.py` |
| Already ranked: answer verifier (LR#5), MCP server plus AssetOpsBench (LR#7) | S–M | See landscape report | LR §5.4 | `llm_agent.py` |

### Prescriptive and decision: lead time and crew capacity are the missing MSME constraints

The 2025 literature decides from the **latest RUL distribution, jointly with spare parts** ([RePEc](https://ideas.repec.org/a/eee/reensy/v264y2025ipas0951832025004909.html), unverified gains). A credible counter-strand argues that renewal-theory heuristics compete with DRL ([arXiv 2509.20145](https://arxiv.org/pdf/2509.20145)). ATLAS's decision graph does not beat a tuned threshold rule (`paper.md:209-211`), so a stronger baseline is honest progress. DRL itself should wait.

| Enhancement | Effort | Why it matters | Source | Plugs into ATLAS |
|---|---|---|---|---|
| Spare-parts lead time and holding cost in Monte Carlo (order when P(RUL < L + slack) > p) | S | MSMEs wait days for parts; ordering is part of the decision | [PHM Society](https://papers.phmsociety.org/index.php/phme/article/view/1482) | `simulation.py`, `decision.py`, a per-asset UI field |
| Renewal-theory heuristic as an ablation baseline | S | More defensible than DRL; answers the "tuned threshold" limitation | [arXiv 2509.20145](https://arxiv.org/pdf/2509.20145) | `ablation_engine.py` |
| Multi-asset weekly schedule (CP-SAT/PuLP; one crew, shift windows) | M | Shared technician capacity is the real MSME constraint | Inference from the notes; no direct source | New "plan the week" endpoint reading RUL and cost outputs |
| Value-of-information prompt (wide interval leads to "inspect" instead of "repair") | M | Uses uncertainty for a decision, not just for display | [DOAJ](https://doaj.org/article/d6ea08bde5b24d67a8fbd780cf852e02) | `decision.py` rule on conformal width |
| What-if panel on simulated domains (change load, re-run sim plus RUL) | M | Makes "digital twin" literal; label it simulated | [arXiv 2607.16969](https://arxiv.org/pdf/2607.16969) | 3D asset page plus `simulation.py` |

### Trust and MLOps: drift-triggered retraining beats a schedule

ATLAS already has batch retraining with a 3% gate and a retrain history. What it lacks is a *reason* to retrain. **CDSeer reports 57.1% better precision with 99% fewer labels** in an industrial drift deployment, a self-reported, general-ML result ([arXiv 2410.09190](https://arxiv.org/pdf/2410.09190)). For counterfactuals, Andringa et al. publish C-MAPSS code and report RMSE falling **from 9.56 to 8.47** with uncertainty counterfactuals as augmentation ([TU Delft](https://repository.tudelft.nl/record/uuid:1dc6f636-29ab-49db-86a6-b630e60fd3a3)). The code URL is not yet verified.

| Enhancement | Effort | Why it matters | Source | Plugs into ATLAS |
|---|---|---|---|---|
| Operator feedback as labels (confirm / false alarm / fixed: failure mode) | S–M | The only realistic label source on MSME machines; feeds recalibration and drift | [PHM Society MOXAI](https://papers.phmsociety.org/index.php/phme/article/download/4111/2446) | `server/operations_api.py` alarms and work orders |
| Drift-triggered retraining (per-sensor KS/PSI plus ADWIN on conformal coverage) | S | Stronger evidence than scheduled retraining | [arXiv 2410.09190](https://arxiv.org/pdf/2410.09190) | `learning_engine.py`; logged in the retrain history |
| Actionable counterfactual RUL view (controllable inputs only; validity, proximity, sparsity) | M | "What extends RUL" is what an owner asks | [TU Delft](https://repository.tudelft.nl/record/uuid:1dc6f636-29ab-49db-86a6-b630e60fd3a3), [arXiv 2607.16969](https://arxiv.org/pdf/2607.16969) | `server/atlas/explain.py` next to occlusion attribution |
| Model-health card (alert precision from work-order closures, version registry, rollback) | M | Failures are rare, so work-order precision is the only honest metric | [IIETA review](https://www.iieta.org/journals/jesa/paper/10.18280/jesa.590611) (date metadata inconsistent) | Admin models page plus `learning_events` |

### Sensing and edge: a sub-₹5k ESP32 node makes the first real industrial domain

A 2025 Sensors paper builds an **ESP32 node with a MEMS accelerometer and microphone, with on-device anomaly detection**, aimed at small rotating machines ([PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12609400/)). An ADXL345 is enough for broadband ISO-style RMS severity. Bearing-defect frequencies need a lower-noise ADXL355 (practitioner guidance, not peer-reviewed) ([Zbotic](https://zbotic.in/industrial-vibration-sensor-predictive-maintenance-guide/)). The ₹ figure is an estimate: the paper's cost table was not read.

| Enhancement | Effort | Why it matters | Source | Plugs into ATLAS |
|---|---|---|---|---|
| ESP32 vibration node firmware plus `Esp32VibrationAdapter` (RMS velocity, crest factor, kurtosis, coarse FFT over MQTT; BOM in ₹) | M | The first real, non-simulated industrial domain | [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12609400/), [KMITL](https://dspace.kmitl.ac.th/items/28d053d4-e4ed-4231-98bf-f47b02acc067) | Subclass `base_adapter.py` via `server/mqtt_client.py`; `tests/test_adapter_conformance.py` |
| CT-clamp run-hours and load channel (SCT-013) | S | The cheapest utilization and power-signature signal | [Edge Impulse](https://docs.edgeimpulse.com/experts/brushless-dc-motor-anomaly-detection) | Same adapter, `current_rms` feature |
| Edge anomaly-first baseline (K-means centroids learned over a 3–7 day commissioning window) | M | No run-to-failure labels on MSME machines; extends LR#8 | [Edge Impulse](https://docs.edgeimpulse.com/experts/brushless-dc-motor-anomaly-detection) | Server-side first, then exported to firmware |
| Offline-first "ATLAS Edge" compose profile (RPi; Mosquitto persistence, QoS1 store-and-forward) | M | Intermittent shop-floor connectivity (inference; no source quantifies it) | Inference from the notes | `docker-compose.yml` profile |
| Commissioning wizard (machine class, mount photo, baseline timer) | M | Adoption barriers are skills, not algorithms | [IIETA review](https://www.iieta.org/journals/jesa/paper/10.18280/jesa.590611) | Admin onboarding route plus asset profiles |

### Standards and interoperability: ISO 20816 first, AAS PdM submodel for credibility

Adopt standards in this order: ISO 20816-3 severity zones, then Sparkplug B (now **ISO/IEC 20237:2023**, [ISO](https://www.iso.org/standard/86204.html)), then OPC UA only where machines already expose it, then AAS export. The new **IDTA 02048 Predictive Maintenance submodel (June 2025)** gives the AAS export (LR#11) a specific target ([IDTA](https://industrialdigitaltwin.org/wp-content/uploads/2025/06/IDTA-02048_Submodel_PredictiveMaintenance.pdf)). The ISO 20816 zone values come from vendor blogs, not the ISO text. Verify them before citing.

| Enhancement | Effort | Why it matters | Source | Plugs into ATLAS |
|---|---|---|---|---|
| ISO 20816-3 severity module (A–D zones plus a baseline-relative alarm/trip) | S | Interpretable value from day one, with no ML and no history | [Fabrico](https://www.fabrico.io/blog/iso-20816-vibration-severity-zones/) (secondary) | New function plus unit test; colour band on the 3D twin; rule feature beside the anomaly score |
| Sparkplug B topics and payload (Eclipse Tahu); birth/death gives free "sensor offline" detection | M | Typed payloads and state management over plain MQTT | [Eclipse](https://sparkplug.eclipse.org/resources/articles/2022-07-12-the-key-differences-between-opc-ua-and-mqtt-sparkplug/) | `server/mqtt_client.py`, keeping JSON as a fallback |
| AAS export with Nameplate, TechnicalData, IDTA 02029 MeasurementValue and IDTA 02048 PdM; validate in BaSyx | M | Industrial reviewers take "digital twin" seriously | [IDTA 02048](https://industrialdigitaltwin.org/wp-content/uploads/2025/06/IDTA-02048_Submodel_PredictiveMaintenance.pdf), [IDTA 02029-1](https://industrialdigitaltwin.org/en/wp-content/uploads/sites/2/2025/12/IDTA-02029-1_Sensor4.0_MeasurementValue.pdf) | `/assets/{id}/aas` in `server/platform_api.py` |
| Read-only OPC UA client adapter (`asyncua`) | M | Only for newer CNCs and PLCs | [Proxus](https://proxus.io/blog/mqtt-vs-opc-ua-in-modern-iiot/) | New adapter; `docs/GOOD_FIRST_ISSUES.md` already lists it |
| Real Modbus RTU/TCP recipe (RS-485 to USB for energy meters and VFDs) | S–M | Uses devices already installed in MSME panels (inference) | Inference from the notes | `scripts/modbus_bridge.py` docs |
| ISO 13374 / OSA-CBM mapping table | S | Documentation for reviewers. Block names come from background knowledge and must be verified | Unverified | `docs/` only |

### Workflow and integration: predictions only pay off as WhatsApp work orders

Since 1 July 2025, Meta bills WhatsApp per delivered template message ([Meta](https://developers.facebook.com/docs/whatsapp/pricing)). An India utility template costs about **₹0.115 ex-GST** ([Montymobile](https://montymobile.com/blogs/whatsapp-business-api-pricing-in-india-inr-rates-gst-and-the-2026-currency-migration-deadline)). At that rate, 20 machines with 2 alerts a day comes to about ₹150 a month. Sources conflict on when in-window utility messages started being charged (1 Jan vs 1 Oct 2026).

| Enhancement | Effort | Why it matters | Source | Plugs into ATLAS |
|---|---|---|---|---|
| WhatsApp utility-template alerts with reply-to-ack or reply-to-create-WO webhook | S–M | Meets technicians where they already are | [Meta](https://developers.facebook.com/docs/whatsapp/pricing) | `server/alert_handler.py`, `tests/test_notifications.py` |
| Alert hygiene (dedup, hysteresis, quiet hours, escalation) | S | Alert fatigue kills PdM (inference) | Inference from the notes | `server/alert_handler.py` |
| `WorkOrderSink` interface plus one CMMS connector (ERPNext or Atlas CMMS) | M | Fits existing workflows. Integrating with Atlas CMMS makes the name collision more visible | [GitHub Grashjs/cmms](https://github.com/Grashjs/cmms) | `operations_api.py` work orders |
| Failure-mode pick list on work-order closure, used as a label source | S | Closes the ML feedback loop | Inference; ties to commit `232e9a6` | `WorkOrdersPage.tsx` plus learning engine |
| Hindi plus one regional language (react-i18next; Bhashini or IndicTrans2) | M | The SRS promised Bhashini and it was never built | [Apolitical](https://apolitical.co/en/navigator/case-studies/india-using-ai-to-make-government-services-available-in-22-languages) (secondary) | Client strings; `ALERT_LANGUAGES` (`alert_handler.py:141`) |
| Daily shift digest (PDF or WhatsApp) | S | Matches how owners consume information (inference) | Inference from the notes | Scheduled job |

### Security and privacy: read-only OT and DPDP-minimal by design

The DPDP Rules 2025 were notified on 13 Nov 2025, with core obligations due around **May 2027** (sources differ on 12 vs 13 May) ([AZB & Partners](https://www.azbpartners.com/bank/update-indias-digital-personal-data-protection-framework-comes-into-effect/)). They touch only personal data: recipient phone numbers, names and chat logs. Machine telemetry is not personal data. IEC 62443 SL2 is the practical target, but every claim about it comes from secondary vendor sources ([FlowFuse](https://flowfuse.com/blog/2026/05/nis2-iec-62443-manufacturers)). This is not legal advice.

| Enhancement | Effort | Why it matters | Source | Plugs into ATLAS |
|---|---|---|---|---|
| Read-only OT posture (no register writes exposed; documented) | S | The biggest trust-builder with plant owners (inference) | Inference from the notes | Adapters plus `SECURITY.md` |
| MQTT TLS on 8883 with per-device credentials and Sparkplug-scoped ACLs | S | Anonymous access is already off; this completes the setup | [NIST MEP](https://nist.gov/mep/cybersecurity-resources-manufacturers/where-start) | `scripts/generate_mqtt_passwords.py`, Mosquitto config |
| DPDP-minimal recipients (consent text, deletion endpoint, chat-log retention) | S | Required once WhatsApp alerts hold phone numbers | [AZB & Partners](https://www.azbpartners.com/bank/update-indias-digital-personal-data-protection-framework-comes-into-effect/) | `server/auth.py` users; ties to the Privacy page launch blocker |
| Finer roles (owner, supervisor, technician, viewer) plus config-change audit | M | Extends existing RBAC and the hash-chained audit | [Security Boulevard](https://securityboulevard.com/2026/06/zone-and-conduit-modelling-under-iec-62443-a-practical-guide-for-uk-smes/) | `server/auth.py`, `server/audit.py` |
| Outbound-only support tunnel (WireGuard or Tailscale) | S | No inbound ports opened at the plant | Inference from the notes | Deployment docs |

### Adoption and business: a pilot kit and SAMARTH centres beat waiting for subsidies

The **SAMARTH Udyog Industry 4.0 centres provide no financial assistance**, only awareness, demos and training ([Lok Sabha reply](https://eparlib.nic.in/bitstream/123456789/2970836/1/AS129.pdf)). Digital MSME is listed as "yet to be launched" ([NI-MSME](https://nimsme.gov.in/about-scheme/msme-champions-scheme)). That points to partnering for pilots rather than counting on subsidies. Competitor pricing is opaque. Nanoprecise is estimated at **$40–120 per asset per month** by a third party ([SoftwareFinder](https://softwarefinder.com/facility-management-software/nanoprecise)). Augury's 310% ROI comes from a study Augury commissioned ([Augury](https://www.augury.com/media-center/press/augurys-solutions-delivered-310-3-year-return-according-to-independent-research/)).

| Enhancement | Effort | Why it matters | Source | Plugs into ATLAS |
|---|---|---|---|---|
| "Pilot in a box": 3 ESP32 nodes, an RPi gateway and a 6-week protocol | M | Mirrors the 4–8 week, 2–3 asset pilots competitors run (vendor guide) | [Guidewheel](https://www.guidewheel.com/compare/what-is-augury-guide-better-alternative) | Docs plus the edge profile |
| ROI calculator in the UI (downtime ₹/hour, breakdowns per year, payback) | S | Cost is a top barrier; speaks the owner's language | [ecorpit](https://ecorpit.com/ai-predictive-maintenance-factory-floor-india-roi-2026/) (vendor-sourced) | About or evidence page |
| Case-study instrumentation (before/after MTBF, stoppages, alert precision) | S | Produces the India-specific, non-vendor ROI evidence that is missing; publishable | [Khan et al., IEEE Access](https://doaj.org/article/ca23140a35594f2ebedb85991dc70824) | Audit log plus work orders |
| SAMARTH centre outreach (C4i4 Pune, IISc I-4.0 India, CMTI SMDDC) | S | A free, open tool fits their non-funding mandate (inference) | [SAMARTH portal](https://samarthudyog-i40.in/about) | Outreach only |
| ZED / TPM metric mapping (MTBF, MTTR, availability) | S | Gives MSMEs pursuing ZED a reason to adopt. The ZED parameter list was not retrieved | Unverified | Evidence page |
| Pricing hypothesis: open core plus paid kit, or ~₹300–1,000 per machine per month | Decision | A hypothesis to test in pilots, not evidence | [SoftwareFinder](https://softwarefinder.com/facility-management-software/nanoprecise) | Business plan |

## Top 10 enhancements by value for effort

| Rank | Enhancement | Effort | Why it ranks here |
|---|---|---|---|
| 1 | ISO 20816-3 severity module | S | Useful on day one with no history; one function and a test |
| 2 | Monotone-RUL constraint plus coverage-under-drift experiment | S | Two paper results that build on PR #14 directly |
| 3 | Spare-parts lead time in the Monte Carlo cost step | S | Adds the real MSME constraint to an engine that already exists |
| 4 | Renewal-theory baseline in the ablation | S | Answers the "does not beat a tuned threshold" limitation honestly |
| 5 | FailureSensorIQ score for the chat LLM | S | External agent number from an eval script alone |
| 6 | Deep ensemble from the existing 5 seeds, then conformalized | S–M | The seeds already exist; it feeds a real distribution into Monte Carlo |
| 7 | Operator feedback labels plus drift-triggered retraining | S–M | Gives batch retraining a reason to fire and a label source |
| 8 | MetroPT-3 compressor domain | S–M | Real maintenance-log labels for an MSME-typical asset, under CC BY 4.0 |
| 9 | WhatsApp alerts plus alert hygiene | S–M | About ₹150 a month for 20 machines; the channel technicians actually use |
| 10 | TSFM few-shot curve (Chronos-2, TTM, MOMENT) | S–M | Publishable either way; tests the label-scarce regime that matters |

The ESP32 node with `Esp32VibrationAdapter` (M) is the highest-value item outside the top 10. It would turn ATLAS from mostly simulated into one real industrial domain. It is ranked lower only because it needs hardware.

## Conclusion

The one thing that most changes how strong the work looks is moving from "four of five domains simulated" to "real data with real labels". That does not need new modelling. MetroPT-3, XJTU-SY and Backblaze each come with failure ground truth, and one ESP32 node makes a domain ATLAS owns end to end. Most of the remaining paper limitations (uncalibrated confidence, single seeds, FD001 only, no safety override, not beating a tuned threshold) can be closed with S-sized work on top of code that already exists. The cheapest credibility gains are not code at all: syncing PR #14, retiring the legacy docs and their test counts, and closing the moot patent items.

The decision-layer work is where ATLAS can differentiate rather than catch up. On accuracy it is respectable but not leading. Lead-time-aware ordering, a crew-constrained weekly plan and work orders with verified fields are less crowded than RUL accuracy, and closer to what an MSME owner pays for. The launch blockers (name collision, domain, Privacy and Terms pages, HTTPS, the database role) are decisions only you can make. They should be settled before any public pilot, because a pilot under a colliding name, without a privacy page, would undo the trust the read-only, DPDP-minimal design is meant to build.

Caveats: this report was written from the research notes and was not re-verified against the live repo after PR #14. Effort estimates assume one researcher. Items marked unverified, vendor-sourced or inference should be checked before citing.
