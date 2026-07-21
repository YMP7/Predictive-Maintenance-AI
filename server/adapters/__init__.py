"""
ATLAS Machine Adapter Layer
===========================
The ONLY domain-specific code in the ATLAS pipeline.
Every adapter normalizes its domain's telemetry into a single NormalizedReading
schema. Everything downstream (World Model, AMKB, Decision Graph, etc.) consumes
ONLY NormalizedReading — never raw domain data.

Available adapters:
  - CMAPSSAdapter    : NASA C-MAPSS turbofan benchmark dataset
  - LaptopAdapter    : Host machine via psutil + smartctl  [Month 6]
  - MobileAdapter    : Android device via Termux:API        [Month 6]
  - ServerAdapter    : Cloud VM via SSH + nvidia-smi        [Month 6]
"""

from server.adapters.base_adapter import (
    NormalizedReading,
    AdapterStatus,
    MachineAdapter,
    DatasetNotFoundError,
    AdapterConnectionError,
)
from server.adapters.cmapss_adapter import CMAPSSAdapter

__all__ = [
    "NormalizedReading",
    "AdapterStatus",
    "MachineAdapter",
    "DatasetNotFoundError",
    "AdapterConnectionError",
    "CMAPSSAdapter",
]
