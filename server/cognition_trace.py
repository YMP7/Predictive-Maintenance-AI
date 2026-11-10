"""
Read-only cognition trace (D5 backend): GET /api/admin/cognition/{machine_id}/trace.

Runs the frozen pipeline's own public calls in order (adapter window, World Model, AMKB, Machine DNA,
Adaptive Context, RUL, Simulation, Decision Graph, Explainability, Learning) with a timer around each,
and returns every intermediate output. Nothing here changes a model or its math:
- RUL p10/p90 are quantiles of the same Normal(mean, sqrt(neighbour variance)) the Simulation Engine samples.
- The failure-time histogram re-draws the engine's samples with the same seed, so they match exactly.
Each live trace is stored in `cognition_traces`; `?ts=` replays the latest stored trace at or before ts.
"""

from __future__ import annotations

import dataclasses
import functools
import hashlib
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query

from server.audit import audit, correlation_id
from server.auth import require_admin

STAGES = ["adapter", "world_model", "amkb", "machine_dna", "adaptive_context", "rul", "simulation", "decision",
          "explainability", "learning"]
Z90 = 1.2815515655446004  # standard normal 90th percentile

router = APIRouter(dependencies=[Depends(require_admin)])


# ---------------------------------------------------------------- helpers shared with the audit hooks


def window_hash(window: Any) -> str:
    return hashlib.sha256(np.asarray(window, dtype=np.float32).tobytes()).hexdigest()[:16]


@functools.lru_cache(maxsize=32)
def _file_digest(path: str, mtime: float) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def model_ref(domain: str) -> Dict[str, Optional[str]]:
    """Checkpoint name and content hash for the domain's World Model (the model version)."""
    from server.adapters.domain_profile import get_profile
    from server.api import MODELS_DIR

    for name in get_profile(domain).checkpoints:
        p = Path(MODELS_DIR) / name
        if p.exists():
            return {"model": name, "version": _file_digest(str(p), p.stat().st_mtime)}
    return {"model": None, "version": None}


def truth_cap(domain: str) -> Optional[float]:
    """RUL cap of run-to-failure domains (C-MAPSS: 125 cycles), None elsewhere."""
    from server.adapters.domain_profile import get_profile

    p = get_profile(domain)
    return float(p.rul_scale) if p.run_to_failure and p.rul_scale else None


def rul_band(mean: float, variance: float) -> Dict[str, float]:
    std = max(float(np.sqrt(max(variance, 0.0))), 1e-3)  # same floor as SimulationEngine
    return {"mean": float(mean), "std": std, "p10": max(0.0, float(mean) - Z90 * std), "p90": float(mean) + Z90 * std}


def _jsonable(obj: Any) -> Any:
    return json.loads(json.dumps(obj, default=lambda o: o.tolist() if hasattr(o, "tolist") else
                                 (o.isoformat() if isinstance(o, datetime) else str(o))))


# ---------------------------------------------------------------- trace storage


class MemoryTraceStore:
    def __init__(self):
        self.items: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def save(self, trace: Dict[str, Any]) -> None:
        with self._lock:
            self.items.append(trace)

    def find(self, domain: str, machine_id: str, ts: datetime) -> Optional[Dict[str, Any]]:
        with self._lock:
            hits = [t for t in self.items if t["domain"] == domain and t["machine_id"] == machine_id
                    and _parse_ts(t["ts"]) <= ts]
        return hits[-1] if hits else None

    def history(self, domain: str, machine_id: str, limit: int) -> List[Dict[str, Any]]:
        with self._lock:
            hits = [t for t in self.items if t["domain"] == domain and t["machine_id"] == machine_id]
        return sorted(hits, key=lambda t: t["ts"])[-limit:]

    def summary(self) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self.items)
        out: Dict[str, Dict[str, Any]] = {}
        for t in items:
            r = out.setdefault(t["domain"], {"domain": t["domain"], "traces": 0, "machines": set(), "lat": [], "last_trace": None})
            r["traces"] += 1
            r["machines"].add(t["machine_id"])
            r["lat"].append(t.get("total_latency_ms") or 0.0)
            r["last_trace"] = max(r["last_trace"] or t["ts"], t["ts"])
        return [{"domain": d, "traces": r["traces"], "machines": len(r["machines"]),
                 "mean_latency_ms": sum(r["lat"]) / len(r["lat"]), "last_trace": r["last_trace"]} for d, r in out.items()]


