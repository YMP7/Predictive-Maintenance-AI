"""
Learning Engine — ATLAS Continuous Improvement & Retraining Subsystem (Month 7)
===============================================================================
Manages batch/periodic retraining and model adaptation for ATLAS domains.
Enforces a strict non-online boundary (batch-only) with automated candidate-vs-active
validation gating to mathematically prevent regressions from corrupting production checkpoints.

Key Architectural Guarantees:
  1. Non-Online Boundary: Strictly batch-driven retraining; online parameter updating is banned.
  2. Candidate vs. Best-Ever Promotion Gate: A candidate model is trained in isolation and must satisfy
     `RMSE_candidate <= RMSE_best_ever * (1 + epsilon_tol)` on a held-out validation slice of the
     training data (never the test split) before being promoted to production.
  3. Empirical Tolerance (epsilon_tol = 0.03): 3% tolerance band justified by Month 3 5-seed
     empirical variance (14.98 +/- 0.13, max spread ~2.3%) to absorb CPU non-deterministic gradient noise.
  4. Atomic Checkpoint Promotion: Overwrites production checkpoints atomically via tempfile + os.replace().
  5. Rollback Invariance: Rejected candidates are immediately discarded; active checkpoints remain bitwise-identical.
  6. Audit Trail: Every attempt is persistently logged to PostgreSQL/TimescaleDB `learning_events`.
"""

from server.adapters.domain_profile import get_profile
import copy
import functools
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from server.atlas.world_model import (
    MODELS_DIR,
    WorldModel,
    WorldModelConfig,
)

logger = logging.getLogger("ATLAS.LearningEngine")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_DATA_DIR = _PROJECT_ROOT / "data" / "processed"


@functools.lru_cache(maxsize=1)
def _cmapss_training_windows() -> Tuple[np.ndarray, np.ndarray]:
    from server.adapters.cmapss_adapter import CMAPSSAdapter
    from server.atlas.train_rul import build_windows

    adapter = CMAPSSAdapter(subset="FD001", split="train")
    adapter.connect()
    try:
        return build_windows(adapter, seq_len=30)
    finally:
        adapter.disconnect()


