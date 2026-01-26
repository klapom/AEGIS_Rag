"""Seed minimal graph data into Neo4j for E2E testing.

Sprint 119 Feature 119.2: Graph Test Seed Data Script

This script creates minimal test graph data to enable E2E tests in:
- frontend/e2e/graph/edge-filters.spec.ts
- frontend/e2e/graph/graph-visualization.spec.ts

The script creates realistic AegisRAG architecture entities and relationships
with varying weights for threshold slider testing.

## Data Created

**Entities (10 nodes):**
- 3 entity types: TECHNOLOGY (8), CONCEPT (1), ORGANIZATION (1)
- Includes: Qdrant, Neo4j, Redis, BGE-M3, LangGraph, Docling, FastAPI, React, Playwright, AegisRAG

**Relationships (13 edges):**
- 10 RELATES_TO relationships with varying weights (0.4-0.95)
- 3 MENTIONED_IN relationships for chunk provenance
- Weights designed to test threshold slider functionality

**Chunks (2 nodes):**
- Test chunks for entity provenance
- Links entities to source documents

## Usage

### Inside Docker Container (Recommended):
```bash
# Seed test data
docker exec aegis-api python scripts/seed_test_graph_data.py

# Clean test data
docker exec aegis-api python scripts/seed_test_graph_data.py --clean

# Seed with custom namespace
docker exec aegis-api python scripts/seed_test_graph_data.py --namespace my_test_namespace
```

### Outside Docker (Local Development):
```bash
# Requires Poetry environment with neo4j, structlog
poetry run python scripts/seed_test_graph_data.py --namespace test_graph
```

## Environment Variables

The script reads Neo4j configuration from environment variables:
- NEO4J_URI (default: bolt://localhost:7687)
- NEO4J_USER (default: neo4j)
- NEO4J_PASSWORD (default: aegis-rag-neo4j-password)
- NEO4J_DATABASE (default: neo4j)

## Verification

After seeding, verify the data via:
1. Neo4j Browser: http://localhost:7474
   ```cypher
   MATCH (n:base {namespace_id: 'test_graph'}) RETURN n
   ```

2. Graph Viz API:
   ```bash
   curl http://localhost:8000/api/v1/graph/viz/statistics
   ```

3. Frontend UI:
   - Navigate to http://192.168.178.10
   - Open Graph Visualization
   - Select namespace 'test_graph'
   - Should see 10 nodes, 13+ edges

## Notes

- The script uses MERGE for idempotency (safe to run multiple times)
- Default namespace is 'test_graph' for E2E tests
- Data is isolated by namespace for multi-tenant testing
- Cleanup removes all nodes/edges in the specified namespace
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from neo4j import AsyncDriver, AsyncGraphDatabase

logger = structlog.get_logger(__name__)

# Neo4j Configuration (from environment or defaults)
import os

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "aegis-rag-neo4j-password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Test data theme: AegisRAG Architecture
# Entity types match the actual system's entity types
TEST_ENTITIES = [
    {
        "entity_id": "qdrant",
        "entity_name": "Qdrant",
        "entity_type": "TECHNOLOGY",
        "description": "Vector database for semantic search with BGE-M3 embeddings",
    },
    {
        "entity_id": "neo4j",
        "entity_name": "Neo4j",
        "entity_type": "TECHNOLOGY",
        "description": "Graph database for entity and relationship storage",
    },
    {
        "entity_id": "redis",
        "entity_name": "Redis",
        "entity_type": "TECHNOLOGY",
        "description": "In-memory cache for memory and session management",
    },
    {
        "entity_id": "bge-m3",
        "entity_name": "BGE-M3",
        "entity_type": "CONCEPT",
        "description": "Multilingual embedding model with 1024-dim dense and sparse vectors",
    },
    {
        "entity_id": "langgraph",
        "entity_name": "LangGraph",
        "entity_type": "TECHNOLOGY",
        "description": "Multi-agent orchestration framework",
    },
    {
        "entity_id": "docling",
        "entity_name": "Docling",
        "entity_type": "TECHNOLOGY",
        "description": "GPU-accelerated document parser with CUDA support",
    },
    {
        "entity_id": "fastapi",
        "entity_name": "FastAPI",
        "entity_type": "TECHNOLOGY",
        "description": "Python web framework for REST API endpoints",
    },
    {
        "entity_id": "react",
        "entity_name": "React",
        "entity_type": "TECHNOLOGY",
        "description": "Frontend framework with TypeScript and Vite",
    },
    {
        "entity_id": "playwright",
        "entity_name": "Playwright",
        "entity_type": "TECHNOLOGY",
        "description": "End-to-end testing framework for web applications",
    },
    {
        "entity_id": "aegisrag",
        "entity_name": "AegisRAG",
        "entity_type": "ORGANIZATION",
        "description": "Agentic Enterprise Graph Intelligence System",
    },
]

# Relationships with varying weights for threshold slider testing
# Weight range: 0.4 to 0.95 (realistic semantic similarity scores)
TEST_RELATIONSHIPS = [
    {
        "source": "bge-m3",
        "target": "qdrant",
        "type": "RELATES_TO",
        "description": "BGE-M3 generates embeddings stored in Qdrant",
        "weight": 0.95,
    },
    {
        "source": "langgraph",
        "target": "fastapi",
        "type": "RELATES_TO",
        "description": "LangGraph agents exposed via FastAPI endpoints",
        "weight": 0.87,
    },
    {
        "source": "neo4j",
        "target": "qdrant",
        "type": "RELATES_TO",
        "description": "Neo4j stores graph structure, Qdrant stores vectors",
        "weight": 0.72,
    },
    {
        "source": "redis",
        "target": "neo4j",
        "type": "RELATES_TO",
        "description": "Redis caches Neo4j query results",
        "weight": 0.68,
    },
    {
        "source": "docling",
        "target": "bge-m3",
        "type": "RELATES_TO",
        "description": "Docling extracts text for BGE-M3 embedding",
        "weight": 0.81,
    },
    {
        "source": "react",
        "target": "fastapi",
        "type": "RELATES_TO",
        "description": "React frontend calls FastAPI backend",
        "weight": 0.93,
    },
    {
        "source": "playwright",
        "target": "react",
        "type": "RELATES_TO",
        "description": "Playwright tests React components",
        "weight": 0.76,
    },
    {
        "source": "aegisrag",
        "target": "langgraph",
        "type": "RELATES_TO",
        "description": "AegisRAG uses LangGraph for orchestration",
        "weight": 0.89,
    },
    {
        "source": "aegisrag",
        "target": "qdrant",
        "type": "RELATES_TO",
        "description": "AegisRAG uses Qdrant for vector search",
        "weight": 0.91,
    },
    {
        "source": "aegisrag",
        "target": "neo4j",
        "type": "RELATES_TO",
        "description": "AegisRAG uses Neo4j for graph reasoning",
        "weight": 0.90,
    },
    # Additional MENTIONED_IN relationships for chunk provenance
    {
        "source": "qdrant",
        "target": "test_chunk_001",
        "type": "MENTIONED_IN",
        "description": "Qdrant mentioned in architecture documentation",
        "weight": 1.0,
    },
    {
        "source": "neo4j",
        "target": "test_chunk_001",
        "type": "MENTIONED_IN",
        "description": "Neo4j mentioned in architecture documentation",
        "weight": 1.0,
    },
    {
        "source": "bge-m3",
        "target": "test_chunk_002",
        "type": "MENTIONED_IN",
        "description": "BGE-M3 mentioned in embedding documentation",
        "weight": 1.0,
    },
]

# Test chunk data for provenance
TEST_CHUNKS = [
    {
        "chunk_id": "test_chunk_001",
        "text": "AegisRAG uses Qdrant for vector search and Neo4j for graph storage. "
        "The system combines semantic search with graph reasoning.",
        "document_id": "test_doc_architecture",
        "document_path": "docs/ARCHITECTURE.md",
        "chunk_index": 0,
        "tokens": 25,
    },
    {
        "chunk_id": "test_chunk_002",
        "text": "BGE-M3 is a multilingual embedding model that generates 1024-dim dense "
        "vectors and sparse lexical weights for hybrid search.",
        "document_id": "test_doc_embeddings",
        "document_path": "docs/TECH_STACK.md",
        "chunk_index": 0,
        "tokens": 20,
    },
]


async def seed_graph_data(namespace: str = "test_graph") -> None:
    """Seed minimal graph data into Neo4j.

    Args:
        namespace: Namespace for test data isolation (default: "test_graph")
    """
    driver: AsyncDriver | None = None

    try:
        # Connect to Neo4j
        driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )

        logger.info(
            "neo4j_connection_established",
            uri=NEO4J_URI,
            database=NEO4J_DATABASE,
        )

        async with driver.session(database=NEO4J_DATABASE) as session:
            # Step 1: Create chunk nodes
            logger.info("creating_chunk_nodes", count=len(TEST_CHUNKS))
            for chunk in TEST_CHUNKS:
                await session.run(
                    """
                    MERGE (c:chunk {chunk_id: $chunk_id})
                    SET c.text = $text,
                        c.document_id = $document_id,
                        c.document_path = $document_path,
                        c.chunk_index = $chunk_index,
                        c.tokens = $tokens,
                        c.namespace_id = $namespace_id,
                        c.created_at = datetime()
                    """,
                    chunk_id=chunk["chunk_id"],
                    text=chunk["text"],
                    document_id=chunk["document_id"],
                    document_path=chunk["document_path"],
                    chunk_index=chunk["chunk_index"],
                    tokens=chunk["tokens"],
                    namespace_id=namespace,
                )

            logger.info("chunk_nodes_created", count=len(TEST_CHUNKS))

            # Step 2: Create entity nodes with dual labels (:base and :EntityType)
            logger.info("creating_entity_nodes", count=len(TEST_ENTITIES))
            entities_created = 0

            for entity in TEST_ENTITIES:
                # Use backticks for entity_type label to handle spaces/special chars
                entity_type_label = f"`{entity['entity_type']}`"
                labels_str = f"base:{entity_type_label}"

                await session.run(
                    f"""
                    MERGE (e:{labels_str} {{entity_id: $entity_id}})
                    SET e.entity_name = $entity_name,
                        e.entity_type = $entity_type,
                        e.description = $description,
                        e.namespace_id = $namespace_id,
                        e.created_at = datetime()
                    """,
                    entity_id=entity["entity_id"],
                    entity_name=entity["entity_name"],
                    entity_type=entity["entity_type"],
                    description=entity["description"],
                    namespace_id=namespace,
                )
                entities_created += 1

            logger.info("entity_nodes_created", count=entities_created)

            # Step 3: Create relationships (RELATES_TO and MENTIONED_IN)
            logger.info("creating_relationships", count=len(TEST_RELATIONSHIPS))
            relations_created = 0

            for rel in TEST_RELATIONSHIPS:
                if rel["type"] == "RELATES_TO":
                    # Entity-to-entity relationship
                    await session.run(
                        """
                        MATCH (e1:base {entity_id: $source})
                        MATCH (e2:base {entity_id: $target})
                        WHERE e1 <> e2
                        MERGE (e1)-[r:RELATES_TO]->(e2)
                        SET r.weight = $weight,
                            r.description = $description,
                            r.namespace_id = $namespace_id,
                            r.created_at = datetime()
                        """,
                        source=rel["source"],
                        target=rel["target"],
                        weight=rel["weight"],
                        description=rel["description"],
                        namespace_id=namespace,
                    )
                    relations_created += 1

                elif rel["type"] == "MENTIONED_IN":
                    # Entity-to-chunk relationship (provenance)
                    await session.run(
                        """
                        MATCH (e:base {entity_id: $source})
                        MATCH (c:chunk {chunk_id: $target})
                        MERGE (e)-[r:MENTIONED_IN]->(c)
                        SET r.weight = $weight,
                            r.source_chunk_id = $target,
                            r.namespace_id = $namespace_id,
                            r.created_at = datetime()
                        """,
                        source=rel["source"],
                        target=rel["target"],
                        weight=rel["weight"],
                        namespace_id=namespace,
                    )
                    relations_created += 1

            logger.info("relationships_created", count=relations_created)

            # Step 4: Verify creation by counting nodes/edges
            node_result = await session.run(
                "MATCH (n:base {namespace_id: $namespace_id}) RETURN count(n) as count",
                namespace_id=namespace,
            )
            node_record = await node_result.single()
            node_count = node_record["count"] if node_record else 0

            edge_result = await session.run(
                """
                MATCH (n:base {namespace_id: $namespace_id})-[r]-()
                RETURN count(r) as count
                """,
                namespace_id=namespace,
            )
            edge_record = await edge_result.single()
            edge_count = edge_record["count"] if edge_record else 0

            # Get entity type distribution
            type_result = await session.run(
                """
                MATCH (n:base {namespace_id: $namespace_id})
                RETURN n.entity_type as type, count(*) as count
                """,
                namespace_id=namespace,
            )
            type_records = await type_result.data()
            entity_types = {record["type"]: record["count"] for record in type_records}

            logger.info(
                "graph_seeding_complete",
                namespace=namespace,
                nodes=node_count,
                edges=edge_count,
                entity_types=entity_types,
            )

            print(f"\n✅ Graph data seeded successfully!")
            print(f"   Namespace: {namespace}")
            print(f"   Nodes: {node_count}")
            print(f"   Edges: {edge_count}")
            print(f"   Entity Types: {entity_types}")
            print(f"   Chunks: {len(TEST_CHUNKS)}")
            print(f"\n🔍 View in Neo4j Browser: http://localhost:7474")
            print(f"   Cypher query: MATCH (n:base {{namespace_id: '{namespace}'}}) RETURN n")

    except Exception as e:
        logger.error("graph_seeding_failed", error=str(e), exc_info=True)
        print(f"\n❌ Error seeding graph data: {e}")
        raise

    finally:
        if driver:
            await driver.close()
            logger.info("neo4j_connection_closed")


async def clean_test_data(namespace: str = "test_graph") -> None:
    """Remove test graph data from Neo4j.

    Args:
        namespace: Namespace to clean (default: "test_graph")
    """
    driver: AsyncDriver | None = None

    try:
        # Connect to Neo4j
        driver = AsyncGraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )

        logger.info("cleaning_test_data", namespace=namespace)

        async with driver.session(database=NEO4J_DATABASE) as session:
            # Step 1: Delete all relationships for nodes in namespace
            await session.run(
                """
                MATCH (n:base {namespace_id: $namespace_id})-[r]-()
                DELETE r
                """,
                namespace_id=namespace,
            )

            # Step 2: Delete all entity nodes in namespace
            node_result = await session.run(
                """
                MATCH (n:base {namespace_id: $namespace_id})
                DELETE n
                RETURN count(n) as deleted
                """,
                namespace_id=namespace,
            )
            node_record = await node_result.single()
            nodes_deleted = node_record["deleted"] if node_record else 0

            # Step 3: Delete all chunk nodes in namespace
            chunk_result = await session.run(
                """
                MATCH (c:chunk {namespace_id: $namespace_id})
                DELETE c
                RETURN count(c) as deleted
                """,
                namespace_id=namespace,
            )
            chunk_record = await chunk_result.single()
            chunks_deleted = chunk_record["deleted"] if chunk_record else 0

            logger.info(
                "test_data_cleaned",
                namespace=namespace,
                nodes_deleted=nodes_deleted,
                chunks_deleted=chunks_deleted,
            )

            print(f"\n✅ Test data cleaned successfully!")
            print(f"   Namespace: {namespace}")
            print(f"   Nodes deleted: {nodes_deleted}")
            print(f"   Chunks deleted: {chunks_deleted}")

    except Exception as e:
        logger.error("cleanup_failed", error=str(e), exc_info=True)
        print(f"\n❌ Error cleaning test data: {e}")
        raise

    finally:
        if driver:
            await driver.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Seed minimal graph data into Neo4j for E2E testing."
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove test data instead of creating it",
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default="test_graph",
        help="Namespace for test data isolation (default: test_graph)",
    )

    args = parser.parse_args()

    if args.clean:
        print(f"\n🧹 Cleaning test data from namespace: {args.namespace}")
        asyncio.run(clean_test_data(namespace=args.namespace))
    else:
        print(f"\n🌱 Seeding test data into namespace: {args.namespace}")
        asyncio.run(seed_graph_data(namespace=args.namespace))


if __name__ == "__main__":
    main()
