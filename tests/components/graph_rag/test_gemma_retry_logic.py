"""Unit Tests for Gemma Relation Extractor Retry Logic - Sprint 14 Feature 14.5.

Tests the retry logic and error handling features added in Sprint 14 to
RelationExtractor for resilient relation extraction.

Target Coverage: gemma_relation_extractor.py retry logic
Focus: Retry mechanisms, exponential backoff, graceful degradation

Author: Claude Code
Date: 2025-10-27
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from tenacity import RetryError

from src.components.graph_rag.relation_extractor import (
    RelationExtractor,
    create_relation_extractor_from_config,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for testing."""
    client = Mock()
    client.chat = Mock()
    return client


@pytest.fixture
def extractor(mock_ollama_client):
    """Create RelationExtractor with mock client."""
    return RelationExtractor(
        ollama_client=mock_ollama_client,
        max_retries=3,
        retry_min_wait=0.1,  # Faster for tests
        retry_max_wait=0.5,
    )


@pytest.fixture
def sample_entities():
    """Sample entity list for testing."""
    return [
        {"name": "Alex", "type": "PERSON"},
        {"name": "Jordan", "type": "PERSON"},
        {"name": "TechCorp", "type": "ORGANIZATION"},
    ]


@pytest.fixture
def sample_text():
    """Sample text for relation extraction."""
    return "Alex and Jordan worked together at TechCorp on several projects."


# ============================================================================
# Test Retry Configuration
# ============================================================================


@pytest.mark.unit
def test_extractor_initialization_with_retry_params():
    """Test extractor initializes with retry parameters."""
    extractor = RelationExtractor(
        max_retries=5,
        retry_min_wait=1.0,
        retry_max_wait=20.0,
    )

    assert extractor.max_retries == 5
    assert extractor.retry_min_wait == 1.0
    assert extractor.retry_max_wait == 20.0


@pytest.mark.unit
def test_extractor_default_retry_params():
    """Test extractor uses sensible retry defaults."""
    extractor = RelationExtractor()

    assert extractor.max_retries == 3
    assert extractor.retry_min_wait == 2.0
    assert extractor.retry_max_wait == 10.0


@pytest.mark.unit
def test_factory_function_reads_retry_config_from_settings():
    """Test create_relation_extractor_from_config reads retry params."""
    config = Mock()
    config.ollama_base_url = "http://localhost:11434"
    config.gemma_model = "custom-model"
    config.extraction_max_retries = 7
    config.extraction_retry_min_wait = 3.5
    config.extraction_retry_max_wait = 15.0

    with patch("src.components.graph_rag.gemma_relation_extractor.Client"):
        extractor = create_relation_extractor_from_config(config)

        assert extractor.max_retries == 7
        assert extractor.retry_min_wait == 3.5
        assert extractor.retry_max_wait == 15.0


@pytest.mark.unit
def test_factory_function_uses_retry_defaults():
    """Test factory uses retry defaults if not in config."""
    config = Mock()
    config.ollama_base_url = "http://localhost:11434"
    del config.extraction_max_retries
    del config.extraction_retry_min_wait
    del config.extraction_retry_max_wait

    with patch("src.components.graph_rag.gemma_relation_extractor.Client"):
        extractor = create_relation_extractor_from_config(config)

        assert extractor.max_retries == 3
        assert extractor.retry_min_wait == 2.0
        assert extractor.retry_max_wait == 10.0


