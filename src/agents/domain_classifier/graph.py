"""Domain Classification LangGraph Workflow.

Sprint 117.2: C-LARA Hybrid Domain Classification (8 SP)

This module implements the two-stage domain classification workflow:
    Stage A: C-LARA SetFit classifier (~40ms, local)
    Stage B: LLM Verification (optional, when confidence < 0.85)

Graph Structure:
    START → classify_clara → route_by_confidence → {fast_return, llm_verify, llm_fallback} → END

Nodes:
    - classify_clara: Run C-LARA SetFit classification (Stage A)
    - fast_return: Direct return for high confidence (conf >= 0.85)
    - llm_verify_top_k: LLM verifies top-3 candidates (0.60 <= conf < 0.85)
    - llm_fallback_all_domains: Full LLM classification (conf < 0.60)

Conditional Edges:
    - route_by_confidence: Routes based on max confidence score

Performance Targets:
    - Fast path: <50ms (70-80% of requests)
    - LLM verify: <2s (15-25% of requests)
    - LLM fallback: <5s (5-10% of requests)
"""

import time
from typing import Literal

import structlog
from langgraph.graph import END, START, StateGraph

from src.agents.domain_classifier.state import DomainCandidate, DomainClassificationState

logger = structlog.get_logger(__name__)

# Confidence thresholds for routing
CONFIDENCE_THRESHOLD_FAST = 0.85  # High confidence → Fast return
CONFIDENCE_THRESHOLD_VERIFY = 0.60  # Medium confidence → LLM verify
CONFIDENCE_THRESHOLD_UNCLASSIFIED = 0.40  # Low confidence → Use "general" domain


def classify_clara(state: DomainClassificationState) -> DomainClassificationState:
    """Run C-LARA SetFit classification (Stage A).

    This node executes the fast, local SetFit classifier to generate
    initial domain candidates with confidence scores.

    Args:
        state: Current classification state with document_text

    Returns:
        Updated state with candidates and max_confidence

    Performance:
        - Latency: ~40ms (local inference, no LLM)
        - Cost: $0 (no API calls)
        - Accuracy: ~95% (from Sprint 81 C-LARA training)
    """
    start_time = time.perf_counter()

    logger.info(
        "clara_classification_started",
        document_id=state.get("document_id"),
        text_length=len(state["document_text"]),
        top_k=state.get("top_k", 3),
    )

    try:
        # TODO Sprint 117.2: Integrate C-LARA SetFit model
        # For now, return mock candidates
        # Real implementation will call:
        # from src.domains.llm_integration.clara import get_domain_classifier
        # classifier = get_domain_classifier()
        # results = classifier.classify_document(state["document_text"], top_k=state.get("top_k", 3))

        # Mock implementation for infrastructure setup
        mock_candidates: list[DomainCandidate] = [
            {
                "domain_id": "general",
                "confidence": 0.75,
                "reasoning": None,
                "matched_entity_types": [],
                "matched_intent": None,
            },
            {
                "domain_id": "technical",
                "confidence": 0.20,
                "reasoning": None,
                "matched_entity_types": [],
                "matched_intent": None,
            },
        ]

        max_confidence = max(c["confidence"] for c in mock_candidates) if mock_candidates else 0.0

        latency_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "clara_classification_complete",
            document_id=state.get("document_id"),
            num_candidates=len(mock_candidates),
            max_confidence=round(max_confidence, 4),
            latency_ms=round(latency_ms, 2),
        )

        return {
            **state,
            "candidates": mock_candidates,
            "max_confidence": max_confidence,
            "latency_ms": latency_ms,
        }

    except Exception as e:
        logger.error(
            "clara_classification_failed",
            document_id=state.get("document_id"),
            error=str(e),
            exc_info=True,
        )
        return {
            **state,
            "candidates": [],
            "max_confidence": 0.0,
            "error": f"C-LARA classification failed: {str(e)}",
        }


