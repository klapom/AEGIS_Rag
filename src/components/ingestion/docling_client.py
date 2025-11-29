"""Docling CUDA Container Client - Sprint 21 Feature 21.1.

This module provides an HTTP client for interacting with the Docling CUDA Docker container.

Docling is a GPU-accelerated document parsing library that provides:
- OCR for scanned PDFs (Tesseract + GPU acceleration)
- Table extraction with structure preservation
- Layout analysis (headings, lists, columns, formatting)
- Multi-format support (PDF, DOCX, PPTX, XLSX, HTML, images)
- CUDA optimization for RTX 3060 6GB VRAM

================================================================================
SUPPORTED FORMATS (Sprint 33)
================================================================================

MODERN OFFICE FORMATS (SUPPORTED):
  - PDF  (.pdf)   - Full support with OCR, tables, layout
  - DOCX (.docx)  - Full support, requires Word heading styles for section_header
  - PPTX (.pptx)  - Full support with slide titles
  - XLSX (.xlsx)  - Table extraction
  - HTML (.html)  - Structure preserved
  - Images        - PNG, TIFF, JPEG with OCR

LEGACY OFFICE FORMATS (NOT SUPPORTED):
  - DOC  (.doc)   - Legacy Word 97-2003 - NOT SUPPORTED
  - XLS  (.xls)   - Legacy Excel 97-2003 - NOT SUPPORTED
  - PPT  (.ppt)   - Legacy PowerPoint 97-2003 - NOT SUPPORTED

Docling uses python-docx, python-pptx, openpyxl internally which only support
the modern Office Open XML formats (2007+). Legacy binary formats (.doc, .xls, .ppt)
must be converted to modern formats before processing.

WORKAROUND FOR LEGACY FORMATS:
  1. Convert to modern format using Microsoft Office or LibreOffice
  2. Use LibreOffice CLI: `soffice --headless --convert-to docx file.doc`
  3. For programmatic conversion: python-docx2txt (text only, no structure)

See: https://docling-project.github.io/docling/usage/supported_formats/
================================================================================

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
        tables: list of extracted tables with structure
        images: list of image references with positions
        layout: Document layout structure (headings, paragraphs, lists)
        parse_time_ms: Parsing duration in milliseconds
    """

    text: str = Field(description="Full document text with OCR")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    tables: list[dict[str, Any]] = Field(default_factory=list, description="Extracted tables")
    images: list[dict[str, Any]] = Field(default_factory=list, description="Image references")
    layout: dict[str, Any] = Field(default_factory=dict, description="Layout structure")
    parse_time_ms: float = Field(description="Parsing duration")
    json_content: dict[str, Any] = Field(
        default_factory=dict, description="Full Docling JSON response"
    )
    md_content: str = Field(default="", description="Markdown with embedded base64 images")

    @property
    def body(self) -> dict[str, Any] | None:
        """Provide Docling-compatible .body attribute for section extraction.

        Sprint 33 Fix (TD-044): The section_extraction.py expects .body attribute
        which exists on native Docling DoclingDocument objects but not on our
        HTTP API wrapper. This property provides compatibility.

        Returns:
            Body structure from json_content, or None if not available.
        """
        return self.json_content.get("body") if self.json_content else None

    @property
    def document(self) -> "DoclingParsedDocument":
        """Self-reference for code expecting .document attribute.

        Sprint 33 Fix (TD-044): Some code paths check for parsed.document
        expecting a nested document object. Since DoclingParsedDocument IS
        the document, we return self.

        Returns:
            Self reference.
        """
        return self


