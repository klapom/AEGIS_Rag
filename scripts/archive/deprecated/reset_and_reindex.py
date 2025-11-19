"""Reset all indices and re-index with hybrid pipeline (Qdrant + Neo4j).

Sprint 16 Feature 16.7: Complete reset and re-indexing workflow.
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


async def clear_qdrant():
    """Clear Qdrant collection."""
    logger.info("=== Phase 1: Clearing Qdrant ===")

    qdrant_client = QdrantClientWrapper()

    try:
        await qdrant_client.delete_collection(settings.qdrant_collection)
        logger.info(
            "qdrant_collection_deleted",
            collection=settings.qdrant_collection,
        )
    except Exception as e:
        logger.warning(
            "qdrant_collection_delete_failed",
            collection=settings.qdrant_collection,
            error=str(e),
        )


async def clear_neo4j():
    """Clear Neo4j database."""
    logger.info("=== Phase 2: Clearing Neo4j ===")

    try:
        lightrag_wrapper = await get_lightrag_wrapper_async()

        # Clear all nodes and relationships
        await lightrag_wrapper.clear_database()
        logger.info("neo4j_database_cleared")

    except Exception as e:
        logger.error(
            "neo4j_clear_failed",
            error=str(e),
        )


async def clear_lightrag_workdir():
    """Clear LightRAG working directory (embedding cache)."""
    logger.info("=== Phase 3: Clearing LightRAG working directory ===")

    # LightRAG working directory from config
    lightrag_dir = Path(settings.lightrag_working_dir)

    if lightrag_dir.exists():
        try:
            shutil.rmtree(lightrag_dir)
            logger.info(
                "lightrag_workdir_cleared",
                path=str(lightrag_dir),
            )
        except Exception as e:
            logger.error(
                "lightrag_workdir_clear_failed",
                path=str(lightrag_dir),
                error=str(e),
            )
    else:
        logger.info(
            "lightrag_workdir_not_found",
            path=str(lightrag_dir),
        )


async def index_to_qdrant(input_dir: str):
    """Index documents to Qdrant."""
    logger.info("=== Phase 4: Indexing to Qdrant ===")

    pipeline = DocumentIngestionPipeline()

    stats = await pipeline.index_documents(
        input_dir=input_dir,
        batch_size=100,
    )

    logger.info(
        "qdrant_indexing_completed",
        **stats,
    )

    return stats


async def index_to_neo4j(input_dir: str):
    """Index documents to Neo4j/LightRAG."""
    logger.info("=== Phase 5: Indexing to Neo4j ===")

    try:
        lightrag_wrapper = await get_lightrag_wrapper_async()

        # Load documents
        loader = SimpleDirectoryReader(
            input_dir=input_dir,
            required_exts=[".pdf", ".txt", ".md", ".docx", ".csv", ".pptx"],
            recursive=True,
            filename_as_id=True,
        )

        documents = loader.load_data()
        logger.info(
            "documents_loaded_for_neo4j",
            count=len(documents),
        )

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

        logger.info(
            "documents_converted_for_lightrag",
            count=len(lightrag_docs),
        )

        # Insert into LightRAG
        if lightrag_docs:
            graph_stats = await lightrag_wrapper.insert_documents_optimized(lightrag_docs)
            logger.info(
                "neo4j_indexing_completed",
                **graph_stats,
            )
            return graph_stats
        else:
            logger.warning("no_documents_to_index_neo4j")
            return {}

    except Exception as e:
        logger.error(
            "neo4j_indexing_failed",
            error=str(e),
        )
        raise


async def verify_indices():
    """Verify both indices have data."""
    logger.info("=== Phase 6: Verifying indices ===")

    # Verify Qdrant
    qdrant_client = QdrantClientWrapper()
    qdrant_info = await qdrant_client.get_collection_info(settings.qdrant_collection)

    if qdrant_info:
        logger.info(
            "qdrant_verification",
            collection=settings.qdrant_collection,
            points_count=qdrant_info.points_count,
            vectors_count=qdrant_info.vectors_count,
        )
    else:
        logger.error("qdrant_verification_failed")

    # Verify Neo4j
    try:
        lightrag_wrapper = await get_lightrag_wrapper_async()
        graph_stats = await lightrag_wrapper.get_graph_stats()

        logger.info(
            "neo4j_verification",
            **graph_stats,
        )

        # Check if entities and relations exist
        if graph_stats.get("entities_count", 0) > 0 and graph_stats.get("relations_count", 0) > 0:
            logger.info(
                "neo4j_verification_success",
                status="Neo4j has entities and relations ✓",
            )
        else:
            logger.warning(
                "neo4j_verification_warning",
                status="Neo4j is empty or missing entities/relations",
            )

    except Exception as e:
        logger.error(
            "neo4j_verification_failed",
            error=str(e),
        )


async def main():
    """Main execution flow."""
    logger.info(
        "===== Sprint 16 Feature 16.7: Hybrid RAG Reset & Re-index =====",
        chunking_strategy="adaptive",
        chunk_size=600,
        overlap=150,
    )

    # Input directory
    input_dir = Path(settings.documents_base_path) / "sample_documents"

    if not input_dir.exists():
        logger.error(
            "input_directory_not_found",
            path=str(input_dir),
        )
        return

    logger.info(
        "input_directory_found",
        path=str(input_dir),
    )

    try:
        # Step 1-3: Clear all indices
        await clear_qdrant()
        await clear_neo4j()
        await clear_lightrag_workdir()

        logger.info("=== All indices cleared, starting re-indexing ===")

        # Step 4-5: Re-index (parallel)
        qdrant_task = index_to_qdrant(str(input_dir))
        neo4j_task = index_to_neo4j(str(input_dir))

        results = await asyncio.gather(qdrant_task, neo4j_task, return_exceptions=True)

        # Check for errors
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "indexing_task_failed",
                    task=["Qdrant", "Neo4j"][idx],
                    error=str(result),
                )

        # Step 6: Verify
        await verify_indices()

        logger.info(
            "===== Hybrid RAG Re-indexing Complete =====",
            status="success",
        )

    except Exception as e:
        logger.error(
            "reindexing_failed",
            error=str(e),
        )
        raise


if __name__ == "__main__":
    asyncio.run(main())
