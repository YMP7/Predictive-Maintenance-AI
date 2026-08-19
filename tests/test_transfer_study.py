"""
tests/test_transfer_study.py — Unit Tests for Cross-Domain Representation Math & Guards
======================================================================================
Tests the mathematical correctness of Maximum Mean Discrepancy (MMD), Centroid Cosine
Similarity, and Negative Transfer Index using pure synthetic/dummy test vectors.

Also tests the hard structural guard ensuring the study refuses to run on untrained
zero-shot fallback projections.
"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from scripts.run_transfer_study import enforce_all_domains_trained_guard
from server.atlas.transfer_study import TransferStudyEngine


def test_cosine_similarity_mathematical_properties():
    # 1. Identical vectors -> 1.0
    v1 = np.array([1.0, 2.0, 3.0, 4.0])
    assert TransferStudyEngine.compute_cosine_similarity(v1, v1) == pytest.approx(1.0, abs=1e-6)

    # 2. Orthogonal vectors -> 0.0
    v_orth1 = np.array([1.0, 0.0, 0.0])
    v_orth2 = np.array([0.0, 1.0, 0.0])
    assert TransferStudyEngine.compute_cosine_similarity(v_orth1, v_orth2) == pytest.approx(0.0, abs=1e-6)

    # 3. Opposite vectors -> -1.0
    v_opp = -v1
    assert TransferStudyEngine.compute_cosine_similarity(v1, v_opp) == pytest.approx(-1.0, abs=1e-6)

    # 4. Zero vector safety -> 0.0 without divide by zero crash
    v_zero = np.zeros(4)
    assert TransferStudyEngine.compute_cosine_similarity(v1, v_zero) == 0.0

    # 5. Dimension mismatch raises ValueError
    with pytest.raises(ValueError, match="mismatch"):
        TransferStudyEngine.compute_cosine_similarity(np.array([1.0, 2.0]), np.array([1.0, 2.0, 3.0]))


def test_cosine_similarity_matrix_properties():
    # Synthetic cluster embeddings for 3 domains (32-dim)
    np.random.seed(42)
    embeddings = {
        "domain_a": np.random.randn(50, 32) + np.array([1.0] * 32),
        "domain_b": np.random.randn(50, 32) + np.array([-1.0] * 32),
        "domain_c": np.random.randn(50, 32) + np.array([0.0] * 32),
    }

    matrix = TransferStudyEngine.compute_cosine_similarity_matrix(embeddings)

    # Diagonal is strictly 1.0
    for d in embeddings:
        assert matrix[d][d] == 1.0

    # Matrix is symmetric
    assert matrix["domain_a"]["domain_b"] == matrix["domain_b"]["domain_a"]
    assert matrix["domain_a"]["domain_c"] == matrix["domain_c"]["domain_a"]
    assert matrix["domain_b"]["domain_c"] == matrix["domain_c"]["domain_b"]

    # Values bounded in [-1.0, 1.0]
    for d1 in embeddings:
        for d2 in embeddings:
            assert -1.0 <= matrix[d1][d2] <= 1.0


def test_rbf_kernel_diagonal_is_one():
    np.random.seed(42)
    x = np.random.randn(20, 16)
    gamma = 0.1
    k_xx = TransferStudyEngine.compute_rbf_kernel_matrix(x, x, gamma)

    # Diagonal must be exp(0) == 1.0
    for i in range(20):
        assert k_xx[i, i] == pytest.approx(1.0, abs=1e-6)

    # Off-diagonals must be in (0.0, 1.0]
    assert np.all(k_xx > 0.0)
    assert np.all(k_xx <= 1.0)


def test_mmd_mathematical_properties():
    """
    Validates core mathematical properties of MMD:
      1. MMD(X, X) == 0.0 (identity of indiscernibles)
      2. MMD(X, Y) == MMD(Y, X) >= 0.0 (symmetry & non-negativity)
      3. Monotonicity under distribution shift: moving mean further increases MMD
    """
    np.random.seed(42)
    # Synthetic 32-dim Gaussian distributions
    x = np.random.randn(100, 32)
    y_close = np.random.randn(100, 32) + 0.5   # Small shift
    y_far = np.random.randn(100, 32) + 5.0     # Large shift

    # 1. Self-MMD must be strictly 0.0
    mmd_self = TransferStudyEngine.compute_mmd(x, x)
    assert mmd_self == pytest.approx(0.0, abs=1e-5)

    # 2. Symmetry
    mmd_xy = TransferStudyEngine.compute_mmd(x, y_close)
    mmd_yx = TransferStudyEngine.compute_mmd(y_close, x)
    assert mmd_xy == pytest.approx(mmd_yx, abs=1e-6)
    assert mmd_xy > 0.0

    # 3. Monotonicity: larger distribution shift yields larger MMD
    mmd_far = TransferStudyEngine.compute_mmd(x, y_far)
    assert mmd_far > mmd_xy, f"Expected MMD_far ({mmd_far}) > MMD_close ({mmd_xy})"


def test_mmd_matrix_symmetry_and_diagonal():
    np.random.seed(42)
    domain_data = {
        "dom1": np.random.randn(30, 16) + 1.0,
        "dom2": np.random.randn(30, 16) - 1.0,
        "dom3": np.random.randn(30, 16) + 3.0,
    }

    mmd_mat = TransferStudyEngine.compute_mmd_matrix(domain_data)

    for d in domain_data:
        assert mmd_mat[d][d] == 0.0

    assert mmd_mat["dom1"]["dom2"] == mmd_mat["dom2"]["dom1"]
    assert mmd_mat["dom1"]["dom3"] == mmd_mat["dom3"]["dom1"]
    assert mmd_mat["dom2"]["dom3"] == mmd_mat["dom3"]["dom2"]
    assert mmd_mat["dom1"]["dom2"] > 0.0


def test_negative_transfer_index_math():
    # 1. Identical variance -> NTI = 0.0
    within_ruls = np.array([10.0, 12.0, 14.0, 16.0, 18.0])
    cross_ruls = np.array([20.0, 22.0, 24.0, 26.0, 28.0]) # Same variance = 8.0
    nti_equal = TransferStudyEngine.compute_negative_transfer_index(within_ruls, cross_ruls)
    assert nti_equal == pytest.approx(0.0, abs=1e-5)

    # 2. Inflated cross-domain variance -> NTI > 0.0
    cross_inflated = np.array([0.0, 20.0, 50.0, 90.0, 120.0]) # Much larger variance
    nti_positive = TransferStudyEngine.compute_negative_transfer_index(within_ruls, cross_inflated)
    assert nti_positive > 0.0

    # 3. Tighter cross-domain variance -> NTI < 0.0
    cross_tight = np.array([14.0, 14.1, 13.9, 14.0, 14.0])
    nti_negative = TransferStudyEngine.compute_negative_transfer_index(within_ruls, cross_tight)
    assert nti_negative < 0.0


def test_hard_training_status_guard_refuses_untrained_models(tmp_path):
    """
    CRITICAL STRUCTURAL SAFETY GUARD TEST:
    Asserts that TransferStudyEngine and run_transfer_study physically refuse to run
    and throw a loud RuntimeError when domain models are untrained / missing.
    """
    # Create empty mock models dir (only cmapss exists)
    (tmp_path / "best_model.pt").touch()

    engine = TransferStudyEngine(models_dir=tmp_path)

    # cmapss is trained
    assert engine.check_domain_training_status("cmapss") is True

    # laptop, mobile, server are untrained
    assert engine.check_domain_training_status("laptop") is False
    assert engine.check_domain_training_status("mobile") is False
    assert engine.check_domain_training_status("server") is False

    # Engine must refuse to run and list the untrained domains
    with pytest.raises(RuntimeError, match="domains.*laptop.*mobile.*server.*still use.*zero-shot fallback"):
        engine.assert_all_domains_trained(["cmapss", "laptop", "mobile", "server"])

    # CLI guard must also refuse to run
    with pytest.raises(RuntimeError, match="Cannot run Cross-Domain Transfer Study"):
        enforce_all_domains_trained_guard(["cmapss", "laptop", "mobile", "server"], tmp_path)


def test_hard_training_status_guard_passes_when_all_trained(tmp_path):
    """
    Asserts that the guard passes cleanly once all domain checkpoints exist.
    """
    (tmp_path / "best_model.pt").touch()
    (tmp_path / "laptop_world_model.pt").touch()
    (tmp_path / "mobile_world_model.pt").touch()
    (tmp_path / "server_world_model.pt").touch()

    engine = TransferStudyEngine(models_dir=tmp_path)
    domains = engine.assert_all_domains_trained(["cmapss", "laptop", "mobile", "server"])
    assert len(domains) == 4

    # CLI guard passes without exception
    enforce_all_domains_trained_guard(["cmapss", "laptop", "mobile", "server"], tmp_path)


def test_semantic_retrieval_transfer_diagnostics():
    """
    Tests AMKB semantic retrieval transfer evaluation math:
    1. Within-domain retrieval on nearby synthetic latent states
    2. Cross-domain retrieval against distant memory bank
    3. Asserts error inflation ratio and latent distance gap
    """
    np.random.seed(42)
    # Query: 50 points around origin with small noise
    z_query = np.random.randn(50, 32) * 0.1
    y_query = np.linspace(0.1, 0.9, 50)

    # Within memory: nearby points (around origin) with same target function
    z_within = np.random.randn(200, 32) * 0.1
    y_within = np.linspace(0.1, 0.9, 200)

    # Cross memory: distant cluster (mean=10.0) with discordant labels
    z_cross = np.random.randn(200, 32) * 0.1 + 10.0
    y_cross = np.ones(200) * 0.5

    diag = TransferStudyEngine.compute_retrieval_transfer_diagnostics(
        domain="test_domain",
        z_query=z_query,
        y_query_true=y_query,
        z_within_mem=z_within,
        y_within_mem=y_within,
        z_cmapss_mem=z_cross,
        y_cmapss_mem=y_cross,
        k=5,
    )

    assert diag.domain == "test_domain"
    assert diag.within_rmse >= 0.0
    assert diag.cross_rmse >= 0.0
    assert diag.mean_latent_dist_within < diag.mean_latent_dist_cross
    assert diag.mean_latent_dist_cross > 5.0
    assert diag.error_inflation_ratio >= 1.0
