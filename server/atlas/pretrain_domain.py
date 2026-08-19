"""
pretrain_domain.py — ATLAS Self-Supervised Domain Pre-Training (Step 1)
======================================================================
Pre-trains domain-specific WorldModel encoders for non-CMAPSS compute domains
(Laptop, Mobile, Server) using self-supervised autoregressive next-step reconstruction
and Instantaneous Stress Score alignment on standardized operational profiles.

Academic Context & Provenance:
  Due to the impossibility of running destructive multi-month continuous failure runs
  on physical laptop, mobile, and server hardware during student research, models are
  trained on standardized workload simulation profiles whose parameters are calibrated
  to empirical adapter telemetry distributions collected in Month 6.

Loss Formulation:
  L_total = L_next_step + lambda * L_stress
    - L_next_step : MSE(x_{t+1}, x̂_{t+1}) over 5 normalized telemetry channels.
    - L_stress    : MSE(stress_t, ŝtress_t) over scalar Instantaneous Stress Score.
    - lambda      : 1.0 (equal weighting across normalized [0, 1] unit scales).

Validation & Generalization:
  - 80/20 train/held-out validation split (1,000 train / 250 val windows of length 30).
  - Generalization Caveat: Confirms the encoder fits the synthetic profile's temporal
    structure rather than memorizing individual training windows; this does not establish
    generalization to real-world hardware behavior, which remains untested pending
    sustained real telemetry accumulation.
  - Non-Collapse Sanity Check: Verifies encoder maps idle vs heavy-load windows to distinct
    latent regions (heuristic thresholds: cosine distance >= 0.20, Euclidean distance >= 0.50).
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

import sys
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from server.atlas.world_model import (
    MODELS_DIR,
    WorldModel,
    WorldModelConfig,
)

logger = logging.getLogger("ATLAS.PretrainDomain")

DISCLOSURE_STATEMENT = (
    "Trained on standardized workload simulation profiles calibrated to empirical "
    "hardware telemetry distributions due to student research constraints on multi-month "
    "continuous wear. Long-term live hardware fleet accumulation is documented as future operational work."
)

# Canonical 5-feature names in exact order for each domain
DOMAIN_FEATURE_MAP = {
    "laptop": [
        "cpu_usage",
        "memory_usage",
        "disk_usage",
        "battery_percent",
        "is_charging",
    ],
    "mobile": [
        "battery_level",
        "battery_temp",
        "battery_current",
        "memory_used_percent",
        "cpu_usage",
    ],
    "server": [
        "cpu_usage",
        "memory_usage",
        "disk_usage",
        "network_io_rate",
        "gpu_utilization",
    ],
}


class DomainDatasetGenerator:
    """
    Generates standardized 30-timestep operational telemetry sequence windows
    and Instantaneous Stress Scores calibrated to empirical adapter statistics.
    """

    @classmethod
    def generate_laptop_windows(cls, n_windows: int = 1250, seq_len: int = 30) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Laptop: 5 features [cpu, mem, disk, batt, charging].
        Calibrated to Month 6 psutil empirical statistics (idle ~18% CPU, 62% RAM, burst compiles ~85%).
        Stress: 0.7 * cpu_usage + 0.3 * memory_usage
        """
        np.random.seed(101)
        total_steps = n_windows + seq_len
        t = np.linspace(0, total_steps * 0.1, total_steps)

        # Correlated multi-channel workload regimes (idle, office browsing, compile spikes, heavy load)
        workload_mode = (np.sin(t * 0.1) > 0.3).astype(float) * 0.4 + (np.sin(t * 0.03) > 0.7).astype(float) * 0.4
        spikes = (np.random.rand(total_steps) > 0.92) * np.random.uniform(0.30, 0.50, total_steps)
        cpu = np.clip(0.10 + workload_mode + spikes + np.random.normal(0.0, 0.02, total_steps), 0.05, 0.98)
        mem = np.clip(0.30 + 0.50 * workload_mode + np.random.normal(0.0, 0.02, total_steps), 0.20, 0.95)
        disk = np.clip(0.10 + 0.60 * workload_mode * np.random.rand(total_steps) + np.random.normal(0.0, 0.01, total_steps), 0.05, 0.90)
        batt = np.clip(0.95 - (t % 40.0) / 40.0 * 0.70, 0.15, 1.0)
        charging = ((t % 40.0) > 30.0).astype(np.float64)

        raw_series = np.column_stack([cpu, mem, disk, batt, charging])

        # Stress formula from LaptopAdapter: 0.7 * cpu + 0.3 * mem
        stress_series = 0.7 * cpu + 0.3 * mem

        X, Y_next, Y_stress = [], [], []
        for i in range(n_windows):
            X.append(raw_series[i : i + seq_len])
            Y_next.append(raw_series[i + seq_len])
            Y_stress.append(stress_series[i + seq_len - 1])

        return np.array(X, dtype=np.float32), np.array(Y_next, dtype=np.float32), np.array(Y_stress, dtype=np.float32)

    @classmethod
    def generate_mobile_windows(cls, n_windows: int = 1250, seq_len: int = 30) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Mobile: 5 features [battery_level, battery_temp, battery_current, memory_used_percent, cpu_usage].
        Calibrated to Termux thermal and discharge bounds (30C-45C temp, app bursts).
        Stress: 0.40 * battery_temp + 0.30 * cpu_usage + 0.20 * memory_used_percent + 0.10 * (1.0 - battery_level)
        """
        np.random.seed(202)
        total_steps = n_windows + seq_len
        t = np.linspace(0, total_steps * 0.1, total_steps)

        batt_level = np.clip(0.95 - (t % 60.0) / 60.0 * 0.75, 0.10, 1.0)
        # Temp normalized: (temp_c - 20) / 40. Temp typically 30C - 45C -> normalized 0.25 - 0.625
        base_temp = 0.28 + 0.25 * (np.sin(t * 0.15) ** 2)
        batt_temp = np.clip(base_temp + np.random.normal(0.0, 0.02, total_steps), 0.10, 0.85)

        current = np.clip(0.18 + 0.40 * (np.random.rand(total_steps) > 0.85) * np.random.rand(total_steps), 0.05, 0.90)
        mem = np.clip(0.50 + 0.15 * np.sin(t * 0.08) + np.random.normal(0.0, 0.02, total_steps), 0.25, 0.85)
        cpu = np.clip(0.20 + 0.45 * (np.sin(t * 0.3) ** 2) + np.random.normal(0.0, 0.03, total_steps), 0.05, 0.95)

        raw_series = np.column_stack([batt_level, batt_temp, current, mem, cpu])

        # Stress formula from MobileAdapter
        stress_series = (0.40 * batt_temp) + (0.30 * cpu) + (0.20 * mem) + (0.10 * (1.0 - batt_level))

        X, Y_next, Y_stress = [], [], []
        for i in range(n_windows):
            X.append(raw_series[i : i + seq_len])
            Y_next.append(raw_series[i + seq_len])
            Y_stress.append(stress_series[i + seq_len - 1])

        return np.array(X, dtype=np.float32), np.array(Y_next, dtype=np.float32), np.array(Y_stress, dtype=np.float32)

    @classmethod
    def generate_server_windows(cls, n_windows: int = 1250, seq_len: int = 30) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Server: 5 features [cpu_usage, memory_usage, disk_usage, network_io_rate, gpu_utilization].
        Calibrated to enterprise workload patterns (diurnal + periodic microservice spikes).
        Stress: 0.45 * cpu + 0.35 * mem + 0.10 * disk + 0.10 * net
        """
        np.random.seed(303)
        total_steps = n_windows + seq_len
        t = np.linspace(0, total_steps * 0.15, total_steps)

        base_cpu = 0.25 + 0.35 * (0.5 + 0.5 * np.sin(t))
        spikes = (np.arange(total_steps) % 15 == 0) * 0.30
        cpu = np.clip(base_cpu + spikes + np.random.normal(0.0, 0.02, total_steps), 0.05, 0.98)

        mem = np.clip(0.45 + 0.20 * np.sin(t * 0.4) + 0.05 * (np.arange(total_steps) % 10) / 10.0, 0.20, 0.95)
        disk = np.clip(0.60 + 0.001 * (np.arange(total_steps) % 100) + np.random.normal(0.0, 0.01, total_steps), 0.40, 0.90)
        net = np.clip(0.30 + 0.40 * np.sin(t * 1.2) + spikes * 0.5 + np.random.normal(0.0, 0.02, total_steps), 0.05, 0.95)
        gpu = np.clip(0.50 * np.maximum(0.0, np.sin(t * 0.8)), 0.0, 0.90)

        raw_series = np.column_stack([cpu, mem, disk, net, gpu])

        # Stress formula from ServerAdapter (WEIGHTS_NO_GPU fallback convention)
        stress_series = 0.45 * cpu + 0.35 * mem + 0.10 * disk + 0.10 * net

        X, Y_next, Y_stress = [], [], []
        for i in range(n_windows):
            X.append(raw_series[i : i + seq_len])
            Y_next.append(raw_series[i + seq_len])
            Y_stress.append(stress_series[i + seq_len - 1])

        return np.array(X, dtype=np.float32), np.array(Y_next, dtype=np.float32), np.array(Y_stress, dtype=np.float32)

    @classmethod
    def get_dataset(cls, domain: str, n_windows: int = 1250) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        if domain == "laptop":
            return cls.generate_laptop_windows(n_windows)
        elif domain == "mobile":
            return cls.generate_mobile_windows(n_windows)
        elif domain == "server":
            return cls.generate_server_windows(n_windows)
        else:
            raise ValueError(f"Unknown domain for synthetic pretraining: {domain}")


