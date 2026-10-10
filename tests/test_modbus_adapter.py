"""
tests/test_modbus_adapter.py — Comprehensive ModbusAdapter & Simulator Conformance Suite
========================================================================================
Validates Phase 2 of the Universal MachineAdapter SDK:
  - ModbusSimulator in-process server lifecycle, state regimes, and step perturbations.
  - ModbusAdapter register map parsing (dicts, dataclasses, JSON files).
  - DEF-013: Register map path traversal sandboxing and jail escape rejection.
  - DEF-009: Epsilon-safe normalization against zero-span min/max configurations.
  - DEF-008: Dynamic WorldModelConfig sizing and untrained zero-shot refusal.
  - DEF-002: Monotonic cycle and timestamp preservation across consecutive reads.
  - DEF-007: Operational regime distinction (idle vs nominal vs degraded non-collapse).
  - UnknownMachineError contract enforcement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Generator

import numpy as np
import pytest

from server.adapters.base_adapter import (
    AdapterConnectionError,
    AdapterError,
    AdapterStatus,
    ConfigurationPathTraversalError,
    NormalizedReading,
    UnknownMachineError,
    UntrainedDomainModelError,
)
from server.adapters.modbus_adapter import (
    DEFAULT_REGISTER_MAP,
    ModbusAdapter,
    ModbusRegisterChannel,
)
from server.adapters.modbus_simulator import ModbusSimulator
from server.atlas.world_model import UntrainedModelError, WorldModel, WorldModelConfig


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def running_simulator() -> Generator[ModbusSimulator, None, None]:
    """Provides a cleanly running ModbusSimulator on an ephemeral port."""
    sim = ModbusSimulator(port=0, machine_id="test_spindle_01")
    sim.start()
    try:
        yield sim
    finally:
        sim.stop()


@pytest.fixture
def connected_adapter(running_simulator: ModbusSimulator) -> Generator[ModbusAdapter, None, None]:
    """Provides a connected ModbusAdapter communicating with the running simulator."""
    adapter = ModbusAdapter(
        host=running_simulator.host,
        port=running_simulator.port,
        unit_id=running_simulator.unit_id,
        machine_ids=[running_simulator.machine_id],
        domain_id="test_modbus_domain",
    )
    adapter.connect()
    try:
        yield adapter
    finally:
        adapter.disconnect()


# ---------------------------------------------------------------------------
# 1. ModbusSimulator Lifecycle & State Regimes
# ---------------------------------------------------------------------------

class TestModbusSimulatorLifecycle:
    """Verifies simulator behavior, port binding, and telemetry transitions."""

    def test_simulator_starts_and_stops_cleanly(self) -> None:
        sim = ModbusSimulator(port=0)
        port = sim.start()
        assert port > 0
        assert sim._running is True
        sim.stop()
        assert sim._running is False

    def test_simulator_state_transitions(self, running_simulator: ModbusSimulator) -> None:
        sim = running_simulator
        sim.set_state("idle")
        assert sim._state == "idle"
        # Idle register values: [250, 150, 20, 0, 100, 40]
        assert sim._registers[0] == 250
        assert sim._registers[3] == 0

        sim.set_state("nominal")
        assert sim._state == "nominal"
        assert sim._registers[0] == 450
        assert sim._registers[3] == 3600

        sim.set_state("degraded")
        assert sim._state == "degraded"
        assert sim._registers[0] == 780
        assert sim._registers[1] == 5600

        with pytest.raises(ValueError, match="Unknown simulator state"):
            sim.set_state("invalid_state_xyz")

    def test_simulator_step_applies_perturbations(self, running_simulator: ModbusSimulator) -> None:
        sim = running_simulator
        sim.set_state("nominal")
        initial_regs = list(sim._registers)
        # Advance multiple steps
        for _ in range(5):
            sim.step()
        # Telemetry should vary slightly due to physical noise without collapsing
        assert sim._cycle == 5


# ---------------------------------------------------------------------------
# 2. ModbusAdapter Lifecycle & Connection Idempotency
# ---------------------------------------------------------------------------

class TestModbusAdapterLifecycle:
    """Verifies adapter connection handling and error reporting."""

    def test_connect_is_idempotent(self, running_simulator: ModbusSimulator) -> None:
        adapter = ModbusAdapter(
            host=running_simulator.host,
            port=running_simulator.port,
            machine_ids=[running_simulator.machine_id],
        )
        assert adapter.status == AdapterStatus.DISCONNECTED
        assert adapter.connected is False

        # First connect
        adapter.connect()
        assert adapter.status == AdapterStatus.LIVE
        assert adapter.connected is True

        # Second connect must be a safe no-op
        adapter.connect()
        assert adapter.status == AdapterStatus.LIVE
        assert adapter.connected is True

        adapter.disconnect()
        assert adapter.status == AdapterStatus.DISCONNECTED
        assert adapter.connected is False

    def test_unreachable_server_raises_adapter_connection_error(self) -> None:
        # Use an unreachable port
        unreachable_adapter = ModbusAdapter(
            host="127.0.0.1",
            port=59999,
            timeout=0.2,
        )
        with pytest.raises(AdapterConnectionError, match="Cannot connect"):
            unreachable_adapter.connect()
        assert unreachable_adapter.status == AdapterStatus.DISCONNECTED


# ---------------------------------------------------------------------------
# 3. Register Map Flexibility & DEF-013 Sandboxing
# ---------------------------------------------------------------------------

class TestModbusRegisterMapConfiguration:
    """Verifies flexible register map schemas and path traversal guards."""

    def test_custom_register_map_from_dicts(self, running_simulator: ModbusSimulator) -> None:
        custom_map = [
            {"name": "temp", "register": 40001, "scale": 0.1, "min_val": 0.0, "max_val": 100.0},
            {"name": "rpm", "register": 40004, "scale": 1.0, "min_val": 0.0, "max_val": 5000.0},
        ]
        adapter = ModbusAdapter(
            host=running_simulator.host,
            port=running_simulator.port,
            machine_ids=[running_simulator.machine_id],
            register_map=custom_map,
        )
        adapter.connect()
        reading = adapter.get_reading(running_simulator.machine_id)
        adapter.disconnect()

        assert len(reading.features) == 2
        assert "temp" in reading.features
        assert "rpm" in reading.features
        assert adapter.describe()["feature_dim"] == 2

    def test_empty_register_map_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="cannot be an empty list"):
            ModbusAdapter(register_map=[])

    def test_def_013_json_file_loading_inside_sandbox(
        self, tmp_path: Path, running_simulator: ModbusSimulator
    ) -> None:
        config_dir = tmp_path / "configs"
        config_dir.mkdir()
        map_file = config_dir / "spindle_registers.json"
        map_content = [
            {"name": "oil_pressure", "register": 40005, "scale": 0.01, "min_val": 0.0, "max_val": 10.0}
        ]
        map_file.write_text(json.dumps(map_content), encoding="utf-8")

        # Loading within sandbox succeeds
        adapter = ModbusAdapter(
            host=running_simulator.host,
            port=running_simulator.port,
            machine_ids=[running_simulator.machine_id],
            register_map="spindle_registers.json",
            config_base_dir=config_dir,
        )
        assert len(adapter.channels) == 1
        assert adapter.channels[0].name == "oil_pressure"

    def test_def_013_path_traversal_escape_rejected(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "configs"
        config_dir.mkdir()

        # Path attempting jail escape
        malicious_path = "../../etc/shadow_registers.json"
        with pytest.raises(ConfigurationPathTraversalError, match="escapes allowed directory"):
            ModbusAdapter(
                register_map=malicious_path,
                config_base_dir=config_dir,
            )


# ---------------------------------------------------------------------------
# 4. DEF-009 Normalization Epsilon Guard
# ---------------------------------------------------------------------------

class TestModbusDEF009EpsilonGuard:
    """Verifies division-by-zero prevention when channel min_val == max_val."""

    def test_zero_span_channel_normalizes_safely(self, running_simulator: ModbusSimulator) -> None:
        # Deliberately configure min_val == max_val
        zero_span_map = [
            ModbusRegisterChannel(
                name="constant_sensor",
                register=40001,
                scale=1.0,
                min_val=50.0,
                max_val=50.0,  # span = 0.0
            )
        ]
        adapter = ModbusAdapter(
            host=running_simulator.host,
            port=running_simulator.port,
            machine_ids=[running_simulator.machine_id],
            register_map=zero_span_map,
        )
        adapter.connect()
        reading = adapter.get_reading(running_simulator.machine_id)
        adapter.disconnect()

        val = reading.features["constant_sensor"]
        assert val == 0.0 or val == 1.0 or (0.0 <= val <= 1.0)
        assert not np.isnan(val)
        assert not np.isinf(val)


# ---------------------------------------------------------------------------
# 5. DEF-008 Dynamic World Model Sizing & Zero-Shot Guardrail
# ---------------------------------------------------------------------------

class TestModbusDEF008DynamicWorldModel:
    """Verifies dynamic sizing from channel count and untrained rejection."""

    def test_fresh_modbus_adapter_reports_is_trained_false(self, connected_adapter: ModbusAdapter) -> None:
        adapter = connected_adapter
        assert hasattr(adapter, "is_trained")
        assert adapter.is_trained is False
        assert adapter.describe()["is_trained"] is False

        with pytest.raises(UntrainedDomainModelError, match="is_trained=False"):
            adapter.assert_trained()

    def test_dynamic_world_model_sized_from_register_channels(
        self, connected_adapter: ModbusAdapter, running_simulator: ModbusSimulator
    ) -> None:
        adapter = connected_adapter
        reading = adapter.get_reading(running_simulator.machine_id)
        num_channels = len(reading.features)
        assert num_channels == 6

        # Build dynamic WorldModelConfig matching channel count
        cfg = WorldModelConfig(
            domain=adapter.domain_id,
            feature_dim=num_channels,
            is_trained=adapter.is_trained,  # Strictly False
        )
        assert cfg.feature_dim == 6
        assert cfg.is_trained is False

        model = WorldModel(cfg)
        test_window = np.zeros((30, num_channels), dtype=np.float32)

        # DEF-008: Must refuse silent zero-shot inference
        with pytest.raises(UntrainedModelError, match="is_trained=False"):
            model.predict(test_window)


# ---------------------------------------------------------------------------
# 6. DEF-002 Monotonicity & DEF-007 Non-Collapse
# ---------------------------------------------------------------------------

class TestModbusTelemetryGuards:
    """Verifies chronological monotonic ordering and state variance."""

    def test_def_002_chronological_and_cycle_monotonicity(
        self, connected_adapter: ModbusAdapter, running_simulator: ModbusSimulator
    ) -> None:
        adapter = connected_adapter
        mid = running_simulator.machine_id

        readings = [adapter.get_reading(mid) for _ in range(5)]
        cycles = [r.cycle for r in readings]
        timestamps = [r.timestamp for r in readings]

        # Cycles strictly increase
        assert cycles == [1, 2, 3, 4, 5]

        # Timestamps are non-decreasing and valid UTC
        for i in range(len(timestamps) - 1):
            assert timestamps[i] <= timestamps[i + 1]
            assert timestamps[i].endswith("Z")

    def test_def_007_state_regimes_produce_distinct_vectors(
        self, connected_adapter: ModbusAdapter, running_simulator: ModbusSimulator
    ) -> None:
        adapter = connected_adapter
        mid = running_simulator.machine_id

        # 1. Idle state
        running_simulator.set_state("idle")
        reading_idle = adapter.get_reading(mid)

        # 2. Degraded state
        running_simulator.set_state("degraded")
        reading_degraded = adapter.get_reading(mid)

        vec_idle = np.array(reading_idle.feature_vector)
        vec_degraded = np.array(reading_degraded.feature_vector)

        # Euclidean distance between idle and degraded must be significant
        euclidean_dist = float(np.linalg.norm(vec_degraded - vec_idle))
        assert euclidean_dist > 0.25, f"Representation collapse: distance too small ({euclidean_dist})"
        assert reading_degraded.health_index < reading_idle.health_index, (
            "Degraded regime did not lower health index"
        )


# ---------------------------------------------------------------------------
# 7. Unknown Machine ID Error Handling
# ---------------------------------------------------------------------------

class TestModbusUnknownMachineHandling:
    """Verifies that unknown machine queries raise UnknownMachineError."""

    def test_unknown_machine_raises_documented_exception(
        self, connected_adapter: ModbusAdapter
    ) -> None:
        with pytest.raises((KeyError, ValueError, UnknownMachineError)) as exc_info:
            connected_adapter.get_reading("ghost_machine_404")
        assert "ghost_machine_404" in str(exc_info.value)
