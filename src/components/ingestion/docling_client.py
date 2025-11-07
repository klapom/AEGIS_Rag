"""Docling CUDA Container Client - Sprint 21 Feature 21.1.

This module provides an HTTP client for interacting with the Docling CUDA Docker container.

Docling is a GPU-accelerated document parsing library that provides:
- OCR for scanned PDFs (Tesseract + GPU acceleration)
- Table extraction with structure preservation
- Layout analysis (headings, lists, columns, formatting)
- Multi-format support (PDF, DOCX, PPTX, HTML, images)
- CUDA optimization for RTX 3060 6GB VRAM

Container Lifecycle:
  1. start_container() → Docker Compose starts Docling service
  2. _wait_for_ready() → Health check until container ready
  3. parse_document() → Send file, receive parsed content
  4. stop_container() → Free VRAM for next pipeline stage

Memory Optimization:
  - Container only runs during "docling" node in LangGraph pipeline
  - Stops after batch complete to free 6GB VRAM for embedding/graph extraction
  - Sequential execution prevents OOM (4.4GB RAM constraint)

Example:
    >>> client = DoclingContainerClient(base_url="http://localhost:8080")
    >>> await client.start_container()
    >>>
    >>> parsed = await client.parse_document(Path("document.pdf"))
    >>> # parsed = {
    >>> #   "text": "...",
    >>> #   "metadata": {...},
    >>> #   "tables": [...],
    >>> #   "images": [...],
    >>> #   "layout": {...}
    >>> # }
    >>>
    >>> await client.stop_container()
"""

import asyncio
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field

from src.core.exceptions import IngestionError

logger = structlog.get_logger(__name__)


class DoclingParsedDocument(BaseModel):
    """Parsed document from Docling container.

    Attributes:
        text: Full document text (including OCR'd content)
        metadata: Document metadata (filename, pages, size, etc.)
        tables: List of extracted tables with structure
        images: List of image references with positions
        layout: Document layout structure (headings, paragraphs, lists)
        parse_time_ms: Parsing duration in milliseconds
    """

    text: str = Field(description="Full document text with OCR")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    tables: list[dict[str, Any]] = Field(default_factory=list, description="Extracted tables")
    images: list[dict[str, Any]] = Field(default_factory=list, description="Image references")
    layout: dict[str, Any] = Field(default_factory=dict, description="Layout structure")
    parse_time_ms: float = Field(description="Parsing duration")


