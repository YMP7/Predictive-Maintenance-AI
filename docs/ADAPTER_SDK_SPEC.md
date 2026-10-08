# ATLAS MachineAdapter SDK Specification (v1.0.0)

**Project:** ATLAS — Adaptive Machine Cognition Platform  
**Document Type:** Formal Software Development Kit (SDK) Architecture Specification  
**Branch:** `feature/universal-adapter-sdk`  
**Base Tag:** `v1.0.0-viva-defense`  
**Status:** Approved Technical Standard (Phase 1: SDK Formalization)  
**Conformance Suite:** `tests/test_adapter_conformance.py`  

---

## 1. Architectural Mission & Boundary Isolation

The **ATLAS MachineAdapter SDK** defines the single, standardized boundary between physical or simulated machine environments and the downstream ATLAS cognition architecture. 

In industrial deployments, predictive maintenance platforms frequently fail due to tight architectural coupling: telemetry ingestion scripts make hardcoded assumptions about sensor counts, sample rates, operating modes, and communication protocols. When new machinery is introduced, changes ripple destructively through neural encoders, associative memory banks, and decision graphs.

ATLAS establishes an absolute boundary isolation principle:

> **The Single Boundary Principle:**  
> The domain adapter is the **ONLY** place where domain-specific hardware knowledge, communication protocols, sensor channel names, and scaling logic exist. Once raw telemetry crosses the adapter boundary into a `NormalizedReading`, all downstream subsystems (`WorldModel`, `AMKB`, `MachineDNA`, `SimulationEngine`, `DecisionGraph`, `ExplanationEngine`) operate in a completely domain-agnostic fashion.

```
+-------------------------------------------------------------------------------+
|                             Physical / Data Tier                             |
|  [NASA Turbofans]    [Host OS / psutil]    [Android / ADB]    [Enterprise VM] |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
|                         ATLAS MachineAdapter SDK                              |
|   CMAPSSAdapter        LaptopAdapter        MobileAdapter       ServerAdapter |
|                                      |                                        |
|                          Produces NormalizedReading                           |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
|                       ATLAS Cognition Core (Domain-Agnostic)                   |
|   WorldModel (Attention-LSTM) -> State Vector [32-dim]                        |
|   AMKB (pgvector / InMemoryAMKB) -> k-NN Latent Retrieval                     |
|   DecisionGraph -> Cost-Optimized Action Selection                            |
|   ExplanationEngine -> Grounded Attribution & Counterfactuals                 |
+-------------------------------------------------------------------------------+
```

---

## 2. Non-Assumptions of the Interface

A generalized machine adapter contract must be strictly decoupled from any single machine taxonomy. The ATLAS `MachineAdapter` contract explicitly **DOES NOT ASSUME**:

1. **NO Fixed Feature Count:**  
   The interface does not assume 14 sensors (NASA C-MAPSS), 5 sensors (compute workloads), or 16 sensors (mobile devices). A valid adapter may output any number of sensor features $F \ge 1$.
2. **NO Fixed Sampling Frequency or Cadence:**  
   The interface does not assume periodic 1 Hz telemetry, 100 Hz high-frequency vibration streams, or event-driven asynchronous pushes. The streaming engine polls `get_reading()` on demand or receives continuous pushes.
3. **NO Fixed Physical Data Types:**  
   The interface does not assume raw metrics are analog voltages, temperatures, digital RPM counters, or kernel CPU jiffies. Raw telemetry can be of arbitrary type (`Any`) inside `raw_features`, while `features` maps string channel names to normalized floats.
4. **NO Mandatory Fixed Failure Timestamp (Category A vs Category B):**  
   The interface does not force all machines into a run-to-failure degradation model. Benchmark turbofans fail at a known cycle (Category A: Structural Wear), whereas continuous enterprise servers, laptops, and mobile hardware experience workload fluctuations without fixed failure dates (Category B: Instantaneous Operational Stress).

---

## 3. `MachineAdapter` Abstract Base Class (ABC)

Every adapter must inherit from `server.adapters.base_adapter.MachineAdapter` (or import from `server.adapters`).

### 3.1 Class Definition

