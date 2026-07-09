"""
Tests for the Phase 5 notification integration.

Covers:
1. Critical alert triggers SMS + email dispatch (mocked)
2. Debounce suppresses second alert within cooldown window
3. Dispatch failure does not crash ingestion pipeline
4. NOTIFICATIONS_ENABLED=false sends nothing externally
5. Missing credentials with NOTIFICATIONS_ENABLED=true fails loudly at startup
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_critical_alert(machine_id="M001", fault_type="Bearing Wear"):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "machine_id": machine_id,
        "type": "Fault Detection",
        "severity": "Critical",
        "message": f"Critical Vibration Level detected in {machine_id}",
        "fault_type": fault_type,
    }


def _make_high_alert(machine_id="M001", fault_type="Misalignment"):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "machine_id": machine_id,
        "type": "Fault Detection",
        "severity": "High",
        "message": f"Elevated Vibration (Warning) detected in {machine_id}",
        "fault_type": fault_type,
    }


# ---------------------------------------------------------------------------
# 1. Critical alert triggers SMS + email dispatch
# ---------------------------------------------------------------------------

@patch.dict(os.environ, {
    "NOTIFICATIONS_ENABLED": "true",
    "TWILIO_ACCOUNT_SID": "ACtest123",
    "TWILIO_AUTH_TOKEN": "token123",
    "TWILIO_FROM_NUMBER": "+15551234567",
    "TWILIO_TO_NUMBER": "+15559876543",
    "SMTP_HOST": "smtp.test.com",
    "SMTP_PORT": "587",
    "SMTP_FROM": "alerts@test.com",
    "SMTP_USER": "user",
    "SMTP_PASSWORD": "pass",
    "ALERT_EMAIL_TO": "admin@test.com",
    "ALERT_COOLDOWN": "300",
})
def test_critical_alert_triggers_sms_and_email():
    """A Critical alert should attempt SMS + email delivery (via mocked providers)."""
    # Reset singleton
    import server.alert_handler as ah
    ah._alert_handler = None

    handler = ah.AlertHandler()

    # Mock DB cooldown check to allow dispatch
    handler._check_db_cooldown = MagicMock(return_value=False)
    handler._record_notification = MagicMock()
    # Mock recipient lookup to return empty (will fall back to env vars)
    handler._get_admin_recipients = MagicMock(return_value=[])

    sms_called = []
    email_called = []

    original_deliver_sms = handler._deliver_sms
    original_deliver_email = handler._deliver_email

    def mock_sms(alert):
        sms_called.append(alert)

    def mock_email(alert):
        email_called.append(alert)

    handler._deliver_sms = mock_sms
    handler._deliver_email = mock_email

    alert = _make_critical_alert()
    result = handler.queue_alert(alert)

    assert result is True, "Critical alert should be queued successfully"
    assert len(sms_called) == 1, "SMS should be called once for Critical alert"
    assert len(email_called) == 1, "Email should be called once for Critical alert"


# ---------------------------------------------------------------------------
# 2. Debounce suppresses second alert within cooldown window
# ---------------------------------------------------------------------------

@patch.dict(os.environ, {
    "NOTIFICATIONS_ENABLED": "false",
    "ALERT_COOLDOWN": "300",
})
def test_debounce_suppresses_second_alert():
    """Second identical alert within cooldown window should be suppressed."""
    import server.alert_handler as ah
    ah._alert_handler = None

    handler = ah.AlertHandler()
    handler._check_db_cooldown = MagicMock(return_value=False)

    alert = _make_critical_alert(machine_id="M002", fault_type="Overheating")

    # First alert should go through
    result1 = handler.queue_alert(alert)
    assert result1 is True, "First alert should be queued"

    # Second identical alert should be suppressed by in-memory cooldown
    result2 = handler.queue_alert(alert)
    assert result2 is False, "Second alert within cooldown should be suppressed"


# ---------------------------------------------------------------------------
# 3. DB-backed debounce suppresses after restart
# ---------------------------------------------------------------------------

@patch.dict(os.environ, {
    "NOTIFICATIONS_ENABLED": "false",
    "ALERT_COOLDOWN": "300",
})
def test_db_cooldown_suppresses_after_restart():
    """DB cooldown check should suppress alerts even when in-memory state is empty (simulating restart)."""
    import server.alert_handler as ah
    ah._alert_handler = None

    handler = ah.AlertHandler()
    # Simulate DB saying a notification was sent 60 seconds ago (within 300s window)
    handler._check_db_cooldown = MagicMock(return_value=True)

    alert = _make_critical_alert(machine_id="M003", fault_type="Electrical Fault")

    result = handler.queue_alert(alert)
    assert result is False, "Alert should be suppressed by DB cooldown"
    handler._check_db_cooldown.assert_called_once_with("M003", "Electrical Fault")


# ---------------------------------------------------------------------------
# 4. Dispatch failure does not crash ingestion
# ---------------------------------------------------------------------------

@patch.dict(os.environ, {
    "NOTIFICATIONS_ENABLED": "true",
    "TWILIO_ACCOUNT_SID": "ACtest123",
    "TWILIO_AUTH_TOKEN": "token123",
    "TWILIO_FROM_NUMBER": "+15551234567",
    "SMTP_HOST": "smtp.test.com",
    "SMTP_FROM": "alerts@test.com",
    "ALERT_COOLDOWN": "300",
})
def test_dispatch_failure_does_not_crash():
    """If Twilio or SMTP raises, the handler should log the error, not propagate it."""
    import server.alert_handler as ah
    ah._alert_handler = None

    handler = ah.AlertHandler()
    handler._check_db_cooldown = MagicMock(return_value=False)
    handler._record_notification = MagicMock()
    handler._get_admin_recipients = MagicMock(return_value=[])

    # Make SMS and email delivery raise exceptions
    handler._deliver_sms = MagicMock(side_effect=Exception("Twilio API down"))
    handler._deliver_email = MagicMock(side_effect=Exception("SMTP timeout"))

    alert = _make_critical_alert(machine_id="M004", fault_type="Bearing Wear")

    # Should NOT raise — the handler catches delivery errors
    result = handler.queue_alert(alert)
    assert result is True, "Alert should still be queued despite delivery failures"


# ---------------------------------------------------------------------------
# 5. NOTIFICATIONS_ENABLED=false sends nothing externally
# ---------------------------------------------------------------------------

@patch.dict(os.environ, {
    "NOTIFICATIONS_ENABLED": "false",
    "ALERT_COOLDOWN": "300",
})
def test_notifications_disabled_sends_nothing():
    """When NOTIFICATIONS_ENABLED=false, only dashboard/log channels should be used."""
    import server.alert_handler as ah
    ah._alert_handler = None

    handler = ah.AlertHandler()
    handler._check_db_cooldown = MagicMock(return_value=False)

    alert = _make_critical_alert(machine_id="M005", fault_type="Overheating")
    result = handler.queue_alert(alert)
    assert result is True

    channels = handler.get_channels_by_severity("Critical")
    channel_values = [c.value for c in channels]
    assert "sms" not in channel_values, "SMS should not be routed when notifications disabled"
    assert "email" not in channel_values, "Email should not be routed when notifications disabled"
    assert "voice" not in channel_values, "Voice should not be routed when notifications disabled"
    assert "dashboard" in channel_values, "Dashboard should still be routed"
    assert "log" in channel_values, "Log should still be routed"


# ---------------------------------------------------------------------------
# 6. Missing credentials with NOTIFICATIONS_ENABLED=true fails loudly
# ---------------------------------------------------------------------------

@patch.dict(os.environ, {
    "NOTIFICATIONS_ENABLED": "true",
    # Deliberately omitting TWILIO_ACCOUNT_SID, SMTP_HOST, etc.
}, clear=False)
def test_missing_credentials_fails_loudly():
    """NOTIFICATIONS_ENABLED=true with missing Twilio/SMTP creds must raise RuntimeError."""
    import server.alert_handler as ah
    ah._alert_handler = None

    # Remove any credentials that might be set from other tests or .env
    env_overrides = {
        "NOTIFICATIONS_ENABLED": "true",
        "TWILIO_ACCOUNT_SID": "",
        "TWILIO_AUTH_TOKEN": "",
        "TWILIO_FROM_NUMBER": "",
        "SMTP_HOST": "",
        "SMTP_FROM": "",
        "SMTP_USER": "",
    }
    with patch.dict(os.environ, env_overrides):
        with pytest.raises(RuntimeError, match="NOTIFICATIONS_ENABLED=true but missing credentials"):
            ah.AlertHandler()


# ---------------------------------------------------------------------------
# 7. Severity routing correctness
# ---------------------------------------------------------------------------

@patch.dict(os.environ, {
    "NOTIFICATIONS_ENABLED": "true",
    "TWILIO_ACCOUNT_SID": "ACtest123",
    "TWILIO_AUTH_TOKEN": "token123",
    "TWILIO_FROM_NUMBER": "+15551234567",
    "SMTP_HOST": "smtp.test.com",
    "SMTP_FROM": "alerts@test.com",
    "ALERT_COOLDOWN": "300",
})
def test_severity_routing():
    """Verify each severity level maps to correct channels."""
    import server.alert_handler as ah
    ah._alert_handler = None

    handler = ah.AlertHandler()

    critical_channels = {c.value for c in handler.get_channels_by_severity("Critical")}
    assert critical_channels == {"dashboard", "log", "sms", "email", "voice"}

    high_channels = {c.value for c in handler.get_channels_by_severity("High")}
    assert high_channels == {"dashboard", "log", "sms", "email"}

    medium_channels = {c.value for c in handler.get_channels_by_severity("Medium")}
    assert medium_channels == {"dashboard", "log", "email"}

    low_channels = {c.value for c in handler.get_channels_by_severity("Low")}
    assert low_channels == {"dashboard", "log"}


# ---------------------------------------------------------------------------
# 8. High alert triggers email but no voice
# ---------------------------------------------------------------------------

@patch.dict(os.environ, {
    "NOTIFICATIONS_ENABLED": "true",
    "TWILIO_ACCOUNT_SID": "ACtest123",
    "TWILIO_AUTH_TOKEN": "token123",
    "TWILIO_FROM_NUMBER": "+15551234567",
    "SMTP_HOST": "smtp.test.com",
    "SMTP_FROM": "alerts@test.com",
    "ALERT_COOLDOWN": "300",
})
def test_high_alert_no_voice():
    """High severity should trigger SMS + email but NOT voice."""
    import server.alert_handler as ah
    ah._alert_handler = None

    handler = ah.AlertHandler()
    handler._check_db_cooldown = MagicMock(return_value=False)
    handler._record_notification = MagicMock()
    handler._get_admin_recipients = MagicMock(return_value=[])

    voice_called = []
    sms_called = []
    email_called = []

    handler._deliver_voice = lambda a: voice_called.append(a)
    handler._deliver_sms = lambda a: sms_called.append(a)
    handler._deliver_email = lambda a: email_called.append(a)

    alert = _make_high_alert(machine_id="M006", fault_type="Misalignment")
    result = handler.queue_alert(alert)

    assert result is True
    assert len(sms_called) == 1, "SMS should fire for High"
    assert len(email_called) == 1, "Email should fire for High"
    assert len(voice_called) == 0, "Voice should NOT fire for High"
