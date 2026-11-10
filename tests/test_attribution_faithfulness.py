"""Deletion test behind the "Explainable" evidence (scripts/attribution_faithfulness.py)."""

import numpy as np

from scripts.attribution_faithfulness import deletion_curve, summarise


def toy_predict(window):
    # RUL depends only on columns 0 and 1 (column 0 twice as much); the others are noise the model ignores.
    return float(100 - 20 * window[:, 0].mean() - 10 * window[:, 1].mean())


def test_masking_the_true_drivers_moves_the_prediction_more_than_random_columns():
    w = np.ones((30, 14), dtype=np.float32)
    ranking = [0, 1] + list(range(2, 14))  # a faithful ranking
    curve = deletion_curve(toy_predict, w, ranking, k_values=[1, 2, 3], rng=np.random.default_rng(0), random_draws=50)
    assert curve[1]["top"] == 20.0 and curve[2]["top"] == 30.0
    assert curve[1]["top"] > curve[1]["random"] and curve[2]["top"] > curve[2]["random"]


def test_an_unfaithful_ranking_does_no_better_than_random():
    w = np.ones((30, 14), dtype=np.float32)
    ranking = list(range(13, -1, -1))  # drivers ranked last
    curve = deletion_curve(toy_predict, w, ranking, k_values=[2], rng=np.random.default_rng(0), random_draws=50)
    assert curve[2]["top"] == 0.0 < curve[2]["random"]


def test_summary_reports_mean_change_and_win_rate():
    per_unit = [{1: {"top": 5.0, "random": 1.0}}, {1: {"top": 0.5, "random": 1.0}}]
    s = summarise(per_unit, [1])
    assert s["k1"] == {"mean_abs_delta_top": 2.75, "mean_abs_delta_random": 1.0, "top_beats_random_pct": 50.0, "n_units": 2}


def test_the_recorded_result_is_served_and_shows_top_k_beating_random():
    from fastapi.testclient import TestClient

    from server.auth import User, get_current_user
    from server.backend_api import app

    app.dependency_overrides[get_current_user] = lambda: User(username="t_viewer", role="viewer")
    try:
        res = TestClient(app).get("/api/atlas/research/attribution-faithfulness", headers={"X-API-Request": "true"})
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 200
    s = res.json()["summary"]
    assert s["k2"]["n_units"] == 100
    assert s["k2"]["mean_abs_delta_top"] > s["k2"]["mean_abs_delta_random"]
