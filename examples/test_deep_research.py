"""Test Deep Research with new Supervisor Pattern Graph.

Sprint 70 Feature 70.4: Validation script for Deep Research repair.

This script tests the repaired Deep Research implementation:
1. Planner uses correct LLMTask API
2. Searcher reuses CoordinatorAgent
3. Synthesizer reuses AnswerGenerator
4. Supervisor coordinates multi-turn research

Usage:
    python examples/test_deep_research.py
"""

import asyncio
import structlog

logger = structlog.get_logger(__name__)


async def test_research_graph():
    """Test the new research graph end-to-end."""
    from src.agents.research.research_graph import (
        create_initial_research_state,
        get_research_graph,
    )

    # Test query
    query = "What is OMNITRACKER and how does it integrate with other systems?"

    logger.info("=== Testing Deep Research Graph ===")
    logger.info("test_query", query=query)

    try:
        # Create initial state
        initial_state = create_initial_research_state(
            query=query,
            max_iterations=2,  # Limit to 2 for quick test
            namespace="omnitracker",
        )

        logger.info("initial_state_created", state=initial_state)

        # Get graph
        graph = get_research_graph()
        logger.info("graph_created", graph=str(graph))

        # Execute research
        logger.info("executing_research_graph")
        final_state = await graph.ainvoke(initial_state)

        # Log results
        logger.info("research_completed", final_state=final_state)

        # Validate results
        assert final_state["synthesis"], "No synthesis generated!"
        assert len(final_state["all_contexts"]) > 0, "No contexts retrieved!"
        assert len(final_state["sub_queries"]) > 0, "No sub-queries generated!"

        logger.info(
            "=== Test Results ===",
            synthesis_length=len(final_state["synthesis"]),
            num_contexts=len(final_state["all_contexts"]),
            num_sub_queries=len(final_state["sub_queries"]),
            iterations=final_state["iteration"],
        )

        # Print synthesis (truncated)
        print("\n" + "=" * 80)
        print("SYNTHESIS:")
        print("=" * 80)
        print(final_state["synthesis"][:500] + "..." if len(final_state["synthesis"]) > 500 else final_state["synthesis"])
        print("=" * 80)

        print(f"\nSub-queries executed ({len(final_state['sub_queries'])}):")
        for i, sq in enumerate(final_state["sub_queries"], 1):
            print(f"  {i}. {sq}")

        print(f"\nContexts retrieved: {len(final_state['all_contexts'])}")
        print(f"Iterations: {final_state['iteration']}/{final_state['max_iterations']}")

        logger.info("test_passed", status="SUCCESS")
        return True

    except Exception as e:
        logger.error("test_failed", error=str(e), exc_info=True)
        return False


async def test_planner_node():
    """Test planner node in isolation."""
    from src.agents.research.planner import plan_research

    logger.info("=== Testing Planner Node ===")

    query = "Explain OMNITRACKER system architecture"

    try:
        sub_queries = await plan_research(query, max_queries=3)

        logger.info(
            "planner_test_passed",
            num_queries=len(sub_queries),
            queries=sub_queries,
        )

        print("\nPlanner generated sub-queries:")
        for i, sq in enumerate(sub_queries, 1):
            print(f"  {i}. {sq}")

        return True

    except Exception as e:
        logger.error("planner_test_failed", error=str(e), exc_info=True)
        return False


async def test_searcher_node():
    """Test searcher node in isolation."""
    from src.agents.research.searcher import execute_research_queries

    logger.info("=== Testing Searcher Node ===")

    queries = [
        "What is OMNITRACKER?",
        "How does OMNITRACKER integrate with SAP?",
    ]

    try:
        contexts = await execute_research_queries(
            queries=queries,
            namespace="omnitracker",
            top_k_per_query=3,
        )

        logger.info(
            "searcher_test_passed",
            num_contexts=len(contexts),
        )

        print(f"\nSearcher retrieved {len(contexts)} contexts")
        if contexts:
            print(f"Sample context: {contexts[0]['text'][:200]}...")

        return True

    except Exception as e:
        logger.error("searcher_test_failed", error=str(e), exc_info=True)
        return False


async def test_synthesizer_node():
    """Test synthesizer node in isolation."""
    from src.agents.research.synthesizer import synthesize_research_findings

    logger.info("=== Testing Synthesizer Node ===")

    query = "What is OMNITRACKER?"
    contexts = [
        {
            "text": "OMNITRACKER is a workflow management system.",
            "score": 0.9,
            "source_channel": "vector",
        },
        {
            "text": "OMNITRACKER integrates with SAP and other systems.",
            "score": 0.8,
            "source_channel": "graph_global",
        },
    ]

    try:
        result = await synthesize_research_findings(
            query=query,
            contexts=contexts,
            namespace="omnitracker",
        )

        logger.info(
            "synthesizer_test_passed",
            answer_length=len(result["answer"]),
            num_sources=len(result["sources"]),
        )

        print(f"\nSynthesizer generated answer ({len(result['answer'])} chars)")
        print(f"Answer: {result['answer'][:200]}...")
        print(f"Sources cited: {len(result['sources'])}")

        return True

    except Exception as e:
        logger.error("synthesizer_test_failed", error=str(e), exc_info=True)
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("DEEP RESEARCH VALIDATION - Sprint 70 Feature 70.4")
    print("=" * 80 + "\n")

    results = {
        "Planner Node": await test_planner_node(),
        "Searcher Node": await test_searcher_node(),
        "Synthesizer Node": await test_synthesizer_node(),
        "Full Research Graph": await test_research_graph(),
    }

    print("\n" + "=" * 80)
    print("TEST RESULTS:")
    print("=" * 80)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {test_name}")
    print("=" * 80)

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! Deep Research is functional.")
    else:
        print("\n❌ Some tests failed. Check logs above.")

    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
