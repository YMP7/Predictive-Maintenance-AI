import pytest
from unittest.mock import MagicMock
import sys

@pytest.fixture(autouse=True)
def _mock_database(monkeypatch):
    mock_db = MagicMock()
    mock_pool = MagicMock()
    mock_db.pool = mock_pool
    mock_conn = MagicMock()
    mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
    
    # Default mock values
    mock_conn.execute.return_value.fetchone.return_value = [0]
    mock_conn.execute.return_value.fetchall.return_value = []
    
    monkeypatch.setitem(sys.modules, "server.database", mock_db)
    
    # Force reload of dependent modules
    for mod_name in list(sys.modules.keys()):
        if mod_name in ("server.agent_tools", "server.backend_api", "server.auth"):
            del sys.modules[mod_name]
            
    return mock_conn

def test_work_order_requires_real_supporting_alert(_mock_database):
    """Attempting High/Critical work order without grounding_alert_id or supporting alert is rejected."""
    from server.agent_tools import create_work_order
    
    _mock_database.execute.return_value.fetchone.return_value = [0]  # count=0
    _mock_database.execute.return_value.fetchall.return_value = []  # no alerts
    
    # 1. Missing grounding_alert_id
    res_no_id = create_work_order("M001", "Fix bearing", "Critical", justification="Fabricated claim")
    assert "error" in res_no_id
    assert "require an explicit grounding_alert_id" in res_no_id["error"]

    # 2. Fabricated alert ID with no database match
    res_fake_id = create_work_order(
        "M001", "Fix bearing", "Critical",
        justification="Fabricated claim",
        fault_type="bearing_wear",
        grounding_alert_id="non-existent-alert-uuid"
    )
    assert "error" in res_fake_id
    assert "not found in recent verified pipeline alerts" in res_fake_id["error"]


def test_critical_work_order_requires_approval(_mock_database):
    """A Critical-urgency order lands as Pending Approval, not Open, until the approve endpoint is called."""
    from server.agent_tools import create_work_order
    
    def execute_side_effect(query, params):
        mock_cursor = MagicMock()
        if "COUNT" in query:
            mock_cursor.fetchone.return_value = [0]
        elif "FROM alerts" in query and "ai_pipeline" in query:
            mock_cursor.fetchall.return_value = [("Critical", "bearing_wear", "High bearing wear detected", "alert-uuid-1")]
        else:
            mock_cursor.fetchone.return_value = None
            mock_cursor.fetchall.return_value = []
        return mock_cursor
        
    _mock_database.execute.side_effect = execute_side_effect
    
    res = create_work_order(
        machine_id="M001",
        action="Replace drive bearing and inspect races",
        urgency="Critical",
        justification="High bearing wear detected",
        fault_type="bearing_wear",
        grounding_alert_id="alert-uuid-1"
    )
    
    assert "error" not in res
    assert res["status"] == "Pending Approval"
    assert res["created_by"] == "agent:atlas"
    
def test_daily_work_order_cap_enforced(_mock_database):
    """4th work order attempt for the same machine in a day is rejected."""
    from server.agent_tools import create_work_order
    
    # Simulate 3 existing work orders
    _mock_database.execute.return_value.fetchone.return_value = [3]
    
    res = create_work_order("M001", "Fix bearing", "Medium", justification="Routine")
    
    assert "error" in res
    assert "Maximum of 3 work orders" in res["error"]

def test_approve_endpoint_respects_rbac():
    """Viewer role cannot call the approve endpoint."""
    from fastapi.testclient import TestClient
    from server.backend_api import app, get_current_user
    from server.auth import User
    
    client = TestClient(app)
    
    # Override get_current_user to simulate a viewer
    app.dependency_overrides[get_current_user] = lambda: User(username="test_viewer", role="viewer")
    
    res = client.post("/api/work-orders/fake-uuid/approve")
    
    # require_operator_or_admin should throw a 403 Forbidden
    assert res.status_code == 403
    
    # Cleanup
    app.dependency_overrides = {}

def test_grounding_check_rejects_non_pipeline_alerts(_mock_database):
    """Test that the grounding check query correctly includes the provenance filter for ai_pipeline."""
    from server.agent_tools import create_work_order
    
    _mock_database.execute.return_value.fetchone.return_value = [0]  # count=0
    _mock_database.execute.return_value.fetchall.return_value = []  # simulate rejection
    
    res = create_work_order(
        machine_id="M001",
        action="Emergency spindle vibration shutdown",
        urgency="Critical",
        justification="Injected alert payload",
        fault_type="vibration_high",
        grounding_alert_id="injected-alert-uuid"
    )
    
    assert "error" in res
    
    # Verify that the query executed to check alerts included the source filter
    queries = [call[0][0] for call in _mock_database.execute.call_args_list]
    grounding_query = next((q for q in queries if "FROM alerts" in q and "severity" in q), None)
    
    assert grounding_query is not None, "Grounding query was not executed"
    assert "source = 'ai_pipeline'" in grounding_query, "Grounding check is missing the provenance source filter!"