class DbTraceStore:
    def save(self, trace: Dict[str, Any]) -> None:
        from server.database import pool
        with pool.connection() as conn:
            conn.execute("INSERT INTO cognition_traces (time, domain, machine_id, trace) VALUES (%s, %s, %s, %s::jsonb)",
                         (trace["ts"], trace["domain"], trace["machine_id"], json.dumps(trace)))

    def find(self, domain: str, machine_id: str, ts: datetime) -> Optional[Dict[str, Any]]:
        from server.database import pool
        with pool.connection() as conn:
            row = conn.execute("SELECT trace FROM cognition_traces WHERE domain = %s AND machine_id = %s AND time <= %s "
                               "ORDER BY time DESC LIMIT 1", (domain, machine_id, ts)).fetchone()
        return row[0] if row else None

    def history(self, domain: str, machine_id: str, limit: int) -> List[Dict[str, Any]]:
        from server.database import pool
        with pool.connection() as conn:
            rows = conn.execute("SELECT trace FROM cognition_traces WHERE domain = %s AND machine_id = %s "
                                "ORDER BY time DESC LIMIT %s", (domain, machine_id, limit)).fetchall()
        return [r[0] for r in reversed(rows)]

    def summary(self) -> List[Dict[str, Any]]:
        from server.database import pool
        with pool.connection() as conn:
            rows = conn.execute("SELECT domain, count(*), count(DISTINCT machine_id), "
                                "avg((trace->>'total_latency_ms')::float), max(time) FROM cognition_traces "
                                "GROUP BY domain").fetchall()
        return [{"domain": r[0], "traces": r[1], "machines": r[2], "mean_latency_ms": r[3],
                 "last_trace": r[4].isoformat() if r[4] else None} for r in rows]


_STORE: Any = None


def _store():
    global _STORE
    if _STORE is None:
        _STORE = DbTraceStore()
    return _STORE


def _parse_ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- the trace


def _window_and_reading(domain: str, machine_id: str):
    """Window and latest reading from the streaming engine, or from a profiled (pushed) machine."""
    from server.atlas.domain_service import get_domain_service
    from server.ingest import get_ingest_service

    svc = get_domain_service()
    svc.ensure_registered(domain)
    engine, adapter = svc.get_engine(domain), svc.get_adapter(domain)
    window, reading = [], None
    if engine is not None:
        with engine._lock:
            window = [list(r) for r in engine._windows.get(machine_id, [])]
    if adapter is not None:
        try:
            reading = adapter.get_reading(machine_id)
        except Exception:
            reading = None
    if not window:
        ingest = get_ingest_service()
        try:
            if ingest.has_profile(machine_id):
                a = ingest.adapter(machine_id)
                adapter, window, reading = a, a.window(), a.get_reading(machine_id)
        except Exception:
            pass
    return window, reading, adapter


