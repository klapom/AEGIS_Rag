"""Fast Upload Pipeline for Two-Phase Document Upload (Sprint 83 Feature 83.4).

This module provides Phase 1: Fast User Upload (2-5s response time).

Phase 1 Workflow:
    1. Docling parsing (reuse existing)
    2. Adaptive section-aware chunking (reuse existing)
    3. BGE-M3 embedding generation (reuse existing)
    4. Qdrant vector upload (skip Neo4j graph initially)
    5. Hybrid SpaCy NER extraction (entities only, no relations)
    6. Store preliminary entities in Redis cache

Performance Target: <5s total response time

Example:
    >>> from fast_pipeline import run_fast_upload
    >>> document_id = await run_fast_upload(
    ...     file_path="/tmp/document.pdf",
    ...     namespace="research",
    ...     domain="ai_papers",
    ... )
    >>> # Returns document_id after ~2-5s
"""

import asyncio
import hashlib
import time
import uuid
from pathlib import Path
from typing import Any

import spacy
import structlog
from qdrant_client.models import PointStruct

from src.components.ingestion.background_jobs import get_background_job_queue
from src.components.ingestion.docling_client import DoclingClient
from src.components.ingestion.nodes.adaptive_chunking import adaptive_section_chunking
from src.components.shared.embedding_service import get_embedding_service
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.config import settings
from src.core.exceptions import IngestionError

logger = structlog.get_logger(__name__)

# SpaCy model for fast NER (no GPU required)
_spacy_nlp = None


def get_spacy_nlp():
    """Get SpaCy NLP model (singleton).

    Returns:
        spacy.Language: Loaded SpaCy model (en_core_web_sm)
    """
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            _spacy_nlp = spacy.load("en_core_web_sm")
            logger.info("spacy_nlp_loaded", model="en_core_web_sm")
        except OSError:
            # Download if not available
            import subprocess

            subprocess.run(
                ["python", "-m", "spacy", "download", "en_core_web_sm"],
                check=True,
            )
            _spacy_nlp = spacy.load("en_core_web_sm")
            logger.info("spacy_nlp_downloaded_and_loaded", model="en_core_web_sm")
    return _spacy_nlp


async def extract_entities_fast(chunks: list[Any]) -> list[dict[str, Any]]:
    """Extract entities using SpaCy NER (fast, no LLM).

    Args:
        chunks: List of Pydantic Chunk objects

    Returns:
        List of entity dicts [{"text": str, "type": str, "chunk_id": str}, ...]

    Performance: <500ms for 10 chunks
    """
    start_time = time.perf_counter()

    nlp = get_spacy_nlp()
    entities = []

    for chunk in chunks:
        # Get chunk text
        chunk_text = chunk.content if hasattr(chunk, "content") else chunk.text

        # Run SpaCy NER
        doc = nlp(chunk_text[:5000])  # Limit to first 5000 chars for speed

        # Extract entities
        for ent in doc.ents:
            entities.append(
                {
                    "text": ent.text,
                    "type": ent.label_,
                    "chunk_id": getattr(chunk, "id", None),
                }
            )

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "fast_entity_extraction_complete",
        chunks_processed=len(chunks),
        entities_extracted=len(entities),
        duration_ms=round(duration_ms, 2),
    )

    return entities


