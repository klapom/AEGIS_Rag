"""
Log chunks and entities from Neo4j to analyze extraction quality.
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
    print("[*] Analyzing Neo4j chunks and entities...")

    try:
        lightrag = await get_lightrag_wrapper_async()

        if not lightrag.rag or not lightrag.rag.chunk_entity_relation_graph:
            print("[ERROR] LightRAG not properly initialized")
            return

        graph = lightrag.rag.chunk_entity_relation_graph

        # Get all chunks with their text
        print("\n" + "=" * 80)
        print("CHUNKS IN NEO4J")
        print("=" * 80)

        chunk_query = """
        MATCH (c:chunk)
        RETURN c.chunk_id as id, c.chunk_index as index, c.document_id as doc_id,
               c.text as text, c.tokens as tokens
        ORDER BY c.chunk_index
        LIMIT 10
        """

        chunks = await run_query(graph, chunk_query)

        if chunks:
            print(f"\nTotal chunks to display: {len(chunks)} (showing first 10)")
            for i, chunk in enumerate(chunks, 1):
                text = chunk.get("text", "")
                chunk_id = chunk.get("id", "N/A")
                index = chunk.get("index", "N/A")
                tokens = chunk.get("tokens", "N/A")

                # Show first 200 chars of text
                preview = text[:200] if text and len(text) > 200 else text
                # Handle unicode encoding issues
                preview_safe = (
                    preview.encode("utf-8", errors="replace").decode("utf-8") if preview else ""
                )

                print(f"\n--- Chunk {i} ---")
                print(f"  ID: {chunk_id}")
                print(f"  Index: {index}")
                print(f"  Tokens: {tokens}")
                print(f"  Text Preview:")
                print(f"  {preview_safe}...")
                print()
        else:
            print("  No chunks found!")

        # Get total chunk count
        count_query = "MATCH (c:chunk) RETURN count(c) as count"
        count_result = await run_query(graph, count_query)
        total_chunks = count_result[0]["count"] if count_result else 0
        print(f"\nTotal chunks in database: {total_chunks}")

        # Get all entities
        print("\n" + "=" * 80)
        print("ENTITIES IN NEO4J")
        print("=" * 80)

        entity_query = """
        MATCH (e)
        WHERE ANY(label IN labels(e) WHERE label STARTS WITH 'base:')
        RETURN labels(e) as labels, properties(e) as props
        """

        entities = await run_query(graph, entity_query)

        if entities:
            print(f"\nTotal entities: {len(entities)}")
            for i, entity in enumerate(entities, 1):
                labels = entity.get("labels", [])
                props = entity.get("props", {})

                label_str = ":".join(labels)
                print(f"\n--- Entity {i} ---")
                print(f"  Labels: {label_str}")
                print(f"  Properties:")
                for key, val in props.items():
                    if isinstance(val, str) and len(val) > 100:
                        val = val[:100] + "..."
                    print(f"    {key}: {val}")
        else:
            print("  No entities found!")

        # Get relationships
        print("\n" + "=" * 80)
        print("RELATIONSHIPS IN NEO4J")
        print("=" * 80)

        rel_query = """
        MATCH (e)-[r:MENTIONED_IN]->(c:chunk)
        RETURN labels(e) as entity_labels, type(r) as rel_type,
               c.chunk_id as chunk_id, c.chunk_index as chunk_index
        ORDER BY c.chunk_index
        """

        rels = await run_query(graph, rel_query)

        if rels:
            print(f"\nTotal MENTIONED_IN relationships: {len(rels)}")
            for i, rel in enumerate(rels, 1):
                entity_labels = ":".join(rel.get("entity_labels", []))
                chunk_id = rel.get("chunk_id", "N/A")
                chunk_index = rel.get("chunk_index", "N/A")

                print(f"  {i}. ({entity_labels})-[MENTIONED_IN]->(chunk {chunk_index})")
        else:
            print("  No relationships found!")

        # Sample chunk text to see what kind of content we have
        print("\n" + "=" * 80)
        print("SAMPLE CHUNK TEXTS (First 3 chunks, full text)")
        print("=" * 80)

        sample_query = """
        MATCH (c:chunk)
        RETURN c.chunk_index as index, c.text as text
        ORDER BY c.chunk_index
        LIMIT 3
        """

        samples = await run_query(graph, sample_query)

        for sample in samples:
            index = sample.get("index", "N/A")
            text = sample.get("text", "")
            # Handle unicode encoding
            text_safe = text.encode("utf-8", errors="replace").decode("utf-8") if text else ""

            print(f"\n--- Chunk {index} (Full Text) ---")
            print(text_safe)
            print()

        # Analysis summary
        print("\n" + "=" * 80)
        print("ANALYSIS SUMMARY")
        print("=" * 80)
        print(f"Total Chunks: {total_chunks}")
        print(f"Total Entities: {len(entities)}")
        print(f"Total Relations: {len(rels)}")
        print(
            f"\nEntity-to-Chunk Ratio: {len(entities) / total_chunks if total_chunks > 0 else 0:.3f}"
        )
        print(f"Relation-to-Chunk Ratio: {len(rels) / total_chunks if total_chunks > 0 else 0:.3f}")

        if len(entities) < 10 and total_chunks > 100:
            print("\n[WARNING] Very low entity extraction rate!")
            print(
                f"  Expected: ~{total_chunks * 0.05:.0f}-{total_chunks * 0.15:.0f} entities for {total_chunks} chunks"
            )
            print(f"  Actual: {len(entities)} entities")
            print("\n  Possible causes:")
            print("  1. Three-Phase Pipeline is very conservative (working as designed)")
            print("  2. Document has mostly generic/procedural text without named entities")
            print("  3. SpaCy NER model not detecting entities in this domain")

    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
