import pytest
import json
from unittest.mock import MagicMock, patch
from server.mqtt_client import MQTTClientManager, TelemetryPayload
from pydantic import ValidationError

@pytest.fixture
def mock_mqtt_manager():
    # Mock environment variables to satisfy loud failure check
    with patch.dict('os.environ', {'MQTT_BROKER_HOST': 'localhost', 'MQTT_USERNAME': 'test', 'MQTT_PASSWORD': 'pwd', 'CORS_ORIGINS': 'http://localhost:3000'}):
        ingest_cb = MagicMock()
        manager = MQTTClientManager(ingest_cb)
        return manager, ingest_cb

def test_mqtt_valid_payload(mock_mqtt_manager):
    manager, ingest_cb = mock_mqtt_manager
    
    # Create a dummy message
    msg = MagicMock()
    msg.topic = "factory/M001/telemetry"
    valid_data = {
        "timestamp": "2026-07-08T12:00:00Z",
        "vibration": {"x": 0.5, "y": 0.6, "z": 0.2, "rms": 0.8},
        "temperature": 45.0,
        "current": 2.5
    }
    msg.payload = json.dumps(valid_data).encode('utf-8')
    
    # Invoke callback
    manager.on_message(manager.client, None, msg)
    
    # Verify ingest callback was called with parsed data
    ingest_cb.assert_called_once()
    args, _ = ingest_cb.call_args
    assert args[0] == "M001"
    assert args[1]["temperature"] == 45.0

def test_mqtt_malformed_json(mock_mqtt_manager, caplog):
    manager, ingest_cb = mock_mqtt_manager
    
    msg = MagicMock()
    msg.topic = "factory/M001/telemetry"
    msg.payload = b"this is not json"
    
    manager.on_message(manager.client, None, msg)
    
    # Should not crash, and callback should not be called
    ingest_cb.assert_not_called()
    assert "Dropped MQTT message" in caplog.text
    assert "malformed JSON" in caplog.text

def test_mqtt_validation_failure(mock_mqtt_manager, caplog):
    manager, ingest_cb = mock_mqtt_manager
    
    msg = MagicMock()
    msg.topic = "factory/M001/telemetry"
    invalid_data = {
        "timestamp": "2026-07-08T12:00:00Z",
        "vibration": {"x": 0.5, "y": 0.6, "z": 0.2, "rms": 0.8},
        "temperature": -200,  # Below ge=-100 bound
        "current": 2.5
    }
    msg.payload = json.dumps(invalid_data).encode('utf-8')
    
    manager.on_message(manager.client, None, msg)
    
    # Should not crash, and callback should not be called
    ingest_cb.assert_not_called()
    assert "Dropped MQTT message" in caplog.text
    assert "validation failure" in caplog.text

def test_mqtt_invalid_topic(mock_mqtt_manager, caplog):
    manager, ingest_cb = mock_mqtt_manager
    
    msg = MagicMock()
    # Invalid topic structure
    msg.topic = "factory/M001/somethingelse"
    msg.payload = json.dumps({"timestamp": "2026-07-08T12:00:00Z", "temperature": 45, "current": 2, "vibration": {"x":0,"y":0,"z":0,"rms":0}}).encode('utf-8')
    
    manager.on_message(manager.client, None, msg)
    ingest_cb.assert_not_called()
    assert "unexpected topic" in caplog.text

def test_missing_credentials():
    with patch.dict('os.environ', {'CORS_ORIGINS': 'http://localhost:3000'}, clear=True):
        # Should raise ValueError
        with pytest.raises(ValueError, match="MQTT credentials are required"):
            MQTTClientManager(MagicMock())

def test_tls_enforced_in_production():
    with patch.dict('os.environ', {'CORS_ORIGINS': 'https://prod.example.com', 'MQTT_TLS_ENABLED': 'false'}, clear=True):
        with pytest.raises(ValueError, match="TLS must be enabled"):
            MQTTClientManager(MagicMock())

def test_tls_enabled_in_production():
    with patch.dict('os.environ', {'CORS_ORIGINS': 'https://prod.example.com', 'MQTT_TLS_ENABLED': 'true', 'MQTT_BROKER_HOST': 'localhost', 'MQTT_USERNAME': 'test', 'MQTT_PASSWORD': 'pwd'}, clear=True):
        with patch('paho.mqtt.client.Client.tls_set') as mock_tls_set:
            # Should initialize normally without raising ValueError
            manager = MQTTClientManager(MagicMock())
            assert manager.tls_enabled is True
            mock_tls_set.assert_called_once()