def build_trace(domain: str, machine_id: str, k: int, seed: int) -> Dict[str, Any]:
    import server.api as api
    from server.atlas.world_model import prepare_window

    if api._ace is None:
        raise HTTPException(status_code=503, detail="Cognition engines are not initialised")
    t_start = time.perf_counter()
    out: Dict[str, Dict[str, Any]] = {}

    def timed(name: str, fn):
        s = time.perf_counter()
        value = fn()
        out[name] = {"stage": name, "latency_ms": (time.perf_counter() - s) * 1000, "output": value}
        return value

    window, reading, adapter = timed("adapter", lambda: _window_and_reading(domain, machine_id))
    if not window:
        raise HTTPException(status_code=409, detail=f"No sensor window yet for {domain}/{machine_id}")
    feature_dim = len(window[0])
    model = api._ace.get_world_model(domain, feature_dim)
    if model is None:
        raise HTTPException(status_code=409, detail=f"No trained World Model for domain '{domain}' "
                                                    f"with {feature_dim} features (FUTURE-WORK for this domain)")
    seq_len = model.config.seq_len
    if len(window) < seq_len:
        raise HTTPException(status_code=409, detail=f"Warming up: {len(window)}/{seq_len} readings for {domain}/{machine_id}")
    np_window = np.asarray(window[-seq_len:], dtype=np.float32)
    status = getattr(reading, "adapter_status", None)
    quality = (reading.metadata or {}).get("quality") if reading is not None else None
    out["adapter"]["output"] = {
        "adapter": type(adapter).__name__ if adapter is not None else None,
        "adapter_version": getattr(adapter, "VERSION", "sdk-1.0"),
        "adapter_status": status,
        "raw": getattr(reading, "raw_features", None),
        "normalized": getattr(reading, "features", None),
        "quality": quality or ({f: ("SIMULATED" if status == "simulation" else "GOOD") for f in reading.features}
                               if reading is not None else None),
        "window": np_window.tolist(),
        "window_hash": window_hash(np_window),
    }

    pred = timed("world_model", lambda: model.predict(prepare_window(np_window, seq_len=seq_len, feature_dim=feature_dim)))
    sv = np.asarray(pred.state_vector, dtype=np.float32).reshape(-1)
    out["world_model"]["output"] = {"state_vector": sv.tolist(), "rul_raw": float(np.asarray(pred.rul_pred).reshape(-1)[0]),
                                    "attention": None if getattr(pred, "attn_weights", None) is None
                                    else np.asarray(pred.attn_weights).reshape(-1).tolist(),
                                    **model_ref(domain)}

    neighbors = timed("amkb", lambda: api._amkb.retrieve_similar(sv, k=k, domain=domain))
    out["amkb"]["output"] = {"k": k, "neighbors": [
        {"machine_id": n.machine_id, "cycle": n.cycle, "distance": n.similarity, "true_rul": n.true_rul,
         "event_type": n.event_type} for n in neighbors]}

    def dna_stage():
        dna = api._dna_engine.get_dna(domain, machine_id)
        if dna is None:
            return {"dna": None, "reason": "No stored Machine DNA for this unit", "siblings": [], "drift": None}
        sibs = api._dna_engine.retrieve_similar(np.asarray(dna), k=5, domain=domain)
        return {"dna": np.asarray(dna).tolist(), "drift": None, "drift_reason": "Drift against the first recorded trace: GET /api/admin/cognition/{id}/history",
                "siblings": [{"machine_id": getattr(s, "machine_id", None), "distance": getattr(s, "similarity", None)}
                             for s in sibs if getattr(s, "machine_id", None) != machine_id]}

    timed("machine_dna", dna_stage)

    cycle = int(getattr(reading, "cycle", 0) or 0)
    context = timed("adaptive_context", lambda: api._ace.build_context(
        domain=domain, machine_id=machine_id, current_cycle=cycle, current_window=np_window, k=k))
    meta = getattr(reading, "metadata", {}) or {}
    out["adaptive_context"]["output"] = {
        "predicted_rul": context.predicted_rul, "average_neighbor_rul": context.average_neighbor_rul,
        "neighbor_count": len(context.neighbors), "operational_context": getattr(reading, "operational_ctx", {}) or {},
        "synthetic_fields": meta.get("synthetic_fields", []),
    }

    variance = float(np.var([n.rul for n in context.neighbors])) if context.neighbors else 0.0

    def rul_stage():
        band = rul_band(context.predicted_rul, variance)
        truth = getattr(reading, "rul_label", None)
        cap = truth_cap(domain)
        capped = None if truth is None else (min(float(truth), cap) if cap else float(truth))
        # The model is trained on RUL capped at `cap` (piecewise-linear target), so error is measured against
        # the capped truth; the raw label stays visible as ground_truth.
        return {**band, "neighbor_variance": variance, "ground_truth": truth, "truth_cap": cap,
                "ground_truth_capped": capped, "error": None if capped is None else band["mean"] - capped}

    band = timed("rul", rul_stage)

    sims = timed("simulation", lambda: api._simulation_engine.simulate_actions(
        predicted_rul=context.predicted_rul, neighbor_variance=variance, seed=seed))
    n = api._simulation_engine.num_samples
    draws = np.random.default_rng(seed).normal(loc=context.predicted_rul, scale=band["std"], size=n)
    counts, edges = np.histogram(draws, bins=20)
    out["simulation"]["output"] = {"seed": seed, "n": n, "results": [dataclasses.asdict(s) for s in sims],
                                   "histogram": {"edges": edges.tolist(), "counts": counts.tolist()},
                                   "p_failure_now": float(np.mean(draws <= 0))}

    explanation = timed("explainability", lambda: api._explain_engine.explain(context, window=np_window, ace=api._ace))
    out["explainability"]["output"] = explanation.to_dict()

    decision = timed("decision", lambda: api._decision_graph.decide(
        simulation_results=sims, explanation=explanation, predicted_rul=context.predicted_rul, neighbor_variance=variance))
    d = dataclasses.asdict(decision)
    d.pop("explanation", None)  # already the explainability stage
    out["decision"]["output"] = d

    def learning_stage():
        try:
            history = api._learning_engine.get_learning_history(domain=domain, limit=10)
        except Exception as e:  # history lives in the database; the trace still returns
            history, err = [], str(e)
        else:
            err = None
        return {"history": history, "active_model": model_ref(domain), "error": err,
                "note": "Learning is batch/periodic retraining with a 3% promotion gate"}

    timed("learning", learning_stage)

    trace = {
        "domain": domain, "machine_id": machine_id, "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "replayed": False, "correlation_id": correlation_id.get(),
        "total_latency_ms": (time.perf_counter() - t_start) * 1000,
        "stages": [out[s] for s in STAGES],
    }
    return _jsonable(trace)


