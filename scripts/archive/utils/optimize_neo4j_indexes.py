#!/usr/bin/env python3
"""Create Neo4j indexes for performance optimization.

Sprint 68 Feature 68.4: Query Latency Optimization

This script creates indexes on frequently queried properties to speed up
graph search operations (local and global).

Indexes created:
1. base.entity_name - For entity name lookups
2. base.description - For entity description searches
3. base.community_id - For community-based queries
4. base.namespace_id - For namespace filtering
5. chunk.chunk_id - For chunk lookups
6. chunk.namespace_id - For namespace filtering

Expected performance improvement: 30-50% for graph queries
"""

import asyncio

import structlog

from src.components.graph_rag.neo4j_client import Neo4jClient
from src.core.config import settings

logger = structlog.get_logger(__name__)


async def create_indexes():
    """Create Neo4j indexes for performance optimization."""
    client = Neo4jClient()

    # List of indexes to create
    indexes = [
        # Entity indexes
        ("idx_base_entity_name", "base", "entity_name"),
        ("idx_base_description", "base", "description"),
        ("idx_base_community_id", "base", "community_id"),
        ("idx_base_namespace_id", "base", "namespace_id"),
        # Chunk indexes
        ("idx_chunk_chunk_id", "chunk", "chunk_id"),
        ("idx_chunk_namespace_id", "chunk", "namespace_id"),
        ("idx_chunk_document_id", "chunk", "document_id"),
    ]

    logger.info("starting_neo4j_index_creation", count=len(indexes))

    for index_name, label, property_name in indexes:
        try:
            # Create index (IF NOT EXISTS to avoid errors if already created)
            cypher = f"""
            CREATE INDEX {index_name} IF NOT EXISTS
            FOR (n:{label})
            ON (n.{property_name})
            """

            await client.execute_query(cypher)

            logger.info(
                "index_created",
                index_name=index_name,
                label=label,
                property=property_name,
            )

        except Exception as e:
            logger.error(
                "index_creation_failed",
                index_name=index_name,
                error=str(e),
            )

    # Wait for indexes to come online
    logger.info("waiting_for_indexes_to_build")
    await asyncio.sleep(5)

    # Show index status
    try:
        cypher = "SHOW INDEXES"
        indexes_status = await client.execute_query(cypher)

        logger.info(
            "neo4j_indexes_status",
            count=len(indexes_status),
            indexes=[
                {
                    "name": idx.get("name"),
                    "state": idx.get("state"),
                    "type": idx.get("type"),
                }
                for idx in indexes_status
            ],
        )

    except Exception as e:
        logger.warning("failed_to_show_indexes", error=str(e))

    await client.close()
    logger.info("neo4j_index_optimization_complete")


async def main():
    """Main entry point."""
    try:
        await create_indexes()
    except Exception as e:
        logger.error("neo4j_optimization_failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