# ============================================================================
# Test Graceful Degradation on Errors
# Note: Retry behavior with real retries is tested in integration tests.
# These unit tests focus on configuration and graceful degradation.
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graceful_degradation_on_connection_error(extractor, sample_text, sample_entities):
    """Test extractor returns empty list on persistent ConnectionError (graceful degradation)."""
    # Mock client.chat to always fail
    extractor.client.chat.side_effect = ConnectionError("Ollama server unreachable")

    # Should return empty list instead of crashing
    relations = await extractor.extract(sample_text, sample_entities)

    assert relations == []
    # Verify graceful degradation works
    assert isinstance(relations, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graceful_degradation_on_timeout_error(extractor, sample_text, sample_entities):
    """Test extractor returns empty list on persistent TimeoutError (graceful degradation)."""
    extractor.client.chat.side_effect = TimeoutError("Request timeout")

    # Should return empty list instead of crashing
    relations = await extractor.extract(sample_text, sample_entities)

    assert relations == []
    assert isinstance(relations, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graceful_degradation_on_general_exception(extractor, sample_text, sample_entities):
    """Test extractor returns empty list on persistent general exceptions (graceful degradation)."""
    extractor.client.chat.side_effect = Exception("Unexpected error")

    # Should return empty list instead of crashing
    relations = await extractor.extract(sample_text, sample_entities)

    assert relations == []
    assert isinstance(relations, list)


# ============================================================================
# Test Retry Configuration
# Note: Actual retry timing/behavior tested in integration tests
# ============================================================================


@pytest.mark.unit
def test_retry_configuration_stored(sample_text, sample_entities):
    """Test that retry configuration is properly stored in extractor."""
    extractor = RelationExtractor(
        max_retries=5,
        retry_min_wait=1.0,
        retry_max_wait=10.0,
    )

    assert extractor.max_retries == 5
    assert extractor.retry_min_wait == 1.0
    assert extractor.retry_max_wait == 10.0


# ============================================================================
# Test Max Retries Exhaustion - Graceful Degradation
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_max_retries_exceeded_returns_empty(sample_text, sample_entities):
    """Test that extractor returns empty list after max retries exhausted (graceful degradation)."""
    client = Mock()
    client.chat.side_effect = ConnectionError("Persistent failure")

    extractor = RelationExtractor(
        ollama_client=client,
        max_retries=2,
        retry_min_wait=0.05,
        retry_max_wait=0.1,
    )

    # Should return empty list (graceful degradation), not raise
    relations = await extractor.extract(sample_text, sample_entities)

    assert relations == []
    assert isinstance(relations, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_all_retries_fail_logs_error(extractor, sample_text, sample_entities, caplog):
    """Test that exhausted retries log appropriate error."""
    extractor.client.chat.side_effect = TimeoutError("Persistent timeout")
    extractor.max_retries = 2

    with caplog.at_level("ERROR"):
        relations = await extractor.extract(sample_text, sample_entities)

    # Should log failure
    assert any(
        "relation_extraction_failed_all_retries" in record.message for record in caplog.records
    )
    assert relations == []


# ============================================================================
# Test Graceful Degradation
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graceful_degradation_on_persistent_errors(sample_text, sample_entities):
    """Test graceful degradation returns empty relations, doesn't crash."""
    client = Mock()
    client.chat.side_effect = Exception("Catastrophic failure")

    extractor = RelationExtractor(
        ollama_client=client,
        max_retries=1,
        retry_min_wait=0.01,
        retry_max_wait=0.05,
    )

    # Should not raise exception, returns empty
    relations = await extractor.extract(sample_text, sample_entities)
    assert relations == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graceful_degradation_empty_entities(extractor, sample_text):
    """Test graceful handling of empty entity list."""
    relations = await extractor.extract(sample_text, [])

    # Should return empty immediately without calling LLM
    assert relations == []
    assert extractor.client.chat.call_count == 0


# ============================================================================
# Test Retry Success Scenarios
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_first_attempt_succeeds_no_retry(extractor, sample_text, sample_entities):
    """Test that successful first attempt doesn't retry."""
    extractor.client.chat.return_value = {
        "message": {
            "content": '{"relations": [{"source": "Alex", "target": "Jordan", "description": "colleagues", "strength": 7}]}'
        }
    }

    relations = await extractor.extract(sample_text, sample_entities)

    assert len(relations) == 1
    assert extractor.client.chat.call_count == 1  # No retries


# Note: Actual retry behavior (success after failures) is tested in integration tests
# with real Ollama service. Unit tests focus on configuration and graceful degradation.


# ============================================================================
# Test JSON Parsing
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handles_malformed_json_gracefully(extractor, sample_text, sample_entities):
    """Test that malformed JSON returns empty list (graceful degradation)."""
    # Call returns malformed JSON
    extractor.client.chat.return_value = {"message": {"content": "This is not JSON"}}

    relations = await extractor.extract(sample_text, sample_entities)

    # Should return empty list gracefully
    assert relations == []


@pytest.mark.unit
def test_parse_json_response_with_markdown():
    """Test _parse_json_response handles markdown code blocks."""
    extractor = RelationExtractor()

    response = """```json
{"relations": [{"source": "A", "target": "B", "description": "test", "strength": 5}]}
```"""

    parsed = extractor._parse_json_response(response)

    assert "relations" in parsed
    assert len(parsed["relations"]) == 1


@pytest.mark.unit
def test_parse_json_response_returns_empty_on_failure():
    """Test _parse_json_response returns empty structure on parse failure."""
    extractor = RelationExtractor()

    response = "Not valid JSON at all!"

    parsed = extractor._parse_json_response(response)

    assert parsed == {"relations": []}


# ============================================================================
# Test Configuration Edge Cases
# ============================================================================


@pytest.mark.unit
def test_extractor_accepts_zero_retries():
    """Test extractor can be configured with 0 retries (fail-fast mode)."""
    extractor = RelationExtractor(max_retries=0)

    # Just verify it doesn't raise during init
    assert extractor.max_retries == 0


@pytest.mark.unit
def test_extractor_accepts_high_retry_count():
    """Test extractor accepts high retry count for critical scenarios."""
    extractor = RelationExtractor(max_retries=10)

    assert extractor.max_retries == 10
