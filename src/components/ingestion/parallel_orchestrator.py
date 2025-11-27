"""Parallel Ingestion Orchestrator with Asyncio Semaphore (Sprint 33 Feature 33.8).

This module implements parallel file processing for document ingestion,
using asyncio Semaphore for concurrency control and job tracking integration.

Architecture:
  - Asyncio Semaphore: Limit concurrent file processing (default 3)
  - Chunk-level parallelism: Parallel embedding generation (default 10)
  - Job tracker integration: Persistent logging of all progress
  - SSE streaming: Real-time progress updates to frontend

Parallelism Levels:
  1. File-level: Process 3 files concurrently (PARALLEL_FILES=3)
  2. Chunk-level: Generate 10 embeddings concurrently (PARALLEL_CHUNKS=10)

Error Handling:
  - Isolated failures: One file error doesn't stop others
  - Job tracking: All errors logged to SQLite database
  - Graceful degradation: Continue with remaining files

Memory Management:
  - Bounded concurrency via Semaphore (prevent OOM)
  - Docling container lifecycle per file (free VRAM)
  - Chunk batching for embedding service

Use Cases:
  - Batch ingestion: Process directory with hundreds of files
  - Admin UI: Real-time progress bar for long-running jobs
  - Debugging: Replay failed jobs from SQLite logs

Example:
    >>> orchestrator = ParallelIngestionOrchestrator(max_workers=3)
    >>> async for progress in orchestrator.process_files_parallel(
    ...     files=[Path("doc1.pdf"), Path("doc2.pdf")],
    ...     job_tracker=tracker
    ... ):
    ...     print(f"Progress: {progress['progress_percent']}%")

Notes:
  - Designed for 6GB VRAM GPU (RTX 3060)
  - Sequential Docling execution (container start/stop per file)
  - Parallel embeddings for CPU utilization
  - Compatible with LangGraph pipeline (langgraph_pipeline.py)
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import structlog

from src.components.ingestion.job_tracker import IngestionJobTracker

logger = structlog.get_logger(__name__)

# Parallelism constants
PARALLEL_FILES = 3  # Number of files processed concurrently
PARALLEL_CHUNKS = 10  # Number of chunk embeddings generated concurrently


class ParallelIngestionOrchestrator:
    """Parallel file processing orchestrator with asyncio Semaphore.

    Implements bounded concurrency for document ingestion with job tracking
    and SSE progress streaming.

    Attributes:
        max_workers: Maximum concurrent file processing (default 3)
        max_chunk_workers: Maximum concurrent chunk embeddings (default 10)
        _file_semaphore: Asyncio semaphore for file-level concurrency
        _chunk_semaphore: Asyncio semaphore for chunk-level concurrency

    Methods:
        process_files_parallel: Process multiple files with parallelism
        _process_single_file: Process one file (called by semaphore)

    Example:
        >>> orchestrator = ParallelIngestionOrchestrator(max_workers=3)
        >>> files = [Path("doc1.pdf"), Path("doc2.pdf"), Path("doc3.pdf")]
        >>> async for progress in orchestrator.process_files_parallel(files):
        ...     print(progress["message"])
    """

    def __init__(self, max_workers: int = PARALLEL_FILES, max_chunk_workers: int = PARALLEL_CHUNKS):
        """Initialize orchestrator with concurrency limits.

        Args:
            max_workers: Maximum concurrent files (default 3)
            max_chunk_workers: Maximum concurrent chunk embeddings (default 10)

        Example:
            >>> orchestrator = ParallelIngestionOrchestrator(max_workers=5)
        """
        self.max_workers = max_workers
        self.max_chunk_workers = max_chunk_workers
        self._file_semaphore = asyncio.Semaphore(max_workers)
        self._chunk_semaphore = asyncio.Semaphore(max_chunk_workers)

        logger.info(
            "parallel_orchestrator_initialized",
            max_workers=max_workers,
            max_chunk_workers=max_chunk_workers,
        )

    async def process_files_parallel(
        self,
        files: list[Path],
        job_tracker: IngestionJobTracker | None = None,
        job_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Process files in parallel with bounded concurrency.

        Workflow:
        1. Create asyncio tasks for all files (with semaphore)
        2. Gather tasks and yield progress updates
        3. Handle errors per file (isolated failures)
        4. Update job tracker with results

        Args:
            files: List of file paths to process
            job_tracker: Optional job tracker for persistent logging
            job_id: Optional job ID for tracking

        Yields:
            Progress updates as dicts:
            {
                "status": "in_progress" | "completed" | "error",
                "file_path": str,
                "file_name": str,
                "progress_percent": float,
                "completed_files": int,
                "total_files": int,
                "chunks_created": int | None,
                "entities_extracted": int | None,
                "vlm_images_processed": int | None,
                "processing_time_ms": int | None,
                "error": str | None
            }

        Example:
            >>> files = [Path("doc1.pdf"), Path("doc2.pdf")]
            >>> tracker = get_job_tracker()
            >>> job_id = await tracker.create_job("/data/docs", True, 2)
            >>> async for progress in orchestrator.process_files_parallel(files, tracker, job_id):
            ...     print(f"{progress['file_name']}: {progress['progress_percent']}%")
        """
        if not files:
            logger.warning("process_files_parallel_no_files")
            return

        total_files = len(files)
        completed_files = 0
        failed_files = 0

        logger.info(
            "parallel_processing_start",
            total_files=total_files,
            max_workers=self.max_workers,
            job_id=job_id,
        )

        # Create tasks for all files (bounded by semaphore)
        tasks = [
            asyncio.create_task(
                self._process_single_file(
                    file_path=file_path,
                    file_index=idx,
                    total_files=total_files,
                    job_tracker=job_tracker,
                    job_id=job_id,
                )
            )
            for idx, file_path in enumerate(files)
        ]

        # Process tasks as they complete
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                completed_files += 1

                # Calculate progress
                progress_percent = (completed_files / total_files) * 100

                # Yield progress update
                yield {
                    "status": "in_progress" if result["success"] else "error",
                    "file_path": result["file_path"],
                    "file_name": result["file_name"],
                    "progress_percent": progress_percent,
                    "completed_files": completed_files,
                    "total_files": total_files,
                    "chunks_created": result.get("chunks_created"),
                    "entities_extracted": result.get("entities_extracted"),
                    "vlm_images_processed": result.get("vlm_images_processed"),
                    "processing_time_ms": result.get("processing_time_ms"),
                    "error": result.get("error"),
                }

                if not result["success"]:
                    failed_files += 1

            except Exception as e:
                logger.error("parallel_processing_task_failed", error=str(e), exc_info=True)
                failed_files += 1
                completed_files += 1

                # Yield error update
                yield {
                    "status": "error",
                    "file_path": "unknown",
                    "file_name": "unknown",
                    "progress_percent": (completed_files / total_files) * 100,
                    "completed_files": completed_files,
                    "total_files": total_files,
                    "error": str(e),
                }

        # Final summary
        logger.info(
            "parallel_processing_complete",
            total_files=total_files,
            completed_files=completed_files,
            failed_files=failed_files,
            job_id=job_id,
        )

        # Update job tracker with final status
        if job_tracker and job_id:
            final_status = "completed" if failed_files == 0 else "completed_with_errors"
            await job_tracker.update_job_status(
                job_id=job_id,
                status=final_status,  # type: ignore
                processed_files=completed_files,
                total_errors=failed_files,
            )

        # Yield completion message
        yield {
            "status": "completed",
            "file_path": "",
            "file_name": "",
            "progress_percent": 100.0,
            "completed_files": completed_files,
            "total_files": total_files,
            "failed_files": failed_files,
        }

    async def _process_single_file(
        self,
        file_path: Path,
        file_index: int,
        total_files: int,
        job_tracker: IngestionJobTracker | None = None,
        job_id: str | None = None,
    ) -> dict[str, Any]:
        """Process single file with semaphore concurrency control.

        This method acquires semaphore, processes file via LangGraph pipeline,
        releases semaphore, and returns results.

        Args:
            file_path: Path to file
            file_index: File index (0-based)
            total_files: Total number of files
            job_tracker: Optional job tracker
            job_id: Optional job ID

        Returns:
            Processing result dict:
            {
                "success": bool,
                "file_path": str,
                "file_name": str,
                "chunks_created": int | None,
                "entities_extracted": int | None,
                "relations_extracted": int | None,
                "vlm_images_processed": int | None,
                "processing_time_ms": int | None,
                "error": str | None
            }

        Example:
            >>> result = await orchestrator._process_single_file(
            ...     file_path=Path("doc.pdf"),
            ...     file_index=0,
            ...     total_files=1
            ... )
            >>> result["success"]
            True
        """
        start_time = time.time()

        # Acquire semaphore (blocks if max_workers reached)
        async with self._file_semaphore:
            logger.info(
                "file_processing_start",
                file_path=str(file_path),
                file_index=file_index,
                total_files=total_files,
                job_id=job_id,
            )

            try:
                # Add file to job tracker
                file_id = None
                if job_tracker and job_id:
                    file_id = await job_tracker.add_file(
                        job_id=job_id,
                        file_path=str(file_path),
                        file_name=file_path.name,
                        file_type=file_path.suffix,
                        file_size_bytes=file_path.stat().st_size,
                        parser_used="docling",  # Default, will be updated
                    )

                    # Log processing start event
                    await job_tracker.add_event(
                        job_id=job_id,
                        level="INFO",
                        phase="parsing",
                        file_name=file_path.name,
                        page_number=None,
                        chunk_id=None,
                        message=f"Processing started: {file_path.name}",
                    )

                # Process file via LangGraph pipeline
                # Import here to avoid circular dependency
                from src.components.ingestion.langgraph_pipeline import process_single_document

                result = await process_single_document(
                    document_path=str(file_path),
                    document_id=f"{file_path.stem}_{file_index}",
                )

                processing_time_ms = int((time.time() - start_time) * 1000)

                # Extract statistics from result
                success = result.get("success", False)
                state = result.get("state", {})
                chunks_created = len(state.get("chunks", []))
                entities_extracted = len(state.get("entities", []))
                relations_extracted = len(state.get("relations", []))
                vlm_images_processed = len(state.get("vlm_metadata", []))

                # Update file in job tracker
                if job_tracker and job_id and file_id is not None:
                    await job_tracker.update_file(
                        file_id=file_id,
                        status="completed" if success else "failed",
                        chunks_created=chunks_created,
                        entities_extracted=entities_extracted,
                        relations_extracted=relations_extracted,
                        vlm_images_processed=vlm_images_processed,
                        processing_time_ms=processing_time_ms,
                        error_message=result.get("error") if not success else None,
                    )

                    # Log completion event
                    await job_tracker.add_event(
                        job_id=job_id,
                        level="INFO" if success else "ERROR",
                        phase="graph",  # Last phase
                        file_name=file_path.name,
                        page_number=None,
                        chunk_id=None,
                        message=f"Processing {'completed' if success else 'failed'}: {file_path.name}",
                        details={
                            "chunks_created": chunks_created,
                            "entities_extracted": entities_extracted,
                            "processing_time_ms": processing_time_ms,
                        },
                    )

                logger.info(
                    "file_processing_complete",
                    file_path=str(file_path),
                    success=success,
                    chunks_created=chunks_created,
                    processing_time_ms=processing_time_ms,
                )

                return {
                    "success": success,
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "chunks_created": chunks_created,
                    "entities_extracted": entities_extracted,
                    "relations_extracted": relations_extracted,
                    "vlm_images_processed": vlm_images_processed,
                    "processing_time_ms": processing_time_ms,
                    "error": result.get("error") if not success else None,
                }

            except Exception as e:
                processing_time_ms = int((time.time() - start_time) * 1000)
                error_msg = str(e)

                logger.error(
                    "file_processing_failed",
                    file_path=str(file_path),
                    error=error_msg,
                    processing_time_ms=processing_time_ms,
                    exc_info=True,
                )

                # Update file in job tracker
                if job_tracker and job_id and file_id is not None:
                    await job_tracker.update_file(
                        file_id=file_id,
                        status="failed",
                        processing_time_ms=processing_time_ms,
                        error_message=error_msg,
                    )

                    # Log error event
                    await job_tracker.add_event(
                        job_id=job_id,
                        level="ERROR",
                        phase="parsing",
                        file_name=file_path.name,
                        page_number=None,
                        chunk_id=None,
                        message=f"Processing failed: {error_msg}",
                    )

                return {
                    "success": False,
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "chunks_created": None,
                    "entities_extracted": None,
                    "relations_extracted": None,
                    "vlm_images_processed": None,
                    "processing_time_ms": processing_time_ms,
                    "error": error_msg,
                }


# Global singleton instance
_orchestrator: ParallelIngestionOrchestrator | None = None


def get_parallel_orchestrator() -> ParallelIngestionOrchestrator:
    """Get singleton ParallelIngestionOrchestrator instance.

    Returns:
        Global ParallelIngestionOrchestrator instance

    Example:
        >>> orchestrator = get_parallel_orchestrator()
        >>> files = [Path("doc1.pdf"), Path("doc2.pdf")]
        >>> async for progress in orchestrator.process_files_parallel(files):
        ...     print(progress["message"])
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ParallelIngestionOrchestrator()
    return _orchestrator
