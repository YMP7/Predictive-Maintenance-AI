"""Split-conformal RUL interval: quantile, checkpoint binding, and API passthrough."""

import json
import math

import numpy as np

from server.atlas import rul_engine as E


def test_quantile_is_finite_sample_order_statistic():
    r = np.arange(1, 20)  # 19 residuals: ceil(20 * 0.9) = 18th smallest
    assert E.conformal_quantile(r, 0.1) == 18
    assert E.conformal_quantile(-r, 0.1) == 18  # uses |residual|
    assert math.isinf(E.conformal_quantile([1.0, 2.0], 0.1))  # too few points for 90%


def test_quantile_covers_at_nominal_rate_on_exchangeable_data():
    rng = np.random.default_rng(0)
    q = E.conformal_quantile(rng.normal(size=2000), 0.1)
    assert 0.88 <= float(np.mean(np.abs(rng.normal(size=20000)) <= q)) <= 0.92


def _write(tmp_path, model_bytes, sha):
    (tmp_path / "cmapss_world_model.pt").write_bytes(model_bytes)
    (tmp_path / "cmapss_conformal.json").write_text(json.dumps({"alpha": 0.1, "q_cycles": 22.0, "model_sha256": sha}))


def test_calibration_applies_only_to_its_own_checkpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "MODELS_DIR", tmp_path)
    _write(tmp_path, b"model-a", "0" * 64)
    assert E._load_conformal("cmapss") is None  # stale calibration after a retrain
    _write(tmp_path, b"model-a", E.file_sha256(tmp_path / "cmapss_world_model.pt"))
    assert E._load_conformal("cmapss")["q_cycles"] == 22.0


def test_shipped_calibration_matches_shipped_checkpoint():
    assert E._load_conformal("cmapss") is not None, "rerun scripts/conformal_rul.py after retraining"


def test_snapshot_rul_carries_interval():
    from server.adapters.asset_profiles import get_asset_profile
    from server.asset_view import snapshot_rul

    r = snapshot_rul(get_asset_profile("cmapss"),
                     {"rul_cycles": 80.0, "rul_lower": 58.0, "rul_upper": 102.0, "interval_level": 0.9})
    assert (r["lower"], r["upper"], r["interval_level"]) == (58.0, 102.0, 0.9)
