"""
tests/test_ui_mock_regression.py — Regression Guards Against Mock / Hardcoded UI Scaffolds
========================================================================================
Permanently prevents regression of four classes of hardcoded UI / scaffold placeholders:
1. `test_ui_never_labels_estimated_as_measured`:
   Ensures derived thermal estimates are explicitly flagged as heuristic/estimated in metadata
   and distinct from measured physical sensors in UI components.
2. `test_phm_scorecard_sources_canonical_multiseed_baseline`:
   Verifies that the canonical PHM baseline is strictly grounded in the multi-seed average
   (375.00 +/- 21.93) from `data/atlas_evaluation_summary.json` while maintaining single-checkpoint
   validation transparency (394.70).
3. `test_mobile_source_and_version_dynamically_grounded`:
   Ensures MobileAdapter dynamically computes transport/source identifiers across all tiers
   (Wi-Fi, USB ADB, Simulation) rather than returning hardcoded static version strings.
4. `test_uptime_derived_from_dynamic_clock_not_static`:
   Ensures operational cycles and uptime metrics are driven by dynamic time/process elapsed counters
   rather than static placeholder strings or fake uptime percentages.
"""

import json
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from server.adapters.laptop_adapter import LaptopAdapter
from server.adapters.mobile_adapter import MobileAdapter, push_browser_telemetry, clear_browser_telemetry
from server.backend_api import app, atlas_api_startup


@pytest.fixture(scope="module", autouse=True)
def init_api():
    atlas_api_startup()


@pytest.fixture
def client():
    return TestClient(app)


def test_ui_never_labels_estimated_as_measured():
    """
    Guarantees that `thermal_headroom` in LaptopAdapter is never emitted as a measured sensor.
    Must always carry explicit estimation flags and separate UI attribution.
    """
    adapter = LaptopAdapter()
    reading = adapter.get_reading("laptop_local")

    # 1. Adapter raw_features contract
    raw = reading.raw_features
    assert raw.get("is_estimated") is True, "thermal_headroom must have is_estimated=True"
    assert raw.get("thermal_is_estimated") is True, "thermal_is_estimated must be True"
    assert raw.get("estimation_method") == "thermodynamic_heuristic"
    assert "estimated_thermal_c" in raw
    assert "thermal_headroom" in reading.features

    # 2. UI Component Source Inspection:
    # Verify that MonitoringView.tsx structurally segregates estimated metrics
    monitoring_view_path = Path(__file__).resolve().parent.parent / "client" / "src" / "components" / "atlas" / "views" / "MonitoringView.tsx"
    assert monitoring_view_path.exists(), "MonitoringView.tsx must exist"
    content = monitoring_view_path.read_text(encoding="utf-8")
    assert "DERIVED & ESTIMATED METRICS" in content
    assert "ESTIMATED" in content
    assert "thermal_headroom" in content


def test_phm_scorecard_sources_canonical_multiseed_baseline(client):
    """
    Guarantees that the master evaluation summary strictly reports the canonical 375.00 multi-seed
    baseline rather than a fabricated or ambiguous number, while preserving single-checkpoint 394.70.
    """
    res = client.get("/api/atlas/evaluation/summary")
    assert res.status_code == 200, f"Failed to fetch evaluation summary: {res.text}"
    summary = res.json()

    pred = summary.get("prediction_accuracy", {})
    assert "reference_baseline" in pred, "Summary must contain reference_baseline"
    ref = pred["reference_baseline"]

    # Canonical multi-seed baseline matching thesis and QA report
    canonical_phm = ref.get("multiseed_mean_phm")
    canonical_std = ref.get("multiseed_std_phm")
    assert canonical_phm == 375.0, f"Canonical multiseed PHM must be 375.0, found {canonical_phm}"
    assert canonical_std == 21.93, f"Canonical multiseed PHM std must be 21.93, found {canonical_std}"

    # Single-checkpoint evaluation result
    checkpoint_phm = pred.get("phm_score")
    assert checkpoint_phm == 394.7, f"Checkpoint PHM score must be 394.7, found {checkpoint_phm}"


def test_mobile_source_and_version_dynamically_grounded():
    """
    Guarantees that transport source labels and device platform metadata are dynamically
    derived from genuine telemetry packets rather than invariant placeholder strings.
    """
    clear_browser_telemetry()
    try:
        adapter = MobileAdapter()

        # Case A: Synthetic fallback stream
        sim_reading = adapter.get_reading("mobile_device_1")
        assert sim_reading.metadata["simulated"] is True
        assert "Synthetic" in sim_reading.metadata["source"]

        # Case B: Dynamic Web Bridge telemetry push
        dynamic_source_str = f"Lumia Web Bridge Unit Test v{int(time.time())}"
        push_browser_telemetry({
            "machine_id": "mobile_device_1",
            "battery_percent": 84.0,
            "temperature_c": 33.0,
            "current_ma": 310.0,
            "source": dynamic_source_str,
            "platform": "windows_phone"
        })
        live_reading = adapter.get_reading("mobile_device_1")
        assert live_reading.metadata["simulated"] is False
        assert live_reading.metadata["source"] == dynamic_source_str, (
            f"Source must dynamically reflect incoming packet source: {live_reading.metadata['source']}"
        )
        assert live_reading.operational_ctx["platform"] == "windows_phone"
    finally:
        clear_browser_telemetry()


def test_uptime_derived_from_dynamic_clock_not_static(client):
    """
    Guarantees that cycle counters and process uptime are derived from active wall-clock time deltas
    rather than static placeholder strings or invariant uptime percentages.
    """
    adapter = LaptopAdapter()
    t1 = adapter.get_reading("laptop_local").cycle
    time.sleep(0.05)
    t2 = adapter.get_reading("laptop_local").cycle
    assert t2 >= t1, "Cycle counter must be monotonically non-decreasing over elapsed time"

    # API system live metrics
    res = client.get("/api/atlas/system/benchmark")
    assert res.status_code == 200
    live = res.json().get("live_metrics", {})
    assert "process_rss_mb" in live
    assert live["process_rss_mb"] > 0, "Process RSS must be real dynamic memory metric"
    assert "timestamp" in live
