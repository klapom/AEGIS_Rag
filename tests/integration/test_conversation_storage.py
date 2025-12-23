"""Integration tests for conversation storage with follow-up questions.

Sprint 35 Feature 35.3: Follow-up Questions Redis Fix (TD-043)

This test suite verifies:
1. Conversations are saved to Redis correctly
2. Follow-up questions are included in conversation storage
3. Follow-up questions can be retrieved from storage
4. Session persistence across browser refreshes
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.api.v1.chat import FollowUpQuestionsResponse, save_conversation_turn
from src.components.memory import get_redis_memory


@pytest.fixture
async def redis_memory():
    """Get Redis memory manager for testing."""
    redis = get_redis_memory()
    yield redis
    # Cleanup is handled by test teardown


@pytest.fixture
def sample_sources():
    """Sample source documents for testing."""
    return [
        {
            "text": "RAG stands for Retrieval-Augmented Generation",
            "title": "RAG Paper",
            "source": "rag_paper.pdf",
            "score": 0.95,
            "metadata": {"page": 1},
        },
        {
            "text": "Vector search is used to find relevant documents",
            "title": "Vector Search Guide",
            "source": "vector_search.pdf",
            "score": 0.87,
            "metadata": {"page": 3},
        },
    ]


@pytest.fixture
def sample_follow_up_questions():
    """Sample follow-up questions for testing."""
    return [
        "How does RAG improve answer accuracy?",
        "What are the limitations of RAG systems?",
        "Can RAG handle multi-hop reasoning?",
    ]


class TestConversationStorage:
    """Test conversation storage with follow-up questions."""

    @pytest.mark.asyncio
    async def test_save_conversation_with_follow_ups(
        self, redis_memory, sample_sources, sample_follow_up_questions
    ):
        """Test that conversations with follow-up questions are saved correctly."""
        session_id = f"test_session_{int(datetime.now(UTC).timestamp())}"

        # Save conversation with follow-up questions
        success = await save_conversation_turn(
            session_id=session_id,
            user_message="What is RAG?",
            assistant_message="RAG stands for Retrieval-Augmented Generation. It combines retrieval and generation.",
            intent="factual",
            sources=sample_sources,
            follow_up_questions=sample_follow_up_questions,
        )

        assert success, "Failed to save conversation"

        # Retrieve and verify
        conversation = await redis_memory.retrieve(key=session_id, namespace="conversation")

        # Extract value from Redis wrapper
        if isinstance(conversation, dict) and "value" in conversation:
            conversation = conversation["value"]

        assert conversation is not None, "Conversation not found in Redis"
        assert "messages" in conversation
        assert len(conversation["messages"]) == 2, "Should have user + assistant message"
        assert "follow_up_questions" in conversation
        assert len(conversation["follow_up_questions"]) == 3
        assert conversation["follow_up_questions"] == sample_follow_up_questions

        # Cleanup
        await redis_memory._client.delete(f"conversation:{session_id}")

    @pytest.mark.asyncio
    async def test_save_conversation_without_follow_ups(self, redis_memory, sample_sources):
        """Test that conversations can be saved without follow-up questions."""
        session_id = f"test_session_{int(datetime.now(UTC).timestamp())}"

        # Save without follow-up questions
        success = await save_conversation_turn(
            session_id=session_id,
            user_message="What is RAG?",
            assistant_message="RAG is a retrieval system.",
            intent="factual",
            sources=sample_sources,
            follow_up_questions=None,
        )

        assert success

        # Verify
        conversation = await redis_memory.retrieve(key=session_id, namespace="conversation")

        if isinstance(conversation, dict) and "value" in conversation:
            conversation = conversation["value"]

        assert conversation is not None
        assert conversation["follow_up_questions"] == []

        # Cleanup
        await redis_memory._client.delete(f"conversation:{session_id}")

    @pytest.mark.asyncio
    async def test_multiple_turns_preserve_follow_ups(
        self, redis_memory, sample_sources, sample_follow_up_questions
    ):
        """Test that multiple conversation turns preserve follow-up questions."""
        session_id = f"test_session_{int(datetime.now(UTC).timestamp())}"

        # First turn
        await save_conversation_turn(
            session_id=session_id,
            user_message="What is RAG?",
            assistant_message="RAG is retrieval-augmented generation.",
            intent="factual",
            sources=sample_sources,
            follow_up_questions=["Question 1", "Question 2"],
        )

        # Second turn with different follow-ups
        new_follow_ups = ["Follow-up A", "Follow-up B", "Follow-up C"]
        await save_conversation_turn(
            session_id=session_id,
            user_message="How does it work?",
            assistant_message="It retrieves relevant context then generates answers.",
            intent="factual",
            sources=sample_sources,
            follow_up_questions=new_follow_ups,
        )

        # Verify latest follow-ups are stored
        conversation = await redis_memory.retrieve(key=session_id, namespace="conversation")

        if isinstance(conversation, dict) and "value" in conversation:
            conversation = conversation["value"]

        assert len(conversation["messages"]) == 4  # 2 turns = 4 messages
        assert conversation["follow_up_questions"] == new_follow_ups

        # Cleanup
        await redis_memory._client.delete(f"conversation:{session_id}")

    @pytest.mark.asyncio
    async def test_sources_serialization_with_follow_ups(
        self, redis_memory, sample_follow_up_questions
    ):
        """Test that sources are correctly serialized when saving with follow-ups."""
        session_id = f"test_session_{int(datetime.now(UTC).timestamp())}"

        # Test with various source formats
        from src.api.v1.chat import SourceDocument

        pydantic_sources = [
            SourceDocument(
                text="Test content",
                title="Test Doc",
                source="test.pdf",
                score=0.9,
                metadata={"page": 1},
            )
        ]

        success = await save_conversation_turn(
            session_id=session_id,
            user_message="Test query",
            assistant_message="Test answer",
            intent="factual",
            sources=pydantic_sources,
            follow_up_questions=sample_follow_up_questions,
        )

        assert success

        # Verify sources are serialized
        conversation = await redis_memory.retrieve(key=session_id, namespace="conversation")

        if isinstance(conversation, dict) and "value" in conversation:
            conversation = conversation["value"]

        assistant_msg = conversation["messages"][1]
        assert assistant_msg["role"] == "assistant"
        assert "sources" in assistant_msg
        assert len(assistant_msg["sources"]) == 1
        assert isinstance(assistant_msg["sources"][0], dict)
        assert assistant_msg["sources"][0]["text"] == "Test content"

        # Cleanup
        await redis_memory._client.delete(f"conversation:{session_id}")

    @pytest.mark.asyncio
    async def test_ttl_is_set_correctly(self, redis_memory, sample_follow_up_questions):
        """Test that conversation TTL is set to 7 days."""
        session_id = f"test_session_{int(datetime.now(UTC).timestamp())}"

        await save_conversation_turn(
            session_id=session_id,
            user_message="Test",
            assistant_message="Response",
            follow_up_questions=sample_follow_up_questions,
        )

        # Check TTL
        ttl = await redis_memory._client.ttl(f"conversation:{session_id}")

        # TTL should be close to 7 days (604800 seconds)
        # Allow some variance for execution time
        assert ttl > 604700  # At least 604700 seconds (allowing 100s variance)
        assert ttl <= 604800  # Not more than 7 days

        # Cleanup
        await redis_memory._client.delete(f"conversation:{session_id}")


class TestFollowUpQuestionsEndpoint:
    """Test the follow-up questions endpoint integration."""

    @pytest.mark.asyncio
    async def test_get_followup_questions_from_storage(
        self, redis_memory, sample_sources, sample_follow_up_questions
    ):
        """Test that follow-up endpoint returns stored questions."""
        from src.api.v1.chat import get_followup_questions

        session_id = f"test_session_{int(datetime.now(UTC).timestamp())}"

        # Save conversation with follow-ups
        await save_conversation_turn(
            session_id=session_id,
            user_message="What is RAG?",
            assistant_message="RAG is retrieval-augmented generation.",
            intent="factual",
            sources=sample_sources,
            follow_up_questions=sample_follow_up_questions,
        )

        # Get follow-up questions
        response = await get_followup_questions(session_id)

        assert isinstance(response, FollowUpQuestionsResponse)
        assert response.session_id == session_id
        assert len(response.followup_questions) == 3
        assert response.followup_questions == sample_follow_up_questions

        # Cleanup
        await redis_memory._client.delete(f"conversation:{session_id}")

    @pytest.mark.asyncio
    async def test_get_followup_questions_session_not_found(self):
        """Test that endpoint returns 404 for non-existent session."""
        from fastapi import HTTPException

        from src.api.v1.chat import get_followup_questions

        non_existent_session = "non_existent_session_12345"

        with pytest.raises(HTTPException) as exc_info:
            await get_followup_questions(non_existent_session)

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_get_followup_questions_empty_conversation(self, redis_memory):
        """Test that endpoint handles empty conversations gracefully."""
        from src.api.v1.chat import get_followup_questions

        session_id = f"test_session_{int(datetime.now(UTC).timestamp())}"

        # Store empty conversation
        await redis_memory.store(
            key=session_id,
            value={
                "messages": [],
                "follow_up_questions": [],
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "message_count": 0,
            },
            namespace="conversation",
            ttl_seconds=300,
        )

        # Get follow-up questions
        response = await get_followup_questions(session_id)

        assert response.followup_questions == []

        # Cleanup
        await redis_memory._client.delete(f"conversation:{session_id}")


class TestRedisConnectionHandling:
    """Test Redis connection error handling."""

    @pytest.mark.asyncio
    async def test_save_handles_redis_error(self, sample_sources):
        """Test that save_conversation_turn handles Redis errors gracefully."""
        session_id = "test_session_error"

        # Mock Redis to raise an error
        with patch("src.components.memory.get_redis_memory") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.store.side_effect = Exception("Redis connection failed")
            mock_get_redis.return_value = mock_redis

            # Should return False, not raise
            success = await save_conversation_turn(
                session_id=session_id,
                user_message="Test",
                assistant_message="Response",
                sources=sample_sources,
                follow_up_questions=["Question 1"],
            )

            assert success is False

    @pytest.mark.asyncio
    async def test_retrieve_handles_none_result(self, redis_memory):
        """Test that retrieve handles None results correctly."""
        from fastapi import HTTPException

        from src.api.v1.chat import get_followup_questions

        # Try to get follow-ups for session that doesn't exist
        with pytest.raises(HTTPException) as exc_info:
            await get_followup_questions("nonexistent_session")

        assert exc_info.value.status_code == 404
