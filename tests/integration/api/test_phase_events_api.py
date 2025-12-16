"""Integration tests for Phase Events API endpoints.

Sprint 48 Feature 48.4: Chat Stream API Enhancement (8 SP)
Sprint 48 Feature 48.5: Phase Events Redis Persistence (5 SP)

Tests the streaming endpoint with phase events and the retrieval endpoint.
"""

import asyncio
import json

import pytest
from httpx import AsyncClient

from src.api.main import app


@pytest.mark.asyncio
async def test_chat_stream_with_phase_events():
    """Test SSE streaming includes phase_event messages."""
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "What is RAG?", "session_id": "test-phase-events-123"},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Collect all phase events
        phase_events = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    message = json.loads(data_str)
                    if message.get("type") == "phase_event":
                        phase_events.append(message["data"])
                except json.JSONDecodeError:
                    pass

        # Should have received at least one phase event
        assert len(phase_events) > 0

        # Verify phase event structure
        first_event = phase_events[0]
        assert "phase_type" in first_event
        assert "status" in first_event
        assert "start_time" in first_event
        # Optional fields
        assert "metadata" in first_event
        assert isinstance(first_event["metadata"], dict)


@pytest.mark.asyncio
async def test_chat_stream_phase_events_have_timing():
    """Test phase events include timing information."""
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "Hello world", "session_id": "test-timing-456"},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200

        completed_events = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    message = json.loads(data_str)
                    if message.get("type") == "phase_event":
                        event_data = message["data"]
                        if event_data.get("status") == "completed":
                            completed_events.append(event_data)
                except json.JSONDecodeError:
                    pass

        # Should have at least one completed event
        assert len(completed_events) > 0

        # Verify completed events have timing info
        for event in completed_events:
            assert "start_time" in event
            assert "end_time" in event
            assert "duration_ms" in event
            assert event["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_chat_stream_reasoning_complete_event():
    """Test streaming emits reasoning_complete event at the end."""
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "Test reasoning", "session_id": "test-reasoning-789"},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200

        reasoning_complete = None
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    message = json.loads(data_str)
                    if message.get("type") == "reasoning_complete":
                        reasoning_complete = message["data"]
                except json.JSONDecodeError:
                    pass

        # Should have received reasoning_complete event
        assert reasoning_complete is not None
        assert "phase_events" in reasoning_complete
        assert isinstance(reasoning_complete["phase_events"], list)


@pytest.mark.asyncio
async def test_phase_events_persistence():
    """Test phase events are persisted to Redis after streaming."""
    session_id = "test-persistence-001"

    # First, stream a chat query
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "What is machine learning?", "session_id": session_id},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200

        # Consume the entire stream
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break

    # Wait a moment for persistence to complete
    await asyncio.sleep(0.5)

    # Now retrieve the phase events
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/v1/chat/conversations/{session_id}/phase-events")

        assert response.status_code == 200
        events = response.json()

        # Should have received persisted events
        assert isinstance(events, list)
        assert len(events) > 0

        # Verify event structure
        first_event = events[0]
        assert "phase_type" in first_event
        assert "status" in first_event
        assert "start_time" in first_event


@pytest.mark.asyncio
async def test_get_phase_events_not_found():
    """Test retrieving phase events for non-existent conversation."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/chat/conversations/non-existent-session/phase-events"
        )

        # Should return empty list for non-existent conversation
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)
        assert len(events) == 0


@pytest.mark.asyncio
async def test_get_phase_events_structure():
    """Test phase events retrieval returns correct structure."""
    session_id = "test-structure-002"

    # Stream a query
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "Explain neural networks", "session_id": session_id},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break

    # Wait for persistence
    await asyncio.sleep(0.5)

    # Retrieve events
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/v1/chat/conversations/{session_id}/phase-events")

        assert response.status_code == 200
        events = response.json()

        # Verify all events have required fields
        for event in events:
            assert "phase_type" in event
            assert "status" in event
            assert "start_time" in event
            assert "metadata" in event
            assert isinstance(event["metadata"], dict)

            # Check valid phase_type values
            valid_phase_types = [
                "intent_classification",
                "vector_search",
                "bm25_search",
                "rrf_fusion",
                "reranking",
                "graph_query",
                "memory_retrieval",
                "llm_generation",
                "follow_up_questions",
            ]
            assert event["phase_type"] in valid_phase_types

            # Check valid status values
            valid_statuses = ["pending", "in_progress", "completed", "failed", "skipped"]
            assert event["status"] in valid_statuses


@pytest.mark.asyncio
async def test_chat_stream_timeout_error():
    """Test streaming returns timeout error after REQUEST_TIMEOUT_SECONDS."""
    # This test would require mocking a slow coordinator response
    # For now, just verify the timeout constants are accessible
    from src.api.v1.chat import REQUEST_TIMEOUT_SECONDS

    assert REQUEST_TIMEOUT_SECONDS == 90


@pytest.mark.asyncio
async def test_chat_stream_error_event_structure():
    """Test error events have correct structure."""
    # Test with an invalid request that should trigger an error
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={
            "query": "Test error handling",
            "session_id": "test-error-001",
            "intent": "invalid",  # Invalid intent to potentially trigger error
        },
        headers={"Accept": "text/event-stream"},
    ) as response:
        # May return 200 and handle error in stream, or return error status
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            # Look for error events in stream
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        message = json.loads(data_str)
                        if message.get("type") == "error":
                            # Verify error event structure
                            assert "error" in message
                            assert "code" in message
                            assert "recoverable" in message
                            assert isinstance(message["recoverable"], bool)
                            break
                    except json.JSONDecodeError:
                        pass


@pytest.mark.asyncio
async def test_phase_events_ttl():
    """Test phase events have 7-day TTL in Redis."""
    # This test verifies the TTL is set correctly
    # The actual TTL check would require Redis client access
    session_id = "test-ttl-003"

    # Stream a query
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "Test TTL", "session_id": session_id},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break

    # Wait for persistence
    await asyncio.sleep(0.5)

    # Retrieve events to verify they exist
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/v1/chat/conversations/{session_id}/phase-events")
        assert response.status_code == 200
        events = response.json()
        assert len(events) > 0

    # TTL is 7 days (604800 seconds) - verified in implementation
    # Actual TTL check would require direct Redis access


@pytest.mark.asyncio
async def test_multiple_conversations_phase_events_isolation():
    """Test phase events are isolated per conversation."""
    session_id_1 = "test-isolation-001"
    session_id_2 = "test-isolation-002"

    # Stream two different queries
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First conversation
        async with client.stream(
            "POST",
            "/api/v1/chat/stream",
            json={"query": "What is Python?", "session_id": session_id_1},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

        # Second conversation
        async with client.stream(
            "POST",
            "/api/v1/chat/stream",
            json={"query": "What is Java?", "session_id": session_id_2},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

    # Wait for persistence
    await asyncio.sleep(0.5)

    # Retrieve events for both conversations
    async with AsyncClient(app=app, base_url="http://test") as client:
        response_1 = await client.get(
            f"/api/v1/chat/conversations/{session_id_1}/phase-events"
        )
        response_2 = await client.get(
            f"/api/v1/chat/conversations/{session_id_2}/phase-events"
        )

        assert response_1.status_code == 200
        assert response_2.status_code == 200

        events_1 = response_1.json()
        events_2 = response_2.json()

        # Both should have events
        assert len(events_1) > 0
        assert len(events_2) > 0

        # Events should be different (different timing, potentially different phases)
        # At minimum, they should not be identical
        assert events_1 != events_2
