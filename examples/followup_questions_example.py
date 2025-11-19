"""Example usage of follow-up question generation.

Sprint 27 Feature 27.5: Follow-up Question Suggestions

This script demonstrates:
1. Direct usage of generate_followup_questions function
2. API endpoint usage with requests
3. Integration with conversation flow

Run:
    python examples/followup_questions_example.py
"""

import asyncio

from src.agents.followup_generator import generate_followup_questions


async def example_basic_usage():
    """Example 1: Basic follow-up question generation."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Follow-up Question Generation")
    print("=" * 80)

    query = "What is AEGIS RAG?"
    answer = (
        "AEGIS RAG (Agentic Enterprise Graph Intelligence System) is a "
        "production-ready agentic RAG system with four core components: "
        "Vector Search (Qdrant), Graph Reasoning (LightRAG + Neo4j), "
        "Temporal Memory (Graphiti), and Tool Integration (MCP)."
    )
    sources = [
        {
            "text": "AEGIS RAG uses LangGraph for multi-agent orchestration...",
            "source": "docs/CLAUDE.md",
        },
        {
            "text": "Vector search with Qdrant provides semantic retrieval...",
            "source": "docs/architecture.md",
        },
    ]

    print(f"\nQuery: {query}")
    print(f"Answer: {answer[:100]}...")
    print("\nGenerating follow-up questions...")

    questions = await generate_followup_questions(query=query, answer=answer, sources=sources)

    print(f"\nGenerated {len(questions)} follow-up questions:")
    for i, q in enumerate(questions, 1):
        print(f"{i}. {q}")


async def example_without_sources():
    """Example 2: Follow-up generation without sources."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Follow-up Generation Without Sources")
    print("=" * 80)

    query = "How does hybrid search work?"
    answer = (
        "Hybrid search combines vector similarity search with BM25 keyword search "
        "using Reciprocal Rank Fusion (RRF) to merge results."
    )

    print(f"\nQuery: {query}")
    print(f"Answer: {answer}")
    print("\nGenerating follow-up questions (no sources)...")

    questions = await generate_followup_questions(query=query, answer=answer, sources=None)

    print(f"\nGenerated {len(questions)} follow-up questions:")
    for i, q in enumerate(questions, 1):
        print(f"{i}. {q}")


async def example_long_conversation():
    """Example 3: Follow-up generation in multi-turn conversation."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Multi-Turn Conversation with Follow-ups")
    print("=" * 80)

    conversation = [
        {
            "query": "What is vector search?",
            "answer": "Vector search finds semantically similar documents using embedding vectors and similarity metrics like cosine similarity.",
        },
        {
            "query": "How does Qdrant implement vector search?",
            "answer": "Qdrant uses HNSW (Hierarchical Navigable Small World) graphs for efficient approximate nearest neighbor search with sub-linear time complexity.",
        },
        {
            "query": "What are the performance characteristics of HNSW?",
            "answer": "HNSW provides O(log N) search time with high recall (>95%) and supports billions of vectors. It trades memory for speed using graph-based indexing.",
        },
    ]

    for i, turn in enumerate(conversation, 1):
        print(f"\n--- Turn {i} ---")
        print(f"User: {turn['query']}")
        print(f"Assistant: {turn['answer'][:80]}...")

        questions = await generate_followup_questions(
            query=turn["query"], answer=turn["answer"], sources=None
        )

        print(f"\nFollow-up suggestions ({len(questions)}):")
        for j, q in enumerate(questions[:3], 1):  # Show top 3
            print(f"  {j}. {q}")


async def example_api_usage():
    """Example 4: Using the API endpoint (requires running server)."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: API Endpoint Usage")
    print("=" * 80)

    print("\nAPI Endpoint:")
    print("GET /api/v1/chat/sessions/{session_id}/followup-questions")

    print("\nExample Request:")
    print(
        """
    import requests

    session_id = "user-123-session"
    response = requests.get(
        f"http://localhost:8000/api/v1/chat/sessions/{session_id}/followup-questions"
    )

    if response.status_code == 200:
        data = response.json()
        print(f"Session: {data['session_id']}")
        print(f"From cache: {data['from_cache']}")
        print(f"Questions: {data['followup_questions']}")
    else:
        print(f"Error: {response.status_code}")
    """
    )

    print("\nExample Response:")
    print(
        """
    {
      "session_id": "user-123-session",
      "followup_questions": [
        "How does vector search work in AEGIS RAG?",
        "What role does graph reasoning play in retrieval?",
        "Can you explain the agentic architecture?"
      ],
      "generated_at": "2025-11-18T10:30:00Z",
      "from_cache": false
    }
    """
    )


async def example_error_handling():
    """Example 5: Error handling and graceful degradation."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Error Handling")
    print("=" * 80)

    # Test with empty inputs
    print("\nTest 1: Empty query and answer")
    questions = await generate_followup_questions(query="", answer="")
    print(f"Result: {len(questions)} questions (should still generate generic ones)")

    # Test with very long inputs (will be truncated)
    print("\nTest 2: Very long inputs (will be truncated)")
    long_query = "What is AEGIS RAG? " * 100  # 2000+ chars
    long_answer = "AEGIS RAG is a system. " * 100  # 2000+ chars
    questions = await generate_followup_questions(query=long_query, answer=long_answer)
    print(f"Result: {len(questions)} questions (inputs truncated to 300/500 chars)")

    print("\nAll errors are handled gracefully - no exceptions raised!")


async def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("AEGIS RAG - Follow-up Question Generation Examples")
    print("Sprint 27 Feature 27.5")
    print("=" * 80)

    await example_basic_usage()
    await example_without_sources()
    await example_long_conversation()
    await example_api_usage()
    await example_error_handling()

    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80 + "\n")

    print("Next Steps:")
    print("1. Start the API server: uvicorn src.api.main:app --reload")
    print("2. Test the endpoint with curl or Postman")
    print(
        "3. Integrate into React frontend (see docs/sprints/SPRINT_27_FEATURE_27.5_FOLLOWUP_QUESTIONS.md)"
    )
    print("4. Monitor metrics: cache hit rate, question CTR, follow-up rate")


if __name__ == "__main__":
    asyncio.run(main())
