"""Multi-Turn RAG Agent Implementation.

Sprint 63 Feature 63.1: Multi-Turn RAG Template (13 SP)

This module implements the LangGraph workflow for multi-turn conversations with:
- Context preparation from conversation history
- Document retrieval
- Contradiction detection
- Answer generation
- Memory summarization
"""

import time
from typing import Any

import structlog
from langgraph.graph import END, START, StateGraph

from src.agents.multi_turn.nodes import (
    answer_node,
    detect_contradictions_node,
    prepare_context_node,
    search_node,
    update_memory_node,
)
from src.agents.multi_turn.state import MultiTurnState

logger = structlog.get_logger(__name__)


class MultiTurnAgent:
    """Multi-turn conversational RAG agent.

    This agent maintains conversation context across multiple turns,
    detects contradictions, and generates memory summaries.

    Workflow:
    1. PrepareContext: Enhance query with conversation history
    2. Search: Retrieve relevant documents
    3. DetectContradictions: Check for conflicts with previous answers
    4. Answer: Generate response with LLM
    5. UpdateMemory: Summarize conversation if threshold reached
    """

    def __init__(self) -> None:
        """Initialize MultiTurnAgent with LangGraph workflow."""
        self.graph = self._compile_graph()
        logger.info("multi_turn_agent_initialized")

    def _compile_graph(self) -> Any:
        """Compile the LangGraph workflow.

        Returns:
            Compiled LangGraph workflow
        """
        # Create graph with MultiTurnState
        workflow = StateGraph(MultiTurnState)

        # Add nodes
        workflow.add_node("prepare_context", prepare_context_node)
        workflow.add_node("search", search_node)
        workflow.add_node("detect_contradictions", detect_contradictions_node)
        workflow.add_node("answer", answer_node)
        workflow.add_node("update_memory", update_memory_node)

        # Define edges
        workflow.add_edge(START, "prepare_context")
        workflow.add_edge("prepare_context", "search")
        workflow.add_edge("search", "detect_contradictions")
        workflow.add_edge("detect_contradictions", "answer")
        workflow.add_edge("answer", "update_memory")
        workflow.add_edge("update_memory", END)

        # Compile graph
        return workflow.compile()

    async def process_turn(
        self,
        query: str,
        conversation_id: str,
        conversation_history: list[dict[str, Any]],
        namespace: str = "default",
        detect_contradictions: bool = True,
        max_history_turns: int = 5,
    ) -> dict[str, Any]:
        """Process a single conversation turn.

        Args:
            query: User's query
            conversation_id: Conversation identifier
            conversation_history: Previous conversation turns
            namespace: Namespace to search in
            detect_contradictions: Enable contradiction detection
            max_history_turns: Max turns to include in context

        Returns:
            Dictionary with answer, sources, contradictions, and metadata
        """
        start_time = time.time()

        logger.info(
            "multi_turn_process_start",
            conversation_id=conversation_id,
            query=query[:100],
            history_turns=len(conversation_history),
        )

        # Convert history to ConversationTurn objects
        from src.api.models.multi_turn import ConversationTurn, Source

        conversation_turns = []
        for turn_dict in conversation_history:
            sources = [Source(**s) for s in turn_dict.get("sources", [])]
            conversation_turns.append(
                ConversationTurn(
                    query=turn_dict["query"],
                    answer=turn_dict["answer"],
                    sources=sources,
                    timestamp=turn_dict.get("timestamp"),
                    intent=turn_dict.get("intent"),
                )
            )

        # Create initial state
        initial_state = {
            "messages": [],
            "conversation_history": conversation_turns,
            "current_query": query,
            "enhanced_query": "",
            "current_context": [],
            "contradictions": [],
            "memory_summary": None,
            "namespace": namespace,
            "conversation_id": conversation_id,
            "turn_number": len(conversation_history) + 1,
            "detect_contradictions": detect_contradictions,
            "max_history_turns": max_history_turns,
            "answer": "",
            "metadata": {},
        }

        # Run through LangGraph workflow
        try:
            result = await self.graph.ainvoke(initial_state)

            # Extract results
            answer = result.get("answer", "")
            sources = []
            for ctx in result.get("current_context", []):
                sources.append(
                    Source(
                        text=ctx.get("text", "")[:500],
                        title=ctx.get("title"),
                        source=ctx.get("source"),
                        score=ctx.get("score"),
                        metadata=ctx.get("metadata", {}),
                    )
                )

            contradictions = result.get("contradictions", [])
            memory_summary = result.get("memory_summary")

            latency = time.time() - start_time

            logger.info(
                "multi_turn_process_complete",
                conversation_id=conversation_id,
                turn_number=result.get("turn_number", 1),
                latency_seconds=latency,
                sources_count=len(sources),
                contradictions_count=len(contradictions),
            )

            return {
                "answer": answer,
                "query": query,
                "conversation_id": conversation_id,
                "sources": sources,
                "contradictions": contradictions,
                "memory_summary": memory_summary,
                "turn_number": result.get("turn_number", 1),
                "metadata": {
                    "latency_seconds": latency,
                    "enhanced_query": result.get("enhanced_query", query),
                    "agent_path": [
                        "prepare_context",
                        "search",
                        "detect_contradictions",
                        "answer",
                        "update_memory",
                    ],
                },
            }

        except Exception as e:
            logger.error(
                "multi_turn_process_failed",
                conversation_id=conversation_id,
                error=str(e),
                exc_info=True,
            )
            raise
