"""
tests/test_ablations.py — Unit Tests for ATLAS Ablation Studies (Month 7 Week 3)
=================================================================================
Tests the mathematical validity, edge case handling (Spearman rank correlation zero-variance),
grounding toggles, cost evaluation, and cross-compute evaluation metrics.
"""

from pathlib import Path
from unittest.mock import MagicMock
import numpy as np
import pytest

from server.atlas.adaptive_context import AdaptiveContext, NeighborContext
from server.atlas.explain import ExplanationEngine, ExplanationReport
from server.atlas.simulation import MaintenanceAction
from server.atlas.ablation_engine import (
    AblationEngine,
    Ablation1Result,
    Ablation2Result,
    Ablation3Result,
    Ablation4Result,
)


def test_explanation_engine_grounding_toggle():
    """
    Tests that ExplanationEngine correctly respects grounding_enabled flag.
    - When True: constructs AMKB citations and bounded confidence.
    - When False: skips citations, sets 0.50 maximal uncertainty prior, and returns explanatory note.
    """
    mock_neighbors = [
        NeighborContext(machine_id="1", cycle=100, rul=25.0, distance=0.1),
        NeighborContext(machine_id="2", cycle=120, rul=24.0, distance=0.2),
    ]
    ctx = AdaptiveContext(
        domain="cmapss",
        machine_id="10",
        query_cycle=50,
        predicted_rul=24.5,
        neighbors=mock_neighbors,
        average_neighbor_rul=24.5,
        machine_dna=None,
    )

    # 1. Grounded Explainer
    expl_grounded = ExplanationEngine(grounding_enabled=True)
    rep_g = expl_grounded.explain(ctx)
    assert len(rep_g.citations) == 2
    assert rep_g.confidence_score > 0.0
    assert "grounded in 2 historically similar" in rep_g.primary_justification

    # 2. Ungrounded Explainer
    expl_ungrounded = ExplanationEngine(grounding_enabled=False)
    rep_u = expl_ungrounded.explain(ctx)
    assert len(rep_u.citations) == 0
    assert rep_u.confidence_score == pytest.approx(0.50, abs=1e-6)
    assert rep_u.confidence_level == "Moderate"
    assert "Ungrounded prediction" in rep_u.primary_justification
    assert "0.50 maximal uncertainty prior" in rep_u.note


def test_ablation_1_cost_and_waste_math(tmp_path):
    """
    Tests Ablation 1 mathematical evaluation:
    - Premature waste discarded cycles when true_rul > 60 and action is REPLACE
    - Missed failure detection when true_rul <= 5 and action is CONTINUE
    - Cost reduction calculation
    """
    engine = AblationEngine(models_dir=tmp_path)

    # Synthetic 4-unit scenario:
    # Unit 0: true_rul = 80.0 (healthy), pred = 20.0 -> Rule A replaces prematurely (waste 80), ATLAS continues
    # Unit 1: true_rul = 4.0 (critical), pred = 45.0 -> Rule A continues (missed failure), ATLAS replaces
    # Unit 2: true_rul = 10.0 (near failure), pred = 15.0 -> Both replace
    # Unit 3: true_rul = 100.0 (healthy), pred = 90.0 -> Both continue
    true_ruls = np.array([80.0, 4.0, 10.0, 100.0])
    pred_ruls = np.array([20.0, 45.0, 15.0, 90.0])
    variances = np.array([5.0, 50.0, 2.0, 5.0])

    expl_reports = [
        ExplanationReport(confidence_score=0.8, confidence_level="High", primary_justification="", citations=[]),
        ExplanationReport(confidence_score=0.2, confidence_level="Low", primary_justification="", citations=[]),
        ExplanationReport(confidence_score=0.9, confidence_level="High", primary_justification="", citations=[]),
        ExplanationReport(confidence_score=0.8, confidence_level="High", primary_justification="", citations=[]),
    ]

    res = engine.run_ablation_1(true_ruls, pred_ruls, variances, expl_reports)

    # Under Pipeline A:
    # Unit 0: pred 20 < 30 -> REPLACE. true_rul 80 > 60 -> premature waste = 80.0
    # Unit 1: pred 45 >= 30 -> CONTINUE. true_rul 4 <= 5 -> missed failure = 1, cost = 1000.0 (unplanned failure)
    # Unit 2: pred 15 < 30 -> REPLACE. true_rul 10 <= 60 -> premature waste = 0, cost = 60.0
    # Unit 3: pred 90 >= 30 -> CONTINUE. true_rul 100 > 30 -> cost = 0.0
    assert res.premature_waste_cycles_a == pytest.approx(80.0, abs=1e-2)
    assert res.missed_failures_a == 1
    assert res.total_cost_pipeline_a >= 1000.0


