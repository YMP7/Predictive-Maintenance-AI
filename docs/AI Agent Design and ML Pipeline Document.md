# AI Agent Design and ML Pipeline Document
## Implemented Baseline and Target ML Architecture

**Validated against code:** June 21, 2026

## 1. Design Boundary

The repository currently implements a deterministic baseline, not a trained ML pipeline. Keeping that distinction explicit is important:

- The baseline provides explainable threshold and pattern rules.
- The RUL estimator uses linear trend extrapolation over a synthetic degradation score.
- The simulator supplies already-computed vibration RMS values.
- No FFT, trained classifier, LSTM, Bhashini, TensorRT, or feedback learner runs in production code.

The baseline is useful for integration, demonstration, data collection, and establishing testable interfaces. The target ML architecture described later in this document is a roadmap.

## 2. Implemented Architecture

```text
MultiMachineSimulator
    |
    v
AIAgent
    |- FaultDetector
    |- RULEstimator
    |- AlertGenerator
    `- latest result cache
    |
    v
DataService
    |- in-memory telemetry/status/alert caches
    |- SQLite persistence
    `- AlertHandler
    |
    v
FastAPI + React dashboard
```

### 2.1 Fault Detector

Inputs:

- Vibration RMS
- Temperature
- Current draw
- Machine ID for threshold selection

Outputs:

- Fault type
- Human-readable threshold issues
- Normal, Warning, or Critical health state in the orchestrator

The current detector recognizes `Misalignment`, `Overheating`, `Bearing Wear`, and `Electrical Fault` through ordered rules.

### 2.2 RUL Estimator

The current degradation score is:

```text
0.5 * (vibration_rms / 5.0)
+ 0.3 * ((temperature - 45) / 30)
+ 0.2 * ((current - 2.5) / 2.0)
```

Scores are clipped to `[0, 1]`. After 10 samples, a first-order polynomial estimates the trend toward a critical score of 0.8. History is bounded at 1,000 scores per machine.

This is a demonstration heuristic. It does not represent a Weibull model, survival model, LSTM, or field-calibrated lifetime estimate.

### 2.3 Communication Module

Implemented communication features:

- English, Hindi, Telugu, Tamil, and Marathi template dictionaries
- Alert cooldown
- Severity-based channel routing
- Dashboard and log delivery
- Optional Twilio SMS/voice
- Optional SMTP email

Translation is local and template-based. Bhashini is not integrated.

### 2.4 Digital Twin State

The implemented virtual state contains:

- Vibration axes and RMS
- Temperature
- Current
- Health status and fault type
- Detected issues
- RUL and confidence
- Maintenance recommendation
- Recent telemetry trends and alerts

RPM, load, thermal maps, kinematic simulation, and 500 ms synchronization are not implemented. The default simulation interval is one second and is configurable.

## 3. Implemented Data Pipeline

```text
Reading generation
    -> finite-number validation
    -> machine-specific threshold checks
    -> rule-based fault classification
    -> degradation score update
    -> linear RUL estimate
    -> alert generation
    -> memory and SQLite persistence
    -> dashboard polling
```

The system does not currently denoise, resample, normalize, calculate FFT features, or impute missing values. Invalid required readings are rejected.

## 4. Data Retention and Restart Behavior

Persistent SQLite data:

- Raw simulated telemetry and status
- Generated alerts

In-memory bounded data:

- 1,000 telemetry readings per machine
- 500 recent alerts
- 1,000 degradation scores per machine
- 1,000 delivered alert records

After restart, telemetry and alerts are reloaded. RUL degradation history is not reconstructed, so RUL confidence collection begins again.

## 5. Target ML Pipeline

The following pipeline is proposed, not implemented:

```text
Physical sensors
    -> timestamp alignment and quality checks
    -> denoising and windowing
    -> time-domain and frequency-domain features
    -> labeled/versioned dataset
    -> baseline and candidate model training
    -> offline evaluation
    -> versioned model artifact
    -> edge inference adapter
    -> drift and outcome monitoring
    -> controlled retraining
```

### 5.1 Candidate Features

Time-domain candidates:

- RMS
- Peak and peak-to-peak
- Crest factor
- Kurtosis and skewness
- Temperature rise rate
- Current mean, variance, and load-normalized values

Frequency-domain candidates:

- Dominant frequencies
- Band energy
- 1x/2x/3x rotational components
- Bearing characteristic frequencies
- Spectral entropy

These require raw, correctly sampled vibration waveforms. The current simulator emits one aggregate reading and cannot support meaningful FFT analysis.

### 5.2 Candidate Models

| Model | Candidate purpose | Gate before adoption |
|---|---|---|
| Rule baseline | Explainable fallback | Already implemented |
| Isolation Forest | Unlabeled anomaly scoring | Compare false alarms against baseline |
| Random Forest | Fault classification | Labeled field dataset and cross-validation |
| Gradient boosting | Tabular fault classification | Compare accuracy, size, and latency |
| Survival/regression model | RUL prediction | Known failure/censoring data |
| LSTM/temporal model | Sequence-based RUL | Sufficient sequence data and edge benchmark |

No model should replace the rule baseline until it improves validated outcomes and stays within latency and memory limits.

## 6. Training and Evaluation Requirements

Required artifacts before claiming model accuracy:

1. Versioned dataset with machine, sensor, operating regime, and label metadata
2. Train/validation/test split that prevents leakage between machines or time periods
3. Reproducible feature pipeline
4. Confusion matrix and per-class precision/recall
5. False-positive rate by operating regime
6. RUL MAE/MAPE with clear treatment of zero and censored lifetimes
7. Inference latency and memory benchmark on the target edge device
8. Model version, checksum, rollback path, and rule fallback

The repository does not currently contain the datasets needed to establish >90% accuracy or <20% RUL MAPE.

## 7. Edge Deployment Roadmap

The current Docker image runs Python/FastAPI on a standard Linux container. Jetson, TensorRT, ONNX, and ROS2 deployment have not been implemented or benchmarked.

Recommended sequence:

1. Define a sensor adapter interface independent of ROS2.
2. Capture representative field data using that interface.
3. Benchmark the Python rule baseline on the chosen edge device.
4. Export only validated trained models to ONNX.
5. Compare ONNX Runtime and TensorRT for latency, memory, and numerical parity.
6. Add ROS2 only if the physical integration requires it.

## 8. Multilingual Roadmap

The local template dictionaries are the operational fallback. A future Bhashini integration should include:

- Request timeout and retry policy
- Cached translations
- Provider failure fallback to local templates
- Approved maintenance terminology per language
- Audit trail of source and translated text
- Privacy review before sending operational data externally

## 9. Feedback Learning Roadmap

A human-in-the-loop system requires stored feedback such as:

- Alert confirmed or rejected
- Actual fault and component
- Maintenance action and timestamp
- Downtime and replacement outcome
- Operator comments

The current database has no feedback tables or retraining workflow. These must be designed before adaptive thresholds or online learning can be claimed.

## 10. Security and Reliability

Implemented controls:

- Optional API key for control endpoints
- Bounded in-memory structures
- SQLite persistence
- Per-channel alert error isolation
- Docker health check and restart policy

Required for a real production installation:

- TLS termination
- Identity-based authorization
- Secret manager
- Signed/versioned model artifacts
- Database backup and retention
- Network isolation
- Audit logging for control actions and model decisions

## 11. Validation Status

The current automated suite validates the deterministic prototype, API behavior, latency, memory growth, and simulation integration. It does not validate trained-model accuracy, physical sensor behavior, cloud services, Bhashini, or long-duration edge reliability.
