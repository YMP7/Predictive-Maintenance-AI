# AI Digital Twin Prototype - Quick Start Checklist
## Validated Runbook

**Last validated:** June 21, 2026  
**Current automated result:** 29 tests passed  
**Default application URL:** `http://localhost:8000`

## 1. What Is Ready

- [x] Python simulator and AI-agent modules
- [x] FastAPI backend
- [x] React dashboard
- [x] SQLite telemetry and alert persistence
- [x] Alert cooldown, localization, and provider hooks
- [x] Unit, integration, pipeline, performance, and API tests
- [x] Docker image and Compose deployment
- [x] Docker health check and restart policy
- [ ] Physical sensor integration
- [ ] Trained ML models and field accuracy validation
- [ ] Bhashini and cloud synchronization
- [ ] Live provider acceptance testing
- [ ] Operator UAT and production TLS/identity controls

## 2. Prerequisites

Local development:

- Python 3.12 recommended
- Node.js 20 or later
- npm

Container deployment:

- Docker Desktop or Docker Engine
- Docker Compose v2

## 3. Verify Project Files

Required runtime files:

```text
ai_agent.py
alert_handler.py
backend_api.py
data_service.py
data_sync.py
integrated_server.py
sensor_simulator.py
config/machines.json
client/
requirements.txt
Dockerfile
docker-compose.yml
```

Python syntax check:

```powershell
python -m py_compile sensor_simulator.py ai_agent.py alert_handler.py data_service.py data_sync.py backend_api.py integrated_server.py
```

## 4. Install Dependencies

Python:

```powershell
python -m pip install -r requirements.txt
```

Frontend:

```powershell
Set-Location client
npm ci
Set-Location ..
```

## 5. Configure Environment

The repository includes `.env`. Review these values before running:

```dotenv
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=
CORS_ORIGINS=*
SIMULATION_ENABLED=true
SIMULATION_INTERVAL=1
ALERT_COOLDOWN=300
ALERT_LANGUAGES=en,hi,te,ta,mr
LOG_LEVEL=INFO
LOG_FILE=./logs/agent.log
```

Set a non-empty `API_KEY` to require `X-API-Key` on simulation and fault-injection endpoints.

## 6. Validate the Backend

Run all automated tests:

```powershell
python -m pytest test_suite.py test_integration.py test_ai_pipeline.py test_performance.py test_api.py -q -p no:cacheprovider
```

Expected result:

```text
29 passed
```

## 7. Build the Frontend

Because the workspace path contains `&`, use the direct Node entrypoints on Windows:

```powershell
Set-Location client
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build
Set-Location ..
```

The production files are written to `client/dist` and served by `integrated_server.py`.

## 8. Run Locally

```powershell
python integrated_server.py
```

Verify:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/status
```

Open:

- Dashboard: `http://localhost:8000/dashboard`
- OpenAPI: `http://localhost:8000/docs`

Stop the process with `Ctrl+C`. The FastAPI lifespan handler stops the simulation thread cleanly.

## 9. Run with Docker

Build and start:

```powershell
docker compose up -d --build
```

Verify:

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/health
docker logs --tail 50 ai-digital-twin
```

The container should report `healthy`. The dashboard and API share port 8000; port 3000 is not exposed in production.

Persistent volumes store:

- `/app/data/digital_twin.db`
- `/app/logs/agent.log`

Stop without deleting data:

```powershell
docker compose stop
```

Start again:

```powershell
docker compose start
```

## 10. Test API Endpoints

Read endpoints:

```powershell
Invoke-RestMethod http://localhost:8000/api/dashboard/summary
Invoke-RestMethod http://localhost:8000/api/machines
Invoke-RestMethod http://localhost:8000/api/machines/M001/status
Invoke-RestMethod 'http://localhost:8000/api/machines/M001/telemetry?limit=10'
```

Fault injection without API key:

```powershell
$body = @{ fault_mode = 'bearing_wear' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/machines/M001/fault -ContentType application/json -Body $body
```

With `API_KEY` configured:

```powershell
$headers = @{ 'X-API-Key' = 'your-key' }
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/machines/M001/fault -Headers $headers -ContentType application/json -Body $body
```

Reset the machine with `fault_mode` set to `normal`.

## 11. Alert Provider Configuration

Twilio SMS/voice:

```dotenv
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
TWILIO_TO_NUMBER=
```

SMTP email:

```dotenv
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_USE_TLS=true
ALERT_EMAIL_TO=
```

Without credentials, the system logs simulated delivery. Do not claim live delivery until provider sandbox or production credentials have been tested.

## 12. Linux Host Monitoring

`setup_monitoring.sh` installs:

- A five-minute container/API health check
- Automatic container restart
- Logrotate configuration
- Cron output in `/var/log/ai-digital-twin/monitor.log`

Run as root on the Linux Docker host:

```bash
sudo bash setup_monitoring.sh
```

This script is not intended for native Windows hosts.

## 13. Troubleshooting

| Symptom | Check |
|---|---|
| Docker cannot connect | Start Docker Desktop/Engine |
| Port 8000 already in use | Change host `API_PORT` before `docker compose up` |
| Dashboard API errors | Verify `/health` and rebuild `client/dist` |
| Fault control returns 401 | Send the configured `X-API-Key` |
| Unknown machine returns 404 | Use M001, M002, M003, or M004 |
| Request returns 422 | Check limit, interval, or JSON body validation |
| No RUL yet | Allow at least 10 readings after agent startup |
| No external alert delivered | Check credentials, provider access, and logs |
| Windows `npm run build` fails | Use direct TypeScript and Vite Node commands above |

## 14. Release Checklist

- [x] Python syntax passes
- [x] 29 automated tests pass
- [x] TypeScript compiles
- [x] Vite production build succeeds
- [x] Docker image builds
- [x] Container becomes healthy
- [x] Dashboard deep link returns HTTP 200
- [x] SQLite data persists across restart
- [ ] Set a real API key
- [ ] Configure TLS and identity controls
- [ ] Validate provider delivery
- [ ] Back up SQLite data
- [ ] Complete operator UAT
- [ ] Validate accuracy using labeled field data

## 15. Current Project Boundary

The prototype is deployable and suitable for demonstration and controlled pilot data collection. It is not yet a field-validated ML product: model accuracy, calibrated RUL, long-duration reliability, physical sensor integration, and operator acceptance remain separate milestones.
