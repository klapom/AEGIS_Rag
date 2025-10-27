"""Integration Tests for Extraction Factory - Sprint 14 Feature 14.2.

Tests the extraction factory with real services (Ollama, Neo4j) to verify:
- Pipeline creation with real extractors
- Runtime pipeline switching
- End-to-end extraction flow

Requirements:
- Ollama running on localhost:11434
- Neo4j running on localhost:7687
- Models: nomic-embed-text, gemma-3-4b-it

Author: Claude Code
Date: 2025-10-27
"""

import pytest

from src.components.graph_rag.extraction_factory import (
    ExtractionPipelineFactory,
    create_extraction_pipeline_from_config,
)
from src.core.config import get_settings


# ============================================================================
# Integration Tests - Real Services
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_factory_creates_functional_three_phase_pipeline():
    """Test factory creates a working ThreePhaseExtractor with real services."""
    settings = get_settings()

    # Create pipeline
    pipeline = ExtractionPipelineFactory.create(settings)

    # Test extraction with real text
    test_text = "Alice and Bob work together at TechCorp in San Francisco."

    entities, relations = await pipeline.extract(test_text, document_id="test_integration_1")

    # Verify we got results
    assert len(entities) > 0, "Should extract at least one entity"
    assert all("name" in e for e in entities), "All entities should have names"

    # Relations may or may not exist depending on Gemma extraction
    assert isinstance(relations, list), "Relations should be a list"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_convenience_function_with_real_config():
    """Test create_extraction_pipeline_from_config with real settings."""
    # Use default settings
    pipeline = create_extraction_pipeline_from_config()

    test_text = "Dr. Smith founded MedTech Inc. in Boston last year."

    entities, relations = await pipeline.extract(test_text, document_id="test_integration_2")

    # Verify extraction worked
    assert len(entities) > 0
    # Check entity structure
    entity_names = [e.get("name", "") for e in entities]
    assert any(name for name in entity_names), "Should have entity names"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_handles_empty_text_gracefully():
    """Test pipeline gracefully handles edge cases with real services."""
    settings = get_settings()
    pipeline = ExtractionPipelineFactory.create(settings)

    # Empty text
    entities, relations = await pipeline.extract("", document_id="test_empty")

    # Should return empty results without crashing
    assert isinstance(entities, list)
    assert isinstance(relations, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_handles_long_text():
    """Test pipeline processes longer text with real services."""
    settings = get_settings()
    pipeline = ExtractionPipelineFactory.create(settings)

    long_text = """
    Microsoft Corporation was founded by Bill Gates and Paul Allen in 1975.
    The company is headquartered in Redmond, Washington. In recent years,
    Microsoft has made significant investments in artificial intelligence and
    cloud computing through Azure. CEO Satya Nadella has led the company's
    transformation since 2014, focusing on cloud services and enterprise solutions.
    """

    entities, relations = await pipeline.extract(long_text, document_id="test_long")

    # Should extract multiple entities from longer text
    assert len(entities) >= 3, f"Should extract at least 3 entities from long text, got {len(entities)}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_semantic_dedup_enabled():
    """Test that semantic deduplication works in pipeline."""
    settings = get_settings()
    # Ensure dedup is enabled
    settings.enable_semantic_dedup = True

    pipeline = ExtractionPipelineFactory.create(settings)

    # Text with duplicate entities (different forms)
    text = "Apple Inc. was founded in California. Apple is a technology company. APPLE has millions of customers."

    entities, relations = await pipeline.extract(text, document_id="test_dedup")

    # With dedup, should have fewer entities than raw NER would find
    # (This is a soft check - exact count depends on SpaCy and dedup threshold)
    assert len(entities) > 0
    entity_names = [e.get("name", "").lower() for e in entities]

    # Should not have 3 separate "apple" entities if dedup worked
    apple_count = sum(1 for name in entity_names if "apple" in name)
    assert apple_count <= 2, f"Dedup should reduce duplicate entities, found {apple_count} 'apple' variants"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_extractions_sequential():
    """Test multiple sequential extractions work correctly."""
    settings = get_settings()
    pipeline = ExtractionPipelineFactory.create(settings)

    texts = [
        "Google was founded by Larry Page and Sergey Brin.",
        "Amazon CEO Jeff Bezos started the company in Seattle.",
        "Tesla's Elon Musk is revolutionizing electric vehicles.",
    ]

    all_entities = []

    for i, text in enumerate(texts):
        entities, relations = await pipeline.extract(text, document_id=f"test_sequential_{i}")
        all_entities.extend(entities)

    # Should have extracted entities from all texts
    assert len(all_entities) >= len(texts), "Should extract at least one entity per text"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_with_special_characters():
    """Test pipeline handles text with special characters."""
    settings = get_settings()
    pipeline = ExtractionPipelineFactory.create(settings)

    text = "Dr. O'Brien & Associates™ works with François Müller at Zürich AG (est. 2020)."

    entities, relations = await pipeline.extract(text, document_id="test_special_chars")

    # Should handle special chars without crashing
    assert isinstance(entities, list)
    assert len(entities) > 0


# ============================================================================
# E2E Scenario Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_document_processing_workflow():
    """E2E test: Full document processing with extraction factory.

    This test simulates a complete workflow:
    1. Create pipeline from config
    2. Extract entities and relations
    3. Verify data quality
    """
    # Step 1: Get pipeline
    pipeline = create_extraction_pipeline_from_config()

    # Step 2: Process document
    document = """
    OpenAI released ChatGPT in November 2022, revolutionizing conversational AI.
    The model was developed by a team led by Sam Altman in San Francisco.
    OpenAI's research focuses on safe and beneficial artificial general intelligence.
    """

    entities, relations = await pipeline.extract(document, document_id="test_e2e_workflow")

    # Step 3: Verify data quality
    assert len(entities) >= 2, "Should extract multiple entities from document"

    # Verify entity structure
    for entity in entities:
        assert "name" in entity, "Entity must have name"
        assert "type" in entity, "Entity must have type"

    # Verify relation structure (if any exist)
    for relation in relations:
        assert "source" in relation, "Relation must have source"
        assert "target" in relation, "Relation must have target"
        assert "description" in relation, "Relation must have description"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_batch_document_processing():
    """E2E test: Batch processing multiple documents.

    Simulates processing a batch of documents through the pipeline,
    typical in production ingestion scenarios.
    """
    pipeline = create_extraction_pipeline_from_config()

    documents = [
        {
            "id": "doc_1",
            "text": "Netflix was founded by Reed Hastings and Marc Randolph in 1997.",
        },
        {
            "id": "doc_2",
            "text": "Spotify is a Swedish company founded in Stockholm by Daniel Ek.",
        },
        {
            "id": "doc_3",
            "text": "Adobe Systems develops creative software including Photoshop.",
        },
    ]

    results = []

    for doc in documents:
        entities, relations = await pipeline.extract(doc["text"], document_id=doc["id"])
        results.append({
            "document_id": doc["id"],
            "entity_count": len(entities),
            "relation_count": len(relations),
            "entities": entities,
            "relations": relations,
        })

    # Verify all documents processed
    assert len(results) == 3

    # Verify we extracted entities from each document
    for result in results:
        assert result["entity_count"] > 0, f"Document {result['document_id']} should have entities"

    # Total entities should be reasonable
    total_entities = sum(r["entity_count"] for r in results)
    assert total_entities >= 6, f"Should extract at least 6 entities total, got {total_entities}"