```python
class MachineAdapter(abc.ABC):
    """
    Abstract base class for all ATLAS domain adapters.
    
    Subclasses must implement:
      - domain_id    : str property
      - machine_ids  : List[str] property
      - _connect()   : Establish transport / load dataset
      - _disconnect(): Release resources / close sockets
      - get_reading(machine_id: str) -> NormalizedReading
    """
```

### 3.2 Required Properties

| Property | Type | Description | Exceptions / Constraints |
|---|---|---|---|
| `domain_id` | `@property -> str` | Unique machine domain identifier (e.g., `"cmapss"`, `"laptop"`, `"industrial_pump"`). | Must return non-empty ASCII string. Must be deterministic. |
| `machine_ids` | `@property -> List[str]` | List of all distinct machine/unit identifiers managed by this adapter. | Must return at least one valid machine identifier string. |
| `status` | `@property -> AdapterStatus` | Current operational lifecycle status. | Returns one of: `AdapterStatus.LIVE`, `STREAMING`, `SIMULATION`, `DISCONNECTED`. |

### 3.3 Lifecycle Methods

```python
def connect(self) -> None:
    """
    Public connection entrypoint. Guaranteed to be idempotent:
    calling connect() repeatedly will not leak sockets or reset cursors.
    """
    if not self._connected:
        self._connect()
        self._connected = True

def disconnect(self) -> None:
    """
    Public disconnection entrypoint. Releases network sockets, file handles,
    and background worker threads. Sets status to AdapterStatus.DISCONNECTED.
    """
    if self._connected:
        self._disconnect()
        self._connected = False
        self._status = AdapterStatus.DISCONNECTED
```

#### Abstract Internal Hooks:
- `_connect(self) -> None`: Subclass hook establishing network connections, hardware drivers, or loading dataset files into memory. May raise `AdapterConnectionError` or `DatasetNotFoundError`.
- `_disconnect(self) -> None`: Subclass hook closing sockets, worker threads, and clearing cached records. Must not raise exceptions.

### 3.4 Telemetry Polling Interface

```python
@abc.abstractmethod
def get_reading(self, machine_id: str) -> NormalizedReading:
    """
    Return the next NormalizedReading for the specified machine_id.
    
    Parameters:
      machine_id: Unique identifier belonging to self.machine_ids
      
    Returns:
      NormalizedReading: Fully schema-compliant telemetry unit.
      
    Raises:
      UnknownMachineError: If machine_id is not in self.machine_ids.
                           (Subclasses KeyError and ValueError for backwards compatibility).
    """
```

```python
def get_all_readings(self) -> List[NormalizedReading]:
    """Convenience method polling one reading per managed machine."""
    return [self.get_reading(mid) for mid in self.machine_ids]
```

### 3.5 Metadata Interface

```python
def describe(self) -> Dict[str, Any]:
    """
    Returns an introspection dictionary consumed by the API gateway (/api/atlas/domains).
    Subclasses should extend this dictionary with domain-specific metadata.
    """
    return {
        "domain_id":   self.domain_id,
        "machine_ids": self.machine_ids,
        "status":      self._status.value,
        "connected":   self._connected,
    }
```

---

## 4. `NormalizedReading` Schema Contract

The `NormalizedReading` dataclass is the single universal contract between all machine adapters and downstream cognition engines.

```python
@dataclass
class NormalizedReading:
    domain:          str
    machine_id:      str
    timestamp:       str
    health_index:    float                 # [0.0, 1.0]
    cycle:           int                   # time-step index or uptime seconds
    rul_label:       Optional[float]       # Ground truth RUL (cycles/days) if known, else None
    features:        Dict[str, float]      # Normalised sensor features in [0.0, 1.0]
    raw_features:    Dict[str, Any]        # Original un-normalised sensor readings
    operational_ctx: Dict[str, Any]        # Operational context / operating regime
    metadata:        Dict[str, Any]        # Adapter metadata / diagnostics
    adapter_status:  str = AdapterStatus.LIVE.value
```

### 4.1 Field-by-Field Contract

