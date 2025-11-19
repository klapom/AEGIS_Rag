"""
Check what node labels exist in Neo4j.
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
    print("[*] Checking Neo4j node labels...")

    try:
        lightrag = await get_lightrag_wrapper_async()

        if not lightrag.rag or not lightrag.rag.chunk_entity_relation_graph:
            print("[ERROR] LightRAG not properly initialized")
            return

        graph = lightrag.rag.chunk_entity_relation_graph

        # Get all node labels
        label_query = """
        MATCH (n)
        RETURN DISTINCT labels(n) as labels, count(n) as count
        ORDER BY count DESC
        """

        results = await run_query(graph, label_query)

        print("\nNode labels in Neo4j:")
        print("=" * 60)
        for row in results:
            labels = row["labels"]
            count = row["count"]
            label_str = ":".join(labels) if labels else "(no label)"
            print(f"   {label_str}: {count} nodes")

        # Sample some nodes to see properties
        print("\n\nSample node properties:")
        print("=" * 60)
        sample_query = """
        MATCH (n)
        RETURN labels(n) as labels, properties(n) as props
        LIMIT 3
        """

        samples = await run_query(graph, sample_query)
        for i, row in enumerate(samples, 1):
            labels = row["labels"]
            props = row["props"]
            label_str = ":".join(labels) if labels else "(no label)"
            print(f"\n{i}. {label_str}")
            print(f"   Properties: {list(props.keys())}")

            # Show first property value as example
            if props:
                first_key = list(props.keys())[0]
                first_val = props[first_key]
                if isinstance(first_val, str) and len(first_val) > 100:
                    first_val = first_val[:100] + "..."
                print(f"   Sample: {first_key} = {first_val}")

    except Exception as e:
        print(f"\n[ERROR] Check failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