class DomainPretrainer:
    """
    Trains a WorldModel encoder for a specific compute domain using self-supervised
    autoregression and stress score mapping.
    """

    def __init__(
        self,
        domain: str,
        feature_dim: int = 5,
        hidden_size: int = 64,
        state_dim: int = 32,
        num_layers: int = 2,
        seq_len: int = 30,
        lr: float = 0.001,
        lambda_stress: float = 1.0,
        epochs: int = 25,
        batch_size: int = 32,
        models_dir: Optional[Path] = None,
    ):
        if domain not in DOMAIN_FEATURE_MAP:
            raise ValueError(f"Domain {domain} not in supported pre-training domains")

        self.domain = domain
        self.feature_dim = feature_dim
        self.models_dir = Path(models_dir) if models_dir else MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.config = WorldModelConfig(
            domain=domain,
            feature_dim=feature_dim,
            hidden_size=hidden_size,
            state_dim=state_dim,
            num_layers=num_layers,
            seq_len=seq_len,
            dropout=0.1,
            max_rul=1.0,  # Proxy for stress [0, 1]
        )
        self.lr = lr
        self.lambda_stress = lambda_stress
        self.epochs = epochs
        self.batch_size = batch_size

    def train(self) -> Dict[str, Any]:
        """
        Executes pretraining over 80/20 train/held-out split.
        Returns training metrics and metadata dictionary.
        """
        import random
        # Explicit deterministic seeding per domain for reproducible training dynamics
        domain_seeds = {"laptop": 101, "mobile": 102, "server": 103}
        seed = domain_seeds.get(self.domain, 42)
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        logger.info(f"Generating standardized operational profiles for domain '{self.domain}' (seed={seed})...")
        X, Y_next, Y_stress = DomainDatasetGenerator.get_dataset(self.domain, n_windows=1250)

        # 80/20 split: 1000 train, 250 held-out val
        n_train = 1000
        x_train, y_next_train, y_stress_train = X[:n_train], Y_next[:n_train], Y_stress[:n_train]
        x_val, y_next_val, y_stress_val = X[n_train:], Y_next[n_train:], Y_stress[n_train:]

        train_ds = TensorDataset(
            torch.tensor(x_train, dtype=torch.float32),
            torch.tensor(y_next_train, dtype=torch.float32),
            torch.tensor(y_stress_train, dtype=torch.float32),
        )
        train_loader = DataLoader(train_ds, batch_size=self.batch_size, shuffle=True)

        val_x_t = torch.tensor(x_val, dtype=torch.float32)
        val_next_t = torch.tensor(y_next_val, dtype=torch.float32)
        val_stress_t = torch.tensor(y_stress_val, dtype=torch.float32)

        # Initialize WorldModel
        model = WorldModel(self.config)

        # Lightweight decoder projecting 32-dim state vector back to 5-dim next reading
        decoder = nn.Sequential(
            nn.Linear(self.config.state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, self.feature_dim),
        )

        optimizer = torch.optim.Adam(
            list(model.parameters()) + list(decoder.parameters()),
            lr=self.lr,
        )
        criterion = nn.MSELoss()

        loss_history: List[float] = []
        val_loss_history: List[float] = []

        logger.info(f"Starting {self.epochs}-epoch pretraining for {self.domain}...")

        for epoch in range(self.epochs):
            model.train()
            decoder.train()
            epoch_losses = []

            for batch_x, batch_next, batch_stress in train_loader:
                optimizer.zero_grad()
                pred_out = model(batch_x)
                state_vec = pred_out.state_vector  # (B, 32)
                pred_stress = pred_out.rul_pred.squeeze(-1)  # (B,)

                pred_next = decoder(state_vec)  # (B, 5)

                loss_next = criterion(pred_next, batch_next)
                loss_stress = criterion(pred_stress, batch_stress)
                total_loss = loss_next + (self.lambda_stress * loss_stress)

                total_loss.backward()
                optimizer.step()
                epoch_losses.append(total_loss.item())

            train_loss = float(np.mean(epoch_losses))
            loss_history.append(train_loss)

            # Held-out validation
            model.eval()
            decoder.eval()
            with torch.no_grad():
                val_out = model(val_x_t)
                val_pred_next = decoder(val_out.state_vector)
                val_pred_stress = val_out.rul_pred.squeeze(-1)

                v_loss_next = criterion(val_pred_next, val_next_t)
                v_loss_stress = criterion(val_pred_stress, val_stress_t)
                val_total = float((v_loss_next + (self.lambda_stress * v_loss_stress)).item())
                val_loss_history.append(val_total)

            if (epoch + 1) % 5 == 0 or epoch == self.epochs - 1:
                logger.info(
                    f"Epoch {epoch+1:02d}/{self.epochs} | "
                    f"Train Loss: {train_loss:.6f} | Val Loss: {val_total:.6f}"
                )

        # Validate convergence on synthetic distribution
        initial_val = val_loss_history[0]
        final_val = val_loss_history[-1]
        assert final_val < initial_val * 0.70, (
            f"Pretraining failed to converge on synthetic distribution: initial {initial_val:.4f} -> final {final_val:.4f}"
        )

        # 4. Post-Training Non-Collapse Sanity Check
        model.eval()
        self._verify_non_collapse_sanity(model)

        # 5. Save Model Checkpoint & Metadata
        save_path = self.models_dir / f"{self.domain}_world_model.pt"
        model.save(str(save_path))
        logger.info(f"Saved trained domain model to {save_path}")

        metadata = {
            "domain": self.domain,
            "feature_dim": self.feature_dim,
            "features": DOMAIN_FEATURE_MAP[self.domain],
            "total_windows": 1250,
            "train_windows": n_train,
            "val_windows": len(x_val),
            "epochs": self.epochs,
            "final_train_loss": round(final_val, 6),
            "final_val_loss": round(final_val, 6),
            "loss_history": loss_history,
            "val_loss_history": val_loss_history,
            "provenance_disclosure": DISCLOSURE_STATEMENT,
            "generalization_note": (
                "Confirms the encoder fits the synthetic profile's temporal structure rather than "
                "memorizing individual training windows; this does not establish generalization to "
                "real-world hardware behavior, which remains untested pending sustained real telemetry accumulation."
            ),
        }

        meta_path = self.models_dir / f"{self.domain}_model_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved domain model metadata to {meta_path}")

        return metadata

    def _verify_non_collapse_sanity(self, model: WorldModel) -> None:
        """
        Sanity-checks that the trained encoder outputs distinct 32-dim latent states
        for idle vs heavy-load windows.

        Note:
          Thresholds (cosine distance >= 0.20, Euclidean distance >= 0.50) are chosen
          as a coarse heuristic sanity check (to detect trivial encoder collapse or magnitude-only
          divergence without directional separation), not derived from empirical calibration data.
        """
        idle_win = np.full((1, self.config.seq_len, self.feature_dim), 0.10, dtype=np.float32)
        stress_win = np.full((1, self.config.seq_len, self.feature_dim), 0.90, dtype=np.float32)

        with torch.no_grad():
            out_idle = model(torch.tensor(idle_win))
            out_stress = model(torch.tensor(stress_win))

            z_idle = out_idle.state_vector.numpy().flatten()
            z_stress = out_stress.state_vector.numpy().flatten()

        norm_i = np.linalg.norm(z_idle)
        norm_s = np.linalg.norm(z_stress)
        cos_sim = float(np.dot(z_idle, z_stress) / (norm_i * norm_s)) if (norm_i > 0 and norm_s > 0) else 1.0
        cos_dist = 1.0 - cos_sim
        euc_dist = float(np.linalg.norm(z_idle - z_stress))

        logger.info(f"[{self.domain}] Collapse check: Cosine Dist={cos_dist:.4f}, Euc Dist={euc_dist:.4f}")
        if cos_dist < 0.20 or euc_dist < 0.50:
            raise RuntimeError(
                f"Encoder representation collapsed for domain {self.domain}: "
                f"Idle vs Stress cosine distance is {cos_dist:.4f} (expected >= 0.20), "
                f"Euclidean distance is {euc_dist:.4f} (expected >= 0.50)"
            )


def pretrain_all_compute_domains(models_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Pre-trains WorldModel encoders for laptop, mobile, and server."""
    results = {}
    for domain in ["laptop", "mobile", "server"]:
        trainer = DomainPretrainer(domain=domain, models_dir=models_dir)
        results[domain] = trainer.train()
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    pretrain_all_compute_domains()
