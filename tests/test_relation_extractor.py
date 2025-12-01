"""Direct test of RelationExtractor and RELATES_TO storage."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main():
    print("=" * 60)
    print("Testing RelationExtractor directly")
    print("=" * 60)

    # Test text with clear relationships
    test_text = """
    Machine Learning is a subset of Artificial Intelligence.
    Deep Learning is a specialized type of Machine Learning.
    TensorFlow is a framework developed by Google.
    PyTorch is a framework developed by Facebook.
    Both TensorFlow and PyTorch are used for Deep Learning.
    """

    # Mock entities that would be extracted
    test_entities = [
        {"name": "Machine Learning", "type": "TECHNOLOGY"},
        {"name": "Artificial Intelligence", "type": "TECHNOLOGY"},
        {"name": "Deep Learning", "type": "TECHNOLOGY"},
        {"name": "TensorFlow", "type": "PRODUCT"},
        {"name": "PyTorch", "type": "PRODUCT"},
        {"name": "Google", "type": "ORGANIZATION"},
        {"name": "Facebook", "type": "ORGANIZATION"},
    ]

    print(f"\nTest text: {test_text[:100]}...")
    print(f"Test entities: {[e['name'] for e in test_entities]}")

    # Test 1: RelationExtractor
    print("\n" + "-" * 40)
    print("Test 1: RelationExtractor.extract()")
    print("-" * 40)

    try:
        from src.components.graph_rag.relation_extractor import RelationExtractor

        extractor = RelationExtractor()
        relations = await extractor.extract(test_text, test_entities)

        print(f"Relations extracted: {len(relations)}")
        for rel in relations:
            print(f"  {rel['source']} --[{rel.get('type', 'RELATES_TO')}]--> {rel['target']}")
            if rel.get("description"):
                print(f"    Description: {rel['description'][:60]}...")

    except Exception as e:
        print(f"ERROR: RelationExtractor failed: {e}")
        import traceback
        traceback.print_exc()
        relations = []

    # Test 2: Store to Neo4j
    if relations:
        print("\n" + "-" * 40)
        print("Test 2: Store RELATES_TO to Neo4j")
        print("-" * 40)

        try:
            from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async

            lightrag = await get_lightrag_wrapper_async()

            # First, ensure entities exist in Neo4j
            from src.components.graph_rag.neo4j_client import get_neo4j_client
            neo4j = get_neo4j_client()

            # Create test entities if they don't exist
            for entity in test_entities:
                create_query = """
                MERGE (e:base {entity_name: $name})
                SET e.entity_type = $type
                """
                await neo4j.execute_write(create_query, {"name": entity["name"], "type": entity["type"]})
            print(f"Created/merged {len(test_entities)} test entities in Neo4j")

            # Store relations
            chunk_id = "test_chunk_001"
            relations_created = await lightrag._store_relations_to_neo4j(
                relations=relations, chunk_id=chunk_id
            )
            print(f"Relations stored to Neo4j: {relations_created}")

            # Verify
            verify_query = """
            MATCH (e1:base)-[r:RELATES_TO]->(e2:base)
            WHERE r.source_chunk = $chunk_id
            RETURN e1.entity_name AS source, e2.entity_name AS target, r.description AS desc
            """
            stored = await neo4j.execute_read(verify_query, {"chunk_id": chunk_id})
            print(f"\nVerified RELATES_TO in Neo4j: {len(stored)}")
            for rel in stored:
                print(f"  {rel['source']} --> {rel['target']}")

        except Exception as e:
            print(f"ERROR: Neo4j storage failed: {e}")
            import traceback
            traceback.print_exc()

    # Final count
    print("\n" + "-" * 40)
    print("Final RELATES_TO count")
    print("-" * 40)

    from src.components.graph_rag.neo4j_client import get_neo4j_client
    client = get_neo4j_client()
    count_result = await client.execute_read(
        "MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count"
    )
    print(f"Total RELATES_TO: {count_result[0]['count']}")


if __name__ == "__main__":
    asyncio.run(main())
