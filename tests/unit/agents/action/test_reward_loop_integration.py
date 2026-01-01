"""Integration tests for reward loop in SecureActionAgent.

Sprint 68 Feature 68.7: Tool-Execution Reward Loop (FEAT-007)
Tests integration of reward calculator and policy with agent.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.action import ActionConfig, SecureActionAgent, ToolSelectionPolicy


class TestRewardLoopIntegration:
    """Test reward loop integration with SecureActionAgent."""

    @pytest.fixture
    def mock_sandbox(self):
        """Create mock sandbox backend."""
        sandbox = MagicMock()
        sandbox.execute = AsyncMock()
        sandbox.get_workspace_path = MagicMock(return_value="/tmp/aegis-workspace")
        sandbox.get_repo_path = MagicMock(return_value="/repo")
        return sandbox

    @pytest.fixture
    def agent_with_reward_loop(self, mock_sandbox):
        """Create agent with reward loop enabled."""
        config = ActionConfig(enable_reward_loop=True, epsilon=0.1, alpha=0.1)
        return SecureActionAgent(config=config, sandbox_backend=mock_sandbox)

    @pytest.fixture
    def agent_without_reward_loop(self, mock_sandbox):
        """Create agent with reward loop disabled."""
        config = ActionConfig(enable_reward_loop=False)
        return SecureActionAgent(config=config, sandbox_backend=mock_sandbox)

    def test_initialization_with_reward_loop(self, agent_with_reward_loop):
        """Test agent initializes reward loop components."""
        assert agent_with_reward_loop.enable_reward_loop is True
        assert agent_with_reward_loop.policy is not None
        assert agent_with_reward_loop.reward_calculator is not None

    def test_initialization_without_reward_loop(self, agent_without_reward_loop):
        """Test agent without reward loop."""
        assert agent_without_reward_loop.enable_reward_loop is False
        assert agent_without_reward_loop.policy is None
        assert agent_without_reward_loop.reward_calculator is None

    @pytest.mark.asyncio
    async def test_execute_with_learning_success(self, agent_with_reward_loop, mock_sandbox):
        """Test execute_with_learning with successful execution."""
        # Mock sandbox execution result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Output"
        mock_result.exit_code = 0
        mock_sandbox.execute.return_value = mock_result

        # Register tools
        agent_with_reward_loop.register_tools(["search", "grep", "find"])

        # Execute with learning
        result = await agent_with_reward_loop.execute_with_learning(
            "search for files", context="search"
        )

        assert result["success"] is True
        assert "reward" in result
        assert "q_value" in result
        assert "tool_name" in result
        assert result["reward"] > 0  # Successful execution should have positive reward

    @pytest.mark.asyncio
    async def test_execute_with_learning_failure(self, agent_with_reward_loop, mock_sandbox):
        """Test execute_with_learning with failed execution."""
        # Mock sandbox execution failure
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "Error"
        mock_result.exit_code = 1
        mock_result.timed_out = False
        mock_sandbox.execute.return_value = mock_result

        agent_with_reward_loop.register_tools(["search"])

        result = await agent_with_reward_loop.execute_with_learning(
            "search for files", tool_name="search"
        )

        assert result["success"] is False
        assert result["reward"] < 0  # Failed execution should have negative reward

    @pytest.mark.asyncio
    async def test_execute_with_learning_user_feedback(
        self, agent_with_reward_loop, mock_sandbox
    ):
        """Test execute_with_learning with user feedback."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Output"
        mock_result.exit_code = 0
        mock_sandbox.execute.return_value = mock_result

        agent_with_reward_loop.register_tools(["search"])

        # Positive feedback
        result = await agent_with_reward_loop.execute_with_learning(
            "search", tool_name="search", user_feedback=1
        )

        assert result["reward"] > 1.0  # Should include user feedback bonus

        # Negative feedback
        result = await agent_with_reward_loop.execute_with_learning(
            "search", tool_name="search", user_feedback=-1
        )

        assert result["reward"] < 1.0  # Should include user feedback penalty

    @pytest.mark.asyncio
    async def test_execute_with_learning_q_value_update(
        self, agent_with_reward_loop, mock_sandbox
    ):
        """Test Q-value updates after execution."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Output"
        mock_result.exit_code = 0
        mock_sandbox.execute.return_value = mock_result

        agent_with_reward_loop.register_tools(["search"])

        # Initial Q-value should be 0
        initial_q = agent_with_reward_loop.policy.get_q_value("search", "search")
        assert initial_q == 0.0

        # Execute and update
        await agent_with_reward_loop.execute_with_learning("search", tool_name="search")

        # Q-value should be updated
        updated_q = agent_with_reward_loop.policy.get_q_value("search", "search")
        assert updated_q > 0.0

    @pytest.mark.asyncio
    async def test_execute_with_learning_without_reward_loop(
        self, agent_without_reward_loop, mock_sandbox
    ):
        """Test execute_with_learning falls back when reward loop disabled."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Output"
        mock_result.exit_code = 0
        mock_sandbox.execute.return_value = mock_result

        result = await agent_without_reward_loop.execute_with_learning("task")

        assert result["success"] is True
        assert "reward" not in result  # No reward calculated
        assert "tool_name" in result

    def test_register_tools(self, agent_with_reward_loop):
        """Test registering available tools."""
        tools = ["search", "grep", "find", "ls"]

        agent_with_reward_loop.register_tools(tools)

        assert agent_with_reward_loop.available_tools == tools

    def test_get_policy_statistics(self, agent_with_reward_loop):
        """Test getting policy statistics."""
        # Add some state
        agent_with_reward_loop.policy.update_q_value("tool", "context", 1.0)

        stats = agent_with_reward_loop.get_policy_statistics()

        assert "total_tools" in stats
        assert "total_updates" in stats
        assert stats["total_updates"] == 1

    def test_get_policy_statistics_without_reward_loop(self, agent_without_reward_loop):
        """Test getting statistics fails when reward loop disabled."""
        with pytest.raises(RuntimeError, match="Reward loop is disabled"):
            agent_without_reward_loop.get_policy_statistics()

    def test_export_policy(self, agent_with_reward_loop):
        """Test exporting policy state."""
        agent_with_reward_loop.policy.update_q_value("tool", "context", 1.0)

        state = agent_with_reward_loop.export_policy()

        assert "epsilon" in state
        assert "q_values" in state
        assert "total_updates" in state

    def test_export_policy_without_reward_loop(self, agent_without_reward_loop):
        """Test exporting policy fails when reward loop disabled."""
        with pytest.raises(RuntimeError, match="Reward loop is disabled"):
            agent_without_reward_loop.export_policy()

    def test_load_policy(self, agent_with_reward_loop):
        """Test loading policy state."""
        policy_state = {
            "epsilon": 0.15,
            "alpha": 0.1,
            "gamma": 0.9,
            "total_updates": 5,
            "q_values": {"tool:context": 1.5},
            "counts": {"tool:context": 3},
        }

        agent_with_reward_loop.load_policy(policy_state)

        assert agent_with_reward_loop.policy.epsilon == 0.15
        assert agent_with_reward_loop.policy.total_updates == 5
        assert agent_with_reward_loop.policy.get_q_value("tool", "context") == 1.5

    def test_load_policy_without_reward_loop(self, agent_without_reward_loop):
        """Test loading policy fails when reward loop disabled."""
        with pytest.raises(RuntimeError, match="Reward loop is disabled"):
            agent_without_reward_loop.load_policy({})

    @pytest.mark.asyncio
    async def test_tool_selection_policy_integration(
        self, agent_with_reward_loop, mock_sandbox
    ):
        """Test policy-based tool selection."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Output"
        mock_result.exit_code = 0
        mock_sandbox.execute.return_value = mock_result

        # Register tools and set Q-values
        agent_with_reward_loop.register_tools(["search", "grep", "find"])
        agent_with_reward_loop.policy.q_values[("search", "search")] = 2.0
        agent_with_reward_loop.policy.q_values[("grep", "search")] = 1.0
        agent_with_reward_loop.policy.q_values[("find", "search")] = 0.5

        # Force exploitation
        agent_with_reward_loop.policy.epsilon = 0.0

        # Execute without specifying tool (should select "search")
        result = await agent_with_reward_loop.execute_with_learning(
            "search for files", context="search"
        )

        assert result["tool_name"] == "search"  # Should select tool with highest Q-value

    def test_custom_policy_injection(self, mock_sandbox):
        """Test injecting custom policy instance."""
        custom_policy = ToolSelectionPolicy(epsilon=0.2, alpha=0.15)
        # Directly set Q-value instead of update (which applies epsilon decay)
        custom_policy.q_values[("custom_tool", "context")] = 5.0

        config = ActionConfig(enable_reward_loop=True)
        agent = SecureActionAgent(
            config=config, sandbox_backend=mock_sandbox, policy=custom_policy
        )

        # Epsilon should still be 0.2 since we didn't call update_q_value
        assert agent.policy.epsilon == 0.2
        assert agent.policy.get_q_value("custom_tool", "context") == 5.0
