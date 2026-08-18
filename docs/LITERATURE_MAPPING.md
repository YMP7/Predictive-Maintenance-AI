# ATLAS — Academic Literature Mapping & Citations Guide

This document formally maps the 36 foundational research papers to their direct implementation, theoretical justification, and architectural roles across the ATLAS platform.

---

## Literature Mapping by Subsystem & Architectural Pillar

```
                        [ ATLAS Platform Architecture ]
                                       │
   ┌───────────────────┬───────────────┴───────────────┬───────────────────┐
   ▼                   ▼                               ▼                   ▼
[ Pillar 1: RUL &   [ Pillar 2: Memory &            [ Pillar 3: Monte   [ Pillar 4: Domain
  Attention Core ]    Knowledge Graphs (AMKB) ]       Carlo Decisions ]   Adaptation & IoT ]
 (Papers 1–6)        (Papers 7–10)                   (Papers 11–14)      (Papers 15–36)
```

---

### Pillar 1: RUL Prognostics, Attention-LSTM & Asymmetric Loss
*Grounding for: `server/atlas/world_model.py`, `server/atlas/train_rul.py`, `ml/preprocessing.py`*

| # | Paper Title | Direct Role in ATLAS Architecture | Relevant Code / Section |
|---|---|---|---|
| 1 | **Remaining Useful Life Prediction Using Attention-LSTM Neural Network of Aircraft Engines** | Theoretical and empirical justification for replacing standard LSTM with Temporal Attention over hidden states to capture degradation dynamics across 30-cycle operational windows. | [`server/atlas/world_model.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/world_model.py) (`TemporalAttention` layer) |
| 2 | **A Deep Learning-Based Prognostic Approach for Predicting Turbofan Engine Degradation and Remaining Useful Life** | Justification for sliding window sequence extraction, piece-wise linear RUL degradation assumption (125-cycle cap), and feature normalization. | [`ml/preprocessing.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/ml/preprocessing.py) (`compute_train_rul`, `make_windows`) |
| 3 | **Asymmetric-Loss-Guided Hybrid CNN-BiLSTM-Attention Model for Industrial RUL Prediction with Interpretable Failure Heatmaps** | Justifies why PHM scoring function penalizes late predictions ($d > 0$) more severely than early predictions ($d < 0$), and motivates attention pooling as an interpretable temporal weight. | [`server/adapters/cmapss_adapter.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/adapters/cmapss_adapter.py) (`phm_score`) |
| 4 | **Interpretable Ensemble RUL Prediction Enables Dynamic Maintenance Scheduling for Aircraft Engines** | Connects prognostic RUL distribution and uncertainty bounds to downstream scheduling decisions, supporting the transition from RUL to action optimization. | [`server/atlas/rul_engine.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/rul_engine.py) |
| 5 | **Linear Methods for Predictive Maintenance: The Case of NASA C-MAPSS Datasets** | Establishes statistical baselines for C-MAPSS FD001 and motivates the necessity of non-linear state encoders for complex multi-sensor trajectories. | Thesis Chapter: Baseline Comparison |
| 6 | **An Interpretable Systematic Review of Machine Learning Models for Predictive Maintenance of Aircraft Engine** | Provides taxonomy and comparative survey of prognostics models on turbofan engines, structuring the thesis related-work section. | Thesis Chapter: Related Work |

---

### Pillar 2: Memory-Augmented Architectures, Knowledge Graphs & RAG
*Grounding for: `server/atlas/amkb.py`, `server/atlas/adaptive_context.py`, `server/atlas/machine_dna.py`*

| # | Paper Title | Direct Role in ATLAS Architecture | Relevant Code / Section |
|---|---|---|---|
| 7 | **Construction of Intelligent Decision Support Systems through Integration of RAG and Knowledge Graphs** | Inspires the AMKB experience-retrieval pipeline: embedding real-time state vectors into vector space to ground AI decisions in historical precedent. | [`server/atlas/amkb.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/amkb.py) (`retrieve_similar`) |
| 8 | **Knowledge Graphs as Tools for Explainable Machine Learning: A Survey** | Provides theoretical framework for using structured contextual entities (unit profiles, sensor baselines) alongside embeddings to explain predictions. | [`server/atlas/machine_dna.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/machine_dna.py) |
| 9 | **Memory-Augmented Graph Neural Networks: A Brain-Inspired Review** | Motivates persistent machine memory as an external cognitive store rather than relying exclusively on parametric neural network weights. | [`server/atlas/amkb.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/amkb.py) |
| 10 | **Relational Dynamic Memory Networks** | Justifies dynamic memory updating where experiences are continuously written with metadata outcomes and queried via angular (cosine) distance. | [`server/atlas/amkb.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/amkb.py) (`store_experience`) |

---

### Pillar 3: Monte Carlo Simulation & Cost-Weighted Decision Graph
*Grounding for: `server/atlas/simulation.py`, `server/atlas/decision.py`*

