"""Unit tests for ExtractionService domain prompt support.

Sprint 76 Feature 76.2 (TD-085): DSPy domain-optimized prompts
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.components.graph_rag.extraction_service import ExtractionService
from src.prompts.extraction_prompts import (
    GENERIC_ENTITY_EXTRACTION_PROMPT,
    GENERIC_RELATION_EXTRACTION_PROMPT,
)


@pytest.fixture
def extraction_service():
    """Create ExtractionService instance for testing."""
    return ExtractionService()


@pytest.mark.asyncio
class TestExtractionServiceDomain:
    """Test domain-specific prompt loading in ExtractionService."""

    async def test_get_extraction_prompts_no_domain(self, extraction_service):
        """Test that generic prompts are returned when no domain is specified."""
        entity_prompt, relation_prompt = await extraction_service.get_extraction_prompts(None)

        assert entity_prompt == GENERIC_ENTITY_EXTRACTION_PROMPT
        assert relation_prompt == GENERIC_RELATION_EXTRACTION_PROMPT

    async def test_get_extraction_prompts_domain_not_found(self, extraction_service):
        """Test that generic prompts are returned when domain doesn't exist."""
        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_repo:
            mock_domain_repo = AsyncMock()
            mock_domain_repo.get_domain.return_value = None  # Domain not found
            mock_repo.return_value = mock_domain_repo

            entity_prompt, relation_prompt = await extraction_service.get_extraction_prompts(
                "nonexistent_domain"
            )

            assert entity_prompt == GENERIC_ENTITY_EXTRACTION_PROMPT
            assert relation_prompt == GENERIC_RELATION_EXTRACTION_PROMPT

    async def test_get_extraction_prompts_domain_no_custom_prompts(self, extraction_service):
        """Test fallback to generic when domain exists but has no custom prompts."""
        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_repo:
            mock_domain_repo = AsyncMock()
            # Domain exists but no entity_prompt/relation_prompt fields
            mock_domain_repo.get_domain.return_value = {
                "name": "test_domain",
                "description": "Test domain",
                "status": "trained",
                # Missing entity_prompt and relation_prompt!
            }
            mock_repo.return_value = mock_domain_repo

            entity_prompt, relation_prompt = await extraction_service.get_extraction_prompts(
                "test_domain"
            )

            assert entity_prompt == GENERIC_ENTITY_EXTRACTION_PROMPT
            assert relation_prompt == GENERIC_RELATION_EXTRACTION_PROMPT

    async def test_get_extraction_prompts_with_custom_domain_prompts(self, extraction_service):
        """Test that custom domain prompts are returned when available."""
        custom_entity_prompt = "Extract medical entities from: {text}"
        custom_relation_prompt = "Extract medical relations between: {entities} in {text}"

        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_repo:
            mock_domain_repo = AsyncMock()
            mock_domain_repo.get_domain.return_value = {
                "name": "medical_reports",
                "description": "Medical domain",
                "status": "trained",
                "entity_prompt": custom_entity_prompt,
                "relation_prompt": custom_relation_prompt,
            }
            mock_repo.return_value = mock_domain_repo

            entity_prompt, relation_prompt = await extraction_service.get_extraction_prompts(
                "medical_reports"
            )

            assert entity_prompt == custom_entity_prompt
            assert relation_prompt == custom_relation_prompt

    async def test_get_extraction_prompts_error_fallback(self, extraction_service):
        """Test that generic prompts are used when domain lookup fails."""
        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_repo:
            mock_domain_repo = AsyncMock()
            mock_domain_repo.get_domain.side_effect = Exception("Redis connection failed")
            mock_repo.return_value = mock_domain_repo

            entity_prompt, relation_prompt = await extraction_service.get_extraction_prompts(
                "test_domain"
            )

            # Should fall back to generic prompts on error
            assert entity_prompt == GENERIC_ENTITY_EXTRACTION_PROMPT
            assert relation_prompt == GENERIC_RELATION_EXTRACTION_PROMPT

    @pytest.mark.parametrize(
        "domain,should_use_custom",
        [
            (None, False),
            ("", False),
            ("medical_reports", True),
            ("legal_contracts", True),
            ("tech_docs", True),
        ],
    )
    async def test_extract_entities_uses_domain_prompts(
        self, extraction_service, domain, should_use_custom
    ):
        """Test that extract_entities() calls get_extraction_prompts() with domain."""
        custom_entity_prompt = "Custom: {text}"
        custom_relation_prompt = "Custom relations"

        with patch.object(
            extraction_service, "get_extraction_prompts", new_callable=AsyncMock
        ) as mock_get_prompts:
            # Setup mock
            if should_use_custom and domain:
                mock_get_prompts.return_value = (custom_entity_prompt, custom_relation_prompt)
            else:
                mock_get_prompts.return_value = (
                    GENERIC_ENTITY_EXTRACTION_PROMPT,
                    GENERIC_RELATION_EXTRACTION_PROMPT,
                )

            # Mock LLM proxy to avoid actual API calls
            with patch.object(extraction_service, "llm_proxy") as mock_llm_proxy:
                mock_llm_proxy.chat.return_value = '{"entities": []}'

                with patch.object(extraction_service, "_get_llm_model", new_callable=AsyncMock):
                    try:
                        await extraction_service.extract_entities(
                            text="Test text", document_id="doc_001", domain=domain
                        )
                    except Exception:
                        # We don't care if extraction fails, we just want to verify
                        # that get_extraction_prompts was called correctly
                        pass

            # Verify get_extraction_prompts was called with the domain
            # Note: May be called multiple times due to @retry decorator
            # Check that it was called at least once with the correct domain
            assert mock_get_prompts.called, "get_extraction_prompts should have been called"
            # Verify the domain parameter was passed correctly (check last call)
            mock_get_prompts.assert_called_with(domain)
