"""Streaming Pipeline Orchestrator with AsyncIO Queues (Sprint 37 Feature 37.1).

Architecture:
  - Chunks flow immediately to next stage (no batch waiting)
  - AsyncIO Queues for inter-stage communication
  - Backpressure via queue maxsize
  - Error isolation per chunk
  - Parallel workers per stage

Pipeline Flow:
  Docling Parse → VLM (images) → Chunking → Embedding → Graph Extraction
                                    ↓            ↓              ↓
                                chunk_queue  embed_queue  extraction_queue

Each stage runs as an async task, passing items via queues.
Backpressure is handled via queue maxsize.

Example:
    >>> config = PipelineConfig(
    ...     chunk_queue_max_size=10,
    ...     embedding_workers=2,
    ... )
    >>> orchestrator = StreamingPipelineOrchestrator(config)
    >>> result = await orchestrator.process_document(
    ...     document_path=Path("doc.pdf"),
    ...     document_id="doc_001",
    ... )
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from src.components.ingestion.docling_client import DoclingContainerClient
from src.components.ingestion.image_processor import ImageProcessor
from src.components.ingestion.pipeline_queues import (
    ChunkQueueItem,
    EmbeddedChunkItem,
    TypedQueue,
)
from src.components.shared.embedding_service import get_embedding_service
from src.core.config import settings
from src.core.exceptions import IngestionError

logger = structlog.get_logger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for streaming pipeline.

    Attributes:
        chunk_queue_max_size: Max items in chunk queue (backpressure control)
        embedding_queue_max_size: Max items in embedding queue
        embedding_workers: Number of parallel embedding workers
        extraction_workers: Number of parallel extraction workers
        vlm_workers: Number of parallel VLM workers
        embedding_timeout: Timeout for embedding operations (seconds)
        extraction_timeout: Timeout for extraction operations (seconds)
        vlm_timeout: Timeout for VLM operations (seconds)
    """

    chunk_queue_max_size: int = 10
    embedding_queue_max_size: int = 10
    embedding_workers: int = 2
    extraction_workers: int = 4
    vlm_workers: int = 1
    embedding_timeout: int = 60
    extraction_timeout: int = 120
    vlm_timeout: int = 180