def fast_return(state: DomainClassificationState) -> DomainClassificationState:
    """Fast return path for high confidence classifications.

    This node is triggered when max_confidence >= 0.85.
    It returns the top candidate without LLM verification.

    Args:
        state: Current state with high-confidence candidates

    Returns:
        Final classification state

    Performance:
        - Total latency: ~40ms (C-LARA only)
        - Expected usage: 70-80% of requests
    """
    logger.info(
        "fast_return_triggered",
        document_id=state.get("document_id"),
        max_confidence=state["max_confidence"],
    )

    candidates = state["candidates"]
    top_candidate = candidates[0] if candidates else None

    if not top_candidate:
        # Fallback to "general" domain if no candidates
        return {
            **state,
            "final_domain_id": "general",
            "final_confidence": 0.0,
            "classification_path": "fast",
            "classification_status": "unclassified",
            "requires_review": True,
            "reasoning": "No candidates returned from C-LARA",
            "matched_entity_types": [],
            "matched_intent": None,
            "alternative_domains": [],
        }

    return {
        **state,
        "final_domain_id": top_candidate["domain_id"],
        "final_confidence": top_candidate["confidence"],
        "classification_path": "fast",
        "classification_status": "confident",
        "requires_review": False,
        "reasoning": None,  # Fast path doesn't provide reasoning
        "matched_entity_types": [],
        "matched_intent": None,
        "alternative_domains": candidates[1:],
    }


def llm_verify_top_k(state: DomainClassificationState) -> DomainClassificationState:
    """LLM verification of top-k candidates (Stage B - Verify).

    This node is triggered when 0.60 <= max_confidence < 0.85.
    It uses LLM to verify the top-3 C-LARA candidates with reasoning.

    Args:
        state: Current state with medium-confidence candidates

    Returns:
        Final classification state with LLM reasoning

    Performance:
        - Latency: ~2s (LLM inference)
        - Expected usage: 15-25% of requests
    """
    start_time = time.perf_counter()

    logger.info(
        "llm_verify_started",
        document_id=state.get("document_id"),
        num_candidates=len(state["candidates"]),
        max_confidence=state["max_confidence"],
    )

    try:
        # TODO Sprint 117.2: Integrate LLM verification
        # Real implementation will call LLM to verify top-3 candidates
        # from src.domains.llm_integration import get_llm_client
        # llm = get_llm_client()
        # result = llm.verify_domain_candidates(
        #     text=state["document_text"],
        #     candidates=state["candidates"][:3]
        # )

        # Mock implementation
        candidates = state["candidates"]
        top_candidate = candidates[0] if candidates else None

        if not top_candidate:
            return llm_fallback_all_domains(state)

        # Mock LLM enrichment
        verified_confidence = min(top_candidate["confidence"] + 0.10, 0.95)

        llm_latency_ms = (time.perf_counter() - start_time) * 1000
        total_latency_ms = state.get("latency_ms", 0.0) + llm_latency_ms

        logger.info(
            "llm_verify_complete",
            document_id=state.get("document_id"),
            verified_domain=top_candidate["domain_id"],
            original_confidence=top_candidate["confidence"],
            verified_confidence=verified_confidence,
            llm_latency_ms=round(llm_latency_ms, 2),
        )

        return {
            **state,
            "final_domain_id": top_candidate["domain_id"],
            "final_confidence": verified_confidence,
            "classification_path": "verified",
            "classification_status": "confident" if verified_confidence >= 0.75 else "uncertain",
            "requires_review": verified_confidence < 0.75,
            "reasoning": f"LLM verified domain '{top_candidate['domain_id']}' with high confidence",
            "matched_entity_types": ["Entity1", "Entity2"],  # Mock
            "matched_intent": "technical_documentation",  # Mock
            "alternative_domains": candidates[1:3],
            "latency_ms": total_latency_ms,
        }

    except Exception as e:
        logger.error(
            "llm_verify_failed",
            document_id=state.get("document_id"),
            error=str(e),
            exc_info=True,
        )
        # Fallback to C-LARA result
        candidates = state["candidates"]
        top_candidate = candidates[0] if candidates else None

        if not top_candidate:
            return {
                **state,
                "final_domain_id": "general",
                "final_confidence": 0.0,
                "classification_path": "verified",
                "classification_status": "unclassified",
                "requires_review": True,
                "error": f"LLM verification failed: {str(e)}",
            }

        return {
            **state,
            "final_domain_id": top_candidate["domain_id"],
            "final_confidence": top_candidate["confidence"],
            "classification_path": "verified",
            "classification_status": "uncertain",
            "requires_review": True,
            "reasoning": None,
            "error": f"LLM verification failed, using C-LARA result: {str(e)}",
        }


