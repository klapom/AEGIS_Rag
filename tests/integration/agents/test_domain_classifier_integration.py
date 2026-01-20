"""Integration tests for Domain Classification Workflow.

Sprint 117.2: C-LARA Hybrid Domain Classification (8 SP)

Tests the complete classification workflow end-to-end:
- API endpoint integration
- LangGraph execution
- Database interactions
- LangSmith tracing
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.api.main import app
from src.agents.domain_classifier import get_domain_classification_graph


# ============================================================================
# API Endpoint Integration Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_classify_endpoint_basic():
    """Test /admin/domains/classify endpoint basic functionality."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Mock domain repository to avoid DB dependency
        with patch("src.api.v1.domain_training.get_domain_repository") as mock_repo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.list_domains = AsyncMock(
                return_value=[
                    {"name": "medical", "description": "Medical domain"},
                    {"name": "technical", "description": "Technical domain"},
                    {"name": "general", "description": "General domain"},
                ]
            )
            mock_repo.return_value = mock_repo_instance

            response = await client.post(
                "/api/v1/admin/domains/classify",
                json={
                    "text": "This is a medical research paper about COVID-19 treatments.",
                    "top_k": 3,
                    "threshold": 0.5,
                    "force_llm": False,
                },
            )

    assert response.status_code == 200
    data = response.json()

    assert "classifications" in data
    assert "recommended" in data
    assert "confidence" in data
    assert "classification_path" in data
    assert "classification_status" in data
    assert "latency_ms" in data

    # Fast path should be used (mock returns high confidence)
    # Note: Actual path depends on mock C-LARA implementation


@pytest.mark.asyncio
@pytest.mark.integration
async def test_classify_endpoint_with_document_id():
    """Test classify endpoint with document_id tracking."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("src.api.v1.domain_training.get_domain_repository") as mock_repo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.list_domains = AsyncMock(return_value=[])
            mock_repo.return_value = mock_repo_instance

            response = await client.post(
                "/api/v1/admin/domains/classify",
                json={
                    "text": "Test document",
                    "document_id": "doc_integration_test_123",
                    "top_k": 3,
                },
            )

    assert response.status_code == 200
    data = response.json()

    assert "recommended" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_classify_endpoint_force_llm():
    """Test classify endpoint with force_llm=True."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("src.api.v1.domain_training.get_domain_repository") as mock_repo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.list_domains = AsyncMock(return_value=[])
            mock_repo.return_value = mock_repo_instance

            response = await client.post(
                "/api/v1/admin/domains/classify",
                json={
                    "text": "Medical document",
                    "force_llm": True,
                },
            )

    assert response.status_code == 200
    data = response.json()

    # Should use verified path (LLM was forced)
    # Note: Mock implementation may vary
    assert "classification_path" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_classify_endpoint_validation_errors():
    """Test classify endpoint input validation."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test empty text
        response = await client.post(
            "/api/v1/admin/domains/classify",
            json={
                "text": "",  # Too short
                "top_k": 3,
            },
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
@pytest.mark.integration
async def test_classify_endpoint_top_k_validation():
    """Test top_k parameter validation."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test top_k out of range
        response = await client.post(
            "/api/v1/admin/domains/classify",
            json={
                "text": "Valid text here",
                "top_k": 15,  # Max is 10
            },
        )

        assert response.status_code == 422


# ============================================================================
# LangGraph Workflow Integration Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_langgraph_workflow_complete():
    """Test complete LangGraph workflow execution."""
    graph = get_domain_classification_graph()

    initial_state = {
        "document_text": "This is a comprehensive medical research paper discussing novel COVID-19 treatments and vaccine efficacy.",
        "document_id": "integration_test_doc",
        "chunk_ids": ["chunk_1", "chunk_2"],
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    result = await graph.ainvoke(initial_state)

    # Verify all required fields are present
    assert "final_domain_id" in result
    assert "final_confidence" in result
    assert "classification_path" in result
    assert "classification_status" in result
    assert "requires_review" in result
    assert "latency_ms" in result
    assert "alternative_domains" in result

    # Verify confidence is valid
    assert 0.0 <= result["final_confidence"] <= 1.0

    # Verify classification status is valid
    assert result["classification_status"] in ["confident", "uncertain", "unclassified"]

    # Verify classification path is valid
    assert result["classification_path"] in ["fast", "verified", "fallback"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_langgraph_workflow_with_langsmith_metadata():
    """Test LangGraph with LangSmith tracing metadata."""
    graph = get_domain_classification_graph()

    initial_state = {
        "document_text": "Technical documentation for API design.",
        "document_id": "doc_langsmith_test",
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    # Execute with metadata (for LangSmith tracing)
    result = await graph.ainvoke(
        initial_state,
        config={
            "metadata": {
                "test_type": "integration",
                "sprint": "117.2",
                "feature": "c-lara-domain-classification",
            }
        },
    )

    assert "final_domain_id" in result
    # LangSmith metadata doesn't affect result structure


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.performance
async def test_classification_latency_fast_path():
    """Test classification latency for fast path (<50ms target)."""
    graph = get_domain_classification_graph()

    initial_state = {
        "document_text": "Medical research document.",
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    # Mock high confidence for fast path
    with patch("src.agents.domain_classifier.graph.classify_clara") as mock_clara:
        mock_clara.return_value = {
            **initial_state,
            "candidates": [
                {"domain_id": "medical", "confidence": 0.95, "reasoning": None, "matched_entity_types": [], "matched_intent": None},
            ],
            "max_confidence": 0.95,
            "latency_ms": 35.0,
        }

        result = await graph.ainvoke(initial_state)

        # Fast path should be quick
        assert result["latency_ms"] < 100  # Generous threshold for testing
        assert result["classification_path"] == "fast"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_classification_multiple_documents():
    """Test classifying multiple documents in sequence."""
    graph = get_domain_classification_graph()

    test_documents = [
        "Medical research about cancer treatments.",
        "Technical documentation for software architecture.",
        "Legal contract for service agreements.",
    ]

    results = []

    for doc_text in test_documents:
        initial_state = {
            "document_text": doc_text,
            "top_k": 3,
            "threshold": 0.5,
            "force_llm": False,
        }

        result = await graph.ainvoke(initial_state)
        results.append(result)

    # Verify all classifications succeeded
    assert len(results) == 3
    for result in results:
        assert "final_domain_id" in result
        assert result["final_confidence"] >= 0.0


# ============================================================================
# Error Handling Integration Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_classify_endpoint_error_handling():
    """Test API endpoint error handling."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Mock repository error
        with patch("src.api.v1.domain_training.get_domain_repository") as mock_repo:
            mock_repo.side_effect = Exception("Database connection failed")

            response = await client.post(
                "/api/v1/admin/domains/classify",
                json={
                    "text": "Test document",
                    "top_k": 3,
                },
            )

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_langgraph_graceful_degradation():
    """Test LangGraph handles errors gracefully."""
    graph = get_domain_classification_graph()

    # Test with problematic input
    initial_state = {
        "document_text": "x" * 100000,  # Very long text
        "top_k": 3,
        "threshold": 0.5,
        "force_llm": False,
    }

    # Should still complete without crashing
    result = await graph.ainvoke(initial_state)

    assert "final_domain_id" in result
    # May have error field, but should still return a result
