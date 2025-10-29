"""Test Hybrid RAG with only 10 documents.

Sprint 16 Feature 16.7: Quick test of hybrid indexing pipeline.
"""

import asyncio
import shutil
from pathlib import Path

import structlog
from llama_index.core import SimpleDirectoryReader

from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.components.vector_search.ingestion import DocumentIngestionPipeline
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.config import settings

logger = structlog.get_logger(__name__)


async def main():
    """Test with 10 documents only."""
    logger.info(
        "===== Test: Hybrid RAG with 10 Documents =====",
        chunking_strategy="adaptive",
        chunk_size=600,
        overlap=150,
    )

    # Input directory
    input_dir = Path(settings.documents_base_path) / "sample_documents"

    if not input_dir.exists():
        logger.error("input_directory_not_found", path=str(input_dir))
        return

    try:
        # Step 1: Clear Qdrant
        logger.info("=== Step 1: Clearing Qdrant ===")
        qdrant_client = QdrantClientWrapper()
        await qdrant_client.delete_collection(settings.qdrant_collection)
        logger.info("qdrant_cleared")

        # Step 2: Clear Neo4j
        logger.info("=== Step 2: Clearing Neo4j (skip - will fail gracefully) ===")
        # Skip Neo4j clear for now - will overwrite

        # Step 3: Clear LightRAG working directory (skip if in use)
        logger.info("=== Step 3: Clearing LightRAG working directory (skip if locked) ===")
        lightrag_dir = Path(settings.lightrag_working_dir)
        if lightrag_dir.exists():
            try:
                shutil.rmtree(lightrag_dir)
                logger.info("lightrag_workdir_cleared", path=str(lightrag_dir))
            except PermissionError:
                logger.warning("lightrag_workdir_locked", path=str(lightrag_dir), note="Will overwrite data")

        # Step 4: Load ONLY 10 documents
        logger.info("=== Step 4: Loading 10 documents ===")
        loader = SimpleDirectoryReader(
            input_dir=str(input_dir),
            required_exts=[".pdf", ".docx"],  # Use available file types
            recursive=True,
            filename_as_id=True,
        )
        all_documents = loader.load_data()

        # Take only first 10 documents
        documents = all_documents[:10]
        logger.info("documents_loaded_for_test", total=len(all_documents), selected=len(documents))

        # Step 5: Index to Qdrant
        logger.info("=== Step 5: Indexing to Qdrant ===")
        pipeline = DocumentIngestionPipeline()

        # Manual indexing with selected documents
        await pipeline.qdrant_client.create_collection(
            collection_name=settings.qdrant_collection,
            vector_size=pipeline.embedding_service.get_embedding_dimension(),
        )

        chunks = await pipeline.chunk_documents(documents)
        embeddings = await pipeline.generate_embeddings(chunks)

        from qdrant_client.models import PointStruct
        points = [
            PointStruct(
                id=chunk.chunk_id,
                vector=embedding,
                payload=chunk.to_qdrant_payload(),
            )
            for chunk, embedding in zip(chunks, embeddings, strict=False)
        ]

        await pipeline.qdrant_client.upsert_points(
            collection_name=settings.qdrant_collection,
            points=points,
            batch_size=100,
        )

        logger.info("qdrant_indexing_complete", chunks=len(chunks), points=len(points))

        # Step 6: Index to Neo4j
        logger.info("=== Step 6: Indexing to Neo4j ===")
        lightrag_wrapper = await get_lightrag_wrapper_async()

        # Convert to LightRAG format
        lightrag_docs = []
        for doc in documents:
            content = doc.get_content()
            if content and content.strip():
                lightrag_docs.append({
                    "text": content,
                    "id": doc.doc_id or doc.metadata.get("file_name", "unknown"),
                })

        logger.info("documents_converted_for_lightrag", count=len(lightrag_docs))

        if lightrag_docs:
            graph_stats = await lightrag_wrapper.insert_documents_optimized(lightrag_docs)
            logger.info("neo4j_indexing_complete", **graph_stats)

        # Step 7: Verify
        logger.info("=== Step 7: Verification ===")

        # Qdrant
        qdrant_info = await qdrant_client.get_collection_info(settings.qdrant_collection)
        if qdrant_info:
            logger.info(
                "qdrant_verification_success",
                points_count=qdrant_info.points_count,
                vectors_count=qdrant_info.vectors_count,
            )

        # Neo4j
        graph_stats = await lightrag_wrapper.get_graph_stats()
        logger.info("neo4j_verification_success", **graph_stats)

        logger.info("===== Test Complete =====")

    except Exception as e:
        logger.error("test_failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
