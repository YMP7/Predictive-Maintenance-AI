# Project Management and Execution Document

> [!IMPORTANT]
> **Implementation Status (June 21, 2026):**
> This document details the **12-month pilot project management roadmap** for a full factory rollout alongside the **current verified prototype progress**.
> - **Current Prototype Status**: The baseline digital twin prototype is **fully implemented and verified**. It features an integrated FastAPI/React server, SQLite database, localized alarm rules, linear trend RUL prediction, and a Docker container with 29 passing automated tests.
> - **Enterprise Rollout Status**: ROS2 sensor ingestion, trained LSTM deep learning models, Bhashini voice translation, and physical factory installation represent future roadmap tasks for the pilot deployment phase.

---

### 1. Current Implementation Progress (As of June 21, 2026)

The project has completed its prototyping milestones, translating the initial system architecture into a working Dockerized service:

| Phase | Planned Timeline | Current Implementation State | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1** (Requirements & BOM) | Months 1-2 | Completed SRS, SAD, and detailed hardware Bill of Materials (BOM) centered on NVIDIA Jetson edge gateways. | **COMPLETED** |
| **Phase 2** (Edge OS & Ingestion) | Months 3-4 | Built the core data ingestion loop (`data_service.py`), multi-machine simulator (`sensor_simulator.py`), and local SQLite database persistence. | **PROTOTYPE COMPLETE**<br>*(ROS2/Physical edge pending)* |
| **Phase 3** (AI Model & Backend) | Months 5-7 | Implemented rule-based anomaly classification and linear-regression trend RUL in `ai_agent.py`. FastAPI server (`backend_api.py`) created. | **PROTOTYPE COMPLETE**<br>*(Trained LSTM/NoSQL pending)* |
| **Phase 4** (Dashboard & Alerts) | Months 8-9 | Created React SPA served by FastAPI on unified port 8000 (`integrated_server.py`). Template localization for 5 languages. | **PROTOTYPE COMPLETE**<br>*(Bhashini/SMS gateway pending)* |
| **Phase 5** (Pilot & Validation) | Months 10-12 | Docker Compose setup completed. Created a 29-test automated validation suite checking pipeline integrity, API, and performance. | **PROTOTYPE VERIFIED**<br>*(Factory trial pending)* |

---

### 2. Work Breakdown Structure (WBS) (Roadmap for Pilot Rollout)
The WBS details the complete 12-month path from prototype completion to a fully productionized factory environment:

| Phase | Task | Duration | Deliverables |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Requirement Finalization & Component Procurement | Month 1-2 | SRS, SAD, BOM (Bill of Materials). |
| **Phase 2** | Hardware Integration & Edge OS Setup | Month 3-4 | Sensor Kit Prototype, ROS2 Integration. |
| **Phase 3** | AI Model Development & Cloud Backend | Month 5-7 | Trained ML Models, Firebase Integration. |
| **Phase 4** | Digital Twin Dashboard & Localization | Month 8-9 | Web Dashboard, Bhashini Integration. |
| **Phase 5** | Pilot Testing & Field Trials | Month 10-12 | Field Test Report, Final MVP. |

---

### 3. Risk Register
| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Hardware Failure** | High | Use industrial-grade (IP65) enclosures and redundant sensors. |
| **Connectivity Issues** | Medium | Implement local storage (SQLite edge caching) and LTE failover. |
| **Model Accuracy** | High | Start with threshold-based alerts (implemented) and transition to ML as data grows. |
| **User Adoption** | Medium | Provide voice alerts in local languages (Bhashini) and simplified visual UI (React). |

---

### 4. Test Plan

The testing strategy encompasses multiple levels to ensure the robustness and reliability of the system:
- **Unit Testing**: Isolated testing of individual software modules, such as sensor simulators, rule logic in `ai_agent.py`, and data service queries. (Verified with 29 automated tests).
- **Integration Testing**: Verifying data loop from simulated sensors to SQLite storage and API responses. (Verified with 29 automated tests).
- **Accuracy Testing [Target Roadmap]**: Validating machine learning model predictions against known run-to-failure datasets.
- **User Acceptance Testing (UAT) [Target Roadmap]**: Conducting on-site walkthroughs with shop floor operators to verify dashboard usability.

---

### 5. Deployment Plan (Roadmap for Field Trials)
1. **Site Survey**: Assessment of the factory floor to map machinery and electrical outlets, selecting mounting points.
2. **Installation**: Physical mounting of the IP67-rated sensor enclosure and the NVIDIA Jetson edge gateway to the machinery.
3. **Calibration**: Established 48-hour baseline collection window to adjust machines' warning/critical thresholds in `config/machines.json`.
4. **Activation**: Starting the integrated system daemon and enabling cellular/WiFi communication bridges.
5. **Training**: A short hands-on demo to teach operators how to respond to alert notifications.

---

### 6. Pilot Project Budget Summary (Estimated)
The total estimated cost for a multi-machine pilot rollout is **₹10,20,000**.

| Category | Cost (₹) | Details |
| :--- | :--- | :--- |
| **Hardware Costs** | 2,50,000 | Procurement of 10 edge gateway kits (NVIDIA Jetson Xavier NX, sensors, enclosures, ADCs). |
| **Software & AI Development** | 3,20,000 | Integration of Bhashini translation, cloud-hosted Firebase DB, and LSTM training. |
| **Prototyping & Testing** | 2,40,000 | Custom PCB fabrication, lab calibration equipment, and third-party penetration testing. |
| **Contingency & Operations** | 2,10,000 | Travel for site surveys, on-site installation, training sessions, and cellular data plans. |
| **Total** | **10,20,000** | |
