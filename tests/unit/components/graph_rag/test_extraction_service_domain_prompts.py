"""Unit tests for domain-aware prompt selection in ExtractionService.

Sprint 125 Feature 125.7: Domain-Aware Extraction Pipeline

Tests:
- Domain-trained prompts prioritized over generic DSPy
- Generic DSPy prompts used when no trained prompts
- Legacy prompts used when flag set
- Fallback to generic when domain lookup fails
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.components.graph_rag.extraction_service import ExtractionService


@pytest.fixture
def extraction_service():
    """Create ExtractionService instance."""
    return ExtractionService()


@pytest.mark.asyncio
async def test_domain_trained_prompts_priority(extraction_service):
    """Test that domain-trained prompts are prioritized over generic DSPy."""
    with patch(
        "src.components.domain_training.get_domain_repository"
    ) as mock_repo:
        # Mock domain repository with trained prompts
        mock_domain_repo = AsyncMock()
        mock_domain_repo.get_domain = AsyncMock(
            return_value={
                "name": "entertainment",
                "entity_prompt": "TRAINED ENTITY PROMPT for entertainment",
                "relation_prompt": "TRAINED RELATION PROMPT for entertainment",
                "status": "ready",
                "trained_at": "2026-02-01T12:00:00",
            }
        )
        mock_repo.return_value = mock_domain_repo

        # Get prompts for domain with trained prompts
        entity_prompt, relation_prompt = await extraction_service.get_extraction_prompts(
            domain="entertainment"
        )

        # Assertions
        assert "TRAINED ENTITY PROMPT" in entity_prompt
        assert "TRAINED RELATION PROMPT" in relation_prompt
        mock_domain_repo.get_domain.assert_called_once_with("entertainment")


@pytest.mark.asyncio
async def test_generic_dspy_prompts_when_no_trained(extraction_service):
    """Test that generic DSPy prompts are used when domain has no trained prompts."""
    with patch(
        "src.components.domain_training.get_domain_repository"
    ) as mock_repo, patch(
        "src.components.graph_rag.extraction_service.USE_DSPY_PROMPTS", True
    ), patch(
        "src.components.graph_rag.extraction_service.get_active_extraction_prompts"
    ) as mock_get_prompts:

        # Mock domain repository with NO trained prompts
        mock_domain_repo = AsyncMock()
        mock_domain_repo.get_domain = AsyncMock(
            return_value={
                "name": "new_domain",
                "entity_prompt": None,  # Not trained yet
                "relation_prompt": None,
                "status": "pending",
                "trained_at": None,
            }
        )
        mock_repo.return_value = mock_domain_repo

        # Mock get_active_extraction_prompts (returns DSPy prompts)
        mock_get_prompts.return_value = (
            "DSPY ENTITY PROMPT",
            "DSPY RELATION PROMPT",
        )

        # Get prompts for domain without trained prompts
        entity_prompt, relation_prompt = await extraction_service.get_extraction_prompts(
            domain="new_domain"
        )

        # Assertions
        assert entity_prompt == "DSPY ENTITY PROMPT"
        assert relation_prompt == "DSPY RELATION PROMPT"
        mock_domain_repo.get_domain.assert_called_once_with("new_domain")


@pytest.mark.asyncio
async def test_generic_dspy_prompts_when_no_domain(extraction_service):
    """Test that generic DSPy prompts are used when no domain provided."""
    with patch(
        "src.components.graph_rag.extraction_service.USE_DSPY_PROMPTS", True
    ), patch(
        "src.components.graph_rag.extraction_service.get_active_extraction_prompts"
    ) as mock_get_prompts:

        # Mock get_active_extraction_prompts
        mock_get_prompts.return_value = (
            "DSPY ENTITY PROMPT",
            "DSPY RELATION PROMPT",
        )

        # Get prompts without domain
        entity_prompt, relation_prompt = await extraction_service.get_extraction_prompts(
            domain=None
        )

        # Assertions
        assert entity_prompt == "DSPY ENTITY PROMPT"
        assert relation_prompt == "DSPY RELATION PROMPT"
        mock_get_prompts.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_to_dspy_when_domain_lookup_fails(extraction_service):
    """Test that DSPy prompts are used when domain lookup fails."""
    with patch(
        "src.components.domain_training.get_domain_repository"
    ) as mock_repo, patch(
        "src.components.graph_rag.extraction_service.USE_DSPY_PROMPTS", True
    ), patch(
        "src.components.graph_rag.extraction_service.get_active_extraction_prompts"
    ) as mock_get_prompts:

        # Mock domain repository to raise error
        mock_domain_repo = AsyncMock()
        mock_domain_repo.get_domain = AsyncMock(side_effect=Exception("Neo4j connection failed"))
        mock_repo.return_value = mock_domain_repo

        # Mock get_active_extraction_prompts
        mock_get_prompts.return_value = (
            "DSPY ENTITY PROMPT",
            "DSPY RELATION PROMPT",
        )

        # Get prompts (should fallback to DSPy, not raise)
        entity_prompt, relation_prompt = await extraction_service.get_extraction_prompts(
            domain="entertainment"
        )

        # Assertions
        assert entity_prompt == "DSPY ENTITY PROMPT"
        assert relation_prompt == "DSPY RELATION PROMPT"


@pytest.mark.asyncio
async def test_legacy_prompts_when_flag_disabled(extraction_service):
    """Test that legacy prompts are used when USE_DSPY_PROMPTS=False."""
    with patch(
        "src.components.domain_training.get_domain_repository"
    ) as mock_repo, patch(
        "src.components.graph_rag.extraction_service.USE_DSPY_PROMPTS", False
    ):

        # Mock domain repository with no trained prompts
        mock_domain_repo = AsyncMock()
        mock_domain_repo.get_domain = AsyncMock(
            return_value={
                "name": "some_domain",
                "entity_prompt": None,
                "relation_prompt": None,
                "status": "pending",
            }
        )
        mock_repo.return_value = mock_domain_repo

        # Get prompts (should use legacy)
        entity_prompt, relation_prompt = await extraction_service.get_extraction_prompts(
            domain="some_domain"
        )

        # Assertions
        # Legacy prompts contain "Extract entities" and "Extract relationships"
        assert "Extract" in entity_prompt or "entities" in entity_prompt.lower()
        assert "Extract" in relation_prompt or "relationships" in relation_prompt.lower()


@pytest.mark.asyncio
async def test_domain_not_found_fallback(extraction_service):
    """Test fallback when domain does not exist in Neo4j."""
    with patch(
        "src.components.domain_training.get_domain_repository"
    ) as mock_repo, patch(
        "src.components.graph_rag.extraction_service.USE_DSPY_PROMPTS", True
    ), patch(
        "src.components.graph_rag.extraction_service.get_active_extraction_prompts"
    ) as mock_get_prompts:

        # Mock domain repository returning None (domain not found)
        mock_domain_repo = AsyncMock()
        mock_domain_repo.get_domain = AsyncMock(return_value=None)
        mock_repo.return_value = mock_domain_repo

        # Mock get_active_extraction_prompts
        mock_get_prompts.return_value = (
            "DSPY ENTITY PROMPT",
            "DSPY RELATION PROMPT",
        )

        # Get prompts for non-existent domain
        entity_prompt, relation_prompt = await extraction_service.get_extraction_prompts(
            domain="nonexistent_domain"
        )

        # Assertions
        assert entity_prompt == "DSPY ENTITY PROMPT"
        assert relation_prompt == "DSPY RELATION PROMPT"
        mock_domain_repo.get_domain.assert_called_once_with("nonexistent_domain")
