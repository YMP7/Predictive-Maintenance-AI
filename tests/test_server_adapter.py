import math
import pytest
from unittest.mock import MagicMock, patch

from server.adapters.base_adapter import AdapterStatus
from server.adapters.server_adapter import ServerAdapter
from server.atlas.domain_service import DomainService


def test_server_adapter_simulation_features_and_bounds():
    adapter = ServerAdapter(has_gpu=True)
    adapter.connect()

    assert adapter._is_live is False
    reading = adapter.get_reading("server_prod_1")

    assert reading.domain == "server"
    assert reading.machine_id == "server_prod_1"
    assert reading.rul_label is None
    assert reading.adapter_status == AdapterStatus.SIMULATION.value

    # 5 standard features
    expected_keys = {
        "cpu_usage",
        "memory_usage",
        "disk_usage",
        "network_io_rate",
        "gpu_utilization",
    }
    assert set(reading.features.keys()) == expected_keys

    # Value bounds in [0.0, 1.0]
    for k, v in reading.features.items():
        assert 0.0 <= v <= 1.0, f"Feature {k} out of bounds: {v}"

    assert 0.0 <= reading.health_index <= 1.0


def test_stress_weights_mathematical_consistency():
    # 1. Assert weights sum strictly to 1.0
    sum_gpu = sum(ServerAdapter.WEIGHTS_WITH_GPU.values())
    sum_no_gpu = sum(ServerAdapter.WEIGHTS_NO_GPU.values())

    assert math.isclose(sum_gpu, 1.0, rel_tol=1e-6), f"GPU weights sum to {sum_gpu}, expected 1.0"
    assert math.isclose(sum_no_gpu, 1.0, rel_tol=1e-6), f"Non-GPU weights sum to {sum_no_gpu}, expected 1.0"

    adapter = ServerAdapter()
    dummy_features = {
        "cpu_usage": 1.0,
        "memory_usage": 1.0,
        "disk_usage": 1.0,
        "network_io_rate": 1.0,
        "gpu_utilization": 1.0,
    }

    # At full saturation (all 1.0), health_index must equal exactly 1.0
    assert math.isclose(adapter.compute_health_index(dummy_features, has_gpu=True), 1.0, rel_tol=1e-6)
    assert math.isclose(adapter.compute_health_index(dummy_features, has_gpu=False), 1.0, rel_tol=1e-6)


def test_server_adapter_live_ssh_mock():
    adapter = ServerAdapter(host="192.168.1.100", username="testuser")
    adapter._is_live = True

    mock_client = MagicMock()
    adapter._ssh_client = mock_client

    def mock_exec_command(cmd, timeout=2.0):
        if "free" in cmd:
            return "Mem: 16000000 8000000"
        elif "loadavg" in cmd:
            return "2.0 1.5 1.0"
        elif "df" in cmd:
            return "/dev/sda1 100000000 40000000"
        elif "net/dev" in cmd:
            return "eth0: 50000000 1000 0 0 0 0 0 0 50000000 1000"
        elif "nvidia-smi" in cmd:
            return "65"
        return ""

    with patch.object(adapter, "_exec_command", side_effect=mock_exec_command):
        reading = adapter.get_reading("server_prod_1")

        assert reading.adapter_status == AdapterStatus.LIVE.value
        assert reading.features["memory_usage"] == 0.5
        assert reading.features["disk_usage"] == 0.4
        assert reading.features["gpu_utilization"] == 0.65
        assert 0.0 <= reading.features["cpu_usage"] <= 1.0
        assert 0.0 <= reading.health_index <= 1.0


def test_server_adapter_transition_on_connection_drop():
    """
    Asserts that if a live SSH connection drops mid-poll, the adapter
    cleanly flips to SIMULATION status and returns a valid reading without crashing.
    """
    adapter = ServerAdapter(host="192.168.1.100", username="testuser")
    adapter._is_live = True
    adapter._ssh_client = MagicMock()

    # Simulate network failure / connection reset
    with patch.object(adapter, "_poll_ssh_live", side_effect=ConnectionResetError("SSH socket closed")):
        reading = adapter.get_reading("server_prod_1")

        # Must auto-transition to simulation fallback
        assert adapter._is_live is False
        assert adapter._ssh_client is None
        assert reading.adapter_status == AdapterStatus.SIMULATION.value
        assert 0.0 <= reading.health_index <= 1.0
        assert len(reading.features) == 5


def test_domain_service_register_server():
    service = DomainService()
    success = service.register_server()
    assert success is True
    assert "server" in service._adapters
    assert "server" in service._engines
