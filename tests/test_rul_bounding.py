"""
tests/test_rul_bounding.py

Phase 8 carry-over: Tests for the new RUL smoothing and bounding logic.

Covers:
1. 365-day upper cap on positive-slope extrapolation
2. Headroom-based RUL for m<=0 (stable/improving machines)
3. Median filter removing spike noise
4. EMA smoothing behavior
5. Boundary: current_deg >= 0.8 returns rul_days=0
6. Regression: the "38,544 days" bug cannot recur
"""
import numpy as np
from server.ai_agent import RULEstimator


class TestRULBounding:
    """Test the 365-day cap prevents absurdly large RUL values."""

    def test_rul_capped_at_365_days(self):
        """With very slow degradation, RUL should never exceed 365 days."""
        estimator = RULEstimator()
        # Feed 20 readings with extremely slow degradation
        for i in range(20):
            reading = {
                "vibration": {"rms": 0.1 + i * 0.001},  # Barely increasing
                "temperature": 42.0 + i * 0.01,
                "current": 2.3 + i * 0.001,
            }
            estimator.update_degradation("M001", reading)

        result = estimator.estimate_rul("M001")
        assert result["rul_days"] is not None
        assert result["rul_days"] <= 365, (
            f"RUL should be capped at 365 days, got {result['rul_days']}"
        )

    def test_38544_days_bug_cannot_recur(self):
        """
        Regression: the old code could produce rul_days > 38000.
        With the new min(365, ...) cap this must be impossible.
        """
        estimator = RULEstimator()
        # Create conditions that would have produced huge RUL:
        # very small positive slope (tiny degradation increase)
        for i in range(50):
            reading = {
                "vibration": {"rms": 0.05 + i * 0.0001},  # Nearly flat
                "temperature": 40.0,
                "current": 2.3,
            }
            estimator.update_degradation("M001", reading)

        result = estimator.estimate_rul("M001")
        assert result["rul_days"] is not None
        assert result["rul_days"] <= 365, (
            f"38544-day bug regression: got rul_days={result['rul_days']}"
        )


class TestRULStableMachine:
    """Test the m<=0 headroom-based RUL calculation."""

    def test_stable_machine_returns_headroom_rul(self):
        """Stable/improving machine should use headroom formula, not extrapolation."""
        estimator = RULEstimator()
        # Feed decreasing degradation (improving machine)
        for i in range(15):
            score = 0.5 - i * 0.01  # Decreasing
            reading = {
                "vibration": {"rms": max(0.1, score * 5)},
                "temperature": 42.0,
                "current": 2.3,
            }
            estimator.update_degradation("M001", reading)

        result = estimator.estimate_rul("M001")
        assert result["status"] == "Stable"
        assert result["rul_days"] >= 30, "Stable machine should have at least 30 days RUL"
        assert result["rul_days"] <= 365, "Stable machine RUL should be capped at 365"

    def test_flat_degradation_returns_stable(self):
        """Flat (constant) degradation should produce 'Stable' status."""
        estimator = RULEstimator()
        for _ in range(15):
            reading = {
                "vibration": {"rms": 0.5},
                "temperature": 45.0,
                "current": 2.5,
            }
            estimator.update_degradation("M001", reading)

        result = estimator.estimate_rul("M001")
        # With constant input, m should be ~0 or very small
        assert result["rul_days"] is not None
        assert result["rul_days"] <= 365


class TestRULCriticalThreshold:
    """Test boundary: current_deg >= 0.8 returns rul_days=0."""

    def test_critical_degradation_returns_zero_rul(self):
        """Machine at critical threshold should have 0 days RUL."""
        estimator = RULEstimator()
        for i in range(15):
            reading = {
                "vibration": {"rms": 4.0 + i * 0.1},  # High vibration
                "temperature": 70.0 + i * 1.0,         # High temp
                "current": 4.0 + i * 0.1,              # High current
            }
            estimator.update_degradation("M001", reading)

        result = estimator.estimate_rul("M001")
        assert result["rul_days"] == 0, (
            f"Critical machine should have rul_days=0, got {result['rul_days']}"
        )
        assert result["status"] == "Degrading"
        assert result["confidence"] == 0.95


