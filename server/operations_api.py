"""
Operations endpoints added in redesign P4: ISA-18.2 alarm handling (acknowledge, shelve, unshelve, clear),
the work-order lifecycle beyond approve/resolve (create, reject, start, assign), and users and roles.

Every state change is audited with the actor and the reason. Alarms are the rows the cognition and
threshold pipelines write to `alerts`; this module never raises alarms itself.
"""

from __future__ import annotations

import logging
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from server import audit as A
from server.auth import User, get_current_user, require_admin, require_operator_or_admin
from server.database import pool

logger = logging.getLogger("DigitalTwin.operations")
router = APIRouter()

_ID = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"

# ---------------------------------------------------------------- alarms (ISA-18.2)

# action -> {current state: next state}. Return to normal is not detected automatically yet: an operator
# clears an acknowledged alarm with a reason (ADR-018).
_TRANSITIONS = {
    "ack": {"unack": "ack", "rtn_unack": "cleared"},
    "shelve": {"unack": "shelved", "ack": "shelved", "rtn_unack": "shelved"},
    "unshelve": {"shelved": "unack"},
    "clear": {"ack": "cleared"},
}

# A shelve that has run out hands the alarm back to the operator unacknowledged.
_EFFECTIVE_STATE = "CASE WHEN state = 'shelved' AND shelved_until <= NOW() THEN 'unack' ELSE state END"


def next_alarm_state(action: str, state: str) -> Optional[str]:
    return _TRANSITIONS[action].get(state)