def test_work_order_rejects_mismatched_fault_type(_mock_database):
    """
    DEF-012a Exploit tests:
    1. Rejects mismatched fault_type enum even if valid alert ID is provided.
    2. Rejects ungrounded action text even if matching fault_type enum is provided (plausibility gate).
    3. Accepts legitimate bound action with matching alert ID and plausible action text.
    """
    from server.agent_tools import create_work_order
    
    def execute_side_effect(query, params):
        mock_cursor = MagicMock()
        if "COUNT" in query:
            mock_cursor.fetchone.return_value = [0]
        elif "FROM alerts" in query and "ai_pipeline" in query:
            # Genuine Critical alert exists for vibration_high
            mock_cursor.fetchall.return_value = [
                ("Critical", "vibration_high", "Severe spindle vibration spike (rms=4.8)", "alert-vib-001")
            ]
        else:
            mock_cursor.fetchone.return_value = None
            mock_cursor.fetchall.return_value = []
        return mock_cursor
        
    _mock_database.execute.side_effect = execute_side_effect
    
    # 1. Exploit attempt 1: Agent cites vibration alert ID, but declares coolant_pressure fault_type
    res_exploit_enum = create_work_order(
        machine_id="M001",
        action="Flush coolant loop and replace valve",
        urgency="Critical",
        justification="Coolant line pressure dropped below operating minimum",
        fault_type="coolant_pressure",
        grounding_alert_id="alert-vib-001",
    )
    assert "error" in res_exploit_enum
    assert "Grounding check failed" in res_exploit_enum["error"]
    assert "Declared fault_type 'coolant_pressure' does not match grounding alert fault_type 'vibration_high'" in res_exploit_enum["error"]

    # 2. Exploit attempt 2: Agent attempts to game enum check by setting fault_type='vibration_high',
    # but action remains an unrelated coolant repair (plausibility filter catches this)
    res_exploit_action = create_work_order(
        machine_id="M001",
        action="Flush coolant loop and replace valve",
        urgency="Critical",
        justification="Coolant line pressure dropped due to severe vibration-induced seal damage",
        fault_type="vibration_high",
        grounding_alert_id="alert-vib-001",
    )
    assert "error" in res_exploit_action
    assert "Plausibility check failed" in res_exploit_action["error"]
    assert "does not contain recognized corrective action vocabulary" in res_exploit_action["error"]
    
    # 3. Legitimate attempt: Action, fault_type, and alert ID all align on vibration_high
    res_valid = create_work_order(
        machine_id="M001",
        action="Balance spindle and replace drive bearing",
        urgency="Critical",
        justification="Severe vibration spike and accelerometer oscillation detected on spindle",
        fault_type="vibration_high",
        grounding_alert_id="alert-vib-001",
    )
    assert "error" not in res_valid
    assert res_valid["status"] == "Pending Approval"
    assert res_valid["created_by"] == "agent:atlas"


@pytest.mark.parametrize("fault_type,action,message,alert_id", [
    ("vibration_high", "Inspect and balance spindle rotor", "Spindle vibration spike", "alt-1"),
    ("temp_high", "Clean radiator and replace cooling fan", "Thermal overload detected", "alt-2"),
    ("current_overload", "Megger test motor windings and inspect drive", "Amperage surge detected", "alt-3"),
    ("bearing_wear", "Replace spindle bearing and pack grease", "High acoustic bearing wear", "alt-4"),
    ("coolant_pressure", "Flush coolant loop and replace valve", "Coolant line pressure drop", "alt-5"),
])
def test_all_fault_types_accept_legitimate_actions_and_alerts(_mock_database, fault_type, action, message, alert_id):
    """
    False-positive prevention test:
    Proves that for every fault_type in the taxonomy, a legitimate, correctly-phrased maintenance
    action backed by a valid alert passes validation cleanly and lands in 'Pending Approval'.
    """
    from server.agent_tools import create_work_order
    
    def execute_side_effect(query, params):
        mock_cursor = MagicMock()
        if "COUNT" in query:
            mock_cursor.fetchone.return_value = [0]
        elif "FROM alerts" in query and "ai_pipeline" in query:
            mock_cursor.fetchall.return_value = [
                ("Critical", fault_type, message, alert_id)
            ]
        else:
            mock_cursor.fetchone.return_value = None
            mock_cursor.fetchall.return_value = []
        return mock_cursor
        
    _mock_database.execute.side_effect = execute_side_effect

    res = create_work_order(
        machine_id="M001",
        action=action,
        urgency="Critical",
        justification=f"Telemetry confirmed {message}",
        fault_type=fault_type,
        grounding_alert_id=alert_id,
    )

    assert "error" not in res, f"Legitimate action for {fault_type} was falsely rejected: {res.get('error')}"
    assert res["status"] == "Pending Approval"
    assert res["fault_type"] == fault_type
    assert res["grounding_alert_id"] == alert_id
    assert res["created_by"] == "agent:atlas"

