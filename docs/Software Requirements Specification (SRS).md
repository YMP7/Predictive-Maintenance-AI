# Software Requirements Specification (SRS)
## AI-Powered Digital Twin & Predictive Maintenance System

> [!IMPORTANT]
> **Implementation Status (June 21, 2026):**
> - **Current Implemented Specification**: The prototype implements rule-based fault detection, linear trend RUL estimation, a React dashboard, local SQLite persistence, and a Docker container with a 29-test automated suite verifying all operations.
> - **Target Specification (Roadmap)**: Advanced features including physical high-resolution sensors, trained deep LSTM models, Bhashini translation API, ROS2 communication nodes, and central cloud database synchronization.

---

### 1. Introduction

#### 1.1 Purpose
This document specifies the software requirements for the "AI-Powered Digital Twin & Predictive Maintenance System." The system is designed to provide a premium, robust edge-cloud solution for industrial machinery monitoring and predictive health analytics, enabling high-resolution data collection, edge-based fault diagnostics, and rapid alert propagation.

#### 1.2 Scope
The system encompasses several key functionalities to achieve its objectives:
- **High-Fidelity IoT Data Ingestion**: Gathering multi-axis vibration, temperature, and current parameters.
- **Robust Edge Processing**: Pre-processing raw waveforms, performing FFT analysis, and conducting real-time validation on all inputs.
- **Predictive Health Analytics**: Classifying faults (Bearing Wear, Misalignment, Overheating, etc.) and calculating Remaining Useful Life (RUL).
- **Digital Twin Visualization**: A real-time web dashboard depicting machinery health and trend histories.
- **Localized Alert Dispatch**: Multi-channel (email/SMS) warning propagation based on alert severity.
- **Automated Verification**: End-to-end testing coverage to validate every data ingest and analytical task.

#### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
| :--- | :--- |
| **RUL** | Remaining Useful Life: The expected lifespan of an asset before it is likely to fail or require maintenance. |
| **FFT** | Fast Fourier Transform: An algorithm that computes the discrete Fourier transform of a sequence, converting time-series signals to frequency domain. |
| **Edge Gateway** | On-site high-performance edge processing hardware (e.g. NVIDIA Jetson Xavier NX). |
| **Bhashini** | National Language Translation Mission (India) API for regional language translations. |

---

### 2. Overall Description

#### 2.1 Product Perspective
The system is conceived as a professional-grade Industry 4.0 monitoring unit. It mounts directly to industrial machinery, connects via shielded instrumentation cables, processes high-frequency signals locally on an edge gateway, and integrates with secure cloud databases for fleet management.

#### 2.2 Product Functions
- **Real-Time Data Capture**: Continuous tracking of vibration, current, and temperature.
- **Input Validation**: Verifying that every data point received is physically possible, finite, and complete.
- **Fault Diagnostics**: Automated classification of mechanical issues.
- **RUL Prognostics**: Estimating remaining days to failure.
- **Unified Interface**: Real-time rendering of health statuses, alerts, and trend charts.
- **Multi-lingual Notification**: Text and voice notifications localized for maintenance engineers.

#### 2.3 User Classes and Characteristics

| User Class | Characteristics | Key Needs |
| :--- | :--- | :--- |
| **Factory Operators** | Production floor staff. | High-visibility warning lights, sirens, and simple localized text/voice alerts. |
| **Maintenance Engineers** | Technical specialists. | Detailed telemetry plots, spectral FFT trends, RUL estimations, and diagnostic recommendations. |
| **Operations Managers** | Fleet decision-makers. | Machine uptime reports, maintenance histories, and prediction performance validation. |

#### 2.4 Operating Environment
Deployed on high-interference industrial shop floors. Sensor casings must be IP67 rated. The edge gateway runs Linux (Ubuntu/JetPack) with a containerized service stack. Cloud synchronization operates over secure WiFi/cellular bridges.

---

### 3. Functional Requirements

#### 3.1 Data Acquisition & Processing
- **FR-1**: The system shall collect data from tri-axis vibration, temperature, and current sensors at a minimum frequency of 10Hz to ensure comprehensive monitoring.
- **FR-2**: The edge gateway shall filter high-frequency noise from raw waveforms and perform FFT processing for spectral vibration analysis.
- **FR-3**: Telemetry data shall be synchronized with the cloud database every 5 seconds under normal operation, and immediately upon anomaly detection.
- **FR-12 (Data Integrity Validation)**: The system shall validate all incoming telemetry readings in real-time. Any non-finite, missing, or out-of-bounds parameter must trigger an immediate sensor-fault alert, preventing corrupted data from propagating to the AI analytics model.