class DoclingClient:
    """HTTP client for Docling CUDA Docker container.

    Sprint 25 Feature 25.9: Renamed from DoclingContainerClient to DoclingClient for consistency.

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
    ) -> None:
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
            1. Check if container already running (docker ps)
            2. If running: Skip start, just verify health
            3. If not running: Start container via docker compose
            4. Wait for health check: GET /health → 200 OK
            5. set _container_running = True

        Raises:
            IngestionError: If container fails to start or health check times out

        Example:
            >>> await client.start_container()
            >>> # Container now running on http://localhost:8080
        """
        logger.info("docling_container_start_requested")

        try:
            # Check if container already running
            check_result = subprocess.run(
                ["docker", "ps", "--filter", "name=aegis-docling", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=True,
            )

            if "aegis-docling" in check_result.stdout:
                logger.info("docling_container_already_running", container="aegis-docling")
                # Verify it's healthy
                await self._wait_for_ready()
                self._container_running = True
                logger.info("docling_container_verified_healthy", base_url=self.base_url)
                return

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
            raise IngestionError(
                document_id="docling_container",
                reason=f"Failed to start Docling container: {e.stderr}",
            ) from e
        except Exception as e:
            logger.error("docling_container_start_error", error=str(e), exc_info=True)
            raise IngestionError(
                document_id="docling_container",
                reason=f"Unexpected error starting Docling container: {e}",
            ) from e

    async def stop_container(self) -> None:
        """Stop Docling CUDA container to free VRAM.

        Workflow:
            1. Run: docker compose stop docling
            2. set _container_running = False
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
            raise IngestionError(
                document_id="docling_container",
                reason=f"Failed to stop Docling container: {e.stderr}",
            ) from e
        except Exception as e:
            logger.error("docling_container_stop_error", error=str(e), exc_info=True)
            raise IngestionError(
                document_id="docling_container",
                reason=f"Unexpected error stopping Docling container: {e}",
            ) from e

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
            document_id="docling_container",
            reason=f"Docling container health check timeout after {elapsed:.1f}s ({attempts} attempts)",
        )

    async def parse_document(self, file_path: Path) -> DoclingParsedDocument:
        """Parse a single document via Docling container (async pattern).

        Workflow:
            1. Validate file exists and is readable
            2. POST /v1/convert/file/async → get task_id
            3. Poll GET /v1/status/poll/{task_id} until success/failure
            4. GET /v1/result/{task_id} → parse content
            5. Return DoclingParsedDocument

        Args:
            file_path: Path to document file (PDF, DOCX, PPTX, TXT, etc.)

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

        # Sprint 33: Reject legacy Office formats (not supported by Docling)
        LEGACY_FORMATS = {".doc", ".xls", ".ppt"}
        file_ext = file_path.suffix.lower()
        if file_ext in LEGACY_FORMATS:
            raise IngestionError(
                f"Legacy Office format '{file_ext}' is NOT SUPPORTED. "
                f"Please convert to modern format (.docx, .xlsx, .pptx) before processing. "
                f"File: {file_path.name}"
            )

        if not self._container_running:
            logger.warning(
                "docling_parse_without_start",
                file_path=str(file_path),
                message="Container not explicitly started, health may be unknown",
            )

        file_size_bytes = file_path.stat().st_size
        logger.info(
            "TIMING_docling_parse_start",
            stage="docling",
            file_path=str(file_path),
            file_size_bytes=file_size_bytes,
            file_size_mb=round(file_size_bytes / 1024 / 1024, 2),
        )

        client = await self._ensure_client()
        start_time = time.perf_counter()

        # Timing variables for sub-stages
        upload_start = time.perf_counter()

        try:
            # Step 1: Submit file to async API
            with open(file_path, "rb") as f:
                files = {"files": (file_path.name, f, "application/octet-stream")}
                # Request both markdown and JSON (Feature 21.5: JSON for tables/images/layout)
                # Note: image_export_mode=embedded only works for MD/HTML, not JSON
                # For JSON, images are references only - we extract from MD
                data = {
                    "to_formats": ["md", "json"],
                    "image_export_mode": "embedded",  # Embed images as base64 in MD output
                    "include_images": True,  # Extract images from document
                    "images_scale": 2.0,  # Scale factor for image quality
                }

                response = await client.post(
                    f"{self.base_url}/v1/convert/file/async",
                    files=files,
                    data=data,
                    timeout=30.0,  # Short timeout for submission
                )
                response.raise_for_status()

            upload_end = time.perf_counter()
            upload_duration_ms = (upload_end - upload_start) * 1000

            task_data = response.json()
            task_id = task_data.get("task_id")
            if not task_id:
                raise IngestionError(str(file_path), f"No task_id in response: {task_data}")

            logger.info(
                "TIMING_docling_file_uploaded",
                stage="docling",
                substage="file_upload",
                duration_ms=round(upload_duration_ms, 2),
                task_id=task_id,
                file_path=str(file_path),
            )

            # Start polling timer
            polling_start = time.perf_counter()

            # Step 2: Poll for task completion
            poll_interval = 2.0  # seconds
            max_polls = int(self.timeout_seconds / poll_interval)

            for attempt in range(max_polls):
                await asyncio.sleep(poll_interval)

                status_response = await client.get(
                    f"{self.base_url}/v1/status/poll/{task_id}",
                    timeout=30.0,  # Longer timeout for status polling (Docling can be slow)
                )
                status_response.raise_for_status()
                status_data = status_response.json()
                task_status = status_data.get("task_status")

                if task_status == "success":
                    polling_end = time.perf_counter()
                    polling_duration_ms = (polling_end - polling_start) * 1000
                    logger.info(
                        "TIMING_docling_task_completed",
                        stage="docling",
                        substage="task_polling",
                        duration_ms=round(polling_duration_ms, 2),
                        task_id=task_id,
                        poll_attempts=attempt + 1,
                    )
                    break
                elif task_status == "failure":
                    raise IngestionError(str(file_path), f"Docling task failed: {status_data}")
                elif task_status in ("pending", "processing", "started"):
                    # Task still in progress, continue polling
                    continue
                else:
                    raise IngestionError(str(file_path), f"Unknown task status: {task_status}")

            else:
                # Timeout: max_polls reached
                elapsed = time.perf_counter() - start_time
                raise IngestionError(
                    str(file_path),
                    f"Docling task timeout after {elapsed:.1f}s (task_id: {task_id}, file: {file_path.name})",
                )

            # Step 3: Fetch result
            result_download_start = time.perf_counter()
            result_response = await client.get(
                f"{self.base_url}/v1/result/{task_id}",
                timeout=30.0,
            )
            result_response.raise_for_status()
            result_data = result_response.json()
            result_download_end = time.perf_counter()
            result_download_ms = (result_download_end - result_download_start) * 1000

            logger.info(
                "TIMING_docling_result_downloaded",
                stage="docling",
                substage="result_download",
                duration_ms=round(result_download_ms, 2),
                task_id=task_id,
            )

            parse_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

            # Extract document content
            document = result_data.get("document", {})
            text = document.get("md_content", "") or document.get("text_content", "")
            json_content = document.get("json_content", {})

            # Extract markdown content with embedded images (for HTML report generation)
            md_content = document.get("md_content", "")

            # Extract tables from JSON (Feature 21.5)
            tables_data = []
            for table in json_content.get("tables", []):
                table_info = {
                    "ref": table.get("self_ref", ""),
                    "label": table.get("label", "table"),
                    "captions": table.get("captions", []),
                    "page_no": None,
                    "bbox": None,
                }
                # Extract provenance (page number, bounding box)
                prov = table.get("prov", [])
                if prov:
                    p = prov[0] if isinstance(prov, list) else prov
                    table_info["page_no"] = p.get("page_no")
                    table_info["bbox"] = p.get("bbox")
                tables_data.append(table_info)

            # Extract images/pictures from JSON (Feature 21.5)
            images_data = []
            for picture in json_content.get("pictures", []):
                image_info = {
                    "ref": picture.get("self_ref", ""),
                    "label": picture.get("label", "picture"),
                    "captions": picture.get("captions", []),
                    "page_no": None,
                    "bbox": None,
                }
                # Extract provenance
                prov = picture.get("prov", [])
                if prov:
                    p = prov[0] if isinstance(prov, list) else prov
                    image_info["page_no"] = p.get("page_no")
                    image_info["bbox"] = p.get("bbox")
                images_data.append(image_info)

            # Extract layout information (Feature 21.5)
            layout_info = {
                "schema_name": json_content.get("schema_name", ""),
                "version": json_content.get("version", ""),
                "pages": json_content.get("pages", {}),
                "body": json_content.get("body", {}),
                "texts_count": len(json_content.get("texts", [])),
                "groups_count": len(json_content.get("groups", [])),
            }

            # Create DoclingParsedDocument
            parsed = DoclingParsedDocument(
                text=text,
                metadata={
                    "filename": document.get("filename", file_path.name),
                    "schema_name": layout_info["schema_name"],
                    "version": layout_info["version"],
                },
                tables=tables_data,
                images=images_data,
                layout=layout_info,
                parse_time_ms=parse_time,
                json_content=json_content,  # Store full JSON for advanced features (table content, embedded images)
                md_content=md_content,  # Store markdown with embedded base64 images
            )

            # Calculate throughput metrics
            throughput_kb_per_sec = (file_size_bytes / 1024) / (parse_time / 1000) if parse_time > 0 else 0

            logger.info(
                "TIMING_docling_parse_complete",
                stage="docling",
                duration_ms=round(parse_time, 2),
                file_path=str(file_path),
                file_size_bytes=file_size_bytes,
                text_length=len(parsed.text),
                tables_count=len(parsed.tables),
                images_count=len(parsed.images),
                throughput_kb_per_sec=round(throughput_kb_per_sec, 2),
                task_id=task_id,
                timing_breakdown={
                    "file_upload_ms": round(upload_duration_ms, 2),
                    "task_polling_ms": round(polling_duration_ms, 2),
                    "result_download_ms": round(result_download_ms, 2),
                },
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
                str(file_path),
                f"Docling parse failed (HTTP {e.response.status_code}): {e.response.text[:200]}",
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
                str(file_path),
                f"Docling parse timeout after {elapsed/1000:.1f}s (file: {file_path.name})",
            ) from e
        except Exception as e:
            logger.error(
                "docling_parse_error", file_path=str(file_path), error=str(e), exc_info=True
            )
            raise IngestionError(str(file_path), f"Unexpected error parsing document: {e}") from e

    async def parse_batch(self, file_paths: list[Path]) -> list[DoclingParsedDocument]:
        """Parse multiple documents efficiently (batch processing).

        Parses documents sequentially to avoid overwhelming container.
        For true parallel processing, use multiple container instances.

        Args:
            file_paths: list of document file paths

        Returns:
            list of DoclingParsedDocument (same order as input)

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

    async def __aenter__(self) -> None:
        """Async context manager entry: start container."""
        await self.start_container()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
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
        >>> client = DoclingClient()
        >>> await client.start_container()
        >>> parsed1 = await parse_document_with_docling(Path("doc1.pdf"), auto_manage_container=False)
        >>> parsed2 = await parse_document_with_docling(Path("doc2.pdf"), auto_manage_container=False)
        >>> await client.stop_container()
    """
    client = DoclingClient(base_url=base_url)

    if auto_manage_container:
        async with client:
            return await client.parse_document(file_path)
    else:
        return await client.parse_document(file_path)


# =============================================================================
# PRE-WARMED SINGLETON CLIENT (Sprint 33 Performance Optimization)
# =============================================================================

# Global singleton for pre-warmed Docling client
_prewarmed_docling_client: DoclingClient | None = None
_prewarmed_client_lock = asyncio.Lock()


async def prewarm_docling_container(
    base_url: str = "http://localhost:8080",
    timeout_seconds: int = 300,
) -> DoclingClient:
    """Pre-warm Docling container during application startup.

    Sprint 33 Performance Fix: Save 5-10s per document by keeping container warm.

    This function should be called during FastAPI lifespan initialization to
    ensure the Docling container is ready before processing any documents.

    Args:
        base_url: Docling container HTTP endpoint
        timeout_seconds: HTTP request timeout for large files

    Returns:
        Pre-warmed DoclingClient instance

    Example:
        >>> # In FastAPI lifespan:
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        ...     client = await prewarm_docling_container()
        ...     yield
        ...     await shutdown_docling_container()

    Note:
        - Container stays running until shutdown_docling_container() called
        - Use get_prewarmed_docling_client() to get the singleton instance
        - This eliminates 5-10s startup overhead per document
    """
    global _prewarmed_docling_client

    async with _prewarmed_client_lock:
        if _prewarmed_docling_client is not None and _prewarmed_docling_client._container_running:
            logger.info("docling_prewarm_skipped", reason="already_running")
            return _prewarmed_docling_client

        logger.info("docling_prewarm_starting", base_url=base_url)
        prewarm_start = time.time()

        _prewarmed_docling_client = DoclingClient(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )

        try:
            await _prewarmed_docling_client.start_container()
            prewarm_duration = time.time() - prewarm_start

            logger.info(
                "docling_prewarm_complete",
                duration_seconds=round(prewarm_duration, 2),
                status="ready",
            )

            return _prewarmed_docling_client

        except Exception as e:
            logger.error(
                "docling_prewarm_failed",
                error=str(e),
                duration_seconds=round(time.time() - prewarm_start, 2),
            )
            _prewarmed_docling_client = None
            raise


def get_prewarmed_docling_client() -> DoclingClient | None:
    """Get pre-warmed Docling client singleton (or None if not pre-warmed).

    Sprint 33 Performance Fix: Use this in ingestion pipeline to avoid
    container startup overhead.

    Returns:
        Pre-warmed DoclingClient instance, or None if not initialized

    Example:
        >>> client = get_prewarmed_docling_client()
        >>> if client is None:
        ...     # Fall back to creating new client
        ...     client = DoclingClient()
        ...     await client.start_container()

    Note:
        - Returns None if prewarm_docling_container() was not called
        - Returns None if container failed to start
        - Thread-safe (uses module-level singleton)
    """
    return _prewarmed_docling_client


def is_docling_container_prewarmed() -> bool:
    """Check if Docling container is pre-warmed and ready.

    Returns:
        True if container is pre-warmed and running, False otherwise
    """
    return (
        _prewarmed_docling_client is not None
        and _prewarmed_docling_client._container_running
    )


async def shutdown_docling_container() -> None:
    """Shutdown pre-warmed Docling container during application shutdown.

    This should be called in FastAPI lifespan cleanup to properly stop
    the container and free VRAM.

    Example:
        >>> # In FastAPI lifespan:
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        ...     await prewarm_docling_container()
        ...     yield
        ...     await shutdown_docling_container()
    """
    global _prewarmed_docling_client

    async with _prewarmed_client_lock:
        if _prewarmed_docling_client is None:
            logger.info("docling_shutdown_skipped", reason="not_running")
            return

        try:
            logger.info("docling_shutdown_starting")
            await _prewarmed_docling_client.stop_container()
            logger.info("docling_shutdown_complete", status="stopped")
        except Exception as e:
            logger.error("docling_shutdown_error", error=str(e))
        finally:
            _prewarmed_docling_client = None


# ============================================================================
# Backward Compatibility Alias (Sprint 25 Feature 25.9)
# ============================================================================
# Deprecation period: Sprint 25-26
DoclingContainerClient = DoclingClient
