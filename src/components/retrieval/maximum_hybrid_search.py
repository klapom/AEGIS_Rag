"""Maximum Hybrid Search - 4-Signal Fusion for AegisRAG.

Sprint 51 - Feature 51.7: Maximum Hybrid Search Foundation

This module implements the ultimate hybrid search by combining ALL retrieval signals:
1. Qdrant Embeddings (semantic similarity)
2. BM25 Keywords (exact keyword matching)
3. LightRAG Local Mode (entity-level facts)
4. LightRAG Global Mode (community/theme summaries)

Architecture:
    Query → [4 Parallel Queries] → Layer RRF → Cross-Modal Fusion → Context Assembly

Layer-wise Fusion:
    - Layer 1 (Chunks): RRF fusion of Qdrant + BM25 → unified chunk ranking
    - Layer 2 (Entities): Parse LightRAG local/global → entity list
    - Layer 3 (Cross-Modal): Align entities to chunks via MENTIONED_IN → boost chunk scores

Academic References:
    - GraphRAG (Edge et al., 2024) - arXiv:2404.16130
    - LightRAG (Guo et al., EMNLP 2025) - arXiv:2410.05779
    - RAG-Fusion (2024) - arXiv:2402.03367
    - HybridRAG (2024) - arXiv:2408.04948

Performance Target:
    - <500ms p95 latency (4 parallel queries)
    - >90% recall compared to individual methods
"""

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

from src.components.graph_rag.lightrag_wrapper import LightRAGClient
from src.components.retrieval.cross_modal_fusion import cross_modal_fusion
from src.components.retrieval.lightrag_context_parser import (
    extract_entity_names,
    parse_lightrag_global_context,
    parse_lightrag_local_context,
)
from src.utils.fusion import reciprocal_rank_fusion

# Lazy import to avoid circular dependency
# hybrid_search.py -> retrieval/__init__.py -> maximum_hybrid_search.py -> hybrid_search.py
if TYPE_CHECKING:
    from src.components.vector_search.hybrid_search import HybridSearch

logger = structlog.get_logger(__name__)


@dataclass
class MaximumHybridResult:
    """Result from Maximum Hybrid Search with metadata."""

    query: str
    results: list[dict[str, Any]]
    total_results: int

    # Signal counts
    qdrant_results_count: int
    bm25_results_count: int
    lightrag_local_entities_count: int
    lightrag_global_communities_count: int

    # Cross-modal fusion metadata
    chunks_boosted_count: int
    boost_percentage: float

    # Latency breakdown
    qdrant_latency_ms: float
    bm25_latency_ms: float
    lightrag_local_latency_ms: float
    lightrag_global_latency_ms: float
    fusion_latency_ms: float
    total_latency_ms: float

    # LightRAG context strings (for debugging)
    lightrag_local_context: str
    lightrag_global_context: str


