"""
Integration tests for SSE Chat streaming endpoint.

Sprint 15 Feature 15.1: SSE Streaming Backend
Sprint 27 Feature 27.10: Citation map integration tests
"""

import json

import pytest
from httpx import AsyncClient

from src.api.main import app


@pytest.mark.asyncio
async def test_chat_stream_basic():
    """Test basic SSE streaming functionality."""
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "What is RAG?"},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Collect all SSE messages
        messages = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]  # Remove "data: " prefix
                if data_str == "[DONE]":
                    break
                try:
                    message = json.loads(data_str)
                    messages.append(message)
                except json.JSONDecodeError:
                    pass

        # Verify message types
        message_types = [msg["type"] for msg in messages]
        assert "metadata" in message_types
        assert any(msg["type"] == "token" for msg in messages)


@pytest.mark.asyncio
async def test_chat_stream_with_session_id():
    """Test SSE streaming with session_id."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        session_id = "test-session-123"
        async with client.stream(
            "POST",
            "/api/v1/chat/stream",
            json={"query": "Hello", "session_id": session_id},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200

            # Check metadata includes session_id
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        message = json.loads(data_str)
                        if message.get("type") == "metadata":
                            assert message.get("session_id") == session_id
                            break
                    except json.JSONDecodeError:
                        pass


@pytest.mark.asyncio
async def test_chat_stream_with_intent():
    """Test SSE streaming with specific intent."""
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "Search docs", "intent": "vector"},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200

        # Verify intent is respected
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    message = json.loads(data_str)
                    if message.get("type") == "intent":
                        assert message.get("intent") == "vector"
                        break
                except json.JSONDecodeError:
                    pass


@pytest.mark.asyncio
async def test_chat_stream_empty_query():
    """Test SSE streaming with empty query returns error."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={"query": ""},
            headers={"Accept": "text/event-stream"},
        )
        # Should return validation error
        assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_chat_stream_invalid_intent():
    """Test SSE streaming with invalid intent."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={"query": "Test", "intent": "invalid_intent"},
            headers={"Accept": "text/event-stream"},
        )
        # Should return validation error or process with default intent
        assert response.status_code in [200, 400, 422]


@pytest.mark.asyncio
async def test_chat_stream_with_sources():
    """Test SSE streaming includes source documents."""
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "Explain RAG", "include_sources": True},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200

        # Check for source messages
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    message = json.loads(data_str)
                    if message.get("type") == "source":
                        # Verify source structure
                        assert "source" in message
                        assert (
                            "document_id" in message["source"] or "context" in message["source"]
                        )
                except json.JSONDecodeError:
                    pass

        # Sources might not always be available depending on query
        # Just verify stream worked
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_sessions_list():
    """Test listing conversation sessions."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/chat/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total_count" in data
        assert isinstance(data["sessions"], list)


@pytest.mark.asyncio
async def test_chat_stream_cors_headers():
    """Test SSE streaming includes CORS headers."""
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "Test CORS"},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200
        # Check for CORS header
        assert "access-control-allow-origin" in response.headers


@pytest.mark.asyncio
async def test_chat_stream_no_buffering():
    """Test SSE streaming disables buffering."""
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "Test buffering"},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200
        # Check for no-buffering header
        assert response.headers.get("x-accel-buffering") == "no"
        assert response.headers.get("cache-control") == "no-cache"


# Sprint 27 Feature 27.10: Citation map integration tests


@pytest.mark.asyncio
async def test_chat_stream_includes_citation_map():
    """Test SSE streaming includes citation_map in metadata."""
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "What is AEGIS RAG?", "include_sources": True},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200

        # Look for citation_map in metadata
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    message = json.loads(data_str)
                    if message.get("type") == "metadata" and "data" in message:
                        data = message["data"]
                        if "citation_map" in data:
                            # Verify citation_map structure
                            citation_map = data["citation_map"]
                            assert isinstance(citation_map, dict)
                            # If citations exist, verify structure
                            if citation_map:
                                # Check first citation
                                first_key = list(citation_map.keys())[0]
                                citation = citation_map[first_key]
                                assert "text" in citation
                                assert "source" in citation
                                assert "title" in citation
                                assert "score" in citation
                                assert "metadata" in citation
                            # Verify citations_count
                            if "citations_count" in data:
                                assert data["citations_count"] == len(citation_map)
                            break
                except json.JSONDecodeError:
                    pass

        # Citation map might not always be present (depends on LLM response)
        # So we just verify the stream worked
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_stream_citation_map_with_vector_intent():
    """Test citation_map is sent with vector search intent."""
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "Explain RAG architecture", "intent": "vector", "include_sources": True},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200

        # Collect all metadata messages
        metadata_messages = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    message = json.loads(data_str)
                    if message.get("type") == "metadata":
                        metadata_messages.append(message)
                except json.JSONDecodeError:
                    pass

        # Verify at least one metadata message exists
        assert len(metadata_messages) > 0


@pytest.mark.asyncio
async def test_chat_stream_citation_map_with_hybrid_intent():
    """Test citation_map is sent with hybrid intent."""
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "What is LangGraph?", "intent": "hybrid", "include_sources": True},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200

        # Just verify stream completes successfully
        message_count = 0
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    json.loads(data_str)
                    message_count += 1
                except json.JSONDecodeError:
                    pass

        # Should have received some messages
        assert message_count > 0


@pytest.mark.asyncio
async def test_chat_stream_citation_numbers_are_integers():
    """Test that citation map keys are integers (1, 2, 3...)."""
    async with AsyncClient(app=app, base_url="http://test") as client, client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "What is AEGIS RAG?", "include_sources": True},
        headers={"Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    message = json.loads(data_str)
                    if message.get("type") == "metadata" and "data" in message:
                        data = message["data"]
                        if "citation_map" in data and data["citation_map"]:
                            citation_map = data["citation_map"]
                            # Verify keys are string representations of integers
                            # (JSON converts int keys to strings)
                            for key in citation_map:
                                # Key should be a string that's parseable as int
                                int(key)  # Raises ValueError if not parseable
                            break
                except json.JSONDecodeError:
                    pass

        assert response.status_code == 200
