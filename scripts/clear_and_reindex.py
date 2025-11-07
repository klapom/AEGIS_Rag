"""
============================================================================
⚠️ DEPRECATED SCRIPT: Sprint 21
============================================================================
This script uses LlamaIndex SimpleDirectoryReader which is being replaced
by Docling CUDA Container in Sprint 21.

REPLACEMENT: Use scripts/test_docling_clear_reindex.py (Sprint 21, Feature 21.1)
MIGRATION STATUS: DO NOT USE for new testing
REMOVAL: Sprint 22
============================================================================

Clear Neo4j manually and reindex Performance Tuning.pptx with the fix.

⚠️ WARNING: This script will be replaced in Sprint 21
"""
import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from llama_index.core import SimpleDirectoryReader

from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.core.config import settings

logger = structlog.get_logger(__name__)


async def main():
    print("="*80)
    print("CLEAR NEO4J AND REINDEX")
    print("="*80)

    test_file = (
        project_root
        / "data"
        / "sample_documents"
        / "9. Performance Tuning"
        / "EN-D-Performance Tuning.pptx"
    )

    print(f"\nFile: {test_file.name}")

    try:
        # Step 1: Clear Neo4j manually
        print(f"\n[1/2] Clearing Neo4j...")
        lightrag = await get_lightrag_wrapper_async()

        if lightrag.rag and lightrag.rag.chunk_entity_relation_graph:
            graph = lightrag.rag.chunk_entity_relation_graph
            async with graph._driver.session() as session:
                await session.run("MATCH (n) DETACH DELETE n")
                print("   [OK] Neo4j cleared")
        else:
            print("   [ERROR] Neo4j not available")
            return

        # Step 2: Index to Neo4j
        print(f"\n[2/2] Indexing to Neo4j...")

        # Load document
        loader = SimpleDirectoryReader(input_files=[str(test_file)])
        documents = loader.load_data()
        print(f"   Loaded {len(documents)} pages")

        # Convert to LightRAG format
        lightrag_docs = []
        for doc in documents:
            content = doc.get_content()
            if content and content.strip():
                lightrag_docs.append({
                    "text": content,
                    "id": doc.doc_id or doc.metadata.get("file_name", "unknown"),
                })

        print(f"   Prepared {len(lightrag_docs)} documents")

        # Index
        graph_stats = await lightrag.insert_documents_optimized(lightrag_docs)

        print(f"\n   [OK] Indexing complete!")
        print(f"       Total entities: {graph_stats.get('total_entities', 0)}")
        print(f"       Total relations: {graph_stats.get('total_relations', 0)}")
        print(f"       Total chunks: {graph_stats.get('total_chunks', 0)}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