class DoclingContainerClient:
    """HTTP client for Docling CUDA Docker container.

    This client manages the lifecycle of the Docling container and provides
    methods for parsing documents via HTTP API.

    Container Management:
        - start_container(): Start via Docker Compose
        - stop_container(): Stop to free VRAM
        - _wait_for_ready(): Health check polling

    Document Parsing:
        - parse_document(): Send single file, receive parsed content
        - parse_batch(): Process multiple files efficiently

    Attributes:
        base_url: Docling container HTTP endpoint (default: http://localhost:8080)
        timeout_seconds: HTTP request timeout (default: 300s for large PDFs)
        max_retries: Retry count for transient failures (default: 3)
        health_check_interval_seconds: Polling interval for readiness (default: 2s)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout_seconds: int = 300,
        max_retries: int = 3,
        health_check_interval_seconds: int = 2,
    ):
        """Initialize Docling container client.

        Args:
            base_url: Docling container HTTP endpoint
            timeout_seconds: HTTP request timeout (for large files)
            max_retries: Retry count for transient failures
            health_check_interval_seconds: Health check polling interval
        """
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.health_check_interval_seconds = health_check_interval_seconds

        # HTTP client (initialized lazily)
        self.client: httpx.AsyncClient | None = None
        self._container_running = False

        logger.info(
            "docling_client_initialized",
            base_url=self.base_url,
            timeout_seconds=self.timeout_seconds,
        )

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized (lazy initialization).

        Returns:
            Initialized AsyncClient

        Note:
            Lazy initialization ensures pickle compatibility for LangGraph state.
        """
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds, connect=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
            logger.debug("docling_http_client_initialized")
        return self.client

    async def start_container(self) -> None:
        """Start Docling CUDA container via Docker Compose.

        Workflow:
            1. Run: docker compose --profile ingestion up -d docling
            2. Wait for health check: GET /health → 200 OK
            3. Set _container_running = True

        Raises:
            IngestionError: If container fails to start or health check times out

        Example:
            >>> await client.start_container()
            >>> # Container now running on http://localhost:8080
        """
        logger.info("docling_container_start_requested")

        try:
            # Start Docker Compose service with "ingestion" profile
            # Sprint 21: Docling service uses profile to avoid always-on GPU usage
            result = subprocess.run(
                ["docker", "compose", "--profile", "ingestion", "up", "-d", "docling"],
                check=True,
                capture_output=True,
                text=True,
                cwd=Path.cwd(),  # Run from project root
            )

            logger.info(
                "docling_container_started",
                stdout=result.stdout[:500] if result.stdout else "",
                stderr=result.stderr[:500] if result.stderr else "",
            )

            # Wait for container to be ready (health check)
            await self._wait_for_ready()

            self._container_running = True
            logger.info("docling_container_ready", base_url=self.base_url)

        except subprocess.CalledProcessError as e:
            logger.error(
                "docling_container_start_failed",
                returncode=e.returncode,
                stdout=e.stdout[:500] if e.stdout else "",
                stderr=e.stderr[:500] if e.stderr else "",
            )
            raise IngestionError(f"Failed to start Docling container: {e.stderr}") from e
        except Exception as e:
            logger.error("docling_container_start_error", error=str(e), exc_info=True)
            raise IngestionError(f"Unexpected error starting Docling container: {e}") from e

    async def stop_container(self) -> None:
        """Stop Docling CUDA container to free VRAM.

        Workflow:
            1. Run: docker compose stop docling
            2. Set _container_running = False
            3. Close HTTP client

        Raises:
            IngestionError: If container fails to stop

        Example:
            >>> await client.stop_container()
            >>> # VRAM freed for next pipeline stage
        """
        logger.info("docling_container_stop_requested")

        try:
            # Stop Docker Compose service (preserves state for restart)
            result = subprocess.run(
                ["docker", "compose", "stop", "docling"],
                check=True,
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )

            logger.info(
                "docling_container_stopped",
                stdout=result.stdout[:200] if result.stdout else "",
            )

            self._container_running = False

            # Close HTTP client
            if self.client:
                await self.client.aclose()
                self.client = None
                logger.debug("docling_http_client_closed")

        except subprocess.CalledProcessError as e:
            logger.error(
                "docling_container_stop_failed",
                returncode=e.returncode,
                stderr=e.stderr[:500] if e.stderr else "",
            )
            raise IngestionError(f"Failed to stop Docling container: {e.stderr}") from e
        except Exception as e:
            logger.error("docling_container_stop_error", error=str(e), exc_info=True)
            raise IngestionError(f"Unexpected error stopping Docling container: {e}") from e

    async def _wait_for_ready(self, max_wait_seconds: int = 60) -> None:
        """Wait for Docling container to be ready (health check).

        Polls GET /health endpoint until 200 OK or timeout.

        Args:
            max_wait_seconds: Maximum wait time before timeout (default: 60s)

        Raises:
            IngestionError: If health check times out or container unhealthy

        Example:
            >>> await client._wait_for_ready()
            >>> # Container ready, can now parse documents
        """
        logger.info("docling_health_check_start", max_wait_seconds=max_wait_seconds)

        client = await self._ensure_client()
        start_time = time.time()
        attempts = 0

        while (time.time() - start_time) < max_wait_seconds:
            attempts += 1

            try:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    elapsed = time.time() - start_time
                    logger.info(
                        "docling_health_check_success",
                        attempts=attempts,
                        elapsed_seconds=round(elapsed, 2),
                    )
                    return

                logger.debug(
                    "docling_health_check_not_ready",
                    status_code=response.status_code,
                    attempt=attempts,
                )

            except httpx.ConnectError:
                # Container not yet accepting connections
                logger.debug("docling_health_check_connection_refused", attempt=attempts)
            except Exception as e:
                logger.debug("docling_health_check_error", error=str(e), attempt=attempts)

            # Wait before next attempt
            await asyncio.sleep(self.health_check_interval_seconds)

        # Timeout exceeded
        elapsed = time.time() - start_time
        logger.error(
            "docling_health_check_timeout",
            attempts=attempts,
            elapsed_seconds=round(elapsed, 2),
            max_wait_seconds=max_wait_seconds,
        )
        raise IngestionError(
            f"Docling container health check timeout after {elapsed:.1f}s ({attempts} attempts)"
        )

    async def parse_document(self, file_path: Path) -> DoclingParsedDocument:
        """Parse a single document via Docling container.

        Workflow:
            1. Validate file exists and is readable
            2. Send file via POST /parse (multipart/form-data)
            3. Receive parsed content (JSON)
            4. Parse into DoclingParsedDocument

        Args:
            file_path: Path to document file (PDF, DOCX, PPTX, etc.)

        Returns:
            DoclingParsedDocument with text, metadata, tables, images, layout

        Raises:
            IngestionError: If parsing fails or file not found
            FileNotFoundError: If file does not exist

        Example:
            >>> parsed = await client.parse_document(Path("report.pdf"))
            >>> print(f"Text length: {len(parsed.text)}")
            >>> print(f"Tables found: {len(parsed.tables)}")
            >>> print(f"Parse time: {parsed.parse_time_ms}ms")
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        if not self._container_running:
            logger.warning(
                "docling_parse_without_start",
                file_path=str(file_path),
                message="Container not explicitly started, health may be unknown",
            )

        logger.info("docling_parse_start", file_path=str(file_path), file_size=file_path.stat().st_size)

        client = await self._ensure_client()
        start_time = time.time()

        try:
            # Open file and prepare multipart upload
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "application/octet-stream")}

                # Send parse request
                response = await client.post(
                    f"{self.base_url}/parse",
                    files=files,
                    timeout=self.timeout_seconds,
                )

                response.raise_for_status()

            # Parse response
            parse_data = response.json()
            parse_time = (time.time() - start_time) * 1000  # Convert to ms

            # Create DoclingParsedDocument
            parsed = DoclingParsedDocument(
                text=parse_data.get("text", ""),
                metadata=parse_data.get("metadata", {}),
                tables=parse_data.get("tables", []),
                images=parse_data.get("images", []),
                layout=parse_data.get("layout", {}),
                parse_time_ms=parse_time,
            )

            logger.info(
                "docling_parse_success",
                file_path=str(file_path),
                text_length=len(parsed.text),
                tables_count=len(parsed.tables),
                images_count=len(parsed.images),
                parse_time_ms=round(parse_time, 2),
            )

            return parsed

        except httpx.HTTPStatusError as e:
            logger.error(
                "docling_parse_http_error",
                file_path=str(file_path),
                status_code=e.response.status_code,
                response_text=e.response.text[:500],
            )
            raise IngestionError(
                f"Docling parse failed (HTTP {e.response.status_code}): {e.response.text[:200]}"
            ) from e
        except httpx.TimeoutException as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(
                "docling_parse_timeout",
                file_path=str(file_path),
                elapsed_ms=round(elapsed, 2),
                timeout_seconds=self.timeout_seconds,
            )
            raise IngestionError(
                f"Docling parse timeout after {elapsed/1000:.1f}s (file: {file_path.name})"
            ) from e
        except Exception as e:
            logger.error("docling_parse_error", file_path=str(file_path), error=str(e), exc_info=True)
            raise IngestionError(f"Unexpected error parsing document: {e}") from e

    async def parse_batch(self, file_paths: list[Path]) -> list[DoclingParsedDocument]:
        """Parse multiple documents efficiently (batch processing).

        Parses documents sequentially to avoid overwhelming container.
        For true parallel processing, use multiple container instances.

        Args:
            file_paths: List of document file paths

        Returns:
            List of DoclingParsedDocument (same order as input)

        Raises:
            IngestionError: If batch processing fails

        Example:
            >>> files = [Path("doc1.pdf"), Path("doc2.pdf"), Path("doc3.pdf")]
            >>> results = await client.parse_batch(files)
            >>> print(f"Parsed {len(results)} documents")
        """
        logger.info("docling_batch_parse_start", batch_size=len(file_paths))

        if not self._container_running:
            logger.warning("docling_batch_parse_without_start")

        results = []
        errors = []

        for idx, file_path in enumerate(file_paths):
            try:
                parsed = await self.parse_document(file_path)
                results.append(parsed)
                logger.debug("docling_batch_parse_progress", current=idx + 1, total=len(file_paths))

            except Exception as e:
                logger.error(
                    "docling_batch_parse_file_error",
                    file_path=str(file_path),
                    error=str(e),
                    current=idx + 1,
                    total=len(file_paths),
                )
                errors.append({"file_path": str(file_path), "error": str(e)})
                # Continue processing remaining files (partial success)

        logger.info(
            "docling_batch_parse_complete",
            total_files=len(file_paths),
            successful=len(results),
            failed=len(errors),
            errors=errors if errors else None,
        )

        return results

    async def __aenter__(self):
        """Async context manager entry: start container."""
        await self.start_container()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit: stop container."""
        await self.stop_container()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


async def parse_document_with_docling(
    file_path: Path,
    base_url: str = "http://localhost:8080",
    auto_manage_container: bool = True,
) -> DoclingParsedDocument:
    """Convenience function to parse a single document with Docling.

    Args:
        file_path: Path to document file
        base_url: Docling container endpoint
        auto_manage_container: If True, start/stop container automatically

    Returns:
        DoclingParsedDocument with parsed content

    Example:
        >>> # Auto-manage container (recommended for one-off parsing)
        >>> parsed = await parse_document_with_docling(Path("report.pdf"))
        >>>
        >>> # Manual management (for batch processing)
        >>> client = DoclingContainerClient()
        >>> await client.start_container()
        >>> parsed1 = await parse_document_with_docling(Path("doc1.pdf"), auto_manage_container=False)
        >>> parsed2 = await parse_document_with_docling(Path("doc2.pdf"), auto_manage_container=False)
        >>> await client.stop_container()
    """
    client = DoclingContainerClient(base_url=base_url)

    if auto_manage_container:
        async with client:
            return await client.parse_document(file_path)
    else:
        return await client.parse_document(file_path)
