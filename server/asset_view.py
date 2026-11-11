"""
TwinFrame: one machine's current state shaped for the 3D Asset View.

The frame carries the part list, each bound channel (normalised value, raw value and
unit, quality code) and a per-part relative load, so the client draws parts without
knowing anything about the domain. Sources: the domain service snapshot for the four
ATLAS domains, the ConfigurableAdapter for machines onboarded with a sensor profile.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from server.adapters.asset_profiles import ASSET_PROFILES, AssetProfile, get_asset_profile, profile_dict

router = APIRouter()
_ID = r"^[A-Za-z0-9_.:-]{1,64}$"
SNAPSHOT_DOMAINS = ("cmapss", "laptop", "mobile", "server")
STALE_AFTER_S = 30.0
ELEVATED, HIGH = 0.75, 0.9


def _num(x: Any) -> Optional[float]:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _age_s(ts: Optional[str], now: datetime) -> Optional[float]:
    if not ts:
        return None
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (now - t).total_seconds()


def channel_load(value: Optional[float], direction: int) -> Optional[float]:
    """How far a normalised channel sits toward its load/degradation end, 0..1; None for neutral channels."""
    if value is None or direction == 0:
        return None
    v = min(1.0, max(0.0, value))
    return v if direction > 0 else 1.0 - v


def part_state(load: Optional[float], monitored: bool, has_values: bool = False) -> str:
    if not monitored:
        return "unmonitored"
    if load is None:
        # readings on neutral channels only (a speed, a pressure): watched, but no load to rank
        return "normal" if has_values else "nodata"
    return "high" if load >= HIGH else "elevated" if load >= ELEVATED else "normal"


def build_frame(domain: str, machine_id: str, profile: AssetProfile, *, features: Dict[str, Any],
                raw: Dict[str, Any], quality: Dict[str, str], parts_override: Dict[str, str],
                units_override: Dict[str, str], ts: Optional[str], status: Optional[str],
                adapter_status: Optional[str], health_index: Optional[float], rul: Optional[dict],
                rul_note: Optional[str] = None, rul_pending: bool = False) -> dict:
    channels: List[dict] = []
    for feature, b in profile.channels.items():
        value = _num(features.get(feature))
        q = quality.get(feature, "GOOD") if value is not None else "MISSING"
        channels.append({
            "feature": feature,
            "label": b.label,
            "part": parts_override.get(feature, b.part),
            "dir": b.dir,
            "value": value,
            "raw": _num(raw.get(feature)),
            "unit": units_override.get(feature, b.unit),
            "quality": q,
            "load": channel_load(value, b.dir) if q != "MISSING" else None,
        })
    parts = []
    for p in profile.parts:
        mine = [c for c in channels if c["part"] == p.id]
        loads = [c["load"] for c in mine if c["load"] is not None]
        load = max(loads) if loads else None
        parts.append({"id": p.id, "name": p.name, "detail": p.detail,
                      "channels": [c["feature"] for c in mine], "load": load,
                      "state": part_state(load, bool(mine), any(c["quality"] != "MISSING" for c in mine))})
    return {
        "domain": domain,
        "machine_id": machine_id,
        "kind": profile.kind,
        "label": profile.label,
        "ts": ts,
        "status": status,
        "adapter_status": adapter_status,
        "simulated": adapter_status == "simulation",
        "health_index": health_index,
        "rul": rul,
        "rul_note": None if rul is not None else (rul_note or profile.rul_note),
        # True when a model exists and is only waiting for its first full window.
        "rul_pending": rul is None and rul_pending,
        "attribution": profile.attribution,
        "spin": _num(features.get(profile.spin)) if profile.spin else None,
        "spin_label": profile.channels[profile.spin].label if profile.spin else None,
        "parts": parts,
        "channels": channels,
    }


def snapshot_rul(profile: AssetProfile, snap: dict) -> Optional[dict]:
    if snap.get("rul_cycles") is None:
        return None
    return {"value": snap["rul_cycles"], "unit": profile.rul_unit, "uncertainty": snap.get("uncertainty"),
            "normalized": snap.get("normalized_rul"), "confidence": snap.get("confidence"),
            "using_lstm": snap.get("using_lstm")}


def frame_from_snapshot(domain: str, machine_id: str, profile: AssetProfile, snap: dict, now: datetime) -> dict:
    age = _age_s(snap.get("timestamp"), now)
    adapter_status = snap.get("adapter_status")
    q = "SIMULATED" if adapter_status == "simulation" else "STALE" if age is None or age > STALE_AFTER_S else "GOOD"
    return build_frame(domain, machine_id, profile, features=snap.get("features") or {},
                       raw=snap.get("raw_features") or {}, quality={f: q for f in profile.channels},
                       parts_override={}, units_override={}, ts=snap.get("timestamp"),
                       status=snap.get("status"), adapter_status=adapter_status,
                       health_index=snap.get("health_index"), rul=snapshot_rul(profile, snap))


def frame_from_ingest(machine_id: str) -> Optional[dict]:
    from server.ingest import UnknownMachine, get_ingest_service

    svc = get_ingest_service()
    if not svc.has_profile(machine_id):
        return None
    try:
        adapter = svc.adapter(machine_id)
    except UnknownMachine:
        return None
    sp = adapter.profile
    profile = get_asset_profile(sp.domain)
    if profile is None:
        raise HTTPException(status_code=422, detail=f"No 3D asset profile for domain '{sp.domain}'")
    reading = adapter.get_reading(machine_id)
    try:
        from server.atlas.profiled_inference import profiled_rul

        rul, rul_note, rul_pending = profiled_rul(adapter)
    except Exception:  # a model problem must not take the live readings off the screen
        rul, rul_note, rul_pending = None, "The RUL model could not be run for this machine.", False
    by_feature = {c.feature: c for c in sp.channels}
    quality = {f: reading.metadata["quality"].get(c.channel, "MISSING") for f, c in by_feature.items()}
    if sp.simulated:
        quality = {f: ("SIMULATED" if q not in ("MISSING", "STALE") else q) for f, q in quality.items()}
    raw = {f: reading.raw_features.get(c.channel) for f, c in by_feature.items()}
    return build_frame(sp.domain, machine_id, profile, features=reading.features, raw=raw, quality=quality,
                       parts_override={f: c.part for f, c in by_feature.items() if c.part},
                       units_override={f: c.unit for f, c in by_feature.items() if c.unit},
                       ts=reading.timestamp, status=None, adapter_status=reading.adapter_status,
                       health_index=reading.health_index, rul=rul, rul_note=rul_note, rul_pending=rul_pending)


@router.get("/api/atlas/domain/{domain}/profile", tags=["assets"],
            summary="Parts of this machine type and which channel binds to which part")
def asset_profile(domain: str):
    p = get_asset_profile(domain)
    if p is None:
        raise HTTPException(status_code=404, detail=f"No 3D asset profile for domain '{domain}'")
    return profile_dict(domain, p)


@router.get("/api/assets", tags=["assets"], summary="Every machine the 3D Asset View can show")
def list_assets():
    from server.atlas.domain_service import get_domain_service
    from server.ingest import get_ingest_service

    svc = get_domain_service()
    out = []
    for domain in SNAPSHOT_DOMAINS:
        p = ASSET_PROFILES[domain]
        for s in sorted(svc.get_domain_snapshots(domain), key=lambda s: str(s.get("machine_id"))):
            out.append({"domain": domain, "machine_id": s["machine_id"], "kind": p.kind, "label": p.label,
                        "status": s.get("status"), "health_index": s.get("health_index"),
                        "simulated": s.get("adapter_status") == "simulation",
                        "rul": snapshot_rul(p, s), "ts": s.get("timestamp")})
    try:
        profiles = get_ingest_service().profiles.list()
    except Exception:  # profile DB down: still list the domain machines
        profiles = []
    for sp in profiles:
        p = get_asset_profile(sp.domain)
        if p is not None:
            rul = None
            try:
                from server.atlas.profiled_inference import profiled_rul

                rul = profiled_rul(get_ingest_service().adapter(sp.machine_id))[0]
            except Exception:
                pass
            out.append({"domain": sp.domain, "machine_id": sp.machine_id, "kind": p.kind,
                        "label": sp.display_name or p.label, "status": None, "health_index": None,
                        "simulated": sp.simulated, "rul": rul, "ts": None})
    return {"assets": out}


@router.get("/api/assets/{machine_id}/frame", tags=["assets"], summary="TwinFrame for the 3D Asset View")
def asset_frame(machine_id: str, domain: str = Query(..., pattern=_ID)):
    if not re.fullmatch(_ID, machine_id):
        raise HTTPException(status_code=422, detail="Invalid machine id")
    if domain in SNAPSHOT_DOMAINS:
        from server.atlas.domain_service import get_domain_service

        svc = get_domain_service()
        svc.ensure_registered(domain)
        snap = svc.get_snapshot(domain, machine_id)
        if snap is None:
            raise HTTPException(status_code=404, detail=f"No data yet for {domain}/{machine_id}")
        return frame_from_snapshot(domain, machine_id, ASSET_PROFILES[domain], snap, datetime.now(timezone.utc))
    frame = frame_from_ingest(machine_id)
    if frame is None or frame["domain"] != domain:
        raise HTTPException(status_code=404, detail=f"Unknown asset {domain}/{machine_id}")
    return frame


@router.get("/api/admin/sensor-profiles/template", tags=["admin"],
            summary="A ready sensor profile for machine types with a known register map (Modbus today)")
def sensor_profile_template_route(domain: str = Query(..., pattern=_ID), machine_id: str = Query(..., pattern=_ID),
                                  simulated: bool = False):
    from server.adapters.asset_profiles import sensor_profile_template

    t = sensor_profile_template(domain, machine_id, simulated)
    if t is None:
        raise HTTPException(status_code=404, detail=f"No template for {domain}; map the channels by hand")
    return t
