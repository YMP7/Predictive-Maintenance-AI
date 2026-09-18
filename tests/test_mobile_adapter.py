import time
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
    
    # Canonical model keys must be present in features
    canonical_keys = {
        "battery_level",
        "battery_temp",
        "battery_current",
        "memory_used_percent",
        "cpu_usage",
    }
    assert canonical_keys.issubset(set(reading.features.keys()))
    # Multi-sensor expansion exposes physical hardware channels
    assert "accel_x" in reading.features
    assert "gyro_x" in reading.features
    assert "battery_voltage" in reading.features
    # Model contract: feature_vector must be exactly length 5 for WorldModel
    assert len(reading.feature_vector) == 5
    
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
    adapter._wifi_cache = mock_data
    adapter._wifi_cache_time = time.time()
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


def test_mobile_adapter_browser_push():
    from server.adapters.mobile_adapter import push_browser_telemetry
    
    push_browser_telemetry({
        "battery_percent": 92.0,
        "temperature_c": 29.5,
        "current_ma": 280.0,
        "cpu_percent": 18.0,
        "memory_percent": 45.0,
        "source": "Lumia Web Bridge",
        "platform": "windows_phone"
    })
    
    adapter = MobileAdapter()
    reading = adapter.get_reading("mobile_device_1")
    
    assert reading.adapter_status == AdapterStatus.LIVE.value
    assert reading.features["battery_level"] == 0.92
    assert reading.operational_ctx["platform"] == "windows_phone"
    assert reading.metadata["source"] == "Lumia Web Bridge"
    assert reading.metadata["simulated"] is False


def test_mobile_adapter_multi_device_enumeration():
    adapter = MobileAdapter()
    assert adapter.machine_ids == ["mobile_device_1", "mobile_device_2"]


def test_mobile_adapter_dual_device_differentiation():
    adapter = MobileAdapter()
    reading_1 = adapter.get_reading("mobile_device_1")
    reading_2 = adapter.get_reading("mobile_device_2")

    assert reading_1.machine_id == "mobile_device_1"
    assert reading_2.machine_id == "mobile_device_2"
    assert reading_1.operational_ctx["transport"] == "wifi"
    assert reading_2.operational_ctx["transport"] == "usb"
    # Readings are independent
    assert "battery_level" in reading_1.features
    assert "battery_level" in reading_2.features


def test_mobile_adapter_per_device_browser_push():
    from server.adapters.mobile_adapter import push_browser_telemetry

    push_browser_telemetry({
        "machine_id": "mobile_device_2",
        "battery_percent": 88.0,
        "temperature_c": 31.0,
        "current_ma": 450.0,
        "source": "Lumia Secondary Push",
        "platform": "windows_phone"
    })

    adapter = MobileAdapter()
    reading_2 = adapter.get_reading("mobile_device_2")

    assert reading_2.machine_id == "mobile_device_2"
    assert reading_2.adapter_status == AdapterStatus.LIVE.value
    assert reading_2.features["battery_level"] == 0.88
    assert reading_2.metadata["source"] == "Lumia Secondary Push"

