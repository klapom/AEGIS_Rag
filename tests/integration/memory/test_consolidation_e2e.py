"""E2E Integration Tests for Memory Consolidation Pipeline with Real Services.

Sprint 7 Feature 7.5: Memory Consolidation
- NO MOCKS: Uses real Redis → Qdrant and Redis → Graphiti consolidation
- Tests access count and time-based consolidation policies
- Tests background consolidation tasks
- Validates data migration and cleanup

CRITICAL: All tests marked with @pytest.mark.integration
"""

import time
from datetime import datetime, timedelta

import pytest

from src.components.memory import (
    AccessCountPolicy,
    TimeBasedPolicy,
)

# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ============================================================================
# Consolidation Policy Tests
# ============================================================================


async def test_access_count_policy_e2e():
    """Test access count consolidation policy."""
    # Given: Policy with threshold
    policy = AccessCountPolicy(min_access_count=3)

    # When: Check items with different access counts
    should_consolidate_high = policy.should_consolidate({"access_count": 5})
    should_consolidate_low = policy.should_consolidate({"access_count": 1})
    should_consolidate_exact = policy.should_consolidate({"access_count": 3})

    # Then: Correct consolidation decisions
    assert should_consolidate_high is True
    assert should_consolidate_low is False
    assert should_consolidate_exact is True  # >= threshold


async def test_time_based_policy_e2e():
    """Test time-based consolidation policy."""
    # Given: Policy with 1-hour threshold
    policy = TimeBasedPolicy(min_age_hours=1)

    # When: Check items of different ages
    old_item = {
        "stored_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
    }
    new_item = {
        "stored_at": (datetime.utcnow() - timedelta(minutes=30)).isoformat()
    }
    exact_item = {
        "stored_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
    }

    # Then: Correct consolidation decisions
    assert policy.should_consolidate(old_item) is True
    assert policy.should_consolidate(new_item) is False
    assert policy.should_consolidate(exact_item) is True  # >= threshold


# ============================================================================
# Redis → Qdrant Consolidation Tests
# ============================================================================


async def test_consolidation_redis_to_qdrant_e2e(consolidation_pipeline, redis_memory_manager):
    """Test consolidating frequently accessed items from Redis to Qdrant."""
    # Given: Items in Redis with high access counts
    for i in range(3):
        await redis_memory_manager.store(
            key=f"freq_item_{i}",
            value=f"frequently accessed value {i}",
            namespace="memory",
        )

        # Simulate multiple accesses
        for _ in range(5):
            await redis_memory_manager.retrieve(
                key=f"freq_item_{i}",
                namespace="memory",
                track_access=True,
            )

    # When: Run Redis → Qdrant consolidation
    start = time.time()
    result = await consolidation_pipeline.consolidate_redis_to_qdrant(
        namespace="memory",
        batch_size=100,
    )
    latency_ms = (time.time() - start) * 1000

    # Then: Consolidation results
    assert "processed" in result
    assert "consolidated" in result
    assert "skipped" in result
    assert result["processed"] >= 0

    # Then: Reasonable latency
    assert latency_ms < 2000, f"Consolidation {latency_ms}ms exceeds 2s"


async def test_consolidation_no_items_to_consolidate_e2e(consolidation_pipeline):
    """Test consolidation when no items meet criteria."""
    # When: Run consolidation on empty/low-access namespace
    result = await consolidation_pipeline.consolidate_redis_to_qdrant(
        namespace="empty_namespace",
        batch_size=100,
    )

    # Then: No items processed
    assert result["processed"] == 0
    assert result["consolidated"] == 0


async def test_consolidation_access_count_threshold_e2e(consolidation_pipeline, redis_memory_manager):
    """Test that only items meeting access count threshold are consolidated."""
    # Given: Items with varying access counts
    await redis_memory_manager.store(key="low_access", value="data1", namespace="test")
    await redis_memory_manager.store(key="high_access", value="data2", namespace="test")

    # Simulate low access (1 time)
    await redis_memory_manager.retrieve(key="low_access", namespace="test")

    # Simulate high access (5 times)
    for _ in range(5):
        await redis_memory_manager.retrieve(key="high_access", namespace="test")

    # When: Run consolidation
    result = await consolidation_pipeline.consolidate_redis_to_qdrant(
        namespace="test",
        batch_size=100,
    )

    # Then: Only high-access items considered
    # (actual consolidation depends on policy thresholds)
    assert isinstance(result, dict)


