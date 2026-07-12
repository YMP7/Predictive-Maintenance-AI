"""
tests/test_phase8_agent.py

Phase 8: Tests for the agentic AI components.

All tests mock server.database at sys.modules level to avoid requiring
a live TimescaleDB instance, since database.py crashes at import if
DATABASE_URL is not set.

Covers:
1. LLM agent fallback when API key is not set
2. Tool registry completeness
3. Agent memory isolation
4. Work order tool validation
5. System prompt domain restriction
6. Safety bounds
"""
import os
import sys
import importlib
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Module-level fixture: mock server.database before any agent module imports
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_database(monkeypatch):
    """
    Replace server.database with a mock before importing agent modules.
    This avoids the RuntimeError from DATABASE_URL not being set.
    """
    mock_db = MagicMock()
    mock_pool = MagicMock()
    mock_db.pool = mock_pool

    # Set up context manager for pool.connection()
    mock_conn = MagicMock()
    mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.fetchall.return_value = []
    mock_conn.execute.return_value.fetchone.return_value = [0]

    monkeypatch.setitem(sys.modules, "server.database", mock_db)

    # Clear cached imports of agent modules so they re-import with the mock
    for mod_name in list(sys.modules.keys()):
        if mod_name in ("server.agent_tools", "server.agent_memory", "server.llm_agent"):
            del sys.modules[mod_name]

    yield mock_conn

    # Clean up to avoid polluting other test files
    for mod_name in ("server.agent_tools", "server.agent_memory", "server.llm_agent"):
        sys.modules.pop(mod_name, None)


# ---- llm_agent tests ----

class TestLLMAgentFallback:
    """Test agent behavior when Gemini API key is not configured."""

    def test_missing_api_key_returns_fallback(self):
        """When GEMINI_API_KEY is empty, run_agent should return a fallback response."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GEMINI_AGENT_ENABLED": "false"}, clear=False):
            import server.llm_agent as llm_mod
            importlib.reload(llm_mod)

            result = llm_mod.run_agent("What is wrong with M001?", machine_id="M001")

            assert result["llm_enabled"] is False
            assert "not configured" in result["response"].lower() or "⚠" in result["response"]
            assert result["tools_called"] == []
            assert result["work_orders_created"] == []

    def test_fail_loud_when_enabled_but_missing_key(self):
        """When GEMINI_AGENT_ENABLED=true but GEMINI_API_KEY is empty, should raise RuntimeError."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GEMINI_AGENT_ENABLED": "true"}, clear=False):
            with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
                import server.llm_agent as llm_mod
                importlib.reload(llm_mod)


# ---- agent_tools tests ----

class TestAgentToolRegistry:
    """Test the tool registry and declarations are complete and consistent."""

    def test_all_declared_tools_are_registered(self):
        """Every tool in TOOL_DECLARATIONS must have a matching entry in TOOL_REGISTRY."""
        from server.agent_tools import TOOL_DECLARATIONS, TOOL_REGISTRY

        declared_names = {d["name"] for d in TOOL_DECLARATIONS}
        registered_names = set(TOOL_REGISTRY.keys())

        assert declared_names == registered_names, (
            f"Mismatch: declared={declared_names}, registered={registered_names}"
        )

    def test_tool_declarations_have_required_fields(self):
        """Each tool declaration must have name, description, and parameters."""
        from server.agent_tools import TOOL_DECLARATIONS

        for decl in TOOL_DECLARATIONS:
            assert "name" in decl, f"Missing 'name' in declaration: {decl}"
            assert "description" in decl, f"Missing 'description' in {decl['name']}"
            assert "parameters" in decl, f"Missing 'parameters' in {decl['name']}"
            assert decl["parameters"]["type"] == "object", (
                f"Parameters for {decl['name']} should be type 'object'"
            )

    def test_create_work_order_validates_urgency(self, _mock_database):
        """create_work_order should default invalid urgency to 'Medium'."""
        from server.agent_tools import create_work_order

        result = create_work_order(
            machine_id="M001",
            action="Replace bearing",
            urgency="INVALID_VALUE",
        )

        # Find the INSERT INTO work_orders call
        calls = _mock_database.execute.call_args_list
        work_order_call = next(c for c in calls if "INSERT INTO work_orders" in c[0][0])
        
        # Check the actual INSERT call args — urgency is param index 3
        assert work_order_call[0][1][3] == "Medium", (
            f"Invalid urgency should default to 'Medium', got: {work_order_call[0][1][3]}"
        )

    def test_query_telemetry_bounds_hours(self):
        """query_telemetry should not crash with extreme hour values."""
        from server.agent_tools import query_telemetry

        # Should not crash with extreme values
        result = query_telemetry("M001", hours=99999)
        assert result["count"] == 0

        result = query_telemetry("M001", hours=-5)
        assert result["count"] == 0


