"""
train_rul.py — ATLAS C-MAPSS LSTM Training Script
===================================================
Trains the WorldModel (LSTM encoder + RUL head) on the NASA C-MAPSS dataset.
This is the primary Month-1 deliverable: once this script produces a
trained checkpoint, the RULEngine switches from EMA fallback to LSTM inference.

Usage
-----
    python server/atlas/train_rul.py
    python server/atlas/train_rul.py --subset FD001 --epochs 50 --batch-size 256
    python server/atlas/train_rul.py --subset FD001 --quick  # 5 epochs, for CI/dev

Outputs
-------
    data/models/cmapss_world_model.pt    -- model checkpoint (loadable by WorldModel)
    data/models/cmapss_metrics.json      -- RMSE, PHM score, loss history
    data/models/cmapss_training_log.txt  -- per-epoch log

C-MAPSS Training Protocol
--------------------------
The standard approach from the 2008 PHM challenge and subsequent literature:

1. Build sliding windows of 30 consecutive cycles per unit.
2. Target: RUL label capped at MAX_RUL_CAP=125 (from NormalizedReading.rul_label).
3. Loss: MSE on the RUL head output.
4. Evaluation: RMSE + asymmetric PHM scoring function on the test set.
5. Final benchmark: compare RMSE and PHM score to published results.

Published C-MAPSS FD001 baselines for reference (from literature):
    LSTM (Zheng et al. 2017):  RMSE ≈ 16.14, PHM ≈ 338
    Attention LSTM:            RMSE ≈ 13.7
    Our target (2-layer LSTM): RMSE < 15, PHM < 400 (CPU-feasible, not SOTA)

Architecture Note
-----------------
This script intentionally avoids GPU dependencies. All training runs on CPU.
Expected training time: FD001 (≈18k samples, 50 epochs) ≈ 3–8 minutes on
a modern laptop CPU.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Ensure project root is on path when running directly
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from server.adapters.cmapss_adapter import (
    CMAPSSAdapter,
    INFORMATIVE_SENSORS,
    MAX_RUL_CAP,
)
from server.atlas.world_model import (
    MODELS_DIR,
    WorldModel,
    WorldModelConfig,
    prepare_window,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ATLAS.train_rul")


# ---------------------------------------------------------------------------
# Dataset preparation
# ---------------------------------------------------------------------------

def build_windows(
    adapter: CMAPSSAdapter,
    seq_len: int,
    target_ids: Optional[List[str]] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build (X, y) arrays from all units in the adapter.

    X: shape (N_windows, seq_len, feature_dim)
    y: shape (N_windows,) — RUL labels (capped)

    One window per cycle: for cycle t in unit u, the window is
    cycles [max(0, t-seq_len)..t] (left-padded if needed).
    """
    X_list: List[np.ndarray] = []
    y_list: List[float] = []

    feature_dim = len(INFORMATIVE_SENSORS)

    machine_ids = sorted(adapter.machine_ids)
    if target_ids is not None:
        machine_ids = [m for m in machine_ids if m in target_ids]

    for machine_id in machine_ids:
        readings = adapter.get_unit_history(machine_id)
        window_buffer: List[List[float]] = []

        for r in readings:
            window_buffer.append(r.feature_vector)
            window = prepare_window(window_buffer, seq_len, feature_dim)
            X_list.append(window)

            # RUL label (capped) — rul_label is raw from adapter
            rul_raw = r.rul_label if r.rul_label is not None else 0.0
            y_list.append(min(float(rul_raw), float(MAX_RUL_CAP)))

    X = np.stack(X_list, axis=0).astype(np.float32)  # (N, T, F)
    y = np.array(y_list, dtype=np.float32)             # (N,)
    return X, y


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train(
    subset: str = "FD001",
    epochs: int = 50,
    batch_size: int = 256,
    lr: float = 1e-3,
    seq_len: int = 30,
    hidden_size: int = 64,
    num_layers: int = 2,
    dropout: float = 0.2,
    quick: bool = False,
    seed: int = 42,
) -> Dict:
    """
    Full training run. Returns a metrics dict.
    """
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
        
        import random
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
    except ImportError:
        logger.error(
            "PyTorch is required for training. Install:\n"
            "  pip install torch --index-url https://download.pytorch.org/whl/cpu"
        )
        sys.exit(1)

    if quick:
        epochs = 5
        batch_size = 512
        logger.info("Quick mode: 5 epochs, batch=512")

    # ---- Load data ----
    logger.info(f"Loading C-MAPSS {subset} training set...")
    train_adapter = CMAPSSAdapter(subset=subset, split="train")
    train_adapter.connect()

    test_adapter = CMAPSSAdapter(subset=subset, split="test")
    test_adapter.connect()

    import random
    all_train_ids = sorted(train_adapter.machine_ids)
    # Seeded for reproducible 80/20 split
    random.Random(seed).shuffle(all_train_ids)
    split_idx = int(len(all_train_ids) * 0.8)
    train_ids = all_train_ids[:split_idx]
    val_ids = all_train_ids[split_idx:]

    logger.info(f"Building training windows ({len(train_ids)} units) and validation windows ({len(val_ids)} units)...")
    t0 = time.time()
    X_train, y_train = build_windows(train_adapter, seq_len, target_ids=train_ids)
    X_val, y_val = build_windows(train_adapter, seq_len, target_ids=val_ids)
    logger.info(f"Training set: {X_train.shape[0]} windows in {time.time()-t0:.1f}s")
    logger.info(f"Validation set: {X_val.shape[0]} windows")

    # ---- Model ----
    config = WorldModelConfig(
        feature_dim=len(INFORMATIVE_SENSORS),
        hidden_size=hidden_size,
        num_layers=num_layers,
        dropout=dropout,
        seq_len=seq_len,
        max_rul=float(MAX_RUL_CAP),
        domain="cmapss",
    )
    model = WorldModel(config)
    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"WorldModel: {total_params:,} parameters")

    # ---- Optimizer & loss ----
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5
    )
    criterion = nn.MSELoss()

    # ---- DataLoader ----
    X_t = torch.tensor(X_train)
    y_t = torch.tensor(y_train).unsqueeze(1)  # (N, 1)
    dataset = TensorDataset(X_t, y_t)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)

    # ---- Training loop ----
    loss_history: List[float] = []
    val_loss_history: List[float] = []
    val_phm_history: List[float] = []
    
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = MODELS_DIR / "cmapss_training_log.txt"
    log_lines: List[str] = []

    best_val_loss = float("inf")
    best_epoch = 1

    logger.info(f"Training for {epochs} epochs (CPU)...")
    train_start = time.time()

    # Pre-allocate val tensors
    X_val_t = torch.tensor(X_val)
    y_val_t = torch.tensor(y_val).unsqueeze(1)

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        n_batches = 0

        for X_batch, y_batch in loader:
            optimizer.zero_grad()
            out = model(X_batch)
            rul_pred = out.rul_pred
            loss = criterion(rul_pred, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        avg_loss = epoch_loss / max(n_batches, 1)
        loss_history.append(avg_loss)
        
        # Validation
        model.eval()
        with torch.no_grad():
            val_out = model(X_val_t)
            val_preds = val_out.rul_pred
            v_loss = criterion(val_preds, y_val_t).item()
            # Compute PHM on val set (cap predictions to prevent negative numbers)
            val_phm = CMAPSSAdapter.phm_score(y_val, np.maximum(0, val_preds.numpy().flatten()))
            
        val_loss_history.append(v_loss)
        val_phm_history.append(val_phm)
        if v_loss < best_val_loss:
            best_val_loss = v_loss
            best_epoch = epoch
            # Save in WorldModel.save() config-wrapped format — loadable by
            # WorldModel.load() without reconstructing config separately.
            model.save(MODELS_DIR / "best_model.pt")

        scheduler.step(v_loss)

        if epoch % 5 == 0 or epoch == 1:
            elapsed = time.time() - train_start
            msg = f"Epoch {epoch:3d}/{epochs} | Train MSE: {avg_loss:.4f} | Val MSE: {v_loss:.4f} | Val PHM: {val_phm:.1f} | Elapsed: {elapsed:.1f}s"
            logger.info(msg)
            log_lines.append(msg)

    total_time = time.time() - train_start
    logger.info(f"Training complete in {total_time:.1f}s")
    logger.info(f"Early stopping selected epoch {best_epoch} as best checkpoint (Val MSE: {best_val_loss:.4f})")
    
    # Load best checkpoint for final evaluation using WorldModel.load().
    # This uses the config-wrapped format saved above — identical to how
    # the AMKB population script and near-failure tests load the model.
    model = WorldModel.load(MODELS_DIR / "best_model.pt")
    model.eval()

    # ---- Evaluation on test set ----
    logger.info("Evaluating final model strictly on held-out test set...")
    model.eval()
    y_true_list: List[float] = []
    y_pred_list: List[float] = []

    with torch.no_grad():
        for machine_id in sorted(test_adapter.machine_ids):
            # For RUL benchmarking: use the last window only (standard protocol)
            readings = test_adapter.get_unit_history(machine_id)
            if not readings:
                continue

            # Build window from last seq_len cycles
            window_buffer = [r.feature_vector for r in readings[-seq_len:]]
            window = prepare_window(window_buffer, seq_len, len(INFORMATIVE_SENSORS))
            X_test = torch.tensor(window, dtype=torch.float32).unsqueeze(0)

            test_out = model(X_test)
            rul_pred_t = test_out.rul_pred
            y_pred_list.append(float(rul_pred_t.item()))
            # Ground truth from the last reading's rul_label
            y_true_list.append(float(readings[-1].rul_label or 0.0))

    y_true = np.array(y_true_list)
    y_pred = np.array(y_pred_list)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    phm = CMAPSSAdapter.phm_score(y_true, y_pred)

    logger.info(f"{'='*50}")
    logger.info(f"BENCHMARK RESULTS — C-MAPSS {subset}")
    logger.info(f"  RMSE:      {rmse:.4f} cycles")
    logger.info(f"  PHM Score: {phm:.2f} (lower is better)")
    logger.info(f"  Test units evaluated: {len(y_true)}")
    logger.info(f"  (Literature LSTM baseline: RMSE ≈ 16.14, PHM ≈ 338)")
    logger.info(f"{'='*50}")

    # ---- Save model ----
    checkpoint_path = model.save()
    logger.info(f"Model saved: {checkpoint_path}")

    # ---- Save metrics ----
    metrics = {
        "subset": subset,
        "epochs": epochs,
        "batch_size": batch_size,
        "seq_len": seq_len,
        "hidden_size": hidden_size,
        "num_layers": num_layers,
        "learning_rate": lr,
        "training_time_s": round(total_time, 2),
        "final_train_loss": round(loss_history[-1], 6),
        "final_val_loss": round(val_loss_history[-1], 6),
        "loss_history": [round(l, 6) for l in loss_history],
        "val_loss_history": [round(l, 6) for l in val_loss_history],
        "val_phm_history": [round(p, 2) for p in val_phm_history],
        "benchmark": {
            "rmse": round(rmse, 4),
            "phm_score": round(phm, 2),
            "n_test_units": len(y_true),
        },
        "literature_baselines": {
            "Zheng_LSTM_2017": {"rmse": 16.14, "phm": 338},
        },
    }
    metrics_path = MODELS_DIR / "cmapss_metrics.json"
    with open(str(metrics_path), "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Metrics saved: {metrics_path}")

    # ---- Save training log ----
    with open(str(log_path), "w") as f:
        f.write("\n".join(log_lines))

    # ---- Generate Plots (Week 4 deliverable) ----
    try:
        import matplotlib.pyplot as plt
        
        figures_dir = _PROJECT_ROOT / "docs" / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Loss Curve
        plt.figure(figsize=(10, 5))
        epochs_range = range(1, len(loss_history) + 1)
        plt.plot(epochs_range, loss_history, color="#7c3aed", linewidth=2, label="Train MSE")
        plt.plot(epochs_range, val_loss_history, color="#ec4899", linewidth=2, label="Val MSE")
        plt.axvline(x=best_epoch, color='gray', linestyle='--', alpha=0.7, label=f"Best Epoch ({best_epoch})")
        plt.title(f"Training & Validation Loss (MSE) - C-MAPSS {subset}")
        plt.xlabel("Epoch")
        plt.ylabel("MSE Loss")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig(str(figures_dir / f"{subset}_loss_curve.png"), dpi=150, bbox_inches="tight")
        plt.close()
        
        # 2. Predicted vs Actual Scatter (highlighting late predictions at low true RUL)
        plt.figure(figsize=(8, 8))
        
        # Split points into "danger zone" (true RUL <= 30) and "safe zone"
        danger_mask = y_true <= 30
        safe_mask = ~danger_mask
        
        # Safe zone points (normal)
        plt.scatter(y_true[safe_mask], y_pred[safe_mask], alpha=0.6, color="#3b82f6", edgecolors="white", label="RUL > 30 (Safe)")
        
        # Danger zone points - split by early/late
        danger_early_mask = danger_mask & (y_pred <= y_true)
        danger_late_mask = danger_mask & (y_pred > y_true)
        
        plt.scatter(y_true[danger_early_mask], y_pred[danger_early_mask], alpha=0.8, color="#10b981", marker='o', edgecolors="white", label="RUL <= 30 (Early/Safe)")
        plt.scatter(y_true[danger_late_mask], y_pred[danger_late_mask], alpha=0.9, color="#ef4444", marker='x', s=60, label="RUL <= 30 (Late/Dangerous)")
        
        # Perfect prediction line
        max_val = max(np.max(y_true), np.max(y_pred))
        plt.plot([0, max_val], [0, max_val], 'k--', alpha=0.5, label="Perfect Prediction")
        
        plt.title(f"Predicted vs Actual RUL - {subset} Test Set\nRMSE: {rmse:.2f} | PHM Score: {phm:.1f}")
        plt.xlabel("True RUL (cycles)")
        plt.ylabel("Predicted RUL (cycles)")
        plt.legend(loc="upper left")
        plt.grid(True, alpha=0.3)
        plt.savefig(str(figures_dir / f"{subset}_pred_vs_actual.png"), dpi=150, bbox_inches="tight")
        plt.close()
        logger.info(f"Generated plots in {figures_dir}")
    except ImportError:
        logger.warning("matplotlib not installed. Skipping plot generation.")

    # Cleanup
    train_adapter.disconnect()
    test_adapter.disconnect()

    return metrics


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ATLAS WorldModel training script (C-MAPSS LSTM RUL)"
    )
    parser.add_argument(
        "--subset", default="FD001",
        choices=["FD001", "FD002", "FD003", "FD004"],
        help="C-MAPSS subset to train on (default: FD001)",
    )
    parser.add_argument(
        "--epochs", type=int, default=50,
        help="Number of training epochs (default: 50)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=256,
        help="Mini-batch size (default: 256)",
    )
    parser.add_argument(
        "--lr", type=float, default=1e-3,
        help="Adam learning rate (default: 0.001)",
    )
    parser.add_argument(
        "--seq-len", type=int, default=30,
        help="Sliding window length in cycles (default: 30)",
    )
    parser.add_argument(
        "--hidden-size", type=int, default=64,
        help="LSTM hidden state size (default: 64)",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Run only 5 epochs for a quick dev/CI check",
    )
    args = parser.parse_args()

    metrics = train(
        subset=args.subset,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        seq_len=args.seq_len,
        hidden_size=args.hidden_size,
        quick=args.quick,
    )

    print("\n[OK] Training complete.")
    print(f"  RMSE:      {metrics['benchmark']['rmse']}")
    print(f"  PHM Score: {metrics['benchmark']['phm_score']}")
    print(f"  Model:     data/models/cmapss_world_model.pt")


if __name__ == "__main__":
    main()