| # | Paper Title | Direct Role in ATLAS Architecture | Relevant Code / Section |
|---|---|---|---|
| 11 | **Monte Carlo Simulation for the Optimization of Maintenance Strategies in Degrading Systems** | Foundational theoretical basis for `SimulationEngine`: simulating synthetic RUL realizations over degradation uncertainty to calculate expected operational cost per action. | [`server/atlas/simulation.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/simulation.py) (`simulate_actions`) |
| 12 | **Dynamic Optimization of Condition-Based Maintenance Strategies Using Monte Carlo Simulations to Compare Adaptive Inspection Intervals, Threshold Adjustments, and Their Impact on System Performance** | Justifies incorporating action lead times (`ACTION_LEAD_TIME`) into Monte Carlo rollouts so that time-to-intervention directly drives the safety penalty. | [`server/atlas/simulation.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/simulation.py) (`ACTION_LEAD_TIME`) |
| 13 | **Monte Carlo Simulation for Evaluating and Optimizing the Efficiency of BR and QIR Maintenance Strategies** | Informs the cost matrix modeling (unplanned failure cost vs. planned maintenance vs. immediate replacement cost). | [`server/atlas/simulation.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/simulation.py) (`CostModel`) |
| 14 | **An Explainable Artificial Intelligence Model for Predictive Maintenance and Spare Parts Optimization** | Guides the Decision Graph's synthesis of economic cost, inventory impact, and risk scores into human-auditable action recommendations. | [`server/atlas/decision.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/decision.py) (`DecisionRecommendation`) |

---

### Pillar 4: Explainable AI (XAI) & Digital Twin Trust
*Grounding for: `server/atlas/explain.py`, `server/api.py`*

