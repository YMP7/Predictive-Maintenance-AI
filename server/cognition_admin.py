"""
Cognition Dashboard backend (redesign P5, admin only). Reads what the trace endpoint stored; never changes a model's math.

- GET  /api/admin/cognition/{id}/history   stored traces over time: RUL band, latencies, a 2-D PCA of the 32-dim
                                            state vectors, and drift (data, model error, Machine DNA vs its first trace)
- GET  /api/admin/cognition/health          per domain: model loaded, traces, machines, mean latency, last trace
- GET  /api/admin/models/registry           model versions per domain (archived by content hash) with metrics
- POST /api/admin/models/{domain}/activate  make an archived version active (promote or roll back), reason required

The Learning Engine overwrites its checkpoint when it promotes and keeps no versions. The registry archives every
checkpoint it sees under data/models/registry/<domain>/<version>.pt, so any activation can be undone (ADR-025).
"""

from __future__ import annotations

import json
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from server import audit as A
from server import cognition_trace as T
from server.auth import User, require_admin

router = APIRouter(dependencies=[Depends(require_admin)])
_ID = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"
_lock = threading.Lock()

# ---------------------------------------------------------------- pure helpers


def project_states(vectors: Sequence[Sequence[float]]) -> Dict[str, Any]:
    """PCA to two components (numpy SVD, ADR-004). Signs are fixed so the same input always draws the same picture."""
    if len(vectors) == 0:
        return {"points": [], "explained": [0.0, 0.0]}
    X = np.asarray(vectors, dtype=np.float64)
    X = X - X.mean(axis=0)
    if len(X) < 2 or not np.any(X):
        return {"points": [[0.0, 0.0] for _ in range(len(X))], "explained": [0.0, 0.0]}
    _, s, vt = np.linalg.svd(X, full_matrices=False)
    comps = vt[:2].copy()
    for i, c in enumerate(comps):
        if c[np.argmax(np.abs(c))] < 0:
            comps[i] = -c
    pts = X @ comps.T
    if pts.shape[1] < 2:
        pts = np.hstack([pts, np.zeros((len(pts), 1))])
    var = s ** 2
    explained = [float(v / var.sum()) for v in var[:2]] + [0.0] * max(0, 2 - len(var))
    return {"points": np.round(pts, 6).tolist(), "explained": [round(e, 6) for e in explained]}


DRIFT_MIN_PER_SIDE = 3
SD_FLOOR = 0.01  # features are normalised to 0..1; below 1 % of range a shift in "sd" is noise, not drift


def data_drift(early: List[Dict[str, float]], late: List[Dict[str, float]]) -> List[Dict[str, Any]]:
    """Mean shift of each normalised feature between the earliest and latest traces, in pooled standard deviations.
    Needs DRIFT_MIN_PER_SIDE traces on each side; the pooled sd is floored at SD_FLOOR."""
    if len(early) < DRIFT_MIN_PER_SIDE or len(late) < DRIFT_MIN_PER_SIDE:
        return []
    feats = sorted(set().union(*early, *late))
    out = []
    for f in feats:
        a = np.array([e[f] for e in early if e.get(f) is not None], dtype=float)
        b = np.array([e[f] for e in late if e.get(f) is not None], dtype=float)
        if len(a) == 0 or len(b) == 0:
            continue
        sd = max(float(np.sqrt((a.var() + b.var()) / 2)), SD_FLOOR)
        out.append({"feature": f, "early_mean": float(a.mean()), "late_mean": float(b.mean()),
                    "shift_sd": float((b.mean() - a.mean()) / sd)})
    return sorted(out, key=lambda d: -abs(d["shift_sd"]))


def model_drift(pairs: List[Tuple[float, float]]) -> Dict[str, Any]:
    """Mean absolute RUL error in the first and second half of the traces that have ground truth."""
    if not pairs:
        return {"n": 0, "mae_early": None, "mae_recent": None}
    err = [abs(p - t) for p, t in pairs]
    half = max(1, len(err) // 2)
    return {"n": len(err), "mae_early": round(float(np.mean(err[:half])), 6),
            "mae_recent": round(float(np.mean(err[half:] or err)), 6)}


def dna_drift(baseline: Optional[Sequence[float]], current: Optional[Sequence[float]]) -> Optional[Dict[str, float]]:
    if baseline is None or current is None:
        return None
    a, b = np.asarray(baseline, dtype=float), np.asarray(current, dtype=float)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b)) or 1e-12
    return {"l2": round(float(np.linalg.norm(b - a)), 9), "cosine": round(max(0.0, 1.0 - float(a @ b) / denom), 9)}