# ---- agent_memory tests ----

class TestAgentMemoryIsolation:
    """Test agent memory behavior regarding user sessions."""

    def test_memories_are_keyed_by_machine_not_user(self, _mock_database):
        """
        Documents the current design: memories are keyed by machine_id.
        get_recent_memories for a machine returns ALL users' memories for that machine.
        """
        from server.agent_memory import AgentMemory

        memory = AgentMemory()

        # Save memories from two different users for the same machine
        memory.save_memory(
            machine_id="M001",
            user_message="What's wrong?",
            agent_response="Bearing wear detected",
            tools_used=["query_telemetry"],
            username="user_a",
        )

        memory.save_memory(
            machine_id="M001",
            user_message="Status update?",
            agent_response="Still degrading",
            tools_used=["query_telemetry", "get_recent_alerts"],
            username="user_b",
        )

        # Verify both INSERTs were made (2 execute calls, 2 commits)
        assert _mock_database.execute.call_count == 2
        assert _mock_database.commit.call_count == 2

        # The SELECT in get_recent_memories filters by machine_id only
        _mock_database.execute.return_value.fetchall.return_value = [
            ("mem1", "2026-07-10T12:00:00Z", "Bearing wear detected", "query_telemetry", "user_a"),
            ("mem2", "2026-07-10T12:01:00Z", "Still degrading", "query_telemetry,get_recent_alerts", "user_b"),
        ]

        memories = memory.get_recent_memories("M001", limit=10)

        # Both users' memories are returned — this is the documented behavior
        assert len(memories) == 2
        triggered_by_users = {m["triggered_by"] for m in memories}
        assert triggered_by_users == {"user_a", "user_b"}


# ---- System prompt tests ----

class TestSystemPrompt:
    """Test system prompt configuration."""

    def test_system_prompt_has_domain_restriction(self):
        """The system prompt should contain a domain restriction clause."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GEMINI_AGENT_ENABLED": "false"}, clear=False):
            import server.llm_agent as llm_mod
            importlib.reload(llm_mod)

            prompt = llm_mod.SYSTEM_PROMPT
            assert "STRICT DOMAIN RESTRICTION" in prompt
            assert "politely decline" in prompt.lower()

    def test_system_prompt_lists_all_machines(self):
        """System prompt should reference all four machines."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GEMINI_AGENT_ENABLED": "false"}, clear=False):
            import server.llm_agent as llm_mod
            importlib.reload(llm_mod)

            prompt = llm_mod.SYSTEM_PROMPT
            for mid in ["M001", "M002", "M003", "M004"]:
                assert mid in prompt, f"System prompt should reference {mid}"

    def test_max_tool_rounds_is_bounded(self):
        """MAX_TOOL_ROUNDS should be a reasonable safety cap."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GEMINI_AGENT_ENABLED": "false"}, clear=False):
            import server.llm_agent as llm_mod
            importlib.reload(llm_mod)

            assert llm_mod.MAX_TOOL_ROUNDS <= 10, (
                f"MAX_TOOL_ROUNDS={llm_mod.MAX_TOOL_ROUNDS} is too high"
            )
            assert llm_mod.MAX_TOOL_ROUNDS >= 1