| # | Paper Title | Direct Role in ATLAS Architecture | Relevant Code / Section |
|---|---|---|---|
| 15 | **Explainable, Interpretable & Trustworthy AI for Intelligent Digital Twin: Case Study on Remaining Useful Life** | Primary conceptual pillar for ATLAS: combining Digital Twin operational modeling with auditable explainability (citations + feature attribution) to establish operator trust. | [`server/atlas/explain.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/explain.py) (`ExplanationReport`) |
| 16 | **Explainable Predictive Maintenance: A Survey of Current Methods, Challenges and Opportunities** | Defines the evaluation criteria for explainability (grounding, consistency, fidelity, and separation of ground-truth citations from circular model self-reference). | [`server/atlas/explain.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/explain.py) |
| 17 | **Explainable AI for Predictive Maintenance: A Review and Standardized Evaluation Framework** | Informs the confidence scoring formula: combining cosine similarity with true RUL trajectory variance: `confidence = similarity * (1 / (1 + variance))`. | [`server/atlas/explain.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/explain.py) (confidence formula) |
| 18 | **Research on Milling Machine Predictive Maintenance Based on Machine Learning and SHAP Analysis** | Benchmarks feature attribution methods, justifying occlusion sensitivity as a robust, non-gradient model-agnostic attribution method. | [`server/atlas/explain.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/explain.py) (`calculate_feature_attribution`) |
| 19 | **Explainable AI in Manufacturing: Predictive Maintenance and Quality Control** | Frames the practical operator requirements: explaining *why* an engine is failing by linking dominant sensors to physical subsystem functions (e.g. HPC outlet temp). | [`server/atlas/explain.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/explain.py) (`SENSOR_DESCRIPTIONS`) |

---

### Pillar 5: Cross-Domain Transfer Learning & Heterogeneous Machine Generalization
*Grounding for: `server/adapters/*`, Month 6 Adapters, Month 7–8 Transfer Study*

| # | Paper Title | Direct Role in ATLAS Architecture | Relevant Code / Section |
|---|---|---|---|
| 20 | **LAMA-Net: Unsupervised Domain Adaptation via Latent Alignment and Manifold Learning for RUL Prediction** | Grounding for the upcoming Month 7 Cross-Domain Transfer Study: aligning latent representations across different physical machine regimes. | Thesis Chapter: Cross-Domain Transfer |
| 21 | **Transfer Learning for Remaining Useful Life Prediction Based on Consensus Self-Organizing Models** | Informs Machine DNA transferability: evaluating how degradation representations learned on C-MAPSS generalize to laptop and cloud server metrics. | [`server/atlas/machine_dna.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/machine_dna.py) |
| 22 | **Interpretable Domain Adaptation Transformer: A Transfer Learning Method for Fault Diagnosis of Rotating Machinery** | Guides multi-domain feature mapping and domain-agnostic projection layers. | [`server/atlas/adaptive_context.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/adaptive_context.py) |
| 23 | **Joint Adaptive Transfer Learning Network for Cross-Domain Fault Diagnosis Based on Multi-Layer Feature Fusion** | Supports the multi-source fusion of thermal, compute, and power features across heterogeneous domains. | [`server/adapters/base_adapter.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/adapters/base_adapter.py) (`NormalizedReading`) |
| 24 | **Cross-Machine Fault Diagnosis with Semi-Supervised Discriminative Adversarial Domain Adaptation** | Justifies unsupervised / zero-shot evaluation on target machines where failure labels do not yet exist (`true_rul = None`). | [`server/adapters/laptop_adapter.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/adapters/laptop_adapter.py) |
| 25 | **A Multi-Source Information Transfer Learning Method with Subdomain Adaptation for Cross-Domain Fault Diagnosis** | Informs sub-signature mapping in Machine DNA (Thermal, Power, Failure profiles). | [`server/atlas/machine_dna.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/machine_dna.py) |
| 26 | **Cross-Domain Open Set Fault Diagnosis Based on Weighted Domain Adaptation with Double Classifiers** | Informs handling out-of-distribution operational states in the AMKB. | [`server/atlas/amkb.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/amkb.py) |
| 27 | **Overcoming Negative Transfer by Online Selection: Distant Domain Adaptation for Fault Diagnosis** | Crucial theoretical guard for ATLAS: ensures distant domains (e.g. laptop stress vs turbofan degradation) are explicitly partitioned by domain key to avoid negative transfer. | [`server/atlas/amkb.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/amkb.py) (`domain = %s` filter) |

---

### Pillar 6: IoT Telemetry, Edge Sensing, Industrial Benchmarks & Datasets
*Grounding for: `server/adapters/mobile_adapter.py`, `server/adapters/server_adapter.py`, Benchmarking*

| # | Paper Title | Direct Role in ATLAS Architecture | Relevant Code / Section |
|---|---|---|---|
| 28 | **Predictive Maintenance — Bridging Artificial Intelligence and IoT** | Justifies edge telemetry ingestion via HTTP/MQTT/Termux into the unified adapter layer. | [`server/adapters/mobile_adapter.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/adapters/mobile_adapter.py) |
| 29 | **Low-Cost IoT-Based Predictive Maintenance Using Vibration** | Argues the viability of low-cost commodity telemetry (laptop/mobile sensors) alongside high-end industrial systems. | [`server/adapters/laptop_adapter.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/adapters/laptop_adapter.py) |
| 30 | **A Survey on Predictive Maintenance for Industry 4.0** | Contextualizes ATLAS within the Industry 4.0 reference architecture (Digital Twin + Edge Sensing + Predictive Analytics). | Thesis Chapter: Introduction |
| 31 | **A Comprehensive Survey of Machine Learning Techniques for Predictive Maintenance** | Benchmark methodology reference for preprocessing, validation splits, and evaluation metrics. | Thesis Chapter: Methodology |
| 32 | **A Machine Learning Implementation to Predictive Maintenance and Monitoring of Industrial Compressors** | Comparative reference for industrial rotating equipment telemetry and degradation indicators. | Thesis Chapter: Domain Analysis |
| 33 | **A Benchmark Dataset for Predictive Maintenance** | Comparative benchmark dataset reference (synthetic manufacturing lines vs real turbofan telemetry). | Thesis Chapter: Experimental Setup |
| 34 | **The MetroPT Dataset for Predictive Maintenance** | Real-world multi-sensor transportation dataset reference, motivating cross-domain benchmark releases. | Thesis Chapter: Benchmark Discussion |
| 35 | **Predictive Maintenance Using Machine Learning: A Case Study in Manufacturing Management** | Case study grounding the economic justification for cost-weighted decision models over fixed maintenance intervals. | [`server/atlas/decision.py`](file:///c:/Users/yegir/Documents/MSME/AI-Powered%20Digital%20Twin%20&%20Predictive%20Maintainence/server/atlas/decision.py) |
| 36 | **CruiseBench: A Real-Flight-Aligned N-CMAPSS Benchmark for Engine RUL Prediction** | Contextualizes NASA C-MAPSS vs next-generation N-CMAPSS flight-profile benchmarks for future extension. | Thesis Chapter: Future Work |

---

## How to Cite in Thesis / Paper Sections

1. **Chapter 2 (Literature Review & Background)**:
   - Cite **Surveys & Taxonomies**: Papers 6, 16, 17, 30, 31.
   - Cite **Benchmark & Datasets**: Papers 2, 5, 33, 34, 36.
2. **Chapter 3 (System Architecture & Attention Prognostics Engine)**:
   - Cite **Prognostics & Attention**: Papers 1, 2, 3, 4, 15.
   - Cite **Memory & Dynamic Memory Networks**: Papers 7, 8, 9, 10.
3. **Chapter 4 (Explainable AI & Digital Twin Memory Engine)**:
   - Cite **XAI & Feature Attribution**: Papers 3, 8, 15, 16, 17, 18, 19.
4. **Chapter 5 (Simulation & Decision Graph)**:
   - Cite **Monte Carlo Optimization & Cost Models**: Papers 11, 12, 13, 14, 35.
5. **Chapter 6 (Heterogeneous Multi-Domain Validation & Transfer Study)**:
   - Cite **Domain Adaptation & Transfer Learning**: Papers 20, 21, 22, 23, 24, 25, 26, 27.
   - Cite **IoT & Low-Cost Sensing**: Papers 28, 29, 32.
