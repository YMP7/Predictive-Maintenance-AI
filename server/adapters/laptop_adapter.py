"""
Laptop Adapter — ATLAS Machine Adapter Layer (Month 6)
======================================================
Provides live telemetry from the local Windows machine using psutil.

Design Principle:
This validates the adapter contract on a live system with a different
feature dimension (5 instead of 14) than C-MAPSS.

NOTE ON HEALTH INDEX:
For C-MAPSS, `health_index` represents degradation toward failure. 
For the Laptop domain, since there is no known physical failure point, 
`health_index` is redefined as an **Instantaneous Stress Score** (a weighted 
sum of CPU and Memory saturation). A laptop under heavy load isn't necessarily 
degrading, it is just busy. This semantic inconsistency must be addressed 
before cross-domain transfer studies.
"""

import logging
import time
from typing import List, Optional

import psutil

from server.adapters.base_adapter import (
    AdapterStatus,
    DomainType,
    MachineAdapter,
    NormalizedReading,
)

logger = logging.getLogger("ATLAS.LaptopAdapter")


class LaptopAdapter(MachineAdapter):
    """
    Live telemetry adapter for the local laptop.
    Uses psutil to gather OS-level metrics.
    """

    def __init__(self) -> None:
        super().__init__()
        self._start_time = time.time()
        
    @property
    def domain_id(self) -> str:
        return DomainType.LAPTOP.value

    @property
    def machine_ids(self) -> List[str]:
        return ["laptop_local"]

    def _connect(self) -> None:
        """Initialize psutil (e.g., priming the CPU percent call)."""
        psutil.cpu_percent()
        logger.info("[laptop] LaptopAdapter initialized and primed psutil.")

    def _disconnect(self) -> None:
        logger.info("[laptop] LaptopAdapter disconnected.")

    def get_reading(self, machine_id: str) -> NormalizedReading:
        """
        Poll live OS metrics and return a NormalizedReading.
        
        Features:
          - cpu_usage        : [0, 1]
          - memory_usage     : [0, 1]
          - disk_usage       : [0, 1]
          - battery_percent  : [0, 1]
          - is_charging      : [0, 1]
        """
        if machine_id not in self.machine_ids:
            raise ValueError(f"Unknown machine_id: {machine_id}")

        # 1. Gather raw metrics
        raw_cpu = psutil.cpu_percent(interval=None)  # Non-blocking if primed
        raw_mem = psutil.virtual_memory()
        
        # Disk usage for the system drive (C:\ on Windows, / on Linux)
        try:
            # We assume C:\\ since user is on Windows, but fallback to / if missing
            import os
            drive = "C:\\" if os.name == "nt" else "/"
            raw_disk = psutil.disk_usage(drive)
            disk_percent = raw_disk.percent
        except Exception:
            disk_percent = 0.0

        raw_battery = psutil.sensors_battery()
        if raw_battery:
            batt_percent = raw_battery.percent
            is_charging = 1.0 if raw_battery.power_plugged else 0.0
        else:
            # Desktop fallback
            batt_percent = 100.0
            is_charging = 1.0

        # 2. Normalize features to [0, 1]
        features = {
            "cpu_usage": raw_cpu / 100.0,
            "memory_usage": raw_mem.percent / 100.0,
            "disk_usage": disk_percent / 100.0,
            "battery_percent": batt_percent / 100.0,
            "is_charging": is_charging,
        }

        # 3. Compute Instantaneous Stress Score (Proxy for health_index)
        # 70% CPU, 30% Memory
        stress_score = (0.7 * features["cpu_usage"]) + (0.3 * features["memory_usage"])

        # 4. Raw features for debugging
        raw_features = {
            "cpu_percent": raw_cpu,
            "memory_percent": raw_mem.percent,
            "disk_percent": disk_percent,
            "battery_percent": batt_percent,
            "is_charging": is_charging,
        }

        uptime_seconds = int(time.time() - self._start_time)

        return NormalizedReading(
            domain=self.domain_id,
            machine_id=machine_id,
            timestamp=NormalizedReading.timestamp_now(),
            health_index=stress_score,
            cycle=uptime_seconds,
            rul_label=None,
            features=features,
            raw_features=raw_features,
            operational_ctx={"os": "windows"},
            metadata={"source": "psutil"},
            adapter_status=AdapterStatus.LIVE.value,
        )