class TestRULSmoothingLogic:
    """Test median filter and EMA smoothing behavior."""

    def test_spike_noise_filtered(self):
        """A single anomalous spike should not drastically change the RUL estimate."""
        estimator_clean = RULEstimator()
        estimator_spike = RULEstimator()

        # Base readings: gentle linear increase
        base_readings = []
        for i in range(20):
            reading = {
                "vibration": {"rms": 0.5 + i * 0.05},
                "temperature": 45.0 + i * 0.5,
                "current": 2.4 + i * 0.02,
            }
            base_readings.append(reading)

        # Clean version
        for r in base_readings:
            estimator_clean.update_degradation("M001", r)

        # Spike version: inject a massive spike at index 10
        for i, r in enumerate(base_readings):
            if i == 10:
                spike_reading = {
                    "vibration": {"rms": 5.0},     # Huge spike
                    "temperature": 80.0,            # Huge spike
                    "current": 4.5,                 # Huge spike
                }
                estimator_spike.update_degradation("M001", spike_reading)
            else:
                estimator_spike.update_degradation("M001", r)

        rul_clean = estimator_clean.estimate_rul("M001")
        rul_spike = estimator_spike.estimate_rul("M001")

        # Both should produce valid RUL
        assert rul_clean["rul_days"] is not None
        assert rul_spike["rul_days"] is not None

        # The spike version should not be drastically different due to median filter
        if rul_clean["rul_days"] > 0 and rul_spike["rul_days"] > 0:
            ratio = rul_spike["rul_days"] / rul_clean["rul_days"]
            assert 0.3 < ratio < 3.0, (
                f"Spike should be filtered: clean={rul_clean['rul_days']}, "
                f"spike={rul_spike['rul_days']}, ratio={ratio:.2f}"
            )

    def test_confidence_is_bounded(self):
        """Confidence should always be between 0.05 and 0.95."""
        estimator = RULEstimator()
        for i in range(20):
            reading = {
                "vibration": {"rms": 0.5 + i * 0.05},
                "temperature": 45.0 + i * 0.5,
                "current": 2.4 + i * 0.02,
            }
            estimator.update_degradation("M001", reading)

        result = estimator.estimate_rul("M001")
        assert 0.05 <= result["confidence"] <= 0.95, (
            f"Confidence out of bounds: {result['confidence']}"
        )

    def test_noisy_sensor_trend_reports_low_confidence_without_artificial_floor(self):
        """
        Regression guard for Fix 4:
        Noisy or erratic degradation data (R^2 near 0) must report honest low confidence
        near the 0.05 floor, and must NEVER be artificially clamped to >= 0.50.
        Tests both RULEstimator and _EMAFallback.
        """
        from server.atlas.rul_engine import _EMAFallback

        np.random.seed(2)
        n_points = 40
        noisy_samples = list(np.random.uniform(0.15, 0.65, n_points))

        # 1. Test RULEstimator
        estimator = RULEstimator()
        for s in noisy_samples:
            estimator.update_degradation("M_NOISY", {
                "vibration": {"rms": s * 5.0},
                "temperature": 45.0,
                "current": 2.5
            })
        res_est = estimator.estimate_rul("M_NOISY")
        assert res_est["confidence"] < 0.35, (
            f"RULEstimator must not inflate confidence on noisy data: got {res_est['confidence']}"
        )
        assert res_est["confidence"] >= 0.05

        # 2. Test _EMAFallback
        fallback = _EMAFallback()
        for s in noisy_samples:
            fallback.update("M_NOISY", s)
        rul_days, conf_fb, uncert, status = fallback.predict("M_NOISY")
        assert conf_fb < 0.35, (
            f"_EMAFallback must not inflate confidence on noisy data: got {conf_fb}"
        )
        assert conf_fb >= 0.05

    def test_clean_linear_trend_reports_high_confidence(self):
        """
        Confirms that genuine, clean linear degradation trends maintain high confidence (>= 0.85)
        and are not regressed by the confidence floor change.
        """
        from server.atlas.rul_engine import _EMAFallback

        np.random.seed(42)
        clean_samples = [0.20 + 0.015 * i + np.random.normal(0, 0.002) for i in range(30)]

        # 1. Test RULEstimator
        estimator = RULEstimator()
        for s in clean_samples:
            estimator.update_degradation("M_CLEAN", {
                "vibration": {"rms": s * 5.0},
                "temperature": 45.0,
                "current": 2.5
            })
        res_est = estimator.estimate_rul("M_CLEAN")
        assert res_est["confidence"] >= 0.85, (
            f"RULEstimator should have high confidence on clean linear data: got {res_est['confidence']}"
        )

        # 2. Test _EMAFallback
        fallback = _EMAFallback()
        for s in clean_samples:
            fallback.update("M_CLEAN", s)
        rul_days, conf_fb, uncert, status = fallback.predict("M_CLEAN")
        assert conf_fb >= 0.85, (
            f"_EMAFallback should have high confidence on clean linear data: got {conf_fb}"
        )

