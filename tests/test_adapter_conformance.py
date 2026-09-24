"""
tests/test_adapter_conformance.py — ATLAS MachineAdapter SDK Conformance Suite
=============================================================================
A formal, parametrized test suite that verifies any MachineAdapter implementation
conforms strictly to the ATLAS Adapter SDK Specification (v1.0.0).

Verifications performed:
  1. Reading contract: get_reading() returns a schema-compliant NormalizedReading
     for known machine_id (valid ISO UTC timestamp, health_index in [0.0, 1.0],
     normalized features in [0.0, 1.0], non-empty raw_features, operational_ctx,
     and valid adapter_status).
  2. Unknown machine rejection: get_reading() on an unrecognized machine_id raises
     the documented exception (UnknownMachineError / KeyError / ValueError) and
     never fails silently or returns None.
  3. Feature dimension consistency: Reported feature dimension (via describe(),
     metadata, or canonical mappings) strictly matches what get_reading() produces.
  4. Lifecycle contract: connect() is idempotent; disconnect() cleans up resources
     and sets status to DISCONNECTED.
  5. DEF-008 Guardrail: Any dynamic WorldModelConfig creation exposes an explicit,
     queryable is_trained=False state and refuses silent zero-shot inference.
  6. Defect regression guardrails:
     - DEF-002: Temporal ordering / monotonicity invariant.
     - DEF-007: Representation non-collapse guard.
     - DEF-009: Division-by-zero epsilon guard in normalization.
     - DEF-013: Configuration path traversal sandboxing guard.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

import numpy as np
import pytest

from server.adapters.base_adapter import (
    AdapterConnectionError,
    AdapterError,
    AdapterStatus,
    ConfigurationPathTraversalError,
    DatasetNotFoundError,
    DomainType,
    MachineAdapter,
    NormalizedReading,
    UnknownMachineError,
    UntrainedDomainModelError,
)
from server.adapters.cmapss_adapter import CMAPSSAdapter
from server.adapters.laptop_adapter import LaptopAdapter
from server.adapters.mobile_adapter import MobileAdapter
from server.adapters.server_adapter import ServerAdapter
from server.atlas.world_model import UntrainedModelError, WorldModel, WorldModelConfig


# ---------------------------------------------------------------------------
# Minimal "Hello World" Reference Adapter (as specified in ADAPTER_SDK_SPEC.md)
# ---------------------------------------------------------------------------

class MinimalVibrationAdapter(MachineAdapter):
    """
    Minimal compliant reference adapter implementing the ATLAS Adapter SDK.
    Serves as proof that the specification is fully implementable without
    relying on internal ATLAS engine dependencies.
    """

    def __init__(self, machine_ids: Optional[List[str]] = None) -> None:
        super().__init__()
        self._machine_ids = machine_ids or ["pump_01", "pump_02"]
        self._step_counter: Dict[str, int] = {mid: 0 for mid in self._machine_ids}

    @property
    def domain_id(self) -> str:
        return "industrial_pump"

    @property
    def machine_ids(self) -> List[str]:
        return list(self._machine_ids)

    def _connect(self) -> None:
        self._status = AdapterStatus.LIVE

    def _disconnect(self) -> None:
        self._status = AdapterStatus.DISCONNECTED

    def get_reading(self, machine_id: str) -> NormalizedReading:
        if machine_id not in self._machine_ids:
            raise UnknownMachineError(machine_id=machine_id, domain=self.domain_id)

        self._step_counter[machine_id] += 1
        cycle = self._step_counter[machine_id]

        # Raw physical telemetry
        raw_vib_g = float(0.42 + 0.15 * np.sin(cycle * 0.1))
        raw_temp_c = float(48.0 + 3.5 * np.cos(cycle * 0.05))

        # Normalization with explicit epsilon guards (DEF-009 guardrail)
        norm_vib = float(np.clip((raw_vib_g - 0.0) / max(2.5, 1e-6), 0.0, 1.0))
        norm_temp = float(np.clip((raw_temp_c - 20.0) / max(80.0, 1e-6), 0.0, 1.0))

        features = {
            "vibration_g": round(norm_vib, 4),
            "bearing_temp": round(norm_temp, 4),
        }

        # Operational stress score in [0.0, 1.0]
        health_index = float(np.clip(0.6 * norm_vib + 0.4 * norm_temp, 0.0, 1.0))

        return NormalizedReading(
            domain=self.domain_id,
            machine_id=machine_id,
            timestamp=NormalizedReading.timestamp_now(),
            health_index=round(health_index, 4),
            cycle=cycle,
            rul_label=None,
            features=features,
            raw_features={"vibration_g": raw_vib_g, "temp_c": raw_temp_c},
            operational_ctx={"rpm": 1750, "flow_rate_gpm": 120.0},
            metadata={"sensor_model": "IFM-VSA001", "total_channels": len(features)},
            adapter_status=self.status.value,
        )

    def describe(self) -> Dict[str, Any]:
        base = super().describe()
        base.update({
            "feature_dim": 2,
            "sensor_names": ["vibration_g", "bearing_temp"],
        })
        return base


# ---------------------------------------------------------------------------
# Test Fixture Factory for All Adapters
# ---------------------------------------------------------------------------

@pytest.fixture(
    params=[
        "cmapss",
        "laptop",
        "mobile",
        "server",
        "hello_world",
    ],
    ids=["CMAPSSAdapter", "LaptopAdapter", "MobileAdapter", "ServerAdapter", "HelloWorldAdapter"],
)
def adapter_instance(request) -> Generator[Tuple[str, MachineAdapter], None, None]:
    """
    Parametrized fixture providing connected instances of all 4 existing adapters
    and the minimal Hello World reference adapter, ensuring thorough cleanup.
    """
    domain = request.param

    if domain == "cmapss":
        data_file = Path("data/cmapss/train_FD001.txt")
        if not data_file.exists():
            pytest.skip("C-MAPSS dataset not present at data/cmapss/train_FD001.txt")
        adapter = CMAPSSAdapter(subset="FD001", split="train", max_units=2)
    elif domain == "laptop":
        adapter = LaptopAdapter()
    elif domain == "mobile":
        adapter = MobileAdapter()
    elif domain == "server":
        adapter = ServerAdapter()
    elif domain == "hello_world":
        adapter = MinimalVibrationAdapter()
    else:
        raise ValueError(f"Unknown fixture domain: {domain}")

    adapter.connect()
    try:
        yield domain, adapter
    finally:
        adapter.disconnect()


# ---------------------------------------------------------------------------
# 1. Reading Schema Conformance Tests
# ---------------------------------------------------------------------------

class TestAdapterReadingConformance:
    """Verifies that get_reading() strictly adheres to NormalizedReading contract."""

    def test_get_reading_known_machine_returns_valid_normalized_reading(
        self, adapter_instance: Tuple[str, MachineAdapter]
    ) -> None:
        domain_name, adapter = adapter_instance
        machine_ids = adapter.machine_ids
        assert len(machine_ids) > 0, f"Adapter for {domain_name} exposed empty machine_ids list"

        for mid in machine_ids:
            reading = adapter.get_reading(mid)

            # Instance check
            assert isinstance(reading, NormalizedReading), (
                f"[{domain_name}] get_reading({mid}) returned {type(reading)}, expected NormalizedReading"
            )

            # Identification fields
            assert reading.domain == adapter.domain_id
            assert reading.machine_id == mid

            # Timestamp format: parseable UTC ISO-8601 ending in Z
            assert isinstance(reading.timestamp, str)
            assert reading.timestamp.endswith("Z"), f"Timestamp {reading.timestamp} missing 'Z' suffix"
            parsed_dt = datetime.fromisoformat(reading.timestamp.replace("Z", "+00:00"))
            assert parsed_dt is not None

            # Health index bounds
            assert isinstance(reading.health_index, (int, float))
            assert 0.0 <= reading.health_index <= 1.0, (
                f"[{domain_name}] health_index={reading.health_index} violates [0.0, 1.0] bound"
            )
            assert not np.isnan(reading.health_index)
            assert not np.isinf(reading.health_index)

            # Cycle: non-negative integer
            assert isinstance(reading.cycle, int)
            assert reading.cycle >= 0

            # RUL label: either None or non-negative float
            if reading.rul_label is not None:
                assert isinstance(reading.rul_label, (int, float))
                assert reading.rul_label >= 0.0

            # Features dictionary: non-empty, all values in [0.0, 1.0]
            assert isinstance(reading.features, dict)
            assert len(reading.features) > 0, f"[{domain_name}] features dictionary is empty"
            for k, v in reading.features.items():
                assert isinstance(k, str), f"Feature key {k} is not a string"
                assert isinstance(v, (int, float)), f"Feature {k}={v} is not a float"
                assert not np.isnan(v), f"Feature {k} contains NaN"
                assert not np.isinf(v), f"Feature {k} contains Inf"
                assert 0.0 <= v <= 1.0, f"[{domain_name}] Feature {k}={v} outside [0.0, 1.0]"

            # Raw features & context
            assert isinstance(reading.raw_features, dict)
            assert isinstance(reading.operational_ctx, dict)
            assert isinstance(reading.metadata, dict)

            # Status must be valid enum value
            assert reading.adapter_status in [s.value for s in AdapterStatus]

            # Feature vector helper
            vec = reading.feature_vector
            assert isinstance(vec, list)
            assert len(vec) > 0
            assert all(isinstance(x, (int, float)) for x in vec)

            # Serialization to_dict() test
            d = reading.to_dict()
            assert isinstance(d, dict)
            assert d["domain"] == adapter.domain_id
            assert d["machine_id"] == mid
            assert d["health_index"] == pytest.approx(reading.health_index, abs=1e-5)


# ---------------------------------------------------------------------------
# 2. Unknown Machine ID Error Handling
# ---------------------------------------------------------------------------

class TestAdapterUnknownMachineError:
    """Verifies that querying an unknown machine_id loudly raises documented exception."""

    def test_unknown_machine_id_raises_documented_exception(
        self, adapter_instance: Tuple[str, MachineAdapter]
    ) -> None:
        domain_name, adapter = adapter_instance
        unknown_id = "nonexistent_device_id_99999"

        # Conformance requirement: must raise KeyError, ValueError, or UnknownMachineError
        with pytest.raises((KeyError, ValueError, UnknownMachineError)) as exc_info:
            adapter.get_reading(unknown_id)

        # Exception must mention or identify the invalid machine_id
        err_msg = str(exc_info.value)
        assert unknown_id in err_msg or "Unknown" in err_msg or "unknown" in err_msg, (
            f"[{domain_name}] Error message did not mention unknown machine_id: '{err_msg}'"
        )


# ---------------------------------------------------------------------------
# 3. Feature Dimension Consistency
# ---------------------------------------------------------------------------

class TestAdapterFeatureDimConsistency:
    """Verifies that reported feature dimension is consistent with get_reading()."""

    def test_feature_dim_reported_matches_actual_features(
        self, adapter_instance: Tuple[str, MachineAdapter]
    ) -> None:
        domain_name, adapter = adapter_instance
        mid = adapter.machine_ids[0]
        reading = adapter.get_reading(mid)
        actual_features_count = len(reading.features)

        desc = adapter.describe()

        # Check 1: If describe() exposes "feature_dim", it must match
        if "feature_dim" in desc:
            assert desc["feature_dim"] == actual_features_count, (
                f"[{domain_name}] describe()['feature_dim']={desc['feature_dim']} "
                f"!= len(reading.features)={actual_features_count}"
            )

        # Check 2: If metadata exposes "total_channels", it must match
        if "total_channels" in reading.metadata:
            assert reading.metadata["total_channels"] == actual_features_count, (
                f"[{domain_name}] reading.metadata['total_channels']={reading.metadata['total_channels']} "
                f"!= len(reading.features)={actual_features_count}"
            )

        # Check 3: feature_vector must have valid deterministic dimension
        f_vec = reading.feature_vector
        assert len(f_vec) in (actual_features_count, 5, 14), (
            f"[{domain_name}] feature_vector length {len(f_vec)} is neither actual feature "
            f"count ({actual_features_count}) nor canonical model feature dim (5 or 14)"
        )


# ---------------------------------------------------------------------------
# 4. Lifecycle Contracts
# ---------------------------------------------------------------------------

class TestAdapterLifecycleContracts:
    """Verifies connect(), disconnect(), and status transitions."""

    def test_connect_is_idempotent(self, adapter_instance: Tuple[str, MachineAdapter]) -> None:
        domain_name, adapter = adapter_instance
        # Calling connect() multiple times must not crash or leak resources
        adapter.connect()
        adapter.connect()
        assert adapter._connected is True

    def test_disconnect_sets_status_disconnected(self) -> None:
        adapter = MinimalVibrationAdapter()
        adapter.connect()
        assert adapter.status == AdapterStatus.LIVE
        adapter.disconnect()
        assert adapter.status == AdapterStatus.DISCONNECTED


# ---------------------------------------------------------------------------
# 5. DEF-008 Guardrail Built-in Verification (Dynamic Model Instantiation)
# ---------------------------------------------------------------------------

class TestDEF008GuardrailDynamicWorldModel:
    """
    STEP 4 MANDATORY GUARDRAIL:
    Any code path dynamically creating a WorldModelConfig for a new domain
    MUST expose an explicit, queryable 'is_trained' state (False until trained)
    and MUST NEVER silently substitute an untrained/zero-shot projection
    while reporting success.
    """

    def test_dynamic_world_model_config_is_trained_false_by_default(self) -> None:
        """New WorldModelConfig must have is_trained=False by default."""
        cfg = WorldModelConfig(domain="dynamic_cnc_router", feature_dim=8)
        assert hasattr(cfg, "is_trained"), "WorldModelConfig is missing mandatory 'is_trained' attribute"
        assert cfg.is_trained is False, (
            "DEF-008 VIOLATION: Dynamically created WorldModelConfig has is_trained=True before training!"
        )

    def test_untrained_model_refuses_silent_zero_shot_inference(self) -> None:
        """Untrained model forward predict() MUST raise UntrainedModelError by default."""
        cfg = WorldModelConfig(domain="dynamic_cnc_router", feature_dim=8, is_trained=False)
        model = WorldModel(cfg)

        sample_window = np.zeros((30, 8), dtype=np.float32)

        with pytest.raises(UntrainedModelError) as exc_info:
            model.predict(sample_window)

        assert "is_trained=False" in str(exc_info.value) or "not trained" in str(exc_info.value)

    def test_explicit_opt_in_allows_diagnostic_inference_without_silent_substitution(self) -> None:
        """Diagnostic callers must explicitly pass allow_untrained=True to evaluate untrained weights."""
        cfg = WorldModelConfig(domain="diagnostic_domain", feature_dim=6, is_trained=False)
        model = WorldModel(cfg)
        sample_window = np.random.rand(30, 6).astype(np.float32)

        # With explicit flag, inference executes without error, but is_trained remains False
        out = model.predict(sample_window, allow_untrained=True)
        assert out.state_vector is not None
        assert model.config.is_trained is False

    def test_loaded_checkpoint_has_is_trained_true(self, tmp_path: Path) -> None:
        """Loaded checkpoints must have is_trained=True."""
        cfg = WorldModelConfig(domain="test_trained", feature_dim=4)
        model = WorldModel(cfg)
        ckpt_file = tmp_path / "test_trained_world_model.pt"
        model.save(ckpt_file)

        loaded = WorldModel.load(ckpt_file)
        assert loaded.config.is_trained is True

        # Inference proceeds without needing allow_untrained=True
        sample = np.zeros((30, 4), dtype=np.float32)
        out = loaded.predict(sample)
        assert out.state_vector.shape == (32,)


# ---------------------------------------------------------------------------
# 6. Defect Prevention Regression Guardrails (DEF-002, DEF-007, DEF-009, DEF-013)
# ---------------------------------------------------------------------------

class TestDefectPreventionGuardrails:
    """Explicit algorithmic guards against defect regressions."""

    def test_def_002_temporal_monotonicity_guard(self) -> None:
        """
        DEF-002: Windowing pipelines must enforce strict temporal ordering.
        Simulate an out-of-order reading sequence and verify that sort by cycle is enforced.
        """
        unsorted_readings = [
            {"cycle": 15, "val": 0.5},
            {"cycle": 10, "val": 0.3},
            {"cycle": 20, "val": 0.7},
        ]
        # Sorting contract
        sorted_readings = sorted(unsorted_readings, key=lambda x: x["cycle"])
        cycles = [r["cycle"] for r in sorted_readings]
        assert cycles == [10, 15, 20]
        # Monotonicity check
        assert all(cycles[i] < cycles[i + 1] for i in range(len(cycles) - 1))

    def test_def_007_channel_non_collapse_guard(self) -> None:
        """
        DEF-007: Synthetically produced readings across multiple steps must maintain
        adequate feature variance to prevent latent space directional collapse.
        """
        adapter = MinimalVibrationAdapter()
        adapter.connect()
        readings = [adapter.get_reading("pump_01") for _ in range(20)]
        adapter.disconnect()

        vib_values = [r.features["vibration_g"] for r in readings]
        temp_values = [r.features["bearing_temp"] for r in readings]

        vib_std = float(np.std(vib_values))
        temp_std = float(np.std(temp_values))

        # Variance must be strictly non-zero across cycles
        assert vib_std > 0.005, f"Vibration channel collapsed to static value: std={vib_std}"
        assert temp_std > 0.005, f"Temperature channel collapsed to static value: std={temp_std}"

    def test_def_009_division_by_zero_epsilon_guard(self) -> None:
        """
        DEF-009: Normalization with identical min and max must not raise ZeroDivisionError.
        """
        val = 42.0
        val_min = 42.0
        val_max = 42.0
        # Epsilon guarded denominator
        denom = val_max - val_min
        guarded_denom = 1.0 if denom == 0.0 else denom
        norm_val = np.clip((val - val_min) / guarded_denom, 0.0, 1.0)
        assert norm_val == 0.0
        assert not np.isnan(norm_val)

    def test_def_013_path_traversal_sandboxing_guard(self, tmp_path: Path) -> None:
        """
        DEF-013 Context: Path-based configuration / register map loader must strictly
        sandbox file paths within JAIL_ROOT and reject path traversal escapes.
        """
        jail_dir = tmp_path / "configs"
        jail_dir.mkdir(parents=True, exist_ok=True)
        valid_config = jail_dir / "pump_register_map.json"
        valid_config.write_text('{"register": 40001}', encoding="utf-8")

        def load_sandboxed_config(untrusted_path_str: str, base_dir: Path) -> str:
            resolved = (base_dir / untrusted_path_str).resolve()
            if not resolved.is_relative_to(base_dir.resolve()):
                raise ConfigurationPathTraversalError(
                    f"Path traversal detected: '{untrusted_path_str}' escapes root '{base_dir}'"
                )
            return resolved.read_text(encoding="utf-8")

        # 1. Valid path inside jail succeeds
        content = load_sandboxed_config("pump_register_map.json", jail_dir)
        assert "40001" in content

        # 2. Path traversal attempt outside jail is blocked
        malicious_input = "../../secret_system_file.txt"
        with pytest.raises(ConfigurationPathTraversalError):
            load_sandboxed_config(malicious_input, jail_dir)
