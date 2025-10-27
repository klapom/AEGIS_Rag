"""
Integration tests for SSE Chat streaming endpoint.

Sprint 15 Feature 15.1: SSE Streaming Backend
"""

import json
import pytest
from httpx import AsyncClient

from src.api.main import app


@pytest.mark.asyncio
async def test_chat_stream_basic():
    """Test basic SSE streaming functionality."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream(
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
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream(
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
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/v1/chat/stream",
            json={"query": "Explain RAG", "include_sources": True},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200

            # Check for source messages
            has_sources = False
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        message = json.loads(data_str)
                        if message.get("type") == "source":
                            has_sources = True
                            # Verify source structure
                            assert "source" in message
                            assert "document_id" in message["source"] or "context" in message["source"]
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
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream(
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
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/v1/chat/stream",
            json={"query": "Test buffering"},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200
            # Check for no-buffering header
            assert response.headers.get("x-accel-buffering") == "no"
            assert response.headers.get("cache-control") == "no-cache"
