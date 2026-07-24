"""
World Model — ATLAS Cognition Core
===================================
LSTM-based state-vector encoder. Takes a sliding window of NormalizedReading
feature vectors and encodes them into a fixed-size latent state vector.

Architecture
------------
  Input:  (batch, seq_len, feature_dim)       -- sequence of normalised sensor readings
  LSTM:   2 layers, hidden_size=64, dropout=0.2 between layers
  Output: (batch, hidden_size)                -- state vector (last hidden state)
          (batch, 1)                           -- RUL prediction head

The same architecture is used across all domains. Domain-specific instances
are saved as: data/models/{domain}_world_model.pt

Design Decisions
----------------
- CPU-first: no GPU required. All ops are efficient on modern laptop CPUs.
- Seq-len 30: standard for C-MAPSS (30 consecutive cycles). Shorter windows
  are zero-padded; this is handled in _prepare_window().
- Feature dim is fixed per domain (CMAPSSAdapter: 14 informative sensors).
  For multi-domain training the feature dim is always the ATLAS canonical dim
  (14 for the initial C-MAPSS-only phase; will expand to a superset dim in Month 6).
- The RUL head outputs a single scalar in [0, MAX_RUL_CAP]. During training
  the target is the capped RUL label from NormalizedReading.rul_label.
- The state vector (last LSTM hidden state) is the primary output used by
  AMKB and Machine DNA (Months 2+).

Usage
-----
    cfg = WorldModelConfig(feature_dim=14)
    model = WorldModel(cfg)
    # ... (see RULEngine for inference; see train_rul.py for training)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ATLAS.WorldModel")

# ---------------------------------------------------------------------------
# Attempt PyTorch import — graceful degradation if not installed
# ---------------------------------------------------------------------------

try:
    import torch
    import torch.nn as nn
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    logger.warning(
        "PyTorch not found. WorldModel will operate in STUB mode (no inference). "
        "Install: pip install torch --index-url https://download.pytorch.org/whl/cpu"
    )


# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = _PROJECT_ROOT / "data" / "models"


# ---------------------------------------------------------------------------
# Configuration & Output Dataclasses
# ---------------------------------------------------------------------------

from typing import Any

@dataclass
class PredictionOutput:
    """
    Standardized return type for WorldModel forward() and predict().
    Using a dataclass ensures that downstream subsystems (AMKB, Machine DNA, ACE)
    do not break when new outputs (like attention weights) are added.
    """
    rul_pred: Any
    state_vector: Any
    attn_weights: Optional[Any] = None

@dataclass
class WorldModelConfig:
    """Hyperparameters for the WorldModel.

    These are the values used for C-MAPSS FD001 training.
    They are intentionally conservative to run fast on CPU.

    Canonical dimensions (do not change without updating AMKB + DNA simultaneously):
      hidden_size : 64  — LSTM internal hidden state dimension
      state_dim   : 32  — output state vector dimension (what AMKB + DNA consume)
    """
    feature_dim:    int   = 14    # Number of input sensor features
    hidden_size:    int   = 64    # LSTM hidden state dimension
    state_dim:      int   = 32    # Output state vector dimension → AMKB + DNA
    num_layers:     int   = 2     # LSTM depth
    dropout:        float = 0.2   # Dropout between LSTM layers
    seq_len:        int   = 30    # Input window length (cycles)
    max_rul:        float = 125.0 # RUL cap (must match CMAPSSAdapter.MAX_RUL_CAP)
    domain:         str   = "cmapss"

    # Derived
    @property
    def model_path(self) -> Path:
        return MODELS_DIR / f"{self.domain}_world_model.pt"

    @property
    def metrics_path(self) -> Path:
        return MODELS_DIR / f"{self.domain}_metrics.json"


# ---------------------------------------------------------------------------
# WorldModel — the LSTM encoder + RUL head
# ---------------------------------------------------------------------------

if _TORCH_AVAILABLE:

    class TemporalAttention(nn.Module):
        """
        Computes a soft attention weighting over the sequence of LSTM hidden states.
        Replaces the naive 'take the final timestep' approach with a learned
        aggregation of the entire window.
        """
        def __init__(self, hidden_size: int):
            super().__init__()
            self.attention = nn.Sequential(
                nn.Linear(hidden_size, hidden_size),
                nn.Tanh(),
                nn.Linear(hidden_size, 1, bias=False)
            )

        def forward(self, lstm_out: "torch.Tensor") -> Tuple["torch.Tensor", "torch.Tensor"]:
            # lstm_out: (batch, seq_len, hidden_size)
            scores = self.attention(lstm_out)           # (batch, seq_len, 1)
            weights = torch.softmax(scores, dim=1)      # (batch, seq_len, 1)
            context = torch.sum(weights * lstm_out, dim=1) # (batch, hidden_size)
            return context, weights.squeeze(-1)         # context: (batch, hidden), weights: (batch, seq_len)

    class WorldModel(nn.Module):
        """
        2-layer LSTM encoder with temporal attention, a linear projection to a 
        32-dim state vector, and a separate RUL prediction head.

        Canonical architecture (from ATLAS_PROJECT_CONTEXT.md §3):
            Input:        (batch, seq_len, feature_dim)
            LSTM:         hidden_size=64, 2 layers
            Attention:    Temporal pooling over seq_len → (batch, 64)
            to_state:     Linear(64 → state_dim=32)
            state_vector: (batch, 32)  ← primary output for AMKB + Machine DNA
            rul_head:     Linear(32→16) → ReLU → Dropout → Linear(16→1)  [no final activation]
            rul_pred:     (batch, 1)  — raw linear; clamped ≥ 0 at inference in predict()

        The 32-dim state_vector is the canonical embedding dimension throughout ATLAS.
        AMKB experience embeddings and Machine DNA embeddings are both vector(32).
        Do NOT change state_dim without updating amkb.py and machine_dna.py simultaneously.
        """

        def __init__(self, config: WorldModelConfig) -> None:
            super().__init__()
            self.config = config

            self.lstm = nn.LSTM(
                input_size=config.feature_dim,
                hidden_size=config.hidden_size,
                num_layers=config.num_layers,
                batch_first=True,
                dropout=config.dropout if config.num_layers > 1 else 0.0,
            )

            # Temporal attention over all seq_len outputs
            self.attention = TemporalAttention(config.hidden_size)

            # Project attention context (64) → canonical state vector (32)
            self.to_state = nn.Linear(config.hidden_size, config.state_dim)

            # RUL prediction head on top of the 32-dim state vector.
            # No activation on the output layer — raw linear output allows gradients
            # to flow freely when values are negative at init. Non-negativity is
            # enforced at inference time in predict() via torch.clamp(min=0),
            # and during training via MSE loss (which naturally pushes predictions
            # toward positive ground-truth RUL values).
            # DO NOT add nn.ReLU() or nn.Softplus() here — either will produce
            # dead outputs at init when the linear layer starts with negative weights,
            # making the loss appear stuck and breaking training silently.
            self.rul_head = nn.Sequential(
                nn.Linear(config.state_dim, 16),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(16, 1),
                # No final activation here — see note above
            )

        def forward(
            self, x: "torch.Tensor"
        ) -> PredictionOutput:
            # x: (batch, seq_len, feature_dim)
            lstm_out, _ = self.lstm(x)
            
            # lstm_out: (batch, seq_len, hidden_size)
            context, attn_weights = self.attention(lstm_out)
            
            # context: (batch, hidden_size)
            state_vector = self.to_state(context)    # (batch, state_dim=32)
            rul_pred = self.rul_head(state_vector)   # (batch, 1)
            
            return PredictionOutput(
                rul_pred=rul_pred,
                state_vector=state_vector,
                attn_weights=attn_weights
            )

        # ------------------------------------------------------------------

        def predict(
            self,
            window: np.ndarray,
        ) -> PredictionOutput:
            """
            Convenience: run one window through the model.

            Parameters
            ----------
            window : np.ndarray, shape (seq_len, feature_dim)
                     A single observation window (feature-normalised).

            Returns
            -------
            PredictionOutput containing:
              rul_pred    : float — predicted RUL in cycles (capped at max_rul)
              state_vector: np.ndarray, shape (state_dim=32,)
              attn_weights: np.ndarray, shape (seq_len,)
            """
            self.eval()
            with torch.no_grad():
                x = torch.tensor(window, dtype=torch.float32).unsqueeze(0)  # (1, T, F)
                out = self(x)
                
                rul = out.rul_pred.item()
                # Enforce non-negativity and max cap at inference time
                rul = max(0.0, min(float(rul), self.config.max_rul))
                sv = out.state_vector.squeeze(0).cpu().numpy()
                attn = out.attn_weights.squeeze(0).cpu().numpy()
                
            return PredictionOutput(
                rul_pred=rul,
                state_vector=sv,
                attn_weights=attn
            )

        # ------------------------------------------------------------------

        def save(self, path: Optional[Path] = None) -> Path:
            """Save model weights + config to disk."""
            import json
            target = path or self.config.model_path
            target.parent.mkdir(parents=True, exist_ok=True)
            torch.save({
                "model_state_dict": self.state_dict(),
                "config": {
                    "feature_dim": self.config.feature_dim,
                    "hidden_size": self.config.hidden_size,
                    "state_dim":   self.config.state_dim,
                    "num_layers":  self.config.num_layers,
                    "dropout":     self.config.dropout,
                    "seq_len":     self.config.seq_len,
                    "max_rul":     self.config.max_rul,
                    "domain":      self.config.domain,
                },
            }, str(target))
            logger.info(f"WorldModel saved to {target}")
            return target

        @classmethod
        def load(cls, path: Path) -> "WorldModel":
            """Load a saved checkpoint."""
            checkpoint = torch.load(str(path), map_location="cpu", weights_only=True)
            cfg = WorldModelConfig(**checkpoint["config"])
            model = cls(cfg)
            model.load_state_dict(checkpoint["model_state_dict"], strict=True)
            model.eval()
            logger.info(f"WorldModel loaded from {path}")
            return model

        @classmethod
        def load_for_domain(cls, domain: str) -> Optional["WorldModel"]:
            """Load a model by domain name. Returns None if not yet trained."""
            path = MODELS_DIR / f"{domain}_world_model.pt"
            if not path.exists():
                logger.info(
                    f"No trained WorldModel found for domain '{domain}' at {path}. "
                    "Run: python server/atlas/train_rul.py --domain cmapss"
                )
                return None
            return cls.load(path)

else:
    # Stub for when PyTorch is not installed
    class WorldModel:  # type: ignore[no-redef]
        """PyTorch not installed — stub mode."""

        def __init__(self, config: "WorldModelConfig") -> None:
            self.config = config
            logger.warning("WorldModel operating in STUB mode (PyTorch not installed).")

        def predict(self, window: np.ndarray) -> Tuple[float, np.ndarray]:
            # Return a naive linear-trend estimate as fallback
            if window.shape[0] > 1:
                health_col = window[:, 0]
                rul_estimate = max(0.0, (1.0 - health_col[-1]) * self.config.max_rul)
            else:
                rul_estimate = float(self.config.max_rul * 0.5)
            # state_vector is 32-dim zeros (matches canonical AMKB embedding dim)
            state = np.zeros(self.config.state_dim)
            return rul_estimate, state

        def save(self, path=None) -> None:
            logger.warning("WorldModel.save() is a no-op in STUB mode.")

        @classmethod
        def load(cls, path) -> "WorldModel":
            return cls(WorldModelConfig())

        @classmethod
        def load_for_domain(cls, domain: str) -> None:
            return None


# ---------------------------------------------------------------------------
# Window preparation helper (used by RULEngine and train_rul.py)
# ---------------------------------------------------------------------------

def prepare_window(
    readings: List[List[float]],
    seq_len: int,
    feature_dim: int,
) -> np.ndarray:
    """
    Convert a list of feature vectors into a fixed-size window for the LSTM.

    If len(readings) < seq_len  → zero-pad at the start (left-pad)
    If len(readings) > seq_len  → take the LAST seq_len readings

    Parameters
    ----------
    readings   : List of feature vectors (each is a list of feature_dim floats)
    seq_len    : Target window length
    feature_dim: Number of features per reading

    Returns
    -------
    np.ndarray of shape (seq_len, feature_dim)
    """
    window = np.zeros((seq_len, feature_dim), dtype=np.float32)
    readings_arr = np.array(readings, dtype=np.float32)

    if len(readings_arr) == 0:
        return window

    # Take last seq_len rows if longer
    if len(readings_arr) > seq_len:
        readings_arr = readings_arr[-seq_len:]

    # Right-align (left-pad with zeros)
    window[-len(readings_arr):] = readings_arr
    return window