| Field Name | Type | Allowed Values / Constraints | Semantics & Ground Truth Guarantees |
|---|---|---|---|
| `domain` | `str` | Must match `adapter.domain_id`. | Identifies the physical/operational taxonomy of the machine. |
| `machine_id` | `str` | Must be an element of `adapter.machine_ids`. | Unique identifier of the individual asset. |
| `timestamp` | `str` | UTC ISO-8601 string ending with `"Z"` (e.g. `2026-09-24T16:00:00Z`). | Temporal wall-clock timestamp of acquisition. |
| `health_index` | `float` | Strictly bounded in $[0.0, 1.0]$. `NaN` and `Inf` are forbidden. | **Two-Tier Taxonomy:**<br>• *Category A (Benchmark Ground Truth):* Physical degradation toward failure ($0.0 = \text{fresh}, 1.0 = \text{failed}$).<br>• *Category B (Live Heterogeneous Hardware):* Instantaneous Operational Stress / Workload Saturation index. |
| `cycle` | `int` | Monotonically non-decreasing integer $\ge 0$. | Temporal sequence index (cycle number for time-series datasets, uptime seconds for live devices). |
| `rul_label` | `Optional[float]` | $\ge 0.0$ or `None`. | Empirical ground truth Remaining Useful Life (RUL). **Must be `None`** for live systems without run-to-failure empirical labels. |
| `features` | `Dict[str, float]` | Non-empty dictionary. All values strictly bounded in $[0.0, 1.0]$. | Normalized sensor telemetry consumed by neural encoders and AMKB. Keys must be consistent within a domain. |
| `raw_features` | `Dict[str, Any]` | Dictionary of raw measurements. | Native un-normalized engineering units (e.g., ${}^{\circ}\text{C}$, $\text{mA}$, $\text{m/s}^2$, $\text{RPM}$, $\text{IOPS}$) preserved for debugging and physics-informed models. |
| `operational_ctx`| `Dict[str, Any]`| Dictionary of operational regime parameters. | Environmental and workload settings (e.g. ambient temperature, power supply source, altitude, fan speed). |
| `metadata` | `Dict[str, Any]` | Dictionary of adapter bookkeeping metadata. | Sensor serial numbers, calibration versions, total channel counts (`total_channels`), transport mode (`transport`). |
| `adapter_status` | `str` | `"live"`, `"streaming"`, `"simulation"`, `"disconnected"`. | Operating mode of the adapter at the exact moment of reading acquisition. |

### 4.2 Helper Methods on `NormalizedReading`

- `feature_vector -> List[float]`: Returns an ordered list of float features for direct ingestion into PyTorch tensor windows `(seq_len, feature_dim)`.
- `to_dict() -> Dict[str, Any]`: Returns a JSON-serializable representation of the entire reading, rounding `health_index` to 6 decimal places.
- `timestamp_now() -> str`: Factory classmethod generating a valid UTC ISO-8601 timestamp string with `"Z"` suffix.

---

## 5. Standardized Exception Hierarchy

All exceptions raised across the adapter ecosystem derive from a root `AdapterError`:

```
Exception
  |
  +-- AdapterError
        |
        +-- UnknownMachineError (also inherits KeyError, ValueError)
        +-- ConfigurationPathTraversalError (also inherits ValueError)
        +-- UntrainedDomainModelError (also inherits RuntimeError)
        +-- DatasetNotFoundError (also inherits FileNotFoundError)
        +-- AdapterConnectionError (also inherits ConnectionError)
```

```python
class AdapterError(Exception):
    """Base exception for all MachineAdapter operations."""
    pass

class UnknownMachineError(KeyError, ValueError, AdapterError):
    """
    Raised when an adapter is queried with an unrecognized machine_id.
    Subclasses both KeyError and ValueError so existing callers catch it cleanly.
    """
    def __init__(self, machine_id: str, domain: str = ""):
        self.machine_id = machine_id
        self.domain = domain
        prefix = f"[{domain}] " if domain else ""
        super().__init__(f"{prefix}Unknown machine_id: '{machine_id}'")

class ConfigurationPathTraversalError(ValueError, AdapterError):
    """Raised when adapter config or register map loading escapes jail root (DEF-013 guard)."""
    pass

class UntrainedDomainModelError(RuntimeError, AdapterError):
    """Raised when an untrained model is queried for inference without allow_untrained (DEF-008 guard)."""
    pass
```

