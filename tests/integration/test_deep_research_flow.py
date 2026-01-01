"""Integration test for Deep Research flow.

Sprint 70 Feature 70.4: Test complete deep research workflow.

This test validates the end-to-end deep research flow:
1. Planner decomposes query
2. Searcher executes via CoordinatorAgent
3. Supervisor evaluates and decides
4. Synthesizer generates final report
"""

import pytest

from src.agents.research.research_graph import (
    create_initial_research_state,
    get_research_graph,
)


@pytest.mark.asyncio
@pytest.mark.integration
class TestDeepResearchIntegration:
    """Integration tests for deep research workflow."""

    async def test_full_research_flow_mock(self, mocker):
        """Test complete research flow with mocked components."""
        # Mock all components to avoid external dependencies

        # Mock planner
        mocker.patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mocker.MagicMock(
                generate=mocker.AsyncMock(
                    return_value=mocker.MagicMock(
                        content="1. Query 1\n2. Query 2\n3. Query 3"
                    )
                )
            ),
        )

        # Mock searcher (CoordinatorAgent)
        mocker.patch(
            "src.agents.coordinator.CoordinatorAgent",
            return_value=mocker.MagicMock(
                process_query=mocker.AsyncMock(
                    return_value={
                        "retrieved_contexts": [
                            {
                                "text": "OMNITRACKER is a workflow management system.",
                                "score": 0.9,
                                "source_channel": "vector",
                            },
                            {
                                "text": "OMNITRACKER integrates with SAP.",
                                "score": 0.8,
                                "source_channel": "graph_global",
                            },
                        ]
                    }
                )
            ),
        )

        # Mock synthesizer (AnswerGenerator)
        mocker.patch(
            "src.agents.answer_generator.AnswerGenerator",
            return_value=mocker.MagicMock(
                generate_with_citations=mocker.AsyncMock(
                    return_value={
                        "answer": "OMNITRACKER is a comprehensive workflow management system that integrates seamlessly with SAP and other enterprise systems.",
                        "sources": [
                            {"index": 1, "text": "OMNITRACKER is a workflow management system.", "score": 0.9},
                            {"index": 2, "text": "OMNITRACKER integrates with SAP.", "score": 0.8},
                        ],
                    }
                )
            ),
        )

        # Create initial state
        initial_state = create_initial_research_state(
            query="What is OMNITRACKER?",
            max_iterations=2,
            namespace="omnitracker",
        )

        # Get graph
        graph = get_research_graph()

        # Execute research
        final_state = await graph.ainvoke(initial_state)

        # Verify results
        assert final_state is not None
        assert "synthesis" in final_state
        assert "all_contexts" in final_state
        assert "sub_queries" in final_state

        # Verify synthesis was generated
        assert len(final_state["synthesis"]) > 0
        assert "OMNITRACKER" in final_state["synthesis"]

        # Verify contexts were retrieved
        assert len(final_state["all_contexts"]) > 0

        # Verify sub-queries were generated
        assert len(final_state["sub_queries"]) > 0

        # Verify iterations occurred
        assert final_state["iteration"] >= 1
        assert final_state["iteration"] <= final_state["max_iterations"]

    async def test_research_flow_stops_at_max_iterations(self, mocker):
        """Test that research stops at max iterations."""
        # Mock planner
        mocker.patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mocker.MagicMock(
                generate=mocker.AsyncMock(
                    return_value=mocker.MagicMock(content="1. Query 1")
                )
            ),
        )

        # Mock searcher to return insufficient results
        mocker.patch(
            "src.agents.coordinator.CoordinatorAgent",
            return_value=mocker.MagicMock(
                process_query=mocker.AsyncMock(
                    return_value={
                        "retrieved_contexts": [
                            {"text": "Context", "score": 0.3, "source_channel": "vector"}
                        ]
                    }
                )
            ),
        )

        # Mock synthesizer
        mocker.patch(
            "src.agents.answer_generator.AnswerGenerator",
            return_value=mocker.MagicMock(
                generate_with_citations=mocker.AsyncMock(
                    return_value={"answer": "Limited answer", "sources": []}
                )
            ),
        )

        # Create state with max 2 iterations
        initial_state = create_initial_research_state(
            query="Test query",
            max_iterations=2,
        )

        graph = get_research_graph()
        final_state = await graph.ainvoke(initial_state)

        # Should stop at max iterations even with poor quality
        assert final_state["iteration"] == 2

    async def test_research_flow_stops_on_sufficient_quality(self, mocker):
        """Test that research stops when quality is sufficient."""
        # Mock planner
        mocker.patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mocker.MagicMock(
                generate=mocker.AsyncMock(
                    return_value=mocker.MagicMock(content="1. Query 1")
                )
            ),
        )

        # Mock searcher to return excellent results
        mocker.patch(
            "src.agents.coordinator.CoordinatorAgent",
            return_value=mocker.MagicMock(
                process_query=mocker.AsyncMock(
                    return_value={
                        "retrieved_contexts": [
                            {"text": f"High quality context {i}", "score": 0.9, "source_channel": "vector"}
                            for i in range(10)
                        ]
                    }
                )
            ),
        )

        # Mock synthesizer
        mocker.patch(
            "src.agents.answer_generator.AnswerGenerator",
            return_value=mocker.MagicMock(
                generate_with_citations=mocker.AsyncMock(
                    return_value={"answer": "Comprehensive answer", "sources": [{"index": i} for i in range(5)]}
                )
            ),
        )

        # Create state
        initial_state = create_initial_research_state(
            query="Test query",
            max_iterations=5,
        )

        graph = get_research_graph()
        final_state = await graph.ainvoke(initial_state)

        # Should stop early due to sufficient quality
        assert final_state["iteration"] < 5
        assert len(final_state["all_contexts"]) >= 10

    async def test_research_flow_error_handling(self, mocker):
        """Test error handling in research flow."""
        # Mock planner to fail
        mocker.patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mocker.MagicMock(
                generate=mocker.AsyncMock(side_effect=Exception("LLM error"))
            ),
        )

        # Mock synthesizer for fallback
        mocker.patch(
            "src.agents.answer_generator.AnswerGenerator",
            return_value=mocker.MagicMock(
                generate_with_citations=mocker.AsyncMock(
                    return_value={"answer": "Fallback answer", "sources": []}
                )
            ),
        )

        # Create state
        initial_state = create_initial_research_state(query="Test query")

        graph = get_research_graph()

        # Should not crash, should use fallback
        final_state = await graph.ainvoke(initial_state)

        # Verify fallback behavior
        assert final_state is not None
        # Planner failed, so sub_queries should be [original_query] as fallback
        assert len(final_state["sub_queries"]) >= 1
        assert "error" in final_state
