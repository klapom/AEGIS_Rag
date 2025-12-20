"""
Debug version of indexing script with extensive logging for Three-Phase Pipeline.
Indexes Performance Tuning.pptx with detailed entity extraction logging.
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
    print("=" * 80)
    print("DEBUG: Indexing Performance Tuning with Extended Logging")
    print("=" * 80)

    # Configuration
    collection_name = settings.qdrant_collection

    # Performance Tuning PowerPoint
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

    print(f"\nFile to index: {test_file.name}")
    print(f"File size: {test_file.stat().st_size / 1024 / 1024:.2f} MB")

    try:
        # Step 1: Clear Qdrant
        print(f"\n[1/5] Clearing Qdrant collection '{collection_name}'...")
        qdrant_client = QdrantClientWrapper()
        try:
            await qdrant_client.delete_collection(collection_name)
            print("   [OK] Qdrant cleared")
        except Exception as e:
            print(f"   [INFO] Collection might not exist: {e}")

        # Step 2: Clear Neo4j
        print("\n[2/5] Clearing Neo4j database...")
        try:
            lightrag_wrapper = await get_lightrag_wrapper_async()
            await lightrag_wrapper.clear_database()
            print("   [OK] Neo4j cleared")
        except Exception as e:
            print(f"   [WARNING] Neo4j clear failed: {e}")

        # Step 3: Clear LightRAG working directory
        print("\n[3/5] Clearing LightRAG working directory...")
        lightrag_dir = Path(settings.lightrag_working_dir)
        if lightrag_dir.exists():
            try:
                shutil.rmtree(lightrag_dir)
                print(f"   [OK] LightRAG workdir cleared: {lightrag_dir}")
            except Exception as e:
                print(f"   [WARNING] Could not clear workdir: {e}")

        # Step 4: Index to Qdrant
        print(f"\n[4/5] Indexing to Qdrant: {test_file.name}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            shutil.copy(test_file, temp_path / test_file.name)

            pipeline = DocumentIngestionPipeline(allowed_base_path=temp_path)
            stats = await pipeline.index_documents(
                input_dir=str(temp_path),
                batch_size=100,
            )

            print("   [OK] Qdrant indexing complete")
            print(f"       Documents loaded: {stats.get('documents_loaded', 0)}")
            print(f"       Chunks created: {stats.get('chunks_created', 0)}")
            print(f"       Points indexed: {stats.get('points_indexed', 0)}")

        # Step 5: Index to Neo4j with DETAILED LOGGING
        print("\n[5/5] Indexing to Neo4j/LightRAG with DEBUG logging...")

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

        print(f"   [INFO] Prepared {len(lightrag_docs)} documents for indexing")

        if lightrag_docs:
            # IMPORTANT: Add debug logging to the wrapper
            # We'll call the method and monitor its execution
            print("\n   [DEBUG] Calling insert_documents_optimized...")
            print("   [DEBUG] This uses Three-Phase Pipeline:")
            print("           Phase 1: SpaCy NER extraction")
            print("           Phase 2: Entity deduplication")
            print("           Phase 3: Gemma LLM refinement")
            print()

            # Enable verbose logging by setting environment variable
            import os

            os.environ["LIGHTRAG_DEBUG"] = "1"

            # Call the optimized insertion
            graph_stats = await lightrag_wrapper.insert_documents_optimized(lightrag_docs)

            print("\n   [OK] Neo4j indexing complete")
            print(f"       Chunks stored: {graph_stats.get('chunks_stored', 0)}")
            print(f"       Entities extracted: {graph_stats.get('entities_extracted', 0)}")
            print(f"       Relations extracted: {graph_stats.get('relations_extracted', 0)}")

            # VERIFY the data immediately
            print("\n   [VERIFICATION] Checking Neo4j data...")

            # Quick verification query
            if lightrag_wrapper.rag and lightrag_wrapper.rag.chunk_entity_relation_graph:
                graph = lightrag_wrapper.rag.chunk_entity_relation_graph

                async def run_query(query):
                    async with graph._driver.session() as session:
                        result = await session.run(query)
                        return await result.data()

                # Count entities with names
                entities_with_names = await run_query(
                    """
                    MATCH (e)
                    WHERE ANY(label IN labels(e) WHERE label STARTS WITH 'base:')
                    RETURN COUNT(e) as total,
                           SUM(CASE WHEN e.entity_name IS NOT NULL THEN 1 ELSE 0 END) as with_names,
                           SUM(CASE WHEN e.entity_name IS NULL THEN 1 ELSE 0 END) as without_names
                """
                )

                if entities_with_names:
                    result = entities_with_names[0]
                    print(f"       Total entities: {result['total']}")
                    print(f"       With names: {result['with_names']}")
                    print(f"       Without names (BUG!): {result['without_names']}")

                # Sample entities
                sample_entities = await run_query(
                    """
                    MATCH (e)
                    WHERE ANY(label IN labels(e) WHERE label STARTS WITH 'base:')
                    RETURN labels(e) as labels,
                           e.entity_name as name,
                           e.entity_id as id
                    LIMIT 5
                """
                )

                print("\n       Sample entities:")
                for i, ent in enumerate(sample_entities, 1):
                    label = ":".join(ent["labels"])
                    name = ent.get("name", "UNNAMED!")
                    ent_id = ent.get("id", "no-id")
                    print(f"         {i}. [{label}] name='{name}' id={ent_id}")

                # Check relations
                rel_stats = await run_query(
                    """
                    MATCH ()-[r:MENTIONED_IN]->(c:chunk)
                    RETURN COUNT(DISTINCT c.chunk_index) as unique_chunks,
                           COUNT(r) as total_relations
                """
                )

                if rel_stats:
                    result = rel_stats[0]
                    print(f"\n       Relations: {result['total_relations']} total")
                    print(f"       Spanning {result['unique_chunks']} unique chunks")

        else:
            print("   [WARNING] No documents to index")

        print("\n" + "=" * 80)
        print("INDEXING COMPLETE - Check output above for issues")
        print("=" * 80)

    except Exception as e:
        logger.exception("indexing_failed", error=str(e))
        print(f"\n[ERROR] Indexing failed: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
