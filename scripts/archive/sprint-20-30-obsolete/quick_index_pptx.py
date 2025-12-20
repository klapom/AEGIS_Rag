"""Quick script to index the Performance Tuning PowerPoint file."""

import asyncio
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.components.vector_search.ingestion import DocumentIngestionPipeline


async def main():
    print("=" * 60)
    print("Quick PowerPoint Indexing - Performance Tuning")
    print("=" * 60)

    # File to index
    pptx_file = (
        project_root
        / "data"
        / "sample_documents"
        / "9. Performance Tuning"
        / "EN-D-Performance Tuning.pptx"
    )

    if not pptx_file.exists():
        print(f"ERROR: File not found: {pptx_file}")
        return

    print(f"\nFile: {pptx_file.name}")
    print(f"Size: {pptx_file.stat().st_size / 1024 / 1024:.2f} MB")

    try:
        # Step 1: Index to Qdrant
        print("\n[1/2] Indexing to Qdrant...")
        pipeline = DocumentIngestionPipeline()

        # Process file
        result = await pipeline.ingest_document(str(pptx_file))

        print(f"   ✓ Document indexed: {result['document_id']}")
        print(f"   ✓ Chunks created: {result['chunk_ids_count']}")

        # Step 2: Index to Neo4j/LightRAG
        print("\n[2/2] Indexing to Neo4j (LightRAG)...")
        lightrag = await get_lightrag_wrapper_async()

        # Read file content for LightRAG
        from llama_index.core import SimpleDirectoryReader

        docs = SimpleDirectoryReader(input_files=[str(pptx_file)]).load_data()
        full_text = "\n\n".join([doc.text for doc in docs])

        # Insert to LightRAG
        await lightrag.insert(full_text)
        print("   ✓ Indexed to LightRAG")

        print("\n" + "=" * 60)
        print("✅ INDEXING COMPLETE")
        print("=" * 60)
        print(f"Qdrant: {result['chunk_ids_count']} chunks")
        print("Neo4j: Entities + Relations stored")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
