"""
LLM Streaming Client for Real-Time Token Generation.

Sprint 69 Feature 69.2: LLM Generation Streaming (8 SP)

This module provides a streaming client for real-time LLM token generation,
enabling Time To First Token (TTFT) < 100ms for improved user experience.

Architecture:
    User → FastAPI SSE → StreamingClient → AegisLLMProxy → Ollama/Cloud

Performance Targets:
    - TTFT: < 100ms (measured from request to first token)
    - Throughput: ~50 tokens/second
    - Memory: < 512MB per concurrent stream

Example:
    async for token in stream_llm_response(prompt="What is RAG?"):
        print(token, end="", flush=True)
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

import structlog

from src.core.exceptions import LLMExecutionError
from src.domains.llm_integration.models import LLMTask, QualityRequirement, TaskType
from src.domains.llm_integration.proxy.aegis_llm_proxy import AegisLLMProxy

logger = structlog.get_logger(__name__)


class StreamingClient:
    """
    Streaming client for real-time LLM token generation.

    This client wraps AegisLLMProxy.generate_streaming() to provide a
    clean interface for Server-Sent Events (SSE) endpoints.

    Features:
        - Token-by-token streaming
        - TTFT measurement
        - Error handling with graceful degradation
        - Async iterator interface

    Example:
        client = StreamingClient()
        async for chunk in client.stream(prompt="Explain RAG"):
            if chunk["type"] == "token":
                print(chunk["content"], end="")
            elif chunk["type"] == "done":
                print(f"\nTTFT: {chunk['ttft_ms']}ms")
    """

    def __init__(self, proxy: AegisLLMProxy | None = None) -> None:
        """
        Initialize streaming client.

        Args:
            proxy: Optional AegisLLMProxy instance. If None, creates a new one.
        """
        self.proxy = proxy or AegisLLMProxy()
        logger.info("streaming_client_initialized")

    async def stream(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERATION,
        quality_requirement: QualityRequirement = QualityRequirement.STANDARD,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream LLM response token-by-token with TTFT measurement.

        Sprint 69 Feature 69.2: This method yields tokens as they're generated,
        reducing perceived latency from 320ms to <100ms TTFT.

        Args:
            prompt: User prompt for LLM generation
            task_type: Type of LLM task (default: GENERATION)
            quality_requirement: Quality level (STANDARD, HIGH, CRITICAL)
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional task parameters

        Yields:
            dict: Streaming events with format:
                - {"type": "metadata", "ttft_ms": float, "model": str, "provider": str}
                - {"type": "token", "content": str}
                - {"type": "done", "total_tokens": int, "latency_ms": float}
                - {"type": "error", "error": str}

        Example:
            async for chunk in client.stream("What is AEGIS RAG?"):
                if chunk["type"] == "token":
                    print(chunk["content"], end="", flush=True)
        """
        start_time = time.time()
        ttft_measured = False
        total_tokens = 0

        # Build LLM task
        task = LLMTask(
            task_type=task_type,
            prompt=prompt,
            quality_requirement=quality_requirement,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        logger.info(
            "streaming_started",
            task_id=str(task.id),
            prompt_length=len(prompt),
            quality=quality_requirement.value,
        )

        try:
            # Stream tokens from proxy
            async for chunk in self.proxy.generate_streaming(task):
                # Measure TTFT on first token
                if not ttft_measured and chunk.get("content"):
                    ttft_ms = (time.time() - start_time) * 1000
                    ttft_measured = True

                    logger.info(
                        "ttft_measured",
                        task_id=str(task.id),
                        ttft_ms=ttft_ms,
                        target_ms=100,
                        success=ttft_ms < 100,
                    )

                    # Yield metadata with TTFT
                    yield {
                        "type": "metadata",
                        "ttft_ms": ttft_ms,
                        "model": chunk.get("model", "unknown"),
                        "provider": chunk.get("provider", "unknown"),
                    }

                # Yield token
                if chunk.get("content"):
                    total_tokens += 1
                    yield {
                        "type": "token",
                        "content": chunk["content"],
                    }

            # Streaming completed successfully
            total_latency_ms = (time.time() - start_time) * 1000

            logger.info(
                "streaming_completed",
                task_id=str(task.id),
                total_tokens=total_tokens,
                latency_ms=total_latency_ms,
                tokens_per_second=total_tokens / (total_latency_ms / 1000) if total_latency_ms > 0 else 0,
            )

            yield {
                "type": "done",
                "total_tokens": total_tokens,
                "latency_ms": total_latency_ms,
            }

        except LLMExecutionError as e:
            logger.error(
                "streaming_llm_error",
                task_id=str(task.id),
                error=str(e),
                details=e.details,
            )
            yield {
                "type": "error",
                "error": f"LLM execution failed: {e.message}",
                "recoverable": False,
            }

        except asyncio.CancelledError:
            logger.info("streaming_cancelled", task_id=str(task.id))
            yield {
                "type": "cancelled",
                "message": "Stream cancelled by client",
            }
            raise

        except Exception as e:
            logger.error(
                "streaming_unexpected_error",
                task_id=str(task.id),
                error=str(e),
                exc_info=True,
            )
            yield {
                "type": "error",
                "error": f"Unexpected error: {str(e)}",
                "recoverable": False,
            }


# Singleton instance
_streaming_client: StreamingClient | None = None


def get_streaming_client() -> StreamingClient:
    """
    Get or create singleton StreamingClient instance.

    Returns:
        Singleton StreamingClient instance
    """
    global _streaming_client
    if _streaming_client is None:
        _streaming_client = StreamingClient()
        logger.info("streaming_client_singleton_created")
    return _streaming_client


# Convenience function for simple streaming
async def stream_llm_response(
    prompt: str,
    quality: QualityRequirement = QualityRequirement.STANDARD,
    **kwargs: Any,
) -> AsyncIterator[str]:
    """
    Convenience function to stream LLM response as plain text tokens.

    This is a simplified interface that yields only the token content,
    without metadata or event types. Ideal for simple streaming use cases.

    Args:
        prompt: User prompt
        quality: Quality requirement (STANDARD, HIGH, CRITICAL)
        **kwargs: Additional parameters for StreamingClient.stream()

    Yields:
        str: Token content

    Example:
        async for token in stream_llm_response("What is RAG?"):
            print(token, end="", flush=True)
    """
    client = get_streaming_client()
    async for chunk in client.stream(prompt, quality_requirement=quality, **kwargs):
        if chunk["type"] == "token":
            yield chunk["content"]
