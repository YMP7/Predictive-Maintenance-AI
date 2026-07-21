"""
RUL Engine — ATLAS Cognition Core
==================================
Inference wrapper around WorldModel. Maintains a per-machine sliding window
of NormalizedReading feature vectors and produces RULPredictions.

Design
------
- Primary path: WorldModel LSTM inference (when a trained model exists)
- Fallback path: EMA-based linear degradation trend (identical logic to the
  existing server/ai_agent.py RULEstimator) — guarantees predictions even
  before the LSTM is trained.
- The two paths are transparent to callers — they always receive a RULPrediction.
- The `using_lstm` field in RULPrediction tells the caller which path fired.

The RULEngine is the drop-in replacement for the existing RULEstimator in
ai_agent.py. It is wire-compatible: same input (machine_id + reading dict),
same useful fields in the output (rul_days, confidence, status).

Usage
-----
    from server.atlas.rul_engine import RULEngine

    engine = RULEngine(domain="cmapss")  # loads model if available
    result = engine.update(machine_id="unit_1", reading=normalized_reading)
    print(result.rul_cycles, result.confidence, result.using_lstm)
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from server.adapters.base_adapter import NormalizedReading
from server.atlas.world_model import (
    MODELS_DIR,
    WorldModel,
    WorldModelConfig,
    prepare_window,
)

logger = logging.getLogger("ATLAS.RULEngine")


# ---------------------------------------------------------------------------
# RULPrediction output schema
# ---------------------------------------------------------------------------

@dataclass
class RULPrediction:
    """
    Output of RULEngine.update().

    Attributes
    ----------
    machine_id    : Which machine this prediction is for
    rul_cycles    : Predicted RUL in dataset cycles (or simulation steps)
    rul_days      : Estimated RUL in wall-clock days (cycles * scale_factor)
    confidence    : Prediction confidence in [0, 1]
    uncertainty   : Std-dev estimate (used by SimulationEngine for Monte Carlo)
    status        : "Stable" | "Degrading" | "Critical" | "Insufficient Data"
    using_lstm    : True if the prediction came from the LSTM model
    state_vector  : Latent state from WorldModel (None if EMA fallback)
    health_index  : Normalised degradation in [0, 1] (0=fresh, 1=failed)
    """
    machine_id:   str
    rul_cycles:   float
    rul_days:     float
    confidence:   float
    uncertainty:  float
    status:       str
    using_lstm:   bool
    state_vector: Optional[np.ndarray]
    health_index: float

    def to_dict(self) -> dict:
        return {
            "machine_id":   self.machine_id,
            "rul_cycles":   round(self.rul_cycles, 2),
            "rul_days":     round(self.rul_days, 2),
            "confidence":   round(self.confidence, 4),
            "uncertainty":  round(self.uncertainty, 4),
            "status":       self.status,
            "using_lstm":   self.using_lstm,
            "health_index": round(self.health_index, 4),
            "state_vector": (
                self.state_vector.tolist() if self.state_vector is not None else None
            ),
        }


# ---------------------------------------------------------------------------
# EMA fallback (mirrors existing RULEstimator logic)
# ---------------------------------------------------------------------------

class _EMAFallback:
    """
    Linear-trend RUL estimator based on exponential moving average.
    Used as a fallback when no trained WorldModel is available.
    Preserves the calibrated behaviour of the existing ai_agent.RULEstimator.
    """

    ALPHA = 0.15
    CRITICAL_THRESHOLD = 0.8
    MIN_HISTORY = 10
    STEPS_TO_DAYS = 0.14   # 1 simulation step ≈ 0.14 real days (calibrated)
    MAX_RUL_DAYS = 365

    def __init__(self) -> None:
        self._history: Dict[str, List[float]] = defaultdict(list)

    def update(self, machine_id: str, health_index: float) -> None:
        hist = self._history[machine_id]
        hist.append(health_index)
        if len(hist) > 1000:
            hist.pop(0)

    def predict(self, machine_id: str) -> Tuple[float, float, float, str]:
        """Returns (rul_days, confidence, uncertainty, status)."""
        hist = self._history.get(machine_id, [])
        if len(hist) < self.MIN_HISTORY:
            return 30.0, 0.0, 15.0, "Insufficient Data"

        y_raw = np.array(hist)
        # Median filter
        window = 5
        y_med = np.copy(y_raw)
        for i in range(len(y_raw)):
            s, e = max(0, i - window // 2), min(len(y_raw), i + window // 2 + 1)
            y_med[i] = np.median(y_raw[s:e])
        # EMA
        y_ema = np.zeros_like(y_med)
        y_ema[0] = y_med[0]
        for i in range(1, len(y_med)):
            y_ema[i] = self.ALPHA * y_med[i] + (1 - self.ALPHA) * y_ema[i - 1]

        current = float(y_ema[-1])
        x = np.arange(len(y_ema))
        m, _ = np.polyfit(x, y_ema, 1)

        if current >= self.CRITICAL_THRESHOLD:
            return 0.0, 0.95, 0.5, "Critical"

        y_pred = m * x + _
        ss_res = np.sum((y_ema - y_pred) ** 2)
        ss_tot = np.sum((y_ema - np.mean(y_ema)) ** 2)
        r_sq = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        confidence = float(np.clip(r_sq, 0.5, 0.95))
        uncertainty = float(np.std(y_ema) * self.STEPS_TO_DAYS * 10)

        if m <= 0:
            headroom = max(0.0, self.CRITICAL_THRESHOLD - current)
            rul_days = float(min(self.MAX_RUL_DAYS, max(30, headroom * 200)))
            return rul_days, confidence, uncertainty, "Stable"

        steps = (self.CRITICAL_THRESHOLD - current) / m
        rul_days = float(min(self.MAX_RUL_DAYS, max(1, steps * self.STEPS_TO_DAYS)))
        status = "Degrading" if current > 0.5 else "Stable"
        if rul_days > 30:
            status = "Stable"
        return rul_days, confidence, uncertainty, status


# ---------------------------------------------------------------------------
# RULEngine — primary inference class
# ---------------------------------------------------------------------------

class RULEngine:
    """
    Production RUL inference engine for ATLAS.

    Parameters
    ----------
    domain         : Domain identifier (used to locate the saved model)
    config         : WorldModelConfig override (optional — inferred from checkpoint)
    cycles_per_day : Scale factor to convert RUL cycles → days.
                     C-MAPSS: 1 cycle ≈ 1 flight (≈1 day). Laptop/mobile: 1 step ≈ 0.14 day.
    """

    def __init__(
        self,
        domain: str = "cmapss",
        config: Optional[WorldModelConfig] = None,
        cycles_per_day: float = 1.0,
    ) -> None:
        self.domain = domain
        self.cycles_per_day = cycles_per_day
        self._lock = threading.Lock()

        # Per-machine sliding windows: machine_id -> List[feature_vector]
        self._windows: Dict[str, List[List[float]]] = defaultdict(list)

        # EMA fallback is always kept live (used for confidence cross-check)
        self._ema = _EMAFallback()

        # Try to load a trained WorldModel
        self._model: Optional[WorldModel] = None
        self._config: WorldModelConfig = config or WorldModelConfig(domain=domain)
        self._try_load_model()

    # ------------------------------------------------------------------

    def _try_load_model(self) -> None:
        """Attempt to load a trained WorldModel checkpoint."""
        model = WorldModel.load_for_domain(self.domain)
        if model is not None:
            self._model = model
            self._config = model.config
            logger.info(f"[{self.domain}] RULEngine: LSTM model loaded ✓")
        else:
            logger.info(
                f"[{self.domain}] RULEngine: No LSTM model found — EMA fallback active. "
                "Train with: python server/atlas/train_rul.py --domain cmapss"
            )

    def reload_model(self) -> bool:
        """
        Hot-reload the model (called by LearningEngine after retraining).
        Returns True if a new model was loaded.
        """
        with self._lock:
            try:
                model = WorldModel.load_for_domain(self.domain)
                if model is not None:
                    self._model = model
                    self._config = model.config
                    logger.info(f"[{self.domain}] RULEngine: model hot-reloaded ✓")
                    return True
            except Exception as e:
                logger.error(f"[{self.domain}] RULEngine reload failed: {e}")
        return False

    # ------------------------------------------------------------------

    @property
    def using_lstm(self) -> bool:
        return self._model is not None

    # ------------------------------------------------------------------

    def update(
        self,
        machine_id: str,
        reading: NormalizedReading,
    ) -> RULPrediction:
        """
        Main entry point. Call once per new reading.

        Updates the sliding window for machine_id and returns a fresh
        RULPrediction. Thread-safe.
        """
        with self._lock:
            # Update EMA fallback regardless (cheap)
            self._ema.update(machine_id, reading.health_index)

            # Update sliding window
            window_list = self._windows[machine_id]
            window_list.append(reading.feature_vector)
            seq_len = self._config.seq_len
            if len(window_list) > seq_len:
                window_list.pop(0)

            if self._model is not None:
                return self._lstm_predict(machine_id, reading, window_list)
            else:
                return self._ema_predict(machine_id, reading)

    # ------------------------------------------------------------------

    def _lstm_predict(
        self,
        machine_id: str,
        reading: NormalizedReading,
        window_list: List[List[float]],
    ) -> RULPrediction:
        """LSTM path."""
        window = prepare_window(
            window_list,
            seq_len=self._config.seq_len,
            feature_dim=self._config.feature_dim,
        )
        rul_cycles, state_vector = self._model.predict(window)
        rul_days = rul_cycles * self.cycles_per_day

        # Cross-check with EMA for uncertainty estimate
        ema_days, ema_conf, ema_uncertainty, _ = self._ema.predict(machine_id)
        lstm_ema_delta = abs(rul_days - ema_days)
        uncertainty = float(max(ema_uncertainty, lstm_ema_delta * 0.3))

        # Confidence: higher when EMA and LSTM agree
        agreement = max(0.0, 1.0 - (lstm_ema_delta / max(rul_days + ema_days + 1, 1)))
        confidence = float(np.clip(0.7 + 0.25 * agreement, 0.5, 0.97))

        status = _rul_to_status(rul_days, reading.health_index)

        return RULPrediction(
            machine_id=machine_id,
            rul_cycles=rul_cycles,
            rul_days=rul_days,
            confidence=confidence,
            uncertainty=uncertainty,
            status=status,
            using_lstm=True,
            state_vector=state_vector,
            health_index=reading.health_index,
        )

    def _ema_predict(
        self,
        machine_id: str,
        reading: NormalizedReading,
    ) -> RULPrediction:
        """EMA fallback path."""
        rul_days, confidence, uncertainty, status = self._ema.predict(machine_id)
        # Proxy cycles from days (inverted from cycles_per_day)
        rul_cycles = rul_days / max(self.cycles_per_day, 0.001)

        return RULPrediction(
            machine_id=machine_id,
            rul_cycles=rul_cycles,
            rul_days=rul_days,
            confidence=confidence,
            uncertainty=uncertainty,
            status=status,
            using_lstm=False,
            state_vector=None,
            health_index=reading.health_index,
        )

    # ------------------------------------------------------------------

    def get_window(self, machine_id: str) -> List[List[float]]:
        """Return current sliding window for machine_id (for AMKB use)."""
        with self._lock:
            return list(self._windows.get(machine_id, []))

    def clear_machine(self, machine_id: str) -> None:
        """Reset state for a machine (e.g., after maintenance / restart)."""
        with self._lock:
            self._windows.pop(machine_id, None)
            self._ema._history.pop(machine_id, None)
        logger.info(f"[{self.domain}] RULEngine: cleared state for {machine_id}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rul_to_status(rul_days: float, health_index: float) -> str:
    """Classify a RUL estimate into a status string."""
    if rul_days <= 0 or health_index >= 0.9:
        return "Critical"
    if rul_days < 7 or health_index >= 0.7:
        return "Degrading"
    if rul_days < 30:
        return "Warning"
    return "Stable"
