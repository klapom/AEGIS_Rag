"""Integration test for graph query answer generation.

Sprint 79 Bug Fix: Graph query must route to answer node
Previously graph_query → END, now graph_query → answer → END

This test ensures that when using graph intent, the LangGraph workflow
correctly generates an answer from retrieved graph contexts.
"""

import pytest

from src.agents.coordinator import CoordinatorAgent


@pytest.mark.asyncio
@pytest.mark.integration
async def test_graph_query_generates_answer():
    """Test that graph query intent routes to answer generator node.

    Bug: Previously graph_query went to END, bypassing answer generation.
    Fix: Changed edge from graph_query → END to graph_query → answer → END.

    This test verifies:
    1. Graph query retrieves contexts
    2. Answer generator is invoked
    3. Final result contains "answer" key (not fallback)
    4. Agent path includes graph_query node
    """
    coordinator = CoordinatorAgent(use_persistence=False)

    # Test with amnesty_qa namespace (has graph data)
    result = await coordinator.process_query(
        query="What are the global implications of the USA Supreme Court ruling on abortion?",
        intent="graph",  # Force graph intent
        namespaces=["amnesty_qa"],
    )

    # Verify contexts were retrieved
    assert "retrieved_contexts" in result, "Graph query should retrieve contexts"
    contexts = result["retrieved_contexts"]
    assert len(contexts) > 0, f"Graph query should return contexts, got {len(contexts)}"

    # Verify answer was generated (not fallback)
    assert "answer" in result, "Result should contain 'answer' key"
    answer = result["answer"]
    assert answer, "Answer should not be empty"
    assert answer != "I'm sorry, I couldn't generate an answer. Please try rephrasing your question.", \
        "Answer should not be fallback message (answer node was invoked)"

    # Verify answer is substantive (>100 chars indicates real generation)
    assert len(answer) > 100, f"Answer should be substantive, got {len(answer)} chars"

    # Verify agent path includes graph_query
    agent_path = result.get("metadata", {}).get("agent_path", [])
    assert any("graph_query" in step for step in agent_path), \
        f"Agent path should include graph_query, got: {agent_path}"

    print(f"✅ Graph query generated answer: {len(answer)} chars")
    print(f"✅ Retrieved {len(contexts)} contexts")
    print(f"✅ Agent path: {agent_path}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_graph_query_answer_has_citations():
    """Test that graph query answers include citation markers.

    Verifies that the answer generator with citations is used for graph queries.
    """
    coordinator = CoordinatorAgent(use_persistence=False)

    result = await coordinator.process_query(
        query="What are the impacts of the USA Supreme Court abortion ruling?",
        intent="graph",
        namespaces=["amnesty_qa"],
    )

    # Verify answer and citation_map exist
    assert "answer" in result
    assert "citation_map" in result

    answer = result["answer"]
    citation_map = result["citation_map"]

    # Verify citation markers in answer ([1], [2], etc.)
    import re
    citations = re.findall(r'\[(\d+)\]', answer)

    # Should have at least one citation (since we have contexts)
    assert len(citations) > 0, f"Answer should contain citation markers, got: {answer[:200]}"

    # Verify citation_map has entries
    assert len(citation_map) > 0, "Citation map should have entries"

    print(f"✅ Answer has {len(citations)} citations")
    print(f"✅ Citation map has {len(citation_map)} entries")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_vector_and_hybrid_still_work():
    """Regression test: Ensure vector and hybrid intents still route correctly.

    Verifies that the graph query fix didn't break vector or hybrid routing.
    """
    coordinator = CoordinatorAgent(use_persistence=False)

    # Test vector intent
    vector_result = await coordinator.process_query(
        query="Test vector query",
        intent="vector",
        namespaces=["amnesty_qa"],
    )

    # Should have answer (even if "no context" fallback)
    assert "answer" in vector_result

    # Test hybrid intent
    hybrid_result = await coordinator.process_query(
        query="Test hybrid query",
        intent="hybrid",
        namespaces=["amnesty_qa"],
    )

    # Should have answer
    assert "answer" in hybrid_result

    print("✅ Vector and hybrid intents still work correctly")