class AlarmNote(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class AlarmReason(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class AlarmShelve(AlarmReason):
    # ISA-18.2 shelving is always time-limited: 5 minutes to 24 hours.
    minutes: int = Field(ge=5, le=1440)


def _alarm_row(r) -> dict:
    return {
        "id": r[0], "raised_at": r[1].isoformat(), "machine_id": r[2], "type": r[3],
        "priority": (r[4] or "medium").lower(), "message": r[5], "fault_type": r[6], "source": r[7],
        "state": r[8], "state_by": r[9], "state_at": r[10].isoformat() if r[10] else None,
        "state_reason": r[11], "shelved_until": r[12].isoformat() if r[12] else None,
    }


_ALARM_COLS = (f"id, time, machine_id, type, severity, message, fault_type, source, {_EFFECTIVE_STATE}, "
               "state_by, state_at, state_reason, shelved_until")


@router.get("/api/alarms", tags=["alarms"], summary="Alarms, newest first, with their ISA-18.2 state")
def list_alarms(machine_id: Optional[str] = Query(None, pattern=_ID), limit: int = Query(200, ge=1, le=1000),
                _: User = Depends(get_current_user)):
    where, params = ("WHERE machine_id = %s", [machine_id]) if machine_id else ("", [])
    try:
        with pool.connection() as conn:
            rows = conn.execute(f"SELECT {_ALARM_COLS} FROM alerts {where} ORDER BY time DESC LIMIT %s",
                                [*params, limit]).fetchall()
    except Exception as e:
        logger.error("alarm list failed: %s", e)
        raise HTTPException(status_code=503, detail="Alarm store unavailable")
    return {"count": len(rows), "alarms": [_alarm_row(r) for r in rows]}


def _transition(alarm_id: int, action: str, user: User, reason: Optional[str], minutes: Optional[int] = None) -> dict:
    allowed = list(_TRANSITIONS[action])
    with pool.connection() as conn:
        cur = conn.execute(f"SELECT {_EFFECTIVE_STATE}, machine_id FROM alerts WHERE id = %s", (alarm_id,)).fetchone()
        if cur is None:
            raise HTTPException(status_code=404, detail="Alarm not found")
        before = cur[0]
        new = next_alarm_state(action, before)
        if new is None:
            raise HTTPException(status_code=409, detail=f"Cannot {action} an alarm that is {before}")
        # The state is re-checked in the UPDATE, so two operators cannot both act on the same alarm.
        row = conn.execute(
            f"""UPDATE alerts SET state = %s, state_by = %s, state_at = NOW(), state_reason = %s,
                   shelved_until = CASE WHEN %s::int IS NULL THEN NULL ELSE NOW() + make_interval(mins => %s::int) END,
                   acknowledged = acknowledged OR %s
                WHERE id = %s AND {_EFFECTIVE_STATE} = ANY(%s) RETURNING {_ALARM_COLS}""",
            (new, user.username, reason, minutes, minutes, new in ("ack", "cleared"), alarm_id, allowed)).fetchone()
        if row is None:
            raise HTTPException(status_code=409, detail="The alarm changed meanwhile; reload and try again")
        conn.commit()
    details = {"from": before, "to": new, "reason": reason}
    if minutes:
        details["minutes"] = minutes
    A.audit(category="alarm", action=action, actor=user.username, actor_type="user", role=user.role,
            target=str(alarm_id), details={"machine_id": cur[1], **details})
    return _alarm_row(row)


@router.post("/api/alarms/{alarm_id}/ack", tags=["alarms"], summary="Acknowledge an alarm")
def ack_alarm(alarm_id: int, body: AlarmNote, user: User = Depends(require_operator_or_admin)):
    return _transition(alarm_id, "ack", user, body.reason)


@router.post("/api/alarms/{alarm_id}/shelve", tags=["alarms"], summary="Shelve an alarm for a limited time, with a reason")
def shelve_alarm(alarm_id: int, body: AlarmShelve, user: User = Depends(require_operator_or_admin)):
    return _transition(alarm_id, "shelve", user, body.reason, body.minutes)


@router.post("/api/alarms/{alarm_id}/unshelve", tags=["alarms"], summary="Return a shelved alarm to the operator")
def unshelve_alarm(alarm_id: int, body: AlarmNote, user: User = Depends(require_operator_or_admin)):
    return _transition(alarm_id, "unshelve", user, body.reason)


@router.post("/api/alarms/{alarm_id}/clear", tags=["alarms"], summary="Clear an acknowledged alarm, with a reason")
def clear_alarm(alarm_id: int, body: AlarmReason, user: User = Depends(require_operator_or_admin)):
    return _transition(alarm_id, "clear", user, body.reason)


# ---------------------------------------------------------------- work orders
# Approve and resolve stay in backend_api (existing clients); this adds the rest of the lifecycle:
# Pending Approval -> Open (approve) | Rejected (reject); Open -> In Progress (start); Open | In Progress -> Resolved.

_WO_ROW = "order_id, machine_id, action, urgency"


def audit_work_order(conn, row, username: str, result: str, details: Optional[dict] = None) -> None:
    """Record a human status change in work_order_audit_log and the audit trail."""
    conn.execute(
        "INSERT INTO work_order_audit_log (id, timestamp, machine_id, action, urgency, justification, validation_result) "
        "VALUES (%s, NOW(), %s, %s, %s, %s, %s)",
        (str(uuid.uuid4()), row[1], row[2], row[3], f"order {row[0]} by {username}", result),
    )
    A.audit(category="work_order", action=result.replace("HUMAN_", "").lower(), actor=username, actor_type="user",
            target=str(row[0]), details={"machine_id": row[1], "action": row[2], "urgency": row[3], **(details or {})})


class NewWorkOrder(BaseModel):
    machine_id: str = Field(pattern=_ID)
    domain: Optional[str] = Field(None, pattern=r"^[a-z0-9_]{1,32}$")
    action: str = Field(min_length=3, max_length=500)
    urgency: Literal["Low", "Medium", "High", "Critical"]
    notes: Optional[str] = Field(None, max_length=2000)
    alarm_id: Optional[int] = None


class Assign(BaseModel):
    assignee: Optional[str] = Field(None, max_length=100)


@router.post("/api/work-orders", tags=["work-orders"], status_code=201,
             summary="Create a work order; it waits for approval")
def create_work_order(body: NewWorkOrder, user: User = Depends(require_operator_or_admin)):
    oid = str(uuid.uuid4())
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO work_orders (order_id, machine_id, domain, action, urgency, status, notes, created_by, alarm_id, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, 'Pending Approval', %s, %s, %s, NOW())",
            (oid, body.machine_id, body.domain, body.action, body.urgency, body.notes, user.username, body.alarm_id))
        audit_work_order(conn, (oid, body.machine_id, body.action, body.urgency), user.username, "HUMAN_CREATED",
                         {"domain": body.domain, "alarm_id": body.alarm_id})
        conn.commit()
    return {"order_id": oid, "status": "Pending Approval", "created_by": user.username, **body.model_dump()}


def _move(order_id: str, user: User, from_states: tuple, to: str, result: str, reason: Optional[str] = None) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            f"""UPDATE work_orders SET status = %s, updated_at = NOW(),
                   notes = CASE WHEN %s::text IS NULL THEN notes ELSE concat_ws(E'\\n', notes, %s::text) END
                WHERE order_id::text = %s AND status = ANY(%s) RETURNING {_WO_ROW}""",
            (to, reason, f"{to}: {reason}" if reason else None, order_id, list(from_states))).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"No work order {order_id} in state {' or '.join(from_states)}")
        audit_work_order(conn, row, user.username, result, {"reason": reason} if reason else None)
        conn.commit()
    return {"order_id": order_id, "status": to}


