"""Unit tests for ToolSelectionPolicy.

Sprint 68 Feature 68.7: Tool-Execution Reward Loop (FEAT-007)
Tests ε-greedy policy and Q-learning updates.
"""

import json
import random

import pytest

from src.agents.action.tool_policy import ToolSelectionPolicy


class TestToolSelectionPolicy:
    """Test ToolSelectionPolicy class."""

    @pytest.fixture
    def policy(self):
        """Create policy instance with fixed seed for reproducibility."""
        random.seed(42)
        return ToolSelectionPolicy(epsilon=0.1, alpha=0.1)

    def test_initialization(self):
        """Test policy initialization."""
        policy = ToolSelectionPolicy(epsilon=0.2, alpha=0.15, gamma=0.95)

        assert policy.epsilon == 0.2
        assert policy.alpha == 0.15
        assert policy.gamma == 0.95
        assert policy.total_updates == 0
        assert len(policy.q_values) == 0

    def test_initialization_invalid_epsilon(self):
        """Test initialization with invalid epsilon."""
        with pytest.raises(ValueError, match="epsilon must be in"):
            ToolSelectionPolicy(epsilon=1.5)

    def test_initialization_invalid_alpha(self):
        """Test initialization with invalid alpha."""
        with pytest.raises(ValueError, match="alpha must be in"):
            ToolSelectionPolicy(alpha=-0.1)

    def test_select_tool_empty_list(self, policy):
        """Test selection with empty tool list raises error."""
        with pytest.raises(ValueError, match="available_tools cannot be empty"):
            policy.select_tool("task", [])

    def test_select_tool_exploitation(self, policy):
        """Test exploitation mode selects best Q-value."""
        # Set Q-values
        policy.q_values[("search", "general")] = 2.0
        policy.q_values[("grep", "general")] = 1.0
        policy.q_values[("find", "general")] = 0.5

        # Force exploitation (epsilon=0)
        policy.epsilon = 0.0

        tool = policy.select_tool("general task", ["search", "grep", "find"])

        assert tool == "search"  # Highest Q-value

    def test_select_tool_with_context(self, policy):
        """Test tool selection with explicit context."""
        policy.q_values[("search", "search_task")] = 2.0
        policy.q_values[("grep", "search_task")] = 1.0

        policy.epsilon = 0.0  # Force exploitation

        tool = policy.select_tool("find files", ["search", "grep"], context="search_task")

        assert tool == "search"

    def test_update_q_value(self, policy):
        """Test Q-value update with Q-learning rule."""
        initial_q = policy.get_q_value("tool", "context")
        assert initial_q == 0.0  # Default

        # Update with reward
        policy.update_q_value("tool", "context", reward=1.5)

        # Q(s,a) ← Q(s,a) + α[R - Q(s,a)]
        # Q = 0.0 + 0.1[1.5 - 0.0] = 0.15
        expected_q = 0.0 + 0.1 * (1.5 - 0.0)
        assert policy.get_q_value("tool", "context") == pytest.approx(expected_q)

    def test_update_q_value_multiple_times(self, policy):
        """Test Q-value converges with multiple updates."""
        # Update same tool multiple times with reward=1.0
        for _ in range(10):
            policy.update_q_value("tool", "context", reward=1.0)

        # Q-value should approach 1.0
        q_value = policy.get_q_value("tool", "context")
        assert q_value > 0.5  # Should be converging towards 1.0
        assert q_value < 1.0  # But not quite there yet

    def test_update_q_value_increments_count(self, policy):
        """Test execution count increments with updates."""
        assert policy.get_execution_count("tool", "context") == 0

        policy.update_q_value("tool", "context", reward=1.0)
        assert policy.get_execution_count("tool", "context") == 1

        policy.update_q_value("tool", "context", reward=0.5)
        assert policy.get_execution_count("tool", "context") == 2

    def test_epsilon_decay(self, policy):
        """Test epsilon decays after updates."""
        initial_epsilon = policy.epsilon

        policy.update_q_value("tool", "context", reward=1.0)

        assert policy.epsilon < initial_epsilon
        assert policy.epsilon >= policy.min_epsilon

    def test_epsilon_min_threshold(self, policy):
        """Test epsilon doesn't decay below minimum."""
        policy.min_epsilon = 0.01

        # Perform many updates to force decay
        for _ in range(1000):
            policy.update_q_value("tool", "context", reward=1.0)

        assert policy.epsilon >= policy.min_epsilon

    def test_get_best_tool(self, policy):
        """Test getting best tool for context."""
        policy.q_values[("search", "search_task")] = 2.0
        policy.q_values[("grep", "search_task")] = 1.5
        policy.q_values[("find", "search_task")] = 0.5

        best = policy.get_best_tool("search_task", ["search", "grep", "find"])

        assert best == "search"

    def test_get_best_tool_empty_list(self, policy):
        """Test getting best tool with empty list."""
        best = policy.get_best_tool("context", [])
        assert best is None

    def test_get_tool_statistics_specific_tool(self, policy):
        """Test getting statistics for specific tool."""
        policy.update_q_value("search", "context1", 1.0)
        policy.update_q_value("search", "context2", 0.5)

        stats = policy.get_tool_statistics("search")

        assert stats["tool"] == "search"
        assert len(stats["contexts"]) == 2
        assert stats["total_executions"] == 2
        assert "avg_q_value" in stats

    def test_get_tool_statistics_all_tools(self, policy):
        """Test getting statistics for all tools."""
        policy.update_q_value("tool1", "context", 1.0)
        policy.update_q_value("tool2", "context", 0.5)

        stats = policy.get_tool_statistics()

        assert stats["total_tools"] == 2
        assert stats["total_updates"] == 2
        assert "tools" in stats
        assert set(stats["tools"]) == {"tool1", "tool2"}

    def test_reset(self, policy):
        """Test policy reset."""
        # Add some state
        policy.update_q_value("tool", "context", 1.0)
        assert len(policy.q_values) > 0
        assert policy.total_updates > 0

        policy.reset()

        assert len(policy.q_values) == 0
        assert len(policy.counts) == 0
        assert policy.total_updates == 0
        assert policy.epsilon == 0.1  # Reset to initial

    def test_extract_context(self, policy):
        """Test context extraction from task description."""
        assert policy._extract_context("search for files") == "search"
        assert policy._extract_context("read a file") == "file_ops"
        assert policy._extract_context("execute command") == "execute"
        assert policy._extract_context("download from api") == "network"
        assert policy._extract_context("parse json data") == "data"
        assert policy._extract_context("random task") == "general"

    def test_to_dict(self, policy):
        """Test exporting policy to dictionary."""
        policy.update_q_value("tool1", "context1", 1.0)
        policy.update_q_value("tool2", "context2", 0.5)

        data = policy.to_dict()

        assert data["epsilon"] == policy.epsilon
        assert data["alpha"] == policy.alpha
        assert data["total_updates"] == 2
        assert "tool1:context1" in data["q_values"]
        assert "tool2:context2" in data["q_values"]

    def test_from_dict(self, policy):
        """Test loading policy from dictionary."""
        # Create data
        data = {
            "epsilon": 0.15,
            "alpha": 0.2,
            "gamma": 0.95,
            "total_updates": 5,
            "q_values": {
                "tool1:context1": 1.5,
                "tool2:context2": 0.8,
            },
            "counts": {
                "tool1:context1": 3,
                "tool2:context2": 2,
            },
        }

        loaded = ToolSelectionPolicy.from_dict(data)

        assert loaded.epsilon == 0.15
        assert loaded.alpha == 0.2
        assert loaded.total_updates == 5
        assert loaded.get_q_value("tool1", "context1") == 1.5
        assert loaded.get_execution_count("tool1", "context1") == 3

    def test_to_json(self, policy):
        """Test exporting policy to JSON string."""
        policy.update_q_value("tool", "context", 1.0)

        json_str = policy.to_json()

        # Should be valid JSON
        data = json.loads(json_str)
        assert "epsilon" in data
        assert "q_values" in data

    def test_from_json(self, policy):
        """Test loading policy from JSON string."""
        json_str = """
        {
            "epsilon": 0.15,
            "alpha": 0.2,
            "gamma": 0.9,
            "total_updates": 3,
            "q_values": {
                "tool:context": 1.5
            },
            "counts": {
                "tool:context": 2
            }
        }
        """

        loaded = ToolSelectionPolicy.from_json(json_str)

        assert loaded.epsilon == 0.15
        assert loaded.get_q_value("tool", "context") == 1.5
        assert loaded.get_execution_count("tool", "context") == 2

    def test_roundtrip_serialization(self, policy):
        """Test policy survives serialization roundtrip."""
        # Add state
        policy.update_q_value("tool1", "context1", 1.0)
        policy.update_q_value("tool2", "context2", 0.5)

        # Export and reload
        json_str = policy.to_json()
        loaded = ToolSelectionPolicy.from_json(json_str)

        # Verify state preserved
        assert loaded.epsilon == policy.epsilon
        assert loaded.total_updates == policy.total_updates
        assert loaded.get_q_value("tool1", "context1") == policy.get_q_value(
            "tool1", "context1"
        )
        assert loaded.get_q_value("tool2", "context2") == policy.get_q_value(
            "tool2", "context2"
        )

    def test_get_top_tools(self, policy):
        """Test getting top tools by Q-value."""
        # Directly set Q-values (not using update which applies learning rate)
        policy.q_values[("tool1", "context")] = 2.0
        policy.q_values[("tool2", "context")] = 1.5
        policy.q_values[("tool3", "context")] = 0.5

        stats = policy.get_tool_statistics()
        top_tools = stats["top_tools"]

        assert len(top_tools) <= 5
        assert top_tools[0]["tool"] == "tool1"  # Highest Q-value
        assert top_tools[0]["avg_q_value"] == 2.0
