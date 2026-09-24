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
    DomainType,
    MachineAdapter,
    AdapterError,
    UnknownMachineError,
    ConfigurationPathTraversalError,
    UntrainedDomainModelError,
    DatasetNotFoundError,
    AdapterConnectionError,
)
from server.adapters.cmapss_adapter import CMAPSSAdapter
from server.adapters.laptop_adapter import LaptopAdapter
from server.adapters.mobile_adapter import MobileAdapter
from server.adapters.server_adapter import ServerAdapter
from server.adapters.modbus_adapter import ModbusAdapter, ModbusRegisterChannel
from server.adapters.modbus_simulator import ModbusSimulator

__all__ = [
    "NormalizedReading",
    "AdapterStatus",
    "DomainType",
    "MachineAdapter",
    "AdapterError",
    "UnknownMachineError",
    "ConfigurationPathTraversalError",
    "UntrainedDomainModelError",
    "DatasetNotFoundError",
    "AdapterConnectionError",
    "CMAPSSAdapter",
    "LaptopAdapter",
    "MobileAdapter",
    "ServerAdapter",
    "ModbusAdapter",
    "ModbusRegisterChannel",
    "ModbusSimulator",
]
