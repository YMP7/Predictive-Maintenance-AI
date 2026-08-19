import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient

from server import api
from server.atlas.learning_engine import LearningEngine, LearningResult
from server.atlas.world_model import WorldModel, WorldModelConfig


def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture
def temp_checkpoint(tmp_path):
    """Creates a temporary isolated WorldModel checkpoint for testing."""
    cfg = WorldModelConfig(feature_dim=14, hidden_size=64, state_dim=32, domain="cmapss")
    model = WorldModel(cfg)
    ckpt_path = tmp_path / "test_best_model.pt"
    model.save(ckpt_path)
    return ckpt_path


def test_promotion_gate_math():
    engine = LearningEngine(epsilon_tol=0.03)

    baseline_rmse = 15.00
    acceptable_candidate_rmse = 15.40  # 15.40 <= 15.00 * 1.03 (15.45) -> True
    rejected_candidate_rmse = 15.60    # 15.60 > 15.45 -> False

    assert acceptable_candidate_rmse <= baseline_rmse * (1.0 + engine.epsilon_tol)
    assert not (rejected_candidate_rmse <= baseline_rmse * (1.0 + engine.epsilon_tol))


def test_rejection_leaves_production_checkpoint_bitwise_identical(temp_checkpoint):
    """
    CRITICAL ROLLBACK SAFETY TEST:
    Asserts that if candidate training results in a regression, the active production
    checkpoint file is provably untouched and bitwise-identical (verified by SHA-256 and tensor equality).
    """
    engine = LearningEngine(model_path=temp_checkpoint, epsilon_tol=0.03)

    # 1. Capture exact SHA-256 hash and tensors before run
    initial_hash = compute_file_sha256(temp_checkpoint)
    initial_sd = torch.load(str(temp_checkpoint), weights_only=True)["model_state_dict"]

    # 2. Trigger retraining with a forced regression (+20% RMSE)
    with patch.object(engine, "evaluate_cmapss_benchmark", return_value=15.00), \
         patch.object(engine, "_log_learning_event"):

        baseline_rmse = 15.00
        regressed_rmse = baseline_rmse * 1.25  # 25% regression

        result = engine.retrain_domain(
            domain="cmapss",
            trigger_reason="manual",
            epochs=1,
            forced_candidate_rmse=regressed_rmse,
        )

        # 3. Assert rejection
        assert result.success is False
        assert "REJECTED (Rollback Invariant)" in result.notes
        assert result.checkpoint_path is None

    # 4. Assert bitwise SHA-256 identity of the active checkpoint file
    post_hash = compute_file_sha256(temp_checkpoint)
    assert post_hash == initial_hash, f"Checkpoint hash changed! {post_hash} != {initial_hash}"

    # 5. Assert exact tensor equality across all state_dict keys
    post_sd = torch.load(str(temp_checkpoint), weights_only=True)["model_state_dict"]
    for k in initial_sd:
        assert torch.equal(initial_sd[k], post_sd[k]), f"Tensor '{k}' was modified in production checkpoint!"


def test_promotion_gate_accepts_and_atomically_replaces(temp_checkpoint):
    """
    Asserts that an improved/stable candidate is accepted, saved atomically,
    and updates the active checkpoint.
    """
    engine = LearningEngine(model_path=temp_checkpoint, epsilon_tol=0.03)
    initial_hash = compute_file_sha256(temp_checkpoint)

    with patch.object(engine, "evaluate_cmapss_benchmark", return_value=15.00), \
         patch.object(engine, "_log_learning_event"):

        baseline_rmse = 15.00
        improved_rmse = baseline_rmse * 0.90  # 10% improvement

        result = engine.retrain_domain(
            domain="cmapss",
            trigger_reason="manual",
            epochs=1,
            forced_candidate_rmse=improved_rmse,
        )

        assert result.success is True
        assert "PROMOTED" in result.notes
        assert result.checkpoint_path == str(temp_checkpoint)

    post_hash = compute_file_sha256(temp_checkpoint)
    # Checkpoint should have been atomically updated
    assert post_hash != initial_hash


def test_baseline_evaluation_matches_validated_range():
    """
    REGRESSION GUARD TEST:
    Asserts that LearningEngine.evaluate_cmapss_benchmark() on the active production
    checkpoint data/models/best_model.pt returns an RMSE within the empirically
    validated range [14.0, 16.5] (Month 3 5-seed average: 14.98 +/- 0.13).
    Prevents any future regression to the all-window evaluation artifact (~49.0).
    """
    from server.atlas.world_model import MODELS_DIR
    production_model_path = MODELS_DIR / "best_model.pt"
    assert production_model_path.exists(), "Production checkpoint best_model.pt must exist"

    model = WorldModel.load(production_model_path)
    baseline_rmse = LearningEngine.evaluate_cmapss_benchmark(model)

    assert 14.0 <= baseline_rmse <= 16.5, (
        f"Baseline RMSE {baseline_rmse:.4f} is outside the validated range [14.0, 16.5]! "
        f"Ensure last-window benchmark protocol is used, not all-windows."
    )


def test_learning_history_query():
    engine = LearningEngine()
    history = engine.get_learning_history(domain="cmapss", limit=5)
    assert isinstance(history, list)


def test_api_learning_endpoints():
    client = TestClient(api.app)

    # Mock learning engine inside API
    mock_engine = MagicMock()
    mock_result = LearningResult(
        domain="cmapss",
        trigger_reason="manual",
        n_samples=16500,
        epochs_run=2,
        rmse_before=15.02,
        rmse_after=14.95,
        checkpoint_path="data/models/best_model.pt",
        success=True,
        notes="PROMOTED: Candidate RMSE <= Baseline",
    )
    mock_engine.retrain_domain.return_value = mock_result
    mock_engine.get_learning_history.return_value = [mock_result.to_dict()]

    api._learning_engine = mock_engine

    # 1. Test POST /api/learn/retrain
    resp = client.post("/api/learn/retrain", json={"domain": "cmapss", "epochs": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["domain"] == "cmapss"

    # 2. Test GET /api/learn/history
    resp_hist = client.get("/api/learn/history?domain=cmapss")
    assert resp_hist.status_code == 200
    hist_data = resp_hist.json()
    assert "history" in hist_data
    assert len(hist_data["history"]) == 1
