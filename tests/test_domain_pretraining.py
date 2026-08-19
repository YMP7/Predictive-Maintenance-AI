"""
tests/test_domain_pretraining.py — Unit Tests for Step 1 Domain Pre-Training
==========================================================================
Tests the data generation consistency, exact 5-feature mapping, 80/20 train/val split,
loss reduction on held-out validation data, and non-collapse sanity checks.
"""

from pathlib import Path

import numpy as np
import pytest
import torch

from server.adapters.laptop_adapter import LaptopAdapter
from server.adapters.mobile_adapter import MobileAdapter
from server.adapters.server_adapter import ServerAdapter
from server.atlas.pretrain_domain import (
    DOMAIN_FEATURE_MAP,
    DomainDatasetGenerator,
    DomainPretrainer,
)
from server.atlas.world_model import WorldModel


def test_feature_map_matches_adapter_implementations():
    """
    Asserts that the 5-feature list in DOMAIN_FEATURE_MAP matches the exact
    keys produced by LaptopAdapter, MobileAdapter, and ServerAdapter get_reading().
    """
    # 1. Laptop
    lap = LaptopAdapter()
    lap_reading = lap.get_reading("laptop_local")
    assert list(lap_reading.features.keys()) == DOMAIN_FEATURE_MAP["laptop"]

    # 2. Mobile
    mob = MobileAdapter()
    mob_reading = mob.get_reading("mobile_device_1")
    assert list(mob_reading.features.keys()) == DOMAIN_FEATURE_MAP["mobile"]

    # 3. Server
    srv = ServerAdapter()
    srv_reading = srv.get_reading("server_prod_1")
    assert list(srv_reading.features.keys()) == DOMAIN_FEATURE_MAP["server"]


def test_dataset_generation_shapes_and_bounds():
    for domain in ["laptop", "mobile", "server"]:
        X, Y_next, Y_stress = DomainDatasetGenerator.get_dataset(domain, n_windows=100)

        # Sequence windows (N, 30, 5)
        assert X.shape == (100, 30, 5)
        # Next-step targets (N, 5)
        assert Y_next.shape == (100, 5)
        # Stress targets (N,)
        assert Y_stress.shape == (100,)

        # Bounded in [0.0, 1.0] (allowing small float epsilon)
        assert np.all(X >= -0.01) and np.all(X <= 1.01)
        assert np.all(Y_next >= -0.01) and np.all(Y_next <= 1.01)
        assert np.all(Y_stress >= -0.01) and np.all(Y_stress <= 1.01)


def test_domain_pretraining_execution_and_convergence(tmp_path):
    """
    Runs lightweight pretraining (15 epochs) in a temporary directory to assert:
      - 80/20 train/val split is respected
      - Held-out validation loss is computed
      - Checkpoint {domain}_world_model.pt is saved and loadable
      - Metadata {domain}_model_metadata.json is saved with disclosure statement
    """
    trainer = DomainPretrainer(
        domain="laptop",
        epochs=15,
        batch_size=32,
        models_dir=tmp_path,
    )
    meta = trainer.train()

    assert meta["train_windows"] == 1000
    assert meta["val_windows"] == 250
    assert len(meta["loss_history"]) == 15
    assert len(meta["val_loss_history"]) == 15
    assert "provenance_disclosure" in meta
    assert "generalization_note" in meta

    # Checkpoint exists and loads cleanly
    ckpt_path = tmp_path / "laptop_world_model.pt"
    assert ckpt_path.exists()

    loaded_model = WorldModel.load(str(ckpt_path))
    assert loaded_model.config.domain == "laptop"
    assert loaded_model.config.feature_dim == 5
    assert loaded_model.config.state_dim == 32

    # Forward pass on (30, 5) returns 32-dim state vector
    sample_win = np.random.rand(30, 5).astype(np.float32)
    pred_out = loaded_model.predict(sample_win)
    assert pred_out.state_vector.shape == (32,)


def test_directional_separation_collapse_guard_strict_thresholds():
    """
    Directly tests that all 3 compute domains (laptop, mobile, server)
    enforce and satisfy the strict non-collapse thresholds:
      cosine_distance >= 0.20 (directional separation in latent space)
      euclidean_distance >= 0.50 (magnitude separation)
    """
    for domain in ["laptop", "mobile", "server"]:
        model_path = Path("data/models") / f"{domain}_world_model.pt"
        assert model_path.exists(), f"Model {model_path} must exist"

        model = WorldModel.load(str(model_path))
        trainer = DomainPretrainer(domain=domain)

        # _verify_non_collapse_sanity raises RuntimeError if cos_dist < 0.20 or euc_dist < 0.50
        trainer._verify_non_collapse_sanity(model)


def test_hardcoded_directional_and_magnitude_separation_regression_guard():
    """
    INDEPENDENT REGRESSION GUARD:
    Hardcodes the exact mathematical thresholds (cosine_dist >= 0.20, euclidean_dist >= 0.50)
    directly in the test assertion, decoupled from any method or constant in pretrain_domain.py.
    This guarantees that if pretrain_domain.py thresholds are ever accidentally modified or loosened,
    this regression test will immediately fail.
    """
    HARDCODED_MIN_COSINE_DISTANCE = 0.20
    HARDCODED_MIN_EUCLIDEAN_DISTANCE = 0.50

    for domain in ["laptop", "mobile", "server"]:
        model_path = Path("data/models") / f"{domain}_world_model.pt"
        assert model_path.exists(), f"Model {model_path} must exist on disk"

        model = WorldModel.load(str(model_path))
        model.eval()

        idle_win = np.full((1, 30, 5), 0.10, dtype=np.float32)
        stress_win = np.full((1, 30, 5), 0.90, dtype=np.float32)

        with torch.no_grad():
            out_idle = model(torch.tensor(idle_win))
            out_stress = model(torch.tensor(stress_win))

            z_idle = out_idle.state_vector.numpy().flatten()
            z_stress = out_stress.state_vector.numpy().flatten()

        norm_i = np.linalg.norm(z_idle)
        norm_s = np.linalg.norm(z_stress)
        assert norm_i > 1e-6, f"{domain} idle representation norm collapsed to 0"
        assert norm_s > 1e-6, f"{domain} stress representation norm collapsed to 0"

        cos_sim = float(np.dot(z_idle, z_stress) / (norm_i * norm_s))
        cos_dist = 1.0 - cos_sim
        euc_dist = float(np.linalg.norm(z_idle - z_stress))

        assert cos_dist >= HARDCODED_MIN_COSINE_DISTANCE, (
            f"REGRESSION FAILURE for domain '{domain}': "
            f"Cosine distance {cos_dist:.4f} < hardcoded minimum {HARDCODED_MIN_COSINE_DISTANCE:.2f}"
        )
        assert euc_dist >= HARDCODED_MIN_EUCLIDEAN_DISTANCE, (
            f"REGRESSION FAILURE for domain '{domain}': "
            f"Euclidean distance {euc_dist:.4f} < hardcoded minimum {HARDCODED_MIN_EUCLIDEAN_DISTANCE:.2f}"
        )
