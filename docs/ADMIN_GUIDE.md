# AI Digital Twin - Administrator Guide

This guide is intended for system administrators, IT staff, and developers who deploy, maintain, and troubleshoot the AI Digital Twin and Predictive Maintenance system.

---

## 1. System Requirements

* **Operating System**: Linux (Ubuntu 20.04 LTS or newer recommended) or Windows (10/11 with PowerShell / Git Bash).
* **Hardware**:
  * Minimum: 2 Cores CPU, 8 GB RAM, 20 GB Storage.
  * Recommended: 4 Cores CPU, 16 GB RAM, 50 GB Storage.
* **Software Dependencies**:
  * Python 3.8+ (with `pip`)
  * Node.js v18+ (with `npm` or `pnpm`)
  * SQLite3 (Included by default in Python standard library)
  * Optional: Docker and Docker Compose (for containerized deployments)

---

## 2. Installation and Setup

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-org/ai-digital-twin.git
cd "ai-digital-twin"
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` (or create one) and configure the environment variables:
```bash
# Example .env configuration
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO
LOG_FILE=./logs/agent.log
DB_PATH=./data/digital_twin.db
SIMULATION_ENABLED=true
SIMULATION_INTERVAL=1.0
```

### Step 3: Install Backend Dependencies
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### Step 4: Install Frontend Dependencies
Navigate to the `client` directory and install the Node modules:
```bash
cd client
npm install
```

---

## 3. Launching Services (Local Development)

### Method A: Single Integrated Server (Recommended)
You can start the backend API and frontend simulator together using the integrated server script:
```bash
python integrated_server.py
```
This launches the FastAPI backend on `http://localhost:8000` and automatically initiates sensor telemetry simulation.

### Method B: Separate Front-End Dev Server
To run the front-end in hot-reload mode:
```bash
# Start backend
python backend_api.py

# In a separate terminal, start frontend
cd client
npm run dev
```

> [!WARNING]
> **Windows Path & Ampersand Bug Workaround**
>
> If your project directory path contains space or special characters like an ampersand (`&`), running standard `npm run build` will fail because Windows command wrappers (`.cmd` files) do not handle the ampersand correctly.
>
> In such environments, bypass the `.cmd` wrappers and call the JS files directly via `node`:
> * **TypeScript Compile**: `node node_modules/typescript/lib/tsc.js -b`
> * **Vite Production Build**: `node node_modules/vite/bin/vite.js build`

---

## 4. Production Deployment with Docker

The prototype is fully containerized. You can deploy it using Docker and Docker Compose.

### Build and Run with Docker Compose
```bash
# Build the images and run containers in detached mode
docker-compose up --build -d

# Verify containers are running
docker ps
```
The services will be exposed at:
* Backend API: `http://localhost:8000`
* Frontend Dashboard: `http://localhost:3000`

---

## 5. Monitoring and Maintenance

### Health Checks
The FastAPI backend exposes a health check endpoint:
```bash
curl http://localhost:8000/health
```
A healthy response returns: `{"status": "healthy", "timestamp": "..."}`.

### Log Management
All backend system logs, AI decisions, and warning details are written to the path specified by the `LOG_FILE` environment variable (default: `./logs/agent.log`).
To tail the logs in real-time:
```bash
tail -f logs/agent.log
```

### Log Rotation (Linux Systems)
On production environments, configure log rotation by copying the configuration from `setup_monitoring.sh` to `/etc/logrotate.d/ai-digital-twin` to prevent log files from exhausting disk space.

### SQLite Database Maintenance
The system stores telemetry data and alert logs in a local SQLite file (default: `./data/digital_twin.db`).
* **Backup**: Since SQLite supports simple file copying, backup can be performed by copying `./data/digital_twin.db` when the database is idle:
  ```bash
  sqlite3 data/digital_twin.db ".backup backup_dt_db.db"
  ```
* **Performance**: A cron job can be set up to vacuum the database monthly:
  ```bash
  sqlite3 data/digital_twin.db "VACUUM;"
  ```

---

## 6. Troubleshooting

### High CPU Usage
If Python CPU utilization spikes:
1. Ensure the simulation interval is not set too low. An interval of `< 0.1` seconds puts heavy load on SQLite I/O.
2. Check if multiple simulation threads have been spawned by querying `/health` or restarting the service.

### SQLite Database Locked Error
If the database gets locked during concurrent writes:
1. The backend uses thread-safe SQLite connection handling, but direct external database manipulations during simulation should be avoided.
2. Consider increasing the SQLite timeout parameter or restarting the backend server.
