"""
server/llm_agent.py

Phase 8 Agentic AI: LLM-powered reasoning agent.

Uses Google Gemini Flash with function calling to:
1. Receive an operator question or a machine status context
2. Autonomously call tools (query_telemetry, get_recent_alerts, etc.)
3. Reason over tool outputs
4. Generate a structured, actionable diagnosis and response
5. Persist its reasoning to agent_memory

Set GEMINI_API_KEY in .env to enable. When GEMINI_AGENT_ENABLED=true,
the app will refuse to start if GEMINI_API_KEY is not set (fail-loud).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from server.agent_tools import TOOL_DECLARATIONS, TOOL_REGISTRY
from server.agent_memory import AgentMemory

logger = logging.getLogger("DigitalTwin.LLMAgent")

GEMINI_AGENT_ENABLED = os.getenv("GEMINI_AGENT_ENABLED", "false").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
MAX_TOOL_ROUNDS = 5  # Safety: max tool-calling iterations per request

# Fail-loud: if agent feature is explicitly enabled but key is missing, crash at import
if GEMINI_AGENT_ENABLED and not GEMINI_API_KEY:
    raise RuntimeError(
        "FATAL: GEMINI_AGENT_ENABLED=true but GEMINI_API_KEY is not set. "
        "Add your Gemini API key to .env or set GEMINI_AGENT_ENABLED=false."
    )


SYSTEM_PROMPT = """You are an expert Industrial AI Maintenance Agent for an MSME factory floor.

STRICT DOMAIN RESTRICTION: You MUST ONLY answer questions related to industrial predictive maintenance, telemetry data, factory operations, machine faults, or the digital twin platform. If the user asks a general-knowledge question, programming question, casual chat, or any topic outside of this industrial context, you MUST politely decline and state that you are restricted to factory maintenance and operations.

You have access to real-time telemetry, alert history, maintenance records, and the ability to
create work orders. Your job is to:
1. Diagnose machine faults using real sensor data — not just thresholds, but patterns and context.
2. Provide clear, actionable recommendations in plain language.
3. Autonomously create work orders when maintenance is needed.
4. Remember past diagnoses and escalate if warnings were ignored.

When answering, always:
- Base your diagnosis on actual data from the tools, not assumptions.
- Mention which sensors are out of range and by how much.
- Estimate urgency based on rate of change, not just current value.
- Be concise. Operators are busy on the factory floor.

Available machines: M001 (Lathe), M002 (Pump Motor), M003 (Drill Press), M004 (Furnace).
"""


def _build_gemini_tools() -> List[Dict]:
    """Convert tool declarations to Gemini FunctionDeclaration format."""
    return [
        {
            "function_declarations": [
                {
                    "name": decl["name"],
                    "description": decl["description"],
                    "parameters": decl["parameters"],
                }
                for decl in TOOL_DECLARATIONS
            ]
        }
    ]


def _call_tool(tool_name: str, tool_args: Dict) -> str:
    """Execute a tool and return its result as a JSON string."""
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    try:
        result = fn(**tool_args)
        return json.dumps(result, default=str)
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return json.dumps({"error": str(e)})


def run_agent(
    user_message: str,
    machine_id: Optional[str] = None,
    username: str = "operator",
) -> Dict[str, Any]:
    """
    Main agent entry point. Runs the agentic reasoning loop.

    Args:
        user_message: The operator's question or task
        machine_id: Optional machine context to pre-load
        username: The operator's username (for memory logging)

    Returns:
        dict with: response (str), tools_called (list), work_orders_created (list)
    """
    if not GEMINI_API_KEY:
        # Agent feature not enabled — return informational response
        logger.info("GEMINI_API_KEY not set and agent not enabled — returning fallback.")
        return {
            "response": (
                "⚠️ LLM Agent is not configured. "
                "Set GEMINI_AGENT_ENABLED=true and GEMINI_API_KEY in .env to enable "
                "natural language diagnosis. The rule-based AI agent is still running."
            ),
            "tools_called": [],
            "work_orders_created": [],
            "llm_enabled": False,
        }

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            tools=_build_gemini_tools(),
        )
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        return {
            "response": f"Agent initialization failed: {e}",
            "tools_called": [],
            "work_orders_created": [],
            "llm_enabled": False,
        }

    # Retrieve agent memory for this machine
    memory = AgentMemory()
    memory_context = ""
    if machine_id:
        past = memory.get_recent_memories(machine_id, limit=3)
        if past:
            memory_context = "\n\nAgent Memory (past diagnoses for this machine):\n"
            for m in past:
                memory_context += f"- [{m['timestamp']}] {m['summary']}\n"

    # Build initial message with context
    full_message = user_message
    if machine_id:
        full_message = f"[Context: Machine {machine_id}]\n{user_message}"
    if memory_context:
        full_message = full_message + memory_context

    # Agentic loop
    chat = model.start_chat(history=[])
    tools_called = []
    work_orders_created = []
    final_response = ""

    for _ in range(MAX_TOOL_ROUNDS):
        response = chat.send_message(full_message)
        full_message = ""  # Only first message is the user message

        # Check if Gemini wants to call a tool
        tool_calls_in_response = []
        for part in response.parts:
            if hasattr(part, "function_call") and part.function_call:
                tool_calls_in_response.append(part.function_call)

        if not tool_calls_in_response:
            # No more tool calls — extract final text response
            final_response = response.text
            break

        # Execute each tool call and feed results back
        tool_results = []
        for fc in tool_calls_in_response:
            tool_name = fc.name
            tool_args = dict(fc.args)
            logger.info(f"[LLMAgent] Calling tool: {tool_name}({tool_args})")
            result_str = _call_tool(tool_name, tool_args)
            tools_called.append({"tool": tool_name, "args": tool_args})

            if tool_name == "create_work_order":
                result_dict = json.loads(result_str)
                if "order_id" in result_dict:
                    work_orders_created.append(result_dict)

            tool_results.append({
                "function_response": {
                    "name": tool_name,
                    "response": {"result": result_str},
                }
            })

        # Send tool results back to Gemini
        full_message = tool_results  # type: ignore[assignment]

    else:
        # Hit max rounds without a final text response
        final_response = "I completed my analysis but hit the maximum reasoning steps. Please try a more specific question."

    # Persist to agent memory
    if machine_id and final_response:
        memory.save_memory(
            machine_id=machine_id,
            user_message=user_message,
            agent_response=final_response,
            tools_used=[t["tool"] for t in tools_called],
            username=username,
        )

    logger.info(f"[LLMAgent] Completed for {machine_id or 'fleet'}: {len(tools_called)} tools, {len(work_orders_created)} work orders")

    return {
        "response": final_response,
        "tools_called": tools_called,
        "work_orders_created": work_orders_created,
        "llm_enabled": True,
    }
