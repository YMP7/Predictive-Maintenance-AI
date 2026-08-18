"""
Mobile Adapter — ATLAS Machine Adapter Layer (Month 6)
======================================================
Provides telemetry from mobile Android devices via Termux:API (or realistic
simulation fallback when the physical device is not currently bridged).

Design Principle:
Validates cross-domain generalization on mobile hardware telemetry with 5
battery/thermal/compute dimensions.

NOTE ON HEALTH INDEX:
For the Mobile domain, `health_index` represents a **Thermal & Battery Stress Score**
(a composite of battery temperature, CPU load, memory utilization, and discharge depth).
Like the Laptop domain, this is an instantaneous operational stress score rather than
physical irreversible structural failure.
"""

import json
import logging
import math
import os
import time
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

from server.adapters.base_adapter import (
    AdapterStatus,
    DomainType,
    MachineAdapter,
    NormalizedReading,
)

logger = logging.getLogger("ATLAS.MobileAdapter")


class MobileAdapter(MachineAdapter):
    """
    Adapter for mobile Android telemetry.
    Connects to Termux:API server/bridge when reachable, or generates realistic
    synthetic mobile telemetry cycles under simulation fallback.
    """

    def __init__(self, endpoint_url: Optional[str] = None) -> None:
        super().__init__()
        self._endpoint_url = endpoint_url or os.environ.get("TERMUX_API_URL", "http://127.0.0.1:8088")
        self._start_time = time.time()
        self._is_live = False
        self._sim_step = 0

    @property
    def domain_id(self) -> str:
        return DomainType.MOBILE.value

    @property
    def machine_ids(self) -> List[str]:
        return ["mobile_device_1"]

    def _connect(self) -> None:
        """Probe the Termux endpoint to determine if live connection is possible."""
        try:
            req = urllib.request.Request(
                f"{self._endpoint_url}/battery",
                headers={"User-Agent": "ATLAS-MobileAdapter/1.0"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    self._is_live = True
                    logger.info(f"[mobile] Connected to live Termux:API at {self._endpoint_url}")
                    return
        except Exception as e:
            logger.info(f"[mobile] Termux endpoint unavailable ({e}). Using simulation fallback.")

        self._is_live = False

    def _disconnect(self) -> None:
        logger.info("[mobile] MobileAdapter disconnected.")

    def _poll_termux_live(self) -> Dict[str, Any]:
        """Fetch real battery and thermal status from Termux:API."""
        req = urllib.request.Request(
            f"{self._endpoint_url}/battery",
            headers={"User-Agent": "ATLAS-MobileAdapter/1.0"}
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data

    def _generate_simulation_reading(self) -> Dict[str, float]:
        """Generate realistic synthetic mobile telemetry."""
        self._sim_step += 1
        t = self._sim_step * 0.1

        # Periodic battery discharge & thermal curve
        battery_level = max(0.05, 0.95 - (0.005 * (self._sim_step % 180)))
        temp_c = 28.0 + 10.0 * (0.5 + 0.5 * math.sin(t)) + (0.05 * (self._sim_step % 20))
        cpu = 0.15 + 0.45 * max(0.0, math.sin(t * 1.5))
        mem = 0.55 + 0.15 * math.sin(t * 0.3)
        current_ma = 200.0 + 600.0 * cpu

        return {
            "battery_percent": battery_level * 100.0,
            "temperature_c": temp_c,
            "cpu_percent": cpu * 100.0,
            "memory_percent": mem * 100.0,
            "current_ma": current_ma,
            "is_plugged": False,
        }

    def get_reading(self, machine_id: str) -> NormalizedReading:
        """
        Poll mobile telemetry and return a NormalizedReading.

        Features:
          - battery_level       : [0, 1]
          - battery_temp        : [0, 1] (normalized 20C - 60C)
          - battery_current     : [0, 1] (normalized 0 - 2000mA)
          - memory_used_percent : [0, 1]
          - cpu_usage           : [0, 1]
        """
        if machine_id not in self.machine_ids:
            raise ValueError(f"Unknown machine_id: {machine_id}")

        status = AdapterStatus.SIMULATION.value
        raw_data = {}

        if self._is_live:
            try:
                raw_data = self._poll_termux_live()
                status = AdapterStatus.LIVE.value
            except Exception as e:
                logger.warning(f"[mobile] Live poll failed ({e}), falling back to simulation.")
                self._is_live = False
                raw_data = self._generate_simulation_reading()
        else:
            raw_data = self._generate_simulation_reading()

        # Extract & Normalize
        batt_pct = float(raw_data.get("battery_percent", raw_data.get("percentage", 80.0)))
        temp_c = float(raw_data.get("temperature_c", raw_data.get("temperature", 30.0)))
        cpu_pct = float(raw_data.get("cpu_percent", 25.0))
        mem_pct = float(raw_data.get("memory_percent", 50.0))
        current_ma = float(raw_data.get("current_ma", raw_data.get("current", 350.0)))

        battery_level = min(1.0, max(0.0, batt_pct / 100.0))
        # Normalize temp from [20C, 60C] -> [0, 1]
        battery_temp = min(1.0, max(0.0, (temp_c - 20.0) / 40.0))
        # Normalize current from [0, 2000mA] -> [0, 1]
        battery_current = min(1.0, max(0.0, abs(current_ma) / 2000.0))
        memory_used = min(1.0, max(0.0, mem_pct / 100.0))
        cpu_usage = min(1.0, max(0.0, cpu_pct / 100.0))

        features = {
            "battery_level": battery_level,
            "battery_temp": battery_temp,
            "battery_current": battery_current,
            "memory_used_percent": memory_used,
            "cpu_usage": cpu_usage,
        }

        # Thermal & Battery composite stress score
        stress_score = (
            (0.40 * battery_temp)
            + (0.30 * cpu_usage)
            + (0.20 * memory_used)
            + (0.10 * (1.0 - battery_level))
        )

        uptime_seconds = int(time.time() - self._start_time)

        return NormalizedReading(
            domain=self.domain_id,
            machine_id=machine_id,
            timestamp=NormalizedReading.timestamp_now(),
            health_index=stress_score,
            cycle=uptime_seconds,
            rul_label=None,
            features=features,
            raw_features=raw_data,
            operational_ctx={"platform": "android", "source": "termux" if status == AdapterStatus.LIVE.value else "synthetic"},
            metadata={"source": "Termux:API", "simulated": (status == AdapterStatus.SIMULATION.value)},
            adapter_status=status,
        )
