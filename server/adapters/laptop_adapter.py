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
    Live telemetry adapter for the local laptop (Windows host).
    Gathers OS-level and hardware metrics across compute, memory, storage,
    network, battery, and scheduler subsystems via psutil.
    """

    def __init__(self) -> None:
        super().__init__()
        self._start_time = time.time()
        
        # Rate-delta tracking for throughput and frequency metrics
        self._last_poll_time: Optional[float] = None
        self._last_disk_io: Optional[Any] = None
        self._last_net_io: Optional[Any] = None
        self._last_cpu_stats: Optional[Any] = None
        
    @property
    def domain_id(self) -> str:
        return DomainType.LAPTOP.value

    @property
    def machine_ids(self) -> List[str]:
        return ["laptop_local"]

    def _connect(self) -> None:
        """Initialize psutil (e.g., priming CPU percent and rate counters)."""
        psutil.cpu_percent()
        try:
            self._last_disk_io = psutil.disk_io_counters()
            self._last_net_io = psutil.net_io_counters()
            self._last_cpu_stats = psutil.cpu_stats()
            self._last_poll_time = time.time()
        except Exception as e:
            logger.warning("[laptop] Error priming hardware counters: %s", e)
        logger.info("[laptop] LaptopAdapter initialized and primed psutil.")

    def _disconnect(self) -> None:
        logger.info("[laptop] LaptopAdapter disconnected.")

    def get_reading(self, machine_id: str) -> NormalizedReading:
        """
        Poll live OS metrics and return a NormalizedReading.
        
        Features (15 Genuine Measured Hardware/Kernel Sensors + 1 Model Estimate):
          1.  cpu_usage             : [0, 1] - Total CPU saturation ratio (psutil)
          2.  cpu_frequency         : [0, 1] - Current clock frequency vs max hardware turbo
          3.  cpu_core_p90          : [0, 1] - 90th percentile load across all logical cores
          4.  memory_usage          : [0, 1] - Virtual memory / RAM utilization ratio
          5.  swap_usage            : [0, 1] - Pagefile / swap allocation ratio
          6.  disk_usage            : [0, 1] - C:\\ volume storage capacity consumed ratio
          7.  disk_read_throughput  : [0, 1] - Read bandwidth (normalized to 100 MB/s sustained ceiling)
          8.  disk_write_throughput : [0, 1] - Write bandwidth (normalized to 100 MB/s sustained ceiling)
          9.  disk_iops_rate        : [0, 1] - Combined I/O operations rate (normalized to 5000 IOPS)
          10. network_throughput    : [0, 1] - Combined net I/O bandwidth (normalized to 50 MB/s ceiling)
          11. battery_percent       : [0, 1] - Battery fuel gauge state of charge ratio
          12. is_charging           : {0, 1} - Binary AC power supply status (1=AC, 0=Battery)
          13. process_activity      : [0, 1] - Active system process count (normalized to 600 procs)
          14. context_switches      : [0, 1] - Kernel context switch rate (normalized to 1M switches/s)
          15. interrupt_rate        : [0, 1] - Hardware interrupt rate (normalized to 100k interrupts/s)
          16. thermal_headroom      : [0, 1] - [ESTIMATED] Thermodynamic heuristic die temperature
                                              (35C idle baseline to 95C junction limit)
        """
        if machine_id not in self.machine_ids:
            raise ValueError(f"Unknown machine_id: {machine_id}")

        now = time.time()
        dt = max(now - (self._last_poll_time or (now - 1.0)), 0.05)
        self._last_poll_time = now

        # 1. Gather raw CPU and Core Metrics
        raw_cpu = psutil.cpu_percent(interval=None)  # Non-blocking if primed
        per_cpu = psutil.cpu_percent(percpu=True) or [raw_cpu]
        cpu_p90 = sorted(per_cpu)[int(len(per_cpu) * 0.9)] if per_cpu else raw_cpu

        cpu_freq = psutil.cpu_freq()
        freq_current = cpu_freq.current if cpu_freq else 2400.0
        freq_max = max(cpu_freq.max if (cpu_freq and cpu_freq.max and cpu_freq.max > 0) else 3600.0, freq_current)

        # 2. Gather Memory & Storage
        raw_mem = psutil.virtual_memory()
        raw_swap = psutil.swap_memory()
        
        import os
        drive = "C:\\" if os.name == "nt" else "/"
        try:
            raw_disk = psutil.disk_usage(drive)
            disk_percent = raw_disk.percent
        except Exception:
            disk_percent = 0.0

        # 3. Gather Battery Metrics
        raw_battery = psutil.sensors_battery()
        if raw_battery:
            batt_percent = raw_battery.percent
            is_charging = 1.0 if raw_battery.power_plugged else 0.0
            secs_left = raw_battery.secsleft
        else:
            batt_percent = 100.0
            is_charging = 1.0
            secs_left = -2

        # 4. Gather Rate-Delta Hardware Counters (Disk, Net, Kernel)
        curr_disk_io = psutil.disk_io_counters()
        if curr_disk_io and self._last_disk_io:
            read_bytes_delta = max(0, curr_disk_io.read_bytes - self._last_disk_io.read_bytes)
            write_bytes_delta = max(0, curr_disk_io.write_bytes - self._last_disk_io.write_bytes)
            ops_delta = max(0, (curr_disk_io.read_count + curr_disk_io.write_count) - 
                               (self._last_disk_io.read_count + self._last_disk_io.write_count))
            disk_read_kbps = read_bytes_delta / (1024.0 * dt)
            disk_write_kbps = write_bytes_delta / (1024.0 * dt)
            disk_iops = ops_delta / dt
        else:
            disk_read_kbps = 0.0
            disk_write_kbps = 0.0
            disk_iops = 0.0
        self._last_disk_io = curr_disk_io

        curr_net_io = psutil.net_io_counters()
        if curr_net_io and self._last_net_io:
            net_bytes_delta = max(0, (curr_net_io.bytes_recv + curr_net_io.bytes_sent) - 
                                     (self._last_net_io.bytes_recv + self._last_net_io.bytes_sent))
            net_recv_kbps = max(0, curr_net_io.bytes_recv - self._last_net_io.bytes_recv) / (1024.0 * dt)
            net_sent_kbps = max(0, curr_net_io.bytes_sent - self._last_net_io.bytes_sent) / (1024.0 * dt)
            net_total_kbps = net_bytes_delta / (1024.0 * dt)
        else:
            net_recv_kbps = 0.0
            net_sent_kbps = 0.0
            net_total_kbps = 0.0
        self._last_net_io = curr_net_io

        curr_cpu_stats = psutil.cpu_stats()
        if curr_cpu_stats and self._last_cpu_stats:
            ctx_delta = max(0, curr_cpu_stats.ctx_switches - self._last_cpu_stats.ctx_switches)
            irq_delta = max(0, curr_cpu_stats.interrupts - self._last_cpu_stats.interrupts)
            ctx_switches_per_sec = ctx_delta / dt
            interrupts_per_sec = irq_delta / dt
        else:
            ctx_switches_per_sec = 10000.0
            interrupts_per_sec = 2000.0
        self._last_cpu_stats = curr_cpu_stats

        process_count = len(psutil.pids())

        # 5. Thermodynamic Heuristic Estimate (Explicitly Labeled Model Estimate)
        # Windows user-mode psutil cannot query thermistors without Administrator ring-0 drivers.
        # Modeled from CPU core saturation, clock frequency boost ratio, and memory bus churn.
        estimated_temp_c = round(
            35.0 + (45.0 * (raw_cpu / 100.0)) + 
            (12.0 * max(0.0, (freq_current / freq_max) - 0.5)) + 
            (5.0 * max(0.0, (raw_mem.percent / 100.0) - 0.5)), 
            1
        )
        # Normalized between 35°C idle baseline and 95°C junction thermal throttle ceiling
        thermal_norm = round(min(1.0, max(0.0, (estimated_temp_c - 35.0) / 60.0)), 4)

        # 6. Normalize All 16 Features to [0, 1] with Stated Engineering Ceilings
        features = {
            # Canonical 5 features (must remain exact to preserve World Model tensor contract)
            "cpu_usage": round(min(1.0, max(0.0, raw_cpu / 100.0)), 4),
            "memory_usage": round(min(1.0, max(0.0, raw_mem.percent / 100.0)), 4),
            "disk_usage": round(min(1.0, max(0.0, disk_percent / 100.0)), 4),
            "battery_percent": round(min(1.0, max(0.0, batt_percent / 100.0)), 4),
            "is_charging": is_charging,
            
            # Additional 10 Genuine Measured Hardware / Kernel Channels
            "cpu_frequency": round(min(1.0, max(0.0, freq_current / freq_max)), 4),
            "cpu_core_p90": round(min(1.0, max(0.0, cpu_p90 / 100.0)), 4),
            "swap_usage": round(min(1.0, max(0.0, raw_swap.percent / 100.0)), 4),
            "disk_read_throughput": round(min(1.0, max(0.0, (disk_read_kbps * 1024.0) / 104_857_600.0)), 4),  # 100 MB/s SATA/NVMe sustained ceiling
            "disk_write_throughput": round(min(1.0, max(0.0, (disk_write_kbps * 1024.0) / 104_857_600.0)), 4), # 100 MB/s SATA/NVMe sustained ceiling
            "disk_iops_rate": round(min(1.0, max(0.0, disk_iops / 5000.0)), 4),                                # 5000 IOPS client SSD 4K saturation
            "network_throughput": round(min(1.0, max(0.0, (net_total_kbps * 1024.0) / 52_428_800.0)), 4),     # 50 MB/s 1GbE/Wi-Fi 6 telemetry ceiling
            "process_activity": round(min(1.0, max(0.0, process_count / 600.0)), 4),                            # 600 processes high-density dev ceiling
            "context_switches": round(min(1.0, max(0.0, ctx_switches_per_sec / 1_000_000.0)), 4),              # 1M/s multithread scheduler contention
            "interrupt_rate": round(min(1.0, max(0.0, interrupts_per_sec / 100_000.0)), 4),                    # 100k/s peripheral hardware IRQ stress
            
            # 1 Derived Metric (Explicitly Flagged as Heuristic Estimate)
            "thermal_headroom": thermal_norm,
        }

        # 7. Compute Instantaneous Stress Score (Invariant: only consumes canonical cpu & mem)
        stress_score = round((0.7 * features["cpu_usage"]) + (0.3 * features["memory_usage"]), 4)

        # 8. Un-normalized Raw Features (with explicit labeling on derived thermal estimate)
        raw_features = {
            "cpu_percent": raw_cpu,
            "cpu_freq_mhz": freq_current,
            "cpu_freq_max_mhz": freq_max,
            "core_count_logical": len(per_cpu),
            "core_count_physical": psutil.cpu_count(logical=False) or len(per_cpu),
            "per_cpu_percent": per_cpu,
            "memory_percent": raw_mem.percent,
            "memory_available_gb": round(raw_mem.available / (1024.0**3), 2),
            "memory_total_gb": round(raw_mem.total / (1024.0**3), 2),
            "swap_percent": raw_swap.percent,
            "disk_percent": disk_percent,
            "disk_read_kbps": round(disk_read_kbps, 2),
            "disk_write_kbps": round(disk_write_kbps, 2),
            "disk_iops": round(disk_iops, 1),
            "net_recv_kbps": round(net_recv_kbps, 2),
            "net_sent_kbps": round(net_sent_kbps, 2),
            "battery_percent": batt_percent,
            "is_charging": is_charging,
            "battery_secs_left": secs_left,
            "process_count": process_count,
            "ctx_switches_per_sec": round(ctx_switches_per_sec, 0),
            "interrupts_per_sec": round(interrupts_per_sec, 0),
            # Derived Heuristic with Explicit Companion Metadata
            "estimated_thermal_c": estimated_temp_c,
            "is_estimated": True,
            "thermal_is_estimated": True,
            "estimation_method": "thermodynamic_heuristic",
        }

        uptime_seconds = int(time.time() - self._start_time)

        operational_ctx = {
            "os": "Windows 11" if os.name == "nt" else "Linux",
            "processor": f"x86_64 ({psutil.cpu_count(logical=False) or len(per_cpu)} Phys Cores, {len(per_cpu)} Threads)",
            "total_ram_gb": round(raw_mem.total / (1024.0**3), 1),
            "storage_drive": drive,
            "power_source": "AC Plugged" if is_charging == 1.0 else "Battery",
            "source": "Local OS Host (psutil Telemetry)",
            "total_hardware_sensors": 15,
            "total_derived_metrics": 1,
        }

        metadata = {
            "source": "psutil",
            "simulated": False,
            "total_channels": len(features),
            "has_derived_thermal": True,
        }

        return NormalizedReading(
            domain=self.domain_id,
            machine_id=machine_id,
            timestamp=NormalizedReading.timestamp_now(),
            health_index=stress_score,
            cycle=uptime_seconds,
            rul_label=None,
            features=features,
            raw_features=raw_features,
            operational_ctx=operational_ctx,
            metadata=metadata,
            adapter_status=AdapterStatus.LIVE.value,
        )