@router.get("/api/admin/cognition/{machine_id}/trace", summary="Every pipeline stage's output and latency for a machine; ?ts= replays a stored trace")
def get_trace(
    machine_id: str,
    domain: str = Query(..., pattern=r"^[A-Za-z0-9_.-]{1,64}$"),
    ts: Optional[str] = Query(None, max_length=40, description="Replay the stored trace at or before this ISO time"),
    k: int = Query(10, ge=1, le=50),
    seed: int = Query(42, ge=0, le=2**31 - 1, description="Monte Carlo seed (fixed so a trace is reproducible)"),
):
    if ts:
        try:
            when = _parse_ts(ts)
        except ValueError:
            raise HTTPException(status_code=422, detail="ts must be an ISO 8601 time")
        stored = _store().find(domain, machine_id, when)
        if stored is None:
            raise HTTPException(status_code=404, detail="No stored trace at or before that time")
        return {**stored, "replayed": True}

    trace = build_trace(domain, machine_id, k, seed)
    try:
        _store().save(trace)
    except Exception as e:
        trace["stored"] = False
        trace["store_error"] = str(e)
    by = {s["stage"]: s["output"] for s in trace["stages"]}
    audit(category="cognition", action="trace", target=f"{domain}/{machine_id}", latency_ms=trace["total_latency_ms"],
          details={"window_hash": by["adapter"]["window_hash"], "rul": {k_: by["rul"][k_] for k_ in ("mean", "p10", "p90")},
                   "seed": seed, "recommended_action": by["decision"]["recommended_action"],
                   "stage_latency_ms": {s["stage"]: round(s["latency_ms"], 3) for s in trace["stages"]}})
    return trace
