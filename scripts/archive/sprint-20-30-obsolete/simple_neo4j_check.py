"""
Simple Neo4j check - just counts and entity/relation summary.
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
    print("=" * 80)
    print("NEO4J QUICK CHECK")
    print("=" * 80)

    try:
        lightrag = await get_lightrag_wrapper_async()

        if not lightrag.rag or not lightrag.rag.chunk_entity_relation_graph:
            print("[ERROR] LightRAG not properly initialized")
            return

        graph = lightrag.rag.chunk_entity_relation_graph

        # Count chunks
        chunk_result = await run_query(graph, "MATCH (c:chunk) RETURN count(c) as count")
        chunk_count = chunk_result[0]["count"] if chunk_result else 0

        # Count entities (nodes with base: labels)
        entity_result = await run_query(
            graph,
            "MATCH (e) WHERE ANY(label IN labels(e) WHERE label STARTS WITH 'base:') RETURN count(e) as count",
        )
        entity_count = entity_result[0]["count"] if entity_result else 0

        # Count relationships
        rel_result = await run_query(
            graph, "MATCH ()-[r:MENTIONED_IN]->() RETURN count(r) as count"
        )
        rel_count = rel_result[0]["count"] if rel_result else 0

        # Get document IDs
        doc_result = await run_query(
            graph, "MATCH (c:chunk) RETURN DISTINCT c.document_id as doc_id LIMIT 5"
        )

        print(f"\nCOUNTS:")
        print(f"  Chunks: {chunk_count}")
        print(f"  Entities: {entity_count}")
        print(f"  Relations (MENTIONED_IN): {rel_count}")

        print(f"\nDOCUMENT IDs:")
        for doc in doc_result:
            print(f"  - {doc['doc_id']}")

        # Get entity labels and names
        print(f"\nENTITIES:")
        entities = await run_query(
            graph,
            """
            MATCH (e)
            WHERE ANY(label IN labels(e) WHERE label STARTS WITH 'base:')
            RETURN labels(e) as labels,
                   COALESCE(e.entity_name, e.name, e.id, 'unnamed') as name
        """,
        )

        for i, ent in enumerate(entities, 1):
            label = ":".join(ent["labels"])
            name = ent["name"]
            print(f"  {i}. [{label}] {name}")

        # Get relations summary
        print(f"\nRELATIONSHIPS:")
        rels = await run_query(
            graph,
            """
            MATCH (e)-[r:MENTIONED_IN]->(c:chunk)
            RETURN labels(e) as entity_labels,
                   COALESCE(e.entity_name, e.name, 'unnamed') as entity_name,
                   c.chunk_index as chunk_index
            ORDER BY c.chunk_index
        """,
        )

        for i, rel in enumerate(rels, 1):
            label = ":".join(rel["entity_labels"])
            name = rel["entity_name"]
            chunk_idx = rel["chunk_index"]
            print(f"  {i}. [{label}] '{name}' -> chunk #{chunk_idx}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
