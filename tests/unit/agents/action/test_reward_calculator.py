"""Unit tests for ToolRewardCalculator.

Sprint 68 Feature 68.7: Tool-Execution Reward Loop (FEAT-007)
Tests reward calculation for tool executions.
"""

import pytest

from src.agents.action.reward_calculator import RewardComponents, ToolRewardCalculator


class TestRewardComponents:
    """Test RewardComponents dataclass."""

    def test_total_reward_calculation(self):
        """Test total reward is sum of all components."""
        components = RewardComponents(
            success_reward=1.0,
            efficiency_reward=0.5,
            quality_reward=0.5,
            user_feedback_reward=1.0,
        )

        assert components.total_reward == 3.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        components = RewardComponents(
            success_reward=1.0,
            efficiency_reward=0.5,
            quality_reward=0.5,
            user_feedback_reward=0.0,
        )

        result = components.to_dict()

        assert result["success"] == 1.0
        assert result["efficiency"] == 0.5
        assert result["quality"] == 0.5
        assert result["user_feedback"] == 0.0
        assert result["total"] == 2.0


class TestToolRewardCalculator:
    """Test ToolRewardCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return ToolRewardCalculator()

    def test_initialization(self):
        """Test calculator initialization."""
        calculator = ToolRewardCalculator(efficiency_threshold=1.2)

        assert calculator.efficiency_threshold == 1.2
        assert calculator.quality_checks == {}

    def test_successful_execution_reward(self, calculator):
        """Test reward for successful execution."""
        result = {
            "success": True,
            "execution_time_ms": 100,
            "output": "OK",
        }

        reward = calculator.calculate_reward("tool", result, 200)

        assert reward.success_reward == 1.0
        assert reward.total_reward > 0

    def test_failed_execution_reward(self, calculator):
        """Test reward for failed execution."""
        result = {
            "success": False,
            "execution_time_ms": 100,
            "error": "Command failed",
        }

        reward = calculator.calculate_reward("tool", result, 200)

        assert reward.success_reward == -1.0
        assert reward.efficiency_reward == 0.0  # No efficiency reward for failure
        assert reward.quality_reward == 0.0  # No quality reward for failure

    def test_efficiency_reward_fast_execution(self, calculator):
        """Test efficiency reward for fast execution."""
        result = {
            "success": True,
            "execution_time_ms": 50,  # Fast
            "output": "OK",
        }

        reward = calculator.calculate_reward("tool", result, expected_duration_ms=200)

        assert reward.efficiency_reward > 0
        assert reward.efficiency_reward <= 0.5

    def test_efficiency_reward_slow_execution(self, calculator):
        """Test no efficiency reward for slow execution."""
        result = {
            "success": True,
            "execution_time_ms": 250,  # Slow
            "output": "OK",
        }

        reward = calculator.calculate_reward("tool", result, expected_duration_ms=200)

        assert reward.efficiency_reward == 0.0

    def test_quality_reward_default_check(self, calculator):
        """Test default quality check (non-empty output)."""
        result = {
            "success": True,
            "execution_time_ms": 100,
            "output": "Valid output",
        }

        reward = calculator.calculate_reward("tool", result, 200)

        assert reward.quality_reward == 0.5

    def test_quality_reward_empty_output(self, calculator):
        """Test no quality reward for empty output."""
        result = {
            "success": True,
            "execution_time_ms": 100,
            "output": "",
        }

        reward = calculator.calculate_reward("tool", result, 200)

        assert reward.quality_reward == 0.0

    def test_quality_reward_custom_function(self, calculator):
        """Test custom quality check function."""
        calculator.set_quality_check("search", lambda x: "result" in x)

        # Should pass
        result = {"success": True, "execution_time_ms": 100, "output": "result found"}
        reward = calculator.calculate_reward("search", result, 200)
        assert reward.quality_reward == 0.5

        # Should fail
        result = {"success": True, "execution_time_ms": 100, "output": "nothing here"}
        reward = calculator.calculate_reward("search", result, 200)
        assert reward.quality_reward == 0.0

    def test_quality_reward_custom_dict(self, calculator):
        """Test custom quality check with dictionary."""
        calculator.set_quality_check(
            "parse",
            {
                "required_fields": ["data", "status"],
                "min_length": 10,
            },
        )

        # Valid output
        result = {
            "success": True,
            "execution_time_ms": 100,
            "output": {"data": "test", "status": "ok", "extra": "field"},
        }
        reward = calculator.calculate_reward("parse", result, 200)
        assert reward.quality_reward == 0.5

        # Missing required field
        result = {
            "success": True,
            "execution_time_ms": 100,
            "output": {"data": "test"},  # Missing 'status'
        }
        reward = calculator.calculate_reward("parse", result, 200)
        assert reward.quality_reward == 0.0

    def test_user_feedback_positive(self, calculator):
        """Test positive user feedback reward."""
        result = {"success": True, "execution_time_ms": 100, "output": "OK"}

        reward = calculator.calculate_reward("tool", result, 200, user_feedback=1)

        assert reward.user_feedback_reward == 1.0

    def test_user_feedback_negative(self, calculator):
        """Test negative user feedback reward."""
        result = {"success": True, "execution_time_ms": 100, "output": "OK"}

        reward = calculator.calculate_reward("tool", result, 200, user_feedback=-1)

        assert reward.user_feedback_reward == -1.0

    def test_user_feedback_neutral(self, calculator):
        """Test neutral user feedback."""
        result = {"success": True, "execution_time_ms": 100, "output": "OK"}

        reward = calculator.calculate_reward("tool", result, 200, user_feedback=0)

        assert reward.user_feedback_reward == 0.0

    def test_user_feedback_none(self, calculator):
        """Test no user feedback."""
        result = {"success": True, "execution_time_ms": 100, "output": "OK"}

        reward = calculator.calculate_reward("tool", result, 200, user_feedback=None)

        assert reward.user_feedback_reward == 0.0

    def test_combined_reward_best_case(self, calculator):
        """Test combined reward for best-case execution."""
        result = {
            "success": True,
            "execution_time_ms": 50,  # Fast
            "output": "Valid output",
        }

        reward = calculator.calculate_reward("tool", result, 200, user_feedback=1)

        # Success (1.0) + Efficiency (~0.5) + Quality (0.5) + Feedback (1.0)
        assert reward.total_reward > 2.5
        assert reward.total_reward <= 3.0

    def test_combined_reward_worst_case(self, calculator):
        """Test combined reward for worst-case execution."""
        result = {
            "success": False,
            "execution_time_ms": 500,  # Slow
            "error": "Failed",
        }

        reward = calculator.calculate_reward("tool", result, 200, user_feedback=-1)

        # Failure (-1.0) + No efficiency (0.0) + No quality (0.0) + Negative feedback (-1.0)
        assert reward.total_reward == -2.0

    def test_set_quality_check(self, calculator):
        """Test setting quality check for tool."""
        check_func = lambda x: len(x) > 10

        calculator.set_quality_check("tool", check_func)

        assert "tool" in calculator.quality_checks
        assert calculator.quality_checks["tool"] == check_func

    def test_remove_quality_check(self, calculator):
        """Test removing quality check."""
        calculator.set_quality_check("tool", lambda x: True)
        calculator.remove_quality_check("tool")

        assert "tool" not in calculator.quality_checks

    def test_remove_nonexistent_quality_check(self, calculator):
        """Test removing nonexistent quality check (should not error)."""
        calculator.remove_quality_check("nonexistent")
        # Should not raise exception
