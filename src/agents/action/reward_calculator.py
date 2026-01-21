"""Tool Execution Reward Calculator.

Sprint 68 Feature 68.7: Tool-Execution Reward Loop (FEAT-007)
Calculates rewards for tool executions based on multiple signals.

Reward Components:
- Success/Failure: Did the tool execute without errors? (+1/-1)
- Efficiency: Was execution time within expected range? (+0.5)
- Output Quality: Does output match expected format? (+0.5)
- User Feedback: Explicit thumbs up/down from user? (+1/-1)

Architecture:
Based on Paper 2512.16301 (Tool-Level Adaptation) reinforcement learning approach.
"""

from dataclasses import dataclass
from typing import Any

import structlog

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RewardComponents:
    """Individual components of a reward signal.

    Attributes:
        success_reward: Reward for execution success/failure (+1/-1)
        efficiency_reward: Reward for execution efficiency (+0.5/0)
        quality_reward: Reward for output quality (+0.5/0)
        user_feedback_reward: Reward from user feedback (+1/-1/0)
        total_reward: Sum of all components
    """

    success_reward: float
    efficiency_reward: float
    quality_reward: float
    user_feedback_reward: float

    @property
    def total_reward(self) -> float:
        """Calculate total reward from all components."""
        return (
            self.success_reward
            + self.efficiency_reward
            + self.quality_reward
            + self.user_feedback_reward
        )

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for logging."""
        return {
            "success": self.success_reward,
            "efficiency": self.efficiency_reward,
            "quality": self.quality_reward,
            "user_feedback": self.user_feedback_reward,
            "total": self.total_reward,
        }


class ToolRewardCalculator:
    """Calculate rewards for tool executions.

    Implements multi-component reward calculation for reinforcement learning
    based tool selection optimization.

    Features:
    - Success/failure detection
    - Execution time efficiency
    - Output quality validation
    - User feedback integration

    Example:
        >>> calculator = ToolRewardCalculator()
        >>> result = {"success": True, "execution_time_ms": 150, "output": "..."}
        >>> reward = calculator.calculate_reward("search_tool", result, expected_duration=200)
        >>> print(reward.total_reward)  # 2.5 (success + efficiency + quality)
    """

    def __init__(
        self,
        efficiency_threshold: float = 1.0,
        quality_checks: dict[str, Any] | None = None,
    ) -> None:
        """Initialize reward calculator.

        Args:
            efficiency_threshold: Multiplier for expected duration (default: 1.0)
            quality_checks: Custom quality validation rules per tool
        """
        self.logger = structlog.get_logger(__name__)
        self.efficiency_threshold = efficiency_threshold
        self.quality_checks = quality_checks or {}

        self.logger.info(
            "reward_calculator_initialized",
            efficiency_threshold=efficiency_threshold,
            quality_checks_count=len(self.quality_checks),
        )

    def calculate_reward(
        self,
        tool_name: str,
        execution_result: dict[str, Any],
        expected_duration_ms: float,
        user_feedback: int | None = None,
    ) -> RewardComponents:
        """Calculate reward for a tool execution.

        Args:
            tool_name: Name of the executed tool
            execution_result: Result dictionary with keys:
                - success: Whether execution succeeded (bool)
                - execution_time_ms: Execution time in milliseconds (float)
                - output: Tool output (str, optional)
                - error: Error message if failed (str, optional)
            expected_duration_ms: Expected execution duration in milliseconds
            user_feedback: Optional user feedback (-1, 0, +1)

        Returns:
            RewardComponents with individual and total rewards

        Example:
            >>> result = {"success": True, "execution_time_ms": 100, "output": "OK"}
            >>> reward = calculator.calculate_reward("tool", result, 200)
            >>> assert reward.total_reward > 0
        """
        # Success/failure reward
        success_reward = self._calculate_success_reward(execution_result)

        # Efficiency reward
        efficiency_reward = self._calculate_efficiency_reward(
            execution_result, expected_duration_ms
        )

        # Output quality reward
        quality_reward = self._calculate_quality_reward(tool_name, execution_result)

        # User feedback reward
        user_feedback_reward = self._calculate_user_feedback_reward(user_feedback)

        components = RewardComponents(
            success_reward=success_reward,
            efficiency_reward=efficiency_reward,
            quality_reward=quality_reward,
            user_feedback_reward=user_feedback_reward,
        )

        self.logger.info(
            "reward_calculated",
            tool=tool_name,
            components=components.to_dict(),
            total=components.total_reward,
        )

        return components

    def _calculate_success_reward(self, execution_result: dict[str, Any]) -> float:
        """Calculate reward based on execution success.

        Args:
            execution_result: Execution result dictionary

        Returns:
            +1.0 for success, -1.0 for failure
        """
        if execution_result.get("success", False):
            return 1.0
        return -1.0

    def _calculate_efficiency_reward(
        self, execution_result: dict[str, Any], expected_duration_ms: float
    ) -> float:
        """Calculate reward based on execution efficiency.

        Rewards executions that complete faster than expected duration.

        Args:
            execution_result: Execution result dictionary
            expected_duration_ms: Expected duration in milliseconds

        Returns:
            +0.5 if execution time < threshold * expected, 0.0 otherwise
        """
        execution_time = execution_result.get("execution_time_ms", float("inf"))

        # Only reward if execution succeeded
        if not execution_result.get("success", False):
            return 0.0

        threshold = expected_duration_ms * self.efficiency_threshold

        if execution_time < threshold:
            # Calculate bonus based on how much faster it was
            speedup = 1.0 - (execution_time / threshold)
            return 0.5 * speedup
        return 0.0

    def _calculate_quality_reward(self, tool_name: str, execution_result: dict[str, Any]) -> float:
        """Calculate reward based on output quality.

        Validates output format and content based on tool-specific rules.

        Args:
            tool_name: Name of the tool
            execution_result: Execution result dictionary

        Returns:
            +0.5 if output passes quality checks, 0.0 otherwise
        """
        # Only check quality if execution succeeded
        if not execution_result.get("success", False):
            return 0.0

        output = execution_result.get("output", "")

        # Tool-specific quality checks
        quality_check = self.quality_checks.get(tool_name)
        if quality_check:
            if callable(quality_check):
                if quality_check(output):
                    return 0.5
            elif isinstance(quality_check, dict):
                # Check for expected fields/patterns
                checks_passed = self._validate_quality_dict(output, quality_check)
                if checks_passed:
                    return 0.5
            return 0.0

        # Default quality check: non-empty output
        if output and len(str(output).strip()) > 0:
            return 0.5

        return 0.0

    def _validate_quality_dict(self, output: Any, quality_check: dict[str, Any]) -> bool:
        """Validate output against quality check dictionary.

        Args:
            output: Tool output
            quality_check: Dictionary with validation rules

        Returns:
            True if all checks pass
        """
        # Check for required fields
        if "required_fields" in quality_check and isinstance(output, dict):
            required = quality_check["required_fields"]
            if not all(field in output for field in required):
                return False

        # Check for patterns in string output
        if "patterns" in quality_check and isinstance(output, str):
            patterns = quality_check["patterns"]
            if not all(pattern in output for pattern in patterns):
                return False

        # Check minimum length
        if "min_length" in quality_check:
            if len(str(output)) < quality_check["min_length"]:
                return False

        return True

    def _calculate_user_feedback_reward(self, user_feedback: int | None) -> float:
        """Calculate reward from user feedback.

        Args:
            user_feedback: User feedback signal (-1, 0, +1, or None)

        Returns:
            +1.0 for positive, -1.0 for negative, 0.0 for neutral/None
        """
        if user_feedback is None:
            return 0.0

        # Clamp feedback to [-1, 1]
        feedback = max(-1, min(1, user_feedback))
        return float(feedback)

    def set_quality_check(self, tool_name: str, quality_check: Any) -> None:
        """Set quality check for a specific tool.

        Args:
            tool_name: Name of the tool
            quality_check: Quality check function or dictionary

        Example:
            >>> calculator.set_quality_check("search", {"min_length": 10})
            >>> calculator.set_quality_check("parse", lambda x: "error" not in x)
        """
        self.quality_checks[tool_name] = quality_check
        self.logger.info("quality_check_set", tool=tool_name)

    def remove_quality_check(self, tool_name: str) -> None:
        """Remove quality check for a specific tool.

        Args:
            tool_name: Name of the tool
        """
        if tool_name in self.quality_checks:
            del self.quality_checks[tool_name]
            self.logger.info("quality_check_removed", tool=tool_name)
