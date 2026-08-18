import pytest
from unittest.mock import patch, MagicMock
from server.adapters.mobile_adapter import MobileAdapter
from server.adapters.base_adapter import AdapterStatus
from server.atlas.domain_service import DomainService


def test_mobile_adapter_simulation_fallback():
    adapter = MobileAdapter(endpoint_url="http://invalid.local.termux:9999")
    adapter.connect()
    
    assert adapter._is_live is False
    
    reading = adapter.get_reading("mobile_device_1")
    
    assert reading.domain == "mobile"
    assert reading.machine_id == "mobile_device_1"
    assert reading.rul_label is None
    assert reading.adapter_status == AdapterStatus.SIMULATION.value
    
    # 5 features
    expected_keys = {
        "battery_level",
        "battery_temp",
        "battery_current",
        "memory_used_percent",
        "cpu_usage",
    }
    assert set(reading.features.keys()) == expected_keys
    
    # Bounds check [0, 1]
    for k, v in reading.features.items():
        assert 0.0 <= v <= 1.0, f"Feature {k} out of bounds: {v}"
        
    # Health Index bounds
    assert 0.0 <= reading.health_index <= 1.0


def test_mobile_adapter_live_mock():
    adapter = MobileAdapter(endpoint_url="http://localhost:8088")
    
    mock_data = {
        "percentage": 75.0,
        "temperature": 32.5,
        "current": 420.0,
        "cpu_percent": 35.0,
        "memory_percent": 60.0
    }
    
    adapter._is_live = True
    with patch.object(adapter, "_poll_termux_live", return_value=mock_data):
        reading = adapter.get_reading("mobile_device_1")
        
        assert reading.adapter_status == AdapterStatus.LIVE.value
        assert reading.features["battery_level"] == 0.75
        assert 0.0 <= reading.features["battery_temp"] <= 1.0
        assert reading.health_index > 0.0


def test_domain_service_register_mobile():
    service = DomainService()
    success = service.register_mobile()
    assert success is True
    assert "mobile" in service._adapters
    assert "mobile" in service._engines
