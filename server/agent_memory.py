"""
server/agent_memory.py

Persistent memory store for the Phase 8 Agentic AI.

Stores and retrieves agent reasoning history from the agent_memory TimescaleDB table.
Allows the LLM agent to recall what it diagnosed in past sessions and escalate accordingly.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from server.database import pool

logger = logging.getLogger("DigitalTwin.AgentMemory")


class AgentMemory:
    """Interface to the agent_memory table in TimescaleDB."""

    def save_memory(
        self,
        machine_id: str,
        user_message: str,
        agent_response: str,
        tools_used: List[str],
        username: str = "system",
    ) -> Optional[str]:
        """
        Persist an agent reasoning session to memory.

        Args:
            machine_id: The machine that was analyzed
            user_message: The operator's original question
            agent_response: The agent's final response
            tools_used: List of tool names that were called
            username: The operator who triggered this session

        Returns:
            The memory_id UUID string, or None on failure
        """
        memory_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        # Store a compact summary of the diagnosis
        summary = agent_response[:500] if len(agent_response) > 500 else agent_response

        try:
            with pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO agent_memory
                        (memory_id, machine_id, timestamp, user_message, agent_response, summary, tools_used, triggered_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        memory_id,
                        machine_id,
                        now,
                        user_message,
                        agent_response,
                        summary,
                        ",".join(tools_used),
                        username,
                    ),
                )
                conn.commit()
            logger.debug(f"[AgentMemory] Saved memory {memory_id} for {machine_id}")
            return memory_id
        except Exception as e:
            logger.error(f"[AgentMemory] Failed to save memory: {e}")
            return None

    def get_recent_memories(
        self,
        machine_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent agent diagnoses for a machine.

        Args:
            machine_id: The machine to look up
            limit: Max memories to return

        Returns:
            List of dicts with keys: memory_id, timestamp, summary, tools_used
        """
        try:
            with pool.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT memory_id, timestamp, summary, tools_used, triggered_by
                    FROM agent_memory
                    WHERE machine_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (machine_id, limit),
                ).fetchall()

            return [
                {
                    "memory_id": str(row[0]),
                    "timestamp": row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1]),
                    "summary": row[2],
                    "tools_used": row[3].split(",") if row[3] else [],
                    "triggered_by": row[4],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"[AgentMemory] Failed to retrieve memories: {e}")
            return []

    def get_all_machine_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent memories across all machines for fleet-level overview."""
        try:
            with pool.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT memory_id, machine_id, timestamp, summary, tools_used, triggered_by
                    FROM agent_memory
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (limit,),
                ).fetchall()

            return [
                {
                    "memory_id": str(row[0]),
                    "machine_id": row[1],
                    "timestamp": row[2].isoformat() if hasattr(row[2], "isoformat") else str(row[2]),
                    "summary": row[3],
                    "tools_used": row[4].split(",") if row[4] else [],
                    "triggered_by": row[5],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"[AgentMemory] Failed to retrieve fleet memories: {e}")
            return []
