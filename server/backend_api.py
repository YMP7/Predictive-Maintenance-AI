import logging
import os
import secrets
import uuid

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pathlib import Path
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from server.adapters.domain_profile import DOMAIN_PROFILES
from server.data_service import get_data_service
from server import machine_registry
from server.machine_registry import MachineConfig, NewMachine
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
    ALGORITHM,
    get_user_from_db,
    get_current_user,
    require_admin,
    require_operator_or_admin,
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

if "*" in cors_origins:
    raise RuntimeError(
        "FATAL: CORS_ORIGINS=* cannot be combined with cookie authentication — any site "
        "could then issue credentialed requests. List the exact frontend origins, e.g. "
        "CORS_ORIGINS=https://app.example.com,http://localhost:3000"
    )

# Every /api route needs a signed-in user, except these. The phone bridge checks its own
# MOBILE_BRIDGE_TOKEN; health is a liveness probe. Registered before CORS so CORS wraps it.
_PUBLIC_API_PATHS = {"/api/auth/login", "/api/auth/logout", "/api/health", "/api/atlas/mobile/telemetry"}


@app.middleware("http")
async def require_login_for_api(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and path not in _PUBLIC_API_PATHS and request.method != "OPTIONS":
        try:
            # Honour dependency_overrides like a normal Depends(get_current_user) would.
            override = request.app.dependency_overrides.get(get_current_user)
            # Cached on request.state so endpoint dependencies don't look the user up again.
            request.state.user = override() if override is not None else await get_current_user(request)
        except HTTPException as e:
            return JSONResponse({"detail": e.detail}, status_code=e.status_code)
    return await call_next(request)


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

# Note: Replacing API Key with JWT Admin dependency for control endpoints


class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
@limiter.limit("5/minute")
def login_for_access_token(request: Request, login_req: LoginRequest):
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


# ---- Device management (admin only): edits config/machines.json and applies it live ----

@app.post("/api/admin/machines", dependencies=[Depends(require_admin)], status_code=201)
def add_machine(payload: NewMachine):
    config = payload.model_dump(exclude={"machine_id"})

    def change(machines: Dict[str, Any]):
        if payload.machine_id in machines:
            raise HTTPException(status_code=409, detail=f"Machine {payload.machine_id} already exists")
        machines[payload.machine_id] = config

    service.apply_registry(machine_registry.mutate(change))
    logger.info("Machine %s added to registry", payload.machine_id)
    return {"machine_id": payload.machine_id, **config}


@app.put("/api/admin/machines/{machine_id}", dependencies=[Depends(require_admin)])
def update_machine(machine_id: str, payload: MachineConfig):
    def change(machines: Dict[str, Any]):
        if machine_id not in machines:
            raise HTTPException(status_code=404, detail="Machine not found")
        machines[machine_id] = payload.model_dump()

    service.apply_registry(machine_registry.mutate(change))
    logger.info("Machine %s updated", machine_id)
    return {"machine_id": machine_id, **payload.model_dump()}


@app.delete("/api/admin/machines/{machine_id}", dependencies=[Depends(require_admin)])
def delete_machine(machine_id: str):
    def change(machines: Dict[str, Any]):
        if machine_id not in machines:
            raise HTTPException(status_code=404, detail="Machine not found")
        del machines[machine_id]

    service.apply_registry(machine_registry.mutate(change))
    logger.info("Machine %s removed from registry; stored telemetry history is kept", machine_id)
    return {"deleted": machine_id}

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
    
    valid_modes = ["normal", "bearing_wear", "misalignment", "rotor_imbalance", "overheating", "electrical_fault"]
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
def agent_chat(
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
def get_agent_memory(
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
def get_work_orders(
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


def _audit_work_order(conn, row, username: str, result: str) -> None:
    """Record a human status change in the same audit table as agent creation."""
    conn.execute(
        "INSERT INTO work_order_audit_log (id, timestamp, machine_id, action, urgency, justification, validation_result) VALUES (%s, NOW(), %s, %s, %s, %s, %s)",
        (str(uuid.uuid4()), row[1], row[2], row[3], f"order {row[0]} by {username}", result),
    )


@app.post("/api/work-orders/{order_id}/approve")
def approve_work_order(order_id: str, current_user: User = Depends(require_operator_or_admin)):
    """Approve a pending work order (Human confirmation gate)."""
    try:
        with pool.connection() as conn:
            result = conn.execute(
                """
                UPDATE work_orders
                SET status = 'Open'
                WHERE order_id = %s AND status = 'Pending Approval'
                RETURNING order_id, machine_id, action, urgency
                """,
                (order_id,)
            ).fetchone()
            if result:
                _audit_work_order(conn, result, current_user.username, "HUMAN_APPROVED")
            conn.commit()
        if not result:
            raise HTTPException(status_code=404, detail="Pending work order not found or already processed")
        return {"status": "approved", "order_id": order_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving work order: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve work order")


@app.patch("/api/work-orders/{order_id}/resolve")
def resolve_work_order(order_id: str, current_user: User = Depends(require_operator_or_admin)):
    """Mark a work order as resolved."""
    try:
        with pool.connection() as conn:
            result = conn.execute(
                """
                UPDATE work_orders
                SET status = 'Resolved', resolved_at = NOW()
                WHERE order_id = %s AND status = 'Open'
                RETURNING order_id, machine_id, action, urgency
                """,
                (order_id,)
            ).fetchone()
            if result:
                _audit_work_order(conn, result, current_user.username, "HUMAN_RESOLVED")
            conn.commit()
        if not result:
            raise HTTPException(status_code=404, detail="Open work order not found")
        return {"status": "resolved", "order_id": order_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving work order: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve work order")


# ---------------------------------------------------------------------------
# ATLAS v5 — Domain Cognition Endpoints
# ---------------------------------------------------------------------------

from server.atlas.domain_service import KNOWN_DOMAINS, get_domain_service as _get_atlas
from server.api import MODELS_DIR


@app.get("/api/atlas/domains")
async def atlas_list_domains():
    """List all registered ATLAS domains and their adapter status."""
    svc = _get_atlas()
    return JSONResponse(content={"domains": svc.get_all_domain_status()})


@app.get("/api/atlas/domain/{domain}/status")
def atlas_domain_status(domain: str):
    """All machine snapshots for a single domain."""
    svc = _get_atlas()
    svc.ensure_registered(domain)
    snapshots = svc.get_domain_snapshots(domain)

    if not snapshots:
        return JSONResponse(content={"domain": domain, "machines": [], "count": 0})
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
def atlas_cross_domain_comparison():
    """
    All domains' latest snapshots side-by-side.
    Primary data source for the Cross-Domain Comparison Dashboard.
    """
    svc = _get_atlas()
    for dom in KNOWN_DOMAINS:
        svc.ensure_registered(dom)
    return JSONResponse(content={"comparison": svc.get_cross_domain_comparison()})


@app.get("/api/atlas/models/status")
def atlas_model_status():
    """
    Report which domains have trained WorldModel checkpoints and which
    are using the EMA fallback.
    """
    models_dir = MODELS_DIR
    model_files = list(models_dir.glob("*_world_model.pt")) if models_dir.exists() else []
    trained_domains = [f.stem.replace("_world_model", "") for f in model_files]
    # The primary C-MAPSS checkpoint is saved as best_model.pt (see server/api.py).
    for name, profile in DOMAIN_PROFILES.items():
        if name not in trained_domains and any((models_dir / f).exists() for f in profile.checkpoints):
            trained_domains.append(name)

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
def atlas_reload_model(domain: str = Query(..., description="Domain to reload model for")):
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
# ATLAS Research & System Benchmark Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/atlas/research/transfer-study")
def atlas_transfer_study():
    """Returns the empirical cross-domain transfer study results."""
    from pathlib import Path
    import json
    json_path = Path(__file__).resolve().parent.parent / "data" / "transfer_study_results.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    # The study is minutes of compute; generate it offline with scripts/run_transfer_study.py.
    raise HTTPException(status_code=404, detail="Transfer study results not found")


@app.get("/api/atlas/research/ablations")
def atlas_ablations():
    """Returns the 4 canonical ATLAS ablation suite results."""
    from pathlib import Path
    import json
    json_path = Path(__file__).resolve().parent.parent / "data" / "ablation_results.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    raise HTTPException(status_code=404, detail="Ablation results not found")


@app.get("/api/atlas/evaluation/summary")
def atlas_evaluation_summary():
    """Returns the master evaluation summary scorecard from data/atlas_evaluation_summary.json."""
    from pathlib import Path
    import json
    json_path = Path(__file__).resolve().parent.parent / "data" / "atlas_evaluation_summary.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    raise HTTPException(status_code=404, detail="Evaluation summary scorecard not found")


@app.get("/api/atlas/system/benchmark")
def atlas_system_benchmark():
    """Returns system benchmark latencies, resource profiles, live memory RSS, and DB pool stats."""
    from pathlib import Path
    import json
    import psutil
    project_root = Path(__file__).resolve().parent.parent
    bench_path = project_root / "data" / "system_benchmark_results.json"
    prof_path = project_root / "data" / "system_resource_profile.json"

    bench_data = {}
    if bench_path.exists():
        with open(bench_path, "r", encoding="utf-8") as f:
            bench_data = json.load(f)

    prof_data = {}
    if prof_path.exists():
        with open(prof_path, "r", encoding="utf-8") as f:
            prof_data = json.load(f)

    process = psutil.Process()
    mem_info = process.memory_info()
    live_rss_mb = round(mem_info.rss / (1024 * 1024), 2)
    sys_mem = psutil.virtual_memory()
    sys_mem_avail_gb = round(sys_mem.available / (1024 * 1024 * 1024), 2)
    sys_cpu_pct = round(psutil.cpu_percent(interval=None), 1)
    proc_cpu_pct = round(process.cpu_percent(interval=None), 1)

    pool_stats = {}
    try:
        from server.database import pool
        stats = pool.get_stats()
        pool_stats = {
            "max_size": pool.max_size,
            "min_size": pool.min_size,
            "connections_num": getattr(stats, "connections_num", pool.max_size),
            "requests_waiting": getattr(stats, "requests_waiting", 0),
        }
    except Exception:
        pool_stats = {"status": "connected", "max_size": 10, "min_size": 2}

    return JSONResponse(content={
        "benchmark": bench_data,
        "profile": prof_data,
        "live_metrics": {
            "process_rss_mb": live_rss_mb,
            "system_memory_available_gb": sys_mem_avail_gb,
            "system_cpu_percent": sys_cpu_pct,
            "process_cpu_percent": proc_cpu_pct,
            "cpu_percent": proc_cpu_pct,
            "threads_count": process.num_threads(),
            "db_pool": pool_stats,
            "timestamp": utc_timestamp(),
        }
    })


@app.get("/api/atlas/domain/{domain}/machine/{machine_id}/window")
def atlas_machine_window(domain: str, machine_id: str):
    """Returns the current sliding feature window for machine_id in domain."""
    svc = _get_atlas()
    svc.ensure_registered(domain)
    engine = svc.get_engine(domain)
    adapter = svc.get_adapter(domain)
    if engine is None or adapter is None:
        raise HTTPException(status_code=404, detail=f"Domain engine for '{domain}' not found")

    with engine._lock:
        window = list(engine._windows.get(machine_id, []))

    if not window:
        # Nothing streamed yet: take one reading so the adapter decides the feature layout.
        try:
            window = [adapter.get_reading(machine_id).feature_vector]
        except Exception:
            raise HTTPException(status_code=404, detail=f"Unknown machine {domain}/{machine_id}")

    snap = svc.get_snapshot(domain, machine_id)
    # Never pad: a padded window would feed made-up readings into /api/decide.
    if len(window) < 30:
        raise HTTPException(
            status_code=409,
            detail=f"Warming up: {len(window)}/30 readings collected for {domain}/{machine_id}. Retry shortly.",
        )

    return JSONResponse(content={
        "domain": domain,
        "machine_id": machine_id,
        "window": window[-30:],
        "seq_len": len(window[-30:]),
        "feature_dim": len(window[0]),
        "cycle": snap.get("cycle", 30) if snap else 30
    })


# ---------------------------------------------------------------------------
# Mobile / Lumia Browser Telemetry Bridge
# ---------------------------------------------------------------------------
from server.adapters.mobile_adapter import push_browser_telemetry


@app.post("/api/atlas/mobile/telemetry")
async def receive_mobile_telemetry(
    payload: Dict[str, Any],
    x_mobile_bridge_token: str = Header(default=""),
):
    """Ingest real-time telemetry pushed from Lumia / mobile browser bridge."""
    # Fails closed: bridge stays disabled until MOBILE_BRIDGE_TOKEN is set
    expected = os.environ.get("MOBILE_BRIDGE_TOKEN", "")
    if not expected or not secrets.compare_digest(x_mobile_bridge_token, expected):
        raise HTTPException(status_code=401, detail="Invalid mobile bridge token")
    try:
        push_browser_telemetry(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse(content={"status": "ok", "received_at": utc_timestamp()})


@app.get("/lumia", response_class=HTMLResponse)
@app.get("/mobile-bridge", response_class=HTMLResponse)
def lumia_bridge_page():
    """Serve mobile telemetry bridge interface for Lumia / Windows Phone."""
    html_path = Path(__file__).resolve().parent / "static" / "lumia_bridge.html"
    if html_path.exists():
        with open(str(html_path), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    raise HTTPException(status_code=404, detail="Lumia bridge template not found")


# ---------------------------------------------------------------------------
# ATLAS Cognition Router Inclusion
# ---------------------------------------------------------------------------
from server.api import app as _atlas_cognition_app, startup_event as atlas_api_startup

app.include_router(
    _atlas_cognition_app.router, dependencies=[Depends(require_operator_or_admin)]
)

@app.on_event("startup")
def ensure_atlas_engines_initialized():
    """Ensure ATLAS cognition engines are initialized if running backend_api standalone."""
    import server.api as _api
    if _api._ace is None:
        atlas_api_startup()


if __name__ == "__main__":
    import uvicorn
    service.start_simulation(interval=int(os.environ.get("SIMULATION_INTERVAL", 1)))
    uvicorn.run(
        app,
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=int(os.environ.get("API_PORT", 8000)),
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )


