"""
tests/test_adapters.py — ATLAS Domain Adapter Tests
====================================================
Tests the NormalizedReading schema, base_adapter interface, and
CMAPSSAdapter behaviour (with and without dataset files present).

Run with:
    $env:PYTHONPATH="."; pytest tests/test_adapters.py -v
"""

import numpy as np
import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from server.adapters.base_adapter import (
    AdapterStatus,
    DomainType,
    MachineAdapter,
    NormalizedReading,
    DatasetNotFoundError,
)


# ---------------------------------------------------------------------------
# NormalizedReading schema tests
# ---------------------------------------------------------------------------

class TestNormalizedReading:
    def _make(self, **overrides) -> NormalizedReading:
        defaults = dict(
            domain="cmapss",
            machine_id="unit_1",
            timestamp="2024-01-01T00:00:00Z",
            health_index=0.25,
            cycle=100,
            rul_label=90.0,
            features={"s2": 0.5, "s3": 0.6, "s4": 0.4},
            raw_features={"s2": 605.0, "s3": 1590.0, "s4": 1400.0},
            operational_ctx={"op_set_1": 0.0, "op_set_2": 0.0, "op_set_3": 100.0},
            metadata={"subset": "FD001"},
            adapter_status=AdapterStatus.STREAMING.value,
        )
        defaults.update(overrides)
        return NormalizedReading(**defaults)

    def test_health_index_range(self):
        r = self._make(health_index=0.75)
        assert 0.0 <= r.health_index <= 1.0

    def test_feature_vector_sorted(self):
        r = self._make(features={"s4": 0.4, "s2": 0.5, "s3": 0.6})
        # feature_vector must be sorted by key (s2, s3, s4)
        assert r.feature_vector == [0.5, 0.6, 0.4]

    def test_to_dict_serialisable(self):
        import json
        r = self._make()
        d = r.to_dict()
        # Must be JSON serialisable
        json.dumps(d)
        assert d["domain"] == "cmapss"
        assert d["health_index"] == pytest.approx(0.25)

    def test_health_index_zero_is_fresh(self):
        r = self._make(health_index=0.0)
        assert r.health_index == 0.0

    def test_health_index_one_is_failed(self):
        r = self._make(health_index=1.0)
        assert r.health_index == 1.0

    def test_rul_label_optional(self):
        r = self._make(rul_label=None)
        assert r.rul_label is None


# ---------------------------------------------------------------------------
# CMAPSSAdapter tests (no real dataset required for most)
# ---------------------------------------------------------------------------

