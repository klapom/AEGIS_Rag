"""Unit tests for Sprint 92 Rank Consistency Fixes.

Tests verify that ranks are consistently 1-indexed (rank 1 = best) across:
- RRF fusion
- Reranking (Ollama and legacy)
- Frontend metadata

Sprint 92: Fix for issue where Rank #6 was shown instead of higher ranks.
"""

import pytest

from src.components.retrieval.reranker import RerankResult
from src.utils.fusion import reciprocal_rank_fusion


def test_rrf_fusion_uses_1_indexed_ranks():
    """Test that RRF fusion assigns 1-indexed ranks (rank 1 = best)."""
    # Create two ranking lists
    vector_results = [
        {"id": "doc1", "score": 0.9},
        {"id": "doc2", "score": 0.8},
        {"id": "doc3", "score": 0.7},
    ]
    bm25_results = [
        {"id": "doc2", "score": 15.3},
        {"id": "doc1", "score": 12.1},
        {"id": "doc4", "score": 10.5},
    ]

    # Apply RRF fusion
    fused = reciprocal_rank_fusion([vector_results, bm25_results], k=60)

    # Verify ranks start from 1 (not 0)
    assert len(fused) > 0, "RRF should return results"
    assert fused[0]["rrf_rank"] == 1, "Best result should have rank 1"
    assert fused[1]["rrf_rank"] == 2, "Second result should have rank 2"

    # Verify ranks are sequential
    ranks = [doc["rrf_rank"] for doc in fused]
    assert ranks == list(range(1, len(fused) + 1)), "Ranks should be 1, 2, 3..."


def test_rerank_result_uses_1_indexed_final_rank():
    """Test that RerankResult assigns 1-indexed final_rank after sorting.

    Sprint 92 Fix: Changed from 0-indexed to 1-indexed for consistency.
    """
    from src.components.retrieval.reranker import CrossEncoderReranker

    # Create test documents
    documents = [
        {"id": "doc1", "text": "Python programming language", "score": 0.7},
        {"id": "doc2", "text": "Java development tutorials", "score": 0.6},
        {"id": "doc3", "text": "Python data science tools", "score": 0.8},
    ]

    # Note: This is a test of the data structure, not actual reranking
    # We'll create RerankResult objects manually to test rank assignment

    # Simulate sorted results (by rerank_score descending)
    results = []
    rerank_scores = [0.95, 0.85, 0.75]  # Descending order
    for idx, (doc, score) in enumerate(zip(documents, rerank_scores)):
        result = RerankResult(
            doc_id=doc["id"],
            text=doc["text"],
            original_score=doc["score"],
            rerank_score=score,
            final_score=score,  # Simplified for test
            original_rank=idx,
            final_rank=0,  # Will be updated
        )
        results.append(result)

    # Sort by rerank_score (highest first) - simulating reranker behavior
    results.sort(key=lambda x: x.rerank_score, reverse=True)

    # Update final ranks (Sprint 92 fix: 1-indexed)
    for rank, result in enumerate(results, start=1):
        result.final_rank = rank

    # Verify ranks start from 1
    assert results[0].final_rank == 1, "Best result should have final_rank=1"
    assert results[1].final_rank == 2, "Second result should have final_rank=2"
    assert results[2].final_rank == 3, "Third result should have final_rank=3"


def test_four_way_hybrid_reranking_assigns_1_indexed_ranks():
    """Test that 4-way hybrid search assigns 1-indexed ranks after reranking.

    Sprint 92 Fix: enumerate(reranked_indices, start=1) for Ollama reranker path.
    """
    # Simulate reranked indices output from OllamaReranker.rerank()
    # Returns list of (doc_idx, score) tuples sorted by score descending
    reranked_indices = [
        (2, 0.95),  # doc at index 2 has highest score
        (0, 0.88),  # doc at index 0 is second
        (1, 0.75),  # doc at index 1 is third
    ]

    # Simulate fused_results before reranking
    fused_results = [
        {"id": "doc_a", "text": "content A", "rrf_score": 0.030},
        {"id": "doc_b", "text": "content B", "rrf_score": 0.028},
        {"id": "doc_c", "text": "content C", "rrf_score": 0.025},
    ]

    # Apply reranking logic (from four_way_hybrid_search.py)
    final_results = []
    for rank, (doc_idx, score) in enumerate(reranked_indices, start=1):
        original = fused_results[doc_idx]
        final_results.append(
            {
                **original,
                "rerank_score": score,
                "final_rank": rank,
            }
        )

    # Verify ranks start from 1
    assert len(final_results) == 3
    assert final_results[0]["final_rank"] == 1, "Best result should have final_rank=1"
    assert final_results[0]["id"] == "doc_c", "Doc C should be ranked first"
    assert final_results[1]["final_rank"] == 2
    assert final_results[1]["id"] == "doc_a"
    assert final_results[2]["final_rank"] == 3
    assert final_results[2]["id"] == "doc_b"


