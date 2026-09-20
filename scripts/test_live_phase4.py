import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

import json
import datetime
from server.database import pool
from server.agent_tools import create_work_order
from server.auth import create_access_token
import urllib.request
import urllib.error

def run_live_phase4_test():
    print("=== LIVE PHASE 4 VERIFICATION ===")

    # 1. Inspect alerts schema & insert a real ai_pipeline alert
    now = datetime.datetime.now(datetime.timezone.utc)
    with pool.connection() as conn:
        cols = conn.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'alerts'").fetchall()
        print("Alerts columns:", cols)

        # Insert alert letting ID auto-generate if serial/integer, or returning id
        row = conn.execute(
            """INSERT INTO alerts (machine_id, type, severity, message, fault_type, time, source)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            ('M001', 'CRITICAL_FAULT', 'Critical', 'Spindle vibration exceeds 4.5 mm/s', 'vibration_high', now, 'ai_pipeline')
        ).fetchone()
        conn.commit()
        alert_id = str(row[0])
        print(f"Seeded real ai_pipeline alert ID: {alert_id} (fault_type='vibration_high', severity='Critical')")

    # 2. Test DEF-012a: Taxonomy Enum Exact-Match Gate
    # Attempt: declare fault_type='coolant_pressure' against vibration alert
    print("\n--- Testing DEF-012a: Taxonomy Enum Exact-Match Gate ---")
    res_enum = create_work_order(
        machine_id='M001',
        action='Flush coolant loop and replace valve',
        urgency='Critical',
        fault_type='coolant_pressure',
        grounding_alert_id=alert_id
    )
    print("Result:", res_enum)
    assert "error" in res_enum, "DEF-012a FAILED: expected rejection!"
    assert "Declared fault_type 'coolant_pressure' does not match grounding alert fault_type 'vibration_high'" in res_enum["error"]
    print("PASS: DEF-012a deterministically rejected mismatched enum!")

    # 3. Test DEF-012b: Action Plausibility Allow-List Gate
    # Attempt: declare fault_type='vibration_high' to pass enum check, but action is unrelated coolant repair
    print("\n--- Testing DEF-012b: Action Plausibility Allow-List Gate ---")
    res_action = create_work_order(
        machine_id='M001',
        action='Flush coolant loop and replace valve',
        urgency='Critical',
        fault_type='vibration_high',
        grounding_alert_id=alert_id
    )
    print("Result:", res_action)
    assert "error" in res_action, "DEF-012b FAILED: expected plausibility rejection!"
    assert "does not contain recognized corrective action vocabulary for fault_type 'vibration_high'" in res_action["error"]
    print("PASS: DEF-012b deterministically rejected implausible action text!")

    # 4. Test Legitimate Work Order Creation
    print("\n--- Testing Legitimate Work Order Creation ---")
    res_valid = create_work_order(
        machine_id='M001',
        action='Inspect and balance spindle rotor',
        urgency='Critical',
        fault_type='vibration_high',
        grounding_alert_id=alert_id
    )
    print("Result:", res_valid)
    assert "error" not in res_valid, f"Legitimate order creation failed: {res_valid.get('error')}"
    assert res_valid["status"] == "Pending Approval"
    assert res_valid["created_by"] == "agent:atlas"
    order_id = res_valid["order_id"]
    print(f"PASS: Legitimate order created: {order_id} with status 'Pending Approval' and created_by='agent:atlas'!")

    # 5. Test Human Confirmation Gate via live HTTP REST API
    print("\n--- Testing Human Confirmation Gate (RBAC Dual-Direction) ---")
    viewer_jwt = create_access_token(data={"sub": "demo_viewer", "role": "viewer"})
    operator_jwt = create_access_token(data={"sub": "operator", "role": "operator"})

    # 5a. Viewer Attempt (Expect 403 Forbidden)
    req_viewer = urllib.request.Request(
        f"http://localhost:8000/api/work-orders/{order_id}/approve",
        method="POST",
        headers={
            "X-API-Request": "true",
            "Cookie": f"access_token={viewer_jwt}"
        }
    )
    try:
        urllib.request.urlopen(req_viewer)
        raise AssertionError("SECURITY BREACH: Viewer was unexpectedly allowed to approve work order!")
    except urllib.error.HTTPError as e:
        print(f"Viewer attempt: HTTP {e.code} ({e.reason}) -> PASS: Unauthorized role physically blocked!")
        assert e.code == 403

    # 5b. Operator Attempt (Expect 200 OK)
    req_operator = urllib.request.Request(
        f"http://localhost:8000/api/work-orders/{order_id}/approve",
        method="POST",
        headers={
            "X-API-Request": "true",
            "Cookie": f"access_token={operator_jwt}"
        }
    )
    resp_op = urllib.request.urlopen(req_operator)
    assert resp_op.status == 200
    res_op_data = json.loads(resp_op.read())
    print(f"Operator attempt: HTTP {resp_op.status} -> {res_op_data} -> PASS: Authorized operator approved order!")

    # 6. Verify final database state
    with pool.connection() as conn:
        status_row = conn.execute("SELECT status, created_by FROM work_orders WHERE order_id = %s", (order_id,)).fetchone()
        print(f"Database verification: order {order_id} status='{status_row[0]}', created_by='{status_row[1]}'")
        assert status_row[0] == "Open", "Expected status to transition to 'Open'!"
        assert status_row[1] == "agent:atlas", "Expected created_by to be 'agent:atlas'!"

    print("\nALL PHASE 4 GATES VALIDATED CLEANLY AGAINST LIVE SERVER AND TIMESCALEDB!")

if __name__ == "__main__":
    run_live_phase4_test()