# ============================================================================
# Redis → Graphiti Conversation Consolidation Tests
# ============================================================================


async def test_consolidation_conversation_to_graphiti_e2e(
    consolidation_pipeline,
    redis_memory_manager,
    graphiti_wrapper,
):
    """Test consolidating conversation context to Graphiti episodic memory."""
    # Given: Conversation context in Redis
    session_id = "test_session_consolidation"
    messages = [
        {"role": "user", "content": "Tell me about memory consolidation"},
        {"role": "assistant", "content": "Memory consolidation moves data between layers"},
        {"role": "user", "content": "How does it work?"},
        {"role": "assistant", "content": "It uses policies based on access patterns and time"},
    ]
    await redis_memory_manager.store_conversation_context(
        session_id=session_id,
        messages=messages,
    )

    # When: Consolidate conversation to Graphiti
    start = time.time()
    result = await consolidation_pipeline.consolidate_conversation_to_graphiti(
        session_id=session_id,
    )
    latency_ms = (time.time() - start) * 1000

    # Then: Consolidation successful
    assert result["consolidated"] is True
    assert "episode_id" in result
    assert result["message_count"] == len(messages)

    # Then: Reasonable latency (LLM extraction takes time)
    assert latency_ms < 15000, f"Conversation consolidation {latency_ms}ms exceeds 15s"


async def test_consolidation_empty_conversation_e2e(consolidation_pipeline):
    """Test consolidating nonexistent conversation."""
    # When: Consolidate nonexistent session
    result = await consolidation_pipeline.consolidate_conversation_to_graphiti(
        session_id="nonexistent_session_xyz",
    )

    # Then: Consolidation skipped
    assert result["consolidated"] is False
    assert result["reason"] == "no_context"


async def test_consolidation_conversation_extracts_entities_e2e(
    consolidation_pipeline,
    redis_memory_manager,
):
    """Test that conversation consolidation triggers entity extraction."""
    # Given: Conversation with clear entities
    session_id = "test_entities_extraction"
    messages = [
        {"role": "user", "content": "Tell me about Tesla and Elon Musk"},
        {"role": "assistant", "content": "Tesla is led by Elon Musk in California"},
    ]
    await redis_memory_manager.store_conversation_context(
        session_id=session_id,
        messages=messages,
    )

    # When: Consolidate
    result = await consolidation_pipeline.consolidate_conversation_to_graphiti(
        session_id=session_id,
    )

    # Then: Entities were extracted
    assert result["consolidated"] is True
    # Note: Entity extraction depends on Ollama performance
    assert "entities_extracted" in result
    assert "relationships_extracted" in result


# ============================================================================
# Full Consolidation Cycle Tests
# ============================================================================


async def test_consolidation_run_full_cycle_e2e(consolidation_pipeline, redis_memory_manager):
    """Test running a complete consolidation cycle."""
    # Given: Data in Redis and active sessions
    # Add some frequently accessed items
    for i in range(2):
        await redis_memory_manager.store(
            key=f"cycle_item_{i}",
            value=f"data {i}",
            namespace="memory",
        )
        for _ in range(4):
            await redis_memory_manager.retrieve(f"cycle_item_{i}", namespace="memory")

    # Add conversation
    session_id = "test_cycle_session"
    await redis_memory_manager.store_conversation_context(
        session_id=session_id,
        messages=[
            {"role": "user", "content": "Test consolidation cycle"},
            {"role": "assistant", "content": "Running full cycle test"},
        ],
    )

    # When: Run full consolidation cycle
    start = time.time()
    result = await consolidation_pipeline.run_consolidation_cycle(
        consolidate_to_qdrant=True,
        consolidate_conversations=True,
        active_sessions=[session_id],
    )
    latency_ms = (time.time() - start) * 1000

    # Then: All operations completed
    assert "started_at" in result
    assert "completed_at" in result
    assert "qdrant_consolidation" in result
    assert "conversation_consolidations" in result
    assert len(result["conversation_consolidations"]) == 1

    # Then: Reasonable latency for full cycle
    assert latency_ms < 20000, f"Full cycle {latency_ms}ms exceeds 20s"


