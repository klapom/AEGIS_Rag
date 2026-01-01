#!/usr/bin/env python3
"""
Example: LLM Streaming Client Usage

Sprint 69 Feature 69.2: LLM Generation Streaming

This example demonstrates how to use the StreamingClient for real-time
LLM token generation with TTFT < 100ms.

Usage:
    poetry run python examples/streaming_example.py
"""

import asyncio
import time

from src.domains.llm_integration.models import QualityRequirement
from src.domains.llm_integration.streaming_client import (
    StreamingClient,
    get_streaming_client,
    stream_llm_response,
)


async def example_basic_streaming():
    """Example 1: Basic streaming with full metadata."""
    print("=" * 80)
    print("Example 1: Basic Streaming with Metadata")
    print("=" * 80)

    client = get_streaming_client()

    prompt = "Explain what RAG (Retrieval-Augmented Generation) is in one sentence."

    print(f"\nPrompt: {prompt}")
    print("\nStreaming Response:")
    print("-" * 80)

    start_time = time.time()
    ttft = None
    total_tokens = 0

    async for chunk in client.stream(
        prompt=prompt,
        quality_requirement=QualityRequirement.MEDIUM,
        temperature=0.7,
    ):
        if chunk["type"] == "metadata":
            ttft = chunk["ttft_ms"]
            print(f"\n[METADATA] TTFT: {ttft:.2f}ms, Model: {chunk['model']}, Provider: {chunk['provider']}")
            print("-" * 80)

        elif chunk["type"] == "token":
            print(chunk["content"], end="", flush=True)
            total_tokens += 1

        elif chunk["type"] == "done":
            total_latency = chunk["latency_ms"]
            print(f"\n\n[DONE] Total tokens: {chunk['total_tokens']}, Latency: {total_latency:.2f}ms")
            print(f"Tokens/second: {total_tokens / (total_latency / 1000):.2f}")

        elif chunk["type"] == "error":
            print(f"\n[ERROR] {chunk['error']}")

    print("\n" + "=" * 80)


async def example_simple_streaming():
    """Example 2: Simple streaming (tokens only, no metadata)."""
    print("=" * 80)
    print("Example 2: Simple Token Streaming (Convenience Function)")
    print("=" * 80)

    prompt = "What are the three main components of AEGIS RAG?"

    print(f"\nPrompt: {prompt}")
    print("\nStreaming Response:")
    print("-" * 80)

    async for token in stream_llm_response(prompt, quality=QualityRequirement.MEDIUM):
        print(token, end="", flush=True)

    print("\n" + "=" * 80)


async def example_high_quality_streaming():
    """Example 3: High quality streaming with specific parameters."""
    print("=" * 80)
    print("Example 3: High Quality Streaming")
    print("=" * 80)

    client = StreamingClient()

    prompt = "Explain the concept of hybrid search in retrieval systems."

    print(f"\nPrompt: {prompt}")
    print("\nStreaming Response (Quality: HIGH, Temp: 0.3):")
    print("-" * 80)

    async for chunk in client.stream(
        prompt=prompt,
        quality_requirement=QualityRequirement.HIGH,
        temperature=0.3,  # Lower temperature for more focused response
        max_tokens=1024,
    ):
        if chunk["type"] == "token":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "done":
            print(f"\n\n[DONE] Latency: {chunk['latency_ms']:.2f}ms")

    print("\n" + "=" * 80)


async def example_concurrent_streaming():
    """Example 4: Concurrent streaming requests."""
    print("=" * 80)
    print("Example 4: Concurrent Streaming (3 parallel requests)")
    print("=" * 80)

    async def stream_query(query_id: int, prompt: str):
        """Helper to stream a single query."""
        print(f"\n[Query {query_id}] {prompt}")
        print(f"[Query {query_id}] Response: ", end="", flush=True)

        async for token in stream_llm_response(prompt):
            print(token, end="", flush=True)

        print(f" [Query {query_id} DONE]")

    # Run 3 queries concurrently
    await asyncio.gather(
        stream_query(1, "What is vector search?"),
        stream_query(2, "What is graph RAG?"),
        stream_query(3, "What is memory consolidation?"),
    )

    print("\n" + "=" * 80)


async def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "LLM Streaming Client Examples" + " " * 29 + "║")
    print("║" + " " * 15 + "Sprint 69 Feature 69.2: TTFT < 100ms" + " " * 27 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    # Run examples sequentially
    await example_basic_streaming()
    await asyncio.sleep(1)

    await example_simple_streaming()
    await asyncio.sleep(1)

    await example_high_quality_streaming()
    await asyncio.sleep(1)

    await example_concurrent_streaming()

    print("\n✅ All examples completed successfully!\n")


if __name__ == "__main__":
    asyncio.run(main())
