"""Debug script to test RELATES_TO extraction directly."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def test_relates_to_extraction():
    """Test the RELATES_TO extraction directly."""
    from src.components.graph_rag.neo4j_client import get_neo4j_client
    from src.components.graph_rag.relation_extractor import RelationExtractor
    from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async

    print("=" * 60)
    print("Testing RELATES_TO Extraction")
    print("=" * 60)

    # Get Neo4j client
    neo4j_client = get_neo4j_client()
    print(f"\n1. Neo4j client initialized: {neo4j_client}")

    # Get chunk_id from Neo4j
    chunk_query = "MATCH (c:chunk) RETURN c.chunk_id as chunk_id, c.text as text LIMIT 1"
    chunks = await neo4j_client.execute_read(chunk_query)
    print(f"\n2. Chunks found: {len(chunks)}")

    if not chunks:
        print("ERROR: No chunks found in Neo4j!")
        return

    chunk_id = chunks[0]["chunk_id"]
    chunk_text = chunks[0]["text"][:200]
    print(f"   chunk_id: {chunk_id}")
    print(f"   text preview: {chunk_text}...")

    # Query entities for this chunk
    entity_query = """
    MATCH (e:base)-[:MENTIONED_IN]->(c:chunk {chunk_id: $chunk_id})
    RETURN e.entity_name AS name, e.entity_type AS type
    """
    print(f"\n3. Running entity query with chunk_id: {chunk_id}")
    entity_results = await neo4j_client.execute_read(entity_query, {"chunk_id": chunk_id})
    print(f"   entity_results type: {type(entity_results)}")
    print(f"   entity_results count: {len(entity_results)}")

    for r in entity_results:
        print(f"   - {r}")

    # Build entities list
    entities = [
        {"name": r["name"], "type": r.get("type", "UNKNOWN")}
        for r in entity_results
        if r.get("name")
    ]
    print(f"\n4. Entities built: {len(entities)}")
    for e in entities:
        print(f"   - {e}")

    if len(entities) < 2:
        print("\nERROR: Less than 2 entities - relation extraction would be skipped!")
        return

    # Test RelationExtractor
    print("\n5. Testing RelationExtractor.extract()...")
    relation_extractor = RelationExtractor()

    try:
        full_text = chunks[0]["text"] if "text" in chunks[0] else chunk_text
        relations = await relation_extractor.extract(full_text, entities)
        print(f"   Relations extracted: {len(relations) if relations else 0}")
        if relations:
            for rel in relations[:5]:
                print(f"   - {rel}")
    except Exception as e:
        print(f"   ERROR in RelationExtractor: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return

    if not relations:
        print("\nWARNING: No relations extracted by LLM!")
        return

    # Test storing relations to Neo4j
    print("\n6. Testing _store_relations_to_neo4j()...")
    lightrag = await get_lightrag_wrapper_async()

    try:
        relations_created = await lightrag._store_relations_to_neo4j(
            relations=relations, chunk_id=chunk_id
        )
        print(f"   Relations created: {relations_created}")
    except Exception as e:
        print(f"   ERROR in _store_relations_to_neo4j: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return

    # Verify RELATES_TO in Neo4j
    print("\n7. Verifying RELATES_TO in Neo4j...")
    verify_query = "MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count"
    result = await neo4j_client.execute_read(verify_query)
    print(f"   RELATES_TO count: {result[0]['count']}")

    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_relates_to_extraction())
