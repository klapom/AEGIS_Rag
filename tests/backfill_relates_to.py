"""Backfill script to create RELATES_TO relationships for ALL chunks in Neo4j.

Run with: poetry run python tests/backfill_relates_to.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def backfill_relates_to():
    """Create RELATES_TO relationships for all chunks in Neo4j."""
    from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
    from src.components.graph_rag.neo4j_client import get_neo4j_client
    from src.components.graph_rag.relation_extractor import RelationExtractor

    print("=" * 60)
    print("Backfilling RELATES_TO Relationships for ALL Chunks")
    print("=" * 60)

    # Get Neo4j client
    neo4j_client = get_neo4j_client()
    print("\n1. Neo4j client initialized")

    # Get all chunks from Neo4j
    chunk_query = "MATCH (c:chunk) RETURN c.chunk_id as chunk_id, c.text as text"
    all_chunks = await neo4j_client.execute_read(chunk_query)
    print(f"\n2. Total chunks in Neo4j: {len(all_chunks)}")

    if not all_chunks:
        print("ERROR: No chunks found in Neo4j!")
        return

    # Initialize RelationExtractor and LightRAG
    relation_extractor = RelationExtractor()
    lightrag = await get_lightrag_wrapper_async()

    total_relations_created = 0
    chunks_processed = 0
    chunks_skipped = 0
    chunks_with_errors = 0

    print(f"\n3. Processing {len(all_chunks)} chunks...\n")

    for idx, chunk_data in enumerate(all_chunks):
        chunk_id = chunk_data["chunk_id"]
        chunk_text = chunk_data.get("text", "")

        # Query entities for this chunk
        entity_query = """
        MATCH (e:base)-[:MENTIONED_IN]->(c:chunk {chunk_id: $chunk_id})
        RETURN e.entity_name AS name, e.entity_type AS type
        """
        try:
            entity_results = await neo4j_client.execute_read(entity_query, {"chunk_id": chunk_id})
            entities = [
                {"name": r["name"], "type": r.get("type", "UNKNOWN")}
                for r in entity_results
                if r.get("name")
            ]
        except Exception as e:
            print(f"   [{idx+1}/{len(all_chunks)}] ERROR querying entities: {e}")
            chunks_with_errors += 1
            continue

        # Need at least 2 entities to find relations
        if len(entities) < 2:
            print(
                f"   [{idx+1}/{len(all_chunks)}] SKIP: {chunk_id[:8]}... ({len(entities)} entities)"
            )
            chunks_skipped += 1
            continue

        # Extract relations via LLM
        try:
            relations = await relation_extractor.extract(chunk_text, entities)

            if not relations:
                print(
                    f"   [{idx+1}/{len(all_chunks)}] NO RELATIONS: {chunk_id[:8]}... (0 relations from {len(entities)} entities)"
                )
                chunks_skipped += 1
                continue

            # Store relations to Neo4j
            relations_created = await lightrag._store_relations_to_neo4j(
                relations=relations, chunk_id=chunk_id
            )
            total_relations_created += relations_created
            chunks_processed += 1
            print(
                f"   [{idx+1}/{len(all_chunks)}] OK: {chunk_id[:8]}... (+{relations_created} relations from {len(entities)} entities)"
            )

        except Exception as e:
            print(
                f"   [{idx+1}/{len(all_chunks)}] ERROR: {chunk_id[:8]}... - {type(e).__name__}: {e}"
            )
            chunks_with_errors += 1
            continue

    # Final stats
    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"   Total chunks:          {len(all_chunks)}")
    print(f"   Chunks processed:      {chunks_processed}")
    print(f"   Chunks skipped:        {chunks_skipped}")
    print(f"   Chunks with errors:    {chunks_with_errors}")
    print(f"   Total RELATES_TO created: {total_relations_created}")

    # Verify RELATES_TO in Neo4j
    verify_query = "MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count"
    result = await neo4j_client.execute_read(verify_query)
    print(f"\n   Final RELATES_TO count: {result[0]['count']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(backfill_relates_to())