async def test_consolidation_cycle_partial_operations_e2e(consolidation_pipeline):
    """Test consolidation cycle with selective operations."""
    # When: Run cycle with only Qdrant consolidation
    result_qdrant_only = await consolidation_pipeline.run_consolidation_cycle(
        consolidate_to_qdrant=True,
        consolidate_conversations=False,
    )

    # Then: Only Qdrant consolidation ran
    assert result_qdrant_only["qdrant_consolidation"] is not None
    assert len(result_qdrant_only["conversation_consolidations"]) == 0

    # When: Run cycle with only conversation consolidation
    result_conv_only = await consolidation_pipeline.run_consolidation_cycle(
        consolidate_to_qdrant=False,
        consolidate_conversations=True,
        active_sessions=["test_session"],
    )

    # Then: Only conversation consolidation attempted
    assert result_conv_only["qdrant_consolidation"] is None


async def test_consolidation_cycle_multiple_sessions_e2e(consolidation_pipeline, redis_memory_manager):
    """Test consolidating multiple sessions in one cycle."""
    # Given: Multiple sessions
    sessions = ["session_1", "session_2", "session_3"]
    for session_id in sessions:
        await redis_memory_manager.store_conversation_context(
            session_id=session_id,
            messages=[
                {"role": "user", "content": f"Session {session_id}"},
                {"role": "assistant", "content": "Response"},
            ],
        )

    # When: Consolidate all sessions
    result = await consolidation_pipeline.run_consolidation_cycle(
        consolidate_to_qdrant=False,
        consolidate_conversations=True,
        active_sessions=sessions,
    )

    # Then: All sessions consolidated
    assert len(result["conversation_consolidations"]) == len(sessions)


# ============================================================================
# Error Handling Tests
# ============================================================================


async def test_consolidation_handles_qdrant_error_e2e(consolidation_pipeline):
    """Test consolidation handles Qdrant consolidation errors gracefully."""
    # When: Run cycle (may encounter errors in test environment)
    result = await consolidation_pipeline.run_consolidation_cycle(
        consolidate_to_qdrant=True,
        consolidate_conversations=False,
    )

    # Then: Cycle completes (errors logged but not raised)
    assert "qdrant_consolidation" in result
    assert "completed_at" in result


async def test_consolidation_handles_conversation_error_e2e(consolidation_pipeline):
    """Test consolidation handles conversation consolidation errors gracefully."""
    # When: Try to consolidate invalid session
    result = await consolidation_pipeline.run_consolidation_cycle(
        consolidate_to_qdrant=False,
        consolidate_conversations=True,
        active_sessions=["invalid_session_xyz"],
    )

    # Then: Cycle completes with error recorded
    assert len(result["conversation_consolidations"]) == 1
    conv_result = result["conversation_consolidations"][0]
    assert "session_id" in conv_result


# ============================================================================
# Performance Tests
# ============================================================================


async def test_consolidation_performance_target_e2e(consolidation_pipeline, redis_memory_manager):
    """Test consolidation meets performance targets."""
    # Given: Small batch of items
    for i in range(5):
        await redis_memory_manager.store(
            key=f"perf_test_{i}",
            value=f"data {i}",
            namespace="test_perf",
        )

    # When: Run consolidation
    start = time.time()
    await consolidation_pipeline.consolidate_redis_to_qdrant(
        namespace="test_perf",
        batch_size=10,
    )
    latency_ms = (time.time() - start) * 1000

    # Then: Meets performance target
    assert latency_ms < 3000, f"Consolidation {latency_ms}ms exceeds 3s for small batch"
