"""
Verify Neo4j/LightRAG data after indexing.
Checks entity and relation counts to validate LightRAG extraction.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async


async def run_query(graph, query):
    """Execute a Cypher query via Neo4j driver."""
    async with graph._driver.session() as session:
        result = await session.run(query)
        records = await result.data()
        return records


async def main():
    print("[*] Verifying Neo4j/LightRAG data...")

    try:
        lightrag = await get_lightrag_wrapper_async()

        # Ensure initialized and get graph handle
        if not lightrag.rag or not lightrag.rag.chunk_entity_relation_graph:
            print("[ERROR] LightRAG not properly initialized")
            return

        graph = lightrag.rag.chunk_entity_relation_graph

        if not hasattr(graph, "_driver"):
            print("[ERROR] Neo4j driver not found in graph instance")
            return

        # Get direct Neo4j statistics
        print("\n[1/4] Checking Neo4j node counts...")

        # Count chunks
        chunk_result = await run_query(graph, "MATCH (n:__Chunk__) RETURN count(n) as count")
        chunk_count = chunk_result[0]["count"] if chunk_result else 0
        print(f"   Chunks: {chunk_count}")

        # Count entities
        entity_result = await run_query(graph, "MATCH (n:__Entity__) RETURN count(n) as count")
        entity_count = entity_result[0]["count"] if entity_result else 0
        print(f"   Entities: {entity_count}")

        # Count all nodes
        all_nodes_result = await run_query(graph, "MATCH (n) RETURN count(n) as count")
        total_nodes = all_nodes_result[0]["count"] if all_nodes_result else 0
        print(f"   Total Nodes: {total_nodes}")

        print("\n[2/4] Checking Neo4j relationship counts...")

        # Count relationships
        rel_result = await run_query(
            graph, "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count"
        )

        total_rels = 0
        if rel_result:
            for row in rel_result:
                count = row["count"]
                rel_type = row["type"]
                print(f"   {rel_type}: {count}")
                total_rels += count
            print(f"   Total Relationships: {total_rels}")
        else:
            print("   No relationships found")

        print("\n[3/4] Sampling entities...")

        # Sample 5 entities
        sample_result = await run_query(
            graph, "MATCH (n:__Entity__) RETURN n.entity_name as name LIMIT 5"
        )

        if sample_result:
            for i, row in enumerate(sample_result, 1):
                print(f"   {i}. {row['name']}")
        else:
            print("   No entities to sample")

        print("\n[4/4] Checking chunk content...")

        # Sample 1 chunk to verify content was stored
        chunk_sample_result = await run_query(
            graph, "MATCH (n:__Chunk__) RETURN n.content as content LIMIT 1"
        )

        if chunk_sample_result and chunk_sample_result[0].get("content"):
            content = chunk_sample_result[0]["content"]
            preview = content[:200] if len(content) > 200 else content
            print("   Sample chunk (first 200 chars):")
            print(f"   {preview}...")
        else:
            print("   No chunk content found")

        print("\n" + "=" * 60)
        print("Summary:")
        print(f"   Chunks: {chunk_count}")
        print(f"   Entities: {entity_count}")
        print(f"   Total Nodes: {total_nodes}")
        print(f"   Total Relationships: {total_rels}")

        # Diagnosis
        print("\n" + "=" * 60)
        if entity_count < 10 and chunk_count > 50:
            print("⚠️  WARNING: Very low entity count for chunk count!")
            print("   Expected: ~10-50 entities for 103 chunks")
            print(f"   Actual: Only {entity_count} entities")
            print("\n   Possible causes:")
            print("   1. spaCy NER not running during extraction")
            print("   2. Entity extraction disabled in LightRAG config")
            print("   3. Extraction failed silently without errors")
        elif total_rels == 0 and entity_count > 0:
            print("⚠️  WARNING: No relationships extracted!")
            print("   Entities exist but no relations between them")
            print("\n   Possible causes:")
            print("   1. Relation extraction disabled")
            print("   2. LLM failed to extract relations")
            print("   3. Extraction timeout")
        else:
            print("✅ Data looks reasonable")

    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
