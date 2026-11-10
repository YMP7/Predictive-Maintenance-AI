"""
ConfigurableAdapter: an SDK v1 MachineAdapter whose sensor mapping comes from a stored Sensor Profile
instead of code. All channel handling (units, scale/offset, valid ranges, sampling rate, quality
flags) lives here, inside the Adapter Layer; transports (HTTP, WebSocket, MQTT, CSV, manual) only
hand raw samples to `ingest()`.

Raw value -> SI value:   value = raw * scale + offset           (unit = the channel's SI unit)
SI value  -> feature:    (value - valid_min) / (valid_max - valid_min), clipped to [0, 1]
Quality per channel:     GOOD | OUT_OF_RANGE | FLATLINE | STALE (> 3 sampling intervals) | MISSING | SIMULATED
"""

from __future__ import annotations

import math
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from server.adapters.base_adapter import AdapterStatus, MachineAdapter, NormalizedReading, UnknownMachineError

VERSION = "1.0.0"
_ID = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"
FUTURE_TOLERANCE_S = 60.0
DEFAULT_MAX_AGE_S = 7 * 24 * 3600.0


class ChannelSpec(BaseModel):
    channel: str = Field(pattern=_ID, description="Name the device sends")
    feature: str = Field(pattern=_ID, description="Normalised feature name the pipeline sees")
    unit: str = Field(min_length=1, max_length=16, description="SI unit after scaling, e.g. K, A, Pa, m/s^2")
    scale: float = 1.0
    offset: float = 0.0
    valid_min: float
    valid_max: float
    sampling_hz: float = Field(1.0, gt=0, le=10000)
    health_weight: float = Field(0.0, ge=0)
    flatline_samples: int = Field(30, ge=0, le=100000, description="Identical consecutive samples before FLATLINE; 0 disables")
    part: Optional[str] = Field(None, pattern=_ID, description="3D part this channel is bound to")

    @model_validator(mode="after")
    def _range(self):
        if not (math.isfinite(self.valid_min) and math.isfinite(self.valid_max)) or self.valid_max <= self.valid_min:
            raise ValueError(f"{self.channel}: valid_max must be greater than valid_min")
        if not (math.isfinite(self.scale) and math.isfinite(self.offset)) or self.scale == 0:
            raise ValueError(f"{self.channel}: scale must be a non-zero finite number")
        return self


class SensorProfile(BaseModel):
    machine_id: str = Field(pattern=_ID)
    domain: str = Field(pattern=_ID)
    display_name: str = Field(min_length=1, max_length=120)
    simulated: bool = False
    window: int = Field(30, ge=1, le=512)
    channels: List[ChannelSpec] = Field(min_length=1, max_length=64)

    @field_validator("channels")
    @classmethod
    def _unique(cls, chans: List[ChannelSpec]):
        for attr in ("channel", "feature"):
            names = [getattr(c, attr) for c in chans]
            if len(names) != len(set(names)):
                raise ValueError(f"duplicate {attr} names in profile")
        return chans


@dataclass
class Reject:
    index: int
    reason: str
    channel: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"index": self.index, "channel": self.channel, "reason": self.reason}


@dataclass
class IngestResult:
    rows: List[Dict[str, Any]] = field(default_factory=list)
    rejects: List[Reject] = field(default_factory=list)
    accepted_samples: int = 0


def _parse_ts(value: Any, now: datetime) -> datetime:
    if value is None or value == "":
        return now
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)) and math.isfinite(value):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    elif isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}", value):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("invalid timestamp")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _number(raw: Any) -> Optional[float]:
    if isinstance(raw, bool):
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


