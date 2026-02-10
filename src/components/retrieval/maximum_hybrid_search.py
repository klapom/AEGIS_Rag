"""Maximum Hybrid Search - 5-Signal Fusion for AegisRAG.

Sprint 51 - Feature 51.7: Maximum Hybrid Search Foundation
Sprint 128: Replaced LightRAG with DualLevelSearch for graph queries.
Sprint 128 Feature 128.4: Added HyDE (Hypothetical Document Embeddings) as 5th signal.

This module implements the ultimate hybrid search by combining ALL retrieval signals:
1. Qdrant Embeddings (semantic similarity)
2. HyDE Embeddings (hypothetical answer document) - Sprint 128
3. BM25 Keywords (exact keyword matching)
4. Graph Local Search (entity-level facts via DualLevelSearch)
5. Graph Global Search (community/theme summaries via DualLevelSearch)

Architecture:
    Query → [5 Parallel Queries] → Layer RRF → Cross-Modal Fusion → Context Assembly

Layer-wise Fusion:
    - Layer 1 (Chunks): RRF fusion of Qdrant + HyDE + BM25 → unified chunk ranking
    - Layer 2 (Entities): DualLevelSearch local/global → entity list
    - Layer 3 (Cross-Modal): Align entities to chunks via MENTIONED_IN → boost chunk scores

Academic References:
    - GraphRAG (Edge et al., 2024) - arXiv:2404.16130
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

from src.components.graph_rag.dual_level_search import get_dual_level_search
from src.components.retrieval.cross_modal_fusion import cross_modal_fusion
from src.components.retrieval.hyde import get_hyde_generator
from src.core.config import settings
from src.utils.fusion import reciprocal_rank_fusion

# Lazy import to avoid circular dependency
# hybrid_search.py -> retrieval/__init__.py -> maximum_hybrid_search.py -> hybrid_search.py
if TYPE_CHECKING:
    from src.components.vector_search.hybrid_search import HybridSearch

logger = structlog.get_logger(__name__)


@dataclass
class MaximumHybridResult:
    """Result from Maximum Hybrid Search with metadata.

    Sprint 128 Feature 128.4: Added HyDE signal tracking.
    """

    query: str
    results: list[dict[str, Any]]
    total_results: int

    # Signal counts
    qdrant_results_count: int
    hyde_results_count: int  # Sprint 128: HyDE signal
    bm25_results_count: int
    graph_local_entities_count: int
    graph_global_communities_count: int

    # Cross-modal fusion metadata
    chunks_boosted_count: int
    boost_percentage: float

    # Latency breakdown
    qdrant_latency_ms: float
    hyde_latency_ms: float  # Sprint 128: HyDE latency
    bm25_latency_ms: float
    graph_local_latency_ms: float
    graph_global_latency_ms: float
    fusion_latency_ms: float
    total_latency_ms: float

    # Graph context strings (for debugging)
    graph_local_context: str
    graph_global_context: str

    # Sprint 128: HyDE metadata
    hyde_enabled: bool
    hypothetical_document: str | None


async def maximum_hybrid_search(
    query: str,
    top_k: int = 10,
    namespaces: list[str] | None = None,
    alpha: float = 0.3,
    use_cross_modal_fusion: bool = True,
) -> MaximumHybridResult:
    """Execute 5-Signal Maximum Hybrid Search.

    Sprint 128 Feature 128.4: Added HyDE (Hypothetical Document Embeddings) as 5th signal.

    This is the ultimate hybrid search that combines all retrieval methods:
    1. Qdrant embeddings (semantic)
    2. HyDE embeddings (hypothetical answer document) - Sprint 128
    3. BM25 keywords (exact match)
    4. Graph local search (entities via DualLevelSearch)
    5. Graph global search (communities via DualLevelSearch)

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
    dual_search = get_dual_level_search()

    # Sprint 128 Feature 128.4 + Sprint 129.8: HyDE with intent guard
    # Skip HyDE for factual queries (entity lookups benefit from graph, not hypothetical docs)
    hyde_generator = None
    hyde_skipped_reason = None
    if settings.hyde_enabled:
        try:
            from src.components.retrieval.intent_classifier import CLARAIntent, classify_intent

            intent_result = await classify_intent(query)
            if intent_result.intent == CLARAIntent.FACTUAL:
                hyde_skipped_reason = "factual_query"
                logger.info(
                    "hyde_skipped",
                    reason="factual_query",
                    intent=intent_result.intent.value,
                    confidence=intent_result.confidence,
                    query=query[:80],
                )
            elif intent_result.intent == CLARAIntent.NAVIGATION:
                hyde_skipped_reason = "navigation_query"
                logger.info(
                    "hyde_skipped",
                    reason="navigation_query",
                    intent=intent_result.intent.value,
                    confidence=intent_result.confidence,
                    query=query[:80],
                )
            else:
                hyde_generator = get_hyde_generator()
                logger.debug(
                    "hyde_enabled_for_query",
                    intent=intent_result.intent.value,
                    query=query[:80],
                )
        except Exception as e:
            # If classification fails, enable HyDE as fallback
            hyde_generator = get_hyde_generator()
            logger.warning("hyde_intent_guard_failed", error=str(e))

    # Step 1: Execute 5 parallel queries (4 base + HyDE if enabled)
    tasks = [
        _qdrant_search(hybrid_search, query, top_k * 2, namespaces),
        _bm25_search(hybrid_search, query, top_k * 2, namespaces),
        _graph_local_search(dual_search, query, namespaces),
        _graph_global_search(dual_search, query, namespaces),
    ]

    # Sprint 128 + 129.8: Add HyDE search if generator is active (intent-gated)
    if hyde_generator is not None:
        tasks.append(_hyde_search(hyde_generator, query, top_k * 2, namespaces))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Extract results (handle exceptions)
    qdrant_result = (
        results[0] if not isinstance(results[0], Exception) else {"results": [], "latency_ms": 0}
    )
    bm25_result = (
        results[1] if not isinstance(results[1], Exception) else {"results": [], "latency_ms": 0}
    )
    local_result = (
        results[2]
        if not isinstance(results[2], Exception)
        else {"entities": [], "context": "", "latency_ms": 0}
    )
    global_result = (
        results[3]
        if not isinstance(results[3], Exception)
        else {"entities": [], "context": "", "latency_ms": 0, "communities_count": 0}
    )

    # Sprint 128 + 129.8: Extract HyDE results if generator was active
    hyde_result = {"results": [], "latency_ms": 0, "hypothetical_doc": None}
    if hyde_generator is not None:
        hyde_result = (
            results[4]
            if not isinstance(results[4], Exception)
            else {"results": [], "latency_ms": 0, "hypothetical_doc": None}
        )

    qdrant_chunks = qdrant_result["results"]
    bm25_chunks = bm25_result["results"]
    hyde_chunks = hyde_result["results"]

    # Sprint 128: Entity names come directly from DualLevelSearch (no text parsing needed)
    local_entities = local_result["entities"]
    global_entities = global_result["entities"]
    local_context = local_result["context"]
    global_context = global_result["context"]

    logger.debug(
        "parallel_queries_complete",
        qdrant_results=len(qdrant_chunks),
        hyde_results=len(hyde_chunks),
        bm25_results=len(bm25_chunks),
        local_entities=len(local_entities),
        global_entities=len(global_entities),
    )

    # Step 2: Layer-wise RRF fusion for chunk layer (Qdrant + HyDE + BM25)
    fusion_start = time.perf_counter()

    chunk_ranking = []
    if qdrant_chunks or hyde_chunks or bm25_chunks:
        # Sprint 128 + 129.8: Include HyDE in RRF fusion if generator was active
        rankings = [qdrant_chunks, bm25_chunks]
        if hyde_generator is not None and hyde_chunks:
            rankings.insert(1, hyde_chunks)  # Insert HyDE after dense search

        chunk_ranking = reciprocal_rank_fusion(
            rankings=rankings,
            k=60,
            id_field="id",
        )

    logger.debug(
        "chunk_layer_fusion_complete",
        fused_chunks=len(chunk_ranking),
        hyde_included=settings.hyde_enabled and len(hyde_chunks) > 0,
    )

    # Step 3: Combine entity lists (local entities first - they're more specific)
    all_entities = local_entities + [e for e in global_entities if e not in local_entities]

    logger.debug(
        "entity_extraction_complete",
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

    # Build result object (Sprint 128: Include HyDE metadata)
    result = MaximumHybridResult(
        query=query,
        results=final_results,
        total_results=len(chunk_ranking),
        qdrant_results_count=len(qdrant_chunks),
        hyde_results_count=len(hyde_chunks),  # Sprint 128
        bm25_results_count=len(bm25_chunks),
        graph_local_entities_count=len(local_entities),
        graph_global_communities_count=global_result.get("communities_count", 0),
        chunks_boosted_count=chunks_boosted,
        boost_percentage=boost_percentage,
        qdrant_latency_ms=qdrant_result["latency_ms"],
        hyde_latency_ms=hyde_result["latency_ms"],  # Sprint 128
        bm25_latency_ms=bm25_result["latency_ms"],
        graph_local_latency_ms=local_result["latency_ms"],
        graph_global_latency_ms=global_result["latency_ms"],
        fusion_latency_ms=fusion_latency_ms,
        total_latency_ms=total_latency_ms,
        graph_local_context=local_context,
        graph_global_context=global_context,
        hyde_enabled=hyde_generator
        is not None,  # Sprint 129.8: reflects actual use (not just setting)
        hypothetical_document=hyde_result.get("hypothetical_doc"),  # Sprint 128
    )

    logger.info(
        "maximum_hybrid_search_complete",
        query=query[:50],
        total_results=result.total_results,
        final_results=len(final_results),
        qdrant_count=result.qdrant_results_count,
        hyde_count=result.hyde_results_count,  # Sprint 128
        hyde_enabled=result.hyde_enabled,  # Sprint 128
        bm25_count=result.bm25_results_count,
        local_entities=result.graph_local_entities_count,
        global_communities=result.graph_global_communities_count,
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


async def _graph_local_search(
    dual_search: Any,
    query: str,
    namespaces: list[str] | None = None,
) -> dict[str, Any]:
    """Execute graph local search via DualLevelSearch (entity-level).

    Sprint 128: Replaced LightRAG with DualLevelSearch.local_search().
    Returns structured entity names directly — no text parsing needed.

    Args:
        dual_search: DualLevelSearch instance
        query: Search query
        namespaces: Namespaces to filter by

    Returns:
        Dictionary with entities list, context string, and latency_ms
    """
    start = time.perf_counter()

    try:
        graph_entities, metadata = await dual_search.local_search(
            query=query, top_k=5, namespaces=namespaces
        )

        # Extract entity names from GraphEntity.properties["matched_entities"]
        entity_names = []
        for ge in graph_entities:
            matched = ge.properties.get("matched_entities", []) if ge.properties else []
            entity_names.extend(matched)
        entity_names = sorted(set(entity_names))

        # Build context string for debugging
        context = "; ".join(f"{ge.name}" for ge in graph_entities)

        latency_ms = (time.perf_counter() - start) * 1000

        logger.debug(
            "graph_local_search_complete",
            query=query[:50],
            entities_found=len(entity_names),
            chunks_found=len(graph_entities),
            latency_ms=round(latency_ms, 2),
        )

        return {"entities": entity_names, "context": context, "latency_ms": latency_ms}

    except Exception as e:
        logger.error("graph_local_search_failed", error=str(e), query=query[:50])
        return {"entities": [], "context": "", "latency_ms": 0}


async def _graph_global_search(
    dual_search: Any,
    query: str,
    namespaces: list[str] | None = None,
) -> dict[str, Any]:
    """Execute graph global search via DualLevelSearch (community-level).

    Sprint 128: Replaced LightRAG with DualLevelSearch.global_search().
    Returns Topic objects with entity lists — no text parsing needed.

    Args:
        dual_search: DualLevelSearch instance
        query: Search query
        namespaces: Namespaces to filter by

    Returns:
        Dictionary with entities list, context string, communities count, and latency_ms
    """
    start = time.perf_counter()

    try:
        topics = await dual_search.global_search(query=query, top_k=3, namespaces=namespaces)

        # Extract entity names from Topic.entities and Topic.keywords
        entity_names = []
        for topic in topics:
            entity_names.extend(topic.entities)
            entity_names.extend(topic.keywords)
        entity_names = sorted(set(entity_names))

        # Build context string for debugging
        context = "; ".join(f"{t.name}: {t.summary[:100]}" for t in topics if t.summary)

        latency_ms = (time.perf_counter() - start) * 1000

        logger.debug(
            "graph_global_search_complete",
            query=query[:50],
            topics_found=len(topics),
            entities_found=len(entity_names),
            latency_ms=round(latency_ms, 2),
        )

        return {
            "entities": entity_names,
            "context": context,
            "latency_ms": latency_ms,
            "communities_count": len(topics),
        }

    except Exception as e:
        logger.error("graph_global_search_failed", error=str(e), query=query[:50])
        return {"entities": [], "context": "", "latency_ms": 0, "communities_count": 0}


async def _hyde_search(
    hyde_generator: Any,
    query: str,
    top_k: int,
    namespaces: list[str] | None = None,
) -> dict[str, Any]:
    """Execute HyDE (Hypothetical Document Embeddings) search.

    Sprint 128 Feature 128.4: HyDE Query Expansion

    Generates a hypothetical answer document, embeds it, and searches Qdrant
    for semantically similar chunks. HyDE improves retrieval for abstract queries.

    Args:
        hyde_generator: HyDEGenerator instance
        query: Search query
        top_k: Number of results
        namespaces: Namespaces to filter by

    Returns:
        Dictionary with results, latency_ms, and hypothetical_doc

    Example:
        >>> result = await _hyde_search(hyde_gen, "What is Amsterdam?", 10)
        >>> print(f"HyDE found {len(result['results'])} results")
    """
    start = time.perf_counter()

    try:
        # Generate hypothetical document and search
        results = await hyde_generator.hyde_search(
            query=query,
            top_k=top_k,
            namespaces=namespaces,
        )

        # Get hypothetical document from cache for metadata
        hypothetical_doc = await hyde_generator.generate_hypothetical_document(query)

        latency_ms = (time.perf_counter() - start) * 1000

        logger.debug(
            "hyde_search_complete",
            query=query[:50],
            results=len(results),
            latency_ms=round(latency_ms, 2),
            hypothetical_length=len(hypothetical_doc),
        )

        return {
            "results": results,
            "latency_ms": latency_ms,
            "hypothetical_doc": hypothetical_doc,
        }

    except Exception as e:
        logger.error("hyde_search_failed", error=str(e), query=query[:50])
        return {"results": [], "latency_ms": 0, "hypothetical_doc": None}
