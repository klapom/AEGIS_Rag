"""Verify RELATES_TO relationships in Neo4j."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def verify():
    from src.components.graph_rag.neo4j_client import get_neo4j_client

    client = get_neo4j_client()

    # Count all relationships
    count_query = "MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count"
    count_result = await client.execute_read(count_query)
    print(f"RELATES_TO count: {count_result[0]['count']}")

    # List all RELATES_TO relationships
    list_query = """
    MATCH (e1:base)-[r:RELATES_TO]->(e2:base)
    RETURN e1.entity_name AS source, e2.entity_name AS target, r.description AS description
    LIMIT 10
    """
    relations = await client.execute_read(list_query)
    print(f"\nRELATES_TO relationships:")
    for rel in relations:
        desc = rel["description"][:60] + "..." if rel["description"] and len(rel["description"]) > 60 else (rel["description"] or "N/A")
        print(f"  {rel['source']} --> {rel['target']}")
        print(f"    {desc}")


if __name__ == "__main__":
    asyncio.run(verify())
