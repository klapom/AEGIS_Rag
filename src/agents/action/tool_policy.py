"""Tool Selection Policy with Reinforcement Learning.

Sprint 68 Feature 68.7: Tool-Execution Reward Loop (FEAT-007)
Implements ε-greedy policy for tool selection with Q-learning updates.

Architecture:
- ε-greedy exploration/exploitation
- Q-learning updates with learning rate α
- Contextual tool selection (task-aware)
- Execution count tracking
- Redis persistence for Q-values

Based on Paper 2512.16301 (Tool-Level Adaptation).
"""

import json
import random
from collections import defaultdict
from typing import Any

import structlog

from src.core.logging import get_logger

logger = get_logger(__name__)


class ToolSelectionPolicy:
    """Q-learning based policy for tool selection.

    Uses ε-greedy strategy to balance exploration (trying new tools)
    and exploitation (using best-performing tools).

    Features:
    - ε-greedy tool selection
    - Q-learning value updates
    - Execution count tracking
    - Context-aware selection (task type)
    - State persistence to Redis

    Example:
        >>> policy = ToolSelectionPolicy(epsilon=0.1, alpha=0.1)
        >>> tool = policy.select_tool("search task", ["search", "grep", "find"])
        >>> reward = 1.5  # From ToolRewardCalculator
        >>> policy.update_q_value("search", "search_task", reward)
    """

    def __init__(
        self,
        epsilon: float = 0.1,
        alpha: float = 0.1,
        gamma: float = 0.9,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.01,
    ) -> None:
        """Initialize tool selection policy.

        Args:
            epsilon: Exploration rate (0.0 = pure exploitation, 1.0 = pure exploration)
            alpha: Learning rate for Q-value updates (0.0-1.0)
            gamma: Discount factor for future rewards (0.0-1.0)
            epsilon_decay: Decay rate for epsilon after each update
            min_epsilon: Minimum epsilon value (prevents too little exploration)

        Raises:
            ValueError: If parameters are out of valid range
        """
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError(f"epsilon must be in [0, 1], got {epsilon}")
        if not 0.0 <= alpha <= 1.0:
            raise ValueError(f"alpha must be in [0, 1], got {alpha}")
        if not 0.0 <= gamma <= 1.0:
            raise ValueError(f"gamma must be in [0, 1], got {gamma}")

        self.logger = structlog.get_logger(__name__)

        # Policy parameters
        self.epsilon = epsilon
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon

        # Q-values: (tool, context) -> Q-value
        self.q_values: dict[tuple[str, str], float] = defaultdict(float)

        # Execution counts: (tool, context) -> count
        self.counts: dict[tuple[str, str], int] = defaultdict(int)

        # Total updates counter
        self.total_updates = 0

        self.logger.info(
            "tool_policy_initialized",
            epsilon=epsilon,
            alpha=alpha,
            gamma=gamma,
            epsilon_decay=epsilon_decay,
            min_epsilon=min_epsilon,
        )

    def select_tool(
        self, task: str, available_tools: list[str], context: str | None = None
    ) -> str:
        """Select tool using ε-greedy policy.

        With probability ε, selects random tool (exploration).
        With probability 1-ε, selects tool with highest Q-value (exploitation).

        Args:
            task: Task description for logging
            available_tools: List of available tool names
            context: Optional context key for task type (e.g., "search", "file_ops")

        Returns:
            Selected tool name

        Raises:
            ValueError: If available_tools is empty

        Example:
            >>> tools = ["search", "grep", "find"]
            >>> tool = policy.select_tool("find files", tools, context="search")
        """
        if not available_tools:
            raise ValueError("available_tools cannot be empty")

        # Use task type as context if not provided
        if context is None:
            context = self._extract_context(task)

        # Exploration: Random tool
        if random.random() < self.epsilon:
            tool = random.choice(available_tools)
            self.logger.info(
                "tool_selected_exploration",
                tool=tool,
                context=context,
                epsilon=self.epsilon,
                available_count=len(available_tools),
            )
            return tool

        # Exploitation: Best Q-value
        tool_scores = {
            tool: self.q_values[(tool, context)] for tool in available_tools
        }

        best_tool = max(tool_scores, key=tool_scores.get)
        best_q_value = tool_scores[best_tool]

        self.logger.info(
            "tool_selected_exploitation",
            tool=best_tool,
            context=context,
            q_value=best_q_value,
            all_scores=tool_scores,
        )

        return best_tool

    def update_q_value(self, tool: str, context: str, reward: float) -> None:
        """Update Q-value using Q-learning update rule.

        Q(s, a) ← Q(s, a) + α[R - Q(s, a)]

        Where:
        - Q(s, a) is the Q-value for state s, action a
        - α is the learning rate
        - R is the observed reward

        Args:
            tool: Tool name (action)
            context: Context/task type (state)
            reward: Observed reward from execution

        Example:
            >>> policy.update_q_value("search", "search_task", reward=1.5)
            >>> policy.update_q_value("grep", "search_task", reward=-0.5)
        """
        key = (tool, context)
        old_q = self.q_values[key]

        # Q-learning update: Q(s,a) ← Q(s,a) + α[R - Q(s,a)]
        new_q = old_q + self.alpha * (reward - old_q)

        self.q_values[key] = new_q
        self.counts[key] += 1
        self.total_updates += 1

        # Decay epsilon (reduce exploration over time)
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

        self.logger.info(
            "q_value_updated",
            tool=tool,
            context=context,
            old_q=old_q,
            new_q=new_q,
            reward=reward,
            count=self.counts[key],
            epsilon=self.epsilon,
            total_updates=self.total_updates,
        )

    def get_q_value(self, tool: str, context: str) -> float:
        """Get Q-value for tool in given context.

        Args:
            tool: Tool name
            context: Context/task type

        Returns:
            Q-value (0.0 if not seen before)
        """
        return self.q_values.get((tool, context), 0.0)

    def get_execution_count(self, tool: str, context: str) -> int:
        """Get execution count for tool in given context.

        Args:
            tool: Tool name
            context: Context/task type

        Returns:
            Execution count (0 if not seen before)
        """
        return self.counts.get((tool, context), 0)

    def get_best_tool(self, context: str, available_tools: list[str]) -> str | None:
        """Get tool with highest Q-value for given context.

        Args:
            context: Context/task type
            available_tools: List of available tool names

        Returns:
            Tool with highest Q-value, or None if no tools available
        """
        if not available_tools:
            return None

        tool_scores = {
            tool: self.q_values.get((tool, context), 0.0) for tool in available_tools
        }

        return max(tool_scores, key=tool_scores.get)

    def get_tool_statistics(self, tool: str | None = None) -> dict[str, Any]:
        """Get statistics for tool(s).

        Args:
            tool: Optional tool name (if None, returns stats for all tools)

        Returns:
            Dictionary with statistics
        """
        if tool:
            # Statistics for specific tool
            contexts = [ctx for (t, ctx) in self.q_values.keys() if t == tool]
            if not contexts:
                return {"tool": tool, "contexts": [], "total_executions": 0}

            return {
                "tool": tool,
                "contexts": contexts,
                "q_values": {ctx: self.q_values[(tool, ctx)] for ctx in contexts},
                "counts": {ctx: self.counts[(tool, ctx)] for ctx in contexts},
                "total_executions": sum(self.counts[(tool, ctx)] for ctx in contexts),
                "avg_q_value": sum(self.q_values[(tool, ctx)] for ctx in contexts)
                / len(contexts),
            }

        # Statistics for all tools
        all_tools = set(tool for (tool, _) in self.q_values.keys())

        return {
            "total_tools": len(all_tools),
            "total_contexts": len(set(ctx for (_, ctx) in self.q_values.keys())),
            "total_updates": self.total_updates,
            "epsilon": self.epsilon,
            "tools": list(all_tools),
            "top_tools": self._get_top_tools(5),
        }

    def _get_top_tools(self, top_n: int = 5) -> list[dict[str, Any]]:
        """Get top N tools by average Q-value.

        Args:
            top_n: Number of top tools to return

        Returns:
            List of top tools with statistics
        """
        # Calculate average Q-value per tool across all contexts
        tool_avg_q = defaultdict(list)
        for (tool, context), q_value in self.q_values.items():
            tool_avg_q[tool].append(q_value)

        tool_stats = [
            {
                "tool": tool,
                "avg_q_value": sum(q_values) / len(q_values),
                "contexts_count": len(q_values),
            }
            for tool, q_values in tool_avg_q.items()
        ]

        # Sort by average Q-value
        tool_stats.sort(key=lambda x: x["avg_q_value"], reverse=True)

        return tool_stats[:top_n]

    def reset(self) -> None:
        """Reset policy to initial state.

        Clears all Q-values, counts, and resets epsilon.
        """
        self.q_values.clear()
        self.counts.clear()
        self.total_updates = 0
        self.epsilon = 0.1  # Reset to initial value

        self.logger.info("policy_reset")

    def _extract_context(self, task: str) -> str:
        """Extract context from task description.

        Maps task descriptions to context categories for Q-value lookup.

        Args:
            task: Task description

        Returns:
            Context category string
        """
        task_lower = task.lower()

        # Define context keywords
        context_keywords = {
            "search": ["search", "find", "grep", "query", "lookup"],
            "file_ops": ["read", "write", "file", "edit", "create", "save"],
            "execute": ["run", "execute", "exec", "command", "shell"],
            "network": ["http", "request", "fetch", "api", "download"],
            "data": ["parse", "extract", "transform", "convert"],
        }

        # Match task to context
        for context, keywords in context_keywords.items():
            if any(keyword in task_lower for keyword in keywords):
                return context

        # Default context
        return "general"

    def to_dict(self) -> dict[str, Any]:
        """Export policy state to dictionary.

        Returns:
            Dictionary with policy state for persistence
        """
        return {
            "epsilon": self.epsilon,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "epsilon_decay": self.epsilon_decay,
            "min_epsilon": self.min_epsilon,
            "total_updates": self.total_updates,
            "q_values": {f"{tool}:{ctx}": q for (tool, ctx), q in self.q_values.items()},
            "counts": {f"{tool}:{ctx}": c for (tool, ctx), c in self.counts.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolSelectionPolicy":
        """Load policy state from dictionary.

        Args:
            data: Dictionary with policy state

        Returns:
            ToolSelectionPolicy instance with loaded state
        """
        policy = cls(
            epsilon=data["epsilon"],
            alpha=data["alpha"],
            gamma=data.get("gamma", 0.9),
            epsilon_decay=data.get("epsilon_decay", 0.995),
            min_epsilon=data.get("min_epsilon", 0.01),
        )

        policy.total_updates = data.get("total_updates", 0)

        # Load Q-values
        for key, q_value in data.get("q_values", {}).items():
            tool, context = key.split(":", 1)
            policy.q_values[(tool, context)] = q_value

        # Load counts
        for key, count in data.get("counts", {}).items():
            tool, context = key.split(":", 1)
            policy.counts[(tool, context)] = count

        return policy

    def to_json(self) -> str:
        """Export policy state to JSON string.

        Returns:
            JSON string with policy state
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ToolSelectionPolicy":
        """Load policy state from JSON string.

        Args:
            json_str: JSON string with policy state

        Returns:
            ToolSelectionPolicy instance with loaded state
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
