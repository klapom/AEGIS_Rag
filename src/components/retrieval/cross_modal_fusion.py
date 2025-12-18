"""Cross-Modal Fusion - Align entity-based and chunk-based retrieval results.

Sprint 51 - Feature 51.7: Maximum Hybrid Search Foundation

This module implements cross-modal fusion that connects:
1. Chunk rankings (from Qdrant embeddings + BM25)
2. Entity information (from LightRAG local/global modes)

Using the MENTIONED_IN relationship in Neo4j, we boost chunks that contain
highly-ranked entities from LightRAG.

Algorithm:
    1. For each entity E with rank R_e:
       - Find chunks C that mention E (via MENTIONED_IN)
       - Boost each chunk's score by: boost = 1 / (k + R_e)

    2. Combine chunk ranking with entity boosts:
       final_score = rrf_score + alpha * sum(entity_boosts)

Academic Reference:
    - Fusion techniques from RAG-Fusion (2024) and HybridRAG (2024)
    - Entity-chunk alignment inspired by GraphRAG (Edge et al., 2024)
"""

import asyncio
from typing import Any

import structlog

from src.components.graph_rag.neo4j_client import Neo4jClient

logger = structlog.get_logger(__name__)


async def cross_modal_fusion(
    chunk_ranking: list[dict[str, Any]],
    entity_names: list[str],
    neo4j_client: Neo4jClient | None = None,
    alpha: float = 0.3,
    k: int = 60,
    allowed_namespaces: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Boost chunk rankings based on entity mentions.

    This function implements cross-modal fusion by:
    1. Finding chunks that mention highly-ranked entities (via MENTIONED_IN)
    2. Boosting chunk scores proportional to entity importance
    3. Re-ranking chunks with combined scores

    Args:
        chunk_ranking: Ranked chunks from RRF fusion (with 'id', 'rrf_score', 'rank')
        entity_names: List of entity names from LightRAG (ordered by relevance)
        neo4j_client: Neo4j client for MENTIONED_IN queries
        alpha: Weight for entity boost (default: 0.3)
        k: RRF constant for entity score calculation (default: 60)
        allowed_namespaces: Namespaces to filter by (multi-tenant isolation)

    Returns:
        Re-ranked chunks with cross-modal boost applied

    Example:
        >>> chunks = [{"id": "chunk1", "rrf_score": 0.85, "rank": 1}, ...]
        >>> entities = ["Amsterdam", "Netherlands", "Europe"]
        >>> boosted = await cross_modal_fusion(chunks, entities)
        >>> boosted[0]["final_score"]  # Original RRF + entity boost
        0.95
    """
    if not entity_names or not chunk_ranking:
        logger.debug(
            "cross_modal_fusion_skipped",
            reason="empty_inputs",
            chunks=len(chunk_ranking),
            entities=len(entity_names),
        )
        return chunk_ranking

    # Initialize Neo4j client if not provided
    if neo4j_client is None:
        neo4j_client = Neo4jClient()

    logger.info(
        "cross_modal_fusion_start",
        chunks=len(chunk_ranking),
        entities=len(entity_names),
        alpha=alpha,
    )

    try:
        # Step 1: Query Neo4j for entity-chunk relationships
        entity_chunk_map = await _get_entity_chunk_mentions(
            entity_names=entity_names,
            neo4j_client=neo4j_client,
            allowed_namespaces=allowed_namespaces,
        )

        if not entity_chunk_map:
            logger.debug(
                "cross_modal_fusion_no_mentions",
                entities_searched=len(entity_names),
            )
            return chunk_ranking

        # Step 2: Calculate entity importance scores (position-based)
        entity_scores = {}
        for rank, entity_name in enumerate(entity_names, start=1):
            entity_scores[entity_name] = 1.0 / (k + rank)

        # Step 3: Calculate boost for each chunk
        chunk_boosts = {}
        for entity_name, chunk_ids in entity_chunk_map.items():
            entity_score = entity_scores.get(entity_name, 0.0)
            for chunk_id in chunk_ids:
                if chunk_id not in chunk_boosts:
                    chunk_boosts[chunk_id] = 0.0
                chunk_boosts[chunk_id] += entity_score

        logger.debug(
            "cross_modal_fusion_boosts_calculated",
            chunks_with_boosts=len(chunk_boosts),
            avg_boost=sum(chunk_boosts.values()) / len(chunk_boosts) if chunk_boosts else 0,
        )

        # Step 4: Apply boosts to chunk ranking
        boosted_chunks = []
        for chunk in chunk_ranking:
            chunk_id = chunk.get("id")
            rrf_score = chunk.get("rrf_score", chunk.get("score", 0.0))

            # Calculate entity boost
            entity_boost = chunk_boosts.get(chunk_id, 0.0)

            # Combine scores: final = rrf + alpha * entity_boost
            final_score = rrf_score + (alpha * entity_boost)

            boosted_chunk = {
                **chunk,
                "entity_boost": entity_boost,
                "final_score": final_score,
                "cross_modal_boosted": entity_boost > 0,
            }
            boosted_chunks.append(boosted_chunk)

        # Step 5: Re-rank by final score
        boosted_chunks.sort(key=lambda x: x["final_score"], reverse=True)

        # Update ranks
        for rank, chunk in enumerate(boosted_chunks, start=1):
            chunk["final_rank"] = rank

        boosted_count = sum(1 for c in boosted_chunks if c.get("cross_modal_boosted", False))

        logger.info(
            "cross_modal_fusion_complete",
            total_chunks=len(boosted_chunks),
            chunks_boosted=boosted_count,
            boost_percentage=round(boosted_count / len(boosted_chunks) * 100, 1) if boosted_chunks else 0,
        )

        return boosted_chunks

    except Exception as e:
        logger.error(
            "cross_modal_fusion_failed",
            error=str(e),
            chunks=len(chunk_ranking),
            entities=len(entity_names),
        )
        # Fallback: return original ranking
        return chunk_ranking


async def _get_entity_chunk_mentions(
    entity_names: list[str],
    neo4j_client: Neo4jClient,
    allowed_namespaces: list[str] | None = None,
) -> dict[str, list[str]]:
    """Query Neo4j for entity-chunk MENTIONED_IN relationships.

    Args:
        entity_names: List of entity names to look up
        neo4j_client: Neo4j client instance
        allowed_namespaces: Namespaces to filter by

    Returns:
        Dictionary mapping entity_name -> list[chunk_id]
    """
    if not entity_names:
        return {}

    try:
        # Build Cypher query with namespace filtering
        if allowed_namespaces:
            cypher = """
            UNWIND $entity_names AS entity_name
            MATCH (e:base {entity_name: entity_name})-[:MENTIONED_IN]->(c:chunk)
            WHERE e.namespace_id IN $allowed_namespaces
              AND c.namespace_id IN $allowed_namespaces
            RETURN e.entity_name AS entity_name, collect(DISTINCT c.chunk_id) AS chunk_ids
            """
            params = {
                "entity_names": entity_names,
                "allowed_namespaces": allowed_namespaces,
            }
        else:
            cypher = """
            UNWIND $entity_names AS entity_name
            MATCH (e:base {entity_name: entity_name})-[:MENTIONED_IN]->(c:chunk)
            RETURN e.entity_name AS entity_name, collect(DISTINCT c.chunk_id) AS chunk_ids
            """
            params = {"entity_names": entity_names}

        results = await neo4j_client.execute_read(cypher, params)

        # Build entity -> chunk_ids map
        entity_chunk_map = {}
        for record in results:
            entity_name = record["entity_name"]
            chunk_ids = record["chunk_ids"]
            entity_chunk_map[entity_name] = chunk_ids

        logger.debug(
            "entity_chunk_mentions_retrieved",
            entities_queried=len(entity_names),
            entities_found=len(entity_chunk_map),
            total_chunks_linked=sum(len(chunks) for chunks in entity_chunk_map.values()),
        )

        return entity_chunk_map

    except Exception as e:
        logger.error(
            "entity_chunk_mentions_query_failed",
            error=str(e),
            entities=len(entity_names),
        )
        return {}


async def get_chunks_for_entities(
    entity_names: list[str],
    neo4j_client: Neo4jClient | None = None,
    top_k: int = 20,
    allowed_namespaces: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Retrieve chunks that mention specific entities (for pure entity-based retrieval).

    This is a simplified version of cross-modal fusion that directly returns chunks
    mentioning the given entities, without needing a base chunk ranking.

    Args:
        entity_names: List of entity names to search for
        neo4j_client: Neo4j client instance
        top_k: Maximum chunks to return per entity
        allowed_namespaces: Namespaces to filter by

    Returns:
        List of chunks with entity mention metadata
    """
    if not entity_names:
        return []

    if neo4j_client is None:
        neo4j_client = Neo4jClient()

    try:
        # Query chunks that mention any of the entities
        if allowed_namespaces:
            cypher = """
            UNWIND $entity_names AS entity_name
            MATCH (e:base {entity_name: entity_name})-[:MENTIONED_IN]->(c:chunk)
            WHERE e.namespace_id IN $allowed_namespaces
              AND c.namespace_id IN $allowed_namespaces
            WITH c, collect(DISTINCT e.entity_name) AS mentioned_entities, count(DISTINCT e) AS entity_count
            RETURN c.chunk_id AS id,
                   c.text AS text,
                   c.document_id AS document_id,
                   c.namespace_id AS namespace_id,
                   mentioned_entities,
                   entity_count AS score
            ORDER BY entity_count DESC
            LIMIT $top_k
            """
            params = {
                "entity_names": entity_names,
                "top_k": top_k,
                "allowed_namespaces": allowed_namespaces,
            }
        else:
            cypher = """
            UNWIND $entity_names AS entity_name
            MATCH (e:base {entity_name: entity_name})-[:MENTIONED_IN]->(c:chunk)
            WITH c, collect(DISTINCT e.entity_name) AS mentioned_entities, count(DISTINCT e) AS entity_count
            RETURN c.chunk_id AS id,
                   c.text AS text,
                   c.document_id AS document_id,
                   mentioned_entities,
                   entity_count AS score
            ORDER BY entity_count DESC
            LIMIT $top_k
            """
            params = {"entity_names": entity_names, "top_k": top_k}

        results = await neo4j_client.execute_read(cypher, params)

        chunks = []
        for rank, record in enumerate(results, start=1):
            chunks.append({
                "id": record["id"],
                "text": record["text"] or "",
                "document_id": record.get("document_id", ""),
                "namespace_id": record.get("namespace_id", "default"),
                "score": record.get("score", 0),
                "rank": rank,
                "search_type": "entity_mention",
                "mentioned_entities": record.get("mentioned_entities", []),
            })

        logger.debug(
            "get_chunks_for_entities_complete",
            entities=len(entity_names),
            chunks_found=len(chunks),
        )

        return chunks

    except Exception as e:
        logger.error(
            "get_chunks_for_entities_failed",
            error=str(e),
            entities=len(entity_names),
        )
        return []
