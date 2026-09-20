"""
server/agent_tools.py

Tool registry for the Phase 8 Agentic AI.

Each function here is a "tool" the LLM agent can autonomously call.
The tool_registry dict maps tool names to callables for the agent loop.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
import json
from typing import Any, Dict, List, Optional
import uuid

from server.database import pool

logger = logging.getLogger("DigitalTwin.AgentTools")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Tool: query_telemetry
# ---------------------------------------------------------------------------

def query_telemetry(machine_id: str, hours: float = 1.0) -> Dict[str, Any]:
    """Retrieve recent telemetry readings for a machine from TimescaleDB."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max(0.1, min(hours, 168)))
        with pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT time, vibration_rms, temperature, current_val
                FROM telemetry
                WHERE machine_id = %s AND time >= %s
                ORDER BY time DESC
                LIMIT 100
                """,
                (machine_id, cutoff)
            ).fetchall()
        readings = [
            {
                "timestamp": row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
                "vibration_rms": float(row[1]) if row[1] is not None else None,
                "temperature": float(row[2]) if row[2] is not None else None,
                "current": float(row[3]) if row[3] is not None else None,
            }
            for row in rows
        ]
        return {"machine_id": machine_id, "count": len(readings), "readings": readings}
    except Exception as e:
        logger.error(f"query_telemetry error: {e}")
        return {"machine_id": machine_id, "count": 0, "readings": [], "error": str(e)}


# ---------------------------------------------------------------------------
# Tool: get_recent_alerts
# ---------------------------------------------------------------------------

def get_recent_alerts(machine_id: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """Retrieve recent system alerts, optionally filtered by machine."""
    try:
        with pool.connection() as conn:
            if machine_id:
                rows = conn.execute(
                    """
                    SELECT id, machine_id, type, severity, message, fault_type, time
                    FROM alerts WHERE machine_id = %s ORDER BY time DESC LIMIT %s
                    """,
                    (machine_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, machine_id, type, severity, message, fault_type, time
                    FROM alerts ORDER BY time DESC LIMIT %s
                    """,
                    (limit,)
                ).fetchall()
        alerts = [
            {
                "alert_id": str(row[0]),
                "machine_id": row[1],
                "alert_type": row[2],
                "severity": row[3],
                "message": row[4],
                "fault_type": row[5],
                "timestamp": row[6].isoformat() if hasattr(row[6], "isoformat") else str(row[6]),
            }
            for row in rows
        ]
        return {"count": len(alerts), "alerts": alerts}
    except Exception as e:
        logger.error(f"get_recent_alerts error: {e}")
        return {"count": 0, "alerts": [], "error": str(e)}


# ---------------------------------------------------------------------------
# Tool: get_maintenance_history
# ---------------------------------------------------------------------------

