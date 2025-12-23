"""Test ingestion to debug RELATES_TO extraction."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main():
    from pathlib import Path

    from src.components.graph_rag.neo4j_client import get_neo4j_client
    from src.components.ingestion.langgraph_pipeline import run_ingestion_pipeline

    # Count RELATES_TO before
    client = get_neo4j_client()
    before_result = await client.execute_read(
        "MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count"
    )
    before_count = before_result[0]["count"]
    print(f"RELATES_TO count BEFORE: {before_count}")

    # Run ingestion - use a PDF file that Docling can process
    file_path = Path("data/sample_documents/1. Basic Admin/DE-D-BasicAdministration.pdf")
    document_id = "test_relates_to_002"
    batch_id = "test_batch_002"
    print(f"\nStarting ingestion of {file_path}...")

    try:
        result = await run_ingestion_pipeline(
            document_path=str(file_path),
            document_id=document_id,
            batch_id=batch_id,
        )
        print("\nIngestion completed!")
        print(f"Result keys: {result.keys() if isinstance(result, dict) else type(result)}")

        if isinstance(result, dict):
            print(f"Chunks created: {len(result.get('chunks', []))}")
            print(f"Relations count: {result.get('relations_count', 'N/A')}")
            print(f"Graph status: {result.get('graph_status', 'N/A')}")

    except Exception as e:
        print(f"Ingestion failed: {e}")
        import traceback

        traceback.print_exc()

    # Count RELATES_TO after
    after_result = await client.execute_read("MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count")
    after_count = after_result[0]["count"]
    print(f"\nRELATES_TO count AFTER: {after_count}")
    print(f"NEW RELATES_TO created: {after_count - before_count}")

    # Show new RELATES_TO if any
    if after_count > before_count:
        new_rels = await client.execute_read(
            """
            MATCH (e1:base)-[r:RELATES_TO]->(e2:base)
            RETURN e1.entity_name AS source, e2.entity_name AS target,
                   r.description AS desc
            ORDER BY r.created_at DESC
            LIMIT 10
        """
        )
        print("\nNew RELATES_TO relationships:")
        for rel in new_rels:
            print(f"  {rel['source']} --> {rel['target']}")
            if rel.get("desc"):
                print(f"    {rel['desc'][:60]}...")


if __name__ == "__main__":
    asyncio.run(main())