---

## 6. Audit Findings from Existing Adapters

In accordance with Phase 1 Step 1, a comprehensive audit was performed across `server/adapters/base_adapter.py` and the 4 existing domain adapters (`CMAPSSAdapter`, `LaptopAdapter`, `MobileAdapter`, `ServerAdapter`):

### 6.1 Architectural Leaks Identified in Base Contract

1. **Hardcoded Domain Features in Base Dataclass (`base_adapter.py` lines 122–145):**
   `NormalizedReading._CANONICAL_MODEL_FEATURES` hardcoded domain keys (`"mobile"`, `"laptop"`, `"server"`) directly inside what should be a domain-agnostic dataclass. A 5th generic domain fell back to alphabetical key sorting, creating a structural asymmetry.
2. **Closed Domain Enum (`DomainType` in `base_adapter.py` lines 60–65):**
   `DomainType` defined only `CMAPSS`, `LAPTOP`, `MOBILE`, `SERVER`. Dynamic or third-party adapters cannot be added if domain type validation checks against this closed enum.
3. **Exception Inconsistency on Unknown Machine ID:**
   - `CMAPSSAdapter` raised `KeyError`
   - `LaptopAdapter`, `MobileAdapter`, and `ServerAdapter` raised `ValueError`
   *Resolution:* Standardized on `UnknownMachineError`, which inherits from **both** `KeyError` and `ValueError`, eliminating caller ambiguity.
4. **Dimension Exposure Inconsistency:**
   - `CMAPSSAdapter` exposed `feature_dim` via `describe()`
   - `LaptopAdapter` and `MobileAdapter` exposed `total_channels` inside `reading.metadata`
   - `ServerAdapter` exposed feature count implicitly via `len(features) == 5`
   *Resolution:* The SDK specification requires all adapters to report `feature_dim` in `describe()` and `total_channels` in `metadata`.
5. **Lifecycle State Omission in `_connect()`:**
   - In `LaptopAdapter`, `_connect()` did not set `self._status = AdapterStatus.LIVE`, leaving status as `DISCONNECTED` despite live telemetry acquisition.
   - In `ServerAdapter`, `_connect()` left status as `DISCONNECTED` when host configuration was absent, rather than transitioning to `AdapterStatus.SIMULATION`.
   *Resolution:* Fixed in SDK conformance contract: `_connect()` must explicitly set `self._status`.

---

## 7. Mandatory Defect Guardrails Built into the SDK

The Adapter SDK architecture directly incorporates mitigations against the 5 critical defect classes identified in the mandatory audit:

### 7.1 DEF-002: Row-Order Silent Corruption in Ingestion
- **The Defect:** Unsorted telemetry frames produce valid tensor shapes `(30, F)` but silently corrupted temporal progressions, invalidating LSTM hidden state transitions.
- **The SDK Guard:** Any adapter producing sequence windows or timeseries batches must enforce explicit monotonic sorting:
  $$\text{Sort by } (machine\_id, cycle) \quad \text{or} \quad (machine\_id, timestamp)$$
  The conformance suite includes `test_def_002_temporal_monotonicity_guard` verifying that sequence batching rejects or re-orders out-of-order frames before tensor formation.

### 7.2 DEF-007: Representation Collapse across Channels
- **The Defect:** When synthetic telemetry channels remain static ($\text{std} \approx 0$), encoder reconstruction loss is satisfied trivially, collapsing the 32-dimensional latent space to a constant line ($\text{Cosine Distance} < 0.20$).
- **The SDK Guard:** Adapters and simulators must maintain multi-modal dynamic operational regimes. The conformance suite includes `test_def_007_channel_non_collapse_guard`, verifying that every channel exhibits variance strictly above the zero floor across cycles ($\sigma > 0.005$).

### 7.3 DEF-008: Silent Zero-Shot Fallback Routing
- **The Defect:** Multi-domain API endpoints silently served untrained zero-shot projections instead of real trained Attention-LSTM checkpoints, returning plausible-looking predictions without error flags.
- **The SDK Guard:** Any code path that dynamically creates a `WorldModelConfig` or binds a new adapter domain to the cognition engine exposes an explicit, queryable attribute:
  $$\text{config.is\_trained} \equiv \text{False until real training completes}$$
  Attempting inference via `model.predict()` when `is_trained == False` raises `UntrainedModelError` unless explicitly overridden with `allow_untrained=True`. Zero-shot fallback can never masquerade as a trained model.

