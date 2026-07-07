# AI Agent Deployment and Operations Guide
## Production Deployment and Operational Management

> [!IMPORTANT]
> **Implementation Status (June 21, 2026):**
> This guide outlines both the **current verified prototype deployment** and the **recommended professional production architecture**.
> - **Current Implemented Setup**: Runs on robust edge hardware using Python/FastAPI, SQLite, and a Docker/Docker Compose environment. The system serves both the React dashboard and API on port `8000` via `integrated_server.py`.
> - **Target Enterprise Roadmap**: Mentions of PostgreSQL, Redis, Prometheus/Grafana metrics, TensorFlow, and custom rollback scripts are design targets for future high-scale multi-machine environments. They are marked with `[Target Roadmap]` throughout this document.

---

### 1. Executive Summary
This document provides comprehensive guidance for deploying the AI Agent to production environments and managing its ongoing operations. It covers hardware requirements, deployment procedures, monitoring, maintenance, and troubleshooting.

### 2. System Requirements

#### 2.1 Hardware Requirements
The AI Agent is designed for robust edge intelligence and requires capable hardware to support local feature extraction, FFT analysis, and real-time inference.

**Minimum Configuration (1 Machine Monitoring):**
- **Processor**: Intel Core i5 (4 cores, 2.5+ GHz) or equivalent x86 processor
- **RAM**: 8GB
- **Storage**: 64GB SSD (NVMe recommended)
- **Network**: Ethernet or stable WiFi
- **OS**: Linux (Ubuntu 20.04 LTS or later)

**Recommended Production Configuration (5-10 Machines):**
- **Processor**: NVIDIA Jetson Xavier NX or Intel Core i7 (6+ cores)
- **RAM**: 16GB
- **Storage**: 128GB NVMe SSD
- **Network**: Gigabit Ethernet
- **OS**: Linux (Ubuntu 20.04 LTS or JetPack 5.x)

**Enterprise Configuration (50+ Machines):**
- **Processor**: NVIDIA Jetson AGX Orin or Intel Xeon (8+ cores)
- **RAM**: 32GB+
- **Storage**: 256GB+ NVMe SSD
- **Network**: Redundant Gigabit Ethernet
- **OS**: Linux (Ubuntu 22.04 LTS or JetPack 6.x)

*Note on Low-End Hardware:* Basic single-board computers (such as Raspberry Pi 4/5) and microcontrollers are not recommended for production deployments due to limited computational bandwidth for high-frequency raw sensor processing and FFT computation.

#### 2.2 Software Dependencies
```
Python 3.8+
├── numpy >= 1.19.0
├── pandas >= 1.1.0
├── scikit-learn >= 0.23.0
├── fastapi >= 0.63.0 (for REST API)
├── uvicorn >= 0.13.0 (for API server)
├── requests >= 2.25.0
├── pyyaml >= 5.3.0
├── python-dotenv >= 0.15.0
├── pytest >= 6.2.0 (for testing)
└── tensorflow >= 2.4.0 [Target Roadmap - for future LSTM models]
```

#### 2.3 Network Requirements
- **Bandwidth**: Minimum 1 Mbps for sensor data upload
- **Latency**: < 100ms for real-time alerts
- **Reliability**: 99.5% uptime
- **Firewall**: Allow port 8000 (Dashboard and API are unified on port 8000 via `integrated_server.py`. In Vite-based development, port 3000 is used for the frontend dev server).

### 3. Pre-Deployment Checklist

#### 3.1 Infrastructure Setup
- [x] Provision edge gateway (Intel PC or NVIDIA Jetson)
- [x] Install Linux OS (Ubuntu 20.04 LTS or JetPack)
- [x] Configure network connectivity
- [x] Set up SSH access
- [x] Configure firewall rules (allow port 8000)
- [ ] Set up NTP for time synchronization
- [ ] Configure backup strategy (SQLite/PostgreSQL backups)
- [ ] Set up monitoring infrastructure [Target Roadmap]

#### 3.2 Software Preparation
- [x] Install Python 3.8+
- [x] Create virtual environment
- [x] Install all dependencies (`pip install -r requirements.txt`)
- [ ] Download pre-trained deep learning models [Target Roadmap]
- [x] Prepare configuration files (`.env` and `config/machines.json`)
- [x] Set up logging infrastructure (logs directed to `logs/agent.log`)
- [x] Configure SQLite database (automatically initialized in `data/digital_twin.db`)
- [ ] Prepare SSL certificates [Target Roadmap]

#### 3.3 Data Preparation
- [ ] Collect baseline sensor data (48 hours)
- [x] Calibrate sensor thresholds (configured in `config/machines.json`)
- [x] Prepare machine configuration
- [x] Document machine specifications
- [x] Set up data collection pipeline (via `sensor_simulator.py` or physical sensors)
- [x] Verify data quality
- [x] Test alert delivery mechanisms (email/SMS handlers verified via `test_suite.py`)
- [ ] Prepare operator documentation

