import logging
import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional, List, Dict

from data_service import get_data_service


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# Initialize FastAPI app
app = FastAPI(
    title="AI Digital Twin API",
    description="Predictive Maintenance System API for MSMEs",
    version="1.0.0"
)

cors_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
    if origin.strip()
] or ["*"]

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

service = get_data_service()
logger = logging.getLogger("DigitalTwin")
_api_key_warning_logged = False

class FaultInjectionPayload(BaseModel):
    fault_mode: str


def require_machine(machine_id: str) -> None:
    if machine_id not in service.machine_info:
        raise HTTPException(status_code=404, detail="Machine not found")

def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    """Require X-API-Key for control endpoints when API_KEY is configured."""
    expected_key = os.environ.get("API_KEY")
    if not expected_key:
        global _api_key_warning_logged
        if not _api_key_warning_logged:
            logger.warning("API_KEY is not set; control endpoints are running without API-key enforcement.")
            _api_key_warning_logged = True
        return

    if not x_api_key or not secrets.compare_digest(x_api_key, expected_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": utc_timestamp(),
        "version": "1.0.0"
    }

@app.get("/api/status")
async def system_status():
    return {
        "status": "running",
        "simulation_running": service.is_running,
        "timestamp": utc_timestamp()
    }

@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    summary = service.get_dashboard_summary()
    return JSONResponse(content=summary)

@app.get("/api/machines")
async def get_all_machines():
    machines = service.get_all_machines_info()
    return JSONResponse(content=machines)

@app.get("/api/machines/{machine_id}/status")
async def get_machine_status(machine_id: str):
    status = service.get_machine_status(machine_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Machine not found")
    return JSONResponse(content=status)

@app.get("/api/machines/{machine_id}/telemetry")
async def get_machine_telemetry(
    machine_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
):
    require_machine(machine_id)
    telemetry = service.get_machine_telemetry(machine_id, limit=limit)
    return JSONResponse(content=telemetry)

@app.get("/api/machines/{machine_id}/trends")
async def get_machine_trends(machine_id: str):
    require_machine(machine_id)
    trends = service.get_machine_trends(machine_id)
    return JSONResponse(content=trends)

@app.get("/api/alerts/recent")
async def get_recent_alerts(limit: int = Query(default=50, ge=1, le=500)):
    alerts = service.get_recent_alerts(limit=limit)
    return JSONResponse(content=alerts)

@app.get("/api/alerts/machine/{machine_id}")
async def get_machine_alerts(
    machine_id: str,
    limit: int = Query(default=20, ge=1, le=500),
):
    require_machine(machine_id)
    alerts = service.get_alerts_by_machine(machine_id, limit=limit)
    return JSONResponse(content=alerts)

@app.post("/api/simulation/start", dependencies=[Depends(require_api_key)])
async def start_simulation(
    interval: float = Query(default=1.0, gt=0, le=3600),
):
    service.start_simulation(interval=interval)
    return {"status": "simulation started", "interval": interval}

@app.post("/api/simulation/stop", dependencies=[Depends(require_api_key)])
async def stop_simulation():
    service.stop_simulation()
    return {"status": "simulation stopped"}

@app.post("/api/machines/{machine_id}/fault", dependencies=[Depends(require_api_key)])
async def inject_fault(machine_id: str, payload: FaultInjectionPayload):
    if machine_id not in service.simulator.machines:
        raise HTTPException(status_code=404, detail="Machine not found in simulator")
    
    valid_modes = ["normal", "bearing_wear", "misalignment", "overheating", "electrical_fault"]
    if payload.fault_mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid fault mode. Choose from {valid_modes}")
        
    service.simulator.machines[machine_id].fault_mode = payload.fault_mode
    # Reset degradation steps to allow clean progression
    service.simulator.machines[machine_id].degradation_step = 0
    return {"status": "fault injected", "machine_id": machine_id, "fault_mode": payload.fault_mode}

if __name__ == "__main__":
    import uvicorn
    service.start_simulation(interval=int(os.environ.get("SIMULATION_INTERVAL", 1)))
    uvicorn.run(
        app,
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=int(os.environ.get("API_PORT", 8000)),
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )
