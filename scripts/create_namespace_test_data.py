#!/usr/bin/env python3
"""Create test data for namespace isolation testing.

Sprint 41: Creates sample documents in different namespaces to verify isolation.

Usage:
    poetry run python scripts/create_namespace_test_data.py
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
from dotenv import load_dotenv

load_dotenv(".env.dgx-spark")

# Override hostnames for running outside Docker
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"
os.environ["QDRANT_GRPC_PORT"] = "6334"

from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams


async def create_qdrant_collection():
    """Create Qdrant collection with namespace index."""
    print("Creating Qdrant collection...")

    from src.components.vector_search.qdrant_client import get_qdrant_client

    client = get_qdrant_client()
    collection_name = "aegis_documents"

    # Check if collection exists
    collections = await client.async_client.get_collections()
    collection_names = [c.name for c in collections.collections]

    if collection_name in collection_names:
        print(f"  Collection {collection_name} already exists")
    else:
        # Create collection with BGE-M3 dimensions (1024)
        await client.async_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
        print(f"  Created collection: {collection_name}")

    # Create namespace index
    try:
        await client.async_client.create_payload_index(
            collection_name=collection_name,
            field_name="namespace_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        print("  Created namespace_id index")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  namespace_id index already exists")
        else:
            print(f"  Index creation note: {e}")

    return client, collection_name


async def create_test_documents():
    """Create test documents in different namespaces."""
    print("\nCreating test documents...")

    client, collection_name = await create_qdrant_collection()

    # Generate fake embeddings (1024 dimensions for BGE-M3)
    import random
    def fake_embedding():
        return [random.uniform(-1, 1) for _ in range(1024)]

    # Test documents in different namespaces
    test_docs = [
        # Default namespace
        {
            "id": str(uuid.uuid4()),
            "text": "AEGIS RAG is an enterprise RAG system with hybrid search capabilities.",
            "namespace_id": "default",
            "source": "default_doc1.md",
            "document_id": "doc_default_1",
        },
        {
            "id": str(uuid.uuid4()),
            "text": "The system uses Qdrant for vector search and Neo4j for graph queries.",
            "namespace_id": "default",
            "source": "default_doc2.md",
            "document_id": "doc_default_2",
        },
        # General namespace (company-wide)
        {
            "id": str(uuid.uuid4()),
            "text": "Company policy requires all documents to be properly classified.",
            "namespace_id": "general",
            "source": "company_policy.md",
            "document_id": "doc_general_1",
        },
        # Evaluation namespace
        {
            "id": str(uuid.uuid4()),
            "text": "Namespace isolation ensures documents are only visible within their namespace.",
            "namespace_id": "eval_sprint41",
            "source": "namespace_test.md",
            "document_id": "doc_eval_1",
        },
        {
            "id": str(uuid.uuid4()),
            "text": "The SecureNeo4jClient validates all queries contain namespace filters.",
            "namespace_id": "eval_sprint41",
            "source": "namespace_test.md",
            "document_id": "doc_eval_2",
        },
        # User project namespace
        {
            "id": str(uuid.uuid4()),
            "text": "This is a private document in Alice's project about machine learning.",
            "namespace_id": "user_alice_project1",
            "source": "alice_ml_notes.md",
            "document_id": "doc_alice_1",
        },
    ]

    # Create points
    points = []
    for doc in test_docs:
        point = PointStruct(
            id=doc["id"],
            vector=fake_embedding(),
            payload={
                "text": doc["text"],
                "namespace_id": doc["namespace_id"],
                "source": doc["source"],
                "document_id": doc["document_id"],
                "chunk_id": doc["id"],
            }
        )
        points.append(point)
        print(f"  + [{doc['namespace_id']}] {doc['source']}: {doc['text'][:50]}...")

    # Upsert all points
    await client.async_client.upsert(
        collection_name=collection_name,
        points=points,
    )

    print(f"\n  Inserted {len(points)} documents into Qdrant")
    return len(points)


async def create_neo4j_entities():
    """Create test entities in Neo4j with namespace tags."""
    print("\nCreating Neo4j entities...")

    from src.core.neo4j_safety import get_secure_neo4j_client

    client = get_secure_neo4j_client()

    # Test entities in different namespaces
    entities = [
        ("AEGIS RAG", "System", "default", "Enterprise RAG system"),
        ("Qdrant", "Technology", "default", "Vector database"),
        ("Neo4j", "Technology", "default", "Graph database"),
        ("Company Policy", "Document", "general", "Corporate guidelines"),
        ("Namespace Isolation", "Feature", "eval_sprint41", "Multi-tenancy feature"),
        ("SecureNeo4jClient", "Component", "eval_sprint41", "Security wrapper"),
        ("Machine Learning", "Topic", "user_alice_project1", "ML research topic"),
    ]

    for name, entity_type, namespace, description in entities:
        await client.execute_write(
            """
            MERGE (e:base {entity_name: $name})
            SET e.entity_type = $entity_type,
                e.namespace_id = $namespace,
                e.description = $description
            """,
            parameters={
                "name": name,
                "entity_type": entity_type,
                "namespace": namespace,
                "description": description,
            }
        )
        print(f"  + [{namespace}] {name} ({entity_type})")

    print(f"\n  Created {len(entities)} entities in Neo4j")
    return len(entities)


async def verify_namespace_isolation():
    """Verify namespace isolation works correctly."""
    print("\n" + "=" * 60)
    print("VERIFYING NAMESPACE ISOLATION")
    print("=" * 60)

    from src.core.namespace import get_namespace_manager

    manager = get_namespace_manager()

    # Test 1: Search in default namespace
    print("\n1. Search in 'default' namespace:")
    results = await manager.search_qdrant(
        query_vector=[0.1] * 1024,
        allowed_namespaces=["default"],
        limit=10,
    )
    print(f"   Found {len(results)} documents")
    for r in results[:3]:
        print(f"   - {r.get('payload', {}).get('source', 'unknown')}: {r.get('payload', {}).get('text', '')[:40]}...")

    # Test 2: Search in eval_sprint41 namespace
    print("\n2. Search in 'eval_sprint41' namespace:")
    results = await manager.search_qdrant(
        query_vector=[0.1] * 1024,
        allowed_namespaces=["eval_sprint41"],
        limit=10,
    )
    print(f"   Found {len(results)} documents")
    for r in results[:3]:
        print(f"   - {r.get('payload', {}).get('source', 'unknown')}: {r.get('payload', {}).get('text', '')[:40]}...")

    # Test 3: Cross-namespace search (general + user_alice)
    print("\n3. Cross-namespace search ('general' + 'user_alice_project1'):")
    results = await manager.search_qdrant(
        query_vector=[0.1] * 1024,
        allowed_namespaces=["general", "user_alice_project1"],
        limit=10,
    )
    print(f"   Found {len(results)} documents")
    for r in results:
        ns = r.get('payload', {}).get('namespace_id', 'unknown')
        src = r.get('payload', {}).get('source', 'unknown')
        print(f"   - [{ns}] {src}")

    # Test 4: Empty namespace returns empty
    print("\n4. Empty namespace list:")
    results = await manager.search_qdrant(
        query_vector=[0.1] * 1024,
        allowed_namespaces=[],
        limit=10,
    )
    print(f"   Found {len(results)} documents (expected: 0)")

    # Test 5: Neo4j entity search
    print("\n5. Neo4j entity search in 'eval_sprint41':")
    results = await manager.search_neo4j_local(
        query_terms=["namespace", "security"],
        allowed_namespaces=["eval_sprint41"],
        top_k=10,
    )
    print(f"   Found {len(results)} entities")

    return True


async def main():
    """Create test data and verify namespace isolation."""
    print("=" * 60)
    print("NAMESPACE TEST DATA CREATION")
    print("=" * 60)

    try:
        qdrant_count = await create_test_documents()
        neo4j_count = await create_neo4j_entities()

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"  Qdrant documents: {qdrant_count}")
        print(f"  Neo4j entities: {neo4j_count}")

        await verify_namespace_isolation()

        print("\n" + "=" * 60)
        print("TEST DATA CREATION COMPLETE")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
