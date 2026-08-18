"""
Server Adapter — ATLAS Machine Adapter Layer (Month 6)
======================================================
Provides telemetry from Linux Enterprise Servers / Cloud VMs via Paramiko SSH
(with automatic simulation fallback when no live VM host is configured).

Design Principle:
Validates the high-end server validation tier with 5 core infrastructure features
(CPU, Memory, Disk, Network IO, and GPU compute utilization).

NOTE ON HEALTH INDEX:
Following the Category B (Live Heterogeneous Hardware) taxonomy in base_adapter.py,
`health_index` represents an **Instantaneous Server Workload & Saturation Score**.
A production server under peak traffic is operating under high stress, not experiencing
irreversible structural mechanical failure.
"""

import logging
import math
import os
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import paramiko
    _HAS_PARAMIKO = True
except ImportError:
    paramiko = None
    _HAS_PARAMIKO = False

from server.adapters.base_adapter import (
    AdapterStatus,
    DomainType,
    MachineAdapter,
    NormalizedReading,
)

logger = logging.getLogger("ATLAS.ServerAdapter")


class ServerAdapter(MachineAdapter):
    """
    Adapter for Linux server telemetry via SSH.
    Connects to remote server via Paramiko when credentials are provided,
    otherwise provides high-fidelity enterprise server workload simulation.
    """

    # Canonical weight distributions (guaranteed to sum to 1.0)
    WEIGHTS_WITH_GPU: Dict[str, float] = {
        "cpu": 0.35,
        "memory": 0.25,
        "gpu": 0.20,
        "disk": 0.10,
        "network": 0.10,
    }

    WEIGHTS_NO_GPU: Dict[str, float] = {
        "cpu": 0.45,
        "memory": 0.35,
        "gpu": 0.00,
        "disk": 0.10,
        "network": 0.10,
    }

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 22,
        username: Optional[str] = None,
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        connect_timeout: float = 5.0,
        exec_timeout: float = 2.0,
        has_gpu: bool = False,
    ) -> None:
        super().__init__()
        self._host = host or os.environ.get("SSH_SERVER_HOST")
        self._port = int(port or os.environ.get("SSH_SERVER_PORT", 22))
        self._username = username or os.environ.get("SSH_SERVER_USER", "root")
        self._password = password or os.environ.get("SSH_SERVER_PASSWORD")
        self._key_filename = key_filename or os.environ.get("SSH_SERVER_KEY_FILE")
        self._connect_timeout = connect_timeout
        self._exec_timeout = exec_timeout
        self._has_gpu = has_gpu

        self._ssh_client: Optional[Any] = None
        self._is_live = False
        self._start_time = time.time()
        self._sim_step = 0

    @property
    def domain_id(self) -> str:
        return DomainType.SERVER.value

    @property
    def machine_ids(self) -> List[str]:
        return ["server_prod_1"]

    def _connect(self) -> None:
        """Attempt SSH handshake if host is configured and paramiko is available."""
        if not self._host:
            logger.info("[server] No SSH_SERVER_HOST configured. Running in simulation fallback mode.")
            self._is_live = False
            return

        if not _HAS_PARAMIKO:
            logger.info("[server] paramiko is not installed. Running in simulation fallback mode.")
            self._is_live = False
            return

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                key_filename=self._key_filename,
                timeout=self._connect_timeout,
                banner_timeout=self._connect_timeout,
            )
            self._ssh_client = client
            self._is_live = True
            logger.info(f"[server] Successfully connected via SSH to {self._host}:{self._port}")
        except Exception as e:
            logger.info(f"[server] SSH connection to {self._host} failed ({e}). Using simulation fallback.")
            self._is_live = False
            if self._ssh_client:
                try:
                    self._ssh_client.close()
                except Exception:
                    pass
                self._ssh_client = None

    def _disconnect(self) -> None:
        if self._ssh_client:
            try:
                self._ssh_client.close()
            except Exception:
                pass
            self._ssh_client = None
        self._is_live = False
        logger.info("[server] ServerAdapter disconnected.")

    def _exec_command(self, cmd: str) -> str:
        """Executes a command with a strict per-command timeout."""
        if not self._ssh_client:
            raise ConnectionError("SSH client not connected")
        _, stdout, stderr = self._ssh_client.exec_command(cmd, timeout=self._exec_timeout)
        return stdout.read().decode("utf-8").strip()

    def _poll_ssh_live(self) -> Dict[str, Any]:
        """Polls Linux /proc and system metrics via SSH."""
        # 1. CPU & Memory via vmstat / free
        mem_info = self._exec_command("free | grep Mem | awk '{print $2, $3}'")
        mem_nums = [float(x) for x in mem_info.split() if x.replace('.', '', 1).isdigit()]
        if len(mem_nums) >= 2 and mem_nums[0] > 0:
            memory_usage = min(1.0, max(0.0, mem_nums[1] / mem_nums[0]))
        else:
            memory_usage = 0.50

        # 2. CPU load via /proc/loadavg
        load_info = self._exec_command("cat /proc/loadavg | awk '{print $1}'")
        load_nums = [float(x) for x in load_info.split() if x.replace('.', '', 1).isdigit()]
        load_val = load_nums[0] if load_nums else 1.0
        cpu_usage = min(1.0, max(0.0, load_val / float(os.cpu_count() or 4.0)))

        # 3. Root disk usage via df
        df_info = self._exec_command("df -k / | tail -n 1 | awk '{print $2, $3}'")
        df_nums = [float(x) for x in df_info.split() if x.replace('.', '', 1).isdigit()]
        if len(df_nums) >= 2 and df_nums[0] > 0:
            disk_usage = min(1.0, max(0.0, df_nums[1] / df_nums[0]))
        else:
            disk_usage = 0.50

        # 4. Network RX/TX delta proxy
        net_info = self._exec_command("cat /proc/net/dev | grep -E 'eth0|ens' | head -n 1 | awk '{print $2, $10}'")
        net_usage = 0.35  # default baseline throughput proxy
        if net_info:
            net_nums = [float(x) for x in net_info.split() if x.replace('.', '', 1).isdigit()]
            if len(net_nums) >= 2:
                bytes_total = net_nums[0] + net_nums[1]
                # Normalized traffic intensity modulo typical 1Gbps capacity
                net_usage = min(1.0, (bytes_total % 100_000_000) / 100_000_000)

        # 5. GPU utilization if nvidia-smi exists
        gpu_util = 0.0
        has_gpu = False
        try:
            gpu_out = self._exec_command("nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits")
            if gpu_out and gpu_out.isdigit():
                gpu_util = float(gpu_out) / 100.0
                has_gpu = True
        except Exception:
            gpu_util = 0.0
            has_gpu = False

        return {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "disk_usage": disk_usage,
            "network_io_rate": net_usage,
            "gpu_utilization": gpu_util,
            "has_gpu": has_gpu,
        }

    def _generate_simulation_reading(self) -> Dict[str, Any]:
        """Generates realistic enterprise server multi-core & burst load metrics."""
        self._sim_step += 1
        t = self._sim_step * 0.15

        # Periodic server load pattern (e.g. diurnal traffic + microservice spikes)
        base_cpu = 0.25 + 0.35 * (0.5 + 0.5 * math.sin(t))
        spike_cpu = 0.30 if (self._sim_step % 15 == 0) else 0.0
        cpu_usage = min(1.0, max(0.05, base_cpu + spike_cpu))

        mem_usage = min(0.95, max(0.20, 0.45 + 0.20 * math.sin(t * 0.4) + 0.05 * (self._sim_step % 10) / 10.0))
        disk_usage = min(0.90, 0.60 + 0.001 * (self._sim_step % 100))
        net_io = min(1.0, max(0.05, 0.30 + 0.40 * math.sin(t * 1.2) + spike_cpu * 0.5))
        gpu_util = min(1.0, max(0.0, 0.50 * math.sin(t * 0.8))) if self._has_gpu else 0.0

        return {
            "cpu_usage": cpu_usage,
            "memory_usage": mem_usage,
            "disk_usage": disk_usage,
            "network_io_rate": net_io,
            "gpu_utilization": gpu_util,
            "has_gpu": self._has_gpu,
        }

    def compute_health_index(self, features: Dict[str, float], has_gpu: bool) -> float:
        """
        Computes the Category B Instantaneous Stress Score using normalized weights.
        Both formulas sum strictly to 1.0.
        """
        w = self.WEIGHTS_WITH_GPU if has_gpu else self.WEIGHTS_NO_GPU
        score = (
            w["cpu"] * features["cpu_usage"]
            + w["memory"] * features["memory_usage"]
            + w["gpu"] * features.get("gpu_utilization", 0.0)
            + w["disk"] * features["disk_usage"]
            + w["network"] * features["network_io_rate"]
        )
        return float(min(1.0, max(0.0, score)))

    def get_reading(self, machine_id: str) -> NormalizedReading:
        """
        Poll server metrics and return a NormalizedReading.

        Features:
          - cpu_usage        : [0, 1]
          - memory_usage     : [0, 1]
          - disk_usage       : [0, 1]
          - network_io_rate  : [0, 1]
          - gpu_utilization  : [0, 1]
        """
        if machine_id not in self.machine_ids:
            raise ValueError(f"Unknown machine_id: {machine_id}")

        status = AdapterStatus.SIMULATION.value
        raw_metrics: Dict[str, Any] = {}

        if self._is_live:
            try:
                raw_metrics = self._poll_ssh_live()
                status = AdapterStatus.LIVE.value
            except Exception as e:
                logger.warning(f"[server] SSH polling failed ({e}). Auto-transitioning to simulation fallback.")
                self._is_live = False
                if self._ssh_client:
                    try:
                        self._ssh_client.close()
                    except Exception:
                        pass
                    self._ssh_client = None
                raw_metrics = self._generate_simulation_reading()
        else:
            raw_metrics = self._generate_simulation_reading()

        has_gpu = bool(raw_metrics.get("has_gpu", False))

        features = {
            "cpu_usage": float(min(1.0, max(0.0, raw_metrics["cpu_usage"]))),
            "memory_usage": float(min(1.0, max(0.0, raw_metrics["memory_usage"]))),
            "disk_usage": float(min(1.0, max(0.0, raw_metrics["disk_usage"]))),
            "network_io_rate": float(min(1.0, max(0.0, raw_metrics["network_io_rate"]))),
            "gpu_utilization": float(min(1.0, max(0.0, raw_metrics["gpu_utilization"]))),
        }

        stress_score = self.compute_health_index(features, has_gpu)
        uptime_seconds = int(time.time() - self._start_time)

        return NormalizedReading(
            domain=self.domain_id,
            machine_id=machine_id,
            timestamp=NormalizedReading.timestamp_now(),
            health_index=stress_score,
            cycle=uptime_seconds,
            rul_label=None,
            features=features,
            raw_features=raw_metrics,
            operational_ctx={
                "tier": "enterprise_server",
                "transport": "ssh" if status == AdapterStatus.LIVE.value else "synthetic",
                "gpu_available": has_gpu,
            },
            metadata={
                "source": "paramiko" if status == AdapterStatus.LIVE.value else "synthetic_server",
                "simulated": (status == AdapterStatus.SIMULATION.value),
            },
            adapter_status=status,
        )
