# System Architecture Document (SAD)
## AI-Powered Digital Twin & Predictive Maintenance System

> [!IMPORTANT]
> **Document Status (June 21, 2026):**
> This document distinguishes between the **Current Implemented Prototype** and the **Recommended Professional Production Architecture**.
> - **Current Implemented Prototype**: Uses Python, FastAPI, React, SQLite, and Docker, with telemetry simulated for four machines.
> - **Recommended Professional Production Architecture**: A high-performance, robust edge-cloud design using NVIDIA Jetson edge gateways, industrial-grade sensors (MEMS and Pt100), and a local-to-cloud sync pipeline (FastAPI/PostgreSQL/MQTT) to ensure complete and accurate data capture.

---

### 1. Overview of Architectures

For a professional-grade product that guarantees high-resolution data capture and real-time edge intelligence, the system employs a **Hybrid Edge-Cloud Architecture**.

```mermaid
graph TD
    subgraph Perception Layer (Industrial Sensors)
        Vib[ADXL355 Tri-axial Vibration Sensor]
        Temp[Pt100 RTD Temperature Probe]
        Curr[SCT-013 Split-core Current Clamps]
    end

    subgraph Edge Layer (NVIDIA Jetson Xavier NX)
        ROS2[ROS2 Communication Bus]
        FFT[FFT & Feature Extraction Engine]
        AIAgent[AI Inference Engine - ONNX/Linear]
        FastAPI[FastAPI Server & Data Sync]
        SQLite[(Local SQLite/PostgreSQL Edge DB)]
    end

    subgraph User Interface & Presentation
        React[React Digital Twin Dashboard]
    end

    subgraph Cloud Layer (Enterprise Target)
        PostgreSQL[(Central PostgreSQL DB)]
        Redis[(Redis Cache)]
        Translate[Bhashini Translation Service]
        Notify[Twilio SMS & SMTP Gateway]
    end

    Perception Layer -->|SPI / ADC / 4-20mA| Edge Layer
    ROS2 --> FFT
    FFT --> AIAgent
    AIAgent --> FastAPI
    FastAPI <--> SQLite
    FastAPI -->|MQTT / HTTPS Sync| CloudLayer
    React <-->|REST API / Port 8000| FastAPI
    Cloud Layer --> Notify
```

---

### 2. Architectural Comparison

| Layer / Aspect | Current Implemented Prototype | Recommended Professional Production Setup | Target Enterprise Expansion |
| :--- | :--- | :--- | :--- |
| **Edge Gateway Hardware** | Standard Local PC (Simulated) | **NVIDIA Jetson Xavier NX (8GB/16GB)** | NVIDIA Jetson AGX Orin Edge Servers |
| **Vibration Sensing** | Simulated RMS values | **ADXL355 Tri-axial High-Resolution MEMS** | Industrial Piezoelectric Accelerometers |
| **Temperature Sensing** | Simulated temp values | **Pt100 RTD Sensor with Transmitter** | Non-contact Infrared Pyrometer Sensors |
| **Current Sensing** | Simulated current values | **Multi-phase SCT Split-Core CT Clamps** | Hall Effect Current Transducers (isolated) |
| **Communication Protocol**| Local Python imports / HTTP | **MQTT, Local HTTP (FastAPI) & I2C/SPI** | ROS2 Node Mesh Network, WebSockets |
| **Storage Engine** | SQLite (`digital_twin.db`) | **SQLite (Local) + PostgreSQL (Cloud Sync)** | Distributed CockroachDB, Redis Caching |
| **Analytics Engine** | Rule thresholds + Linear RUL | **Real-time FFT + ONNX ML Inference + RUL** | Deep LSTM networks + Drift detection |
| **Notification Services** | simulated email/SMS logs | **SMTP Email + Twilio SMS** | Bhashini Translation API + SMS/Voice |
| **Estimated Hardware Cost** | ₹0 (Runs on existing PC) | **~₹45,000 - ₹55,000 per machine setup** | ₹1,80,000+ per multi-machine floor |

