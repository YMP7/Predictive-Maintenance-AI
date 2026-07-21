"""
C-MAPSS Domain Adapter — ATLAS Machine Adapter Layer
=====================================================
Streams NASA C-MAPSS turbofan dataset (FD001–FD004) as NormalizedReadings.

Dataset Setup
-------------
Download from: https://data.nasa.gov/dataset/C-MAPSS-Aircraft-Engine-Simulator-Data/xaut-bemq
(or search: "NASA C-MAPSS CMAPSSData.zip")

Place files in:  data/cmapss/
Required files:
  - train_FD001.txt   (used for World Model training + AMKB population)
  - test_FD001.txt    (used for RUL benchmarking)
  - RUL_FD001.txt     (ground-truth RUL labels for test set)
  - train_FD002.txt, train_FD003.txt, train_FD004.txt  (optional, for multi-condition runs)

C-MAPSS Schema
--------------
Each row: [unit_id, cycle, op_set_1, op_set_2, op_set_3, s1..s21]
  - unit_id: engine unit number (1..N_units)
  - cycle:   current flight cycle (monotonically increasing per unit)
  - op_set_1,2,3: operational settings (altitude, TRA, h)
  - s1..s21: 21 sensor measurements

This adapter exposes a subset of 14 informative sensors (the 7 constant sensors
are dropped automatically — they carry no predictive signal).

Usage
-----
    adapter = CMAPSSAdapter(subset="FD001", split="train")
    adapter.connect()
    reading = adapter.get_reading("unit_1")
    print(reading.health_index, reading.rul_label)

Iteration Modes
---------------
  STREAMING:  Steps through cycles sequentially (one get_reading() = one row).
              Use for training the World Model and populating the AMKB.
  BENCHMARK:  Returns the LAST window for each unit (test set only).
              Use for RUL benchmarking against ground-truth labels.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np

from server.adapters.base_adapter import (
    AdapterStatus,
    DatasetNotFoundError,
    MachineAdapter,
    NormalizedReading,
)

logger = logging.getLogger("ATLAS.CMAPSSAdapter")

# ---------------------------------------------------------------------------
# C-MAPSS constants
# ---------------------------------------------------------------------------

# Column names matching the raw .txt format
_RAW_COLS = (
    ["unit_id", "cycle", "op_set_1", "op_set_2", "op_set_3"]
    + [f"s{i}" for i in range(1, 22)]
)

# Sensors that are constant across all conditions (zero variance) — dropped
_CONSTANT_SENSORS = {"s1", "s5", "s6", "s10", "s16", "s18", "s19"}

# The 14 informative sensors used as features
INFORMATIVE_SENSORS = [s for s in [f"s{i}" for i in range(1, 22)] if s not in _CONSTANT_SENSORS]

# Operational settings used as operational context
OP_SETTINGS = ["op_set_1", "op_set_2", "op_set_3"]

# Max RUL cap used during training (standard CMAPSS practice: cap at 125)
MAX_RUL_CAP = 125

# Supported subsets
VALID_SUBSETS = {"FD001", "FD002", "FD003", "FD004"}

# Data directory (relative to project root, resolved at import time)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = _PROJECT_ROOT / "data" / "cmapss"

DOWNLOAD_INSTRUCTIONS = """
To download the NASA C-MAPSS dataset:

  1. Visit: https://data.nasa.gov/dataset/C-MAPSS-Aircraft-Engine-Simulator-Data/xaut-bemq
     OR: https://www.kaggle.com/datasets/behrad3d/nasa-cmaps

  2. Download 'CMAPSSData.zip' and extract.

  3. Place these files in: {data_dir}/
       train_FD001.txt
       test_FD001.txt
       RUL_FD001.txt
       (+ FD002/003/004 variants if needed)