### 4. Installation and Setup

#### 4.1 Step-by-Step Installation

**Option A: Standard Python Virtual Environment Deployment (Verified Prototype)**
```bash
# 1. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Python and dependencies
sudo apt-get install -y python3 python3-pip python3-venv

# 3. Create project directory
mkdir -p /opt/ai-digital-twin
cd /opt/ai-digital-twin

# 4. Clone repository or copy source files
# git clone https://github.com/your-org/ai-digital-twin.git .

# 5. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 6. Install Python dependencies
pip install -r requirements.txt

# 7. Configure environment
cp .env.example .env
# Edit .env to set simulation, logging, and alert channels

# 8. Run automated test suite to verify
python -m pytest test_suite.py test_integration.py test_ai_pipeline.py test_performance.py test_api.py -q -p no:cacheprovider

# 9. Start integrated server (hosts both API and Frontend on port 8000)
python integrated_server.py
```

**Option B: Docker Compose Deployment (Verified Prototype)**
```bash
# 1. Install Docker and Docker Compose
sudo apt-get install -y docker.io docker-compose

# 2. Navigate to project directory
cd /opt/ai-digital-twin

# 3. Build and launch containers in background
docker-compose up --build -d

# 4. Verify running containers and health check
docker-compose ps
```

*Note on Target Roadmap Scripts:* Enterprise deployment steps like `./scripts/download_models.sh` or `python manage.py migrate` (for Django/SQL databases) are future roadmap items.

#### 4.2 Configuration Files
Create `.env` file with necessary configuration:

```env
# Machine Configuration
# (Actual machine mappings are defined in config/machines.json)
SIMULATION_ENABLED=true
SIMULATION_INTERVAL=1

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
LOG_FILE=./logs/agent.log

# Database Configuration (SQLite)
# [Target Roadmap] For PostgreSQL configurations:
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=ai_digital_twin
# DB_USER=admin
# DB_PASSWORD=secure_password

# Alert Configuration
ALERT_COOLDOWN=300
ALERT_LANGUAGES=en,hi,te,ta,mr

# Notification API Integrations (Optional)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+1234567890
TWILIO_TO_NUMBER=+1987654321
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com
ALERT_EMAIL_TO=recipient@example.com

# Model Configuration [Target Roadmap]
# RUL_MODEL=weibull
# ANOMALY_THRESHOLD=-0.5
```

#### 4.3 Systemd Service Setup
Create `/etc/systemd/system/ai-digital-twin.service`:

```ini
[Unit]
Description=AI Digital Twin Predictive Maintenance Agent
After=network.target

[Service]
Type=simple
User=ai-agent
WorkingDirectory=/opt/ai-digital-twin
Environment="PATH=/opt/ai-digital-twin/venv/bin"
ExecStart=/opt/ai-digital-twin/venv/bin/python integrated_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-digital-twin
sudo systemctl start ai-digital-twin
```

---

### 5. Deployment Procedures `[Target Roadmap]`

#### 5.1 Development to Staging Deployment
```bash
# 1. Run full test suite
python -m pytest test_suite.py -v

# 2. Build Docker image
docker build -t ai-digital-twin:latest .

# 3. Deploy to staging
./scripts/deploy_staging.sh # Target Script

# 4. Run smoke tests
pytest tests/smoke/ -v # Target Script

# 5. Verify in staging environment
curl http://staging.example.com/api/health
```

#### 5.2 Staging to Production Deployment
```bash
# 1. Create backup of SQLite DB
cp data/digital_twin.db data/digital_twin.db.bak

# 2. Deploy new version
./scripts/deploy_production.sh # Target Script

# 3. Verify deployment
curl http://localhost:8000/health
```

#### 5.3 Blue-Green Deployment
For zero-downtime deployments in large enterprise architectures (future roadmap):
- Deploy to "green" environment and route traffic once health checks pass.

---

### 6. Monitoring and Observability

#### 6.1 Health Checks
FastAPI exposes a `/health` check endpoint implemented in `backend_api.py`.
```json
{
  "status": "healthy",
  "timestamp": "2026-06-21T08:00:00Z"
}
```
*Note:* Component-specific checks (e.g. `check_sensor_pipeline()`) are roadmap integrations.

#### 6.2 Metrics Collection
Key metrics to monitor locally on the edge device:

| Metric | Target | Alert Threshold | Source |
| :--- | :--- | :--- | :--- |
| **API Response Time** | < 100ms | > 500ms | System logs / browser dev tools |
| **CPU Usage** | < 50% | > 80% | `top` / `htop` command |
| **Memory Usage** | < 60% | > 85% | `free -m` command |
| **Disk Usage** | < 70% | > 90% | `df -h` command |
| **Alert Generation Latency** | < 1 second | > 5 seconds | System logs |
| **Model Uptime** | > 99.5% | < 99% | Systemd service logs |

