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


def test_mqtt_rejects_unregistered_machine_id(mock_mqtt_manager, caplog):
    """
    Security test: Unregistered machine_id extracted from topic must be rejected
    before JSON deserialization or ingestion, logging a security warning.
    """
    manager, ingest_cb = mock_mqtt_manager

    msg = MagicMock()
    msg.topic = "factory/ROGUE_UNKNOWN_MACHINE/telemetry"
    valid_data = {
        "timestamp": "2026-07-08T12:00:00Z",
        "vibration": {"x": 0.5, "y": 0.6, "z": 0.2, "rms": 0.8},
        "temperature": 45.0,
        "current": 2.5
    }
    msg.payload = json.dumps(valid_data).encode("utf-8")

    manager.on_message(manager.client, None, msg)

    # Ingestion callback must NEVER be called
    ingest_cb.assert_not_called()
    assert "[SECURITY WARNING]" in caplog.text
    assert "ROGUE_UNKNOWN_MACHINE" in caplog.text
    assert "not registered" in caplog.text


def test_mqtt_accepts_registered_machine_id(mock_mqtt_manager):
    """
    Legitimate registered machine_id must pass through smoothly and reach ingest_callback.
    """
    manager, ingest_cb = mock_mqtt_manager

    msg = MagicMock()
    msg.topic = "factory/M002/telemetry"
    valid_data = {
        "timestamp": "2026-07-08T12:00:00Z",
        "vibration": {"x": 0.3, "y": 0.4, "z": 0.1, "rms": 0.5},
        "temperature": 42.0,
        "current": 2.1
    }
    msg.payload = json.dumps(valid_data).encode("utf-8")

    manager.on_message(manager.client, None, msg)

    ingest_cb.assert_called_once()
    args, _ = ingest_cb.call_args
    assert args[0] == "M002"
    assert args[1]["temperature"] == 42.0


def test_plaintext_password_files_not_tracked_in_git():
    """
    Git hygiene test: Confirms that pwfile.raw or any *.raw credential file
    under mosquitto/config/ is not present in git tracking index.
    """
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    res = subprocess.run(
        ["git", "ls-files", "mosquitto/config/"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True
    )
    tracked_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    raw_files = [f for f in tracked_files if f.endswith(".raw")]

    assert not raw_files, f"Plaintext password files must not be tracked in git index! Found: {raw_files}"
    assert "mosquitto/config/pwfile.raw" not in tracked_files

