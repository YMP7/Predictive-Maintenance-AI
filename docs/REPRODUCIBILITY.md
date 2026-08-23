# ATLAS Open-Source Benchmark & Reproducibility Guide
**Month 8 Deliverable | Standalone Evaluation Harness, Artifact Manifest & Tolerance Bounds**

---

## 1. Overview & Evaluation Scope

This document provides complete, step-by-step instructions for peer reviewers, thesis examiners, and external researchers to reproduce the empirical benchmarks, transfer studies, cognition ablations, and system profiles of the **ATLAS (Adaptive Telemetry Learning & Autonomous System)** framework.

### Evaluation Capabilities:
1. **Prediction Accuracy**: Attention-LSTM Remaining Useful Life (RUL) estimation on NASA C-MAPSS FD001 ($N=100$ test turbofans).
2. **Cross-Domain Transfer Study**: Maximum Mean Discrepancy (MMD), pairwise centroid cosine similarity, and Negative Transfer Index (NTI) across 4 heterogeneous hardware domains.
3. **Cognition Pipeline Ablations**: 4 canonical ablations (Cost reduction, Grounded Explainability, Decision Graph near-failure safety parity, and 3×3 cross-compute transfer).
4. **End-to-End Latency Benchmarks**: Isolated stage micro-benchmarks and full cognition pipeline latencies ($p_{50}, p_{95}, p_{99}$).
5. **System Resource Profile**: Resident Set Size (RSS) memory footprint, zero-leak audit, and multi-tier concurrency scaling.

---

## 2. Reproducibility Scope & Statistical Tolerance Definitions

> [!IMPORTANT]
> **What "Reproducibility" Means in ATLAS (Fixed-Checkpoint vs. Retraining Variance)**:
> In modern deep learning systems operating on CPU architectures, reproducibility falls into two distinct operational categories:
> 
> 1. **Fixed-Checkpoint Evaluation (Deterministic & Bit-Consistent)**:
>    - When evaluating the locked model checkpoints (`best_model.pt`, `laptop_world_model.pt`, `mobile_world_model.pt`, `server_world_model.pt`) using `scripts/evaluate_atlas.py`, all neural forward passes, attention pooling operations, and decision rules produce **identical results within float32 numerical precision ($\pm 0.001$)**.
> 
> 2. **Retraining from Scratch (Statistical Tolerance Bands)**:
>    - As empirically characterized across multi-seed training studies (Month 3 and Month 7), retraining the Attention-LSTM from random initialization across different seeds and CPU execution thread allocations exhibits minor non-deterministic floating-point accumulation.
>    - Expected empirical tolerance bands under re-training:
>      - **C-MAPSS FD001 RUL RMSE**: $15.21 \pm 0.30$ cycles (Validation Gate: $\le 16.0$ cycles)
>      - **C-MAPSS FD001 PHM Score**: $375.00 \pm 21.93$ (Validation Gate: $\le 400.0$)
>      - **Spearman Rank Correlation $r_s$ (Ablation 2)**: $-0.509 \pm 0.04$
>      - **Disagreement Cost Savings (Ablation 3)**: $10.46\% \pm 1.5\%$
> 
> 3. **Monte Carlo Simulation Seeding**:
>    - The Monte Carlo stochastic rollout engine uses fixed seeding (`seed=42`) for benchmark evaluation. When evaluated across varying random seeds on borderline early-life units, expected cost variance remains below $<3\%$.

---

## 3. Checkpoints & Model Weight Integrity Manifest

All trained model checkpoints and scaler artifacts are versioned in `data/models/`. Verify the SHA-256 integrity of the repository checkpoints using `python scripts/evaluate_atlas.py manifest`:

| Model / Checkpoint | File Path | Parameters | File Size | SHA-256 Checksum |
| :--- | :--- | :---: | :---: | :--- |
| **C-MAPSS World Model** | `data/models/best_model.pt` | 60,609 | 248.9 KB | `bff765692b8239aae8766a123f1856773efec9936af00b69ed571ad98085fd3d` |
| **Laptop World Model** | `data/models/laptop_world_model.pt` | 58,305 | 239.9 KB | `053bd408b75898eb818dd52dfe8562cee1a6c7cf1660ece098d47ee04c2896bf` |
| **Mobile World Model** | `data/models/mobile_world_model.pt` | 58,305 | 239.9 KB | `782a542545b689e9bbb9997cdcd9637ba9eeb8536e0eb99852a9f832f743e46c` |
| **Server World Model** | `data/models/server_world_model.pt` | 58,305 | 239.9 KB | `856ebde39dfe4ec6b01a92fe494985d9f78134e4e06e13e0c9dce134b1c2ed12` |
| **Machine DNA Scaler** | `data/models/machine_dna_scaler.json` | 6 features | 889 B | `edcfc8f5991504834118b400e4fc6612775dcba5b6f66cce23a335d343a26521` |

---

## 4. Quickstart Reproduction Recipes

### Quick Reproduction (< 10 seconds)
Run the entire test and evaluation suite with quick-pass benchmarking:
```bash
python scripts/evaluate_atlas.py all --quick
```

### Full Multi-Trial Verification
Run the complete multi-trial evaluation across all modules:
```bash
python scripts/evaluate_atlas.py all
```

### Modular Command Reference:
| Command | Evaluated Target | Output Artifact |
| :--- | :--- | :--- |
| `python scripts/evaluate_atlas.py manifest` | Checkpoint SHA-256 integrity | Terminal JSON |
| `python scripts/evaluate_atlas.py prediction` | Attention-LSTM RMSE & PHM | Terminal JSON |
| `python scripts/evaluate_atlas.py transfer` | MMD & NTI Transfer Study | `data/transfer_study_results.json` |
| `python scripts/evaluate_atlas.py ablations` | 4-Part Cognition Ablation Suite | `data/ablation_results.json` |
| `python scripts/evaluate_atlas.py benchmark --quick` | Latency distribution & throughput | `data/system_benchmark_results.json` |
| `python scripts/evaluate_atlas.py profile --quick` | Memory RSS & concurrency load | `data/system_resource_profile.json` |

---

## 5. Offline / Zero-Database In-Memory Mode

To ensure effortless reproducibility for peer reviewers without requiring a running PostgreSQL/TimescaleDB/pgvector service:
- `scripts/evaluate_atlas.py` incorporates an exact **`InMemoryAMKB`** vector engine.
- If PostgreSQL is unreachable, `InMemoryAMKB` automatically activates using float32 normalized dot-product cosine distance:
  $$\text{dist}(u, v) = 1.0 - \frac{u \cdot v}{\|u\|_2 \|v\|_2}$$
- Numerical equivalence against live pgvector `<=>` is formally tested and verified in `tests/test_evaluation_cli.py` within $< 10^{-5}$ tolerance.

---

## 6. Citation & Research Deliverables

When citing the ATLAS system, please reference the corresponding chapter deliverables:
- **Prediction & Digital Twin Architecture**: `docs/ATLAS_PROJECT_CONTEXT.md`
- **Cross-Domain Transfer Study**: `docs/TRANSFER_STUDY_RESULTS.md`
- **Cognition Pipeline Ablations**: `docs/ABLATION_STUDY_RESULTS.md`
- **System Latency & Throughput Benchmark**: `docs/ATLAS_BENCHMARK.md`
- **Resource Footprint & Concurrency Profile**: `docs/ATLAS_RESOURCE_PROFILE.md`