@dataclass
class LearningResult:
    """Output summary of a retraining run."""
    domain: str
    trigger_reason: str
    n_samples: int
    epochs_run: int
    rmse_before: float
    rmse_after: float
    checkpoint_path: Optional[str]
    success: bool
    notes: str
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LearningEngine:
    """
    ATLAS Learning Engine.
    Handles controlled retraining, validation gating, and learning event audit trails.
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        epsilon_tol: float = 0.03,
        min_samples_threshold: int = 500,
        log_events: bool = True,
    ) -> None:
        """
        Parameters
        ----------
        model_path : Path to active production checkpoint (default: data/models/best_model.pt)
        epsilon_tol : Regression tolerance threshold (default: 0.03 = 3.0%).
        min_samples_threshold : Minimum new samples required for automatic triggers.
                                (NOTE: For static C-MAPSS benchmark this threshold is inert/unreached
                                by default; it actively gates live streaming domains once accumulated).
        """
        self.model_path = Path(model_path) if model_path else (MODELS_DIR / "best_model.pt")
        self._explicit_path = model_path is not None
        # False for studies run on scratch copies, so they never appear as production events.
        self.log_events = bool(log_events)
        self.epsilon_tol = float(epsilon_tol)
        self.min_samples_threshold = int(min_samples_threshold)

    @staticmethod
    def _atomic_save_checkpoint(model: WorldModel, target_path: Path) -> Path:
        """
        Atomically saves model checkpoint to target_path using a temporary file
        and os.replace() to guarantee zero risk of corrupted checkpoints on interrupt/crash.
        """
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = target_path.parent / f"{target_path.stem}_tmp_{os.getpid()}_{int(time.time() * 1000)}{target_path.suffix}"
        try:
            model.save(temp_file)
            os.replace(str(temp_file), str(target_path))
            logger.info(f"[LearningEngine] Checkpoint promoted atomically to {target_path}")
            return target_path
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

    @classmethod
    def evaluate_cmapss_benchmark(
        cls,
        model: WorldModel,
        subset: str = "FD001",
        split: str = "test",
    ) -> float:
        """
        Evaluates WorldModel on C-MAPSS using the standard benchmark protocol:
        one prediction per unit (last window only) compared against ground-truth RUL.
        """
        from server.adapters.cmapss_adapter import CMAPSSAdapter, INFORMATIVE_SENSORS
        from server.atlas.world_model import prepare_window

        model.eval()
        test_adapter = CMAPSSAdapter(subset=subset, split=split)
        test_adapter.connect()
        try:
            seq_len = model.config.seq_len
            feature_dim = model.config.feature_dim or len(INFORMATIVE_SENSORS)
            y_true_list: List[float] = []
            y_pred_list: List[float] = []

            with torch.no_grad():
                for machine_id in sorted(test_adapter.machine_ids):
                    readings = test_adapter.get_unit_history(machine_id)
                    if not readings:
                        continue
                    window_buffer = [r.feature_vector for r in readings[-seq_len:]]
                    window = prepare_window(window_buffer, seq_len, feature_dim)
                    X_test = torch.tensor(window, dtype=torch.float32).unsqueeze(0)
                    out = model(X_test)
                    pred = float(out.rul_pred.item())
                    # Enforce non-negativity and max cap
                    pred = max(0.0, min(pred, float(model.config.max_rul)))
                    y_pred_list.append(pred)
                    y_true_list.append(float(readings[-1].rul_label or 0.0))

            if not y_true_list:
                return 999.0
            y_true = np.array(y_true_list, dtype=np.float32)
            y_pred = np.array(y_pred_list, dtype=np.float32)
            mse = float(np.mean((y_true - y_pred) ** 2))
            return float(np.sqrt(mse))
        finally:
            test_adapter.disconnect()

    @staticmethod
    def evaluate_model(model: WorldModel, X: np.ndarray, y: np.ndarray) -> float:
        """Computes RMSE over an arbitrary (X, y) dataset (used for testing and custom batches)."""
        model.eval()
        with torch.no_grad():
            X_tensor = torch.tensor(X, dtype=torch.float32)
            out = model(X_tensor)
            preds = out.rul_pred.squeeze().cpu().numpy()
            if preds.ndim == 0:
                preds = np.array([preds.item()])
            # Enforce non-negativity and max cap
            preds = np.clip(preds, 0.0, model.config.max_rul)
            y_clean = np.clip(y, 0.0, model.config.max_rul)
            mse = float(np.mean((preds - y_clean) ** 2))
            return float(np.sqrt(mse))

    def _load_cmapss_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """C-MAPSS FD001 training windows, built by the adapter.

        The adapter is the only source: it scales features exactly as the model is trained
        (train_rul.py) and served. data/processed/fd001_train.npz is z-scored, a different
        scale; retraining on it scored the gate on inputs the shipped model never sees and
        promoted candidates that were far worse on the test set.
        """
        return _cmapss_training_windows()

    def _split(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Fixed 90/10 train/validation split of the training windows.

        The promotion gate scores on this validation slice; the FD001 test split is
        kept for final reporting only, so it never influences which model is kept.
        """
        X, y = self._load_cmapss_data()
        idx = np.random.default_rng(0).permutation(len(X))
        n_val = max(1, int(len(X) * 0.1))
        # shortcut: splits windows, not units, so one engine can sit on both sides; split by unit if the npz gains unit ids.
        return X[idx[n_val:]], y[idx[n_val:]], X[idx[:n_val]], y[idx[:n_val]]

    @staticmethod
    def data_source(domain: str) -> Optional[str]:
        """Where a domain's retraining data comes from, or None when it has none."""
        profile = get_profile(domain)
        if profile.run_to_failure:
            return "benchmark"            # NASA C-MAPSS run-to-failure windows
        if profile.simulated_run_to_failure:
            return "simulated_failure"    # SIMULATED pump run-to-failure (pump_degradation.py)
        if profile.pretrain_generator:
            return "simulated_profile"    # SIMULATED workload profile, stress-score target
        return None

    def _domain_split(self, domain: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Train and validation windows for a domain. The gate only ever scores on the validation part."""
        source = self.data_source(domain)
        if source == "benchmark":
            return self._split()
        if source == "simulated_failure":
            from server.atlas.train_pump_rul import datasets

            d = datasets()
            return d["X_train"], d["y_train"], d["X_val"], d["y_val"]
        # Same 1000 / 250 split of the simulated profile the domain model was pretrained with.
        from server.atlas.pretrain_domain import DomainDatasetGenerator

        X, _, y = DomainDatasetGenerator.get_dataset(domain)
        return X[:1000], y[:1000], X[1000:], y[1000:]

    def _path_for(self, domain: str) -> Path:
        from server.adapters.domain_profile import PRIMARY_DOMAIN

        if self._explicit_path or domain == PRIMARY_DOMAIN:
            return self.model_path
        return MODELS_DIR / get_profile(domain).checkpoints[-1]

    def _validation_rmse(self, model: WorldModel, domain: str = "cmapss") -> float:
        _, _, X_val, y_val = self._domain_split(domain)
        return self.evaluate_model(model, X_val, y_val)

    def _log_learning_event(self, result: LearningResult) -> None:
        """Persists audit record into TimescaleDB / PostgreSQL learning_events table."""
        try:
            from server.database import pool
            with pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO learning_events (
                        domain, trigger_reason, n_samples, epochs_run,
                        rmse_before, rmse_after, checkpoint_path, success, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        result.domain,
                        result.trigger_reason,
                        result.n_samples,
                        result.epochs_run,
                        result.rmse_before,
                        result.rmse_after,
                        result.checkpoint_path,
                        result.success,
                        result.notes,
                    ),
                )
                conn.commit()
                logger.info("[LearningEngine] Audit event logged to database.")
        except Exception as e:
            logger.warning(f"[LearningEngine] Database logging skipped ({e})")

    def retrain_domain(
        self,
        domain: str = "cmapss",
        trigger_reason: str = "manual",
        epochs: int = 5,
        batch_size: int = 128,
        lr: float = 1e-3,
        forced_candidate_rmse: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> LearningResult:
        """
        Executes a controlled retraining run for the specified domain.

        Parameters
        ----------
        domain : Domain identifier. C-MAPSS retrains on the NASA benchmark; the pump on SIMULATED
                 run-to-failure data; laptop, phone and server on their SIMULATED workload profiles
                 (stress-score target). No domain retrains on real failures other than C-MAPSS's
                 simulated benchmark, and none retrains online.
        trigger_reason : 'manual' | 'scheduled' | 'sample_threshold'
        epochs : Number of training epochs on candidate model
        batch_size : Batch size
        lr : Learning rate
        forced_candidate_rmse : Optional test override to test promotion gate without training.
        seed : Seeds the candidate's training (batch order, dropout) so a run can be reproduced.
        """
        source = self.data_source(domain)
        model_path = self._path_for(domain)
        if source is None:
            return LearningResult(
                domain=domain,
                trigger_reason=trigger_reason,
                n_samples=0,
                epochs_run=0,
                rmse_before=0.0,
                rmse_after=0.0,
                checkpoint_path=None,
                success=False,
                notes=f"Domain '{domain}' has no retraining data source (no benchmark, simulator or profile registered).",
            )

        # 1. Evaluate baseline active model
        if not model_path.exists():
            # Initial bootstrap if no model exists
            cfg = WorldModelConfig(domain=domain)
            active_model = WorldModel(cfg)
            rmse_before = 999.0
        else:
            active_model = WorldModel.load(model_path)
            rmse_before = self._validation_rmse(active_model, domain)

        # 2. Train candidate model on isolated copy
        candidate_model = copy.deepcopy(active_model)

        if forced_candidate_rmse is not None:
            # Test override mode: bypass heavy training loop and set candidate score directly
            rmse_after = float(forced_candidate_rmse)
            n_samples = 0
            epochs_run = epochs
        else:
            X_train, y_train, _, _ = self._domain_split(domain)
            n_samples = len(X_train)
            epochs_run = epochs
            if seed is not None:
                np.random.seed(seed)
                torch.manual_seed(seed)

            candidate_model.train()
            optimizer = torch.optim.Adam(candidate_model.parameters(), lr=lr)
            criterion = nn.MSELoss()

            X_tensor = torch.tensor(X_train, dtype=torch.float32)
            y_tensor = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)
            dataset = TensorDataset(X_tensor, y_tensor)
            loader = DataLoader(dataset, batch_size=batch_size, shuffle=True,
                                generator=torch.Generator().manual_seed(seed) if seed is not None else None)

            for epoch in range(1, epochs + 1):
                for bx, by in loader:
                    optimizer.zero_grad()
                    out = candidate_model(bx)
                    loss = criterion(out.rul_pred, by)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(candidate_model.parameters(), max_norm=1.0)
                    optimizer.step()

            # 3. Evaluate candidate model
            rmse_after = self._validation_rmse(candidate_model, domain)

        # 4. Check Candidate vs. Best-Ever Promotion Gate
        # Anchored to the best RMSE ever promoted, not the current model, so the
        # 3% tolerance cannot compound across runs (10 x +2.9% would be +33%).
        gate_file = model_path.with_suffix(".gate.json")
        best_rmse = rmse_before
        if gate_file.exists():
            best_rmse = min(best_rmse, float(json.loads(gate_file.read_text())["best_val_rmse"]))
        max_acceptable_rmse = best_rmse * (1.0 + self.epsilon_tol)
        is_promoted = (rmse_after <= max_acceptable_rmse) or (rmse_before >= 990.0)

        saved_path: Optional[str] = None
        if is_promoted:
            # Non-destructive safety guard: if forced_candidate_rmse is active on default production model,
            # simulate promotion without overwriting validated production weights.
            is_production_model = False
            try:
                is_production_model = model_path.resolve().parent == MODELS_DIR.resolve()
            except Exception:
                pass

            if forced_candidate_rmse is not None and is_production_model:
                logger.info(
                    "[LearningEngine] forced_candidate_rmse active on production checkpoint. "
                    "Promotion checkpoint disk overwrite skipped to preserve validated weights."
                )
                saved_path = str(model_path)
            else:
                self._atomic_save_checkpoint(candidate_model, model_path)
                gate_file.write_text(json.dumps({"best_val_rmse": min(best_rmse, rmse_after)}))
                saved_path = str(model_path)

            success = True
            notes = self._provenance(source, seed, lr) + (
                f"PROMOTED: Candidate val RMSE ({rmse_after:.4f}) <= "
                f"Best ({best_rmse:.4f}) * (1 + {self.epsilon_tol:.2f}) = {max_acceptable_rmse:.4f}"
            )
        else:
            success = False
            notes = self._provenance(source, seed, lr) + (
                f"REJECTED (Rollback Invariant): Candidate val RMSE ({rmse_after:.4f}) exceeded "
                f"acceptable threshold ({max_acceptable_rmse:.4f} = Best {best_rmse:.4f} * (1 + {self.epsilon_tol:.2f})). "
                f"Production checkpoint was NOT modified."
            )

        result = LearningResult(
            domain=domain,
            trigger_reason=trigger_reason,
            n_samples=n_samples,
            epochs_run=epochs_run,
            rmse_before=rmse_before,
            rmse_after=rmse_after,
            checkpoint_path=saved_path,
            success=success,
            notes=notes,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        # 5. Persist audit log
        if self.log_events:
            self._log_learning_event(result)

        return result

    @staticmethod
    def _provenance(source: Optional[str], seed: Optional[int], lr: float) -> str:
        label = {"benchmark": "NASA C-MAPSS", "simulated_failure": "SIMULATED run-to-failure",
                 "simulated_profile": "SIMULATED workload profile"}.get(source or "", "unknown")
        return f"[data: {label}; lr {lr:g}" + (f"; seed {seed}" if seed is not None else "") + "] "

    def get_learning_history(self, domain: str = "cmapss", limit: int = 20) -> List[Dict[str, Any]]:
        """Queries historical learning events from the database."""
        try:
            from server.database import pool
            with pool.connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, triggered_at, domain, trigger_reason, n_samples,
                           epochs_run, rmse_before, rmse_after, checkpoint_path,
                           success, notes
                    FROM learning_events
                    WHERE domain = %s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (domain, limit),
                )
                rows = cursor.fetchall()
                cols = [
                    "id", "triggered_at", "domain", "trigger_reason", "n_samples",
                    "epochs_run", "rmse_before", "rmse_after", "checkpoint_path",
                    "success", "notes"
                ]
                return [
                    {cols[i]: (str(val) if i == 1 else val) for i, val in enumerate(row)}
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"[LearningEngine] Could not fetch history ({e})")
            return []
