"""Unit tests for share conversation endpoints.

Sprint 38 Feature 38.3: Share Conversation Links

Tests cover:
- Create share link endpoint
- Get shared conversation endpoint
- Token expiry validation
- Error handling (not found, expired)
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status

from src.api.v1.chat import (
    ShareLinkResponse,
    ShareSettings,
    SharedConversationResponse,
)


@pytest.fixture
def mock_redis_memory():
    """Mock RedisMemoryManager for testing."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing."""
    return {
        "messages": [
            {
                "role": "user",
                "content": "What is AEGIS RAG?",
                "timestamp": "2025-12-08T10:00:00Z",
            },
            {
                "role": "assistant",
                "content": "AEGIS RAG is an Agentic Enterprise Graph Intelligence System...",
                "timestamp": "2025-12-08T10:00:05Z",
                "intent": "vector",
                "source_count": 3,
                "sources": [],
            },
        ],
        "created_at": "2025-12-08T10:00:00Z",
        "updated_at": "2025-12-08T10:00:05Z",
        "message_count": 2,
        "follow_up_questions": ["How does hybrid search work?"],
        "title": "Discussion about AEGIS RAG",
    }


class TestCreateShareLink:
    """Tests for POST /chat/sessions/{session_id}/share endpoint."""

    @pytest.mark.asyncio
    async def test_create_share_link_success(
        self, test_client, mock_redis_memory, sample_conversation_data
    ):
        """Test successful share link creation."""
        session_id = "test-session-123"

        # Mock Redis memory retrieve (session exists)
        mock_redis_memory.retrieve.return_value = {"value": sample_conversation_data}
        mock_redis_memory.store.return_value = True

        with patch("src.api.v1.chat.get_redis_memory", return_value=mock_redis_memory):
            response = test_client.post(
                f"/v1/chat/sessions/{session_id}/share",
                json={"expiry_hours": 24},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate response structure
        assert "share_url" in data
        assert "share_token" in data
        assert "expires_at" in data
        assert data["session_id"] == session_id

        # Validate token format (URL-safe base64)
        assert len(data["share_token"]) > 16
        assert "/" not in data["share_token"]  # URL-safe

        # Validate expiry timestamp is in future
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        now = datetime.now(UTC)
        assert expires_at > now

        # Validate Redis store was called with correct params
        mock_redis_memory.store.assert_called_once()
        call_args = mock_redis_memory.store.call_args
        assert call_args.kwargs["namespace"] == "share"
        assert call_args.kwargs["ttl_seconds"] == 24 * 3600

    @pytest.mark.asyncio
    async def test_create_share_link_custom_expiry(self, test_client, mock_redis_memory, sample_conversation_data):
        """Test share link creation with custom expiry hours."""
        session_id = "test-session-456"

        mock_redis_memory.retrieve.return_value = {"value": sample_conversation_data}
        mock_redis_memory.store.return_value = True

        with patch("src.api.v1.chat.get_redis_memory", return_value=mock_redis_memory):
            response = test_client.post(
                f"/v1/chat/sessions/{session_id}/share",
                json={"expiry_hours": 168},  # 7 days (max)
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate 7-day expiry
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        now = datetime.now(UTC)
        expected_expiry = now + timedelta(hours=168)

        # Allow 5 second tolerance for test execution time
        assert abs((expires_at - expected_expiry).total_seconds()) < 5

        # Validate Redis TTL
        mock_redis_memory.store.assert_called_once()
        call_args = mock_redis_memory.store.call_args
        assert call_args.kwargs["ttl_seconds"] == 168 * 3600

    @pytest.mark.asyncio
    async def test_create_share_link_session_not_found(self, test_client, mock_redis_memory):
        """Test share link creation for non-existent session."""
        session_id = "nonexistent-session"

        # Mock Redis memory retrieve (session not found)
        mock_redis_memory.retrieve.return_value = None

        with patch("src.api.v1.chat.get_redis_memory", return_value=mock_redis_memory):
            response = test_client.post(
                f"/v1/chat/sessions/{session_id}/share",
                json={"expiry_hours": 24},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_share_link_invalid_expiry(self, test_client, mock_redis_memory, sample_conversation_data):
        """Test share link creation with invalid expiry hours."""
        session_id = "test-session-789"

        mock_redis_memory.retrieve.return_value = {"value": sample_conversation_data}

        with patch("src.api.v1.chat.get_redis_memory", return_value=mock_redis_memory):
            # Test expiry too low
            response = test_client.post(
                f"/v1/chat/sessions/{session_id}/share",
                json={"expiry_hours": 0},  # Invalid: must be >= 1
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Test expiry too high
            response = test_client.post(
                f"/v1/chat/sessions/{session_id}/share",
                json={"expiry_hours": 200},  # Invalid: must be <= 168
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_share_link_redis_failure(self, test_client, mock_redis_memory, sample_conversation_data):
        """Test share link creation when Redis store fails."""
        session_id = "test-session-fail"

        mock_redis_memory.retrieve.return_value = {"value": sample_conversation_data}
        mock_redis_memory.store.side_effect = Exception("Redis connection error")

        with patch("src.api.v1.chat.get_redis_memory", return_value=mock_redis_memory):
            response = test_client.post(
                f"/v1/chat/sessions/{session_id}/share",
                json={"expiry_hours": 24},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to create share link" in response.json()["detail"]


class TestGetSharedConversation:
    """Tests for GET /chat/share/{share_token} endpoint."""

    @pytest.mark.asyncio
    async def test_get_shared_conversation_success(
        self, test_client, mock_redis_memory, sample_conversation_data
    ):
        """Test successful retrieval of shared conversation."""
        share_token = "Xk9f2mZ_pQrT1aB3"
        session_id = "test-session-shared"

        # Mock share data
        share_data = {
            "value": {
                "session_id": session_id,
                "created_at": "2025-12-08T10:30:00Z",
                "expires_at": "2025-12-09T10:30:00Z",
            }
        }

        # Mock conversation data
        conversation_data = {"value": sample_conversation_data}

        # Setup mock to return different data for different namespaces
        async def mock_retrieve(key, namespace, track_access=True):
            if namespace == "share" and key == share_token:
                return share_data
            elif namespace == "conversation" and key == session_id:
                return conversation_data
            return None

        mock_redis_memory.retrieve.side_effect = mock_retrieve

        with patch("src.api.v1.chat.get_redis_memory", return_value=mock_redis_memory):
            response = test_client.get(f"/v1/chat/share/{share_token}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate response structure
        assert data["session_id"] == session_id
        assert data["title"] == "Discussion about AEGIS RAG"
        assert data["message_count"] == 2
        assert len(data["messages"]) == 2
        assert "shared_at" in data
        assert "expires_at" in data
        assert "created_at" in data

        # Validate messages are included
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_get_shared_conversation_token_not_found(self, test_client, mock_redis_memory):
        """Test retrieval with non-existent or expired token."""
        share_token = "InvalidToken123"

        # Mock Redis memory retrieve (token not found)
        mock_redis_memory.retrieve.return_value = None

        with patch("src.api.v1.chat.get_redis_memory", return_value=mock_redis_memory):
            response = test_client.get(f"/v1/chat/share/{share_token}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found or expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_shared_conversation_invalid_share_data(self, test_client, mock_redis_memory):
        """Test retrieval with invalid share data (missing session_id)."""
        share_token = "InvalidDataToken"

        # Mock share data without session_id
        share_data = {
            "value": {
                "created_at": "2025-12-08T10:30:00Z",
                "expires_at": "2025-12-09T10:30:00Z",
            }
        }

        mock_redis_memory.retrieve.return_value = share_data

        with patch("src.api.v1.chat.get_redis_memory", return_value=mock_redis_memory):
            response = test_client.get(f"/v1/chat/share/{share_token}")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Invalid share data" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_shared_conversation_deleted(self, test_client, mock_redis_memory):
        """Test retrieval when conversation has been deleted."""
        share_token = "DeletedConvToken"
        session_id = "deleted-session"

        # Mock share data exists
        share_data = {
            "value": {
                "session_id": session_id,
                "created_at": "2025-12-08T10:30:00Z",
                "expires_at": "2025-12-09T10:30:00Z",
            }
        }

        # Setup mock: share exists but conversation deleted
        async def mock_retrieve(key, namespace, track_access=True):
            if namespace == "share" and key == share_token:
                return share_data
            elif namespace == "conversation" and key == session_id:
                return None  # Conversation deleted
            return None

        mock_redis_memory.retrieve.side_effect = mock_retrieve

        with patch("src.api.v1.chat.get_redis_memory", return_value=mock_redis_memory):
            response = test_client.get(f"/v1/chat/share/{share_token}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "no longer exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_shared_conversation_no_tracking(self, test_client, mock_redis_memory, sample_conversation_data):
        """Test that shared conversation retrieval does not track access."""
        share_token = "NoTrackToken"
        session_id = "no-track-session"

        share_data = {
            "value": {
                "session_id": session_id,
                "created_at": "2025-12-08T10:30:00Z",
                "expires_at": "2025-12-09T10:30:00Z",
            }
        }

        conversation_data = {"value": sample_conversation_data}

        async def mock_retrieve(key, namespace, track_access=True):
            if namespace == "share" and key == share_token:
                return share_data
            elif namespace == "conversation" and key == session_id:
                return conversation_data
            return None

        mock_redis_memory.retrieve.side_effect = mock_retrieve

        with patch("src.api.v1.chat.get_redis_memory", return_value=mock_redis_memory):
            response = test_client.get(f"/v1/chat/share/{share_token}")

        assert response.status_code == status.HTTP_200_OK

        # Verify retrieve was called with track_access=False
        retrieve_calls = mock_redis_memory.retrieve.call_args_list
        assert len(retrieve_calls) == 2

        # Both calls should have track_access=False
        for call in retrieve_calls:
            assert call.kwargs.get("track_access") is False
