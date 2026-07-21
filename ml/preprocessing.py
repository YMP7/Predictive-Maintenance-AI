"""
ml/preprocessing.py — ATLAS C-MAPSS Preprocessing Pipeline
============================================================
Week 2 deliverable: a clean, reusable preprocessing pipeline that takes raw
C-MAPSS files in and produces windowed, normalized PyTorch-ready tensors out.

This is the standalone ML-layer preprocessing module. The CMAPSSAdapter
(server/adapters/cmapss_adapter.py) calls this internally for the server
pipeline. Use this directly for:
  - Training scripts (server/atlas/train_rul.py)
  - Notebooks (notebooks/week1_eda.ipynb, week4_training.ipynb)
  - Ablation/benchmark scripts (scripts/run_ablations.py)

Usage
-----
    from ml.preprocessing import CMAPSSPreprocessor

    prep = CMAPSSPreprocessor(subset="FD001", seq_len=30)
    X_train, y_train = prep.get_train_windows()
    X_test,  y_test  = prep.get_test_windows()

    # Or: get raw DataFrames for EDA
    train_df = prep.load_raw_train()
    prep.plot_sensor_variance(train_df)         # identify constant sensors
    prep.plot_unit_degradation(train_df, unit=1)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("ATLAS.preprocessing")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = _PROJECT_ROOT / "data" / "cmapss"

# Raw column names (no headers in C-MAPSS files)
RAW_COLUMNS = (
    ["unit", "cycle", "op1", "op2", "op3"]
    + [f"s{i}" for i in range(1, 22)]
)

# Sensors that are constant (near-zero variance) in FD001.
# These carry no predictive signal and are dropped.
# Run plot_sensor_variance() on a new subset to verify before extending.
CONSTANT_SENSORS_FD001 = {"s1", "s5", "s6", "s10", "s16", "s18", "s19"}

# The 14 informative sensors used as model features (FD001 default)
INFORMATIVE_SENSORS_FD001 = [
    s for s in [f"s{i}" for i in range(1, 22)]
    if s not in CONSTANT_SENSORS_FD001
]

# Standard RUL ceiling (piecewise linear target — early-life RUL is unreliable)
DEFAULT_RUL_CAP = 125

# Standard sliding window length
DEFAULT_SEQ_LEN = 30


# ---------------------------------------------------------------------------
# CMAPSSPreprocessor
# ---------------------------------------------------------------------------

class CMAPSSPreprocessor:
    """
    Full preprocessing pipeline for C-MAPSS FD001–FD004.

    Steps performed (in order):
      1. Load raw .txt files and assign column names
      2. Compute RUL labels for training set (max_cycle - current_cycle)
      3. Clip RUL at `rul_cap` (default 125)
      4. Drop constant/non-informative sensors
      5. Normalise features (z-score, fit on train, applied to test — no leakage)
      6. Slice into sliding windows of length `seq_len`

    Parameters
    ----------
    subset      : "FD001" | "FD002" | "FD003" | "FD004"
    seq_len     : Sliding window length in cycles (default 30)
    rul_cap     : RUL ceiling for piecewise linear target (default 125)
    drop_sensors: Set of sensor names to drop (default: CONSTANT_SENSORS_FD001)
    data_dir    : Path to directory containing .txt files (default: data/cmapss/)
    """

    def __init__(
        self,
        subset: str = "FD001",
        seq_len: int = DEFAULT_SEQ_LEN,
        rul_cap: int = DEFAULT_RUL_CAP,
        drop_sensors: Optional[set] = None,
        data_dir: Optional[Path] = None,
    ) -> None:
        self.subset = subset
        self.seq_len = seq_len
        self.rul_cap = rul_cap
        self.drop_sensors = drop_sensors if drop_sensors is not None else CONSTANT_SENSORS_FD001
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR

        self._feature_mean: Optional[np.ndarray] = None
        self._feature_std:  Optional[np.ndarray] = None
        self._feature_cols: Optional[List[str]]  = None

    # ------------------------------------------------------------------
    # Step 1 — Raw loading
    # ------------------------------------------------------------------

    def load_raw(self, split: str) -> pd.DataFrame:
        """
        Load a raw C-MAPSS .txt file and assign column names.

        Parameters
        ----------
        split : "train" | "test"

        Returns
        -------
        pd.DataFrame with columns: unit, cycle, op1, op2, op3, s1..s21
        """
        filename = f"{split}_{self.subset}.txt"
        filepath = self.data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(
                f"C-MAPSS file not found: {filepath}\n"
                f"Download from: https://www.kaggle.com/datasets/behrad3d/nasa-cmaps\n"
                f"Place in: {self.data_dir}/"
            )
        df = pd.read_csv(str(filepath), sep=r"\s+", header=None, names=RAW_COLUMNS)
        # Drop any extra columns from trailing whitespace
        df = df.loc[:, RAW_COLUMNS[:len(df.columns)]]
        logger.info(f"Loaded {split}_{self.subset}.txt: {len(df)} rows, {df['unit'].nunique()} units")
        return df

    def load_raw_train(self) -> pd.DataFrame:
        return self.load_raw("train")

    def load_raw_test(self) -> pd.DataFrame:
        return self.load_raw("test")

    def load_rul_labels(self) -> np.ndarray:
        """Load ground-truth RUL labels for the test set."""
        filepath = self.data_dir / f"RUL_{self.subset}.txt"
        if not filepath.exists():
            raise FileNotFoundError(f"RUL file not found: {filepath}")
        return np.loadtxt(str(filepath))

    # ------------------------------------------------------------------
    # Step 2–3 — RUL computation + clipping
    # ------------------------------------------------------------------

    def compute_train_rul(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add a `rul` column to the training DataFrame.
        For each unit: rul = max_cycle_for_unit - current_cycle
        Then clip at `self.rul_cap`.

        Sorts by (unit, cycle) first — without this, out-of-order rows produce
        correct shape output but silently wrong RUL values inside windows.
        """
        # Guarantee row order before any window computation
        df = df.sort_values(["unit", "cycle"]).reset_index(drop=True)

        max_cycles = df.groupby("unit")["cycle"].max().rename("max_cycle")
        df = df.merge(max_cycles, on="unit")
        df["rul"] = df["max_cycle"] - df["cycle"]
        df["rul"] = df["rul"].clip(upper=self.rul_cap)
        df = df.drop(columns=["max_cycle"])
        return df

    # ------------------------------------------------------------------
    # Step 4 — Drop constant sensors
    # ------------------------------------------------------------------

    def get_feature_cols(self, df: Optional[pd.DataFrame] = None) -> List[str]:
        """Return the list of sensor column names after dropping constants."""
        if self._feature_cols is not None:
            return self._feature_cols
        all_sensor_cols = [f"s{i}" for i in range(1, 22)]
        self._feature_cols = [s for s in all_sensor_cols if s not in self.drop_sensors]
        return self._feature_cols

    # ------------------------------------------------------------------
    # Step 5 — Normalisation (fit on train, apply to both)
    # ------------------------------------------------------------------

    def fit_normalizer(self, train_df: pd.DataFrame) -> None:
        """
        Fit z-score normaliser on training data.
        Must be called before transform_features() on either split.

        IMPORTANT: fit ONLY on train_df — never on test_df.
        Fitting on test would leak test statistics into the training pipeline.
        """
        cols = self.get_feature_cols(train_df)
        data = train_df[cols].values.astype(np.float32)
        self._feature_mean = data.mean(axis=0)
        self._feature_std  = data.std(axis=0)
        # Replace zero-std with 1 to avoid division by zero (constant sensors
        # should have been dropped already, but belt-and-suspenders)
        self._feature_std = np.where(self._feature_std == 0, 1.0, self._feature_std)
        logger.info(f"Normaliser fit on {len(data)} training rows, {len(cols)} features")

    def transform_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Apply z-score normalisation to sensor columns.
        fit_normalizer() must be called first.

        Returns
        -------
        np.ndarray, shape (n_rows, n_features) — normalised sensor values
        """
        if self._feature_mean is None:
            raise RuntimeError("Call fit_normalizer(train_df) before transform_features()")
        cols = self.get_feature_cols(df)
        data = df[cols].values.astype(np.float32)
        return (data - self._feature_mean) / self._feature_std

    # ------------------------------------------------------------------
    # Step 6 — Sliding window construction
    # ------------------------------------------------------------------

    def make_windows(
        self,
        df: pd.DataFrame,
        features: np.ndarray,
        rul_col: Optional[str] = "rul",
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build sliding windows from a per-unit time series.

        For each cycle t in unit u, the window is the last `seq_len` cycles
        ending at t (left-zero-padded if fewer than seq_len cycles exist).

        Parameters
        ----------
        df       : DataFrame with 'unit' and 'cycle' columns
        features : Normalised feature array, shape (n_rows, n_features)
        rul_col  : Column name for RUL target ('rul' for train, None for test)

        Returns
        -------
        X : np.ndarray, shape (n_windows, seq_len, n_features)
        y : np.ndarray, shape (n_windows,) — RUL values (or empty array if rul_col is None)
        """
        X_list: List[np.ndarray] = []
        y_list: List[float] = []

        n_feat = features.shape[1]
        units = df["unit"].unique()

        for uid in sorted(units):
            mask = (df["unit"] == uid).values
            unit_features = features[mask]       # (n_cycles, n_features)
            unit_rul = df.loc[mask, rul_col].values if rul_col and rul_col in df.columns else None

            for i in range(len(unit_features)):
                window = np.zeros((self.seq_len, n_feat), dtype=np.float32)
                start = max(0, i - self.seq_len + 1)
                chunk = unit_features[start:i + 1]
                window[-len(chunk):] = chunk
                X_list.append(window)
                if unit_rul is not None:
                    y_list.append(float(unit_rul[i]))

        X = np.stack(X_list, axis=0)
        y = np.array(y_list, dtype=np.float32) if y_list else np.array([])
        return X, y

    # ------------------------------------------------------------------
    # Convenience: full pipeline in two calls
    # ------------------------------------------------------------------

    def get_train_windows(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Full training pipeline: load → RUL label → normalise (fit here) → window.

        Returns
        -------
        X_train : shape (N, seq_len, n_features)
        y_train : shape (N,)
        """
        df = self.load_raw_train()
        df = self.compute_train_rul(df)
        self.fit_normalizer(df)
        features = self.transform_features(df)
        return self.make_windows(df, features, rul_col="rul")

    def get_test_windows(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Test pipeline: load → apply pre-fitted normaliser → last-window per unit.
        fit_normalizer() must have been called first (via get_train_windows()).

        For RUL benchmarking, only the LAST window per unit is used (standard protocol).

        Returns
        -------
        X_test : shape (n_units, seq_len, n_features) — one window per unit
        y_test : shape (n_units,)                     — ground-truth RUL
        """
        df = self.load_raw_test()
        rul_labels = self.load_rul_labels()
        features = self.transform_features(df)

        X_list: List[np.ndarray] = []
        y_list: List[float] = []
        n_feat = features.shape[1]

        for i, uid in enumerate(sorted(df["unit"].unique())):
            mask = (df["unit"] == uid).values
            unit_features = features[mask]

            # Take LAST seq_len cycles (standard benchmark protocol)
            window = np.zeros((self.seq_len, n_feat), dtype=np.float32)
            chunk = unit_features[-self.seq_len:]
            window[-len(chunk):] = chunk
            X_list.append(window)
            y_list.append(float(rul_labels[i]))

        return np.stack(X_list), np.array(y_list, dtype=np.float32)

    # ------------------------------------------------------------------
    # EDA helpers (Week 1 deliverables)
    # ------------------------------------------------------------------

    def sensor_variance_report(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute variance for each sensor column.
        Use this to identify constant/non-informative sensors.

        Returns a DataFrame sorted ascending by variance (lowest = most constant).
        """
        sensor_cols = [f"s{i}" for i in range(1, 22)]
        variances = df[sensor_cols].var()
        return variances.reset_index().rename(
            columns={"index": "sensor", 0: "variance"}
        ).sort_values("variance").reset_index(drop=True)

    def unit_cycle_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return min/max/mean cycle count per unit."""
        return (
            df.groupby("unit")["cycle"]
            .agg(["min", "max", "count"])
            .rename(columns={"max": "total_cycles", "count": "n_rows"})
            .reset_index()
        )

    def describe(self) -> dict:
        return {
            "subset": self.subset,
            "seq_len": self.seq_len,
            "rul_cap": self.rul_cap,
            "feature_cols": self.get_feature_cols(),
            "n_features": len(self.get_feature_cols()),
            "dropped_sensors": list(self.drop_sensors),
            "normaliser_fit": self._feature_mean is not None,
        }