class StreamingPipelineOrchestrator:
    """Orchestrates streaming document ingestion with parallel stages.

    Pipeline Flow:
    Docling Parse → VLM (images) → Chunking → Embedding → Graph Extraction
                                      ↓            ↓              ↓
                                  chunk_queue  embed_queue  extraction_queue

    Each stage runs as an async task, passing items via queues.
    Backpressure is handled via queue maxsize.

    Error Handling:
    - Errors in one chunk don't stop pipeline
    - Errors accumulated in results["errors"]
    - Failed chunks logged but pipeline continues

    Example:
        >>> orchestrator = StreamingPipelineOrchestrator()
        >>> result = await orchestrator.process_document(
        ...     document_path=Path("doc.pdf"),
        ...     document_id="doc_001",
        ... )
        >>> print(f"Chunks: {len(result['chunks'])}")
        >>> print(f"Errors: {len(result['errors'])}")
    """

    def __init__(self, config: PipelineConfig | None = None):
        """Initialize streaming pipeline orchestrator.

        Args:
            config: Pipeline configuration (uses defaults if None)
        """
        self.config = config or PipelineConfig()
        # Queues will be created per-document
        self._chunk_queue: TypedQueue[ChunkQueueItem] | None = None
        self._embedding_queue: TypedQueue[EmbeddedChunkItem] | None = None

    async def process_document(
        self,
        document_path: Path,
        document_id: str,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> dict[str, Any]:
        """Process a single document through the streaming pipeline.

        Args:
            document_path: Path to document file
            document_id: Unique document identifier
            progress_callback: Optional callback for progress updates

        Returns:
            Processing result with chunks, entities, relations, metrics

        Raises:
            IngestionError: If critical pipeline stage fails
            FileNotFoundError: If document_path does not exist

        Example:
            >>> result = await orchestrator.process_document(
            ...     document_path=Path("doc.pdf"),
            ...     document_id="doc_001",
            ...     progress_callback=lambda p: print(f"Progress: {p['stage']}")
            ... )
        """
        pipeline_start = time.perf_counter()

        logger.info(
            "streaming_pipeline_start",
            document_id=document_id,
            document_path=str(document_path),
            config=self.config,
        )

        # Validate document exists
        if not document_path.exists():
            raise FileNotFoundError(f"Document not found: {document_path}")

        # Create queues for this document
        self._chunk_queue = TypedQueue[ChunkQueueItem](maxsize=self.config.chunk_queue_max_size)
        self._embedding_queue = TypedQueue[EmbeddedChunkItem](
            maxsize=self.config.embedding_queue_max_size
        )

        # Result collectors
        results: dict[str, Any] = {
            "chunks": [],
            "embeddings": [],
            "entities": [],
            "relations": [],
            "errors": [],
            "metrics": {},
        }

        # Stage 1: Parsing + VLM enrichment (sequential)
        try:
            parsed_doc, vlm_metadata = await self._parsing_stage(
                document_path, document_id, progress_callback
            )
            results["vlm_metadata"] = vlm_metadata
        except Exception as e:
            logger.error(
                "parsing_stage_failed",
                document_id=document_id,
                error=str(e),
                exc_info=True,
            )
            results["errors"].append(
                {"stage": "parsing", "error": str(e), "timestamp": time.time()}
            )
            raise IngestionError(document_id=document_id, reason=f"Parsing failed: {e}") from e

        # Stage 2-5: Parallel streaming pipeline
        # Start all stage tasks concurrently
        tasks = [
            asyncio.create_task(
                self._chunking_stage(parsed_doc, document_id, results, progress_callback),
                name="chunking",
            ),
            asyncio.create_task(
                self._embedding_stage(document_id, results, progress_callback),
                name="embedding",
            ),
            asyncio.create_task(
                self._extraction_stage(document_id, results, progress_callback),
                name="extraction",
            ),
        ]

        # Wait for all stages to complete
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            logger.error(
                "pipeline_stage_failed",
                document_id=document_id,
                error=str(e),
                exc_info=True,
            )
            # Cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            results["errors"].append(
                {"stage": "pipeline", "error": str(e), "timestamp": time.time()}
            )

        pipeline_end = time.perf_counter()
        total_duration = pipeline_end - pipeline_start

        # Calculate metrics
        results["metrics"] = {
            "total_duration_seconds": round(total_duration, 2),
            "chunks_created": len(results["chunks"]),
            "embeddings_created": len(results["embeddings"]),
            "entities_extracted": len(results["entities"]),
            "relations_extracted": len(results["relations"]),
            "errors_count": len(results["errors"]),
        }

        logger.info(
            "streaming_pipeline_complete",
            document_id=document_id,
            duration_seconds=round(total_duration, 2),
            metrics=results["metrics"],
        )

        return results

    async def _parsing_stage(
        self,
        document_path: Path,
        document_id: str,
        progress_callback: Callable[[dict], None] | None,
    ) -> tuple[Any, list[dict]]:
        """Stage 1: Parse document with Docling + VLM enrichment.

        Args:
            document_path: Path to document file
            document_id: Unique document identifier
            progress_callback: Optional progress callback

        Returns:
            Tuple of (parsed_document, vlm_metadata)

        Raises:
            IngestionError: If parsing fails
        """
        stage_start = time.perf_counter()
        logger.info("parsing_stage_start", document_id=document_id)

        if progress_callback:
            progress_callback({"stage": "parsing", "progress": 0.0})

        # Initialize Docling client
        docling = DoclingContainerClient(
            base_url=settings.docling_base_url,
            timeout_seconds=settings.docling_timeout_seconds,
            max_retries=settings.docling_max_retries,
        )

        try:
            # Start container
            await docling.start_container()

            # Parse document
            parsed = await docling.parse_document(document_path)
            parsed_doc = parsed.document

            if progress_callback:
                progress_callback({"stage": "parsing", "progress": 0.5})

            # VLM enrichment (if images present)
            vlm_metadata = []
            if hasattr(parsed_doc, "pictures") and len(parsed_doc.pictures) > 0:
                logger.info(
                    "vlm_enrichment_start",
                    document_id=document_id,
                    pictures_count=len(parsed_doc.pictures),
                )

                processor = ImageProcessor()
                try:
                    # Process images in parallel
                    semaphore = asyncio.Semaphore(self.config.vlm_workers)

                    async def process_image(idx: int, picture_item) -> dict | None:
                        async with semaphore:
                            try:
                                pil_image = picture_item.get_image()
                                description = await processor.process_image(
                                    image=pil_image, picture_index=idx
                                )
                                if description:
                                    # Insert into DoclingDocument
                                    picture_item.text = description
                                    return {
                                        "picture_index": idx,
                                        "description": description,
                                        "timestamp": time.time(),
                                    }
                            except Exception as e:
                                logger.warning(
                                    "vlm_image_processing_error",
                                    picture_index=idx,
                                    error=str(e),
                                )
                            return None

                    tasks = [process_image(idx, pic) for idx, pic in enumerate(parsed_doc.pictures)]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    vlm_metadata = [r for r in results if r is not None]

                finally:
                    processor.cleanup()

            if progress_callback:
                progress_callback({"stage": "parsing", "progress": 1.0})

        finally:
            await docling.stop_container()

        stage_end = time.perf_counter()
        logger.info(
            "parsing_stage_complete",
            document_id=document_id,
            duration_seconds=round(stage_end - stage_start, 2),
            vlm_images_processed=len(vlm_metadata),
        )

        return parsed_doc, vlm_metadata

    async def _chunking_stage(
        self,
        parsed_doc: Any,
        document_id: str,
        results: dict,
        progress_callback: Callable[[dict], None] | None,
    ) -> None:
        """Stage 2: Chunk document and put chunks on queue.

        Producer stage - creates chunks and sends to chunk_queue.

        Args:
            parsed_doc: Parsed DoclingDocument
            document_id: Unique document identifier
            results: Results dictionary to populate
            progress_callback: Optional progress callback
        """
        stage_start = time.perf_counter()
        logger.info("chunking_stage_start", document_id=document_id)

        if progress_callback:
            progress_callback({"stage": "chunking", "progress": 0.0})

        try:
            # Import section extraction
            from src.components.ingestion.langgraph_nodes import (
                SectionMetadata,
                adaptive_section_chunking,
            )
            from src.components.ingestion.section_extraction import extract_section_hierarchy

            # Extract sections
            sections = extract_section_hierarchy(parsed_doc, SectionMetadata)

            # Create adaptive chunks
            adaptive_chunks = adaptive_section_chunking(
                sections=sections, min_chunk=800, max_chunk=1800, large_section_threshold=1200
            )

            logger.info(
                "chunking_chunks_created",
                document_id=document_id,
                sections_count=len(sections),
                chunks_count=len(adaptive_chunks),
            )

            # Put chunks on queue (streaming!)
            for idx, chunk in enumerate(adaptive_chunks):
                chunk_item = ChunkQueueItem(
                    chunk_id=f"{document_id}_chunk_{idx}",
                    chunk_index=idx,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    document_id=document_id,
                    metadata={
                        "section_headings": chunk.section_headings,
                        "section_pages": chunk.section_pages,
                        "section_bboxes": chunk.section_bboxes,
                        "primary_section": chunk.primary_section,
                    },
                )

                # Put on queue (blocks if queue is full - backpressure!)
                await self._chunk_queue.put(chunk_item)

                # Store in results for final output
                results["chunks"].append(chunk)

                logger.debug(
                    "chunk_queued",
                    chunk_id=chunk_item.chunk_id,
                    queue_size=self._chunk_queue.qsize(),
                )

            # Signal completion
            await self._chunk_queue.mark_done()

            if progress_callback:
                progress_callback({"stage": "chunking", "progress": 1.0})

        except Exception as e:
            logger.error(
                "chunking_stage_error",
                document_id=document_id,
                error=str(e),
                exc_info=True,
            )
            results["errors"].append(
                {"stage": "chunking", "error": str(e), "timestamp": time.time()}
            )
            # Signal completion even on error
            await self._chunk_queue.mark_done()
            raise

        stage_end = time.perf_counter()
        logger.info(
            "chunking_stage_complete",
            document_id=document_id,
            duration_seconds=round(stage_end - stage_start, 2),
            chunks_created=len(results["chunks"]),
        )

    async def _embedding_stage(
        self,
        document_id: str,
        results: dict,
        progress_callback: Callable[[dict], None] | None,
    ) -> None:
        """Stage 3: Generate embeddings for chunks from queue.

        Consumer-Producer stage - consumes from chunk_queue, produces to embedding_queue.

        Args:
            document_id: Unique document identifier
            results: Results dictionary to populate
            progress_callback: Optional progress callback
        """
        stage_start = time.perf_counter()
        logger.info(
            "embedding_stage_start",
            document_id=document_id,
            workers=self.config.embedding_workers,
        )

        if progress_callback:
            progress_callback({"stage": "embedding", "progress": 0.0})

        # Get embedding service
        embedding_service = get_embedding_service()

        # Worker function
        async def embedding_worker(worker_id: int) -> None:
            """Embedding worker - processes chunks from queue."""
            logger.debug("embedding_worker_start", worker_id=worker_id)

            while True:
                # Get chunk from queue
                chunk_item = await self._chunk_queue.get()
                if chunk_item is None:
                    # Queue is done
                    logger.debug("embedding_worker_done", worker_id=worker_id)
                    break

                try:
                    # Generate embedding
                    # Sprint 92 Fix: Handle both list (Ollama/ST) and dict (FlagEmbedding) returns
                    embedding_result = await asyncio.wait_for(
                        embedding_service.embed_single(chunk_item.text),
                        timeout=self.config.embedding_timeout,
                    )
                    embedding = (
                        embedding_result["dense"]
                        if isinstance(embedding_result, dict)
                        else embedding_result
                    )

                    # Create embedded chunk item
                    embedded_item = EmbeddedChunkItem(
                        chunk_id=chunk_item.chunk_id,
                        chunk_index=chunk_item.chunk_index,
                        text=chunk_item.text,
                        embedding=embedding,
                        token_count=chunk_item.token_count,
                        document_id=chunk_item.document_id,
                        metadata=chunk_item.metadata,
                    )

                    # Put on embedding queue
                    await self._embedding_queue.put(embedded_item)

                    # Store in results
                    results["embeddings"].append(embedding)

                    logger.debug(
                        "chunk_embedded",
                        worker_id=worker_id,
                        chunk_id=chunk_item.chunk_id,
                        embedding_dim=len(embedding),
                    )

                except TimeoutError:
                    logger.error(
                        "embedding_timeout",
                        worker_id=worker_id,
                        chunk_id=chunk_item.chunk_id,
                        timeout=self.config.embedding_timeout,
                    )
                    results["errors"].append(
                        {
                            "stage": "embedding",
                            "chunk_id": chunk_item.chunk_id,
                            "error": "Timeout",
                            "timestamp": time.time(),
                        }
                    )
                except Exception as e:
                    logger.error(
                        "embedding_error",
                        worker_id=worker_id,
                        chunk_id=chunk_item.chunk_id,
                        error=str(e),
                        exc_info=True,
                    )
                    results["errors"].append(
                        {
                            "stage": "embedding",
                            "chunk_id": chunk_item.chunk_id,
                            "error": str(e),
                            "timestamp": time.time(),
                        }
                    )

        # Start workers
        workers = [
            asyncio.create_task(embedding_worker(i), name=f"embedding_worker_{i}")
            for i in range(self.config.embedding_workers)
        ]

        # Wait for all workers to complete
        await asyncio.gather(*workers)

        # Signal completion
        await self._embedding_queue.mark_done()

        if progress_callback:
            progress_callback({"stage": "embedding", "progress": 1.0})

        stage_end = time.perf_counter()
        logger.info(
            "embedding_stage_complete",
            document_id=document_id,
            duration_seconds=round(stage_end - stage_start, 2),
            embeddings_created=len(results["embeddings"]),
        )

    async def _extraction_stage(
        self,
        document_id: str,
        results: dict,
        progress_callback: Callable[[dict], None] | None,
    ) -> None:
        """Stage 4: Extract entities/relations from embedded chunks.

        Consumer stage - consumes from embedding_queue.

        Args:
            document_id: Unique document identifier
            results: Results dictionary to populate
            progress_callback: Optional progress callback
        """
        stage_start = time.perf_counter()
        logger.info(
            "extraction_stage_start",
            document_id=document_id,
            workers=self.config.extraction_workers,
        )

        if progress_callback:
            progress_callback({"stage": "extraction", "progress": 0.0})

        # NOTE: Actual graph extraction implementation will be added in Feature 37.2
        # For now, this is a placeholder that consumes the queue

        # Worker function
        async def extraction_worker(worker_id: int) -> None:
            """Extraction worker - processes embedded chunks from queue."""
            logger.debug("extraction_worker_start", worker_id=worker_id)

            while True:
                # Get embedded chunk from queue
                embedded_item = await self._embedding_queue.get()
                if embedded_item is None:
                    # Queue is done
                    logger.debug("extraction_worker_done", worker_id=worker_id)
                    break

                try:
                    # Placeholder: actual extraction logic will be added in Feature 37.2
                    logger.debug(
                        "chunk_extraction_placeholder",
                        worker_id=worker_id,
                        chunk_id=embedded_item.chunk_id,
                    )

                    # Simulate extraction delay
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(
                        "extraction_error",
                        worker_id=worker_id,
                        chunk_id=embedded_item.chunk_id,
                        error=str(e),
                        exc_info=True,
                    )
                    results["errors"].append(
                        {
                            "stage": "extraction",
                            "chunk_id": embedded_item.chunk_id,
                            "error": str(e),
                            "timestamp": time.time(),
                        }
                    )

        # Start workers
        workers = [
            asyncio.create_task(extraction_worker(i), name=f"extraction_worker_{i}")
            for i in range(self.config.extraction_workers)
        ]

        # Wait for all workers to complete
        await asyncio.gather(*workers)

        if progress_callback:
            progress_callback({"stage": "extraction", "progress": 1.0})

        stage_end = time.perf_counter()
        logger.info(
            "extraction_stage_complete",
            document_id=document_id,
            duration_seconds=round(stage_end - stage_start, 2),
        )


__all__ = [
    "PipelineConfig",
    "StreamingPipelineOrchestrator",
]
