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
from server.llm_agent import run_agent
from server.agent_memory import AgentMemory
from server.agent_tools import get_recent_alerts as tool_get_recent_alerts
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


class AgentChatPayload(BaseModel):
    message: str
    machine_id: Optional[str] = None


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


# ---------------------------------------------------------------------------
# Phase 8: Agentic AI Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/agent/chat", dependencies=[Depends(require_operator_or_admin)])
@limiter.limit("10/minute")
async def agent_chat(
    request: Request,
    payload: AgentChatPayload,
    current_user: User = Depends(get_current_user),
):
    """
    Main agentic chat endpoint. Requires operator or admin role.
    The LLM agent reasons over the question, autonomously calls tools
    (telemetry, alerts, maintenance history), and returns a diagnosis.
    Rate-limited to 10 requests/minute to bound autonomous work order creation.
    """
    result = run_agent(
        user_message=payload.message,
        machine_id=payload.machine_id,
        username=current_user.username,
    )
    return JSONResponse(content=result)


@app.get("/api/agent/memory/{machine_id}")
async def get_agent_memory(
    machine_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """Return the agent's past diagnoses for a specific machine."""
    require_machine(machine_id)
    memory = AgentMemory()
    memories = memory.get_recent_memories(machine_id, limit=limit)
    return JSONResponse(content={"machine_id": machine_id, "memories": memories})


@app.get("/api/work-orders")
async def get_work_orders(
    machine_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    """Return maintenance work orders, optionally filtered by machine or status."""
    try:
        with pool.connection() as conn:
            filters = []
            params = []
            if machine_id:
                filters.append("machine_id = %s")
                params.append(machine_id)
            if status:
                filters.append("status = %s")
                params.append(status)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            params.append(limit)
            rows = conn.execute(
                f"""
                SELECT order_id, machine_id, action, urgency, status, created_at, resolved_at, notes, created_by
                FROM work_orders {where}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                params
            ).fetchall()

        orders = [
            {
                "order_id": str(row[0]),
                "machine_id": row[1],
                "action": row[2],
                "urgency": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
                "resolved_at": row[6].isoformat() if row[6] and hasattr(row[6], "isoformat") else None,
                "notes": row[7],
                "created_by": row[8],
            }
            for row in rows
        ]
        return JSONResponse(content={"count": len(orders), "work_orders": orders})
    except Exception as e:
        logger.error(f"Error fetching work orders: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve work orders")


@app.post("/api/work-orders/{order_id}/approve", dependencies=[Depends(require_operator_or_admin)])
async def approve_work_order(order_id: str):
    """Approve a pending work order (Human confirmation gate)."""
    try:
        with pool.connection() as conn:
            result = conn.execute(
                """
                UPDATE work_orders
                SET status = 'Open'
                WHERE order_id = %s AND status = 'Pending Approval'
                RETURNING order_id
                """,
                (order_id,)
            ).fetchone()
            conn.commit()
        if not result:
            raise HTTPException(status_code=404, detail="Pending work order not found or already processed")
        return {"status": "approved", "order_id": order_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving work order: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve work order")


@app.patch("/api/work-orders/{order_id}/resolve", dependencies=[Depends(require_operator_or_admin)])
async def resolve_work_order(order_id: str):
    """Mark a work order as resolved."""
    try:
        with pool.connection() as conn:
            result = conn.execute(
                """
                UPDATE work_orders
                SET status = 'Resolved', resolved_at = NOW()
                WHERE order_id = %s
                RETURNING order_id
                """,
                (order_id,)
            ).fetchone()
            conn.commit()
        if not result:
            raise HTTPException(status_code=404, detail="Work order not found")
        return {"status": "resolved", "order_id": order_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving work order: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve work order")


# ---------------------------------------------------------------------------
# ATLAS v5 — Domain Cognition Endpoints
# ---------------------------------------------------------------------------

from server.atlas.domain_service import get_domain_service as _get_atlas


@app.get("/api/atlas/domains")
async def atlas_list_domains():
    """List all registered ATLAS domains and their adapter status."""
    svc = _get_atlas()
    return JSONResponse(content={"domains": svc.get_all_domain_status()})


@app.get("/api/atlas/domain/{domain}/status")
async def atlas_domain_status(domain: str):
    """All machine snapshots for a single domain."""
    svc = _get_atlas()
    snapshots = svc.get_domain_snapshots(domain)
    if not snapshots:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found or has no data yet")
    return JSONResponse(content={"domain": domain, "machines": snapshots, "count": len(snapshots)})


@app.get("/api/atlas/domain/{domain}/machine/{machine_id}")
async def atlas_machine_snapshot(domain: str, machine_id: str):
    """Latest snapshot for a specific machine in a domain."""
    svc = _get_atlas()
    snap = svc.get_snapshot(domain, machine_id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"No snapshot for {domain}/{machine_id}")
    return JSONResponse(content=snap)


@app.get("/api/atlas/cross-domain/comparison")
async def atlas_cross_domain_comparison():
    """
    All domains' latest snapshots side-by-side.
    Primary data source for the Cross-Domain Comparison Dashboard.
    """
    svc = _get_atlas()
    return JSONResponse(content={"comparison": svc.get_cross_domain_comparison()})


@app.get("/api/atlas/models/status")
async def atlas_model_status():
    """
    Report which domains have trained WorldModel checkpoints and which
    are using the EMA fallback.
    """
    from pathlib import Path
    models_dir = Path("data/models")
    model_files = list(models_dir.glob("*_world_model.pt")) if models_dir.exists() else []
    trained_domains = [f.stem.replace("_world_model", "") for f in model_files]

    metrics = {}
    for domain in trained_domains:
        metrics_path = models_dir / f"{domain}_metrics.json"
        if metrics_path.exists():
            import json as _json
            with open(str(metrics_path)) as f:
                metrics[domain] = _json.load(f)

    svc = _get_atlas()
    engines = {
        domain: {
            "using_lstm": engine.using_lstm,
            "domain": engine.domain,
        }
        for domain, engine in svc._engines.items()
    }

    return JSONResponse(content={
        "trained_domains": trained_domains,
        "active_engines": engines,
        "metrics": metrics,
        "training_command": "python server/atlas/train_rul.py --domain cmapss",
    })


@app.post("/api/atlas/models/reload", dependencies=[Depends(require_admin)])
async def atlas_reload_model(domain: str = Query(..., description="Domain to reload model for")):
    """
    Hot-reload a trained WorldModel after retraining (admin only).
    Returns whether the reload found a new checkpoint.
    """
    svc = _get_atlas()
    engine = svc.get_engine(domain)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"No active engine for domain '{domain}'")
    success = engine.reload_model()
    return JSONResponse(content={"domain": domain, "reloaded": success, "using_lstm": engine.using_lstm})


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    service.start_simulation(interval=int(os.environ.get("SIMULATION_INTERVAL", 1)))
    uvicorn.run(
        app,
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=int(os.environ.get("API_PORT", 8000)),
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )

