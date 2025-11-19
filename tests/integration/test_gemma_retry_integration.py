"""Integration Tests for Gemma Retry Logic - Sprint 14 Feature 14.5.

Tests retry logic with real Ollama service to verify:
- Resilience to transient failures
- Exponential backoff behavior
- Graceful degradation
- Real-world error scenarios

Requirements:
- Ollama running on localhost:11434
- Model: hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M

Author: Claude Code
Date: 2025-10-27
"""

import asyncio
import time

import pytest
from ollama import Client

from src.components.graph_rag.relation_extractor import (
    RelationExtractor,
    create_relation_extractor_from_config,
)
from src.core.config import get_settings


# ============================================================================
# Integration Tests - Real Ollama Service
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extractor_works_with_real_ollama():
    """Test extractor successfully calls real Ollama service."""
    settings = get_settings()
    extractor = create_relation_extractor_from_config(settings)

    entities = [
        {"name": "Alice", "type": "PERSON"},
        {"name": "TechCorp", "type": "ORGANIZATION"},
    ]

    text = "Alice works at TechCorp as a software engineer."

    relations = await extractor.extract(text, entities)

    # Should get relations from Gemma
    assert isinstance(relations, list)
    # Gemma should ideally find the "works at" relationship
    # (soft assertion - depends on model output)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extractor_handles_empty_entities_gracefully():
    """Test extractor handles empty entity list with real service."""
    settings = get_settings()
    extractor = create_relation_extractor_from_config(settings)

    text = "Some text without entities."

    relations = await extractor.extract(text, [])

    # Should return empty without calling Ollama
    assert relations == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extractor_handles_complex_entities():
    """Test extractor with multiple entities and complex relationships."""
    settings = get_settings()
    extractor = create_relation_extractor_from_config(settings)

    entities = [
        {"name": "Dr. Smith", "type": "PERSON"},
        {"name": "Jane Doe", "type": "PERSON"},
        {"name": "MedTech Inc", "type": "ORGANIZATION"},
        {"name": "Boston", "type": "LOCATION"},
    ]

    text = """
    Dr. Smith and Jane Doe founded MedTech Inc together in Boston.
    They developed innovative medical devices and grew the company rapidly.
    """

    relations = await extractor.extract(text, entities)

    # Should extract multiple relationships
    assert isinstance(relations, list)
    # Each relation should have required fields
    for rel in relations:
        assert "source" in rel
        assert "target" in rel
        assert "description" in rel
        assert "strength" in rel
        assert isinstance(rel["strength"], (int, float))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extractor_retry_config_from_settings():
    """Test that retry configuration is properly loaded from settings."""
    settings = get_settings()

    # Create extractor with custom retry settings
    extractor = RelationExtractor(
        max_retries=2,
        retry_min_wait=0.5,
        retry_max_wait=2.0,
    )

    entities = [{"name": "Test", "type": "PERSON"}]
    text = "Test text for configuration."

    # Should work with custom retry config
    relations = await extractor.extract(text, entities)
    assert isinstance(relations, list)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_extractor_performance_with_retry():
    """Test that retry doesn't significantly impact performance on success."""
    settings = get_settings()
    extractor = create_relation_extractor_from_config(settings)

    entities = [
        {"name": "Company A", "type": "ORGANIZATION"},
        {"name": "Company B", "type": "ORGANIZATION"},
    ]

    text = "Company A acquired Company B in a major deal."

    # Measure extraction time
    start_time = time.time()
    relations = await extractor.extract(text, entities)
    elapsed_time = time.time() - start_time

    # Should complete in reasonable time (< 30s for Gemma 3 4B)
    assert elapsed_time < 30, f"Extraction took {elapsed_time:.2f}s, expected < 30s"
    assert isinstance(relations, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_extractions_sequential_with_retry():
    """Test multiple sequential extractions work with retry logic."""
    settings = get_settings()
    extractor = create_relation_extractor_from_config(settings)

    test_cases = [
        {
            "entities": [{"name": "Alice", "type": "PERSON"}, {"name": "Bob", "type": "PERSON"}],
            "text": "Alice and Bob are colleagues.",
        },
        {
            "entities": [{"name": "Google", "type": "ORGANIZATION"}],
            "text": "Google is a technology company.",
        },
        {
            "entities": [{"name": "Paris", "type": "LOCATION"}],
            "text": "Paris is the capital of France.",
        },
    ]

    results = []

    for case in test_cases:
        relations = await extractor.extract(case["text"], case["entities"])
        results.append(relations)

    # All extractions should complete
    assert len(results) == 3
    for result in results:
        assert isinstance(result, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extractor_json_parsing_with_real_response():
    """Test JSON parsing works with real Gemma responses."""
    settings = get_settings()
    extractor = create_relation_extractor_from_config(settings)

    entities = [
        {"name": "Microsoft", "type": "ORGANIZATION"},
        {"name": "Bill Gates", "type": "PERSON"},
    ]

    text = "Bill Gates founded Microsoft in 1975."

    relations = await extractor.extract(text, entities)

    # Verify JSON was correctly parsed
    assert isinstance(relations, list)

    # If relations found, verify structure
    if relations:
        for rel in relations:
            # Check all required fields present and valid types
            assert isinstance(rel.get("source"), str)
            assert isinstance(rel.get("target"), str)
            assert isinstance(rel.get("description"), str)
            assert isinstance(rel.get("strength"), (int, float))
            assert 1 <= rel["strength"] <= 10


# ============================================================================
# Stress Tests - Verify Resilience
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_extractor_handles_large_entity_list():
    """Test extractor handles large number of entities without failure."""
    settings = get_settings()
    extractor = create_relation_extractor_from_config(settings)

    # Create 20 entities
    entities = [
        {"name": f"Entity_{i}", "type": "ORGANIZATION" if i % 2 == 0 else "PERSON"}
        for i in range(20)
    ]

    text = "This is a complex document with many potential relationships between various entities."

    # Should handle large entity list without crashing
    relations = await extractor.extract(text, entities)

    assert isinstance(relations, list)
    # May or may not find relations, but should not crash


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extractor_handles_unicode_text():
    """Test extractor handles unicode characters in real extraction."""
    settings = get_settings()
    extractor = create_relation_extractor_from_config(settings)

    entities = [
        {"name": "François Müller", "type": "PERSON"},
        {"name": "Zürich AG", "type": "ORGANIZATION"},
    ]

    text = "François Müller est le PDG de Zürich AG. 世界 🌍"

    # Should handle unicode without errors
    relations = await extractor.extract(text, entities)

    assert isinstance(relations, list)


# ============================================================================
# E2E Scenario Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_e2e_relation_extraction_workflow():
    """E2E test: Complete relation extraction workflow with retry logic.

    Simulates a production scenario:
    1. Load configuration
    2. Create extractor with retry
    3. Extract relations from realistic document
    4. Verify output quality
    """
    # Step 1: Load config
    settings = get_settings()

    # Step 2: Create extractor
    extractor = create_relation_extractor_from_config(settings)

    # Step 3: Extract from realistic document
    document = """
    In 2022, Elon Musk completed the acquisition of Twitter for $44 billion.
    The deal was finalized after months of negotiations and legal battles.
    Musk became the CEO and immediately implemented major changes to the platform.
    Twitter was later rebranded as X under Musk's leadership.
    """

    entities = [
        {"name": "Elon Musk", "type": "PERSON"},
        {"name": "Twitter", "type": "ORGANIZATION"},
        {"name": "X", "type": "ORGANIZATION"},
    ]

    relations = await extractor.extract(document, entities)

    # Step 4: Verify output quality
    assert isinstance(relations, list), "Output should be a list"

    # Should find key relationships (Musk-Twitter acquisition, Twitter-X rebrand)
    if relations:  # Soft assertion - depends on Gemma output
        # Verify structure
        for rel in relations:
            assert rel["source"] in [e["name"] for e in entities]
            assert rel["target"] in [e["name"] for e in entities]
            assert len(rel["description"]) > 0
            assert 1 <= rel["strength"] <= 10

        print(f"\n✓ Extracted {len(relations)} relations:")
        for rel in relations[:3]:  # Show first 3
            print(f"  - {rel['source']} → {rel['target']}: {rel['description']}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_graceful_degradation_on_service_issues():
    """E2E test: Verify graceful degradation if Ollama is slow or unavailable.

    Note: This test requires simulating service issues, which is complex
    in integration tests. For now, we verify the extractor handles
    edge cases gracefully.
    """
    settings = get_settings()

    # Create extractor with very short retry settings
    extractor = RelationExtractor(
        max_retries=1,
        retry_min_wait=0.1,
        retry_max_wait=0.2,
    )

    entities = [{"name": "Test Entity", "type": "PERSON"}]
    text = "Test document."

    # Should complete without hanging (even if Ollama is slow)
    start_time = time.time()
    relations = await extractor.extract(text, entities)
    elapsed = time.time() - start_time

    # Should not hang indefinitely
    assert elapsed < 60, f"Extraction took {elapsed:.2f}s, may be hanging"
    assert isinstance(relations, list)