class ConfigurableAdapter(MachineAdapter):
    """One machine, mapped by its Sensor Profile. Push-based: samples arrive through ingest()."""

    VERSION = VERSION

    def __init__(self, profile: SensorProfile):
        super().__init__()
        self.profile = profile
        self._by_channel = {c.channel: c for c in profile.channels}
        self._last: Dict[str, Dict[str, Any]] = {}  # channel -> {value, ts, quality, repeats}
        self._window: Deque[List[float]] = deque(maxlen=profile.window)

    # ---- SDK interface
    @property
    def domain_id(self) -> str:
        return self.profile.domain

    @property
    def machine_ids(self) -> List[str]:
        return [self.profile.machine_id]

    def _connect(self) -> None:
        self._status = AdapterStatus.SIMULATION if self.profile.simulated else AdapterStatus.LIVE

    def _disconnect(self) -> None:
        self._status = AdapterStatus.DISCONNECTED

    def get_reading(self, machine_id: str) -> NormalizedReading:
        if machine_id != self.profile.machine_id:
            raise UnknownMachineError(machine_id, self.domain_id)
        now = datetime.now(timezone.utc)
        quality = self.channel_quality(now)
        features = self._features()
        weights = {c.feature: c.health_weight for c in self.profile.channels if c.health_weight > 0}
        health = sum(features[f] * w for f, w in weights.items()) / sum(weights.values()) if weights else 0.0
        fresh = any(q not in ("STALE", "MISSING") for q in quality.values())
        if self.profile.simulated:
            status = AdapterStatus.SIMULATION.value
        else:
            status = AdapterStatus.LIVE.value if fresh else AdapterStatus.DISCONNECTED.value
        last_ts = max((s["ts"] for s in self._last.values()), default=now)
        return NormalizedReading(
            domain=self.domain_id,
            machine_id=machine_id,
            timestamp=last_ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            health_index=float(min(1.0, max(0.0, health))),
            cycle=0,
            rul_label=None,
            features=features,
            raw_features={c.channel: (self._last.get(c.channel) or {}).get("value") for c in self.profile.channels},
            operational_ctx={},
            metadata={"adapter": "ConfigurableAdapter", "adapter_version": VERSION, "quality": quality,
                      "units": {c.feature: c.unit for c in self.profile.channels},
                      "parts": {c.feature: c.part for c in self.profile.channels if c.part}},
            adapter_status=status,
        )

    # ---- profile-driven behaviour
    def _feature(self, spec: ChannelSpec, value: float) -> float:
        return min(1.0, max(0.0, (value - spec.valid_min) / (spec.valid_max - spec.valid_min)))

    def _features(self) -> Dict[str, float]:
        out = {}
        for c in self.profile.channels:
            last = self._last.get(c.channel)
            out[c.feature] = self._feature(c, last["value"]) if last else 0.0
        return out

    def channel_quality(self, now: Optional[datetime] = None) -> Dict[str, str]:
        now = now or datetime.now(timezone.utc)
        out = {}
        for c in self.profile.channels:
            last = self._last.get(c.channel)
            if last is None:
                out[c.channel] = "MISSING"
            elif (now - last["ts"]).total_seconds() > 3.0 / c.sampling_hz:
                out[c.channel] = "STALE"
            else:
                out[c.channel] = last["quality"]
        return out

    def window(self) -> List[List[float]]:
        return [list(r) for r in self._window]

    def ingest(self, samples: List[Any], *, now: Optional[datetime] = None,
               max_age_s: Optional[float] = DEFAULT_MAX_AGE_S) -> IngestResult:
        """Validate and normalise raw samples. Bad values are rejected with a reason; out-of-range values
        are kept and flagged. `max_age_s=None` allows historical backfill."""
        now = now or datetime.now(timezone.utc)
        result = IngestResult()
        parsed = []
        for i, s in enumerate(samples):
            raw = s if isinstance(s, dict) else getattr(s, "model_dump", lambda: {})()
            values = raw.get("values")
            if not isinstance(values, dict) or not values:
                result.rejects.append(Reject(i, "sample is empty"))
                continue
            try:
                ts = _parse_ts(raw.get("ts"), now)
            except (ValueError, OverflowError, OSError):
                result.rejects.append(Reject(i, "invalid timestamp"))
                continue
            age = (now - ts).total_seconds()
            if age < -FUTURE_TOLERANCE_S:
                result.rejects.append(Reject(i, "timestamp is in the future"))
                continue
            if max_age_s is not None and age > max_age_s:
                result.rejects.append(Reject(i, f"older than {int(max_age_s // 86400)} days; use CSV backfill"))
                continue
            parsed.append((i, ts, values))

        for i, ts, values in sorted(parsed, key=lambda p: p[1]):
            kept = 0
            for name, raw_value in values.items():
                spec = self._by_channel.get(name)
                if spec is None:
                    result.rejects.append(Reject(i, f"unknown channel '{name}'", name))
                    continue
                v = _number(raw_value)
                if v is None:
                    result.rejects.append(Reject(i, "not a finite number", name))
                    continue
                value = v * spec.scale + spec.offset
                quality = self._quality(spec, value, ts)
                result.rows.append({"ts": ts, "channel": name, "value": value, "unit": spec.unit, "quality": quality})
                kept += 1
            if kept:
                result.accepted_samples += 1
                self._window.append([self._features()[c.feature] for c in self.profile.channels])
        return result

    def _quality(self, spec: ChannelSpec, value: float, ts: datetime) -> str:
        prev = self._last.get(spec.channel)
        repeats = prev["repeats"] + 1 if prev and prev["value"] == value else 1
        if self.profile.simulated:
            q = "SIMULATED"
        elif not spec.valid_min <= value <= spec.valid_max:
            q = "OUT_OF_RANGE"
        elif spec.flatline_samples and repeats >= spec.flatline_samples:
            q = "FLATLINE"
        else:
            q = "GOOD"
        if prev is None or ts >= prev["ts"]:  # backfilled older samples never replace the latest value
            self._last[spec.channel] = {"value": value, "ts": ts, "quality": q, "repeats": repeats}
        return q
