"""
Unit tests for Month 8 Week 2 Resource Profiling & API Load Testing Harness.
"""

from pathlib import Path
import numpy as np
import pytest

from scripts.profile_resources import (
    compute_latency_stats,
    get_current_process_memory_mb,
    SystemResourceProfiler,
)


def test_compute_latency_stats_percentile_properties():
    """Verify statistical properties and monotonic percentiles."""
    raw = [5.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0, 50.0, 100.0]
    stats = compute_latency_stats(raw)

    assert stats["min_ms"] == 5.0
    assert stats["max_ms"] == 100.0
    assert stats["min_ms"] <= stats["p50_ms"] <= stats["p95_ms"] <= stats["p99_ms"] <= stats["max_ms"]
    assert np.isclose(stats["mean_ms"], np.mean(raw))


def test_get_current_process_memory_mb():
    """Verify process memory lookup returns positive float."""
    rss = get_current_process_memory_mb()
    assert isinstance(rss, float)
    assert rss > 10.0  # Python runtime should take >10 MB


def test_hardware_context_capture():
    """Verify hardware context dictionary structure."""
    profiler = SystemResourceProfiler()
    hw = profiler.hardware_context

    assert "platform" in hw
    assert "processor" in hw
    assert "physical_cores" in hw
    assert "total_ram_gb" in hw
    assert "torch_version" in hw
    assert hw["total_ram_gb"] > 0


def test_resource_profiler_smoke_test(tmp_path):
    """Smoke test running memory profiling on models."""
    profiler = SystemResourceProfiler()
    mem = profiler.profile_memory_footprint()

    assert "baseline_process_ram_mb" in mem
    assert "ram_after_loading_models_mb" in mem
    assert "leak_audit" in mem
    assert mem["leak_audit"]["cycles_evaluated"] == 100
    assert isinstance(mem["leak_audit"]["net_memory_delta_mb"], float)
