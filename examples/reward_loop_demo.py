"""Demonstration of Tool-Execution Reward Loop.

Sprint 68 Feature 68.7: Tool-Execution Reward Loop (FEAT-007)

This script demonstrates how the reward loop learns tool preferences
through reinforcement learning.

Run:
    poetry run python examples/reward_loop_demo.py
"""

import asyncio

from src.agents.action import ActionConfig, SecureActionAgent, get_policy_persistence_manager


async def simulate_tool_executions():
    """Simulate multiple tool executions to demonstrate learning."""
    print("=" * 80)
    print("Tool-Execution Reward Loop Demo")
    print("=" * 80)
    print()

    # Create agent with reward loop enabled
    config = ActionConfig(
        enable_reward_loop=True,
        epsilon=0.2,  # 20% exploration
        alpha=0.1,  # Learning rate
        expected_duration_ms=1000.0,  # Expect 1 second
    )

    agent = SecureActionAgent(config=config)

    # Register available tools
    tools = ["search", "grep", "find", "ls", "cat"]
    agent.register_tools(tools)

    print(f"Registered Tools: {tools}")
    print(f"Initial Epsilon: {agent.policy.epsilon}")
    print(f"Learning Rate (α): {agent.policy.alpha}")
    print()

    # Simulate 20 executions
    print("Simulating 20 tool executions...")
    print()

    for i in range(1, 21):
        # Vary task types
        if i % 3 == 0:
            task = "search for files"
            context = "search"
        elif i % 3 == 1:
            task = "read a file"
            context = "file_ops"
        else:
            task = "execute command"
            context = "execute"

        # Simulate execution (using regular execute_action, not real execution)
        # In real usage, this would call execute_with_learning
        print(f"[{i:2d}] Task: '{task}' (context: {context})")

        # Get tool selection without executing
        agent.policy.epsilon = 0.0  # Force exploitation to see learned behavior
        selected_tool = agent.policy.select_tool(task, tools, context)
        print(f"     Selected Tool: {selected_tool}")

        # Simulate reward (randomize success/failure)
        import random

        reward = random.choice([1.5, 0.5, -0.5])  # Simulated rewards

        # Update Q-value
        agent.policy.update_q_value(selected_tool, context, reward)

        q_value = agent.policy.get_q_value(selected_tool, context)
        print(f"     Reward: {reward:+.1f}, Q-value: {q_value:.3f}")
        print()

    # Show learned statistics
    print("=" * 80)
    print("Learned Policy Statistics")
    print("=" * 80)
    print()

    stats = agent.get_policy_statistics()
    print(f"Total Updates: {stats['total_updates']}")
    print(f"Final Epsilon: {stats['epsilon']:.4f}")
    print()

    print("Top 3 Tools by Average Q-value:")
    for i, tool_stat in enumerate(stats["top_tools"][:3], 1):
        print(
            f"  {i}. {tool_stat['tool']}: "
            f"avg_q={tool_stat['avg_q_value']:.3f}, "
            f"contexts={tool_stat['contexts_count']}"
        )
    print()

    # Show Q-values per context
    print("Q-values by Context:")
    for tool in tools:
        tool_stats = agent.get_policy_statistics(tool)
        if tool_stats["total_executions"] > 0:
            print(f"  {tool}:")
            for context in tool_stats.get("contexts", []):
                q = agent.policy.get_q_value(tool, context)
                count = agent.policy.get_execution_count(tool, context)
                print(f"    - {context}: Q={q:.3f}, count={count}")

    print()

    # Demonstrate persistence
    print("=" * 80)
    print("Policy Persistence Demo")
    print("=" * 80)
    print()

    manager = get_policy_persistence_manager()

    # Save policy
    print("Saving policy to Redis...")
    success = await manager.save_policy("demo_agent", agent.policy)
    if success:
        print("✓ Policy saved successfully!")
    else:
        print("✗ Failed to save policy (Redis may not be running)")

    # Export policy to JSON (alternative persistence)
    policy_json = agent.policy.to_json()
    print()
    print("Policy exported to JSON (first 200 chars):")
    print(policy_json[:200] + "...")
    print()

    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)


def demonstrate_reward_calculation():
    """Demonstrate reward calculation for different scenarios."""
    from src.agents.action import ToolRewardCalculator

    print()
    print("=" * 80)
    print("Reward Calculation Examples")
    print("=" * 80)
    print()

    calculator = ToolRewardCalculator()

    scenarios = [
        {
            "name": "Perfect Execution",
            "result": {"success": True, "execution_time_ms": 100, "output": "Valid output"},
            "expected_ms": 200,
            "feedback": 1,
        },
        {
            "name": "Slow Execution",
            "result": {"success": True, "execution_time_ms": 500, "output": "Valid output"},
            "expected_ms": 200,
            "feedback": 0,
        },
        {
            "name": "Failed Execution",
            "result": {"success": False, "execution_time_ms": 100, "error": "Command failed"},
            "expected_ms": 200,
            "feedback": -1,
        },
        {
            "name": "Empty Output",
            "result": {"success": True, "execution_time_ms": 100, "output": ""},
            "expected_ms": 200,
            "feedback": 0,
        },
    ]

    for scenario in scenarios:
        print(f"Scenario: {scenario['name']}")
        print(f"  Result: {scenario['result']}")

        reward = calculator.calculate_reward(
            tool_name="demo_tool",
            execution_result=scenario["result"],
            expected_duration_ms=scenario["expected_ms"],
            user_feedback=scenario["feedback"],
        )

        print(f"  Rewards:")
        print(f"    Success:    {reward.success_reward:+.1f}")
        print(f"    Efficiency: {reward.efficiency_reward:+.1f}")
        print(f"    Quality:    {reward.quality_reward:+.1f}")
        print(f"    Feedback:   {reward.user_feedback_reward:+.1f}")
        print(f"    TOTAL:      {reward.total_reward:+.1f}")
        print()


if __name__ == "__main__":
    # Run reward calculation demo
    demonstrate_reward_calculation()

    # Run async simulation
    asyncio.run(simulate_tool_executions())
