"""
Base Adapter Interface — ATLAS Machine Adapter Layer
=====================================================
Defines the NormalizedReading schema (the single contract between all domain
adapters and all downstream ATLAS subsystems) and the abstract MachineAdapter
interface every adapter must implement.

Design principle: the adapter is the ONLY place domain-specific knowledge lives.
Once data crosses into NormalizedReading, the rest of the pipeline is domain-agnostic.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DatasetNotFoundError(FileNotFoundError):
    """Raised when a required dataset file (e.g., C-MAPSS) is missing."""

    def __init__(self, dataset: str, expected_path: str, instructions: str = ""):
        self.dataset = dataset
        self.expected_path = expected_path
        msg = (
            f"Dataset '{dataset}' not found at: {expected_path}\n"
            f"{instructions}"
        )
        super().__init__(msg)


class AdapterConnectionError(ConnectionError):
    """Raised when a live adapter (Termux, SSH, etc.) cannot reach its source."""

    def __init__(self, domain: str, reason: str, fallback_active: bool = False):
        self.domain = domain
        self.fallback_active = fallback_active
        suffix = " → simulation fallback is active." if fallback_active else ""
        super().__init__(f"[{domain}] Cannot connect: {reason}{suffix}")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AdapterStatus(str, Enum):
    """Lifecycle status of a domain adapter."""
    LIVE        = "live"        # Reading from a real source in real-time
    STREAMING   = "streaming"   # Replaying a static dataset (C-MAPSS)
    SIMULATION  = "simulation"  # Fallback: generating synthetic data
    DISCONNECTED = "disconnected"  # Source unreachable, not yet in fallback


class DomainType(str, Enum):
    CMAPSS  = "cmapss"
    LAPTOP  = "laptop"
    MOBILE  = "mobile"
    SERVER  = "server"


# ---------------------------------------------------------------------------
# NormalizedReading — the single pipeline schema
# ---------------------------------------------------------------------------

@dataclass
class NormalizedReading:
    """
    The canonical telemetry unit consumed by all ATLAS subsystems.

    Every domain adapter must produce NormalizedReadings. No subsystem
    (World Model, AMKB, Decision Graph, etc.) touches raw domain data.

    Fields
    ------
    domain          : Which adapter produced this reading (DomainType value)
    machine_id      : Unique ID within the domain  (e.g., "unit_1", "laptop_local")
    timestamp       : UTC ISO-8601 string
    health_index    : Normalised degradation in [0.0, 1.0]. 0 = fresh, 1 = failed.
                      The adapter is responsible for computing this from domain signals.
    cycle           : For time-series datasets: the current cycle / step index.
                      For live adapters: total uptime seconds (or 0 if unavailable).
    rul_label       : Ground-truth RUL (cycles/days) if known (C-MAPSS training set).
                      None for live adapters.
    features        : Dict of normalised sensor features in [0, 1] where possible.
                      Keys are domain-specific but consistently named within a domain.
    raw_features    : Original un-normalised sensor values (for diagnostics only).
    operational_ctx : Operational settings / context labels (C-MAPSS op-settings,
                      device power-mode, load profile, etc.)
    metadata        : Adapter-level metadata (firmware version, model, etc.)
    adapter_status  : The adapter's live/streaming/simulation status at read time.
    """

    domain:          str
    machine_id:      str
    timestamp:       str
    health_index:    float                 # [0, 1]
    cycle:           int                   # time-step or uptime-proxy
    rul_label:       Optional[float]       # ground truth (datasets only)
    features:        Dict[str, float]      # normalised sensor dict
    raw_features:    Dict[str, Any]        # raw values for debugging
    operational_ctx: Dict[str, Any]        # domain context labels
    metadata:        Dict[str, Any]        # adapter bookkeeping
    adapter_status:  str = AdapterStatus.LIVE.value

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def feature_vector(self) -> List[float]:
        """Returns features as an ordered list (consistent key order)."""
        return [self.features[k] for k in sorted(self.features)]

    @classmethod
    def timestamp_now(cls) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain":          self.domain,
            "machine_id":      self.machine_id,
            "timestamp":       self.timestamp,
            "health_index":    round(self.health_index, 6),
            "cycle":           self.cycle,
            "rul_label":       self.rul_label,
            "features":        self.features,
            "raw_features":    self.raw_features,
            "operational_ctx": self.operational_ctx,
            "metadata":        self.metadata,
            "adapter_status":  self.adapter_status,
        }


# ---------------------------------------------------------------------------
# Abstract MachineAdapter
# ---------------------------------------------------------------------------

class MachineAdapter(abc.ABC):
    """
    Abstract base class for all ATLAS domain adapters.

    Subclasses must implement:
      - domain_id    : str property
      - machine_ids  : List[str] property
      - _connect()   : Establish connection / load dataset
      - _disconnect(): Release resources
      - get_reading(machine_id) -> NormalizedReading

    The adapter contract guarantees that get_reading() always returns a valid
    NormalizedReading — it must never raise for a healthy instantiated adapter.
    Errors inside get_reading() must be caught and surfaced as either:
      - A simulation-fallback reading (AdapterStatus.SIMULATION), or
      - An AdapterConnectionError (only acceptable during connect/disconnect)
    """

    def __init__(self) -> None:
        self._connected: bool = False
        self._status: AdapterStatus = AdapterStatus.DISCONNECTED

    # ------------------------------------------------------------------
    # Properties (must be implemented by subclasses)
    # ------------------------------------------------------------------

    @property
    @abc.abstractmethod
    def domain_id(self) -> str:
        """The domain this adapter represents (DomainType value)."""
        ...

    @property
    @abc.abstractmethod
    def machine_ids(self) -> List[str]:
        """All machine IDs this adapter can produce readings for."""
        ...

    @property
    def status(self) -> AdapterStatus:
        return self._status

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Connect / load dataset. Safe to call multiple times."""
        if not self._connected:
            self._connect()
            self._connected = True

    def disconnect(self) -> None:
        """Release resources."""
        if self._connected:
            self._disconnect()
            self._connected = False
            self._status = AdapterStatus.DISCONNECTED

    @abc.abstractmethod
    def _connect(self) -> None: ...

    @abc.abstractmethod
    def _disconnect(self) -> None: ...

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_reading(self, machine_id: str) -> NormalizedReading:
        """
        Return the next NormalizedReading for the given machine_id.
        Must ALWAYS return a valid reading — fallback to simulation if needed.
        """
        ...

    def get_all_readings(self) -> List[NormalizedReading]:
        """Convenience: get one reading per machine in one call."""
        return [self.get_reading(mid) for mid in self.machine_ids]

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def describe(self) -> Dict[str, Any]:
        """Summary dict for the /api/atlas/domains endpoint."""
        return {
            "domain_id":   self.domain_id,
            "machine_ids": self.machine_ids,
            "status":      self._status.value,
            "connected":   self._connected,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} domain={self.domain_id} status={self._status.value}>"
