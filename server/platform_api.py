"""
Platform endpoints added in redesign P2: sensor ingestion (HTTP, WebSocket, CSV/Parquet, manual),
sensor profiles and device tokens (admin), the live SSE stream, browser interaction events,
readiness, and the request-audit middleware. `install(app)` wires all of it into the API.
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Literal, Optional, Union

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, ValidationError, model_validator
from starlette.concurrency import run_in_threadpool
from starlette.routing import Match

from server import audit as A
from server.adapters.configurable_adapter import SensorProfile
from server.auth import User, get_current_user, require_admin, require_operator_or_admin
from server.ingest import IngestError, TokenBucket, UnknownMachine, get_ingest_service, sse_events

logger = logging.getLogger("DigitalTwin.platform")
router = APIRouter()

MAX_PUSH_BYTES = 256 * 1024
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_UPLOAD_ROWS = 200_000
MAX_CLIENT_EVENT_BYTES = 64 * 1024
_ID = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"


# ---------------------------------------------------------------- payloads


class PushSample(BaseModel):
    ts: Optional[Union[str, float]] = None
    values: Dict[str, Any] = Field(min_length=1, max_length=64)


class PushBody(BaseModel):
    """Either one sample ({ts?, values}) or a batch ({samples: [...]})."""
    samples: Optional[List[PushSample]] = Field(None, min_length=1, max_length=1000)
    ts: Optional[Union[str, float]] = None
    values: Optional[Dict[str, Any]] = Field(None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def _one_shape(self):
        if (self.samples is None) == (self.values is None):
            raise ValueError("send either 'samples' or 'values'")
        return self

    def as_samples(self) -> List[Dict[str, Any]]:
        if self.samples is not None:
            return [s.model_dump() for s in self.samples]
        return [{"ts": self.ts, "values": self.values}]


def _too_big(request: Request, limit: int) -> None:
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > limit:
        raise HTTPException(status_code=413, detail=f"Body larger than {limit // 1024} KB")


def _device_token(headers) -> Optional[str]:
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return headers.get("x-device-token")


def _raise(e: IngestError):
    raise HTTPException(status_code=e.status, detail=str(e))


# ---------------------------------------------------------------- device push: HTTP


@router.post("/api/ingest/{machine_id}", tags=["ingest"],
             summary="Push sensor samples from a device (Authorization: Bearer <device token>)")
async def push_samples(machine_id: str, request: Request):
    _too_big(request, MAX_PUSH_BYTES)
    body = await request.body()
    if len(body) > MAX_PUSH_BYTES:
        raise HTTPException(status_code=413, detail=f"Body larger than {MAX_PUSH_BYTES // 1024} KB")
    svc = get_ingest_service()
    try:
        device = await run_in_threadpool(svc.authenticate, _device_token(request.headers), machine_id)
    except IngestError as e:
        _raise(e)
    try:
        payload = PushBody.model_validate_json(body)
    except ValidationError as e:
        await run_in_threadpool(svc.devices.touch, device["device_id"], False)
        raise HTTPException(status_code=422, detail=e.errors(include_url=False, include_input=False))
    try:
        return await run_in_threadpool(lambda: svc.ingest(machine_id, payload.as_samples(), source="http",
                                                          actor=device["device_id"], device_id=device["device_id"]))
    except IngestError as e:
        _raise(e)


# ---------------------------------------------------------------- device push: WebSocket


@router.websocket("/api/ingest/ws/{machine_id}")
async def push_websocket(ws: WebSocket, machine_id: str):
    """First message: {"token": "<device token>"}. Then one PushBody per message; each gets an ack."""
    await ws.accept()
    svc = get_ingest_service()
    try:
        first = await asyncio.wait_for(ws.receive_json(), timeout=10)
        device = await run_in_threadpool(svc.authenticate, (first or {}).get("token"), machine_id)
    except (IngestError, asyncio.TimeoutError, ValueError, AttributeError) as e:
        A.audit(category="device", action="websocket.auth", actor="unknown", actor_type="device", target=machine_id,
                outcome="failure", details={"reason": type(e).__name__})
        await ws.close(code=1008)
        return
    A.audit(category="device", action="websocket.connect", actor=device["device_id"], actor_type="device", target=machine_id)
    await ws.send_json({"status": "authenticated", "device_id": device["device_id"]})
    try:
        while True:
            msg = await ws.receive_json()
            if not svc.bucket.allow(device["device_id"]):
                await ws.send_json({"error": "rate limit exceeded"})
                continue
            try:
                payload = PushBody.model_validate(msg)
                summary = await run_in_threadpool(lambda: svc.ingest(machine_id, payload.as_samples(), source="websocket",
                                                                     actor=device["device_id"], device_id=device["device_id"]))
                await ws.send_json(summary)
            except ValidationError as e:
                await ws.send_json({"error": "invalid payload", "detail": e.errors(include_url=False, include_input=False)})
    except WebSocketDisconnect:
        pass
    finally:
        A.audit(category="device", action="websocket.disconnect", actor=device["device_id"], actor_type="device",
                target=machine_id)


# ---------------------------------------------------------------- operator manual entry


class ManualReading(BaseModel):
    values: Dict[str, Any] = Field(min_length=1, max_length=64)
    ts: Optional[str] = Field(None, max_length=40)
    note: Optional[str] = Field(None, max_length=500)


@router.post("/api/machines/{machine_id}/manual-readings", tags=["ingest"],
             dependencies=[Depends(require_operator_or_admin)], summary="Record an operator inspection reading")
def manual_reading(machine_id: str, body: ManualReading, user: User = Depends(get_current_user)):
    svc = get_ingest_service()
    try:
        summary = svc.ingest(machine_id, [{"ts": body.ts, "values": body.values}], source="manual",
                             actor=user.username, actor_type="user")
    except IngestError as e:
        _raise(e)
    if body.note:
        A.audit(category="operator", action="manual_entry.note", actor=user.username, actor_type="user", role=user.role,
                target=machine_id, details={"batch_id": summary["batch_id"], "note": body.note})
    return summary


# ---------------------------------------------------------------- backfill upload (admin)


def _parse_upload(name: str, data: bytes) -> List[Dict[str, Any]]:
    if name.lower().endswith(".parquet"):
        try:
            import pyarrow.parquet as pq
        except ImportError:
            raise HTTPException(status_code=415, detail="Parquet needs the pyarrow package on the server; upload CSV instead")
        table = pq.read_table(io.BytesIO(data)).to_pylist()
        rows = [{k: ("" if v is None else v) for k, v in r.items()} for r in table]
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(status_code=415, detail="CSV must be UTF-8")
        rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise HTTPException(status_code=422, detail="File has no data rows")
    if "ts" not in rows[0]:
        raise HTTPException(status_code=422, detail="First column must be 'ts' (ISO 8601 time); then one column per channel")
    if len(rows) > MAX_UPLOAD_ROWS:
        raise HTTPException(status_code=413, detail=f"More than {MAX_UPLOAD_ROWS} rows; split the file")
    return [{"ts": r["ts"], "values": {k: v for k, v in r.items() if k != "ts" and v not in ("", None)}} for r in rows]


@router.post("/api/admin/ingest/{machine_id}/upload", tags=["ingest"],
             summary="Backfill from CSV or Parquet; dry_run=true returns a validation report and stores nothing")
async def upload_backfill(machine_id: str, request: Request, file: UploadFile = File(...),
                          dry_run: bool = Query(True), user: User = Depends(require_admin)):
    _too_big(request, MAX_UPLOAD_BYTES + 64 * 1024)
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File larger than 10 MB")
    samples = _parse_upload(file.filename or "", data)
    source = "parquet" if (file.filename or "").lower().endswith(".parquet") else "csv"
    svc = get_ingest_service()
    try:
        summary = await run_in_threadpool(lambda: svc.ingest(machine_id, samples, source=source, actor=user.username,
                                                             actor_type="user", max_age_s=None, dry_run=dry_run))
    except IngestError as e:
        _raise(e)
    return {**summary, "rows": len(samples), "file": file.filename}


# ---------------------------------------------------------------- sensor profiles and devices (admin)


@router.get("/api/admin/sensor-profiles", tags=["admin"], dependencies=[Depends(require_admin)])
def list_profiles():
    return [p.model_dump() for p in get_ingest_service().profiles.list()]


@router.put("/api/admin/sensor-profiles/{machine_id}", tags=["admin"], summary="Create or replace a machine's sensor profile")
def put_profile(machine_id: str, profile: SensorProfile, user: User = Depends(require_admin)):
    if profile.machine_id != machine_id:
        raise HTTPException(status_code=400, detail="machine_id in the path and body differ")
    before, after = get_ingest_service().put_profile(profile, actor=user.username)
    A.audit(category="admin", action="sensor_profile.put", actor=user.username, actor_type="user", role=user.role,
            target=machine_id, details={"before": before, "after": after})
    return after


class NewDevice(BaseModel):
    machine_id: str = Field(pattern=_ID)
    protocol: Literal["http", "websocket", "mqtt", "modbus"] = "http"


def _examples(machine_id: str, token: str) -> Dict[str, str]:
    url = f"/api/ingest/{machine_id}"
    return {
        "curl": f"curl -X POST http://<host>:8000{url} -H \"Authorization: Bearer {token}\" "
                f"-H \"Content-Type: application/json\" -d '{{\"values\": {{\"<channel>\": 12.5}}}}'",
        "python": (f"import requests\nrequests.post('http://<host>:8000{url}', headers={{'Authorization': 'Bearer {token}'}},\n"
                   f"              json={{'samples': [{{'ts': '2026-11-08T06:30:00Z', 'values': {{'<channel>': 12.5}}}}]}})"),
        "mqtt": f"topic factory/{machine_id}/telemetry, payload {{\"values\": {{\"<channel>\": 12.5}}}} "
                f"(broker credentials are per device in mosquitto/config)",
        "websocket": f"ws://<host>:8000/api/ingest/ws/{machine_id}: first message {{\"token\": \"{token}\"}}",
    }


@router.get("/api/admin/devices", tags=["admin"], dependencies=[Depends(require_admin)],
            summary="Devices with last seen, message rate, error rate and channel quality")
def list_devices():
    return get_ingest_service().device_health()


@router.post("/api/admin/devices", tags=["admin"], status_code=201,
             summary="Issue a device token (shown once; only its SHA-256 is stored)")
def create_device(body: NewDevice, user: User = Depends(require_admin)):
    svc = get_ingest_service()
    if not svc.has_profile(body.machine_id):
        raise HTTPException(status_code=404, detail="Create the machine's sensor profile first")
    device_id, token = svc.devices.create(body.machine_id, body.protocol)
    A.audit(category="admin", action="device.create", actor=user.username, actor_type="user", role=user.role,
            target=device_id, details={"machine_id": body.machine_id, "protocol": body.protocol})
    return {"device_id": device_id, "machine_id": body.machine_id, "protocol": body.protocol, "token": token,
            "examples": _examples(body.machine_id, token)}


@router.post("/api/admin/devices/{device_id}/rotate", tags=["admin"], summary="Replace a device token; the old one stops working")
def rotate_device(device_id: str, user: User = Depends(require_admin)):
    token = get_ingest_service().devices.rotate(device_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Device not found or revoked")
    A.audit(category="admin", action="device.rotate", actor=user.username, actor_type="user", role=user.role, target=device_id)
    return {"device_id": device_id, "token": token}


@router.delete("/api/admin/devices/{device_id}", tags=["admin"])
def revoke_device(device_id: str, user: User = Depends(require_admin)):
    if not get_ingest_service().devices.revoke(device_id):
        raise HTTPException(status_code=404, detail="Device not found or already revoked")
    A.audit(category="admin", action="device.revoke", actor=user.username, actor_type="user", role=user.role, target=device_id)
    return {"revoked": device_id}


# ---------------------------------------------------------------- live stream


@router.get("/api/stream/machines/{machine_id}", tags=["stream"],
            summary="Server-sent events: readings as they arrive, heartbeat every 15 s, snapshot when ?domain= is given")
async def stream_machine(machine_id: str, request: Request, domain: Optional[str] = Query(None, pattern=_ID)):
    snapshot = None
    if domain:
        from server.atlas.domain_service import get_domain_service
        svc = get_domain_service()
        snapshot = lambda: svc.get_snapshot(domain, machine_id)  # noqa: E731
    return StreamingResponse(sse_events(request, get_ingest_service().broker, machine_id, snapshot=snapshot),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------- browser interaction events


class ClientEvent(BaseModel):
    type: str = Field(pattern=r"^[a-z][a-z0-9_.]{0,39}$")
    ts: str = Field(max_length=40)
    path: Optional[str] = Field(None, max_length=256)
    name: Optional[str] = Field(None, max_length=120)
    detail: Optional[Dict[str, Union[str, int, float, bool, None]]] = Field(None, max_length=20)


class ClientBatch(BaseModel):
    events: List[ClientEvent] = Field(max_length=200)


_client_bucket = TokenBucket(rate=5.0, burst=30.0)


@router.post("/api/audit/client-events", tags=["audit"], status_code=202,
             summary="Batched UI interaction events (page views, commands, 3D parts opened, filters, exports)")
def client_events(batch: ClientBatch, request: Request, user: User = Depends(get_current_user)):
    _too_big(request, MAX_CLIENT_EVENT_BYTES)
    if not _client_bucket.allow(user.username):
        raise HTTPException(status_code=429, detail="Too many client event batches")
    ip = request.client.host if request.client else None
    for e in batch.events:
        A.audit(category="client", action=e.type, actor=user.username, actor_type="user", role=user.role,
                source_ip=ip, target=e.path, details={"name": e.name, "client_ts": e.ts, "detail": e.detail or {}})
    return {"accepted": len(batch.events)}


# ---------------------------------------------------------------- readiness


@router.get("/api/ready", tags=["health"], summary="Readiness: database, MQTT broker, models, audit backlog")
def readiness():
    checks: Dict[str, Any] = {}
    try:
        from server.database import pool
        with pool.connection() as conn:
            conn.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {type(e).__name__}"
    try:
        from server.data_service import get_data_service
        mqtt = getattr(get_data_service(), "mqtt_client", None)
        checks["mqtt"] = "disabled" if mqtt is None else ("connected" if mqtt.client.is_connected() else "disconnected")
    except Exception as e:
        checks["mqtt"] = f"error: {type(e).__name__}"
    import server.api as api
    checks["models"] = sorted(api._ace.domain_models) if api._ace is not None else "not loaded"
    checks["audit"] = {"pending_db_writes": A.get_audit_log().pending_count()}
    ok = checks["database"] == "ok" and isinstance(checks["models"], list)
    return JSONResponse({"status": "ready" if ok else "degraded", "checks": checks}, status_code=200 if ok else 503)


# ---------------------------------------------------------------- request audit middleware


_CID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def _find_template(routes, scope) -> Optional[str]:
    for route in routes:
        try:
            match, child = route.matches(scope)
        except Exception:
            continue
        if match == Match.FULL:
            # Included routers wrap their routes; descend to the route that owns the path template.
            inner = getattr(route, "routes", None) or getattr(getattr(route, "router", None), "routes", None)
            if inner:
                found = _find_template(inner, {**scope, **child})
                if found:
                    return found
            if getattr(route, "path", None):
                return route.path
    return None


def _route_template(app, scope) -> str:
    route = scope.get("route")  # set by routing on the shared scope when available
    if getattr(route, "path", None):
        return route.path
    return _find_template(app.router.routes, scope) or scope["path"]


def install(app) -> None:
    """Mount the routers, the request-audit middleware and the log redaction filter."""
    from server.asset_view import router as asset_router
    from server.cognition_trace import router as trace_router
    from server.operations_api import router as operations_router

    app.include_router(router)
    app.include_router(asset_router)
    app.include_router(operations_router)
    app.include_router(trace_router, tags=["cognition"])
    logging.getLogger().addFilter(A.RedactingFilter())
    for h in logging.getLogger().handlers:
        h.addFilter(A.RedactingFilter())

    @app.middleware("http")
    async def audit_requests(request: Request, call_next):
        incoming = request.headers.get("x-correlation-id", "")
        cid = incoming if _CID.fullmatch(incoming) else str(uuid.uuid4())
        token = A.correlation_id.set(cid)
        start, status = time.perf_counter(), 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Correlation-ID"] = cid
            return response
        finally:
            path = request.url.path
            if path.startswith("/api/"):
                user = getattr(request.state, "user", None)
                A.audit(category="api", action=f"{request.method} {_route_template(app, request.scope)}",
                        actor=user.username if user else "anonymous", actor_type="user" if user else "anonymous",
                        role=user.role if user else None, source_ip=request.client.host if request.client else None,
                        outcome="success" if status < 400 else "failure",
                        latency_ms=(time.perf_counter() - start) * 1000,
                        details={"status": status, "path": path}, correlation_id=cid)
            A.correlation_id.reset(token)