def get_maintenance_history(machine_id: str) -> Dict[str, Any]:
    """Retrieve the maintenance work order history for a machine."""
    try:
        with pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT order_id, machine_id, action, urgency, status, created_at, resolved_at, notes
                FROM work_orders WHERE machine_id = %s ORDER BY created_at DESC LIMIT 20
                """,
                (machine_id,)
            ).fetchall()
        orders = [
            {
                "order_id": str(row[0]),
                "machine_id": row[1],
                "action": row[2],
                "urgency": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
                "resolved_at": row[6].isoformat() if row[6] and hasattr(row[6], "isoformat") else None,
                "notes": row[7],
            }
            for row in rows
        ]
        return {"machine_id": machine_id, "count": len(orders), "work_orders": orders}
    except Exception as e:
        logger.error(f"get_maintenance_history error: {e}")
        return {"machine_id": machine_id, "count": 0, "work_orders": [], "error": str(e)}


# ---------------------------------------------------------------------------
# Tool: create_work_order
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Fault Type Correlation Matrix for Telemetry Grounding
# ---------------------------------------------------------------------------

FAULT_TYPE_CORRELATION_MAP: Dict[str, Set[str]] = {
    "vibration_high": {
        "vibration", "vibrating", "vibrate", "bearing", "imbalance",
        "alignment", "misalignment", "looseness", "mechanical", "oscillation",
        "accel", "accelerometer", "rms", "shaking", "chatter", "spindle"
    },
    "temp_high": {
        "temp", "temperature", "thermal", "overheat", "overheating",
        "heat", "hot", "thermistor", "cooling", "fan", "heatsink"
    },
    "current_overload": {
        "current", "overload", "electrical", "power", "amperage",
        "amp", "amps", "voltage", "surge", "short", "winding", "motor_current"
    },
    "bearing_wear": {
        "bearing", "wear", "lubrication", "friction", "spindle",
        "races", "balls", "grease", "vibration", "looseness"
    },
    "coolant_pressure": {
        "coolant", "pressure", "fluid", "hydraulic", "leak",
        "pump", "psi", "flow", "filter", "radiator", "line"
    },
}


def _alert_correlates_with_work_order(alert_fault_type: Optional[str], alert_msg: str, text: str) -> bool:
    """
    Verifies that the work order description semantically correlates with the triggering alert's
    fault_type or diagnostic message. Prevents using an unrelated real alert to ground arbitrary actions.

    KNOWN LIMITATION:
    Grounding currently validates topical correlation via keyword/token matching.
    This defends against accidental or naive hallucinations, but does NOT defend
    against an adversarially-worded justification engineered to match keywords
    for an unrelated fault (e.g. citing 'vibration-induced coolant seal leak' to
    justify an unrelated coolant repair against a vibration alert).
    Structured `grounding_alert_id` enforcement with server-side taxonomy matching
    is the stronger primary fix, tracked as a follow-up hardening task.
    """
    if not alert_fault_type and not alert_msg:
        return True

    text_lower = text.lower()

    if alert_fault_type:
        ft = alert_fault_type.lower()
        if ft in text_lower:
            return True
        keywords = FAULT_TYPE_CORRELATION_MAP.get(ft, set())
        if any(kw in text_lower for kw in keywords):
            return True

    if alert_msg:
        msg_words = [w for w in alert_msg.lower().replace(",", " ").replace(".", " ").split() if len(w) > 3]
        if any(w in text_lower for w in msg_words):
            return True

    return False


def create_work_order(
    machine_id: str,
    action: str,
    urgency: str = "Medium",
    notes: str = "",
    justification: str = "",
    grounding_alert_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Autonomously create a maintenance work order for a machine with strict telemetry grounding.

    NOTE ON GROUNDING ENFORCEMENT:
    `grounding_alert_id` is currently advisory/optional. If provided, the check strictly binds
    validation to that specific pipeline alert ID. If omitted, the check falls back to scanning
    all verified High/Critical pipeline alerts for the machine in the last 24 hours and evaluates
    topical keyword correlation against the fault_type taxonomy.
    """
    valid_urgency = {"Low", "Medium", "High", "Critical"}
    if urgency not in valid_urgency:
        urgency = "Medium"
    try:
        now = datetime.now(timezone.utc)
        with pool.connection() as conn:
            # 1. Volume Cap
            count = conn.execute(
                "SELECT COUNT(*) FROM work_orders WHERE machine_id = %s AND created_at >= NOW() - INTERVAL '1 day'",
                (machine_id,)
            ).fetchone()[0]
            if count >= 3:
                conn.execute(
                    "INSERT INTO work_order_audit_log (id, timestamp, machine_id, action, urgency, justification, validation_result) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (str(uuid.uuid4()), now, machine_id, action, urgency, justification, "Rejected: Volume Cap Exceeded")
                )
                conn.commit()
                return {"error": "Rejected: Maximum of 3 work orders per day per machine exceeded."}
                
            # 2. Telemetry Grounding Validation (for High/Critical)
            if urgency in ("High", "Critical"):
                alert_rows = conn.execute(
                    "SELECT severity, fault_type, message, id FROM alerts WHERE machine_id = %s AND time >= NOW() - INTERVAL '1 day' AND source = 'ai_pipeline'",
                    (machine_id,)
                ).fetchall()

                parsed_alerts = []
                for r in alert_rows:
                    sev = r[0] if len(r) > 0 else ""
                    ftype = r[1] if len(r) > 1 else None
                    msg = r[2] if len(r) > 2 else ""
                    aid = str(r[3]) if len(r) > 3 else None
                    parsed_alerts.append({"severity": sev, "fault_type": ftype, "message": msg, "id": aid})

                # A. Check if explicit grounding_alert_id was supplied
                if grounding_alert_id:
                    matched = [a for a in parsed_alerts if a["id"] == str(grounding_alert_id)]
                    if not matched:
                        rejection_msg = f"Rejected: Grounding alert {grounding_alert_id} not found in recent verified pipeline alerts for {machine_id}."
                        conn.execute(
                            "INSERT INTO work_order_audit_log (id, timestamp, machine_id, action, urgency, justification, validation_result) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (str(uuid.uuid4()), now, machine_id, action, urgency, justification, "Rejected: Invalid Grounding Alert ID")
                        )
                        conn.commit()
                        return {"error": rejection_msg}
                    candidate_alerts = matched
                else:
                    # Filter candidate alerts by required severity
                    if urgency == "Critical":
                        candidate_alerts = [a for a in parsed_alerts if a["severity"] == "Critical"]
                    else:  # High
                        candidate_alerts = [a for a in parsed_alerts if a["severity"] in ("Critical", "High")]

                if not candidate_alerts:
                    rejection_msg = f"Rejected: No supporting {urgency} alert found for {machine_id} in the last 24h."
                    snapshot = json.dumps({"recent_alerts": [a["severity"] for a in parsed_alerts]})
                    conn.execute(
                        "INSERT INTO work_order_audit_log (id, timestamp, machine_id, action, urgency, justification, validation_result, real_data_snapshot) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (str(uuid.uuid4()), now, machine_id, action, urgency, justification, "Rejected: Grounding Failed (Severity)", snapshot)
                    )
                    conn.commit()
                    return {"error": rejection_msg}

                # B. Fault-Type Correlation Check: Action/justification must correlate with at least one matching alert
                wo_text = f"{action} {justification} {notes}"
                correlating_alerts = [
                    a for a in candidate_alerts
                    if _alert_correlates_with_work_order(a["fault_type"], a["message"], wo_text)
                ]

                if not correlating_alerts:
                    found_types = [a["fault_type"] for a in candidate_alerts if a["fault_type"]]
                    rejection_msg = (
                        f"Rejected: Grounding check failed. Work order fault description does not correlate with "
                        f"supporting {urgency} alert fault_type(s): {found_types or ['unspecified']}."
                    )
                    snapshot = json.dumps({
                        "action": action,
                        "justification": justification,
                        "candidate_alert_fault_types": found_types,
                    })
                    conn.execute(
                        "INSERT INTO work_order_audit_log (id, timestamp, machine_id, action, urgency, justification, validation_result, real_data_snapshot) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (str(uuid.uuid4()), now, machine_id, action, urgency, justification, "Rejected: Grounding Fault Type Mismatch", snapshot)
                    )
                    conn.commit()
                    return {"error": rejection_msg}
            
            # 3. Human Confirmation Gate
            status = "Pending Approval" if urgency in ("High", "Critical") else "Open"

            # Insert work order
            order_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO work_orders (order_id, machine_id, action, urgency, status, created_at, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (order_id, machine_id, action, urgency, status, now, notes)
            )
            
            # Insert audit log
            conn.execute(
                "INSERT INTO work_order_audit_log (id, timestamp, machine_id, action, urgency, justification, validation_result) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (str(uuid.uuid4()), now, machine_id, action, urgency, justification, f"Success: {status}")
            )
            conn.commit()

        logger.info(f"[AgentTool] Work order created: {order_id} for {machine_id} — {action} [{urgency}] (Status: {status})")
        return {
            "order_id": order_id, "machine_id": machine_id, "action": action,
            "urgency": urgency, "status": status,
            "created_at": now.isoformat().replace("+00:00", "Z"),
        }
    except Exception as e:
        logger.error(f"create_work_order error: {e}")
        return {"error": str(e)}



