# ATLAS Landscape Report: What Exists, What Matters, What to Build Next

*Generated: 2026-11-12 | Platforms: GitHub, Hugging Face, arXiv, PHM Society, vendor and regulatory sources | About 45 sources | Confidence: Medium (most 2026 numbers come from preprints)*

---

## Executive summary

1. **ATLAS has no direct open-source equal.** No project found combines heterogeneous adapters, RUL, retrieval-grounded explanation, cost simulation, ISA-18.2 alarms, work orders and a 3D twin. The closest projects are [murat-suer/pdm-predictive-maintenance](https://github.com/murat-suer/pdm-predictive-maintenance) (one simulated factory, one domain) and [IBM/AssetOpsBench](https://github.com/IBM/AssetOpsBench) (an agent benchmark, not a product).
2. **ATLAS's accuracy is respectable, not leading.** On FD001 ATLAS reports RMSE 15.42 (15.22 ± 0.30 over five seeds). A plain single-layer LSTM in a 2026 study reaches 14.93 with one seed ([arXiv 2604.27234](https://arxiv.org/abs/2604.27234)). Self-reported results go as low as 7.63 ([IIETA](https://iieta.org/download/file/fid/193414)) under protocols that can't be checked. Accuracy is not where ATLAS wins. Its edge is the system, the honest evidence and the explanations.
3. **The field moved in 2025–26 in three directions that ATLAS can join cheaply:**
   - (a) **Time-series foundation models.** Chronos-2, TimesFM 2.5, TTM and MOMENT are all free on Hugging Face, and frozen Chronos-2 embeddings now beat trained LSTMs on RUL ([arXiv 2606.11990](https://arxiv.org/abs/2606.11990)).
   - (b) **Grounded LLM agents with verification**, exposed over MCP. Examples are IBM's Condition Insight Agent ([arXiv 2603.08171](https://arxiv.org/abs/2603.08171)) and [Predictive Maintenance MCP](https://iris.polito.it/retrieve/949583cf-69a9-47c3-8a8b-e361f7eeff1a/2026DiMaggioPredictive.pdf).
   - (c) **Distribution-free RUL intervals** (conformal prediction).
4. **The biggest weakness reviewers will hit: four of the five domains are simulated.** Open real-failure datasets on Hugging Face and Kaggle can fix this for at least two domains: Backblaze hard drives for the server domain, and NASA/CALCE batteries for the phone and laptop domains.
5. **Two non-technical risks:**
   - **Name collision.** [Grashjs/cmms](https://github.com/Grashjs/cmms) is "Atlas CMMS" (863★, AGPL), a maintenance work-order product in exactly your space.
   - **Regulation.** The EU AI Act timeline shifted. Predictive maintenance on machinery is now largely carved out, so it is not a reason to delay.

---

## 1. Where ATLAS stands today (from the repo)

| Pillar | ATLAS today | Evidence |
|---|---|---|
| RUL accuracy | FD001 RMSE 15.42, PHM 394.7; five seeds 15.22 ± 0.30 | `docs/TITLE_JUSTIFICATION.md` |
| Domains | Turbofan (real benchmark); laptop, phone, server, pump (**simulated**) | same |
| Explainability | Occlusion attribution with a deletion-test faithfulness check (35.4 vs 16.8 cycles, 90% of units) | `scripts/attribution_faithfulness.py` |
| Grounding | AMKB case-retrieval memory, agent chat with evidence | `server/atlas/` |
| Decision | Monte Carlo cost simulation, 47% cheaper than a RUL-threshold rule (ablation) | `docs/ABLATION_STUDY_RESULTS.md` |
| Operations | ISA-18.2 alarms, work orders, RBAC, audit, TimescaleDB, MQTT, Modbus | README |
| Not done | Real-machine validation, FD002–FD004 results, HTTPS deployment | FUTURE-WORK cells |

---

## 2. GitHub: what exists, related or not, and why

### 2.1 Directly related (use, compare against, or cite)

| Repo | ★ | Related? | How it helps ATLAS |
|---|---|---|---|
| [IBM/AssetOpsBench](https://github.com/IBM/AssetOpsBench) | 2,416 | **Yes, strongly** | An agent benchmark for asset operations: 9 asset classes, 141+ scenarios, MCP-native, accepted at KDD 2026, with a [HF dataset](https://huggingface.co/datasets/ibm-research/AssetOpsBench). **Run ATLAS's agent chat on it.** That gives an external, citable score for the "Machine Cognition" claim, which today is only measured internally. |
| [murat-suer/pdm-predictive-maintenance](https://github.com/murat-suer/pdm-predictive-maintenance) | small | **Yes, closest competitor** | Same stack shape: FastAPI, TimescaleDB, React, ISA-18.2, cost-optimal decisions, EU AI Act audit. It has three things ATLAS lacks: **split-conformal RUL intervals**, **purged k-fold with embargo**, and **physics-grounded degradation** (Weibull, ISO 281 bearing life, Arrhenius oil oxidation). ATLAS has things it lacks: heterogeneous domains, retrieval grounding, a 3D twin and a real benchmark. Put it in your related-work table, and borrow conformal intervals and the ISO 281 wear model for the pump simulator. |
| [umbertogriffo/Predictive-Maintenance-using-LSTM](https://github.com/umbertogriffo/Predictive-Maintenance-using-LSTM) | 740 | Yes, as a baseline | The canonical LSTM-on-C-MAPSS tutorial. Useful only as a reproducible baseline row. |
| [jiaxiang-cheng/PyTorch-Transformer-for-RUL-Prediction](https://github.com/jiaxiang-cheng/PyTorch-Transformer-for-RUL-Prediction) | 314 | Yes, as a baseline | A Transformer baseline on C-MAPSS. Add it next to your attention LSTM in the ablation to answer "why not a Transformer?" |
| [mohyunho/N-CMAPSS_DL](https://www.github.com/mohyunho/N-CMAPSS_DL) | – | Yes | A ready pipeline for **N-CMAPSS** (full-flight, realistic). It is the natural "harder benchmark" after FD001. |
| [biswajitsahoo1111/rul_codes_open](https://github.com/biswajitsahoo1111/rul_codes_open) | 222 | Yes | Clean reference implementations of RUL methods, for sanity-checking preprocessing. |
| [kokikwbt/predictive-maintenance](https://github.com/kokikwbt/predictive-maintenance), [phoenixdyf/Opensource_Dataset_Compilation_for_PHM](https://github.com/phoenixdyf/Opensource_Dataset_Compilation_for_PHM) | 176 / 301 | Yes | Dataset indexes. Use them to find real run-to-failure data for the simulated domains (see Section 4). |
| [liguge/Awesome-large-language-model-for-Prognostics-and-health-management](https://github.com/liguge/Awesome-large-language-model-for-Prognostics-and-health-management) | 140 | Yes | A curated LLM-for-PHM paper list. Mine it for the related-work section of the paper. |
| [aangelopoulos/conformal-time-series](https://github.com/aangelopoulos/conformal-time-series), [hamrel-cxu/EnbPI](https://github.com/hamrel-cxu/EnbPI) | 150 / 134 | Yes | Reference code for conformal intervals on time series (see 5.3). |

### 2.2 Adjacent (worth integrating or interoperating with)

| Repo | ★ | Related? | How or why |
|---|---|---|---|
| [thingsboard/thingsboard](https://github.com/thingsboard/thingsboard) + [thingsboard-gateway](https://github.com/thingsboard/thingsboard-gateway) | 22.7k / 2.2k | Partly | The dominant open IoT platform. Its gateway already speaks Modbus, OPC-UA, CAN and BACnet. **Don't rebuild protocol drivers.** Write one ATLAS adapter that ingests from ThingsBoard or its gateway and you inherit hundreds of devices. |
| [eclipse-ditto/ditto](https://github.com/eclipse-ditto/ditto), [Eclipse BaSyx](https://eclipse.dev/basyx/digitization/) | 950 / – | Partly | Standard digital-twin frameworks. BaSyx is the reference implementation of the **Asset Administration Shell (AAS)**, the Industry 4.0 twin standard. Exporting each ATLAS asset as an AAS submodel (health, RUL, recommended action) would let industrial reviewers take "Digital Twin" seriously. |
| [Grashjs/cmms](https://github.com/Grashjs/cmms) ("Atlas CMMS") | 863 | **Name collision** | An open-source CMMS named *Atlas*. Two consequences: (1) a search or trademark conflict for your brand; (2) an integration opportunity, because ATLAS could push work orders into a real CMMS. Decide on the name before any public launch. |
| [dgiot/dgiot](https://github.com/dgiot/dgiot) | 4.9k | Partly | An industrial IoT platform with 300+ protocols. Same lesson as ThingsBoard. |
| [timescale/timescaledb](https://github.com/timescale/timescaledb) | 23.8k | Already used | Use continuous aggregates and compression if you haven't. The murat-suer project does. |
| [yzhao062/pyod](https://github.com/yzhao062/pyod), [unit8co/darts](https://github.com/unit8co/darts), [sktime/sktime](https://github.com/sktime/sktime), [stumpy-dev/stumpy](https://github.com/stumpy-dev/stumpy) | 4k–10k | Partly | Mature anomaly-detection and forecasting libraries. Use them for an **anomaly baseline** before RUL kicks in. RUL needs run-to-failure labels, and anomaly detection doesn't, which matters for real MSME machines with no failure history. |

### 2.3 Searched, judged not related, and why

| What | Why not |
|---|---|
| "Digital twin" repos with the most stars (WeClone 18k, Mirrai, immortal-skill) | These are *persona* clones of people trained on chat logs. Same phrase, unrelated meaning. |
| Battery RUL repos ([XiuzeZhou/RUL](https://github.com/XiuzeZhou/RUL), 521★) | Not related as code, but **the datasets are** (CALCE, NASA battery). Battery fade is the real failure mode of the phone and laptop domains (see Section 4). |
| CWRU bearing fault-diagnosis repos | Classification of fault *type* from high-rate vibration, not RUL. Relevant only if you add a vibration sensor to the pump domain. |
| Small "LLM agent PdM" repos (Sentra, Solar-intel, Agentic_Predictive_Maintenance_LLM; 0–1★ each) | Show the idea is popular, but none publishes a benchmark score. Nothing to reuse. |
| Generic SCADA/HMI portfolio repos (ISA-18.2 tank demos) | Too small. Your alarm module is already richer. |

---

## 3. Hugging Face: models, datasets, Spaces

### 3.1 Models: time-series foundation models (TSFMs) — **highly related**

| Model | Size | Downloads | Licence | How it fits ATLAS |
|---|---|---|---|---|
| [amazon/chronos-2](https://hf.co/amazon/chronos-2) | 120M | 195M | Apache-2.0 | **Best candidate.** Multivariate and supports covariates. A June 2026 paper ([arXiv 2606.11990](https://arxiv.org/abs/2606.11990), EUSIPCO 2026) freezes Chronos-2 and trains only a 2-layer MLP head for RUL. On their Device A it cut MAE from 93 (LSTM) to 44, and from 88 (TCN) to 44. A PHM paper ([PHME](https://papers.phmsociety.org/index.php/phme/article/download/4906/2940)) reports state-of-the-art results on full C-MAPSS with the same zero-shot-embedding idea. |
| [ibm-granite/granite-timeseries-ttm-r2](https://hf.co/ibm-granite/granite-timeseries-ttm-r2) | **0.8M** | 12.6M | Apache-2.0 | Tiny and CPU-friendly, which suits laptop, phone and edge deployment in an MSME. No published RUL result was found, so **testing it would be novel**. |
| [google/timesfm-2.5-200m-pytorch](https://hf.co/google/timesfm-2.5-200m-pytorch) | 231M | 5.5M | Apache-2.0 | Strong univariate forecaster. Less suited to multivariate RUL. |
| [AutonLab/MOMENT-1-large](https://hf.co/AutonLab/MOMENT-1-large) | 346M | 3.3M | MIT | Supports forecasting, classification, anomaly detection and imputation. Reported to collapse on multi-condition subsets FD002/FD004 ([unreviewed source](https://v3-gahmed.pages.dev/projects/dissertation-survival)), and to lose to a TCN autoencoder on anomaly detection ([summary](https://chatpaper.com/paper/336345)). Use it as a comparison, not as the backbone. |
| [Salesforce/moirai-2.0-R-small](https://hf.co/Salesforce/moirai-2.0-R-small) | 11M | 10M | **CC-BY-NC** | Non-commercial licence. Avoid it in a product you may sell. Fine in a research table. |

**Insight:** ATLAS's "World Model" is a trained attention LSTM with a 32-dim state. Adding a frozen TSFM encoder lets you test the question "does foundation-model pretraining remove the need for per-domain training?" Your own transfer study shows that borrowing turbofan memory inflates phone error 8.3x, so this is a well-posed experiment. A positive or negative result is publishable either way.

### 3.2 Models: maintenance LLMs — related

- [predictive-maintenance/qwen3-4b-failuresensoriq-lora](https://hf.co/predictive-maintenance/qwen3-4b-failuresensoriq-lora) is a LoRA adapter on Qwen3-4B for **FailureSensorIQ** (IBM, NeurIPS 2025): 8,296 multiple-choice questions about which sensors reveal which failure modes ([arXiv 2506.03278](https://arxiv.org/abs/2506.03278)). It is small enough to run locally, which would let the ATLAS agent chat work offline. That matters for MSMEs with poor connectivity or data-privacy concerns.

### 3.3 Datasets — related

| Dataset | Use for ATLAS |
|---|---|
| [ibm-research/AssetOpsBench](https://hf.co/datasets/ibm-research/AssetOpsBench) | External evaluation of the agent (see 2.1). |
| [NovaBenya/N-CMAPSS_DS02-006.h5](https://hf.co/datasets/NovaBenya/N-CMAPSS_DS02-006.h5) | Mirror of the realistic N-CMAPSS DS02 subset. Check the licence against NASA's original. |
| [IlyasFardaouixx/backblaze-st4000dm000-predictive-maintenance](https://hf.co/datasets/IlyasFardaouixx/backblaze-st4000dm000-predictive-maintenance) | **Real hard-drive failures**, which can make the *server* domain real. The original source is Backblaze Drive Stats (public). Licence on the mirror is unknown, so prefer the original. |
| [rasinmuhammed/predictive-maintenance-remaining-useful-life](https://hf.co/datasets/rasinmuhammed/predictive-maintenance-remaining-useful-life) | Synthetic, so it doesn't fix the realism gap. Only useful as a sanity check. |
| AI4I 2020 mirrors | Classification with no time dimension, so it does not fit an RUL pipeline. **Not related enough.** |

### 3.4 Spaces

Many C-MAPSS dashboards exist ([cmapss-rul-shap](https://hf.co/spaces/dcdooling/cmapss-rul-shap), [CMAPSS_Predictive_Maintenance_Dashboard](https://hf.co/spaces/Dakoro/CMAPSS_Predictive_Maintenance_Dashboard), …). All of them are single-model demos. **None is a multi-domain platform.** This confirms that ATLAS's differentiation is the system. A lightweight public HF Space of ATLAS (read-only replay, C-MAPSS only) would give it discoverability that none of these has, because people search HF for "cmapss".

---

## 4. The simulated-data problem, and real datasets that fix it

The paper and the evidence page are honest that four domains are simulated. Real data exists for most of them:

| ATLAS domain | Real public data | Failure signal | Effort |
|---|---|---|---|
| Server | **Backblaze Drive Stats** (SMART, 330M drive-days, failures labelled) | Disk failure | Low: CSV, daily, failure label given |
| Laptop / Phone | **NASA PCoE battery** and **CALCE** battery cycling (indexed in [XiuzeZhou/NASA](https://github.com/XiuzeZhou/NASA), [XiuzeZhou/CALCE](https://github.com/XiuzeZhou/CALCE)) | Capacity fade to 70–80% | Medium: cycle-level, not device-level |
| Pump | **PRONOSTIA / FEMTO** and **XJTU-SY** bearing run-to-failure; [Pump sensor data (Kaggle)](https://hf.co/Pankaj001/TimeSeriesForecasting-PumpSensor) | Bearing degradation | Medium |
| Turbofan | **N-CMAPSS** in addition to C-MAPSS FD001 | Realistic flights | Medium |

Moving even *one* simulated domain (server, via Backblaze) to real data turns "five domains, one real" into "five domains, two real". That is the cheapest large gain in credibility.

---

## 5. Research directions from the literature

### 5.1 Benchmark protocol (high relevance)

- Reported FD001 RMSE in 2026 ranges from **7.63** ([IIETA](https://iieta.org/download/file/fid/193414)) to **17.52** (leakage-controlled, [arXiv 2604.27234](https://arxiv.org/abs/2604.27234)). Most of that spread comes from protocol differences (RUL cap, last-window test, scaler leakage), not from better models.
- The leakage-controlled study (cap 130, 30-cycle window, scaler fit on training data only, split by engine) gets LSTM **14.93 / NASA 411** and 1D CNN 16.97. ATLAS's 15.42 / 394.7 sits in that same band. Its PHM score is better than that LSTM's, and its RMSE is slightly worse.
- **Action:** report results on **FD001–FD004** (the adapter already supports all four) and on **N-CMAPSS DS02**, and state the protocol explicitly in a table (cap, window, scaler fit, seeds). FD002 and FD004 have multiple operating conditions. They test the "adaptive context" claim far better than FD001 does, which has one condition.

### 5.2 Foundation-model embeddings (high relevance)

- See 3.1. One experiment is enough: Chronos-2 or TTM frozen encoder plus an MLP head, against your attention LSTM, on FD001 and FD002, five seeds.
- **Caveat:** the EUSIPCO paper used proprietary data with one split and no seeds, so it can't be reproduced. ATLAS would be the first to run this cleanly across domains.

### 5.3 Uncertainty: conformal RUL intervals (high relevance)

- ATLAS shows an "RUL band", and the Monte Carlo decision step needs a calibrated distribution. **Split-conformal** wraps any point model with guaranteed coverage ([Javanmardi & Hüllermeier, IJPHM 2023](https://arxiv.org/pdf/2212.14612)).
- A 2026 IJPHM paper reports **88–92% empirical coverage at 90% nominal** on turbofan data. It argues that the coverage should be *asymmetric*, because over-estimating RUL (failing before you predicted) costs far more ([IJPHM 2026](https://www.papers.phmsociety.org/index.php/ijphm/article/download/4724/2824)). That fits ATLAS's cost-simulation story directly.
- **Action:** add split-conformal intervals and report their coverage. It is roughly 50 lines of code on top of your existing predictions.

### 5.4 Grounded LLM agents with verification (high relevance)

- IBM's **Condition Insight Agent** ([arXiv 2603.08171](https://arxiv.org/abs/2603.08171), ACL 2026 Industry) is deployed on about 1,500 assets across 14 sites. It builds a deterministic *evidence packet* (meter behaviour, work-order patterns, FMEA match), lets a constrained LLM write insights, then checks them with a **rule-based verifier**. In their table, the constrained prompt raised condition-category agreement from 0.70 to 0.91.
- ATLAS already has the evidence half (AMKB retrieval, attribution). **What's missing is the verifier**: a deterministic check that the chat answer's claims (RUL, top sensors, recommended action) match the engine outputs. That is cheap and a strong paper point.
- **MCP:** the [Predictive Maintenance MCP](https://iris.polito.it/retrieve/949583cf-69a9-47c3-8a8b-e361f7eeff1a/2026DiMaggioPredictive.pdf) server (Applied Sciences 2026) and AssetOpsBench's MCP support show where the field is heading. Exposing ATLAS endpoints (get_rul, explain, list_alarms, create_work_order) as an **MCP server** lets any LLM client drive ATLAS, and lets you run AssetOpsBench against it.

### 5.5 Explainability evaluation (medium relevance; ATLAS is ahead)

- Most XAI-for-PHM papers compare explanation methods with proxy metrics such as fidelity, stability and consistency ([Kundu & Hoque, PHM 2023](https://papers.phmsociety.org/index.php/phmconf/article/download/3472/phmc_23_3472); [Solís-Martín et al.](https://arxiv.org/pdf/2303.05517v1.pdf); an 11-metric study on C-MAPSS from [CESI](https://lineact.cesi.fr/publications/improving-predictive-maintenance-evaluating-the-impact-of-preprocessing-andmodel-complexity-on-the-effectiveness-of-explainable-artificial-intelligence-methods/)). Counterfactual RUL explanations are the newer direction ("what change would extend RUL?", Andringa et al., Information Fusion 2025).
- ATLAS's deletion test with a random-sensor control already goes further than most. **Next step:** add a counterfactual "what would extend RUL by N cycles" view. It maps naturally onto the decision graph ("reduce load → +X cycles").

### 5.6 Physics-informed degradation (medium relevance)

- PINN-for-RUL repos are small and immature ([pimlphm/PI-TCN](https://github.com/pimlphm/Physics-informed-machine-learning-based-on-TCN), 32★). The practical lesson comes from the murat-suer project: use **standard wear laws** (ISO 281 bearing life, Weibull, Arrhenius) to make the *simulators* credible. Do that before any PINN modelling.

---

## 6. Market, standards and regulation

| Topic | Finding | Relevance to ATLAS |
|---|---|---|
| **AWS Lookout for Equipment** | Closed to new customers Oct 2024, **discontinued 7 Oct 2026**. AWS points users to IoT SiteWise anomaly detection ([AWS blog](https://aws.amazon.com/blogs/machine-learning/preserve-access-and-explore-alternatives-for-amazon-lookout-for-equipment)). | Hyperscalers retreated from stand-alone PdM ML. This opens room for open, self-hosted tools. Good line for the paper's motivation. |
| **Indian MSMEs** | Only about 7% are exploring AI tools. Main barriers are resistance (36%) and cost (18%). Retrofit sensors at about ₹1–2 lakh per 20–30 machines (vendor estimate) ([ecorpit](https://ecorpit.com/ai-predictive-maintenance-factory-floor-india-roi-2026/), [cionlabs](https://cionlabs.com/brownfield-iot-retrofitting-legacy-indian-machinery-with-smart-wireless-intelligence/)). A systematic review names **low-cost sensors** and **federated learning** as key enablers in data-scarce settings ([IIETA review](https://www.iieta.org/journals/jesa/paper/10.18280/jesa.590611)). | Your repo folder says MSME. Lean into it: CPU-only (TTM is 0.8M parameters), a cheap ESP32 or Modbus retrofit adapter, an anomaly-first mode for machines with no failure history, offline LLM. Market numbers are vendor-sourced, so cite them cautiously. |
| **Asset Administration Shell** | The Industry 4.0 twin standard. Eclipse BaSyx is the reference implementation ([Eclipse BaSyx](https://projects.eclipse.org/node/12344); [Sensors 2023 survey](https://mdpi.com/1424-8220/23/11/5229)). | Exporting assets as AAS gives standards credibility. ISO 13374 / OSA-CBM wasn't found in the search; if your docs cite it, it's still worth mapping your 10 pipeline stages onto its 6 layers. |
| **EU AI Act** | The Digital Omnibus deal (7 May 2026) moved product-embedded high-risk obligations to Aug 2028. Routine PdM and anomaly detection on machinery is **largely carved out** ([Hannes Snellman](https://www.hannessnellman.com/news-and-views/blog/updates-to-the-ai-act-and-product-liability-directive-key-changes-for-industrial-companies/), [techUK](https://www.techuk.org/resource/eu-ai-omnibus-deal-reached-more-clarity-on-ai-act-obligations.html)). Cyber Resilience Act incident reporting starts Sept 2026. | Low regulatory risk. Your audit trail and human-in-the-loop operator decision are still good practice and a selling point. Secondary legal sources; check the Official Journal text before citing. |

---

## 7. Recommendations, ranked by value ÷ effort

| # | Do this | Why | Effort |
|---|---|---|---|
| 1 | **Resolve the "ATLAS" name collision** with Atlas CMMS before launch | Same market; risk to discoverability and trademark | Decision |
| 2 | **Split-conformal RUL intervals** with reported coverage | Calibrated band feeds Monte Carlo; reviewers expect it in 2026 | ~1 day |
| 3 | **FD002–FD004 results** plus a protocol table | Tests "adaptive" on multi-condition data; makes results comparable | 1–2 days |
| 4 | **Server domain on real Backblaze data** | Turns the biggest weakness into a strength | 2–4 days |
| 5 | **Deterministic answer verifier** for agent chat | Mirrors IBM's deployed design; cheap, strong paper point | 1–2 days |
| 6 | **Frozen Chronos-2 / TTM encoder experiment** vs attention LSTM | Very current research question; result is publishable either way | 3–5 days |
| 7 | **ATLAS as an MCP server** plus an **AssetOpsBench run** | External, citable agent score; joins the MCP ecosystem | ~1 week |
| 8 | **Anomaly-first mode** (PyOD/stumpy) for machines with no failure history | The realistic MSME case: no run-to-failure labels | 2–3 days |
| 9 | Pump simulator using **ISO 281 / Weibull** wear laws | Makes simulated numbers defensible | 2 days |
| 10 | **ThingsBoard gateway adapter** instead of more protocol drivers | Hundreds of protocols for one adapter | 2–3 days |
| 11 | **AAS export** of each asset (BaSyx) | Standards credibility for industrial reviewers | ~1 week |
| 12 | Public **HF Space** (read-only C-MAPSS replay) | Discoverability; no comparable multi-domain Space exists | 1–2 days |

**Don't do** (judged low value here):
- Fine-tune Llama for time series (the Ankur87 models). TSFMs make that obsolete.
- Chase single-number FD001 SOTA. It depends on protocol and won't convince reviewers.
- Adopt Moirai in the product. Its CC-BY-NC licence rules out commercial use.
- Add CWRU fault classification. It doesn't fit the RUL story.

---

## 8. Gaps and caveats

- Most 2026 numbers are **preprints or self-reported**. Only the conformal (IJPHM 2023) and FailureSensorIQ (NeurIPS 2025) results are peer-reviewed. The IBM agent paper reports no sample sizes and no inter-judge agreement.
- No paper was found that tests **TTM on RUL**, or that compares Chronos, TTM and MOMENT head-to-head on C-MAPSS. ATLAS would be filling a gap, not reproducing a known result.
- No rigorous, India-specific MSME evidence was found. The market and cost numbers are from vendors.
- Kaggle and Papers-with-Code weren't searched directly. Papers with Code leaderboards have been unreliable since its 2025 wind-down; check before citing.
- The 7.63 FD001 claim (IIETA) was not verified and should not be quoted as SOTA.

## Methodology

- **GitHub:** 22 queries through the GitHub API (topics: predictive-maintenance, remaining-useful-life, digital-twin, TSFM, anomaly detection, PHM, CMMS, IoT/Modbus/OPC-UA, conformal, XAI, Backblaze, CWRU, ISA-18.2, physics-informed). Read the READMEs of AssetOpsBench and pdm-predictive-maintenance in full.
- **Hugging Face:** 4 hub searches plus model and dataset card reads for 7 repositories.
- **Web:** 11 searches.
- **Full text:** 3 papers read in full (arXiv 2606.11990, 2604.27234, 2603.08171).
