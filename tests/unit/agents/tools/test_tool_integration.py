"""Unit tests for tool integration.

Sprint 70 Feature 70.5: Tool Use in Normal Chat
"""

import pytest

from src.agents.tools.tool_integration import (
    _extract_tool_request,
    should_use_tools,
    tools_node,
)


class TestShouldUseTools:
    """Test should_use_tools conditional function."""

    def test_should_use_tools_with_tool_marker(self):
        """Test detection with explicit tool marker."""
        state = {"answer": "[TOOL:search] machine learning"}

        decision = should_use_tools(state)

        assert decision == "tools"

    def test_should_use_tools_with_search_marker(self):
        """Test detection with search marker."""
        state = {"answer": "[SEARCH:python] best practices"}

        decision = should_use_tools(state)

        assert decision == "tools"

    def test_should_use_tools_with_fetch_marker(self):
        """Test detection with fetch marker."""
        state = {"answer": "[FETCH:url] https://example.com"}

        decision = should_use_tools(state)

        assert decision == "tools"

    def test_should_use_tools_with_action_indicator(self):
        """Test detection with action indicator."""
        state = {"answer": "I need to check the latest documentation"}

        decision = should_use_tools(state)

        assert decision == "tools"

    def test_should_use_tools_with_check_indicator(self):
        """Test detection with check indicator."""
        state = {"answer": "Let me check the API status"}

        decision = should_use_tools(state)

        assert decision == "tools"

    def test_should_use_tools_normal_answer(self):
        """Test normal answer without tool indicators."""
        state = {"answer": "Python is a programming language"}

        decision = should_use_tools(state)

        assert decision == "end"

    def test_should_use_tools_empty_answer(self):
        """Test empty answer."""
        state = {"answer": ""}

        decision = should_use_tools(state)

        assert decision == "end"

    def test_should_use_tools_missing_answer(self):
        """Test missing answer field."""
        state = {}

        decision = should_use_tools(state)

        assert decision == "end"


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
