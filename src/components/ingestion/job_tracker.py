"""Ingestion Job Tracking with SQLite Persistence (Sprint 33 Feature 33.7).

This module implements a persistent job tracking system for document ingestion,
storing job metadata, events, and file-level progress in SQLite database.

Architecture:
  - SQLite database with 3 tables: ingestion_jobs, ingestion_events, ingestion_files
  - Thread-safe database operations with connection pooling
  - Retention policy for automatic cleanup of old jobs
  - Structured logging integration for debugging

Database Schema:
  ingestion_jobs:
    - Job-level metadata (status, config, file counts)
    - Supports running, completed, failed, cancelled states

  ingestion_events:
    - Event-level logging (INFO, DEBUG, WARN, ERROR)
    - Phase tracking (parsing, vlm, chunking, embedding, bm25, graph)
    - File/page/chunk-level granularity

  ingestion_files:
    - File-level progress (pages, chunks, entities, relations)
    - Parser type (docling, llamaindex)
    - VLM image counts and processing times

Use Cases:
  - Admin dashboard: Display job history and statistics
  - Debugging: Replay ingestion events for failed jobs
  - Analytics: Track parser performance and error patterns
  - Retention: Automatically cleanup jobs older than N days

Example:
    >>> tracker = IngestionJobTracker()
    >>> job_id = await tracker.create_job(
    ...     directory_path="/data/documents",
    ...     recursive=True,
    ...     total_files=10
    ... )
    >>> await tracker.add_event(job_id, "INFO", "parsing", "report.pdf", None, None, "Parsing started")
    >>> await tracker.update_job_status(job_id, "completed")

Notes:
  - Database path: data/jobs/ingestion_jobs.db
  - Retention default: 90 days
  - Thread-safe: Uses asyncio locks for concurrent access
  - Cleanup: Automatically run on startup and via scheduled task
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import structlog

logger = structlog.get_logger(__name__)

# Database path (relative to project root)
DB_PATH = Path("data/jobs/ingestion_jobs.db")

# Job status literals
JobStatus = Literal["running", "completed", "failed", "cancelled"]
EventLevel = Literal["INFO", "DEBUG", "WARN", "ERROR"]
Phase = Literal["parsing", "vlm", "chunking", "embedding", "bm25", "graph"]
ParserType = Literal["docling", "llamaindex", "unsupported"]
FileStatus = Literal["pending", "processing", "completed", "failed", "skipped"]


class IngestionJobTracker:
    """Thread-safe SQLite job tracker for ingestion pipeline.

    Implements persistent tracking of ingestion jobs with event logging,
    file-level progress, and automatic retention cleanup.

    Attributes:
        db_path: Path to SQLite database file
        retention_days: Number of days to retain completed jobs (default 90)
        _lock: Asyncio lock for thread-safe database access
        _initialized: Database initialization flag

    Methods:
        create_job: Create new ingestion job
        update_job_status: Update job status (running → completed/failed)
        add_event: Log ingestion event (INFO/DEBUG/WARN/ERROR)
        add_file: Add file to job tracking
        update_file: Update file progress (pages, chunks, entities)
        get_job: Retrieve job by ID
        get_jobs: List all jobs with filtering
        get_events: Get events for specific job
        get_errors: Get only ERROR-level events
        cleanup_old_jobs: Delete jobs older than retention_days

    Example:
        >>> tracker = IngestionJobTracker()
        >>> job_id = await tracker.create_job("/data/docs", recursive=True, total_files=5)
        >>> await tracker.add_event(job_id, "INFO", "parsing", "file.pdf", None, None, "Started")
        >>> await tracker.update_job_status(job_id, "completed")
    """

    def __init__(self, db_path: Path | None = None, retention_days: int = 90) -> None:
        """Initialize job tracker with database path and retention policy.

        Args:
            db_path: Path to SQLite database (default: data/jobs/ingestion_jobs.db)
            retention_days: Days to retain completed jobs (default 90)

        Example:
            >>> tracker = IngestionJobTracker()
            >>> tracker.db_path
            PosixPath('data/jobs/ingestion_jobs.db')
        """
        self.db_path = db_path or DB_PATH
        self.retention_days = retention_days
        self._lock = asyncio.Lock()
        self._initialized = False

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "job_tracker_initialized",
            db_path=str(self.db_path),
            retention_days=retention_days,
        )

    async def _init_db(self) -> None:
        """Initialize database schema if not exists.

        Creates 3 tables:
        - ingestion_jobs: Job-level metadata
        - ingestion_events: Event-level logging
        - ingestion_files: File-level progress

        Thread-safe: Uses asyncio lock to prevent concurrent initialization.

        Example:
            >>> tracker = IngestionJobTracker()
            >>> await tracker._init_db()  # Called automatically on first operation
        """
        async with self._lock:
            if self._initialized:
                return

            def init_schema(conn: sqlite3.Connection) -> None:
                """Create database schema (run in thread pool)."""
                cursor = conn.cursor()

                # Table 1: ingestion_jobs
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ingestion_jobs (
                        id TEXT PRIMARY KEY,
                        started_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP,
                        status TEXT NOT NULL,
                        directory_path TEXT NOT NULL,
                        recursive BOOLEAN NOT NULL,
                        total_files INTEGER NOT NULL,
                        processed_files INTEGER DEFAULT 0,
                        total_errors INTEGER DEFAULT 0,
                        total_warnings INTEGER DEFAULT 0,
                        config TEXT
                    )
                """
                )

                # Table 2: ingestion_events
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ingestion_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
                        timestamp TIMESTAMP NOT NULL,
                        level TEXT NOT NULL,
                        phase TEXT,
                        file_name TEXT,
                        page_number INTEGER,
                        chunk_id TEXT,
                        message TEXT NOT NULL,
                        details TEXT
                    )
                """
                )

                # Table 3: ingestion_files
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ingestion_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
                        file_path TEXT NOT NULL,
                        file_name TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        file_size_bytes INTEGER,
                        parser_used TEXT,
                        status TEXT NOT NULL,
                        pages_total INTEGER,
                        pages_processed INTEGER DEFAULT 0,
                        chunks_created INTEGER DEFAULT 0,
                        entities_extracted INTEGER DEFAULT 0,
                        relations_extracted INTEGER DEFAULT 0,
                        vlm_images_total INTEGER DEFAULT 0,
                        vlm_images_processed INTEGER DEFAULT 0,
                        processing_time_ms INTEGER,
                        error_message TEXT,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """
                )

                # Indexes for performance
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_jobs_status ON ingestion_jobs(status)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_jobs_started ON ingestion_jobs(started_at)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_events_job ON ingestion_events(job_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_events_level ON ingestion_events(level)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_files_job ON ingestion_files(job_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_files_status ON ingestion_files(status)"
                )

                conn.commit()

                logger.info("job_tracker_schema_initialized", db_path=str(self.db_path))

            # Run in thread pool (SQLite blocks async event loop)
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: init_schema(sqlite3.connect(self.db_path, check_same_thread=False))
            )

            self._initialized = True

    async def create_job(
        self,
        directory_path: str,
        recursive: bool,
        total_files: int,
        config: dict[str, Any] | None = None,
    ) -> str:
        """Create new ingestion job and return job ID.

        Args:
            directory_path: Directory being indexed
            recursive: Whether scan is recursive
            total_files: Total number of files to process
            config: Optional configuration metadata (JSON-serializable)

        Returns:
            Job ID (UUID format)

        Example:
            >>> job_id = await tracker.create_job(
            ...     directory_path="/data/documents",
            ...     recursive=True,
            ...     total_files=10,
            ...     config={"vlm_enabled": True}
            ... )
            >>> job_id
            'job_2025-11-27_123456'
        """
        await self._init_db()

        # Generate job ID with timestamp
        from datetime import datetime

        job_id = f"job_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"

        started_at = datetime.now()
        config_json = json.dumps(config) if config else None

        def insert_job(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ingestion_jobs (
                    id, started_at, status, directory_path, recursive, total_files, config
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    started_at,
                    "running",
                    directory_path,
                    recursive,
                    total_files,
                    config_json,
                ),
            )
            conn.commit()

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: insert_job(sqlite3.connect(self.db_path, check_same_thread=False))
        )

        logger.info(
            "job_created",
            job_id=job_id,
            directory_path=directory_path,
            total_files=total_files,
        )

        return job_id

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        processed_files: int | None = None,
        total_errors: int | None = None,
        total_warnings: int | None = None,
    ) -> None:
        """Update job status and counters.

        Args:
            job_id: Job ID
            status: New status (running/completed/failed/cancelled)
            processed_files: Number of files processed (optional)
            total_errors: Total error count (optional)
            total_warnings: Total warning count (optional)

        Example:
            >>> await tracker.update_job_status("job_123", "completed", processed_files=10)
        """
        await self._init_db()

        def update_job(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()

            # Build UPDATE query dynamically
            updates = ["status = ?"]
            params = [status]

            if status in ("completed", "failed", "cancelled"):
                updates.append("completed_at = ?")
                params.append(datetime.now())

            if processed_files is not None:
                updates.append("processed_files = ?")
                params.append(processed_files)

            if total_errors is not None:
                updates.append("total_errors = ?")
                params.append(total_errors)

            if total_warnings is not None:
                updates.append("total_warnings = ?")
                params.append(total_warnings)

            params.append(job_id)

            query = f"UPDATE ingestion_jobs SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: update_job(sqlite3.connect(self.db_path, check_same_thread=False))
        )

        logger.info(
            "job_status_updated",
            job_id=job_id,
            status=status,
            processed_files=processed_files,
        )

    async def add_event(
        self,
        job_id: str,
        level: EventLevel,
        phase: Phase | None,
        file_name: str | None,
        page_number: int | None,
        chunk_id: str | None,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log ingestion event.

        Args:
            job_id: Job ID
            level: Event level (INFO/DEBUG/WARN/ERROR)
            phase: Pipeline phase (parsing/vlm/chunking/embedding/bm25/graph)
            file_name: File being processed (optional)
            page_number: Page number (optional)
            chunk_id: Chunk ID (optional)
            message: Event message
            details: Additional metadata (JSON-serializable, optional)

        Example:
            >>> await tracker.add_event(
            ...     job_id="job_123",
            ...     level="INFO",
            ...     phase="parsing",
            ...     file_name="report.pdf",
            ...     page_number=None,
            ...     chunk_id=None,
            ...     message="Parsing started"
            ... )
        """
        await self._init_db()

        timestamp = datetime.now()
        details_json = json.dumps(details) if details else None

        def insert_event(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ingestion_events (
                    job_id, timestamp, level, phase, file_name, page_number, chunk_id, message, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    timestamp,
                    level,
                    phase,
                    file_name,
                    page_number,
                    chunk_id,
                    message,
                    details_json,
                ),
            )
            conn.commit()

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: insert_event(sqlite3.connect(self.db_path, check_same_thread=False))
        )

        # Log ERROR events to structlog
        if level == "ERROR":
            logger.error(
                "ingestion_event_error",
                job_id=job_id,
                phase=phase,
                file_name=file_name,
                message=message,
            )

    async def add_file(
        self,
        job_id: str,
        file_path: str,
        file_name: str,
        file_type: str,
        file_size_bytes: int,
        parser_used: ParserType,
    ) -> int:
        """Add file to job tracking.

        Args:
            job_id: Job ID
            file_path: Full file path
            file_name: File name only
            file_type: File extension (e.g., '.pdf')
            file_size_bytes: File size in bytes
            parser_used: Parser type (docling/llamaindex/unsupported)

        Returns:
            File record ID (auto-increment)

        Example:
            >>> file_id = await tracker.add_file(
            ...     job_id="job_123",
            ...     file_path="/data/report.pdf",
            ...     file_name="report.pdf",
            ...     file_type=".pdf",
            ...     file_size_bytes=2457600,
            ...     parser_used="docling"
            ... )
        """
        await self._init_db()

        def insert_file(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ingestion_files (
                    job_id, file_path, file_name, file_type, file_size_bytes, parser_used,
                    status, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    file_path,
                    file_name,
                    file_type,
                    file_size_bytes,
                    parser_used,
                    "pending",
                    datetime.now(),
                ),
            )
            conn.commit()
            return cursor.lastrowid

        file_id = await asyncio.get_event_loop().run_in_executor(
            None, lambda: insert_file(sqlite3.connect(self.db_path, check_same_thread=False))
        )

        return file_id

    async def update_file(
        self,
        file_id: int,
        status: FileStatus | None = None,
        pages_processed: int | None = None,
        chunks_created: int | None = None,
        entities_extracted: int | None = None,
        relations_extracted: int | None = None,
        vlm_images_processed: int | None = None,
        processing_time_ms: int | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update file progress.

        Args:
            file_id: File record ID
            status: New status (pending/processing/completed/failed/skipped)
            pages_processed: Number of pages processed
            chunks_created: Number of chunks created
            entities_extracted: Number of entities extracted
            relations_extracted: Number of relations extracted
            vlm_images_processed: Number of VLM images processed
            processing_time_ms: Total processing time in milliseconds
            error_message: Error message (if failed)

        Example:
            >>> await tracker.update_file(
            ...     file_id=1,
            ...     status="completed",
            ...     pages_processed=10,
            ...     chunks_created=25
            ... )
        """
        await self._init_db()

        def update_file_record(conn: sqlite3.Connection) -> None:
            cursor = conn.cursor()

            # Build UPDATE query dynamically
            updates = []
            params = []

            if status is not None:
                updates.append("status = ?")
                params.append(status)

                if status in ("completed", "failed", "skipped"):
                    updates.append("completed_at = ?")
                    params.append(datetime.now())

            if pages_processed is not None:
                updates.append("pages_processed = ?")
                params.append(pages_processed)

            if chunks_created is not None:
                updates.append("chunks_created = ?")
                params.append(chunks_created)

            if entities_extracted is not None:
                updates.append("entities_extracted = ?")
                params.append(entities_extracted)

            if relations_extracted is not None:
                updates.append("relations_extracted = ?")
                params.append(relations_extracted)

            if vlm_images_processed is not None:
                updates.append("vlm_images_processed = ?")
                params.append(vlm_images_processed)

            if processing_time_ms is not None:
                updates.append("processing_time_ms = ?")
                params.append(processing_time_ms)

            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            if not updates:
                return

            params.append(file_id)
            query = f"UPDATE ingestion_files SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: update_file_record(sqlite3.connect(self.db_path, check_same_thread=False))
        )

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Retrieve job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job record as dict or None if not found

        Example:
            >>> job = await tracker.get_job("job_123")
            >>> job["status"]
            'completed'
        """
        await self._init_db()

        def fetch_job(conn: sqlite3.Connection) -> dict[str, Any] | None:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ingestion_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()

            if not row:
                return None

            columns = [desc[0] for desc in cursor.description]
            job_dict = dict(zip(columns, row, strict=False))

            # Parse JSON config
            if job_dict.get("config"):
                job_dict["config"] = json.loads(job_dict["config"])

            return job_dict

        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: fetch_job(sqlite3.connect(self.db_path, check_same_thread=False))
        )

    async def get_jobs(
        self,
        status: JobStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List jobs with optional filtering.

        Args:
            status: Filter by status (optional)
            limit: Maximum number of results (default 100)
            offset: Pagination offset (default 0)

        Returns:
            List of job records (sorted by started_at DESC)

        Example:
            >>> jobs = await tracker.get_jobs(status="completed", limit=10)
            >>> len(jobs)
            10
        """
        await self._init_db()

        def fetch_jobs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            cursor = conn.cursor()

            if status:
                query = "SELECT * FROM ingestion_jobs WHERE status = ? ORDER BY started_at DESC LIMIT ? OFFSET ?"
                cursor.execute(query, (status, limit, offset))
            else:
                query = "SELECT * FROM ingestion_jobs ORDER BY started_at DESC LIMIT ? OFFSET ?"
                cursor.execute(query, (limit, offset))

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            jobs = []
            for row in rows:
                job_dict = dict(zip(columns, row, strict=False))
                if job_dict.get("config"):
                    job_dict["config"] = json.loads(job_dict["config"])
                jobs.append(job_dict)

            return jobs

        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: fetch_jobs(sqlite3.connect(self.db_path, check_same_thread=False))
        )

    async def get_events(
        self,
        job_id: str,
        level: EventLevel | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Get events for job.

        Args:
            job_id: Job ID
            level: Filter by level (optional)
            limit: Maximum number of results (default 1000)

        Returns:
            List of event records (sorted by timestamp ASC)

        Example:
            >>> events = await tracker.get_events("job_123", level="ERROR")
        """
        await self._init_db()

        def fetch_events(conn: sqlite3.Connection) -> list[dict[str, Any]]:
            cursor = conn.cursor()

            if level:
                query = "SELECT * FROM ingestion_events WHERE job_id = ? AND level = ? ORDER BY timestamp ASC LIMIT ?"
                cursor.execute(query, (job_id, level, limit))
            else:
                query = (
                    "SELECT * FROM ingestion_events WHERE job_id = ? ORDER BY timestamp ASC LIMIT ?"
                )
                cursor.execute(query, (job_id, limit))

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            events = []
            for row in rows:
                event_dict = dict(zip(columns, row, strict=False))
                if event_dict.get("details"):
                    event_dict["details"] = json.loads(event_dict["details"])
                events.append(event_dict)

            return events

        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: fetch_events(sqlite3.connect(self.db_path, check_same_thread=False))
        )

    async def get_errors(self, job_id: str) -> list[dict[str, Any]]:
        """Get only ERROR-level events for job.

        Args:
            job_id: Job ID

        Returns:
            List of ERROR events

        Example:
            >>> errors = await tracker.get_errors("job_123")
        """
        return await self.get_events(job_id, level="ERROR")

    async def cleanup_old_jobs(self, retention_days: int | None = None) -> int:
        """Delete jobs older than retention period.

        Args:
            retention_days: Days to retain (default: self.retention_days)

        Returns:
            Number of jobs deleted

        Example:
            >>> deleted_count = await tracker.cleanup_old_jobs(retention_days=30)
            >>> deleted_count
            15
        """
        await self._init_db()

        retention = retention_days or self.retention_days
        cutoff_date = datetime.now() - timedelta(days=retention)

        def delete_old_jobs(conn: sqlite3.Connection) -> int:
            cursor = conn.cursor()

            # Delete jobs older than cutoff (CASCADE deletes events/files)
            cursor.execute(
                "DELETE FROM ingestion_jobs WHERE started_at < ? AND status IN ('completed', 'failed', 'cancelled')",
                (cutoff_date,),
            )
            deleted_count = cursor.rowcount
            conn.commit()

            return deleted_count

        deleted = await asyncio.get_event_loop().run_in_executor(
            None, lambda: delete_old_jobs(sqlite3.connect(self.db_path, check_same_thread=False))
        )

        logger.info(
            "job_tracker_cleanup_complete",
            retention_days=retention,
            deleted_count=deleted,
        )

        return deleted


# Global singleton instance
_tracker: IngestionJobTracker | None = None


def get_job_tracker() -> IngestionJobTracker:
    """Get singleton IngestionJobTracker instance.

    Returns:
        Global IngestionJobTracker instance

    Example:
        >>> tracker = get_job_tracker()
        >>> job_id = await tracker.create_job("/data/docs", True, 10)
    """
    global _tracker
    if _tracker is None:
        _tracker = IngestionJobTracker()
    return _tracker