def llm_fallback_all_domains(state: DomainClassificationState) -> DomainClassificationState:
    """Full LLM classification fallback (Stage B - Fallback).

    This node is triggered when max_confidence < 0.60.
    It uses LLM to classify against all available domains.

    Args:
        state: Current state with low-confidence candidates

    Returns:
        Final classification state with LLM reasoning

    Performance:
        - Latency: ~5s (LLM inference with all domains)
        - Expected usage: 5-10% of requests
    """
    start_time = time.perf_counter()

    logger.info(
        "llm_fallback_started",
        document_id=state.get("document_id"),
        max_confidence=state["max_confidence"],
    )

    try:
        # TODO Sprint 117.2: Integrate full LLM classification
        # Real implementation will call LLM with all domains
        # from src.domains.llm_integration import get_llm_client
        # from src.components.domain_training import get_domain_repository
        # llm = get_llm_client()
        # repo = get_domain_repository()
        # all_domains = await repo.list_domains()
        # result = llm.classify_document(
        #     text=state["document_text"],
        #     domains=all_domains
        # )

        # Mock implementation - check if confidence is very low
        max_conf = state["max_confidence"]
        if max_conf < CONFIDENCE_THRESHOLD_UNCLASSIFIED:
            # Use "general" domain for unclassifiable documents
            logger.warning(
                "document_unclassifiable",
                document_id=state.get("document_id"),
                max_confidence=max_conf,
            )

            llm_latency_ms = (time.perf_counter() - start_time) * 1000
            total_latency_ms = state.get("latency_ms", 0.0) + llm_latency_ms

            return {
                **state,
                "final_domain_id": "general",
                "final_confidence": 0.5,  # Default confidence for fallback
                "classification_path": "fallback",
                "classification_status": "unclassified",
                "requires_review": True,
                "reasoning": "Confidence too low for all domains, using general fallback",
                "matched_entity_types": [],
                "matched_intent": None,
                "alternative_domains": state["candidates"],
                "latency_ms": total_latency_ms,
            }

        # Use LLM to boost confidence
        candidates = state["candidates"]
        top_candidate = candidates[0] if candidates else None

        if not top_candidate:
            top_candidate = {"domain_id": "general", "confidence": 0.5}

        llm_latency_ms = (time.perf_counter() - start_time) * 1000
        total_latency_ms = state.get("latency_ms", 0.0) + llm_latency_ms

        logger.info(
            "llm_fallback_complete",
            document_id=state.get("document_id"),
            final_domain=top_candidate["domain_id"],
            llm_latency_ms=round(llm_latency_ms, 2),
        )

        return {
            **state,
            "final_domain_id": top_candidate["domain_id"],
            "final_confidence": 0.65,  # LLM-boosted confidence
            "classification_path": "fallback",
            "classification_status": "uncertain",
            "requires_review": True,
            "reasoning": f"LLM fallback selected '{top_candidate['domain_id']}' after low C-LARA confidence",
            "matched_entity_types": ["FallbackEntity"],
            "matched_intent": "general",
            "alternative_domains": candidates[1:] if len(candidates) > 1 else [],
            "latency_ms": total_latency_ms,
        }

    except Exception as e:
        logger.error(
            "llm_fallback_failed",
            document_id=state.get("document_id"),
            error=str(e),
            exc_info=True,
        )

        return {
            **state,
            "final_domain_id": "general",
            "final_confidence": 0.0,
            "classification_path": "fallback",
            "classification_status": "unclassified",
            "requires_review": True,
            "reasoning": None,
            "error": f"LLM fallback failed: {str(e)}",
        }


