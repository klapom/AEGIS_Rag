"""Quick script to check Neo4j content."""
import asyncio

from src.components.graph_rag.neo4j_client import Neo4jClient


async def main():
    client = Neo4jClient()

    # Count nodes by label
    result = await client.execute_query("""
        MATCH (n)
        RETURN labels(n) as labels, count(n) as count
    """)
    print("=== NODE COUNTS ===")
    for r in result:
        print(f"  {r}")

    # Get entity names from base label
    result2 = await client.execute_query("""
        MATCH (n:base)
        RETURN n.entity_id as entity_id
        LIMIT 15
    """)
    print("\n=== ENTITIES (base label) ===")
    for r in result2:
        print(f"  {r}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
