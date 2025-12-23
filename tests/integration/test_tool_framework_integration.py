"""Integration tests for Tool Framework.

Sprint 59: End-to-end tool framework integration tests.

These tests verify that all components work together correctly:
- Tool registration
- Parameter validation
- Tool execution
- Sandboxing integration
"""

import pytest

from src.domains.llm_integration.tools.executor import ToolExecutor
from src.domains.llm_integration.tools.registry import ToolRegistry


@pytest.mark.integration
class TestToolFrameworkIntegration:
    """Integration tests for complete tool framework."""

    @pytest.mark.asyncio
    async def test_bash_tool_end_to_end(self):
        """Test bash tool from registration to execution."""
        executor = ToolExecutor(sandbox_enabled=False)

        # Execute bash command
        result = await executor.execute(
            "bash", {"command": "echo 'integration test'", "timeout": 10}
        )

        assert "result" in result
        result_data = result["result"]
        assert result_data["success"] is True
        assert "integration test" in result_data["stdout"]

    @pytest.mark.asyncio
    async def test_python_tool_end_to_end(self):
        """Test python tool from registration to execution."""
        executor = ToolExecutor(sandbox_enabled=False)

        # Execute python code
        result = await executor.execute(
            "python", {"code": "result = 10 + 20\nprint(result)", "timeout": 10}
        )

        assert "result" in result
        result_data = result["result"]
        assert result_data["success"] is True
        assert "30" in result_data["output"]

    @pytest.mark.asyncio
    async def test_tool_validation_integration(self):
        """Test that parameter validation works end-to-end."""
        executor = ToolExecutor()

        # Missing required parameter
        result = await executor.execute(
            "bash",
            {
                # Missing "command" parameter
                "timeout": 10
            },
        )

        assert "error" in result
        assert "Invalid parameters" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_tool_execution(self):
        """Test batch execution of multiple tools."""
        executor = ToolExecutor(sandbox_enabled=False)

        tool_calls = [
            {"name": "bash", "parameters": {"command": "echo 'first'"}},
            {"name": "python", "parameters": {"code": "print('second')"}},
        ]

        results = await executor.batch_execute(tool_calls)

        assert len(results) == 2
        # Both should have successful results
        assert "result" in results[0]
        assert "result" in results[1]

    @pytest.mark.asyncio
    async def test_tool_executor_stats(self):
        """Test execution statistics tracking."""
        executor = ToolExecutor(sandbox_enabled=False)

        # Execute some tools
        await executor.execute("bash", {"command": "echo 'test'"})
        await executor.execute("python", {"code": "print('test')"})

        # Check stats
        stats = executor.get_stats()

        assert stats["total_executions"] >= 2
        assert "error_rate" in stats

    @pytest.mark.asyncio
    async def test_openai_schema_generation(self):
        """Test OpenAI schema generation for all tools."""
        schema = ToolRegistry.get_openai_tools_schema()

        assert len(schema) >= 2  # At least bash and python

        # Check bash tool schema
        bash_tool = next((t for t in schema if t["function"]["name"] == "bash"), None)
        assert bash_tool is not None
        assert "parameters" in bash_tool["function"]
        assert "command" in bash_tool["function"]["parameters"]["properties"]


@pytest.mark.integration
class TestToolSecurityIntegration:
    """Integration tests for tool security features."""

    @pytest.mark.asyncio
    async def test_bash_security_enforcement(self):
        """Test that dangerous bash commands are blocked."""
        executor = ToolExecutor(sandbox_enabled=False)

        # Try dangerous command
        result = await executor.execute("bash", {"command": "rm -rf /"})

        # Should be blocked by security check
        assert "result" in result
        result_data = result["result"]
        assert "error" in result_data
        assert "blocked" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_python_security_enforcement(self):
        """Test that dangerous Python code is blocked."""
        executor = ToolExecutor(sandbox_enabled=False)

        # Try importing blocked module
        result = await executor.execute("python", {"code": "import os\nos.system('ls')"})

        # Should be blocked by AST validation
        assert "result" in result
        result_data = result["result"]
        assert result_data["success"] is False
        assert "blocked" in result_data["error"].lower()


@pytest.mark.integration
class TestResearchAgentIntegration:
    """Integration tests for research agent."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires LLM and vector DB setup")
    async def test_research_workflow_integration(self):
        """Test complete research workflow (requires setup)."""
        from src.agents.research import run_research

        # This test would require full system setup
        # Including LLM proxy, vector DB, graph DB
        result = await run_research("What is machine learning?", max_iterations=1)

        assert "synthesis" in result
        assert "search_results" in result