def route_by_confidence(
    state: DomainClassificationState,
) -> Literal["fast_return", "llm_verify", "llm_fallback"]:
    """Route classification based on confidence score.

    Routing Logic:
        - conf >= 0.85  → fast_return (70-80% of requests)
        - 0.60 <= conf < 0.85 → llm_verify (15-25%)
        - conf < 0.60  → llm_fallback (5-10%)
        - force_llm=True → llm_verify (override)

    Args:
        state: Current state with max_confidence

    Returns:
        Next node name to execute
    """
    max_conf = state.get("max_confidence", 0.0)
    force_llm = state.get("force_llm", False)

    if force_llm:
        logger.info(
            "routing_forced_llm",
            document_id=state.get("document_id"),
            max_confidence=max_conf,
        )
        return "llm_verify"

    if max_conf >= CONFIDENCE_THRESHOLD_FAST:
        logger.info(
            "routing_fast_return",
            document_id=state.get("document_id"),
            max_confidence=max_conf,
        )
        return "fast_return"

    if max_conf >= CONFIDENCE_THRESHOLD_VERIFY:
        logger.info(
            "routing_llm_verify",
            document_id=state.get("document_id"),
            max_confidence=max_conf,
        )
        return "llm_verify"

    logger.info(
        "routing_llm_fallback",
        document_id=state.get("document_id"),
        max_confidence=max_conf,
    )
    return "llm_fallback"


def create_domain_classification_graph() -> StateGraph:
    """Create domain classification LangGraph workflow.

    Graph Structure:
        START → classify_clara → route_by_confidence → {fast_return, llm_verify, llm_fallback} → END

    LangSmith Tracing:
        - Automatic tracing when LANGCHAIN_TRACING_V2=true
        - Traces available at: https://smith.langchain.com
        - Project: aegis-rag (configurable via LANGCHAIN_PROJECT)
        - Each node execution is tracked with timing and state

    Returns:
        Compiled LangGraph StateGraph ready for execution

    Example:
        >>> graph = create_domain_classification_graph()
        >>> result = await graph.ainvoke(
        ...     {
        ...         "document_text": "This is a medical research paper...",
        ...         "document_id": "doc_123",
        ...         "top_k": 3,
        ...         "threshold": 0.5,
        ...         "force_llm": False
        ...     },
        ...     config={
        ...         "metadata": {
        ...             "sprint": "117.2",
        ...             "feature": "c-lara-domain-classification"
        ...         }
        ...     }
        ... )
        >>> print(result["final_domain_id"])  # "medical"
        >>> print(result["classification_path"])  # "fast"
    """
    # Create graph
    graph = StateGraph(DomainClassificationState)

    # Add nodes
    graph.add_node("classify_clara", classify_clara)
    graph.add_node("fast_return", fast_return)
    graph.add_node("llm_verify", llm_verify_top_k)
    graph.add_node("llm_fallback", llm_fallback_all_domains)

    # Add edges
    graph.add_edge(START, "classify_clara")

    # Conditional routing based on confidence
    graph.add_conditional_edges(
        "classify_clara",
        route_by_confidence,
        {
            "fast_return": "fast_return",
            "llm_verify": "llm_verify",
            "llm_fallback": "llm_fallback",
        },
    )

    # All paths end after classification
    graph.add_edge("fast_return", END)
    graph.add_edge("llm_verify", END)
    graph.add_edge("llm_fallback", END)

    # Compile with LangSmith tracing metadata
    compiled = graph.compile()

    logger.info(
        "domain_classification_graph_compiled",
        nodes=["classify_clara", "fast_return", "llm_verify", "llm_fallback"],
        tracing_enabled=True,
        note="LangSmith tracing automatic when LANGCHAIN_TRACING_V2=true",
    )

    return compiled


# Singleton graph instance
_domain_classification_graph: StateGraph | None = None


def get_domain_classification_graph() -> StateGraph:
    """Get singleton instance of domain classification graph.

    Returns:
        Compiled LangGraph StateGraph
    """
    global _domain_classification_graph
    if _domain_classification_graph is None:
        _domain_classification_graph = create_domain_classification_graph()
        logger.info("domain_classification_graph_initialized")
    return _domain_classification_graph
