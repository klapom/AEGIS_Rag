"""Reciprocal Rank Fusion (RRF) for Hybrid Search.

Implementation of RRF algorithm for combining rankings from
multiple retrieval systems (e.g., Vector + BM25).

Reference: Cormack et al. 2009 - "Reciprocal Rank Fusion outperforms Condorcet
and individual Rank Learning Methods"
"""

from collections import defaultdict
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def reciprocal_rank_fusion(
    rankings: list[list[dict[str, Any]]],
    k: int = 60,
    id_field: str = "id",
) -> list[dict[str, Any]]:
    """Combine multiple rankings using Reciprocal Rank Fusion.

    Args:
        rankings: List of ranked results from different retrieval methods
        k: RRF constant (default: 60, from original paper)
        id_field: Field name for document ID (default: "id")

    Returns:
        List of re-ranked results with RRF scores

    Formula:
        RRF_score(d) = sum over all rankings r of: 1 / (k + rank_r(d))

    Example:
        >>> vector_results = [{"id": "doc1", "score": 0.9}, ...]
        >>> bm25_results = [{"id": "doc2", "score": 15.3}, ...]
        >>> fused = reciprocal_rank_fusion([vector_results, bm25_results])
    """
    if not rankings:
        return []

    # Calculate RRF scores
    rrf_scores = defaultdict(float)
    doc_data = {}  # Store original document data

    for _ranking_idx, ranking in enumerate(rankings):
        for rank, doc in enumerate(ranking, start=1):
            # Extract document ID
            doc_id = doc.get(id_field, doc.get("text", str(rank)))

            # Calculate RRF contribution: 1 / (k + rank)
            rrf_contribution = 1.0 / (k + rank)
            rrf_scores[doc_id] += rrf_contribution

            # Store document data (from first occurrence)
            if doc_id not in doc_data:
                doc_data[doc_id] = doc

    # Sort by RRF score (descending)
    sorted_docs = sorted(
        rrf_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    # Build result list
    results = []
    for rank, (doc_id, rrf_score) in enumerate(sorted_docs, start=1):
        doc = doc_data[doc_id].copy()
        doc["rrf_score"] = rrf_score
        doc["rrf_rank"] = rank
        results.append(doc)

    logger.debug(
        "RRF fusion completed",
        input_rankings=len(rankings),
        unique_documents=len(rrf_scores),
        k=k,
    )

    return results


def weighted_reciprocal_rank_fusion(
    rankings: list[list[dict[str, Any]]],
    weights: list[float] | None = None,
    k: int = 60,
    id_field: str = "id",
) -> list[dict[str, Any]]:
    """Weighted version of RRF for different ranking importance.

    Args:
        rankings: List of ranked results
        weights: Weights for each ranking (default: equal weights)
        k: RRF constant (default: 60)
        id_field: Field name for document ID

    Returns:
        List of re-ranked results with weighted RRF scores

    Example:
        >>> # Give vector search 70% weight, BM25 30% weight
        >>> results = weighted_reciprocal_rank_fusion(
        ...     [vector_results, bm25_results],
        ...     weights=[0.7, 0.3]
        ... )
    """
    if not rankings:
        return []

    # Default to equal weights
    if weights is None:
        weights = [1.0 / len(rankings)] * len(rankings)

    # Normalize weights
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    # Calculate weighted RRF scores
    rrf_scores = defaultdict(float)
    doc_data = {}

    for _ranking_idx, (ranking, weight) in enumerate(
        zip(rankings, normalized_weights, strict=False)
    ):
        for rank, doc in enumerate(ranking, start=1):
            doc_id = doc.get(id_field, doc.get("text", str(rank)))

            # Weighted RRF contribution
            rrf_contribution = weight * (1.0 / (k + rank))
            rrf_scores[doc_id] += rrf_contribution

            if doc_id not in doc_data:
                doc_data[doc_id] = doc

    # Sort by weighted RRF score
    sorted_docs = sorted(
        rrf_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    # Build result list
    results = []
    for rank, (doc_id, rrf_score) in enumerate(sorted_docs, start=1):
        doc = doc_data[doc_id].copy()
        doc["weighted_rrf_score"] = rrf_score
        doc["rrf_rank"] = rank
        results.append(doc)

    logger.debug(
        "Weighted RRF fusion completed",
        input_rankings=len(rankings),
        weights=normalized_weights,
        unique_documents=len(rrf_scores),
    )

    return results


def analyze_ranking_diversity(
    rankings: list[list[dict[str, Any]]],
    top_k: int = 10,
    id_field: str = "id",
) -> dict[str, Any]:
    """Analyze diversity and overlap between multiple rankings.

    Args:
        rankings: List of ranked results
        top_k: Analyze top-K results (default: 10)
        id_field: Field name for document ID

    Returns:
        Dictionary with diversity metrics
    """
    if not rankings:
        return {}

    # Get top-k IDs from each ranking
    ranking_sets = []
    for ranking in rankings:
        ids = [doc.get(id_field, doc.get("text", str(i))) for i, doc in enumerate(ranking[:top_k])]
        ranking_sets.append(set(ids))

    # Calculate metrics
    all_docs = set().union(*ranking_sets)
    common_docs = set.intersection(*ranking_sets)

    pairwise_overlap = []
    for i in range(len(ranking_sets)):
        for j in range(i + 1, len(ranking_sets)):
            overlap = len(ranking_sets[i] & ranking_sets[j])
            overlap_pct = (overlap / top_k) * 100
            pairwise_overlap.append(overlap_pct)

    avg_overlap = sum(pairwise_overlap) / len(pairwise_overlap) if pairwise_overlap else 0

    return {
        "total_unique_documents": len(all_docs),
        "common_documents": len(common_docs),
        "common_percentage": (len(common_docs) / top_k) * 100 if top_k > 0 else 0,
        "average_pairwise_overlap": avg_overlap,
        "ranking_count": len(rankings),
        "analyzed_top_k": top_k,
    }