@router.post("/api/work-orders/{order_id}/reject", tags=["work-orders"], summary="Reject a pending work order, with a reason")
def reject_work_order(order_id: str, body: AlarmReason, user: User = Depends(require_operator_or_admin)):
    return _move(order_id, user, ("Pending Approval",), "Rejected", "HUMAN_REJECTED", body.reason)


@router.post("/api/work-orders/{order_id}/start", tags=["work-orders"], summary="Start work on an open order")
def start_work_order(order_id: str, user: User = Depends(require_operator_or_admin)):
    return _move(order_id, user, ("Open",), "In Progress", "HUMAN_STARTED")


@router.patch("/api/work-orders/{order_id}/assign", tags=["work-orders"], summary="Assign a work order to an operator or admin")
def assign_work_order(order_id: str, body: Assign, user: User = Depends(require_operator_or_admin)):
    with pool.connection() as conn:
        if body.assignee is not None:
            ok = conn.execute("SELECT 1 FROM users WHERE username = %s AND role IN ('operator', 'admin')",
                              (body.assignee,)).fetchone()
            if ok is None:
                raise HTTPException(status_code=422, detail="Assignee must be an existing operator or admin")
        before = conn.execute("SELECT assignee FROM work_orders WHERE order_id::text = %s", (order_id,)).fetchone()
        row = conn.execute(
            f"""UPDATE work_orders SET assignee = %s, updated_at = NOW()
                WHERE order_id::text = %s AND status NOT IN ('Resolved', 'Rejected') RETURNING {_WO_ROW}""",
            (body.assignee, order_id)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="No open work order with that id")
        conn.commit()
    A.audit(category="work_order", action="assign", actor=user.username, actor_type="user", role=user.role,
            target=order_id, details={"before": {"assignee": before[0] if before else None},
                                      "after": {"assignee": body.assignee}})
    return {"order_id": order_id, "assignee": body.assignee}


# ---------------------------------------------------------------- users and roles

Role = Literal["admin", "operator", "viewer"]


class RoleChange(BaseModel):
    role: Role


@router.get("/api/users/assignable", tags=["work-orders"], summary="Operators and admins a work order can go to")
def assignable_users(_: User = Depends(require_operator_or_admin)):
    with pool.connection() as conn:
        rows = conn.execute("SELECT username, role FROM users WHERE role IN ('operator', 'admin') ORDER BY username").fetchall()
    return [{"username": r[0], "role": r[1]} for r in rows]


@router.get("/api/admin/users", tags=["admin"], dependencies=[Depends(require_admin)],
            summary="Accounts and their roles (no password hashes or contact details)")
def list_users():
    with pool.connection() as conn:
        rows = conn.execute("SELECT username, role, created_at, email IS NOT NULL FROM users ORDER BY username").fetchall()
    return [{"username": r[0], "role": r[1], "created_at": r[2].isoformat() if r[2] else None, "has_email": r[3]}
            for r in rows]


@router.patch("/api/admin/users/{username}", tags=["admin"], summary="Change a user's role")
def change_role(username: str, body: RoleChange, user: User = Depends(require_admin)):
    if username == user.username:
        raise HTTPException(status_code=409, detail="You cannot change your own role")
    with pool.connection() as conn:
        before = conn.execute("SELECT role FROM users WHERE username = %s", (username,)).fetchone()
        if before is None:
            raise HTTPException(status_code=404, detail="User not found")
        conn.execute("UPDATE users SET role = %s WHERE username = %s", (body.role, username))
        conn.commit()
    A.audit(category="admin", action="user.role", actor=user.username, actor_type="user", role=user.role,
            target=username, details={"before": {"role": before[0]}, "after": {"role": body.role}})
    return {"username": username, "role": body.role}
