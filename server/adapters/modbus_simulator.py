"""
server/adapters/modbus_simulator.py — Standalone Industrial Modbus TCP Simulator
================================================================================
A self-contained Modbus TCP server for local development, integration testing,
and automated adapter conformance validation without physical hardware.

Simulates typical multi-channel telemetry for an industrial rotating asset
(e.g., CNC milling spindle, slurry pump, or centrifugal compressor) across
holding registers (Function Code 03 / 16).

Features:
  - Ephemeral port support (port=0 binds to any free OS port).
  - Configurable register layout with sensible industrial defaults.
  - Three distinct operating regimes: 'idle', 'nominal', and 'degraded'.
  - Micro-jitter simulation for realistic temporal variance (DEF-007 compliance).
  - Context manager interface for clean pytest fixture lifecycle management.
"""

from __future__ import annotations

import logging
import random
import socket
import threading
import time
import warnings
from typing import Dict, List, Optional, Tuple

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="pymodbus.*")
    from pymodbus.client import ModbusTcpClient
    from pymodbus.datastore import (
        ModbusDeviceContext,
        ModbusSequentialDataBlock,
        ModbusServerContext,
    )
    from pymodbus.server import ServerStop, StartTcpServer

logger = logging.getLogger(__name__)


# Standard default register mapping (6 holding registers starting at address 0 / 40001):
# 40001 (reg 0): Spindle Temperature [deci-degC: 450 = 45.0 °C]
# 40002 (reg 1): Vibration Peak [milli-mm/s: 1250 = 1.250 mm/s]
# 40003 (reg 2): Motor Current [deci-Amps: 142 = 14.2 A]
# 40004 (reg 3): Spindle Speed [RPM: 3600 = 3600 RPM]
# 40005 (reg 4): Bearing Oil Pressure [centi-bar: 320 = 3.20 bar]
# 40006 (reg 5): Power Factor [x100: 88 = 0.88]
DEFAULT_SIMULATOR_REGISTERS: List[int] = [450, 1250, 142, 3600, 320, 88]


class ModbusSimulator:
    """
    In-process or standalone Modbus TCP simulation server.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        unit_id: int = 1,
        machine_id: str = "cnc_spindle_01",
        initial_registers: Optional[List[int]] = None,
    ):
        self.host = host
        self.requested_port = port
        self.port = port
        self.unit_id = unit_id
        self.machine_id = machine_id
        self._running = False
        self._server_thread: Optional[threading.Thread] = None
        self._cycle = 0
        self._state = "nominal"

        self._registers = list(initial_registers or DEFAULT_SIMULATOR_REGISTERS)
        # Pad datastore to 100 registers to accommodate expanded configurations
        padded_size = max(100, len(self._registers) + 20)
        padded_values = self._registers + [0] * (padded_size - len(self._registers))

        # ModbusSequentialDataBlock(1, ...) sets up 1-based indexing internally mapping to 0
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            self._datablock = ModbusSequentialDataBlock(1, padded_values)
            store = ModbusDeviceContext(
                di=self._datablock,
                co=self._datablock,
                hr=self._datablock,
                ir=self._datablock,
            )
            self._context = ModbusServerContext(devices=store, single=True)

    @staticmethod
    def _find_free_port() -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("", 0))
        free_p = sock.getsockname()[1]
        sock.close()
        return free_p

    def start(self, timeout: float = 5.0) -> int:
        """
        Starts the Modbus TCP server in a background daemon thread.
        Returns the bound TCP port.
        """
        if self._running:
            return self.port

        if self.requested_port == 0:
            self.port = self._find_free_port()
        else:
            self.port = self.requested_port

        self._server_thread = threading.Thread(
            target=StartTcpServer,
            kwargs={"context": self._context, "address": (self.host, self.port)},
            daemon=True,
            name=f"ModbusSimulator-{self.port}",
        )
        self._server_thread.start()
        self._running = True

        # Poll port until accepting connections
        start_time = time.time()
        connected = False
        while time.time() - start_time < timeout:
            try:
                probe = socket.create_connection((self.host, self.port), timeout=0.2)
                probe.close()
                connected = True
                break
            except (ConnectionRefusedError, OSError):
                time.sleep(0.05)

        if not connected:
            self._running = False
            raise RuntimeError(f"ModbusSimulator failed to bind or listen on {self.host}:{self.port}")

        logger.info(f"ModbusSimulator running on {self.host}:{self.port} (Unit ID {self.unit_id})")
        return self.port

    def stop(self) -> None:
        """Stops the Modbus TCP server and releases socket resources."""
        if not self._running:
            return
        self._running = False
        try:
            ServerStop()
        except Exception:
            pass
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=1.5)
        self._server_thread = None
        logger.info(f"ModbusSimulator stopped on {self.host}:{self.port}")

    def set_registers(self, values: List[int], start_address: int = 0) -> None:
        """
        Directly writes holding register values into the simulator datastore.
        Uses a local client write to ensure thread-safe datastore synchronization.
        """
        if not self._running:
            # Update internal model if not running
            for i, v in enumerate(values):
                idx = start_address + i
                if idx < len(self._registers):
                    self._registers[idx] = v
            return

        client = ModbusTcpClient(self.host, port=self.port, timeout=1.0)
        try:
            if client.connect():
                client.write_registers(address=start_address, values=values)
                for i, v in enumerate(values):
                    idx = start_address + i
                    if idx < len(self._registers):
                        self._registers[idx] = v
        finally:
            client.close()

    def set_state(self, state: str) -> None:
        """
        Sets machine operational state:
          - 'idle': Low speed, cool motor, minimal vibration.
          - 'nominal': Standard production operating load and temperature.
          - 'degraded': Rising thermal load, severe harmonic vibration, high current.
        """
        self._state = state
        if state == "idle":
            # Temp: 25.0 C, Vib: 0.15 mm/s, Curr: 2.0 A, RPM: 0, Press: 1.0 bar, PF: 0.40
            self.set_registers([250, 150, 20, 0, 100, 40])
        elif state == "nominal":
            # Temp: 45.0 C, Vib: 1.25 mm/s, Curr: 14.2 A, RPM: 3600, Press: 3.2 bar, PF: 0.88
            self.set_registers([450, 1250, 142, 3600, 320, 88])
        elif state == "degraded":
            # Temp: 78.0 C, Vib: 5.60 mm/s, Curr: 22.0 A, RPM: 3520, Press: 1.8 bar, PF: 0.72
            self.set_registers([780, 5600, 220, 3520, 180, 72])
        else:
            raise ValueError(f"Unknown simulator state: '{state}'. Choose 'idle', 'nominal', or 'degraded'.")

    def step(self) -> None:
        """
        Advances the simulation cycle by 1 step, applying realistic physical micro-perturbations
        to avoid static latent representation collapse (DEF-007 compliance).
        """
        self._cycle += 1
        noise = [
            int(random.gauss(0, 3)),   # temp deci-C (+/- 0.3 C)
            int(random.gauss(0, 25)),  # vib milli-mm/s (+/- 0.025 mm/s)
            int(random.gauss(0, 2)),   # current deci-A (+/- 0.2 A)
            int(random.gauss(0, 12)),  # rpm (+/- 12 RPM)
            int(random.gauss(0, 3)),   # press centi-bar (+/- 0.03 bar)
            int(random.gauss(0, 1)),   # pf (+/- 0.01)
        ]
        perturbed = [max(0, b + n) for b, n in zip(self._registers[:6], noise)]
        self.set_registers(perturbed)

    def __enter__(self) -> ModbusSimulator:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
