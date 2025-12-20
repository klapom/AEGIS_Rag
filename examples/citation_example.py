"""Example demonstrating inline source citations (Sprint 27 Feature 27.10).

This script shows how the citation feature works similar to Perplexity.ai.
"""

import asyncio


async def demo_citation_generation():
    """Demonstrate citation generation with mock data."""
    from src.agents.answer_generator import AnswerGenerator

    # Sample contexts (what would come from retrieval)
    contexts = [
        {
            "text": "AEGIS RAG is an agentic enterprise graph intelligence system that combines vector search, graph reasoning, and temporal memory.",
            "source": "docs/CLAUDE.md",
            "title": "CLAUDE.md",
            "score": 0.95,
            "metadata": {"page": 1},
        },
        {
            "text": "The system uses LangGraph for multi-agent orchestration and supports hybrid retrieval modes.",
            "source": "docs/architecture/README.md",
            "title": "Architecture Overview",
            "score": 0.88,
            "metadata": {"section": "orchestration"},
        },
        {
            "text": "AEGIS RAG integrates with Qdrant for vector search, Neo4j for graph storage, and Redis for short-term memory.",
            "source": "docs/components/databases.md",
            "title": "Database Components",
            "score": 0.82,
            "metadata": {"component": "storage"},
        },
    ]

    print("=" * 80)
    print("AEGIS RAG Citation Demo - Feature 27.10")
    print("=" * 80)
    print()

    # Initialize answer generator
    generator = AnswerGenerator()

    query = "What is AEGIS RAG and what technologies does it use?"

    print(f"Query: {query}")
    print()
    print("Retrieved Contexts:")
    for i, ctx in enumerate(contexts, 1):
        print(f"  [{i}] {ctx['source']}: {ctx['text'][:80]}...")
    print()

    # This would normally call the LLM, but for demo purposes we'll show the expected output
    print("Expected LLM Response (with inline citations):")
    print("-" * 80)

    # Simulate what the LLM would generate
    simulated_answer = """AEGIS RAG is an agentic enterprise graph intelligence system [1] that combines vector search, graph reasoning, and temporal memory [1]. The system uses LangGraph for multi-agent orchestration [2] and supports hybrid retrieval modes [2]. It integrates with multiple databases including Qdrant for vector search, Neo4j for graph storage, and Redis for short-term memory [3]."""

    print(simulated_answer)
    print("-" * 80)
    print()

    # Show citation map structure
    print("Citation Map (sent to frontend):")
    print("-" * 80)
    citation_map = {
        1: {
            "text": contexts[0]["text"],
            "source": contexts[0]["source"],
            "title": contexts[0]["title"],
            "score": contexts[0]["score"],
            "metadata": contexts[0]["metadata"],
        },
        2: {
            "text": contexts[1]["text"],
            "source": contexts[1]["source"],
            "title": contexts[1]["title"],
            "score": contexts[1]["score"],
            "metadata": contexts[1]["metadata"],
        },
        3: {
            "text": contexts[2]["text"],
            "source": contexts[2]["source"],
            "title": contexts[2]["title"],
            "score": contexts[2]["score"],
            "metadata": contexts[2]["metadata"],
        },
    }

    import json

    print(json.dumps(citation_map, indent=2))
    print("-" * 80)
    print()

    print("Frontend Display:")
    print("-" * 80)
    print("The frontend can now:")
    print("1. Display the answer with clickable [1], [2], [3] citations")
    print("2. Show source tooltips on hover")
    print("3. Expand source details on click")
    print("4. Highlight cited sources in the source panel")
    print()

    print("API Response Format:")
    print("-" * 80)
    api_response = {
        "answer": simulated_answer,
        "query": query,
        "session_id": "demo-session-123",
        "intent": "hybrid",
        "sources": [
            {
                "text": ctx["text"][:100] + "...",
                "title": ctx["title"],
                "source": ctx["source"],
                "score": ctx["score"],
                "metadata": ctx["metadata"],
            }
            for ctx in contexts
        ],
        "citation_map": citation_map,
        "metadata": {"latency_seconds": 1.2, "agent_path": ["router", "vector_agent", "generator"]},
    }

    print(json.dumps(api_response, indent=2)[:500] + "...")
    print("-" * 80)


if __name__ == "__main__":
    asyncio.run(demo_citation_generation())
