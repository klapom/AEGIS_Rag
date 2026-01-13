"""Debug script for insert_documents_optimized flow.

Sprint 32 Post-Mortem: Test the full insertion flow to find where entities get lost.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog

logger = structlog.get_logger(__name__)


async def main():
    print("=" * 60)
    print("DEBUG: insert_documents_optimized FLOW")
    print("=" * 60)

    # Test document
    test_doc = {
        "text": """
        AEGIS RAG is a hybrid retrieval augmented generation system.
        It uses Neo4j as graph database and Qdrant for vector search.
        The system is built with Python and uses LangGraph for orchestration.
        Klaus Pommer developed this system as part of his studies.
        """,
        "id": "debug_test_full_flow",
    }

    print("\n[1] Testing insert_documents_optimized with test document...")
    print(f"    Document ID: {test_doc['id']}")
    print(f"    Text length: {len(test_doc['text'])}")

    try:
        from src.components.graph_rag.lightrag_wrapper import get_lightrag_client

        lightrag = get_lightrag_client()

        print("\n[2] Initializing LightRAG...")
        await lightrag._ensure_initialized()
        print("    LightRAG initialized ✅")

        print("\n[3] Calling insert_documents_optimized...")
        result = await lightrag.insert_documents_optimized([test_doc])

        print("\n[4] Results:")
        print(f"    Total: {result.get('total', 0)}")
        print(f"    Success: {result.get('success', 0)}")
        print(f"    Failed: {result.get('failed', 0)}")

        stats = result.get('stats', {})
        print("\n    Stats:")
        print(f"      Total chunks: {stats.get('total_chunks', 0)}")
        print(f"      Total entities: {stats.get('total_entities', 0)}")
        print(f"      Total relations: {stats.get('total_relations', 0)}")

        # Print per-document results
        for doc_result in result.get('results', []):
            print(f"\n    Document {doc_result.get('doc_id', 'unknown')}:")
            print(f"      Status: {doc_result.get('status', 'unknown')}")
            print(f"      Chunks: {doc_result.get('chunks', 0)}")
            print(f"      Entities: {doc_result.get('entities', 0)}")
            print(f"      Relations: {doc_result.get('relations', 0)}")
            if doc_result.get('error'):
                print(f"      Error: {doc_result.get('error')}")

        # Check Neo4j after insertion
        print("\n[5] Checking Neo4j after insertion...")
        from src.components.graph_rag.neo4j_client import Neo4jClient

        neo4j = Neo4jClient()

        # Count base entities
        result_entities = await neo4j.execute_query("""
            MATCH (n:base)
            RETURN count(n) as count
        """)
        print(f"    Entities with :base label: {result_entities[0]['count'] if result_entities else 0}")

        # Count all labels
        result_labels = await neo4j.execute_query("""
            MATCH (n)
            RETURN labels(n) as labels, count(n) as count
            ORDER BY count DESC
        """)
        print("    All node counts by label:")
        for r in result_labels:
            print(f"      {r}")

        # Check for recent entities
        result_recent = await neo4j.execute_query("""
            MATCH (n)
            WHERE n.document_id CONTAINS 'debug' OR n.source_id CONTAINS 'debug'
            RETURN labels(n) as labels, n.entity_id as entity_id, n.entity_name as name
            LIMIT 10
        """)
        print("\n    Recent entities from debug test:")
        for r in result_recent:
            print(f"      {r}")

        await neo4j.close()

    except Exception as e:
        print(f"\n    ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