# ---------------------------------------------------------------------------
# Gemini Function Declaration Schemas
# ---------------------------------------------------------------------------

TOOL_DECLARATIONS = [
    {
        "name": "query_telemetry",
        "description": "Retrieve recent telemetry readings (vibration, temperature, current) from a machine's sensor history.",
        "parameters": {
            "type": "object",
            "properties": {
                "machine_id": {"type": "string", "description": "Machine identifier e.g. M001"},
                "hours": {"type": "number", "description": "How many hours back to query (max 168)"},
            },
            "required": ["machine_id"],
        },
    },
    {
        "name": "get_recent_alerts",
        "description": "Retrieve recent system alerts, optionally filtered to one machine.",
        "parameters": {
            "type": "object",
            "properties": {
                "machine_id": {"type": "string", "description": "Machine identifier, or omit for all machines"},
                "limit": {"type": "integer", "description": "Max alerts to return (default 20)"},
            },
        },
    },
    {
        "name": "get_maintenance_history",
        "description": "Retrieve the work order and maintenance history for a specific machine.",
        "parameters": {
            "type": "object",
            "properties": {
                "machine_id": {"type": "string", "description": "Machine identifier e.g. M001"},
            },
            "required": ["machine_id"],
        },
    },
    {
        "name": "create_work_order",
        "description": "Autonomously create a maintenance work order for a machine. Use this when maintenance action is required.",
        "parameters": {
            "type": "object",
            "properties": {
                "machine_id": {"type": "string", "description": "Machine that needs maintenance"},
                "action": {"type": "string", "description": "What maintenance action is needed"},
                "urgency": {
                    "type": "string",
                    "enum": ["Low", "Medium", "High", "Critical"],
                    "description": "Priority level",
                },
                "notes": {"type": "string", "description": "Additional context or diagnosis notes"},
                "justification": {"type": "string", "description": "Explicit justification citing specific real recent alerts or telemetry data supporting this action and urgency"},
                "grounding_alert_id": {"type": "string", "description": "Optional alert ID from get_recent_alerts that grounds this work order"},
            },
            "required": ["machine_id", "action", "justification"],
        },

    },
]

# ---------------------------------------------------------------------------
# Tool dispatch map
# ---------------------------------------------------------------------------

TOOL_REGISTRY: Dict[str, Any] = {
    "query_telemetry": query_telemetry,
    "get_recent_alerts": get_recent_alerts,
    "get_maintenance_history": get_maintenance_history,
    "create_work_order": create_work_order,
}
