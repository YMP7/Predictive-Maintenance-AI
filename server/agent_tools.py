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

def create_work_order(
    machine_id: str, action: str, urgency: str = "Medium", notes: str = "", justification: str = ""
) -> Dict[str, Any]:
    """Autonomously create a maintenance work order for a machine."""
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
                    "SELECT severity FROM alerts WHERE machine_id = %s AND time >= NOW() - INTERVAL '1 day' AND source = 'ai_pipeline'",
                    (machine_id,)
                ).fetchall()
                
                has_critical = any(r[0] == "Critical" for r in alert_rows)
                has_high = any(r[0] == "High" for r in alert_rows)
                
                valid = True
                if urgency == "Critical" and not has_critical:
                    valid = False
                elif urgency == "High" and not (has_critical or has_high):
                    valid = False
                    
                if not valid:
                    rejection_msg = f"Rejected: No supporting {urgency} alert found for {machine_id} in the last 24h."
                    snapshot = json.dumps({"recent_alerts": [r[0] for r in alert_rows]})
                    conn.execute(
                        "INSERT INTO work_order_audit_log (id, timestamp, machine_id, action, urgency, justification, validation_result, real_data_snapshot) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (str(uuid.uuid4()), now, machine_id, action, urgency, justification, "Rejected: Grounding Failed", snapshot)
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