### 7.4 DEF-009: Division-by-Zero in Normalizers & Confidence
- **The Defect:** Naive inverse variance formulas explode to `Inf` or `NaN` when sensors or neighbor predictions exhibit zero variance.
- **The SDK Guard:** All adapter feature normalizers and confidence formulas must employ explicit epsilon guards:
  $$\text{denom} = \max(\text{scale}, 10^{-6}) \quad \text{or} \quad \text{denom} = (\text{denom} \text{ if } \text{denom} \neq 0 \text{ else } 1.0)$$
  The conformance suite includes `test_def_009_division_by_zero_epsilon_guard` asserting that zero-dynamic-range inputs normalize gracefully to $0.0$ without numerical explosion.

### 7.5 DEF-013: Configuration Path Traversal (Register Map Sandboxing)
- **The Defect:** Path-based configuration loaders (e.g. Modbus register maps, YAML domain configs) that resolve arbitrary user-supplied paths can escape jail boundaries into host system files (`../../etc/passwd` or `../../secret.txt`).
- **The SDK Guard:** The SDK mandates strict path sandboxing:
  ```python
  resolved_path = (jail_root / untrusted_path).resolve()
  if not resolved_path.is_relative_to(jail_root.resolve()):
      raise ConfigurationPathTraversalError(f"Path traversal detected: {untrusted_path}")
  ```
  The conformance suite includes `test_def_013_path_traversal_sandboxing_guard` proving traversal attempts outside the jail root are blocked.

---

## 8. "Hello World" Reference Adapter Implementation

The following complete, self-contained reference adapter illustrates how an engineer with zero prior knowledge of the ATLAS codebase can implement a compliant machine adapter:

```python
"""
minimal_vibration_adapter.py — Self-Contained ATLAS Adapter Example
"""
from typing import Any, Dict, List, Optional
import numpy as np

from server.adapters.base_adapter import (
    AdapterStatus,
    MachineAdapter,
    NormalizedReading,
    UnknownMachineError,
)

class MinimalVibrationAdapter(MachineAdapter):
    """
    Reference adapter for an industrial dual-pump vibration monitoring setup.
    Exposes 2 channels: vibration_g and bearing_temp.
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
        # Establish connection to physical PLC / Modbus bridge
        self._status = AdapterStatus.LIVE

    def _disconnect(self) -> None:
        # Release Modbus connection and sockets
        self._status = AdapterStatus.DISCONNECTED

    def get_reading(self, machine_id: str) -> NormalizedReading:
        if machine_id not in self._machine_ids:
            raise UnknownMachineError(machine_id=machine_id, domain=self.domain_id)

        self._step_counter[machine_id] += 1
        cycle = self._step_counter[machine_id]

        # 1. Acquire raw physical metrics (e.g., from accelerometers and RTDs)
        raw_vib_g = float(0.42 + 0.15 * np.sin(cycle * 0.1))
        raw_temp_c = float(48.0 + 3.5 * np.cos(cycle * 0.05))

        # 2. Normalize to [0.0, 1.0] with explicit epsilon guards (DEF-009)
        norm_vib = float(np.clip((raw_vib_g - 0.0) / max(2.5, 1e-6), 0.0, 1.0))
        norm_temp = float(np.clip((raw_temp_c - 20.0) / max(80.0, 1e-6), 0.0, 1.0))

        features = {
            "vibration_g": round(norm_vib, 4),
            "bearing_temp": round(norm_temp, 4),
        }

        # 3. Category B Operational Stress Score in [0.0, 1.0]
        health_index = float(np.clip(0.6 * norm_vib + 0.4 * norm_temp, 0.0, 1.0))

        # 4. Return strictly compliant NormalizedReading
        return NormalizedReading(
            domain=self.domain_id,
            machine_id=machine_id,
            timestamp=NormalizedReading.timestamp_now(),
            health_index=round(health_index, 4),
            cycle=cycle,
            rul_label=None,  # Live continuous system has no fixed failure label
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


if __name__ == "__main__":
    adapter = MinimalVibrationAdapter()
    adapter.connect()
    reading = adapter.get_reading("pump_01")
    print("Successfully read from adapter:")
    print(f"Domain: {reading.domain} | Machine: {reading.machine_id}")
    print(f"Health Index: {reading.health_index} | Features: {reading.features}")
    adapter.disconnect()
```

