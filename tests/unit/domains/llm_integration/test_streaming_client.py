"""
Unit Tests for LLM Streaming Client.

Sprint 69 Feature 69.2: LLM Generation Streaming (8 SP)

This module tests the streaming client for real-time LLM token generation,
ensuring TTFT < 100ms and correct event handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domains.llm_integration.models import QualityRequirement, TaskType
from src.domains.llm_integration.streaming_client import (
    StreamingClient,
    get_streaming_client,
    stream_llm_response,
)


@pytest.fixture
def mock_proxy():
    """Create mock AegisLLMProxy."""
    proxy = MagicMock()

    # Mock streaming method to return async generator
    async def mock_stream(*args, **kwargs):
        # Simulate TTFT < 100ms by yielding first token immediately
        yield {"content": "Hello", "model": "llama3.2:8b", "provider": "local_ollama"}
        yield {"content": " world", "model": "llama3.2:8b", "provider": "local_ollama"}
        yield {"content": "!", "model": "llama3.2:8b", "provider": "local_ollama"}

    proxy.generate_streaming = mock_stream
    return proxy


@pytest.fixture
def streaming_client(mock_proxy):
    """Create StreamingClient with mocked proxy."""
    return StreamingClient(proxy=mock_proxy)


@pytest.mark.asyncio
async def test_streaming_client_initialization():
    """Test StreamingClient initializes correctly."""
    # Test with default proxy
    client = StreamingClient()
    assert client.proxy is not None

    # Test with custom proxy
    mock_proxy = MagicMock()
    client = StreamingClient(proxy=mock_proxy)
    assert client.proxy == mock_proxy


@pytest.mark.asyncio
async def test_streaming_client_basic_stream(streaming_client):
    """Test basic streaming functionality."""
    chunks = []
    async for chunk in streaming_client.stream(prompt="Test prompt"):
        chunks.append(chunk)

    # Verify we got chunks
    assert len(chunks) > 0

    # Verify chunk types
    chunk_types = {chunk["type"] for chunk in chunks}
    assert "metadata" in chunk_types  # TTFT metadata
    assert "token" in chunk_types  # Token chunks
    assert "done" in chunk_types  # Completion signal

    # Verify metadata has TTFT
    metadata_chunks = [c for c in chunks if c["type"] == "metadata"]
    assert len(metadata_chunks) == 1
    assert "ttft_ms" in metadata_chunks[0]
    assert metadata_chunks[0]["ttft_ms"] < 100  # TTFT target

    # Verify tokens
    token_chunks = [c for c in chunks if c["type"] == "token"]
    assert len(token_chunks) == 3
    assert token_chunks[0]["content"] == "Hello"
    assert token_chunks[1]["content"] == " world"
    assert token_chunks[2]["content"] == "!"

    # Verify done chunk
    done_chunks = [c for c in chunks if c["type"] == "done"]
    assert len(done_chunks) == 1
    assert done_chunks[0]["total_tokens"] == 3
    assert "latency_ms" in done_chunks[0]


@pytest.mark.asyncio
async def test_streaming_client_with_quality_requirements(streaming_client):
    """Test streaming with different quality requirements."""
    chunks = []
    async for chunk in streaming_client.stream(
        prompt="High quality test",
        quality_requirement=QualityRequirement.HIGH,
        temperature=0.3,
        max_tokens=1024,
    ):
        chunks.append(chunk)

    # Verify we got expected chunks
    assert len(chunks) > 0
    token_chunks = [c for c in chunks if c["type"] == "token"]
    assert len(token_chunks) == 3


@pytest.mark.asyncio
async def test_streaming_client_error_handling():
    """Test error handling in streaming client."""
    from src.core.exceptions import LLMExecutionError

    # Create proxy that raises error
    mock_proxy = MagicMock()

    async def error_stream(*args, **kwargs):
        raise LLMExecutionError("Test error", details={"reason": "test"})
        yield  # Make it a generator

    mock_proxy.generate_streaming = error_stream

    client = StreamingClient(proxy=mock_proxy)

    chunks = []
    async for chunk in client.stream(prompt="Error test"):
        chunks.append(chunk)

    # Verify error was caught and yielded
    error_chunks = [c for c in chunks if c["type"] == "error"]
    assert len(error_chunks) == 1
    assert "LLM execution failed" in error_chunks[0]["error"]
    assert error_chunks[0]["recoverable"] is False


@pytest.mark.asyncio
async def test_streaming_client_cancellation():
    """Test stream cancellation."""
    import asyncio

    mock_proxy = MagicMock()

    async def slow_stream(*args, **kwargs):
        yield {"content": "Token 1"}
        await asyncio.sleep(10)  # Long delay
        yield {"content": "Token 2"}

    mock_proxy.generate_streaming = slow_stream

    client = StreamingClient(proxy=mock_proxy)

    chunks = []

    async def stream_task():
        async for chunk in client.stream(prompt="Test"):
            chunks.append(chunk)
            if chunk["type"] == "token":
                # Cancel after first token
                raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await stream_task()

    # Verify we got at least metadata and one token
    assert len(chunks) >= 2


@pytest.mark.asyncio
async def test_get_streaming_client_singleton():
    """Test singleton pattern for streaming client."""
    client1 = get_streaming_client()
    client2 = get_streaming_client()

    # Should be same instance
    assert client1 is client2


@pytest.mark.asyncio
async def test_stream_llm_response_convenience_function():
    """Test convenience function for simple streaming."""
    mock_proxy = MagicMock()

    async def mock_stream(*args, **kwargs):
        yield {"content": "Hello"}
        yield {"content": " world"}

    mock_proxy.generate_streaming = mock_stream

    # Patch singleton to use our mock
    with patch("src.domains.llm_integration.streaming_client._streaming_client", StreamingClient(proxy=mock_proxy)):
        tokens = []
        async for token in stream_llm_response("Test"):
            tokens.append(token)

        assert tokens == ["Hello", " world"]


@pytest.mark.asyncio
async def test_streaming_client_ttft_measurement(streaming_client):
    """Test TTFT (Time To First Token) measurement."""
    chunks = []
    async for chunk in streaming_client.stream(prompt="TTFT test"):
        chunks.append(chunk)
        if chunk["type"] == "metadata":
            # TTFT should be measured on first token
            assert "ttft_ms" in chunk
            # Should be very fast (< 100ms target)
            assert chunk["ttft_ms"] < 100
            # Should also have model and provider info
            assert "model" in chunk
            assert "provider" in chunk
            break  # We only need to check first metadata


@pytest.mark.asyncio
async def test_streaming_client_task_creation(streaming_client):
    """Test that streaming client creates LLMTask correctly."""
    # We can't easily inspect task creation without mocking deeper,
    # but we can verify that the stream accepts all expected parameters
    chunks = []
    async for chunk in streaming_client.stream(
        prompt="Test prompt",
        task_type=TaskType.GENERATION,
        quality_requirement=QualityRequirement.CRITICAL,
        temperature=0.5,
        max_tokens=512,
    ):
        chunks.append(chunk)

    # Verify stream completed successfully
    done_chunks = [c for c in chunks if c["type"] == "done"]
    assert len(done_chunks) == 1


@pytest.mark.asyncio
async def test_streaming_client_empty_response():
    """Test handling of empty response from LLM."""
    mock_proxy = MagicMock()

    async def empty_stream(*args, **kwargs):
        # No tokens generated
        return
        yield  # Make it a generator

    mock_proxy.generate_streaming = empty_stream

    client = StreamingClient(proxy=mock_proxy)

    chunks = []
    async for chunk in client.stream(prompt="Empty test"):
        chunks.append(chunk)

    # Should still have done event, but no tokens
    done_chunks = [c for c in chunks if c["type"] == "done"]
    assert len(done_chunks) == 1
    assert done_chunks[0]["total_tokens"] == 0
