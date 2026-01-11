"""Document Parsing Nodes for LangGraph Ingestion Pipeline.

Sprint 54 Feature 54.3: Extracted from langgraph_nodes.py

This module handles document parsing using either:
- Docling CUDA container (GPU-accelerated, for PDF/DOCX/PPTX)
- LlamaIndex SimpleDirectoryReader (for exclusive formats)

Nodes:
- docling_extraction_node: Primary parser with CUDA acceleration
- docling_parse_node: Backward compatibility alias for docling_extraction_node
- llamaindex_parse_node: Fallback for LlamaIndex-exclusive formats
"""

import time
from contextlib import suppress
from pathlib import Path

import structlog

from src.components.ingestion.docling_client import DoclingContainerClient
from src.components.ingestion.ingestion_state import (
    IngestionState,
    add_error,
    calculate_progress,
)
from src.components.ingestion.logging_utils import log_memory_snapshot, log_phase_summary
from src.core.exceptions import IngestionError

logger = structlog.get_logger(__name__)


async def docling_extraction_node(state: IngestionState) -> IngestionState:
    """Node 2: Parse document with Docling CUDA container + extract BBox (Feature 21.6).

    Workflow:
    1. Start Docling container (if not running or restart required)
    2. Parse document via HTTP API
    3. Stop container (free VRAM for next stage)
    4. Store parsed content in state

    Args:
        state: Current ingestion state

    Returns:
        Updated state with parsed document

    Raises:
        IngestionError: If parsing fails

    Example:
        >>> state = await docling_parse_node(state)
        >>> len(state["parsed_content"])
        15000  # 15KB of parsed text
        >>> state["docling_status"]
        'completed'
    """
    docling_node_start = time.perf_counter()

    logger.info(
        "node_docling_start",
        document_id=state["document_id"],
        document_path=state["document_path"],
    )

    state["docling_status"] = "running"
    state["docling_start_time"] = time.time()

    # Sprint 83 Feature 83.1: Log memory snapshot before Docling processing
    import psutil
    process = psutil.Process()
    mem_info = process.memory_info()
    log_memory_snapshot(
        phase="docling_start",
        ram_used_mb=mem_info.rss // (1024**2),
        ram_available_mb=psutil.virtual_memory().available // (1024**2),
    )

    try:
        # Get document path
        doc_path = Path(state["document_path"])

        if not doc_path.exists():
            raise IngestionError(
                document_id=state.get("document_id", "unknown"),
                reason=f"Document not found: {doc_path}",
            )

        # Sprint 33 Performance Fix: Use pre-warmed Docling client if available
        from src.components.ingestion.docling_client import (
            get_prewarmed_docling_client,
            is_docling_container_prewarmed,
        )
        from src.core.config import settings

        # Check if we have a pre-warmed client (saves 5-10s per document)
        prewarmed_client = get_prewarmed_docling_client()
        use_prewarmed = prewarmed_client is not None and is_docling_container_prewarmed()
        should_stop_container = not use_prewarmed  # Only stop if we started it

        if use_prewarmed:
            logger.info(
                "docling_using_prewarmed_container",
                document_id=state["document_id"],
                startup_time_saved="5-10s",
            )
            docling = prewarmed_client
        else:
            # Fallback: Create new client (old behavior)
            logger.info(
                "docling_creating_new_client",
                document_id=state["document_id"],
                reason="no_prewarmed_container",
            )
            docling = DoclingContainerClient(
                base_url=settings.docling_base_url,
                timeout_seconds=settings.docling_timeout_seconds,
                max_retries=settings.docling_max_retries,
            )

            # Start container (or restart if memory leak detected)
            if state.get("requires_container_restart", False):
                logger.info("docling_container_restart", reason="vram_leak")
                # Stop any existing container first (suppress errors if container not running)
                with suppress(Exception):
                    await docling.stop_container()

            await docling.start_container()

        try:
            # Parse document
            parsed = await docling.parse_document(doc_path)

            # Sprint 33 Fix (TD-044): DoclingParsedDocument now has .document property
            # All formats use unified code path
            state["document"] = parsed.document  # Works for all formats

            # Sprint 68 Feature 68.3: Explicit memory cleanup after parsing
            # Release intermediate parsing data structures to reduce memory footprint
            import gc

            gc.collect()  # Trigger garbage collection to free parsing buffers

            # Extract page dimensions from json_content if available
            # Sprint 33 Fix (TD-044): Docling API pages is ALWAYS a dict {"1": PageItem, "2": PageItem}
            # Schema: additionalProperties with $ref to PageItem (page_no: int, size: {width, height})
            page_dimensions = {}
            pages_data = parsed.json_content.get("pages", {}) if parsed.json_content else {}

            # Pages is a dict: {"1": {"page_no": 1, "size": {...}}, "2": {...}}
            for page_key, page_info in pages_data.items():
                if isinstance(page_info, dict):
                    # page_no from PageItem, fallback to dict key as int
                    page_no = page_info.get(
                        "page_no", int(page_key) if page_key.isdigit() else None
                    )
                    size = page_info.get("size", {})
                    if page_no is not None and size:
                        page_dimensions[page_no] = {
                            "width": size.get("width", 0),
                            "height": size.get("height", 0),
                            "unit": "pt",
                            "dpi": 72,
                        }

            logger.info(
                "docling_document_processed",
                document_id=state["document_id"],
                has_body=parsed.body is not None,
                pages_count=len(page_dimensions),
            )

            state["page_dimensions"] = page_dimensions  # Feature 21.6: Page metadata
            state["parsed_content"] = parsed.text  # Keep for backwards compatibility
            state["parsed_metadata"] = parsed.metadata
            state["parsed_tables"] = parsed.tables
            state["parsed_images"] = parsed.images
            state["parsed_layout"] = parsed.layout
            state["docling_status"] = "completed"

            logger.info(
                "node_docling_parsed",
                document_id=state["document_id"],
                text_length=len(parsed.text),
                tables_count=len(parsed.tables),
                images_count=len(parsed.images),
                pages_count=len(page_dimensions),
                parse_time_ms=parsed.parse_time_ms,
            )

            # Sprint 33: Removed verbose raw_text_complete logging (caused Unicode errors on Windows)
            # Text length is logged above in node_docling_parsed
            logger.debug(
                "docling_raw_text_available",
                document_id=state["document_id"],
                raw_text_length=len(parsed.text),
                first_100_chars=parsed.text[:100].encode("ascii", errors="replace").decode("ascii"),
            )

        finally:
            # Sprint 33 Performance Fix: Only stop container if we started it ourselves
            # Pre-warmed containers stay running for subsequent documents
            if should_stop_container:
                await docling.stop_container()
                logger.info("docling_container_stopped", vram_freed="~6GB")
            else:
                logger.info(
                    "docling_container_kept_running",
                    reason="prewarmed_container",
                    vram_note="Container stays warm for next document",
                )

        state["docling_end_time"] = time.time()
        state["overall_progress"] = calculate_progress(state)

        docling_node_end = time.perf_counter()
        total_docling_ms = (docling_node_end - docling_node_start) * 1000

        logger.info(
            "node_docling_complete",
            document_id=state["document_id"],
            duration_seconds=round(state["docling_end_time"] - state["docling_start_time"], 2),
        )

        # Sprint 83 Feature 83.1: Log Docling phase summary with memory metrics
        log_phase_summary(
            phase="docling_extraction",
            total_time_ms=total_docling_ms,
            items_processed=1,  # 1 document parsed
            pages_extracted=len(page_dimensions),
            tables_count=len(parsed.tables),
            images_count=len(parsed.images),
        )

        # Sprint 83 Feature 83.1: Log memory snapshot after Docling processing
        mem_info = process.memory_info()
        log_memory_snapshot(
            phase="docling_complete",
            ram_used_mb=mem_info.rss // (1024**2),
            ram_available_mb=psutil.virtual_memory().available // (1024**2),
        )

        return state

    except Exception as e:
        logger.error("node_docling_error", document_id=state["document_id"], error=str(e))
        add_error(state, "docling", str(e), "error")
        state["docling_status"] = "failed"
        state["docling_end_time"] = time.time()
        raise