Then re-run: python server/atlas/train_rul.py --domain cmapss
""".format(data_dir=DATA_DIR)


# ---------------------------------------------------------------------------
# Low-level loader
# ---------------------------------------------------------------------------

def _load_raw(filepath: Path) -> np.ndarray:
    """Load a C-MAPSS .txt file into a (N_rows, N_cols) float array."""
    if not filepath.exists():
        raise DatasetNotFoundError(
            dataset=filepath.name,
            expected_path=str(filepath),
            instructions=DOWNLOAD_INSTRUCTIONS,
        )
    data = np.loadtxt(str(filepath))
    # Some versions have trailing whitespace that creates an extra column
    if data.shape[1] == len(_RAW_COLS) + 1:
        data = data[:, : len(_RAW_COLS)]
    return data


def _load_rul_labels(filepath: Path) -> np.ndarray:
    """Load RUL_FD00X.txt which is one number per test unit."""
    if not filepath.exists():
        raise DatasetNotFoundError(
            dataset=filepath.name,
            expected_path=str(filepath),
            instructions=DOWNLOAD_INSTRUCTIONS,
        )
    return np.loadtxt(str(filepath))


# ---------------------------------------------------------------------------
# Per-unit sequence builder
# ---------------------------------------------------------------------------

class _UnitSequence:
    """Holds all cycles for a single engine unit from one split."""

    def __init__(
        self,
        unit_id: int,
        data: np.ndarray,
        rul_final: Optional[float],
        feature_min: np.ndarray,
        feature_max: np.ndarray,
    ) -> None:
        self.unit_id = unit_id
        self._raw = data          # shape (n_cycles, n_cols)
        self.rul_final = rul_final
        self._feature_min = feature_min
        self._feature_max = feature_max
        self._cursor = 0          # for streaming mode

        # Pre-compute RUL labels per cycle (for training set)
        total_cycles = int(self._raw[:, 1].max())
        if rul_final is not None:
            # Test set: RUL at last observed cycle = rul_final
            # We back-calculate per cycle
            last_cycle = int(self._raw[-1, 1])
            self._rul_per_cycle: Optional[np.ndarray] = (
                np.array([rul_final + (last_cycle - int(row[1])) for row in self._raw])
            )
        else:
            # Training set: unit fails at total_cycles, RUL = (total - current)
            self._rul_per_cycle = np.array(
                [max(0, total_cycles - int(row[1])) for row in self._raw]
            )

    # ------------------------------------------------------------------

    @property
    def machine_id(self) -> str:
        return f"unit_{self.unit_id}"

    @property
    def n_cycles(self) -> int:
        return len(self._raw)

    @property
    def is_exhausted(self) -> bool:
        return self._cursor >= self.n_cycles

    def reset(self) -> None:
        self._cursor = 0

    # ------------------------------------------------------------------

    def _row_to_reading(self, row_idx: int, domain: str, subset: str) -> NormalizedReading:
        row = self._raw[row_idx]
        cycle = int(row[1])

        # Raw sensor values (informative only)
        col_offset = 5  # unit_id, cycle, op1, op2, op3
        sensor_cols = {s: i + col_offset for i, s in enumerate([f"s{j}" for j in range(1, 22)])}

        raw_features: Dict[str, float] = {
            s: float(row[sensor_cols[s]]) for s in INFORMATIVE_SENSORS
        }
        op_ctx: Dict[str, float] = {
            op: float(row[i + 2]) for i, op in enumerate(OP_SETTINGS)
        }

        # Normalise features to [0, 1] using train-set min/max
        feature_arr = np.array([raw_features[s] for s in INFORMATIVE_SENSORS])
        denom = self._feature_max - self._feature_min
        denom = np.where(denom == 0, 1.0, denom)  # avoid div-by-zero
        norm_arr = np.clip((feature_arr - self._feature_min) / denom, 0.0, 1.0)
        features: Dict[str, float] = {
            s: float(norm_arr[i]) for i, s in enumerate(INFORMATIVE_SENSORS)
        }

        # RUL label (capped at MAX_RUL_CAP for training stability)
        rul_raw = float(self._rul_per_cycle[row_idx])
        rul_capped = min(rul_raw, MAX_RUL_CAP)

        # Health index: 1 - RUL/MAX_RUL (0 = fresh, 1 = at failure)
        health_index = float(np.clip(1.0 - (rul_capped / MAX_RUL_CAP), 0.0, 1.0))

        return NormalizedReading(
            domain=domain,
            machine_id=self.machine_id,
            timestamp=NormalizedReading.timestamp_now(),
            health_index=health_index,
            cycle=cycle,
            rul_label=rul_raw,
            features=features,
            raw_features={s: raw_features[s] for s in INFORMATIVE_SENSORS},
            operational_ctx=op_ctx,
            metadata={
                "subset": subset,
                "total_cycles": self.n_cycles,
                "rul_capped": rul_capped,
                "max_rul_cap": MAX_RUL_CAP,
            },
            adapter_status=AdapterStatus.STREAMING.value,
        )

    # ------------------------------------------------------------------

    def next_reading(self, domain: str, subset: str) -> Optional[NormalizedReading]:
        """Stream: advance cursor and return the reading at current position."""
        if self.is_exhausted:
            return None
        r = self._row_to_reading(self._cursor, domain, subset)
        self._cursor += 1
        return r

    def last_reading(self, domain: str, subset: str) -> NormalizedReading:
        """Benchmark mode: return only the last observed cycle."""
        return self._row_to_reading(self.n_cycles - 1, domain, subset)

    def all_readings(self, domain: str, subset: str) -> List[NormalizedReading]:
        """Return all cycles as a list (for batch AMKB population)."""
        return [self._row_to_reading(i, domain, subset) for i in range(self.n_cycles)]


# ---------------------------------------------------------------------------
# CMAPSSAdapter
# ---------------------------------------------------------------------------

class CMAPSSAdapter(MachineAdapter):
    """
    ATLAS adapter for the NASA C-MAPSS turbofan degradation dataset.

    Parameters
    ----------
    subset      : "FD001" | "FD002" | "FD003" | "FD004"
    split       : "train" (streaming, RUL computed from max cycle)
                | "test"  (benchmark, RUL from RUL_FDxxx.txt labels)
    data_dir    : Path to directory containing the .txt files (default: data/cmapss/)
    max_units   : Limit number of engine units loaded (None = all). Useful for
                  quick development runs.
    """

    def __init__(
        self,
        subset: str = "FD001",
        split: str = "train",
        data_dir: Optional[Path] = None,
        max_units: Optional[int] = None,
    ) -> None:
        super().__init__()
        if subset not in VALID_SUBSETS:
            raise ValueError(f"subset must be one of {VALID_SUBSETS}, got '{subset}'")
        if split not in ("train", "test"):
            raise ValueError(f"split must be 'train' or 'test', got '{split}'")

        self._subset = subset
        self._split = split
        self._data_dir = Path(data_dir) if data_dir else DATA_DIR
        self._max_units = max_units

        self._units: Dict[str, _UnitSequence] = {}
        self._feature_min: Optional[np.ndarray] = None
        self._feature_max: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def domain_id(self) -> str:
        return "cmapss"

    @property
    def machine_ids(self) -> List[str]:
        return list(self._units.keys())

    @property
    def subset(self) -> str:
        return self._subset

    @property
    def split(self) -> str:
        return self._split

    @property
    def n_units(self) -> int:
        return len(self._units)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        logger.info(f"Loading C-MAPSS {self._subset} [{self._split}]...")
        train_path = self._data_dir / f"train_{self._subset}.txt"
        test_path  = self._data_dir / f"test_{self._subset}.txt"
        rul_path   = self._data_dir / f"RUL_{self._subset}.txt"

        # Always load train data to compute normalisation stats
        train_raw = _load_raw(train_path)

        # Compute min/max from train set for the 14 informative sensors
        col_offset = 5
        sensor_indices = [
            col_offset + i
            for i, s in enumerate([f"s{j}" for j in range(1, 22)])
            if s in INFORMATIVE_SENSORS
        ]
        train_sensors = train_raw[:, sensor_indices]
        self._feature_min = train_sensors.min(axis=0)
        self._feature_max = train_sensors.max(axis=0)

        if self._split == "train":
            raw = train_raw
            rul_labels: Optional[np.ndarray] = None
        else:
            raw = _load_raw(test_path)
            rul_labels = _load_rul_labels(rul_path)

        # Group by unit_id
        unit_ids = np.unique(raw[:, 0]).astype(int)
        if self._max_units:
            unit_ids = unit_ids[: self._max_units]

        for uid in unit_ids:
            unit_data = raw[raw[:, 0] == uid]
            rul_final = float(rul_labels[uid - 1]) if rul_labels is not None else None
            self._units[f"unit_{uid}"] = _UnitSequence(
                unit_id=uid,
                data=unit_data,
                rul_final=rul_final,
                feature_min=self._feature_min,
                feature_max=self._feature_max,
            )

        self._status = AdapterStatus.STREAMING
        logger.info(
            f"C-MAPSS {self._subset} loaded: {len(self._units)} units, "
            f"split={self._split}"
        )

    def _disconnect(self) -> None:
        self._units.clear()
        logger.info(f"C-MAPSS {self._subset} adapter disconnected.")

    # ------------------------------------------------------------------
    # Reading interface
    # ------------------------------------------------------------------

    def get_reading(self, machine_id: str) -> NormalizedReading:
        """
        Stream mode: return the next cycle for machine_id.
        When the unit is exhausted, it auto-resets (loops) so the adapter
        is always live during development. For a single-pass evaluation,
        check `unit_exhausted(machine_id)` before calling.
        """
        if machine_id not in self._units:
            raise KeyError(f"Unknown machine_id '{machine_id}' for CMAPSSAdapter")
        unit = self._units[machine_id]
        if unit.is_exhausted:
            unit.reset()
        reading = unit.next_reading(self.domain_id, self._subset)
        return reading  # type: ignore[return-value]  # reset guarantees non-None

    def get_benchmark_reading(self, machine_id: str) -> NormalizedReading:
        """Benchmark mode: return only the last observed cycle (for RUL scoring)."""
        if machine_id not in self._units:
            raise KeyError(f"Unknown machine_id '{machine_id}'")
        return self._units[machine_id].last_reading(self.domain_id, self._subset)

    def get_unit_history(self, machine_id: str) -> List[NormalizedReading]:
        """Return ALL cycles for a unit (for batch AMKB population)."""
        if machine_id not in self._units:
            raise KeyError(f"Unknown machine_id '{machine_id}'")
        return self._units[machine_id].all_readings(self.domain_id, self._subset)

    def unit_exhausted(self, machine_id: str) -> bool:
        """True if the unit has no more cycles left in streaming mode."""
        if machine_id not in self._units:
            return True
        return self._units[machine_id].is_exhausted

    def reset_unit(self, machine_id: str) -> None:
        """Reset streaming cursor for a unit back to cycle 0."""
        if machine_id in self._units:
            self._units[machine_id].reset()

    def reset_all(self) -> None:
        """Reset all unit cursors."""
        for unit in self._units.values():
            unit.reset()

    # ------------------------------------------------------------------
    # Batch iteration helpers
    # ------------------------------------------------------------------

    def iter_all_readings(self) -> Iterator[NormalizedReading]:
        """
        Yield every reading from every unit, in unit/cycle order.
        Useful for batch AMKB population and World Model training.
        """
        self.reset_all()
        for machine_id in sorted(self._units):
            unit = self._units[machine_id]
            for i in range(unit.n_cycles):
                yield unit._row_to_reading(i, self.domain_id, self._subset)

    def describe(self) -> dict:
        base = super().describe()
        base.update({
            "subset": self._subset,
            "split": self._split,
            "n_units": self.n_units,
            "informative_sensors": INFORMATIVE_SENSORS,
            "feature_dim": len(INFORMATIVE_SENSORS),
            "max_rul_cap": MAX_RUL_CAP,
            "data_dir": str(self._data_dir),
        })
        return base

    # ------------------------------------------------------------------
    # PHM scoring function (standard C-MAPSS literature metric)
    # ------------------------------------------------------------------

    @staticmethod
    def phm_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        Asymmetric PHM scoring function from the 2008 PHM challenge.
        Penalises late predictions (under-estimation) more heavily than early ones.

            s_i = exp(-d/13) - 1   if d < 0  (early prediction — light penalty)
            s_i = exp( d/10) - 1   if d >= 0 (late prediction  — heavy penalty)
        where d = y_pred - y_true

        Returns the sum of s_i across all predictions. Lower is better.
        """
        d = y_pred - y_true
        scores = np.where(d < 0, np.exp(-d / 13.0) - 1.0, np.exp(d / 10.0) - 1.0)
        return float(np.sum(scores))