async def maximum_hybrid_search(
    query: str,
    top_k: int = 10,
    namespaces: list[str] | None = None,
    alpha: float = 0.3,
    use_cross_modal_fusion: bool = True,
) -> MaximumHybridResult:
    """Execute 4-Signal Maximum Hybrid Search.

    This is the ultimate hybrid search that combines all retrieval methods:
    1. Qdrant embeddings (semantic)
    2. BM25 keywords (exact match)
    3. LightRAG local (entities)
    4. LightRAG global (communities)

    Args:
        query: User query string
        top_k: Number of final results to return
        namespaces: List of namespaces to search in (multi-tenant isolation)
        alpha: Weight for cross-modal entity boost (default: 0.3)
        use_cross_modal_fusion: Enable entity-chunk alignment (default: True)

    Returns:
        MaximumHybridResult with unified ranking and detailed metadata

    Example:
        >>> result = await maximum_hybrid_search("What is Amsterdam?", top_k=10)
        >>> result.total_results
        25
        >>> result.chunks_boosted_count
        8
        >>> result.results[0]["final_score"]
        0.95
    """
    start_time = time.perf_counter()

    logger.info(
        "maximum_hybrid_search_start",
        query=query[:100],
        top_k=top_k,
        namespaces=namespaces,
        alpha=alpha,
        use_cross_modal_fusion=use_cross_modal_fusion,
    )

    # Initialize components (lazy import to avoid circular dependency)
    from src.components.vector_search.hybrid_search import HybridSearch

    hybrid_search = HybridSearch()
    lightrag_client = LightRAGClient()

    # Step 1: Execute 4 parallel queries
    tasks = [
        _qdrant_search(hybrid_search, query, top_k * 2, namespaces),
        _bm25_search(hybrid_search, query, top_k * 2, namespaces),
        _lightrag_local_search(lightrag_client, query),
        _lightrag_global_search(lightrag_client, query),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Extract results (handle exceptions)
    qdrant_result = (
        results[0] if not isinstance(results[0], Exception) else {"results": [], "latency_ms": 0}
    )
    bm25_result = (
        results[1] if not isinstance(results[1], Exception) else {"results": [], "latency_ms": 0}
    )
    local_result = (
        results[2] if not isinstance(results[2], Exception) else {"context": "", "latency_ms": 0}
    )
    global_result = (
        results[3] if not isinstance(results[3], Exception) else {"context": "", "latency_ms": 0}
    )

    qdrant_chunks = qdrant_result["results"]
    bm25_chunks = bm25_result["results"]
    local_context = local_result["context"]
    global_context = global_result["context"]

    logger.debug(
        "parallel_queries_complete",
        qdrant_results=len(qdrant_chunks),
        bm25_results=len(bm25_chunks),
        local_context_length=len(local_context),
        global_context_length=len(global_context),
    )

    # Step 2: Layer-wise RRF fusion for chunk layer (Qdrant + BM25)
    fusion_start = time.perf_counter()

    chunk_ranking = []
    if qdrant_chunks or bm25_chunks:
        chunk_ranking = reciprocal_rank_fusion(
            rankings=[qdrant_chunks, bm25_chunks],
            k=60,
            id_field="id",
        )

    logger.debug(
        "chunk_layer_fusion_complete",
        fused_chunks=len(chunk_ranking),
    )

    # Step 3: Parse LightRAG contexts into structured entities
    local_parsed = parse_lightrag_local_context(local_context)
    global_parsed = parse_lightrag_global_context(global_context)

    # Extract entity names for cross-modal fusion
    local_entities = extract_entity_names(local_parsed)
    global_entities = extract_entity_names(global_parsed)

    # Combine entity lists (local entities first - they're more specific)
    all_entities = local_entities + [e for e in global_entities if e not in local_entities]

    logger.debug(
        "entity_parsing_complete",
        local_entities=len(local_entities),
        global_entities=len(global_entities),
        combined_entities=len(all_entities),
    )

    # Step 4: Cross-Modal Fusion (align entities to chunks via MENTIONED_IN)
    if use_cross_modal_fusion and all_entities and chunk_ranking:
        chunk_ranking = await cross_modal_fusion(
            chunk_ranking=chunk_ranking,
            entity_names=all_entities,
            alpha=alpha,
            allowed_namespaces=namespaces,
        )
        chunks_boosted = sum(1 for c in chunk_ranking if c.get("cross_modal_boosted", False))
        boost_percentage = (
            round(chunks_boosted / len(chunk_ranking) * 100, 1) if chunk_ranking else 0
        )
    else:
        chunks_boosted = 0
        boost_percentage = 0.0

    fusion_latency_ms = (time.perf_counter() - fusion_start) * 1000

    # Step 5: Select top-k final results
    final_results = chunk_ranking[:top_k]

    total_latency_ms = (time.perf_counter() - start_time) * 1000

    # Build result object
    result = MaximumHybridResult(
        query=query,
        results=final_results,
        total_results=len(chunk_ranking),
        qdrant_results_count=len(qdrant_chunks),
        bm25_results_count=len(bm25_chunks),
        lightrag_local_entities_count=len(local_entities),
        lightrag_global_communities_count=len(global_parsed.get("communities", [])),
        chunks_boosted_count=chunks_boosted,
        boost_percentage=boost_percentage,
        qdrant_latency_ms=qdrant_result["latency_ms"],
        bm25_latency_ms=bm25_result["latency_ms"],
        lightrag_local_latency_ms=local_result["latency_ms"],
        lightrag_global_latency_ms=global_result["latency_ms"],
        fusion_latency_ms=fusion_latency_ms,
        total_latency_ms=total_latency_ms,
        lightrag_local_context=local_context,
        lightrag_global_context=global_context,
    )

    logger.info(
        "maximum_hybrid_search_complete",
        query=query[:50],
        total_results=result.total_results,
        final_results=len(final_results),
        qdrant_count=result.qdrant_results_count,
        bm25_count=result.bm25_results_count,
        local_entities=result.lightrag_local_entities_count,
        global_communities=result.lightrag_global_communities_count,
        chunks_boosted=chunks_boosted,
        boost_pct=boost_percentage,
        total_latency_ms=round(total_latency_ms, 2),
    )

    return result


async def _qdrant_search(
    hybrid_search: "HybridSearch",
    query: str,
    top_k: int,
    namespaces: list[str] | None = None,
) -> dict[str, Any]:
    """Execute Qdrant vector search with namespace filtering.

    Args:
        hybrid_search: HybridSearch instance
        query: Search query
        top_k: Number of results
        namespaces: Namespaces to filter by

    Returns:
        Dictionary with results and latency_ms
    """
    start = time.perf_counter()

    try:
        # Use vector_search from HybridSearch (handles embeddings)

        filters = None
        if namespaces:
            # Note: MetadataFilters doesn't support namespace filtering yet
            # This is a limitation we'll need to handle separately
            pass

        results = await hybrid_search.vector_search(
            query=query,
            top_k=top_k,
            filters=filters,
        )

        # Filter by namespace manually if needed
        if namespaces:
            results = [
                r
                for r in results
                if r.get("metadata", {}).get("namespace", "default") in namespaces
            ]

        latency_ms = (time.perf_counter() - start) * 1000

        logger.debug(
            "qdrant_search_complete",
            query=query[:50],
            results=len(results),
            latency_ms=round(latency_ms, 2),
        )

        return {"results": results, "latency_ms": latency_ms}

    except Exception as e:
        logger.error("qdrant_search_failed", error=str(e), query=query[:50])
        return {"results": [], "latency_ms": 0}


async def _bm25_search(
    hybrid_search: "HybridSearch",
    query: str,
    top_k: int,
    namespaces: list[str] | None = None,
) -> dict[str, Any]:
    """Execute BM25 keyword search with namespace filtering.

    Args:
        hybrid_search: HybridSearch instance
        query: Search query
        top_k: Number of results
        namespaces: Namespaces to filter by

    Returns:
        Dictionary with results and latency_ms
    """
    start = time.perf_counter()

    try:
        results = await hybrid_search.keyword_search(
            query=query,
            top_k=top_k * 2,  # Get extra for namespace filtering
        )

        # Filter by namespace manually
        if namespaces:
            results = [
                r
                for r in results
                if r.get("metadata", {}).get("namespace", "default") in namespaces
            ][:top_k]

        latency_ms = (time.perf_counter() - start) * 1000

        logger.debug(
            "bm25_search_complete",
            query=query[:50],
            results=len(results),
            latency_ms=round(latency_ms, 2),
        )

        return {"results": results, "latency_ms": latency_ms}

    except Exception as e:
        logger.error("bm25_search_failed", error=str(e), query=query[:50])
        return {"results": [], "latency_ms": 0}


async def _lightrag_local_search(
    lightrag_client: LightRAGClient,
    query: str,
) -> dict[str, Any]:
    """Execute LightRAG local mode query (entity-level).

    Args:
        lightrag_client: LightRAGClient instance
        query: Search query

    Returns:
        Dictionary with context string and latency_ms
    """
    start = time.perf_counter()

    try:
        # Query LightRAG in local mode (only_need_context=True returns raw context)
        # Note: This requires LightRAG to support only_need_context parameter
        # Fallback: Use regular query_graph and extract context

        result = await lightrag_client.query_graph(
            query=query,
            mode="local",
        )

        # Extract context from result
        # LightRAG returns GraphQueryResult with 'answer' field
        # For maximum_hybrid_search, we treat 'answer' as the context string
        context = result.answer if hasattr(result, "answer") else ""

        latency_ms = (time.perf_counter() - start) * 1000

        logger.debug(
            "lightrag_local_search_complete",
            query=query[:50],
            context_length=len(context),
            latency_ms=round(latency_ms, 2),
        )

        return {"context": context, "latency_ms": latency_ms}

    except Exception as e:
        logger.error("lightrag_local_search_failed", error=str(e), query=query[:50])
        return {"context": "", "latency_ms": 0}


async def _lightrag_global_search(
    lightrag_client: LightRAGClient,
    query: str,
) -> dict[str, Any]:
    """Execute LightRAG global mode query (community-level).

    Args:
        lightrag_client: LightRAGClient instance
        query: Search query

    Returns:
        Dictionary with context string and latency_ms
    """
    start = time.perf_counter()

    try:
        result = await lightrag_client.query_graph(
            query=query,
            mode="global",
        )

        context = result.answer if hasattr(result, "answer") else ""

        latency_ms = (time.perf_counter() - start) * 1000

        logger.debug(
            "lightrag_global_search_complete",
            query=query[:50],
            context_length=len(context),
            latency_ms=round(latency_ms, 2),
        )

        return {"context": context, "latency_ms": latency_ms}

    except Exception as e:
        logger.error("lightrag_global_search_failed", error=str(e), query=query[:50])
        return {"context": "", "latency_ms": 0}
