import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

import json
import datetime
import urllib.request
import urllib.error
import subprocess
from server.database import pool
from server.agent_tools import create_work_order
from server.auth import create_access_token

def step_header(phase, name):
    print(f"\n{'='*70}\n[{phase}] {name}\n{'='*70}")

def run_full_live_e2e():
    results = {}

    # -----------------------------------------------------------------------
    # Phase 0: Pre-Flight & Infrastructure
    # -----------------------------------------------------------------------
    step_header("PHASE 0", "Infrastructure & Database Health")
    with pool.connection() as conn:
        exts = [r[0] for r in conn.execute("SELECT extname FROM pg_extension").fetchall()]
        print(f"TimescaleDB Extensions: {exts}")
        assert "timescaledb" in exts and "vector" in exts, "Missing required PG extensions!"

    docker_ps = subprocess.run(["docker", "ps", "--format", "{{.Names}} ({{.Status}}): {{.Ports}}"], capture_output=True, text=True).stdout
    print(f"Docker Containers:\n{docker_ps.strip()}")
    assert "timescaledb" in docker_ps and "mosquitto" in docker_ps, "Docker containers not running!"
    results["Phase 0"] = "PASS"

    # -----------------------------------------------------------------------
    # Phase 1: Unified Server Boot & Routing
    # -----------------------------------------------------------------------
    step_header("PHASE 1", "Unified Server Boot & API Routing")
    resp = urllib.request.urlopen("http://localhost:8000/health")
    health_data = json.loads(resp.read())
    print(f"GET /health -> HTTP {resp.status}: {json.dumps(health_data)}")
    assert resp.status == 200 and health_data.get("status") == "healthy"

    resp = urllib.request.urlopen("http://localhost:8000/api/status")
    status_data = json.loads(resp.read())
    print(f"GET /api/status -> HTTP {resp.status}: {json.dumps(status_data)}")
    assert resp.status == 200 and status_data.get("status") == "running"

    resp = urllib.request.urlopen("http://localhost:8000/api/atlas/domains")
    domains_data = json.loads(resp.read())
    print(f"GET /api/atlas/domains -> HTTP {resp.status}: {len(domains_data.get('domains', []))} domains registered")
    registered_domain_ids = [d["domain_id"] for d in domains_data.get("domains", [])]
    print(f"Registered Domain IDs: {registered_domain_ids}")
    assert set(registered_domain_ids) == {"cmapss", "laptop", "mobile", "server"}
    results["Phase 1"] = "PASS"

    # -----------------------------------------------------------------------
    # Phase 2: Telemetry Ingestion (Phase A Fleet & Phase B 4 Domains)
    # -----------------------------------------------------------------------
    step_header("PHASE 2", "Telemetry Ingestion (Phase A Fleet & Phase B ATLAS Domains)")
    # 2A: Phase A IoT Fleet
    resp = urllib.request.urlopen("http://localhost:8000/api/dashboard/summary")
    summary = json.loads(resp.read())
    machines = [m["machine_id"] for m in summary.get("machines", [])]
    print(f"Phase A Fleet Machines ({summary.get('total_machines')} units): {machines}")
    assert set(machines) == {"M001", "M002", "M003", "M004"}

    resp = urllib.request.urlopen("http://localhost:8000/api/machines/M001/telemetry?limit=2")
    m001_telemetry = json.loads(resp.read())
    print(f"M001 Live Telemetry Samples (Latest 2):\n{json.dumps(m001_telemetry, indent=2)}")
    assert len(m001_telemetry) >= 1

    # 2B: Phase B ATLAS 4 Domains
    for d in domains_data.get("domains", []):
        print(f"ATLAS Domain: {d['domain_id']:<8} | status: {d.get('status', 'unknown'):<12} | connected: {d.get('connected')}")
    results["Phase 2"] = "PASS"

    # -----------------------------------------------------------------------
    # Phase 3: Machine Cognition, Anomaly Detection & Explainability
    # -----------------------------------------------------------------------
    step_header("PHASE 3", "Machine Cognition, RUL & Explainability")
    # Test Laptop domain
    laptop_req = json.dumps({
        "domain": "laptop",
        "machine_id": "laptop_local",
        "cycle": 100,
        "window": [[0.75, 0.40, 0.50, 1.0, 0.60]] * 30,
        "k": 3
    }).encode()

    req = urllib.request.Request("http://localhost:8000/api/context", data=laptop_req, headers={"Content-Type": "application/json"})
    laptop_ctx = json.loads(urllib.request.urlopen(req).read())
    print(f"Laptop Context -> RUL: {laptop_ctx.get('predicted_rul'):.4f} | Neighbors: {len(laptop_ctx.get('neighbors', []))}")
    assert laptop_ctx.get("predicted_rul") is not None and laptop_ctx.get("predicted_rul") >= 0.0

    req = urllib.request.Request("http://localhost:8000/api/decide", data=laptop_req, headers={"Content-Type": "application/json"})
    laptop_decide = json.loads(urllib.request.urlopen(req).read())
    print(f"Laptop Decision -> Action: {laptop_decide.get('recommended_action')}")

    # Test Mobile domain (5 canonical features extracted from 16 channels)
    mobile_req = json.dumps({
        "domain": "mobile",
        "machine_id": "mobile_device_1",
        "cycle": 50,
        "window": [[0.80, 0.35, 0.25, 0.30, 0.55]] * 30,
        "k": 3
    }).encode()

    req = urllib.request.Request("http://localhost:8000/api/context", data=mobile_req, headers={"Content-Type": "application/json"})
    mobile_ctx = json.loads(urllib.request.urlopen(req).read())
    print(f"Mobile Context -> RUL: {mobile_ctx.get('predicted_rul'):.4f} | Neighbors: {len(mobile_ctx.get('neighbors', []))}")
    assert mobile_ctx.get("predicted_rul") is not None and mobile_ctx.get("predicted_rul") >= 0.0

    req = urllib.request.Request("http://localhost:8000/api/decide", data=mobile_req, headers={"Content-Type": "application/json"})
    mobile_decide = json.loads(urllib.request.urlopen(req).read())
    print(f"Mobile Decision -> Action: {mobile_decide.get('recommended_action')}")
    results["Phase 3"] = "PASS"

    # -----------------------------------------------------------------------
    # Phase 4: Agent Safeguards, DEF-012a/b Gates & Human Approval
    # -----------------------------------------------------------------------
    step_header("PHASE 4", "Agent Safeguards & Security Gates (DEF-012a, DEF-012b, RBAC)")
    now = datetime.datetime.now(datetime.timezone.utc)
    with pool.connection() as conn:
        conn.execute("DELETE FROM work_orders WHERE machine_id = 'M001'")
        row = conn.execute(
            """INSERT INTO alerts (machine_id, type, severity, message, fault_type, time, source)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            ("M001", "CRITICAL_FAULT", "Critical", "Vibration spike 4.8 mm/s on spindle", "vibration_high", now, "ai_pipeline")
        ).fetchone()
        conn.commit()
        alert_id = str(row[0])
    print(f"Seeded verified pipeline alert ID: {alert_id} (fault_type='vibration_high')")

    # 4A. DEF-012a Rejection (Taxonomy Enum Mismatch)
    res_enum = create_work_order("M001", "Flush coolant loop and replace valve", "Critical", fault_type="coolant_pressure", grounding_alert_id=alert_id)
    print(f"DEF-012a Exploit Rejection Response:\n{json.dumps(res_enum, indent=2)}")
    assert "error" in res_enum and "Declared fault_type 'coolant_pressure' does not match" in res_enum["error"]
    print("PASS: DEF-012a exact-match gate blocked enum mismatch.")

    # 4B. DEF-012b Rejection (Action Plausibility Allow-List Mismatch)
    res_action = create_work_order("M001", "Flush coolant loop and replace valve", "Critical", fault_type="vibration_high", grounding_alert_id=alert_id)
    print(f"DEF-012b Exploit Rejection Response:\n{json.dumps(res_action, indent=2)}")
    assert "error" in res_action and "does not contain recognized corrective action vocabulary" in res_action["error"]
    print("PASS: DEF-012b plausibility gate blocked unrelated action text.")

    # 4C. Legitimate Grounded Order Creation
    res_valid = create_work_order("M001", "Inspect and balance spindle rotor", "Critical", fault_type="vibration_high", grounding_alert_id=alert_id)
    print(f"Legitimate Work Order Response:\n{json.dumps(res_valid, indent=2)}")
    assert "order_id" in res_valid and res_valid["status"] == "Pending Approval"
    assert res_valid["created_by"] == "agent:atlas"
    order_id = res_valid["order_id"]
    print(f"PASS: Work order {order_id} created in 'Pending Approval' with created_by='agent:atlas'.")

    # 4D. Human Confirmation Gate (RBAC Dual-Direction)
    viewer_jwt = create_access_token(data={"sub": "demo_viewer", "role": "viewer"})
    operator_jwt = create_access_token(data={"sub": "operator", "role": "operator"})

    # Viewer attempt (Expect 403)
    req_v = urllib.request.Request(
        f"http://localhost:8000/api/work-orders/{order_id}/approve",
        method="POST",
        headers={"X-API-Request": "true", "Cookie": f"access_token={viewer_jwt}"}
    )
    try:
        urllib.request.urlopen(req_v)
        raise AssertionError("SECURITY VIOLATION: Viewer role approved work order!")
    except urllib.error.HTTPError as e:
        print(f"Viewer Approval Attempt: HTTP {e.code} ({e.reason}) -> PASS: Viewer blocked.")
        assert e.code == 403

    # Operator attempt (Expect 200)
    req_op = urllib.request.Request(
        f"http://localhost:8000/api/work-orders/{order_id}/approve",
        method="POST",
        headers={"X-API-Request": "true", "Cookie": f"access_token={operator_jwt}"}
    )
    resp_op = urllib.request.urlopen(req_op)
    op_result = json.loads(resp_op.read())
    print(f"Operator Approval Attempt: HTTP {resp_op.status} -> {json.dumps(op_result)} -> PASS: Operator approved.")
    assert resp_op.status == 200 and op_result.get("status") == "approved"

    # Verify DB transition
    with pool.connection() as conn:
        row = conn.execute("SELECT status, created_by FROM work_orders WHERE order_id = %s", (order_id,)).fetchone()
        print(f"Final DB Record: order_id={order_id}, status='{row[0]}', created_by='{row[1]}'")
        assert row[0] == "Open" and row[1] == "agent:atlas"
    results["Phase 4"] = "PASS"

    # -----------------------------------------------------------------------
    # Phase 5: Unified Frontend UI Build Verification
    # -----------------------------------------------------------------------
    step_header("PHASE 5", "Unified Frontend UI Availability")
    resp_spa = urllib.request.urlopen("http://localhost:8000/")
    spa_content = resp_spa.read().decode("utf-8")
    print(f"GET http://localhost:8000/ -> HTTP {resp_spa.status} (Length: {len(spa_content)} bytes)")
    assert resp_spa.status == 200 and "<div id=\"root\">" in spa_content
    assert "assets/index-" in spa_content
    print("PASS: Production React SPA successfully served from FastAPI root!")
    results["Phase 5"] = "PASS"

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"\n{'='*70}\nE2E LIVE VALIDATION EXECUTION SUMMARY\n{'='*70}")
    for phase, status in results.items():
        print(f"  {phase:<12} : {status}")
    print("ALL PHASES PASSED 100% CLEANLY LIVE!\n")

if __name__ == "__main__":
    run_full_live_e2e()