---

## 9. Conformance Test Certification

Any new adapter must pass the automated conformance test suite in `tests/test_adapter_conformance.py` prior to domain registration:

```bash
pytest tests/test_adapter_conformance.py -v
```

A passing suite certifies:
- 100% adherence to the `NormalizedReading` schema and value bounds.
- Explicit exception raising on unknown machine queries.
- Feature dimension consistency between descriptor and output payload.
- Safe lifecycle idempotency and resource cleanup.
- Full compliance with DEF-002, DEF-007, DEF-008, DEF-009, and DEF-013 guardrails.

---

## 10. Phase 2: Industrial Modbus TCP Protocol Adapter

Phase 2 introduces the first generic industrial protocol adapter: [`ModbusAdapter`](../server/adapters/modbus_adapter.py) communicating with physical or simulated assets via Modbus TCP (IEC 61158 / Modbus-IDA), paired with an in-process [`ModbusSimulator`](../server/adapters/modbus_simulator.py).

### 10.1 Key Architectural Decision: Config-Driven Register Mapping (Layer 2)

Rather than hardcoding register meanings in Python code, `ModbusAdapter` accepts a **Register Map** configuration. This decouples the network protocol from asset telemetry:

```json
[
  {
    "name": "temperature_c",
    "register": 40001,
    "scale": 0.1,
    "offset": 0.0,
    "unit": "degC",
    "min_val": 15.0,
    "max_val": 100.0,
    "register_type": "holding"
  },
  {
    "name": "vibration_mms",
    "register": 40002,
    "scale": 0.001,
    "offset": 0.0,
    "unit": "mm/s",
    "min_val": 0.0,
    "max_val": 10.0,
    "register_type": "holding"
  }
]
```

#### Address Resolution Table

| Conventional Notation | Function Code | Protocol Address (`address`) | Description |
|:----------------------|:--------------|:-----------------------------|:------------|
| `40001` – `49999`     | FC03 / FC16   | `register - 40001` (0..9998) | 16-bit Holding Register |
| `30001` – `39999`     | FC04          | `register - 30001` (0..9998) | 16-bit Input Register |
| `0` – `9999`          | Configurable  | `register` (direct offset)   | Direct 0-based offset |

### 10.2 ModbusSimulator Capabilities

`ModbusSimulator` provides an in-process, hardware-free Modbus TCP server:
- **Dynamic Port Binding**: `ModbusSimulator(port=0)` binds to an available OS ephemeral port.
- **Three Operational Regimes**:
  - `idle`: Minimal temperature, low vibration (0.15 mm/s), 0 RPM.
  - `nominal`: Standard operational load, 45.0 °C, 1.25 mm/s, 3600 RPM.
  - `degraded`: Thermal overload (78.0 °C), severe harmonic vibration (5.60 mm/s), 22.0 A current.
- **Physical Noise Perturbation (`sim.step()`)**: Applies Gaussian jitter across cycles to prevent latent representation collapse (DEF-007).
- **CLI Utility**: Executable directly via `python scripts/run_modbus_sim.py --port 5020 --state nominal`.

### 10.3 Dynamic World Model Sizing (Layer 3) & DEF-008 Compliance

When onboarding a Modbus machine, `WorldModelConfig` is sized dynamically from the register map:

```python
reading = adapter.get_reading("cnc_spindle_01")
cfg = WorldModelConfig(
    domain=adapter.domain_id,
    feature_dim=len(reading.features),  # Dynamically matched to register channels
    is_trained=adapter.is_trained,      # Strictly False until trained checkpoint exists
)
model = WorldModel(cfg)

# DEF-008: Calling predict() before training raises UntrainedModelError
model.predict(window)  # -> UntrainedModelError: DEF-008 prohibits silent zero-shot inference
```