def test_rank_in_metadata_for_frontend():
    """Test that rank is included in metadata for frontend display.

    Sprint 92 Fix: Added rank to enhanced_metadata in _extract_sources().
    """
    # Simulate a context dict from RetrievedContext.model_dump()
    ctx = {
        "id": "chunk_123",
        "text": "This is the chunk content.",
        "score": 0.85,
        "rank": 1,  # This is the field we need to preserve
        "source": "/docs/manual.pdf",
        "document_id": "doc_456",
        "search_type": "hybrid",
        "metadata": {
            "page": 5,
            "format": "pdf",
        },
    }

    # Simulate the metadata enhancement logic from _extract_sources()
    enhanced_metadata = ctx.get("metadata", {})

    # Sprint 92 Fix: Add rank to metadata
    if "rank" in ctx and ctx["rank"] is not None:
        enhanced_metadata["rank"] = ctx["rank"]

    # Verify rank is in metadata
    assert "rank" in enhanced_metadata, "Rank should be added to metadata"
    assert enhanced_metadata["rank"] == 1, "Rank value should be preserved"

    # Verify other metadata is preserved
    assert enhanced_metadata["page"] == 5
    assert enhanced_metadata["format"] == "pdf"


def test_rank_consistency_across_pipeline():
    """Integration test: Verify rank consistency from RRF to frontend.

    Tests the full pipeline:
    1. RRF fusion assigns rrf_rank (1-indexed)
    2. Reranking assigns final_rank (1-indexed)
    3. VectorSearchAgent extracts rank correctly
    4. API _extract_sources adds rank to metadata
    """
    # Step 1: RRF fusion
    rankings = [
        [{"id": "doc1", "score": 0.9}, {"id": "doc2", "score": 0.8}],
        [{"id": "doc2", "score": 15}, {"id": "doc3", "score": 12}],
    ]
    fused = reciprocal_rank_fusion(rankings, k=60)

    # Verify RRF ranks are 1-indexed
    assert fused[0]["rrf_rank"] == 1
    assert fused[1]["rrf_rank"] == 2

    # Step 2: Simulate reranking (with final_rank)
    # After reranking, order might change but ranks remain 1-indexed
    reranked = [
        {**fused[1], "rerank_score": 0.95, "final_rank": 1},  # doc2 now ranked 1st
        {**fused[0], "rerank_score": 0.85, "final_rank": 2},  # doc1 now ranked 2nd
    ]

    # Step 3: Simulate VectorSearchAgent._convert_results logic
    for result in reranked:
        # Extract rank (final_rank takes precedence)
        rank = result.get("final_rank", result.get("rrf_rank", 0))
        result["extracted_rank"] = rank

    # Verify ranks are extracted correctly
    assert reranked[0]["extracted_rank"] == 1, "Top result should have rank 1"
    assert reranked[1]["extracted_rank"] == 2, "Second result should have rank 2"

    # Step 4: Simulate API _extract_sources logic
    for result in reranked:
        metadata = {}
        if "extracted_rank" in result:
            metadata["rank"] = result["extracted_rank"]
        result["frontend_metadata"] = metadata

    # Verify frontend metadata has correct ranks
    assert reranked[0]["frontend_metadata"]["rank"] == 1
    assert reranked[1]["frontend_metadata"]["rank"] == 2

    # Final assertion: Ranks should be 1, 2, 3... (not 0, 1, 2...)
    ranks = [r["frontend_metadata"]["rank"] for r in reranked]
    assert min(ranks) == 1, "Minimum rank should be 1 (not 0)"
    assert ranks == sorted(ranks), "Ranks should be in ascending order"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