# Backward compatibility alias (deprecated, use docling_extraction_node)
async def docling_parse_node(state: IngestionState) -> IngestionState:
    """DEPRECATED: Use docling_extraction_node instead.

    This alias exists for backward compatibility with existing pipelines.
    """
    return await docling_extraction_node(state)


async def llamaindex_parse_node(state: IngestionState) -> IngestionState:
    """Node 2B: Parse document using LlamaIndex SimpleDirectoryReader (Feature 22.4).

    ============================================================================
    Sprint 24 Feature 24.15: LAZY IMPORT for llama_index
    ============================================================================
    WHY: llama_index is now in optional "ingestion" dependency group (ADR-028)
    WHEN: Import happens on first call to this function (not at module load)
    INSTALL: poetry install --with ingestion
    ============================================================================

    Supports 9 LlamaIndex-exclusive formats:
    - .epub (E-books)
    - .rtf (Rich Text Format)
    - .tex (LaTeX documents)
    - .md (Markdown)
    - .rst (reStructuredText)
    - .adoc (AsciiDoc)
    - .org (Org-Mode)
    - .odt (OpenDocument Text)
    - .msg (Outlook messages)

    Architecture:
    - Uses SimpleDirectoryReader for broad format support
    - Parser-agnostic output (compatible with ParsedDocument model)
    - Text-only parsing (no image/table extraction)
    - Graceful error handling with informative messages

    Args:
        state: Current ingestion state with document_path

    Returns:
        Updated state with parsed_document fields:
        - parsed_content: Extracted text content (combined from all pages)
        - parsed_metadata: Document metadata (format, parser, page_count)
        - parsed_tables: Empty list (LlamaIndex basic parsing)
        - parsed_images: Empty list (no image extraction)
        - parsed_layout: Empty dict (no layout analysis)
        - docling_status: 'completed' (reused for consistency)

    Raises:
        IngestionError: If parsing fails
        ValueError: If format not supported by LlamaIndex
        ImportError: If llama_index not installed

    Example:
        >>> state = await llamaindex_parse_node(state)
        >>> len(state["parsed_content"])
        5000  # 5KB of parsed text
        >>> state["parsed_metadata"]["parser"]
        'llamaindex'
    """
    logger.info(
        "node_llamaindex_start",
        document_id=state["document_id"],
        document_path=state["document_path"],
    )

    state["docling_status"] = "running"
    state["docling_start_time"] = time.time()

    # ========================================================================
    # LAZY IMPORT: llama_index (Sprint 24 Feature 24.15)
    # ========================================================================
    # Load llama_index only when this LlamaIndex-specific node is called.
    # This allows the core application to run without llama_index installed.
    # ========================================================================
    try:
        from llama_index.core import SimpleDirectoryReader
    except ImportError as e:
        error_msg = (
            "llama_index is required for LlamaIndex parsing but is not installed.\n\n"
            "INSTALLATION OPTIONS:\n"
            "1. poetry install --with ingestion\n"
            "2. poetry install --all-extras\n\n"
            "NOTE: This node is only needed for LlamaIndex-exclusive formats (.epub, .rtf, .tex, etc.).\n"
            "For PDF/DOCX/PPTX, use docling_extraction_node instead."
        )
        logger.error(
            "llamaindex_import_failed",
            document_id=state["document_id"],
            error=str(e),
            install_command="poetry install --with ingestion",
        )
        raise ImportError(error_msg) from e

    try:
        # Get document path
        doc_path = Path(state["document_path"])

        if not doc_path.exists():
            raise IngestionError(
                document_id=state["document_id"], reason=f"Document not found: {doc_path}"
            )

        # Validate format is supported
        file_extension = doc_path.suffix.lower()
        from src.components.ingestion.format_router import LLAMAINDEX_EXCLUSIVE, SHARED_FORMATS

        supported_formats = LLAMAINDEX_EXCLUSIVE | SHARED_FORMATS
        if file_extension not in supported_formats:
            raise ValueError(
                f"Format {file_extension} not supported by LlamaIndex. "
                f"Supported formats: {', '.join(sorted(supported_formats))}"
            )

        logger.info(
            "llamaindex_parsing_started",
            document_id=state["document_id"],
            format=file_extension,
        )

        try:
            # Use SimpleDirectoryReader for broad format support
            reader = SimpleDirectoryReader(
                input_files=[str(doc_path)],
                filename_as_id=True,
            )

            # Load document
            llama_documents = reader.load_data()

            if not llama_documents:
                raise ValueError(f"LlamaIndex returned no documents for {doc_path}")

            # Extract text content (combine all pages/sections)
            full_text = "\n\n".join(doc.text for doc in llama_documents)

            # Extract metadata (from first document)
            base_metadata = llama_documents[0].metadata if llama_documents else {}

            # Create comprehensive metadata
            metadata = {
                "source": str(doc_path),
                "format": file_extension,
                "parser": "llamaindex",
                "page_count": len(llama_documents),
                **base_metadata,
            }

            # Store in state (same format as Docling for compatibility)
            state["document"] = None  # No DoclingDocument object
            state["page_dimensions"] = {}  # No page dimensions
            state["parsed_content"] = full_text
            state["parsed_metadata"] = metadata
            state["parsed_tables"] = []  # LlamaIndex basic parsing doesn't extract tables
            state["parsed_images"] = []  # No image extraction
            state["parsed_layout"] = {}  # No layout analysis
            state["docling_status"] = "completed"

            logger.info(
                "llamaindex_parsing_completed",
                document_id=state["document_id"],
                text_length=len(full_text),
                page_count=len(llama_documents),
                format=file_extension,
            )

        except ValueError as e:
            if "No reader found" in str(e):
                logger.error(
                    "llamaindex_unsupported_format",
                    document_id=state["document_id"],
                    format=file_extension,
                    error=str(e),
                )
                raise ValueError(
                    f"Format {file_extension} not supported by LlamaIndex. "
                    f"Supported formats: {', '.join(sorted(supported_formats))}"
                ) from e
            raise

        state["docling_end_time"] = time.time()
        state["overall_progress"] = calculate_progress(state)

        logger.info(
            "node_llamaindex_complete",
            document_id=state["document_id"],
            duration_seconds=round(state["docling_end_time"] - state["docling_start_time"], 2),
        )

        return state

    except Exception as e:
        logger.error("node_llamaindex_error", document_id=state["document_id"], error=str(e))
        add_error(state, "llamaindex", str(e), "error")
        state["docling_status"] = "failed"
        state["docling_end_time"] = time.time()
        raise
