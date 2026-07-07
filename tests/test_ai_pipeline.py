"""
Tests for the AI agent processing pipeline.
"""

import time

from ai_agent import AIAgent
from data_service import get_data_service
from sensor_simulator import MultiMachineSimulator


VALID_STATUSES = {"Normal", "Warning", "Critical"}
VALID_SEVERITIES = {"Low", "Medium", "High", "Critical"}
LATENCY_BUDGET_MS = 100


def _assert_valid_result(result):
    assert result["machine_id"] in {"M001", "M002", "M003", "M004"}
    assert result["status"] in VALID_STATUSES
    assert isinstance(result["fault_type"], str)
    assert isinstance(result["detected_issues"], list)
    assert isinstance(result["rul_days"], (int, float, type(None)))
    assert isinstance(result["rul_confidence"], (int, float))
    assert 0 <= result["rul_confidence"] <= 1
    assert isinstance(result["recommendation"], str)

    for alert in result["alerts"]:
        assert alert["machine_id"] == result["machine_id"]
        assert alert["severity"] in VALID_SEVERITIES
        assert alert["message"]
        assert alert["type"]


def test_ai_pipeline_outputs_valid_results_within_latency_budget():
    simulator = MultiMachineSimulator()
    agent = AIAgent()
    service = get_data_service()
    processed_count = 0

    for _ in range(50):
        readings = simulator.get_all_readings()
        assert len(readings) == 4

        for reading in readings:
            start = time.perf_counter()
            result = agent.process_reading(reading)
            latency_ms = (time.perf_counter() - start) * 1000

            assert latency_ms < LATENCY_BUDGET_MS
            _assert_valid_result(result)
            processed_count += 1

    assert processed_count == 200

    summary = service.get_dashboard_summary()
    counts = summary["machine_status_counts"]
    assert summary["total_machines"] == 4
    assert counts["Normal"] + counts["Warning"] + counts["Critical"] == 4