#### 6.3 Logging Configuration
FastAPI logging is configured to rotate or write directly to `./logs/agent.log`. Ensure the directory permissions allow writes:
```bash
mkdir -p logs
chmod 755 logs
```

#### 6.4 Prometheus Metrics `[Target Roadmap]`
Exporting custom prometheus metrics (via `prometheus_client` or endpoints) is a target enhancement for multi-node setups.

---

### 7. Maintenance and Updates

#### 7.1 Regular Maintenance Tasks
**Daily:**
- Monitor edge device CPU/Memory usage
- Check `logs/agent.log` for anomalous traceback errors
- Verify SQLite database size

**Weekly:**
- Backup the SQLite database (`data/digital_twin.db`) to offline/cloud storage

**Monthly:**
- Perform OS updates and security patches (`sudo apt update && sudo apt upgrade`)
- Inspect physical retrofitted sensor mounts for loose wiring or shifts

#### 7.2 Model Updates `[Target Roadmap]`
For future deep learning models, automated retraining pipelines will execute scripts such as `retrain_models.py` and `evaluate_models.py` when new labeled run-to-failure data is compiled.

#### 7.3 Dependency Updates
```bash
# Check for outdated packages
pip list --outdated

# Update requirements file and test
pip install --upgrade -r requirements.txt
python -m pytest test_suite.py
```

---

### 8. Troubleshooting and Recovery

#### 8.1 Common Issues and Solutions

**Issue: High CPU Usage on Edge Gateway**
- **Action**: Check if the simulation interval is too low. In `.env`, increase `SIMULATION_INTERVAL` to reduce CPU burden on the edge processor.
- **Service Restart**:
  ```bash
  sudo systemctl restart ai-digital-twin
  ```

**Issue: Sensor Data Not Being Written to Database**
- **Action**: Verify write permissions for the `/opt/ai-digital-twin/data/` directory.
  ```bash
  ls -la data/
  # Ensure the user running the agent (or docker container) has write access to digital_twin.db
  ```
- **Action**: Check logs for SQLite lock errors.

#### 8.2 Disaster Recovery
- **Backup**:
  ```bash
  # Cron script for daily SQLite backups
  tar -czf /backups/digital_twin_$(date +%F).tar.gz /opt/ai-digital-twin/data/digital_twin.db
  ```
- **Recovery**:
  1. Stop service: `sudo systemctl stop ai-digital-twin`
  2. Restore database: `cp /backups/digital_twin_date.db /opt/ai-digital-twin/data/digital_twin.db`
  3. Start service: `sudo systemctl start ai-digital-twin`

---

### 9. Performance Optimization

#### 9.1 Caching Strategy
- In-memory caches are maintained for active machine status in `data_service.py` to prevent redundant disk I/O on SQLite for frequent dashboard polls.
- `[Target Roadmap]`: Redis-based caching is planned for enterprise scaling.

#### 9.2 Batch Processing
- Data service processes telemetry readings per machine sequentially at each interval step. Batch predictions and vectorizations using NumPy can be expanded when scaling to 10+ machines.

#### 9.3 Database Optimization
- SQLite indexes are created automatically on table creation to keep query latencies under 10ms.
- `[Target Roadmap]`: PostgreSQL database partitioning for very large historical telemetry sets.

---

### 10. Security Hardening

#### 10.1 Access Control
```bash
# Set proper file permissions
chmod 700 /opt/ai-digital-twin
chmod 600 /opt/ai-digital-twin/.env
```

#### 10.2 Network Security
```bash
# Configure firewall on Ubuntu / JetPack
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 8000/tcp  # Unified Dashboard and API
sudo ufw enable
```

#### 10.3 SSL/TLS Configuration `[Target Roadmap]`
Reverse proxy configuration using Nginx to handle SSL certificates (HTTPS) for remote dashboard access.

---

### 11. Scaling Strategies `[Target Roadmap]`
- **Horizontal**: Load balancers (Nginx) routing to multiple edge gateways.
- **Vertical**: Allocating more CPU cores and RAM to the host edge PC.

---

### 12. Support and Escalation
- **Local Diagnostics**: Run test suite `python -m pytest test_suite.py` to isolate API, logic, or email/SMS handler failures.
- **Logs**: Output is directed to `./logs/agent.log`.

---

### 13. Compliance and Auditing
- **Audit Logging**: Basic logging of API start/stop simulation events is recorded in `./logs/agent.log`.
- **Data Retention**: By default, SQLite stores all historical telemetry. Telemetry purging script is planned for future storage optimization.
