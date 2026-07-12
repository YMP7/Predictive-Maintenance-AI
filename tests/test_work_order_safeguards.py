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
    """Fabricated justification with no matching real alert is rejected."""
    from server.agent_tools import create_work_order
    
    _mock_database.execute.return_value.fetchone.return_value = [0]  # count=0
    _mock_database.execute.return_value.fetchall.return_value = []  # no alerts
    
    res = create_work_order("M001", "Fix bearing", "Critical", justification="Fabricated claim")
    
    assert "error" in res
    assert "Rejected: No supporting Critical alert found" in res["error"]

def test_critical_work_order_requires_approval(_mock_database):
    """A Critical-urgency order lands as Pending Approval, not Open, until the approve endpoint is called."""
    from server.agent_tools import create_work_order
    
    def execute_side_effect(query, params):
        mock_cursor = MagicMock()
        if "COUNT" in query:
            mock_cursor.fetchone.return_value = [0]
        elif "SELECT severity FROM alerts" in query:
            mock_cursor.fetchall.return_value = [("Critical",)]
        else:
            mock_cursor.fetchone.return_value = None
            mock_cursor.fetchall.return_value = []
        return mock_cursor
        
    _mock_database.execute.side_effect = execute_side_effect
    
    res = create_work_order("M001", "Fix bearing", "Critical", justification="High temp alert")
    
    assert "error" not in res
    assert res["status"] == "Pending Approval"
    
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
