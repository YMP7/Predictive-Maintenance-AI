"""
tests/test_benchmark.py — Unit Tests for System Benchmark Runner & Metrics
==========================================================================
Verifies that the benchmarking harness captures valid hardware context, calculates
correct non-negative percentile statistics (p50 <= p95 <= p99), and executes cleanly.
"""

import sys
from pathlib import Path
import numpy as np
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.benchmark_system import LatencyStats, capture_hardware_context, SystemBenchmarkRunner


def test_latency_stats_percentile_properties():
    """Confirms mathematical consistency of computed latency statistics."""
    # Monotonically increasing mock durations in seconds
    durations = [0.001 * i for i in range(1, 101)]  # 1ms to 100ms
    stats = LatencyStats.from_durations_sec(durations)

    assert stats.n_samples == 100
    assert stats.min_ms == pytest.approx(1.0, rel=1e-2)
    assert stats.max_ms == pytest.approx(100.0, rel=1e-2)
    assert stats.min_ms <= stats.p50_ms <= stats.p95_ms <= stats.p99_ms <= stats.max_ms
    assert stats.mean_ms == pytest.approx(50.5, rel=1e-2)


def test_hardware_context_capture():
    """Confirms hardware context captures non-empty system metadata."""
    hw = capture_hardware_context()
    assert hw.platform in ["Windows", "Linux", "Darwin"]
    assert hw.physical_cores >= 1
    assert hw.logical_cores >= 1
    assert hw.total_ram_gb > 0
    assert len(hw.python_version) > 0
    assert len(hw.torch_version) > 0
    assert hw.torch_backend in ["CPU", "CUDA"]
    assert hw.torch_num_threads >= 1


def test_benchmark_runner_smoke_test(tmp_path):
    """Smoke tests the runner with low trial counts (n_trials=2, warmup=1)."""
    runner = SystemBenchmarkRunner(
        n_trials=2,
        n_warmup=1,
    )
    s1 = runner.benchmark_stage_1_adapters()
    assert "cmapss" in s1
    assert "laptop" in s1
    assert s1["cmapss"].n_samples == 2
    assert s1["cmapss"].p50_ms > 0

    s2 = runner.benchmark_stage_2_world_model()
    assert "cmapss" in s2
    assert s2["cmapss"].n_samples == 2

    s4 = runner.benchmark_stage_4_machine_dna()
    assert s4.n_samples == 2

    s6 = runner.benchmark_stage_6_simulation()
    assert s6.n_samples == 2

    s7 = runner.benchmark_stage_7_decision_graph()
    assert s7.n_samples == 2