---

### 3. Professional Hardware Procurement List

To build the highest-quality, most robust monitoring unit capable of processing raw waveforms and running local deep learning inference, the following components are recommended:

| Component | Part Name / Specification | Qty | Est. Cost (INR) | Purpose / Details |
| :--- | :--- | :---: | :---: | :--- |
| **Edge Gateway** | NVIDIA Jetson Xavier NX Module & Dev Kit | 1 | ₹36,000 | 6-core ARM CPU, 384-core Volta GPU, 48 Tensor Cores. Runs local FFT, AI model inference, and local server. |
| **Storage** | 128GB M.2 NVMe SSD (PCIe Gen3) | 1 | ₹3,500 | High-speed, durable storage for telemetry database and system logs. |
| **Vibration Sensor** | ADXL355 High-Resolution Tri-axial Accelerometer | 1 | ₹4,200 | Ultra-low noise, digital output (SPI/I2C) tri-axial accelerometer for high-frequency vibration capture. |
| **Temperature Sensor**| Pt100 RTD Sensor with MAX31865 RTD-to-Digital | 1 | ₹1,500 | Platinum RTD sensor for highly accurate surface temperature readings. |
| **Current Sensor** | SCT-013-000 AC Current Transformer (100A) | 3 | ₹1,950 | Three clamps to monitor three-phase power draw. |
| **ADC Module** | ADS1115 16-bit 4-Channel Analog-to-Digital | 1 | ₹350 | Converts analog current sensor outputs into I2C digital signals. |
| **Enclosure** | IP67 Industrial Aluminum Enclosure | 1 | ₹2,500 | Rugged, dust-tight, and water-tight housing to withstand shop floor environments. |
| **Cabling & Connectors**| Shielded Instrumentation Cable & M12 connectors | 1 | ₹1,800 | Prevents electromagnetic interference (EMI) from motors. |
| **TOTAL COST** | | | **~₹51,800 (~$620)** | **A professional, high-fidelity monitoring station.** |

---

### 4. Component Details & Data Flow

#### 4.1 Perception Layer
- **ADXL355 Tri-axial Accelerometer**: Mounted directly to the motor's bearing housing using a magnetic base or stud. Measures real-time micro-vibrations in X, Y, and Z axes. Connected to the Jetson Xavier via the SPI interface for high-throughput data transfer.
- **Pt100 RTD Sensor**: Embedded in the motor casing or thermal wells. Connected to the MAX31865 RTD-to-Digital converter, providing temperature data with a resolution of 0.03°C over I2C.
- **SCT-013 Clamps**: Placed around the main incoming three-phase power lines of the machine. The analog outputs are digitized by the ADS1115 ADC and fed into the edge gateway.

#### 4.2 Edge Layer
- **ROS2 & FFT Engine**: Ingests raw high-frequency vibration waveforms from the ADXL355. Computes real-time Fast Fourier Transforms (FFT) to extract spectral components (Root Mean Square, kurtosis, and dominant peak frequencies).
- **AI Agent Inference Engine**: Evaluates the processed features against both rule-based thresholds and pre-trained ONNX models for instant classification of anomalies (such as Bearing Wear, Overheating, or Shaft Misalignment). Estimates Remaining Useful Life (RUL) through regression.
- **integrated_server.py & SQLite**: Persists local readings and status cache. Serves the React SPA interface.

#### 4.3 Cloud Sync & Presentation Layer
- **FastAPI Sync**: Edge server securely pushes consolidated telemetry data to a central cloud PostgreSQL database via encrypted MQTT or HTTPS.
- **React Dashboard**: Modern web client queries the API to visualize real-time digital twins of the machines, metrics history, and alert lists.
- **Alert Handler (`alert_handler.py`)**: Directs notifications (email and SMS) to maintenance managers when faults are classified.