#### 3.2 AI & Predictive Analytics
- **FR-4**: The system shall employ machine learning models (e.g., Random Forest or LSTMs) to predict machine Remaining Useful Life (RUL).
- **FR-5**: The system shall classify faults into Bearing Wear, Misalignment, Overheating, and Electrical Fault categories.
- **FR-6**: The system shall support automated model retraining workflows using local operator feedback.
- **FR-13 (Inference Verification & Traceability)**: Every analytical task (anomaly classification, RUL prediction, and alert generation) must run verification checks to match configured machine-specific thresholds, appending a traceable metadata trail (confidence level, parameters, and time) to the alert output.

#### 3.3 Digital Twin & Dashboard
- **FR-7**: The dashboard shall render a real-time digital twin visualization showing machine status cards.
- **FR-8**: The user interface shall support localization in at least 5 regional languages (English, Hindi, Telugu, Tamil, Marathi).
- **FR-9**: The dashboard shall display historical telemetry trends and searchable logs.

#### 3.4 Alerts & Notifications
- **FR-10**: The system shall trigger physical sirens/beacon lights upon critical machine status.
- **FR-11**: The system shall distribute SMS and voice alerts via Twilio/Bhashini in the engineer's configured language.

---

### 4. Non-Functional Requirements

- **NFR-1 (Reliability & Uptime)**: The system shall maintain local edge monitoring uptime of 99.9%.
- **NFR-2 (High-Fidelity Performance)**: Processing latency for local anomaly checks and RUL calculations must remain under 100 milliseconds per reading.
- **NFR-3 (Usability)**: Critical alerts must be readable in under 2 seconds.
- **NFR-4 (Robustness)**: Sensor housings and connections must possess an IP67 rating for high-dust, high-temperature, and chemical-splash resistance.
- **NFR-5 (Task Verification & Automated Test Coverage)**: The software stack must maintain a comprehensive test suite (unit, integration, pipeline, performance, and API contracts) to validate every data loop, threshold trigger, and notification routing task before release.

---

### 5. Requirement Traceability Matrix

The following table maps SRS requirements to the current implemented code and verification status:

| Requirement ID | Status | Implementation Details | Verification Test |
| :--- | :---: | :--- | :--- |
| **FR-1** (10Hz sensors) | **Partial** | Simulated vibration, temperature, and current data generated at configurable intervals (1Hz). | `test_suite.py` (sim verification) |
| **FR-2** (Noise filter & FFT) | **Planned** | Raw wave-processing is planned for industrial ADXL355 integration. | N/A |
| **FR-3** (5s cloud sync) | **Planned** | SQLite database used locally. No cloud sync implemented. | N/A |
| **FR-4** (ML RUL model) | **Partial** | RUL calculated via linear trend extrapolation over degradation history. | `test_suite.py` (RUL regression test) |
| **FR-5** (Fault classification) | **Implemented** | Rule-based classification utilizing machine-specific configuration thresholds. | `test_suite.py` (pattern classification tests) |
| **FR-6** (Model retraining) | **Planned** | Retraining pipelines will be built when labeled field data is gathered. | N/A |
| **FR-7** (Twin dashboard) | **Implemented** | React SPA frontend displaying real-time machinery statuses and charts. | Manual UI testing |
| **FR-8** (Localization) | **Partial** | Template dictionaries for `en, hi, te, ta, mr` are defined locally. | `test_suite.py` (localization key tests) |
| **FR-9** (Historical trends) | **Implemented** | REST API endpoints fetch trend metrics (min, mean, max) from SQLite. | `test_api.py` (telemetry/trend API tests) |
| **FR-10** (Siren / beacon) | **Planned** | Relies on future integration with physical relays on Jetson. | N/A |
| **FR-11** (SMS/Voice alerts) | **Partial** | Twilio SMS/voice and SMTP email channels are implemented (defaulting to logs). | `test_suite.py` (notification handler tests) |
| **FR-12** (Data Validation) | **Implemented** | Check in `ai_agent.py` throws `ValueError` for non-finite or non-numeric inputs. | `test_suite.py` (`test_invalid_inputs_raised`) |
| **FR-13** (Inference Verification)| **Implemented** | `AIAgent` returns a dictionary including confidence, timestamps, and parameters. | `test_suite.py` (threshold & alert tests) |
| **NFR-1** (99.9% uptime) | **Partial** | Docker Compose health check and restart policy verified locally. | Local health endpoint checks |
| **NFR-2** (Latency < 100ms) | **Implemented** | Average processing latency is verified at <10 ms per reading. | `test_performance.py` (latency threshold checks) |
| **NFR-3** (Usability) | **Partial** | Frontend UI uses polling for rapid alert reflection. | Manual browser testing |
| **NFR-4** (IP67 robustness) | **Planned** | Physical aluminum enclosure and M12 cabling to be procured. | N/A |
| **NFR-5** (Automated Testing) | **Implemented** | 29 passing tests covering unit, integration, performance, and API levels. | `pytest` command execution |