async def run_fast_upload(
    file_path: str | Path,
    namespace: str = "default",
    domain: str = "general",
    original_filename: str | None = None,
) -> str:
    """Run Phase 1: Fast Upload Pipeline (2-5s response).

    Workflow:
        1. Docling parsing
        2. Adaptive chunking
        3. BGE-M3 embeddings
        4. Qdrant upload (vector only, skip Neo4j)
        5. SpaCy NER entities
        6. Set status to "processing_background"

    Args:
        file_path: Path to uploaded file
        namespace: Document namespace (for multi-tenant isolation)
        domain: Document domain (for domain-specific extraction)
        original_filename: Original filename (optional)

    Returns:
        document_id: Unique document ID

    Raises:
        IngestionError: If fast upload fails

    Performance Target: <5s
    """
    start_time = time.perf_counter()

    # Generate document ID
    file_path = Path(file_path)
    if not file_path.exists():
        raise IngestionError(
            document_id="unknown",
            reason=f"File not found: {file_path}",
        )

    document_id = f"doc_{hashlib.sha256(str(file_path).encode()).hexdigest()[:16]}"
    filename = original_filename or file_path.name

    logger.info(
        "fast_upload_start",
        document_id=document_id,
        filename=filename,
        namespace=namespace,
        domain=domain,
    )

    # Initialize background job queue
    job_queue = get_background_job_queue()
    await job_queue.initialize()

    # Set initial status
    await job_queue.set_status(
        document_id=document_id,
        status="processing_fast",
        progress_pct=10.0,
        current_phase="parsing",
        namespace=namespace,
        domain=domain,
    )

    try:
        # Step 1: Docling parsing (1-2s)
        parsing_start = time.perf_counter()
        logger.info("fast_upload_parsing_start", document_id=document_id)

        docling_client = DoclingClient()
        parsed_doc = await docling_client.parse_document(str(file_path))

        parsing_duration_ms = (time.perf_counter() - parsing_start) * 1000
        logger.info(
            "fast_upload_parsing_complete",
            document_id=document_id,
            duration_ms=round(parsing_duration_ms, 2),
        )

        await job_queue.set_status(
            document_id=document_id,
            status="processing_fast",
            progress_pct=30.0,
            current_phase="chunking",
            namespace=namespace,
            domain=domain,
        )

        # Step 2: Adaptive chunking (0.5s)
        chunking_start = time.perf_counter()
        logger.info("fast_upload_chunking_start", document_id=document_id)

        chunks = await adaptive_section_chunking(
            parsed_doc=parsed_doc,
            document_id=document_id,
        )

        chunking_duration_ms = (time.perf_counter() - chunking_start) * 1000
        logger.info(
            "fast_upload_chunking_complete",
            document_id=document_id,
            chunks_count=len(chunks),
            duration_ms=round(chunking_duration_ms, 2),
        )

        await job_queue.set_status(
            document_id=document_id,
            status="processing_fast",
            progress_pct=50.0,
            current_phase="embedding",
            namespace=namespace,
            domain=domain,
        )

        # Step 3: Generate embeddings (1-2s)
        embedding_start = time.perf_counter()
        logger.info("fast_upload_embedding_start", document_id=document_id, chunks=len(chunks))

        embedding_service = get_embedding_service()
        texts = [chunk.content for chunk in chunks]
        # Sprint 92 Fix: Handle both list (Ollama/ST) and dict (FlagEmbedding) returns
        batch_result = await embedding_service.embed_batch(texts)
        embeddings = [emb["dense"] if isinstance(emb, dict) else emb for emb in batch_result]

        embedding_duration_ms = (time.perf_counter() - embedding_start) * 1000
        logger.info(
            "fast_upload_embedding_complete",
            document_id=document_id,
            embeddings_generated=len(embeddings),
            duration_ms=round(embedding_duration_ms, 2),
        )

        await job_queue.set_status(
            document_id=document_id,
            status="processing_fast",
            progress_pct=70.0,
            current_phase="indexing",
            namespace=namespace,
            domain=domain,
        )

        # Step 4: Upload to Qdrant (0.5s)
        qdrant_start = time.perf_counter()
        logger.info("fast_upload_qdrant_start", document_id=document_id)

        qdrant = QdrantClientWrapper()
        collection_name = settings.qdrant_collection

        # Ensure collection exists
        await qdrant.create_collection(
            collection_name=collection_name,
            vector_size=1024,  # BGE-M3 dimension
        )

        # Create Qdrant points
        points = []
        chunk_ids = []

        for chunk, embedding, text in zip(chunks, embeddings, texts, strict=False):
            # Generate deterministic chunk ID
            chunk_name = f"{document_id}_chunk_{hashlib.sha256(text.encode()).hexdigest()[:8]}"
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_name))
            chunk_ids.append(chunk_id)

            # Minimal payload (graph data will be added in Phase 2)
            payload = {
                "content": text,
                "contextualized_content": text,  # Will be enhanced in Phase 2
                "document_id": document_id,
                "document_path": str(file_path),
                "page_no": chunk.meta.page_no if hasattr(chunk, "meta") else None,
                "headings": chunk.meta.headings if hasattr(chunk, "meta") else [],
                "chunk_id": chunk_id,
                "contains_images": False,  # Will be enriched in Phase 2
                "image_annotations": [],
                "ingestion_timestamp": time.time(),
                "namespace_id": namespace,
                "fast_upload": True,  # Mark as fast upload (Phase 1)
                "refinement_pending": True,  # Phase 2 pending
            }

            point = PointStruct(
                id=chunk_id,
                vector=embedding,
                payload=payload,
            )
            points.append(point)

        # Upload batch
        await qdrant.upsert_points(
            collection_name=collection_name,
            points=points,
            batch_size=100,
        )

        qdrant_duration_ms = (time.perf_counter() - qdrant_start) * 1000
        logger.info(
            "fast_upload_qdrant_complete",
            document_id=document_id,
            points_uploaded=len(points),
            duration_ms=round(qdrant_duration_ms, 2),
        )

        await job_queue.set_status(
            document_id=document_id,
            status="processing_fast",
            progress_pct=90.0,
            current_phase="entity_extraction",
            namespace=namespace,
            domain=domain,
        )

        # Step 5: SpaCy NER extraction (0.5s)
        entities = await extract_entities_fast(chunks)

        # Store preliminary entities in Redis (for immediate search)
        # Note: Full LLM extraction will be done in Phase 2
        # This is just a placeholder for now - implement Redis cache if needed

        # Mark Phase 1 complete
        await job_queue.set_status(
            document_id=document_id,
            status="processing_background",
            progress_pct=100.0,
            current_phase="fast_upload_complete",
            namespace=namespace,
            domain=domain,
        )

        total_duration = (time.perf_counter() - start_time) * 1000

        logger.info(
            "fast_upload_complete",
            document_id=document_id,
            total_duration_ms=round(total_duration, 2),
            chunks_uploaded=len(points),
            entities_extracted=len(entities),
            timing_breakdown={
                "parsing_ms": round(parsing_duration_ms, 2),
                "chunking_ms": round(chunking_duration_ms, 2),
                "embedding_ms": round(embedding_duration_ms, 2),
                "qdrant_ms": round(qdrant_duration_ms, 2),
            },
        )

        # Check if target met (<5s)
        if total_duration > 5000:
            logger.warning(
                "fast_upload_target_missed",
                document_id=document_id,
                target_ms=5000,
                actual_ms=round(total_duration, 2),
            )

        return document_id

    except Exception as e:
        # Mark as failed
        await job_queue.set_status(
            document_id=document_id,
            status="failed",
            progress_pct=0.0,
            current_phase="fast_upload_failed",
            error_message=str(e),
            namespace=namespace,
            domain=domain,
        )

        logger.error(
            "fast_upload_failed",
            document_id=document_id,
            error=str(e),
        )
        raise IngestionError(document_id=document_id, reason=f"Fast upload failed: {e}") from e
