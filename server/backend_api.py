import logging
import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional, List, Dict
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from server.data_service import get_data_service
from server.database import pool
from server.auth import (
    Token,
    TokenData,
    User,
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM
)
from jose import JWTError, jwt
from datetime import timedelta

def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# Rate limiter (keyed by client IP address)
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="AI Digital Twin API",
    description="Predictive Maintenance System API for MSMEs",
    version="1.0.0"
)
app.state.limiter = limiter
def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    response = JSONResponse(
        {"error": f"Rate limit exceeded: {exc.detail}"}, status_code=429
    )
    # Since our limit is 5/minute, 60 seconds is a safe backoff value
    response.headers["Retry-After"] = "60"
    return response

app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

_cors_env = os.environ.get("CORS_ORIGINS", "").strip()
if _cors_env:
    cors_origins = [origin.strip() for origin in _cors_env.split(",") if origin.strip()]
else:
    cors_origins = ["http://localhost:3000"]

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = get_data_service()
logger = logging.getLogger("DigitalTwin")

if not _cors_env:
    logger.warning(
        "CORS_ORIGINS is not set — defaulting to http://localhost:3000. "
        "Set CORS_ORIGINS in your .env file for production deployments."
    )

class FaultInjectionPayload(BaseModel):
    fault_mode: str


def require_machine(machine_id: str) -> None:
    if machine_id not in service.machine_info:
        raise HTTPException(status_code=404, detail="Machine not found")

# Removed OAuth2PasswordBearer for HttpOnly cookies

# User lookup via TimescaleDB (replaces the old fake_users_db in-memory dict)
def get_user_from_db(username: str) -> dict | None:
    """Query the users table for a single user by username."""
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT username, hashed_password, role FROM users WHERE username = %s",
            (username,)
        ).fetchone()
        if row:
            return {"username": row[0], "hashed_password": row[1], "role": row[2]}
    return None

async def get_current_user(request: Request) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )
    
    # CSRF Protection: Require custom header
    if request.headers.get("X-API-Request") != "true":
        raise HTTPException(
            status_code=403, 
            detail="Missing CSRF protection header (X-API-Request)"
        )

    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=payload.get("role"))
    except JWTError:
        raise credentials_exception
        
    user_dict = get_user_from_db(token_data.username)
    if user_dict is None:
        raise credentials_exception
    return User(**user_dict)

async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return current_user

async def require_operator_or_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return current_user

# Note: Replacing API Key with JWT Admin dependency for control endpoints


class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
@limiter.limit("5/minute")
async def login_for_access_token(request: Request, login_req: LoginRequest):
    user_dict = get_user_from_db(login_req.username)
    if not user_dict or not verify_password(login_req.password, user_dict["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_dict["username"], "role": user_dict["role"]}, expires_delta=access_token_expires
    )
    
    IS_LOCAL_DEV = os.getenv("ENVIRONMENT", "development") == "development"
    
    response = JSONResponse(content={"role": user_dict["role"]})
    # Set HttpOnly cookie for the token
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not IS_LOCAL_DEV,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    # Set non-HttpOnly cookie for frontend UI state
    response.set_cookie(
        key="auth_status",
        value="true",
        httponly=False,
        secure=not IS_LOCAL_DEV,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    # Also set a non-HttpOnly cookie for role if needed by frontend
    response.set_cookie(
        key="user_role",
        value=user_dict["role"],
        httponly=False,
        secure=not IS_LOCAL_DEV,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return response

@app.post("/api/auth/logout")
async def logout():
    response = JSONResponse(content={"detail": "Logged out successfully"})
    response.delete_cookie("access_token", samesite="lax")
    response.delete_cookie("auth_status", samesite="lax")
    response.delete_cookie("user_role", samesite="lax")
    return response

@app.get("/api/auth/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

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

@app.post("/api/simulation/start", dependencies=[Depends(require_operator_or_admin)])
async def start_simulation(
    interval: float = Query(default=1.0, gt=0, le=3600),
):
    service.start_simulation(interval=interval)
    return {"status": "simulation started", "interval": interval}

@app.post("/api/simulation/stop", dependencies=[Depends(require_operator_or_admin)])
async def stop_simulation():
    service.stop_simulation()
    return {"status": "simulation stopped"}

@app.post("/api/machines/{machine_id}/fault", dependencies=[Depends(require_admin)])
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
