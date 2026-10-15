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

FAULT_TYPE_ALLOWED_ACTIONS: Dict[str, Set[str]] = {
    "vibration_high": {
        "vibration", "vibrating", "vibrate", "bearing", "imbalance",
        "alignment", "misalignment", "align", "looseness", "mechanical", "oscillation",
        "accel", "accelerometer", "rms", "shaking", "chatter", "spindle", "balance",
        "rebalance", "mount", "mounting", "rotor", "shaft", "coupling", "tighten", "inspect", "inspection"
    },
    "temp_high": {
        "temp", "temperature", "thermal", "overheat", "overheating",
        "heat", "hot", "thermistor", "cooling", "fan", "heatsink", "coolant", "radiator",
        "lubrication", "lube", "oil", "grease", "inspect", "inspection", "clean", "cleaning"
    },
    "current_overload": {
        "current", "overload", "electrical", "power", "amperage",
        "amp", "amps", "voltage", "surge", "short", "winding", "motor_current", "motor",
        "inverter", "drive", "breaker", "contactor", "megger", "insulation", "inspect", "inspection", "reset"
    },
    "bearing_wear": {
        "bearing", "wear", "lubrication", "lubricate", "friction", "spindle",
        "races", "balls", "grease", "vibration", "looseness", "acoustic", "runout", "pack",
        "cage", "roller", "replace", "replacement", "inspect", "inspection"
    },
    "coolant_pressure": {
        "coolant", "pressure", "fluid", "hydraulic", "leak", "pump", "psi", "flow", "filter",
        "radiator", "line", "valve", "flush", "impeller", "reservoir", "pipe", "seal", "transducer",
        "nozzle", "inspect", "inspection", "clean", "cleaning"
    },
}


def _reject(conn, now, machine_id, action, urgency, justification, result, message, snapshot=None) -> Dict[str, Any]:
    """Record a refused agent work order in the audit log and return the refusal for the LLM."""
    conn.execute(
        "INSERT INTO work_order_audit_log (id, timestamp, machine_id, action, urgency, justification, validation_result, real_data_snapshot) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (str(uuid.uuid4()), now, machine_id, action, urgency, justification, result,
         json.dumps(snapshot) if snapshot is not None else None)
    )
    conn.commit()
    return {"error": message}


