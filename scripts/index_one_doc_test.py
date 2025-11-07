"""
============================================================================
⚠️ DEPRECATED SCRIPT: Sprint 21
============================================================================
This script uses LlamaIndex SimpleDirectoryReader which is being replaced
by Docling CUDA Container in Sprint 21.

REPLACEMENT: Use scripts/test_docling_single_doc.py (Sprint 21, Feature 21.1)
MIGRATION STATUS: DO NOT USE for new testing
REMOVAL: Sprint 22
============================================================================

Sprint 19: Simple indexing for ONE document (UI testing).
Uses BOTH Qdrant AND Neo4j/LightRAG with fixes from Sprint 10 and Sprint 16.

Bug Fixes Applied:
- d8e52c0: start_token/end_token KeyError fix (Sprint 16)
- 79abe52: Path traversal temp directory fix (Sprint 10)

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
from src.components.vector_search.ingestion import DocumentIngestionPipeline
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.config import settings

logger = structlog.get_logger(__name__)


async def main():
    print("[*] Sprint 19: Indexing ONE document with full LightRAG support...")

    # Configuration
    collection_name = settings.qdrant_collection

    # ONE specific file to index
    test_file = (
        project_root
        / "data"
        / "sample_documents"
        / "9. Performance Tuning"
        / "EN-D-Performance Tuning.pptx"
    )

    if not test_file.exists():
        print(f"   ERROR: File not found: {test_file}")
        return

    try:
        # Step 1: Clear Qdrant
        print(f"\n[1/7] Clearing Qdrant collection '{collection_name}'...")
        qdrant_client = QdrantClientWrapper()
        try:
            await qdrant_client.delete_collection(collection_name)
            print("   [OK] Qdrant cleared")
        except Exception as e:
            print(f"   [INFO] Collection might not exist: {e}")

        # Step 2: Clear Neo4j
        print(f"\n[2/7] Clearing Neo4j database...")
        try:
            lightrag_wrapper = await get_lightrag_wrapper_async()
            await lightrag_wrapper.clear_database()
            print("   [OK] Neo4j cleared")
        except Exception as e:
            print(f"   [WARNING] Neo4j clear failed: {e}")

        # Step 3: Clear LightRAG working directory
        print(f"\n[3/7] Clearing LightRAG working directory...")
        lightrag_dir = Path(settings.lightrag_working_dir)
        if lightrag_dir.exists():
            try:
                shutil.rmtree(lightrag_dir)
                print(f"   [OK] LightRAG workdir cleared: {lightrag_dir}")
            except Exception as e:
                print(f"   [WARNING] Could not clear workdir: {e}")

        # Step 4: Index to Qdrant with temp directory fix
        print(f"\n[4/7] Indexing to Qdrant: {test_file.name}")

        # Create temp directory and copy file (to test path traversal fix)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            shutil.copy(test_file, temp_path / test_file.name)
            print(f"   [INFO] Using temp directory: {temp_path}")

            # FIX: Set allowed_base_path to temp directory (Sprint 10 fix 79abe52)
            pipeline = DocumentIngestionPipeline(allowed_base_path=temp_path)

            stats = await pipeline.index_documents(
                input_dir=str(temp_path),
                batch_size=100,
            )

            print(f"   [OK] Qdrant indexing complete")
            print(f"       Documents loaded: {stats.get('documents_loaded', 0)}")
            print(f"       Chunks created: {stats.get('chunks_created', 0)}")
            print(f"       Points indexed: {stats.get('points_indexed', 0)}")

        # Step 5: Index to Neo4j with start_token fix
        print(f"\n[5/7] Indexing to Neo4j/LightRAG: {test_file.name}")

        # Load document
        loader = SimpleDirectoryReader(input_files=[str(test_file)])
        documents = loader.load_data()
        print(f"   [INFO] Loaded {len(documents)} document pages")

        # Convert to LightRAG format
        lightrag_docs = []
        for doc in documents:
            content = doc.get_content()
            if content and content.strip():
                lightrag_docs.append(
                    {
                        "text": content,
                        "id": doc.doc_id or doc.metadata.get("file_name", "unknown"),
                    }
                )

        if lightrag_docs:
            # Use the optimized insert method (includes start_token fix from d8e52c0)
            graph_stats = await lightrag_wrapper.insert_documents_optimized(
                lightrag_docs
            )
            print(f"   [OK] Neo4j indexing complete")
            print(f"       Chunks stored: {graph_stats.get('chunks_stored', 0)}")
            print(f"       Entities extracted: {graph_stats.get('entities_extracted', 0)}")
            print(f"       Relations extracted: {graph_stats.get('relations_extracted', 0)}")
        else:
            print("   [WARNING] No documents to index")

        # Step 6: Verify Qdrant
        print(f"\n[6/7] Verifying Qdrant...")
        qdrant_info = await qdrant_client.get_collection_info(collection_name)
        if qdrant_info:
            print(
                f"   Collection '{collection_name}' has {qdrant_info.points_count} points"
            )
        else:
            print(f"   [WARNING] Could not verify Qdrant collection")

        # Step 7: Verify Neo4j
        print(f"\n[7/7] Verifying Neo4j...")
        graph_stats = await lightrag_wrapper.get_graph_stats()
        print(f"   Chunks: {graph_stats.get('total_chunks', 0)}")
        print(f"   Entities: {graph_stats.get('total_entities', 0)}")
        print(f"   Relations: {graph_stats.get('total_relations', 0)}")

        print("\n[SUCCESS] Indexing complete!")
        print(f"\nSummary:")
        print(f"   - Document: {test_file.name}")
        print(f"   - Collection: {collection_name}")
        print(f"   - Qdrant: {qdrant_info.points_count if qdrant_info else 'N/A'} vectors")
        print(
            f"   - Neo4j: {graph_stats.get('total_entities', 0)} entities, {graph_stats.get('total_relations', 0)} relations"
        )
        print(
            f"\n   Bug Fixes Applied:"
        )
        print(f"   ✅ Path traversal fix (79abe52): allowed_base_path={temp_path}")
        print(f"   ✅ start_token fix (d8e52c0): handled in lightrag_wrapper.py:883-907")

    except Exception as e:
        logger.exception("indexing_failed", error=str(e))
        print(f"\n[ERROR] Indexing failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