def test_ablation_2_spearman_correlation_and_zero_variance_handling(tmp_path):
    """
    Tests Ablation 2 Spearman correlation math and zero-variance edge case:
    - Ungrounded condition (constant 0.50) MUST return rho=None and explanatory note, NOT NaN leak.
    - Grounded condition with varying confidence produces a valid Spearman rho.
    """
    engine = AblationEngine(models_dir=tmp_path)

    n_units = 10
    true_ruls = np.linspace(10.0, 100.0, n_units)
    # Predictions with varying errors
    pred_ruls = true_ruls + np.array([2.0, -5.0, 12.0, -1.0, 20.0, 0.5, -8.0, 15.0, -2.0, 4.0])

    contexts = []
    windows = []
    for i in range(n_units):
        # Varying neighbor variance to produce dynamic grounded confidence
        var = float((i + 1) * 3.0)
        dist = 0.1 * (i % 3)
        mock_neighbors = [
            NeighborContext(machine_id="1", cycle=10, rul=float(true_ruls[i] + np.sqrt(var)), distance=dist)
        ]
        ctx = AdaptiveContext(
            domain="cmapss",
            machine_id=str(i + 1),
            query_cycle=50,
            predicted_rul=float(pred_ruls[i]),
            neighbors=mock_neighbors,
            average_neighbor_rul=float(true_ruls[i]),
            machine_dna=None,
        )
        contexts.append(ctx)
        windows.append(np.zeros((30, 14)))

    res, reports = engine.run_ablation_2(true_ruls, pred_ruls, contexts, windows)

    assert res.grounded_confidence_mean > 0.0
    assert res.grounded_confidence_std > 0.0
    assert res.grounded_spearman_rho is not None
    assert -1.0 <= res.grounded_spearman_rho <= 1.0

    # Ungrounded condition: strictly zero std, rho is None, note explains zero variance
    assert res.ungrounded_confidence_mean == pytest.approx(0.50, abs=1e-6)
    assert res.ungrounded_confidence_std == 0.0
    assert res.ungrounded_spearman_rho is None
    assert "Undefined (Zero Variance)" in res.ungrounded_spearman_note
    assert res.grounded_citation_coverage_pct == 100.0
    assert res.ungrounded_citation_coverage_pct == 0.0


def test_ablation_3_near_failure_metrics(tmp_path):
    """
    Tests Ablation 3 evaluation:
    - Near-failure urgent response rate for true_rul <= 15
    - Policy agreement rate
    """
    engine = AblationEngine(models_dir=tmp_path)

    # 4 units: 2 near-failure (true_rul = 5, 12), 2 healthy (true_rul = 80, 95)
    true_ruls = np.array([5.0, 12.0, 80.0, 95.0])
    pred_ruls = np.array([8.0, 25.0, 75.0, 90.0])
    variances = np.array([2.0, 4.0, 10.0, 8.0])

    expl_reports = [
        ExplanationReport(confidence_score=0.8, confidence_level="High", primary_justification="", citations=[]),
        ExplanationReport(confidence_score=0.7, confidence_level="Moderate", primary_justification="", citations=[]),
        ExplanationReport(confidence_score=0.8, confidence_level="High", primary_justification="", citations=[]),
        ExplanationReport(confidence_score=0.8, confidence_level="High", primary_justification="", citations=[]),
    ]

    res = engine.run_ablation_3(true_ruls, pred_ruls, variances, expl_reports)

    assert res.n_near_failure_units == 2
    assert 0.0 <= res.policy_agreement_rate <= 100.0
    assert 0.0 <= res.near_failure_urgent_rate_naive <= 100.0
    assert 0.0 <= res.near_failure_urgent_rate_atlas <= 100.0
    assert res.avg_mc_sample_cost_std >= 0.0


def test_ablation_4_cross_compute_matrix_properties():
    """
    Tests Ablation 4 3x3 cross-compute retrieval matrix schema and properties:
    - 3x3 matrix exists with keys laptop, mobile, server
    - Diagonal entries are strictly positive within-domain RMSEs
    - Off-diagonal inflation ratios are positive floats
    - NOTE: Explicitly does NOT assert symmetry on retrieval RMSE (retrieval RMSE is directional!).
    """
    models_dir = Path("data/models")
    if not (models_dir / "laptop_world_model.pt").exists():
        pytest.skip("Trained compute domain models not found in data/models")

    engine = AblationEngine(models_dir=models_dir)
    res = engine.run_ablation_4()

    domains = ["laptop", "mobile", "server"]
    for d1 in domains:
        assert d1 in res.cross_compute_matrix
        assert d1 in res.cross_compute_inflation_matrix
        # Within-domain diagonal must be positive RMSE
        within_rmse = res.cross_compute_matrix[d1][d1]
        assert within_rmse > 0.0
        assert res.cross_compute_inflation_matrix[d1][d1] == pytest.approx(1.0, abs=1e-2)

        for d2 in domains:
            assert d2 in res.cross_compute_matrix[d1]
            assert res.cross_compute_matrix[d1][d2] >= 0.0
            assert res.cross_compute_inflation_matrix[d1][d2] > 0.0

    # Week 2 C-MAPSS transfer table exists
    assert "laptop" in res.within_vs_cmapss_transfer
    assert "mobile" in res.within_vs_cmapss_transfer
    assert "server" in res.within_vs_cmapss_transfer
    assert "Laptop's within-domain retrieval RMSE" in res.laptop_asymmetry_analysis