def create_work_order(
    machine_id: str,
    action: str,
    urgency: str = "Medium",
    notes: str = "",
    justification: str = "",
    fault_type: Optional[str] = None,
    grounding_alert_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Autonomously create a maintenance work order for a machine with strict telemetry grounding.

    SECURITY SPECIFICATION (DEF-012a Closure):
    For High and Critical urgency work orders, the autonomous agent MUST provide both
    an explicit `grounding_alert_id` (referencing an active, verified ai_pipeline alert)
    and a matching structured `fault_type` enum. Free-text keyword correlation fallback
    is completely removed for agent work orders.
    Additionally, the requested action is validated against `FAULT_TYPE_ALLOWED_ACTIONS`
    to guarantee action plausibility for the declared fault type.

    Created_by provenance is strictly assigned server-side as 'agent:atlas'.
    """
    valid_urgency = {"Low", "Medium", "High", "Critical"}
    if urgency not in valid_urgency:
        urgency = "Medium"
    try:
        now = datetime.now(timezone.utc)
        with pool.connection() as conn:
            def reject(result: str, message: str, snapshot: Optional[Dict] = None) -> Dict[str, Any]:
                return _reject(conn, now, machine_id, action, urgency, justification, result, message, snapshot)

            # Serialize agent orders per machine until commit, so two concurrent chats can't both pass the cap.
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (machine_id,))

            # 1. Volume Cap (<= 3 per day per machine)
            count = conn.execute(
                "SELECT COUNT(*) FROM work_orders WHERE machine_id = %s AND created_at >= NOW() - INTERVAL '1 day'",
                (machine_id,)
            ).fetchone()[0]
            if count >= 3:
                return reject("Rejected: Volume Cap Exceeded",
                              "Rejected: Maximum of 3 work orders per day per machine exceeded.")

            # 2. Strict Telemetry Grounding Validation (Mandatory for High/Critical)
            if urgency in ("High", "Critical"):
                taxonomy = list(FAULT_TYPE_ALLOWED_ACTIONS.keys())
                # A. Mandatory Grounding Alert ID & Fault Type
                if not grounding_alert_id:
                    return reject("Rejected: Missing Grounding Alert ID",
                                  "Rejected: High and Critical urgency work orders require an explicit grounding_alert_id referencing a verified ai_pipeline alert.")
                if not fault_type:
                    return reject("Rejected: Missing Fault Type",
                                  f"Rejected: High and Critical urgency work orders require a structured fault_type declared from taxonomy: {taxonomy}.")
                norm_fault_type = fault_type.strip().lower()
                if norm_fault_type not in FAULT_TYPE_ALLOWED_ACTIONS:
                    return reject("Rejected: Unrecognized Fault Type",
                                  f"Rejected: Declared fault_type '{fault_type}' is not recognized in system taxonomy: {taxonomy}.")

                # B. Relational & Provenance Validation (Layer 1)
                alert_rows = conn.execute(
                    "SELECT severity, fault_type, message, id FROM alerts WHERE machine_id = %s AND time >= NOW() - INTERVAL '1 day' AND source = 'ai_pipeline'",
                    (machine_id,)
                ).fetchall()

                matching_alert = None
                for r in alert_rows:
                    aid = str(r[3]) if len(r) > 3 else ""
                    if aid == str(grounding_alert_id):
                        matching_alert = {
                            "severity": r[0] if len(r) > 0 else "",
                            "fault_type": (r[1] or "").lower() if len(r) > 1 else "",
                            "message": r[2] if len(r) > 2 else "",
                            "id": aid
                        }
                        break

                if not matching_alert:
                    return reject("Rejected: Invalid Grounding Alert ID",
                                  f"Rejected: Grounding alert {grounding_alert_id} not found in recent verified pipeline alerts for {machine_id}.")

                # C. Severity Floor Validation
                alert_sev = matching_alert["severity"]
                if urgency == "Critical" and alert_sev != "Critical":
                    return reject("Rejected: Insufficient Severity",
                                  f"Rejected: Grounding check failed. Urgency 'Critical' requires a 'Critical' alert, but alert {grounding_alert_id} has severity '{alert_sev}'.")
                elif urgency == "High" and alert_sev not in ("High", "Critical"):
                    return reject("Rejected: Insufficient Severity",
                                  f"Rejected: Grounding check failed. Urgency 'High' requires a 'High' or 'Critical' alert, but alert {grounding_alert_id} has severity '{alert_sev}'.")

                # D. Structured Fault-Type Exact Match (Layer 2)
                if norm_fault_type != matching_alert["fault_type"]:
                    return reject(
                        "Rejected: Fault Type Mismatch",
                        f"Rejected: Grounding check failed. Declared fault_type '{fault_type}' "
                        f"does not match grounding alert fault_type '{matching_alert['fault_type']}'.",
                        {
                            "action": action,
                            "declared_fault_type": fault_type,
                            "alert_fault_type": matching_alert["fault_type"],
                            "grounding_alert_id": grounding_alert_id,
                        },
                    )

                # E. Action Plausibility Allow-List Gate (Layer 3)
                allowed_tokens = FAULT_TYPE_ALLOWED_ACTIONS.get(norm_fault_type, set())
                action_lower = action.lower()
                if not any(token in action_lower for token in allowed_tokens):
                    return reject(
                        "Rejected: Action Plausibility Mismatch",
                        f"Rejected: Plausibility check failed. Work order action '{action}' "
                        f"does not contain recognized corrective action vocabulary for fault_type '{fault_type}'.",
                        {
                            "action": action,
                            "fault_type": fault_type,
                            "allowed_vocabulary_sample": list(allowed_tokens)[:6],
                        },
                    )

            # 3. Human Confirmation Gate
            # Every agent order needs a human release: urgency is LLM-chosen, so it can't gate approval
            status = "Pending Approval"

            # Insert work order with server-derived provenance (agent:atlas)
            order_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO work_orders (order_id, machine_id, action, urgency, status, created_at, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (order_id, machine_id, action, urgency, status, now, notes, "agent:atlas")
            )

            # Insert audit log
            conn.execute(
                "INSERT INTO work_order_audit_log (id, timestamp, machine_id, action, urgency, justification, validation_result) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (str(uuid.uuid4()), now, machine_id, action, urgency, justification, f"Success: {status}")
            )
            conn.commit()

        logger.info(f"[AgentTool] Work order created: {order_id} for {machine_id} — {action} [{urgency}] (Status: {status}, CreatedBy: agent:atlas)")
        return {
            "status": status,
            "order_id": order_id,
            "machine_id": machine_id,
            "action": action,
            "urgency": urgency,
            "fault_type": fault_type,
            "grounding_alert_id": grounding_alert_id,
            "created_by": "agent:atlas",
            "message": f"Work order {order_id} created successfully with status '{status}'."
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
        "description": "Autonomously create a maintenance work order for a machine. For High or Critical urgency, an explicit grounding_alert_id and matching fault_type are strictly required.",
        "parameters": {
            "type": "object",
            "properties": {
                "machine_id": {"type": "string", "description": "Machine that needs maintenance"},
                "action": {"type": "string", "description": "What maintenance action is needed (must correlate with the declared fault_type)"},
                "urgency": {
                    "type": "string",
                    "enum": ["Low", "Medium", "High", "Critical"],
                    "description": "Priority level",
                },
                "fault_type": {
                    "type": "string",
                    "enum": ["vibration_high", "temp_high", "current_overload", "bearing_wear", "coolant_pressure"],
                    "description": "Structured fault category from system taxonomy. Strictly required for High or Critical urgency.",
                },
                "grounding_alert_id": {
                    "type": "string",
                    "description": "UUID of verified ai_pipeline alert justifying this work order. Strictly required for High or Critical urgency.",
                },
                "notes": {"type": "string", "description": "Additional context or diagnosis notes"},
                "justification": {"type": "string", "description": "Explicit justification citing specific real recent alerts or telemetry data supporting this action and urgency"},
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