class TestCMAPSSAdapter:
    def test_invalid_subset_raises(self):
        from server.adapters.cmapss_adapter import CMAPSSAdapter
        with pytest.raises(ValueError, match="subset must be one of"):
            CMAPSSAdapter(subset="FD999")

    def test_invalid_split_raises(self):
        from server.adapters.cmapss_adapter import CMAPSSAdapter
        with pytest.raises(ValueError, match="split must be"):
            CMAPSSAdapter(subset="FD001", split="validation")

    def test_dataset_not_found_raises_helpful_error(self, tmp_path):
        from server.adapters.cmapss_adapter import CMAPSSAdapter, DatasetNotFoundError
        adapter = CMAPSSAdapter(subset="FD001", split="train", data_dir=tmp_path)
        with pytest.raises(DatasetNotFoundError) as exc_info:
            adapter.connect()
        # Should mention the expected path and download instructions
        assert "train_FD001.txt" in str(exc_info.value)
        assert "nasa.gov" in str(exc_info.value).lower() or "kaggle" in str(exc_info.value).lower()

    def test_phm_score_late_prediction_heavier(self):
        """PHM score must penalise late predictions more than early ones."""
        from server.adapters.cmapss_adapter import CMAPSSAdapter
        y_true = np.array([50.0, 50.0])
        # Early: predicted higher than actual (positive error = heavy penalty)
        # Wait — PHM convention: d = y_pred - y_true
        # d > 0 (late prediction) → heavy penalty
        y_pred_late  = np.array([60.0, 60.0])  # d = +10 (late)
        y_pred_early = np.array([40.0, 40.0])  # d = -10 (early)
        score_late  = CMAPSSAdapter.phm_score(y_true, y_pred_late)
        score_early = CMAPSSAdapter.phm_score(y_true, y_pred_early)
        assert score_late > score_early, (
            f"Late prediction should have higher (worse) PHM score. "
            f"Got late={score_late:.2f}, early={score_early:.2f}"
        )

    def test_phm_score_perfect(self):
        """PHM score for perfect predictions should be 0."""
        from server.adapters.cmapss_adapter import CMAPSSAdapter
        y = np.array([50.0, 100.0, 25.0])
        score = CMAPSSAdapter.phm_score(y, y)
        assert abs(score) < 1e-9

    def test_adapter_describe_shape(self, tmp_path):
        """describe() must return a dict with required keys even before connect()."""
        from server.adapters.cmapss_adapter import CMAPSSAdapter
        adapter = CMAPSSAdapter(subset="FD002", split="train", data_dir=tmp_path)
        d = adapter.describe()
        assert d["domain_id"] == "cmapss"
        assert d["subset"] == "FD002"
        assert "feature_dim" in d
        assert "informative_sensors" in d

    @pytest.mark.skipif(
        not (Path("data/cmapss/train_FD001.txt")).exists(),
        reason="C-MAPSS dataset not present (data/cmapss/train_FD001.txt)"
    )
    def test_full_connect_and_stream(self):
        """Integration test — only runs if dataset files are present."""
        from server.adapters.cmapss_adapter import CMAPSSAdapter
        adapter = CMAPSSAdapter(subset="FD001", split="train", max_units=5)
        adapter.connect()
        assert adapter.n_units == 5

        # Stream first reading from unit_1
        r = adapter.get_reading("unit_1")
        assert isinstance(r, NormalizedReading)
        assert 0.0 <= r.health_index <= 1.0
        assert r.domain == "cmapss"
        assert r.rul_label is not None
        assert len(r.feature_vector) == 14  # 14 informative sensors

        # Feature values must be in [0, 1] after normalisation
        for v in r.features.values():
            assert 0.0 <= v <= 1.0, f"Feature not normalised: {v}"

        adapter.disconnect()
        assert adapter.n_units == 0


# ---------------------------------------------------------------------------
# NormalizedReading timestamp_now
# ---------------------------------------------------------------------------

def test_timestamp_format():
    ts = NormalizedReading.timestamp_now()
    # Must end with Z (UTC)
    assert ts.endswith("Z")
    # Must be parseable ISO-8601
    from datetime import datetime
    datetime.fromisoformat(ts.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# World model prepare_window
# ---------------------------------------------------------------------------

class TestPrepareWindow:
    def test_short_window_left_pads(self):
        from server.atlas.world_model import prepare_window
        readings = [[0.1, 0.2], [0.3, 0.4]]
        w = prepare_window(readings, seq_len=5, feature_dim=2)
        assert w.shape == (5, 2)
        # First 3 rows should be zero-padded
        assert np.all(w[:3] == 0.0)
        # Last 2 rows should be the readings
        np.testing.assert_allclose(w[3], [0.1, 0.2])
        np.testing.assert_allclose(w[4], [0.3, 0.4])

    def test_exact_length_no_padding(self):
        from server.atlas.world_model import prepare_window
        readings = [[float(i)] * 3 for i in range(10)]
        w = prepare_window(readings, seq_len=10, feature_dim=3)
        assert w.shape == (10, 3)
        assert w[0, 0] == pytest.approx(0.0)
        assert w[9, 0] == pytest.approx(9.0)

    def test_long_window_truncates_to_last(self):
        from server.atlas.world_model import prepare_window
        readings = [[float(i)] * 2 for i in range(50)]
        w = prepare_window(readings, seq_len=10, feature_dim=2)
        assert w.shape == (10, 2)
        # Last row should be the last reading (index 49)
        assert w[9, 0] == pytest.approx(49.0)
        # First row should be reading at index 40
        assert w[0, 0] == pytest.approx(40.0)

    def test_empty_readings_returns_zeros(self):
        from server.atlas.world_model import prepare_window
        w = prepare_window([], seq_len=5, feature_dim=3)
        assert w.shape == (5, 3)
        assert np.all(w == 0.0)
