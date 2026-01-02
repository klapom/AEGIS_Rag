"""Unit tests for tool integration.

Sprint 70 Feature 70.5: Tool Use in Normal Chat
Sprint 70 Feature 70.11: LLM-based Tool Detection
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel, Field

from src.agents.tools.tool_integration import (
    _extract_tool_request,
    _should_use_tools_markers,
    _should_use_tools_hybrid,
    should_use_tools,
    tools_node,
)


# Mock ToolsConfig for testing
class MockToolsConfig(BaseModel):
    """Mock ToolsConfig for testing."""

    enable_chat_tools: bool = False
    enable_research_tools: bool = False
    tool_detection_strategy: str = "markers"
    explicit_tool_markers: list[str] = Field(
        default_factory=lambda: ["[TOOL:", "[SEARCH:", "[FETCH:"]
    )
    action_hint_phrases: list[str] = Field(
        default_factory=lambda: ["need to", "check", "search", "latest"]
    )


class TestShouldUseToolsMarkers:
    """Test marker-based tool detection strategy."""

    def test_should_use_tools_with_tool_marker(self):
        """Test detection with explicit tool marker."""
        config = MockToolsConfig()
        state = {"answer": "[TOOL:search] machine learning"}

        decision = _should_use_tools_markers(state, config)

        assert decision == "tools"

    def test_should_use_tools_with_search_marker(self):
        """Test detection with search marker."""
        config = MockToolsConfig()
        state = {"answer": "[SEARCH:python] best practices"}

        decision = _should_use_tools_markers(state, config)

        assert decision == "tools"

    def test_should_use_tools_with_fetch_marker(self):
        """Test detection with fetch marker."""
        config = MockToolsConfig()
        state = {"answer": "[FETCH:url] https://example.com"}

        decision = _should_use_tools_markers(state, config)

        assert decision == "tools"

    def test_should_use_tools_normal_answer(self):
        """Test normal answer without tool indicators."""
        config = MockToolsConfig()
        state = {"answer": "Python is a programming language"}

        decision = _should_use_tools_markers(state, config)

        assert decision == "end"

    def test_should_use_tools_empty_answer(self):
        """Test empty answer."""
        config = MockToolsConfig()
        state = {"answer": ""}

        decision = _should_use_tools_markers(state, config)

        assert decision == "end"

    def test_should_use_tools_custom_markers(self):
        """Test with custom configured markers."""
        config = MockToolsConfig(explicit_tool_markers=["<ACTION>", "<DO>"])
        state = {"answer": "<ACTION> do something"}

        decision = _should_use_tools_markers(state, config)

        assert decision == "tools"


class TestShouldUseToolsHybrid:
    """Test hybrid tool detection strategy."""

    def test_hybrid_fast_path_with_marker(self):
        """Test hybrid fast path with explicit marker."""
        config = MockToolsConfig()
        state = {"answer": "[TOOL:search] test"}

        # Should immediately return "tools" (fast path, no LLM call)
        decision = _should_use_tools_hybrid(state, config)

        assert decision == "tools"

    def test_hybrid_no_hints_no_markers(self):
        """Test hybrid with no markers and no action hints."""
        config = MockToolsConfig()
        state = {"answer": "Python is a programming language"}

        # Should return "end" without LLM call
        decision = _should_use_tools_hybrid(state, config)

        assert decision == "end"

    @pytest.mark.asyncio
    async def test_hybrid_slow_path_with_action_hint(self, mocker):
        """Test hybrid slow path with action hint triggering LLM."""
        config = MockToolsConfig()
        state = {
            "answer": "I need to search for Python documentation",
            "question": "How to use Python?"
        }

        # Mock LLM decision
        class MockToolDecision(BaseModel):
            use_tools: bool = True
            reasoning: str = "User needs current documentation"
            tool_type: str = "search"
            query: str = "Python documentation"

        # Mock get_llm_client
        mock_llm_client = MagicMock()
        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_chain = MagicMock()

        mock_chain.ainvoke = AsyncMock(return_value=MockToolDecision())
        mock_structured_llm.with_structured_output.return_value = None
        mock_llm.with_structured_output.return_value = mock_structured_llm

        mock_llm_client.get_chat_model.return_value = mock_llm

        # Create async mock for the chain
        async def mock_chain_invoke(*args, **kwargs):
            return MockToolDecision()

        mocker.patch(
            "src.agents.tools.tool_integration.get_llm_client",
            return_value=mock_llm_client
        )

        # Mock the chain execution
        mocker.patch(
            "src.agents.tools.tool_integration._should_use_tools_llm",
            return_value="tools"
        )

        # Execute
        decision = await _should_use_tools_hybrid(state, config)

        # Should invoke LLM (slow path) and return "tools"
        assert decision == "tools"


class TestShouldUseToolsRouter:
    """Test should_use_tools router function."""

    @pytest.mark.asyncio
    async def test_router_loads_config_and_routes_to_markers(self, mocker):
        """Test router loads config and routes to markers strategy."""
        # Mock config service
        mock_config_service = MagicMock()
        mock_config_service.get_config = AsyncMock(
            return_value=MockToolsConfig(tool_detection_strategy="markers")
        )

        mocker.patch(
            "src.agents.tools.tool_integration.get_tools_config_service",
            return_value=mock_config_service
        )

        state = {"answer": "[TOOL:test]"}

        decision = await should_use_tools(state)

        assert decision == "tools"
        mock_config_service.get_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_router_fallback_on_config_error(self, mocker):
        """Test router falls back to markers on config load error."""
        # Mock config service to raise error
        mocker.patch(
            "src.agents.tools.tool_integration.get_tools_config_service",
            side_effect=Exception("Redis connection failed")
        )

        state = {"answer": "[TOOL:test]"}

        # Should fallback to markers strategy
        decision = await should_use_tools(state)

        # With default markers, should detect [TOOL:]
        assert decision == "tools"

    @pytest.mark.asyncio
    async def test_router_unknown_strategy_fallback(self, mocker):
        """Test router handles unknown strategy."""
        # Mock config with unknown strategy
        mock_config_service = MagicMock()
        mock_config_service.get_config = AsyncMock(
            return_value=MockToolsConfig(tool_detection_strategy="unknown_strategy")
        )

        mocker.patch(
            "src.agents.tools.tool_integration.get_tools_config_service",
            return_value=mock_config_service
        )

        state = {"answer": "[TOOL:test]"}

        # Should fallback to markers
        decision = await should_use_tools(state)

        assert decision == "tools"


class TestExtractToolRequest:
    """Test tool request extraction."""

    def test_extract_tool_marker(self):
        """Test extraction from TOOL marker."""
        answer = "[TOOL:search] machine learning"

        request = _extract_tool_request(answer)

        assert request is not None
        assert request["action"] == "search"
        assert request["parameters"] == {}

    def test_extract_search_marker(self):
        """Test extraction from SEARCH marker."""
        answer = "[SEARCH:python] best practices"

        request = _extract_tool_request(answer)

        assert request is not None
        assert request["action"] == "search python"
        assert request["parameters"] == {}

    def test_extract_fetch_marker(self):
        """Test extraction from FETCH marker."""
        answer = "[FETCH:url] https://example.com"

        request = _extract_tool_request(answer)

        assert request is not None
        assert request["action"] == "fetch url url"
        assert request["parameters"] == {}

    def test_extract_no_marker(self):
        """Test extraction from normal text."""
        answer = "Normal answer without markers"

        request = _extract_tool_request(answer)

        assert request is None

    def test_extract_incomplete_marker(self):
        """Test extraction from incomplete marker."""
        answer = "[TOOL:search without closing bracket"

        request = _extract_tool_request(answer)

        assert request is not None  # Should still extract


class TestToolsNode:
    """Test tools_node execution."""

    @pytest.mark.asyncio
    async def test_tools_node_success(self, mocker):
        """Test successful tool execution."""
        # Mock MCP client and executor
        mock_client = mocker.MagicMock()
        mock_executor = mocker.MagicMock()

        mocker.patch(
            "src.agents.tools.tool_integration.get_mcp_client",
            return_value=mock_client,
        )
        mocker.patch(
            "src.agents.tools.tool_integration.ToolExecutor",
            return_value=mock_executor,
        )

        # Mock ActionAgent
        mock_action_agent = mocker.MagicMock()
        mock_action_agent.graph.ainvoke = mocker.AsyncMock(
            return_value={
                "selected_tool": "search_tool",
                "tool_result": "Search results: Python is a programming language",
            }
        )

        mocker.patch(
            "src.agents.tools.tool_integration.ActionAgent",
            return_value=mock_action_agent,
        )

        # Execute
        state = {
            "answer": "[TOOL:search] python",
            "retrieved_contexts": [],
        }

        result = await tools_node(state)

        # Verify
        assert "retrieved_contexts" in result
        assert len(result["retrieved_contexts"]) == 1
        assert result["retrieved_contexts"][0]["source"] == "tool"
        assert result["retrieved_contexts"][0]["tool_name"] == "search_tool"
        assert result["tool_execution_count"] == 1

    @pytest.mark.asyncio
    async def test_tools_node_error(self, mocker):
        """Test tool execution error handling."""
        # Mock MCP client and executor
        mock_client = mocker.MagicMock()
        mock_executor = mocker.MagicMock()

        mocker.patch(
            "src.agents.tools.tool_integration.get_mcp_client",
            return_value=mock_client,
        )
        mocker.patch(
            "src.agents.tools.tool_integration.ToolExecutor",
            return_value=mock_executor,
        )

        # Mock ActionAgent to raise error
        mocker.patch(
            "src.agents.tools.tool_integration.ActionAgent",
            side_effect=Exception("MCP error"),
        )

        # Execute
        state = {
            "answer": "[TOOL:search] python",
            "retrieved_contexts": [],
        }

        result = await tools_node(state)

        # Should add error context
        assert "retrieved_contexts" in result
        assert len(result["retrieved_contexts"]) == 1
        assert result["retrieved_contexts"][0]["source"] == "tool_error"
        assert result["tool_execution_count"] == 1

    @pytest.mark.asyncio
    async def test_tools_node_no_tool_request(self, mocker):
        """Test when no tool request is found."""
        # Execute
        state = {
            "answer": "Normal answer",
            "retrieved_contexts": [],
        }

        result = await tools_node(state)

        # Should return empty update
        assert result == {}

    @pytest.mark.asyncio
    async def test_tools_node_increments_count(self, mocker):
        """Test that execution count increments."""
        # Mock successful execution
        mock_client = mocker.MagicMock()
        mock_executor = mocker.MagicMock()

        mocker.patch(
            "src.agents.tools.tool_integration.get_mcp_client",
            return_value=mock_client,
        )
        mocker.patch(
            "src.agents.tools.tool_integration.ToolExecutor",
            return_value=mock_executor,
        )

        mock_action_agent = mocker.MagicMock()
        mock_action_agent.graph.ainvoke = mocker.AsyncMock(
            return_value={
                "selected_tool": "tool",
                "tool_result": "result",
            }
        )

        mocker.patch(
            "src.agents.tools.tool_integration.ActionAgent",
            return_value=mock_action_agent,
        )

        # Execute with existing count
        state = {
            "answer": "[TOOL:test]",
            "retrieved_contexts": [],
            "tool_execution_count": 5,
        }

        result = await tools_node(state)

        # Should increment from 5 to 6
        assert result["tool_execution_count"] == 6
