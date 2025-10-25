"""E2E Tests for Three-Phase Extraction Pipeline.

Sprint 13 Feature 13.9: TD-31/32/33 Performance Fix
Tests the new 3-phase extraction pipeline (SpaCy + Dedup + Gemma)
to verify it resolves LightRAG timeout issues.

Expected Performance:
- Phase 1 (SpaCy): < 1s
- Phase 2 (Dedup): < 2s
- Phase 3 (Gemma): < 20s
- Total: < 25s (vs > 300s timeout with old pipeline)
"""

import pytest
import time

from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor


# Test data from LightRAG benchmarks
FICTION_TEXT = """Alex is a powerful person, but Jordan is smarter and more talented. They worked at TechCorp together. Jordan left to found DevStart, a startup focused on AI research. Alex later joined DevStart as Chief Technology Officer. The company is developing a new framework called NeuralGraph, which they plan to present at the AI Summit in San Francisco. Taylor is working with Jordan on this project, while Cruz is managing partnerships with OpenResearch. The Device they're building uses quantum computing."""

FINANCIAL_TEXT = """Stock markets faced a sharp downturn today as tech giants saw significant declines. The Global Tech Index fell 3.4%, with Nexon Technologies dropping 7.8% after disappointing quarterly results. Analysts at MarketWatch attribute the selloff to concerns over rising interest rates and slowing consumer demand. Meanwhile, energy stocks showed resilience, with GreenPower Corp gaining 2.1% on strong earnings."""

SPORTS_TEXT = """At the World Athletics Championship in Tokyo, Noah Carter broke the 100-meter sprint record with a time of 9.58 seconds. The 24-year-old American athlete, training under Coach Maria Santos at the Elite Performance Center in California, attributed his success to innovative training methods and cutting-edge carbon-fiber spikes developed by SpeedTech. Carter's achievement surpassed the previous record held by Marcus Johnson since 2015."""


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.sprint13
@pytest.mark.timeout(120)  # Allow 120s for first test (cold start + extraction)
async def test_three_phase_extraction_fiction_text(ollama_client_real):
    """Test three-phase extraction on fiction text.

    Sprint 13 TD-31 Fix: Replaces slow LightRAG pipeline with fast 3-phase approach.

    Expected Results:
    - Total time: < 90s (first run with cold start)
    - Entities: 10-15 (deduplicated)
    - Relations: 8-12

    Performance Targets (from benchmarks):
    - Phase 1 (SpaCy): ~0.5s
    - Phase 2 (Dedup): ~1.5s
    - Phase 3 (Gemma): ~15-20s (60-90s on cold start)
    """
    start_time = time.perf_counter()

    # Initialize extractor
    extractor = ThreePhaseExtractor()

    # Run extraction
    entities, relations = await extractor.extract(FICTION_TEXT)

    total_time = time.perf_counter() - start_time

    # Verify results
    assert len(entities) >= 8, f"Expected >= 8 entities, got {len(entities)}"
    assert len(relations) >= 6, f"Expected >= 6 relations, got {len(relations)}"

    # Verify performance (allow longer for cold start)
    assert total_time < 120, f"Extraction took {total_time:.1f}s (expected < 120s with cold start)"

    # Verify entity deduplication worked
    entity_names = [e['name'] for e in entities]
    assert len(entity_names) == len(set(entity_names)), \
        f"Duplicate entities found: {entity_names}"

    print(f"[PASS] Fiction text: {len(entities)} entities, {len(relations)} relations in {total_time:.1f}s")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.sprint13
@pytest.mark.timeout(120)
async def test_three_phase_extraction_financial_text(ollama_client_real):
    """Test three-phase extraction on financial text.

    Sprint 13 TD-32 Fix: Demonstrates performance improvement over LightRAG.
    """
    start_time = time.perf_counter()

    extractor = ThreePhaseExtractor()
    entities, relations = await extractor.extract(FINANCIAL_TEXT)

    total_time = time.perf_counter() - start_time

    # Verify results
    assert len(entities) >= 4, f"Expected >= 4 entities, got {len(entities)}"
    assert len(relations) >= 3, f"Expected >= 3 relations, got {len(relations)}"
    assert total_time < 120, f"Extraction took {total_time:.1f}s (expected < 120s)"

    print(f"[PASS] Financial text: {len(entities)} entities, {len(relations)} relations in {total_time:.1f}s")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.sprint13
@pytest.mark.timeout(120)
async def test_three_phase_extraction_sports_text(ollama_client_real):
    """Test three-phase extraction on sports text.

    Sprint 13 TD-33 Fix: Verifies consistent performance across text types.
    """
    start_time = time.perf_counter()

    extractor = ThreePhaseExtractor()
    entities, relations = await extractor.extract(SPORTS_TEXT)

    total_time = time.perf_counter() - start_time

    # Verify results
    assert len(entities) >= 8, f"Expected >= 8 entities, got {len(entities)}"
    assert len(relations) >= 6, f"Expected >= 6 relations, got {len(relations)}"
    assert total_time < 120, f"Extraction took {total_time:.1f}s (expected < 120s)"

    print(f"[PASS] Sports text: {len(entities)} entities, {len(relations)} relations in {total_time:.1f}s")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.sprint13
async def test_three_phase_deduplication_works():
    """Test that semantic deduplication actually removes duplicates.

    Verifies ADR-017 implementation.
    """
    # Text with obvious duplicates
    text = """Alex works at TechCorp. Alex is the CEO of TechCorp. Jordan also works at TechCorp. Jordan and Alex are colleagues."""

    extractor = ThreePhaseExtractor()
    entities, relations = await extractor.extract(text)

    entity_names = [e['name'] for e in entities]

    # Should have deduplicated Alex and Jordan
    assert entity_names.count("Alex") <= 1, "Alex should be deduplicated"
    assert entity_names.count("Jordan") <= 1, "Jordan should be deduplicated"
    assert entity_names.count("TechCorp") <= 1, "TechCorp should be deduplicated"

    print(f"[PASS] Deduplication: {len(entities)} unique entities from text with duplicates")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.sprint13
async def test_three_phase_empty_text():
    """Test that empty text is handled gracefully."""
    extractor = ThreePhaseExtractor()
    entities, relations = await extractor.extract("")

    assert entities == [], "Empty text should return no entities"
    assert relations == [], "Empty text should return no relations"

    print("[PASS] Empty text handled correctly")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.sprint13
async def test_three_phase_can_be_disabled():
    """Test that semantic deduplication can be disabled."""
    extractor = ThreePhaseExtractor(enable_dedup=False)

    assert extractor.deduplicator is None, "Deduplicator should be None when disabled"

    # Should still work, just without deduplication
    entities, relations = await extractor.extract("Alex works at TechCorp.")

    assert len(entities) > 0, "Should still extract entities without dedup"

    print("[PASS] Extraction works with deduplication disabled")