# ---------------------------------------------------------------- history and health


def _by_stage(trace: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {s["stage"]: s for s in trace.get("stages", [])}


@router.get("/api/admin/cognition/health", tags=["cognition"], summary="Cognition health per domain")
def cognition_health():
    from server.atlas.domain_service import KNOWN_DOMAINS, get_domain_service

    try:
        stats = {r["domain"]: r for r in T._store().summary()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Trace store unavailable: {e}")
    svc = get_domain_service()
    rows = []
    for d in sorted(set(KNOWN_DOMAINS) | set(stats)):
        engine = svc.get_engine(d)
        s = stats.get(d, {})
        rows.append({"domain": d, "model_loaded": engine is not None, "using_lstm": bool(engine and engine.using_lstm),
                     **T.model_ref(d), "traces": s.get("traces", 0), "machines": s.get("machines", 0),
                     "mean_latency_ms": s.get("mean_latency_ms"), "last_trace": s.get("last_trace")})
    return {"domains": rows}


@router.get("/api/admin/cognition/{machine_id}/history", tags=["cognition"],
            summary="Stored traces over time: RUL band, latency, PCA of state vectors, drift")
def cognition_history(machine_id: str, domain: str = Query(..., pattern=_ID), limit: int = Query(200, ge=1, le=2000)):
    try:
        traces = T._store().history(domain, machine_id, limit)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Trace store unavailable: {e}")
    cap = T.truth_cap(domain)
    points, states, feats, pairs, dnas = [], [], [], [], []
    lat: Dict[str, List[float]] = {s: [] for s in T.STAGES}
    for t in traces:
        by = _by_stage(t)

        def out(stage: str) -> Dict[str, Any]:
            return by.get(stage, {}).get("output") or {}

        rul = dict(out("rul"))
        if rul.get("ground_truth") is not None and cap:
            rul["ground_truth"] = min(float(rul["ground_truth"]), cap)  # older traces predate ground_truth_capped
        for s in T.STAGES:
            if s in by:
                lat[s].append(float(by[s].get("latency_ms") or 0.0))
        points.append({"ts": t["ts"], "rul_mean": rul.get("mean"), "rul_p10": rul.get("p10"), "rul_p90": rul.get("p90"),
                       "ground_truth": rul.get("ground_truth"), "total_latency_ms": t.get("total_latency_ms"),
                       "recommended_action": out("decision").get("recommended_action"),
                       "stage_latency_ms": {s: by[s].get("latency_ms") for s in by}})
        if out("world_model").get("state_vector"):
            states.append(out("world_model")["state_vector"])
        feats.append(out("adapter").get("normalized") or {})
        if rul.get("mean") is not None and rul.get("ground_truth") is not None:
            pairs.append((float(rul["mean"]), float(rul["ground_truth"])))
        if out("machine_dna").get("dna"):
            dnas.append((t["ts"], out("machine_dna")["dna"]))
    third = max(1, len(feats) // 3)
    dna = dna_drift(dnas[0][1], dnas[-1][1]) if dnas else None
    return {
        "domain": domain, "machine_id": machine_id, "points": points, "truth_cap": cap,
        "projection": project_states(states),
        "stage_latency_ms": {s: (float(np.mean(v)) if v else None) for s, v in lat.items()},
        "drift": {
            "data": data_drift(feats[:third], feats[-third:]) if len(feats) >= 2 else [],
            "model": model_drift(pairs),
            "dna": None if dna is None else {**dna, "baseline_ts": dnas[0][0], "current_ts": dnas[-1][0]},
        },
    }


# ---------------------------------------------------------------- model registry


def _dirs() -> Tuple[Path, Path]:
    from server.api import MODELS_DIR
    models = Path(MODELS_DIR)
    return models, Path(os.environ.get("ATLAS_REGISTRY_DIR", str(models / "registry")))


def _active_file(models: Path, domain: str) -> Optional[Path]:
    from server.adapters.domain_profile import get_profile

    for name in get_profile(domain).checkpoints:
        if (models / name).exists():
            return models / name
    return None


def _metrics(models: Path, domain: str) -> Dict[str, Any]:
    """Scalar training metrics (and the benchmark block, if any) from the domain's metrics or metadata file."""
    for name in (f"{domain}_metrics.json", f"{domain}_model_metadata.json"):
        p = models / name
        if p.exists():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                return {}
            out = {k: v for k, v in raw.items() if isinstance(v, (int, float, str, bool))}
            if isinstance(raw.get("benchmark"), dict):
                out["benchmark"] = raw["benchmark"]
            return out
    return {}


def _archive(models: Path, reg: Path, domain: str) -> Optional[Dict[str, Any]]:
    """Copy the active checkpoint into the registry if this content is not there yet; return its entry."""
    active = _active_file(models, domain)
    if active is None:
        return None
    version = T._file_digest(str(active), active.stat().st_mtime)
    folder = reg / domain
    target, meta = folder / f"{version}.pt", folder / f"{version}.json"
    if not target.exists():
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(active, target)
        meta.write_text(json.dumps({"version": version, "checkpoint": active.name, "size": active.stat().st_size,
                                    "archived_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                                    "metrics": _metrics(models, domain)}), encoding="utf-8")
    return {"version": version, "checkpoint": active.name}


def _versions(reg: Path, domain: str, active: Optional[str]) -> List[Dict[str, Any]]:
    folder = reg / domain
    out = []
    for meta in folder.glob("*.json") if folder.exists() else []:
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
        except ValueError:
            continue
        out.append({**m, "active": m.get("version") == active})
    return sorted(out, key=lambda m: m.get("archived_at", ""))


def _refresh(domain: str) -> bool:
    """Serve the newly active weights now: the streaming RUL engine and the cognition pipeline's model."""
    import server.api as api
    from server.atlas.domain_service import get_domain_service
    from server.atlas.world_model import WorldModel

    engine = get_domain_service().get_engine(domain)
    ok = bool(engine.reload_model()) if engine is not None else False
    models, _ = _dirs()
    active = _active_file(models, domain)
    if api._ace is not None and active is not None:
        model = WorldModel.load(active)
        api._ace.domain_models[domain] = model
        if domain == api.PRIMARY_DOMAIN:
            api._world_model = model
        ok = True
    return ok


@router.get("/api/admin/models/registry", tags=["models"], summary="Model versions per domain, with metrics")
def model_registry():
    import server.api as api
    from server.adapters.domain_profile import DOMAIN_PROFILES

    models, reg = _dirs()
    rows = []
    with _lock:
        for domain in sorted(DOMAIN_PROFILES):
            active = _archive(models, reg, domain)
            history: List[Dict[str, Any]] = []
            if api._learning_engine is not None:
                try:
                    history = api._learning_engine.get_learning_history(domain=domain, limit=20)
                except Exception:
                    history = []
            rows.append({"domain": domain, "active": active, "metrics": _metrics(models, domain),
                         "versions": _versions(reg, domain, active and active["version"]), "learning_history": history})
    return {"domains": rows, "note": "New versions come from retraining (POST /api/learn/retrain, 3% validation gate)."}


class Activate(BaseModel):
    version: str = Field(pattern=r"^[0-9a-f]{6,64}$")
    reason: str = Field(min_length=5, max_length=500)


@router.post("/api/admin/models/{domain}/activate", tags=["models"],
             summary="Make an archived model version active (promote or roll back); audited and reversible")
def activate_version(domain: str, body: Activate, user: User = Depends(require_admin)):
    from server.adapters.domain_profile import DOMAIN_PROFILES

    if domain not in DOMAIN_PROFILES:
        raise HTTPException(status_code=404, detail="Unknown domain")
    models, reg = _dirs()
    with _lock:
        before = _archive(models, reg, domain)  # keep the current weights so this can be undone
        source = reg / domain / f"{body.version}.pt"
        if before is None or not source.exists():
            raise HTTPException(status_code=404, detail="No archived version with that id")
        target = models / before["checkpoint"]
        if before["version"] != body.version:
            tmp = target.with_suffix(".activating")
            shutil.copy2(source, tmp)
            os.replace(tmp, target)  # atomic on the same volume
        reloaded = _refresh(domain)
    after = {"version": body.version, "checkpoint": before["checkpoint"]}
    A.audit(category="model", action="activate", actor=user.username, actor_type="user", role=user.role, target=domain,
            outcome="success" if reloaded else "partial",
            details={"before": before, "after": after, "reason": body.reason, "reloaded": reloaded})
    return {"domain": domain, "active": after, "reloaded": reloaded}
