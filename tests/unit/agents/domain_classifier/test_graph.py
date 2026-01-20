"""Unit tests for Domain Classification LangGraph.

Sprint 117.2: C-LARA Hybrid Domain Classification (8 SP)

Tests the LangGraph workflow with different confidence scenarios:
- High confidence (>= 0.85) → fast_return
- Medium confidence (0.60-0.85) → llm_verify
- Low confidence (< 0.60) → llm_fallback
- force_llm override
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.domain_classifier.graph import (
    classify_clara,
    create_domain_classification_graph,
    fast_return,
    get_domain_classification_graph,
    llm_fallback_all_domains,
    llm_verify_top_k,
    route_by_confidence,
)
from src.agents.domain_classifier.state import DomainCandidate, DomainClassificationState

# ============================================================================
# Node Tests - classify_clara
# ============================================================================


def test_classify_clara_success():
    """Test C-LARA classification returns candidates."""
    state: DomainClassificationState = {
        "document_text": "This is a medical research paper about COVID-19 treatments.",
        "document_id": "doc_123",
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    result = classify_clara(state)

    assert "candidates" in result
    assert isinstance(result["candidates"], list)
    assert len(result["candidates"]) > 0
    assert "max_confidence" in result
    assert isinstance(result["max_confidence"], float)
    assert "latency_ms" in result
    assert result["latency_ms"] >= 0


def test_classify_clara_empty_text():
    """Test C-LARA handles empty document text gracefully."""
    state: DomainClassificationState = {
        "document_text": "",
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    # Should still return candidates (fallback to mock)
    result = classify_clara(state)

    assert "candidates" in result
    assert "error" not in result or result.get("error") is None


# ============================================================================
# Node Tests - fast_return
# ============================================================================


def test_fast_return_with_candidates():
    """Test fast_return returns top candidate."""
    candidates: list[DomainCandidate] = [
        {"domain_id": "medical", "confidence": 0.94, "reasoning": None, "matched_entity_types": [], "matched_intent": None},
        {"domain_id": "research", "confidence": 0.73, "reasoning": None, "matched_entity_types": [], "matched_intent": None},
    ]

    state: DomainClassificationState = {
        "document_text": "test",
        "candidates": candidates,
        "max_confidence": 0.94,
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    result = fast_return(state)

    assert result["final_domain_id"] == "medical"
    assert result["final_confidence"] == 0.94
    assert result["classification_path"] == "fast"
    assert result["classification_status"] == "confident"
    assert result["requires_review"] is False
    assert result["reasoning"] is None  # Fast path doesn't use LLM


def test_fast_return_no_candidates():
    """Test fast_return handles no candidates."""
    state: DomainClassificationState = {
        "document_text": "test",
        "candidates": [],
        "max_confidence": 0.0,
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    result = fast_return(state)

    assert result["final_domain_id"] == "general"
    assert result["final_confidence"] == 0.0
    assert result["classification_status"] == "unclassified"
    assert result["requires_review"] is True


# ============================================================================
# Node Tests - llm_verify_top_k
# ============================================================================


def test_llm_verify_top_k_success():
    """Test LLM verification enriches candidates."""
    candidates: list[DomainCandidate] = [
        {"domain_id": "medical", "confidence": 0.75, "reasoning": None, "matched_entity_types": [], "matched_intent": None},
    ]

    state: DomainClassificationState = {
        "document_text": "test document",
        "candidates": candidates,
        "max_confidence": 0.75,
        "latency_ms": 40.0,
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    result = llm_verify_top_k(state)

    assert result["final_domain_id"] == "medical"
    assert result["final_confidence"] > 0.75  # LLM should boost confidence
    assert result["classification_path"] == "verified"
    assert result["reasoning"] is not None
    assert "latency_ms" in result
    assert result["latency_ms"] > 40.0  # Should include LLM time


def test_llm_verify_handles_no_candidates():
    """Test LLM verify fallback when no candidates."""
    state: DomainClassificationState = {
        "document_text": "test",
        "candidates": [],
        "max_confidence": 0.0,
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    result = llm_verify_top_k(state)

    # Should use general domain
    assert result["final_domain_id"] == "general"
    assert result["classification_status"] == "unclassified"


# ============================================================================
# Node Tests - llm_fallback_all_domains
# ============================================================================


def test_llm_fallback_low_confidence():
    """Test LLM fallback for very low confidence."""
    candidates: list[DomainCandidate] = [
        {"domain_id": "technical", "confidence": 0.35, "reasoning": None, "matched_entity_types": [], "matched_intent": None},
    ]

    state: DomainClassificationState = {
        "document_text": "unclear document",
        "candidates": candidates,
        "max_confidence": 0.35,
        "latency_ms": 40.0,
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    result = llm_fallback_all_domains(state)

    assert result["final_domain_id"] == "general"  # Very low confidence → general
    assert result["classification_path"] == "fallback"
    assert result["classification_status"] == "unclassified"
    assert result["requires_review"] is True


def test_llm_fallback_medium_low_confidence():
    """Test LLM fallback boosts medium-low confidence."""
    candidates: list[DomainCandidate] = [
        {"domain_id": "technical", "confidence": 0.55, "reasoning": None, "matched_entity_types": [], "matched_intent": None},
    ]

    state: DomainClassificationState = {
        "document_text": "technical document",
        "candidates": candidates,
        "max_confidence": 0.55,
        "latency_ms": 40.0,
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    result = llm_fallback_all_domains(state)

    assert result["final_domain_id"] == "technical"
    assert result["final_confidence"] > 0.55  # LLM should boost
    assert result["classification_path"] == "fallback"
    assert result["classification_status"] == "uncertain"
    assert result["requires_review"] is True


# ============================================================================
# Routing Tests
# ============================================================================


def test_route_by_confidence_fast_return():
    """Test routing to fast_return for high confidence."""
    state: DomainClassificationState = {
        "document_text": "test",
        "max_confidence": 0.90,
        "force_llm": False,
        "top_k": 3,
        "threshold": 0.5,
    }

    route = route_by_confidence(state)

    assert route == "fast_return"


def test_route_by_confidence_llm_verify():
    """Test routing to llm_verify for medium confidence."""
    state: DomainClassificationState = {
        "document_text": "test",
        "max_confidence": 0.75,
        "force_llm": False,
        "top_k": 3,
        "threshold": 0.5,
    }

    route = route_by_confidence(state)

    assert route == "llm_verify"


def test_route_by_confidence_llm_fallback():
    """Test routing to llm_fallback for low confidence."""
    state: DomainClassificationState = {
        "document_text": "test",
        "max_confidence": 0.45,
        "force_llm": False,
        "top_k": 3,
        "threshold": 0.5,
    }

    route = route_by_confidence(state)

    assert route == "llm_fallback"


def test_route_by_confidence_force_llm():
    """Test force_llm overrides routing."""
    state: DomainClassificationState = {
        "document_text": "test",
        "max_confidence": 0.95,  # Would normally go to fast_return
        "force_llm": True,
        "top_k": 3,
        "threshold": 0.5,
    }

    route = route_by_confidence(state)

    assert route == "llm_verify"


# ============================================================================
# Graph Tests
# ============================================================================


def test_create_domain_classification_graph():
    """Test graph creation and compilation."""
    graph = create_domain_classification_graph()

    assert graph is not None
    # Graph should be compiled and ready to execute
    assert hasattr(graph, "ainvoke")


def test_get_domain_classification_graph_singleton():
    """Test singleton pattern for graph."""
    graph1 = get_domain_classification_graph()
    graph2 = get_domain_classification_graph()

    # Should return same instance
    assert graph1 is graph2


@pytest.mark.asyncio
async def test_graph_execution_high_confidence():
    """Test full graph execution with high confidence (fast path)."""
    graph = create_domain_classification_graph()

    initial_state: DomainClassificationState = {
        "document_text": "This is a medical research paper.",
        "document_id": "doc_123",
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    # Mock classify_clara to return high confidence
    with patch("src.agents.domain_classifier.graph.classify_clara") as mock_clara:
        mock_clara.return_value = {
            **initial_state,
            "candidates": [
                {"domain_id": "medical", "confidence": 0.92, "reasoning": None, "matched_entity_types": [], "matched_intent": None},
            ],
            "max_confidence": 0.92,
            "latency_ms": 35.0,
        }

        result = await graph.ainvoke(initial_state)

        assert result["final_domain_id"] == "medical"
        assert result["classification_path"] == "fast"
        assert result["requires_review"] is False


@pytest.mark.asyncio
async def test_graph_execution_medium_confidence():
    """Test full graph execution with medium confidence (LLM verify)."""
    graph = create_domain_classification_graph()

    initial_state: DomainClassificationState = {
        "document_text": "Technical documentation.",
        "document_id": "doc_456",
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    # Mock classify_clara to return medium confidence
    with patch("src.agents.domain_classifier.graph.classify_clara") as mock_clara:
        mock_clara.return_value = {
            **initial_state,
            "candidates": [
                {"domain_id": "technical", "confidence": 0.70, "reasoning": None, "matched_entity_types": [], "matched_intent": None},
            ],
            "max_confidence": 0.70,
            "latency_ms": 40.0,
        }

        result = await graph.ainvoke(initial_state)

        assert result["final_domain_id"] == "technical"
        assert result["classification_path"] == "verified"
        assert result["reasoning"] is not None


@pytest.mark.asyncio
async def test_graph_execution_low_confidence():
    """Test full graph execution with low confidence (LLM fallback)."""
    graph = create_domain_classification_graph()

    initial_state: DomainClassificationState = {
        "document_text": "Unclear content.",
        "document_id": "doc_789",
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    # Mock classify_clara to return low confidence
    with patch("src.agents.domain_classifier.graph.classify_clara") as mock_clara:
        mock_clara.return_value = {
            **initial_state,
            "candidates": [
                {"domain_id": "general", "confidence": 0.40, "reasoning": None, "matched_entity_types": [], "matched_intent": None},
            ],
            "max_confidence": 0.40,
            "latency_ms": 38.0,
        }

        result = await graph.ainvoke(initial_state)

        assert result["final_domain_id"] == "general"
        assert result["classification_path"] == "fallback"
        assert result["requires_review"] is True


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_classify_clara_handles_exceptions():
    """Test classify_clara error handling."""
    state: DomainClassificationState = {
        "document_text": "test",
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    # Even with potential errors, should return graceful fallback
    result = classify_clara(state)

    assert "candidates" in result
    assert isinstance(result["candidates"], list)
