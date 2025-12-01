"""LangGraph Ingestion Pipeline Nodes - Sprint 21 Feature 21.6.

This module implements the 6 nodes of the image-enhanced LangGraph ingestion pipeline:

1. memory_check_node       → Check RAM/VRAM availability
2. docling_parse_node      → Parse document with Docling, extract BBox + page dimensions
3. image_enrichment_node   → Qwen3-VL image descriptions (NEW - Feature 21.6)
4. chunking_node          → HybridChunker with BGE-M3, map BBox to chunks
5. embedding_node         → Generate BGE-M3 vectors → Qdrant with full provenance
6. graph_extraction_node  → Extract entities/relations → Neo4j with minimal provenance

Architecture:
  Each node is an async function that:
  - Takes IngestionState as input
  - Performs one specific operation
  - Updates state fields
  - Returns updated IngestionState

Memory Management (Critical):
  - Sequential execution (one node at a time)
  - Docling container start/stop to free VRAM
  - RAM/VRAM monitoring before each stage
  - Container restart if VRAM >5GB (memory leak)

Example:
    >>> state = create_initial_state(...)
    >>> state = await memory_check_node(state)
    >>> state = await docling_parse_node(state)
    >>> state = await chunking_node(state)
    >>> state = await embedding_node(state)
    >>> state = await graph_extraction_node(state)
"""

import asyncio
import subprocess
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.components.ingestion.docling_client import DoclingContainerClient
from src.components.ingestion.image_processor import ImageProcessor
from src.components.ingestion.ingestion_state import (
    IngestionState,
    add_error,
    calculate_progress,
)
from src.components.shared.embedding_service import get_embedding_service
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.chunk import ChunkStrategy
from src.core.chunking_service import get_chunking_service
from src.core.config import settings
from src.core.exceptions import IngestionError

logger = structlog.get_logger(__name__)


# =============================================================================
# DATACLASSES: SECTION METADATA & ADAPTIVE CHUNKS (Feature 32.1, 32.2)
# =============================================================================


@dataclass
class SectionMetadata:
    """Section metadata extracted from Docling JSON (Feature 32.1).

    Represents a document section with hierarchical heading structure,
    bounding box coordinates, and token count for adaptive chunking.

    Attributes:
        heading: Section heading text (e.g., "Multi-Server Architecture")
        level: Heading level (1 = title, 2 = subtitle-level-1, 3 = subtitle-level-2)
        page_no: Page number where section starts
        bbox: Bounding box coordinates {"l": left, "t": top, "r": right, "b": bottom}
        text: Section body text (accumulated from cells)
        token_count: Number of tokens in section text
        metadata: Additional metadata (source, file_type, etc.)
    """

    heading: str
    level: int
    page_no: int
    bbox: dict[str, float]
    text: str
    token_count: int
    metadata: dict[str, Any]


@dataclass
class AdaptiveChunk:
    """Chunk with multi-section metadata (Feature 32.2).

    Created by adaptive_section_chunking() to merge small sections
    intelligently while preserving provenance chain.

    Attributes:
        text: Merged text from all sections
        token_count: Total tokens in chunk
        section_headings: List of all section headings in chunk
        section_pages: List of page numbers for each section
        section_bboxes: List of bounding boxes for each section
        primary_section: First section heading (main topic)
        metadata: Additional metadata (source, file_type, num_sections)
    """

    text: str
    token_count: int
    section_headings: list[str]
    section_pages: list[int]
    section_bboxes: list[dict[str, float]]
    primary_section: str
    metadata: dict[str, Any]


# =============================================================================
# ADAPTIVE SECTION CHUNKING (Feature 32.2)
# =============================================================================


def adaptive_section_chunking(
    sections: list[SectionMetadata],
    min_chunk: int = 800,
    max_chunk: int = 1800,
    large_section_threshold: int = 1200,
) -> list[AdaptiveChunk]:
    """Chunk with section-awareness, merging small sections intelligently (Feature 32.2).

    Implements ADR-039 adaptive section-aware chunking strategy:
    - Large sections (>1200 tokens) → Keep as standalone chunks
    - Small sections (<1200 tokens) → Merge until 800-1800 tokens
    - Track ALL sections in chunk metadata (multi-section support)
    - Preserve thematic coherence when merging

    Args:
        sections: List of SectionMetadata from extract_section_hierarchy()
        min_chunk: Minimum tokens per chunk (default 800)
        max_chunk: Maximum tokens per chunk (default 1800)
        large_section_threshold: Threshold for standalone sections (default 1200)

    Returns:
        List of AdaptiveChunk with multi-section metadata

    Example:
        >>> sections = extract_section_hierarchy(docling_json)
        >>> chunks = adaptive_section_chunking(sections)
        >>> # PowerPoint (15 slides @ 150-250 tokens) → 6-8 chunks
        >>> len(chunks)
        7
        >>> chunks[0].section_headings
        ['Multi-Server Architecture', 'Load Balancing', 'Caching']
    """
    if not sections:
        return []

    chunks = []
    current_sections = []
    current_tokens = 0

    for section in sections:
        section_tokens = section.token_count

        # Large section → standalone chunk (preserve clean extraction)
        if section_tokens > large_section_threshold:
            # Flush any accumulated small sections first
            if current_sections:
                chunks.append(_merge_sections(current_sections))
                current_sections = []
                current_tokens = 0

            # Create standalone chunk for large section
            chunks.append(_create_chunk(section))

        # Small section → merge with others (reduce fragmentation)
        elif current_tokens + section_tokens <= max_chunk:
            current_sections.append(section)
            current_tokens += section_tokens

        # Current batch full → flush and start new
        else:
            chunks.append(_merge_sections(current_sections))
            current_sections = [section]
            current_tokens = section_tokens

    # Flush remaining sections
    if current_sections:
        chunks.append(_merge_sections(current_sections))

    logger.info(
        "adaptive_section_chunking_complete",
        sections_count=len(sections),
        chunks_count=len(chunks),
        avg_sections_per_chunk=round(len(sections) / len(chunks), 2) if chunks else 0,
        min_chunk=min_chunk,
        max_chunk=max_chunk,
        large_section_threshold=large_section_threshold,
    )

    return chunks


def _merge_sections(sections: list[SectionMetadata]) -> AdaptiveChunk:
    """Merge multiple sections into one chunk with multi-section metadata.

    Args:
        sections: List of sections to merge (must be non-empty)

    Returns:
        AdaptiveChunk with merged text and multi-section metadata

    Example:
        >>> sections = [
        ...     SectionMetadata(heading="Architecture", text="...", token_count=400, ...),
        ...     SectionMetadata(heading="Load Balancing", text="...", token_count=350, ...),
        ... ]
        >>> chunk = _merge_sections(sections)
        >>> chunk.section_headings
        ['Architecture', 'Load Balancing']
        >>> chunk.token_count
        750
    """
    if not sections:
        raise ValueError("Cannot merge empty sections list")

    return AdaptiveChunk(
        text="\n\n".join(s.text for s in sections),
        token_count=sum(s.token_count for s in sections),
        section_headings=[s.heading for s in sections],
        section_pages=[s.page_no for s in sections],
        section_bboxes=[s.bbox for s in sections],
        primary_section=sections[0].heading,
        metadata={
            "source": sections[0].metadata.get("source", ""),
            "file_type": sections[0].metadata.get("file_type", ""),
            "num_sections": len(sections),
        },
    )


def _create_chunk(section: SectionMetadata) -> AdaptiveChunk:
    """Create chunk from single section (large section → standalone).

    Args:
        section: Section to convert to chunk

    Returns:
        AdaptiveChunk with single section metadata

    Example:
        >>> section = SectionMetadata(heading="Introduction", text="...", token_count=1500, ...)
        >>> chunk = _create_chunk(section)
        >>> chunk.section_headings
        ['Introduction']
        >>> chunk.token_count
        1500
    """
    return AdaptiveChunk(
        text=section.text,
        token_count=section.token_count,
        section_headings=[section.heading],
        section_pages=[section.page_no],
        section_bboxes=[section.bbox],
        primary_section=section.heading,
        metadata={
            "source": section.metadata.get("source", ""),
            "file_type": section.metadata.get("file_type", ""),
            "num_sections": 1,
        },
    )


# =============================================================================
# NODE 1: MEMORY CHECK
# =============================================================================


async def memory_check_node(state: IngestionState) -> IngestionState:
    """Node 1: Check memory availability (RAM + VRAM).

    Checks:
    - System RAM usage (target: <4.4GB available)
    - GPU VRAM usage (target: <5.5GB, restart if >5.5GB)

    Args:
        state: Current ingestion state

    Returns:
        Updated state with memory check results

    Raises:
        IngestionError: If insufficient memory (RAM <2GB or VRAM unavailable)

    Example:
        >>> state = await memory_check_node(state)
        >>> state["memory_check_passed"]
        True
        >>> state["current_memory_mb"]
        3200.0  # 3.2GB RAM used
    """
    logger.info(
        "node_memory_check_start",
        document_id=state["document_id"],
        batch_index=state["batch_index"],
    )

    try:
        # Check system RAM usage (psutil) - graceful degradation if unavailable
        try:
            import psutil

            memory = psutil.virtual_memory()
            ram_used_mb = memory.used / 1024 / 1024
            ram_available_mb = memory.available / 1024 / 1024

            state["current_memory_mb"] = ram_used_mb

            logger.info(
                "memory_check_ram",
                ram_used_mb=round(ram_used_mb, 2),
                ram_available_mb=round(ram_available_mb, 2),
            )

            # Check if sufficient memory available
            # Sprint 30: Lowered to 500MB for small PDF testing (production should use 2000MB minimum)
            # TODO: Make threshold configurable via settings.min_required_ram_mb
            if ram_available_mb < 500:  # Less than 500MB RAM available
                raise IngestionError(
                    document_id=state["document_id"],
                    reason=f"Insufficient RAM: Only {ram_available_mb:.0f}MB available (need 500MB)",
                )

        except ImportError:
            # psutil not available (common in Uvicorn reloader subprocess on Windows)
            logger.warning(
                "psutil_unavailable",
                note="Skipping RAM check (psutil not available in subprocess)",
            )
            state["current_memory_mb"] = 0.0

        # Check GPU VRAM usage (nvidia-smi)
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                check=True,
            )
            vram_used_mb = float(result.stdout.strip())
            state["current_vram_mb"] = vram_used_mb

            logger.info("memory_check_vram", vram_used_mb=round(vram_used_mb, 2))

            # Check for memory leak (>5.5GB indicates leak from previous batch)
            if vram_used_mb > 5500:
                logger.warning(
                    "vram_leak_detected",
                    vram_used_mb=vram_used_mb,
                    threshold_mb=5500,
                    action="container_restart_required",
                )
                state["requires_container_restart"] = True
                add_error(
                    state,
                    "memory_check",
                    f"VRAM leak detected: {vram_used_mb:.0f}MB (>5.5GB threshold)",
                    "warning",
                )

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning("nvidia_smi_unavailable", error=str(e))
            state["current_vram_mb"] = 0.0  # GPU not available or nvidia-smi not found
            state["requires_container_restart"] = False

        # Mark check as passed (even if psutil unavailable)
        state["memory_check_passed"] = True
        state["overall_progress"] = calculate_progress(state)

        logger.info(
            "node_memory_check_complete",
            document_id=state["document_id"],
            memory_check_passed=True,
            requires_restart=state.get("requires_container_restart", False),
        )

        return state

    except IngestionError:
        # Re-raise IngestionError (insufficient RAM)
        raise
    except Exception as e:
        logger.error("node_memory_check_error", document_id=state["document_id"], error=str(e))
        add_error(state, "memory_check", str(e), "error")
        state["memory_check_passed"] = False
        raise


# =============================================================================
# NODE 2: DOCLING PARSING
# =============================================================================


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
    logger.info(
        "node_docling_start",
        document_id=state["document_id"],
        document_path=state["document_path"],
    )

    state["docling_status"] = "running"
    state["docling_start_time"] = time.time()

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

            # Extract page dimensions from json_content if available
            # Sprint 33 Fix (TD-044): Docling API pages is ALWAYS a dict {"1": PageItem, "2": PageItem}
            # Schema: additionalProperties with $ref to PageItem (page_no: int, size: {width, height})
            page_dimensions = {}
            pages_data = parsed.json_content.get("pages", {}) if parsed.json_content else {}

            # Pages is a dict: {"1": {"page_no": 1, "size": {...}}, "2": {...}}
            for page_key, page_info in pages_data.items():
                if isinstance(page_info, dict):
                    # page_no from PageItem, fallback to dict key as int
                    page_no = page_info.get("page_no", int(page_key) if page_key.isdigit() else None)
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

        logger.info(
            "node_docling_complete",
            document_id=state["document_id"],
            duration_seconds=round(state["docling_end_time"] - state["docling_start_time"], 2),
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


# =============================================================================
# NODE 2B: LLAMAINDEX PARSING (Sprint 22 Feature 22.4)
# =============================================================================


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


# =============================================================================
# NODE 2.5: VLM IMAGE ENRICHMENT (Feature 21.6)
# =============================================================================


async def image_enrichment_node(state: IngestionState) -> IngestionState:
    """Node 2.5: VLM Image Enrichment (Feature 21.6).

    CRITICAL: VLM-Text wird IN DoclingDocument eingefügt!

    Workflow:
    1. Get DoclingDocument from state
    2. For each picture_item in document.pictures:
       a. Filter image (size, aspect ratio)
       b. Extract BBox with page context
       c. Generate VLM description
       d. INSERT description INTO picture_item.text
       e. Store VLM metadata with enhanced BBox
    3. Update state with enriched document + VLM metadata

    Args:
        state: Current ingestion state

    Returns:
        Updated state with enriched document

    Raises:
        IngestionError: If enrichment fails critically

    Example:
        >>> state = await image_enrichment_node(state)
        >>> len(state["vlm_metadata"])
        5  # 5 images processed
        >>> state["enrichment_status"]
        'completed'
    """
    logger.info("node_vlm_enrichment_start", document_id=state["document_id"])

    state["enrichment_status"] = "running"

    try:
        # 1. Get DoclingDocument
        doc = state.get("document")
        if doc is None:
            logger.warning(
                "vlm_enrichment_skipped",
                document_id=state["document_id"],
                reason="no_docling_document",
            )
            state["enrichment_status"] = "skipped"
            state["vlm_metadata"] = []
            state["overall_progress"] = calculate_progress(state)
            return state

        page_dimensions = state.get("page_dimensions", {})
        vlm_metadata = []

        # 2. Initialize ImageProcessor
        processor = ImageProcessor()

        try:
            # 3. Process each picture - Sprint 33 Performance: Parallel VLM Processing
            pictures_count = len(doc.pictures) if hasattr(doc, "pictures") else 0
            logger.info("vlm_processing_start", pictures_total=pictures_count)

            if pictures_count == 0:
                logger.info(
                    "vlm_enrichment_skipped",
                    document_id=state["document_id"],
                    reason="no_pictures",
                )
                state["enrichment_status"] = "skipped"
                state["vlm_metadata"] = []
                state["overall_progress"] = calculate_progress(state)
                return state

            # Sprint 33 Performance Fix: Parallelize VLM image processing (5-10x speedup)
            # Maximum concurrent VLM calls to avoid overwhelming the API
            try:
                from src.core.config import settings

                MAX_CONCURRENT_VLM = settings.ingestion_max_concurrent_vlm
            except Exception:
                MAX_CONCURRENT_VLM = 5  # Conservative default

            vlm_start_time = time.time()

            # Step 3a: Prepare all images with their metadata (synchronous)
            image_tasks_data = []
            for idx, picture_item in enumerate(doc.pictures):
                try:
                    # Get PIL image
                    pil_image = picture_item.get_image()

                    # Extract enhanced BBox (if available)
                    enhanced_bbox = None
                    if hasattr(picture_item, "prov") and picture_item.prov:
                        prov = picture_item.prov[0]
                        page_no = prov.page_no
                        page_dim = page_dimensions.get(page_no, {})

                        if page_dim:
                            page_width = page_dim.get("width", 1)
                            page_height = page_dim.get("height", 1)

                            enhanced_bbox = {
                                "bbox_absolute": {
                                    "left": prov.bbox.l,
                                    "top": prov.bbox.t,
                                    "right": prov.bbox.r,
                                    "bottom": prov.bbox.b,
                                },
                                "page_context": {
                                    "page_no": page_no,
                                    "page_width": page_width,
                                    "page_height": page_height,
                                    "unit": "pt",
                                    "dpi": 72,
                                    "coord_origin": prov.bbox.coord_origin.value,
                                },
                                "bbox_normalized": {
                                    "left": prov.bbox.l / page_width,
                                    "top": prov.bbox.t / page_height,
                                    "right": prov.bbox.r / page_width,
                                    "bottom": prov.bbox.b / page_height,
                                },
                            }

                    image_tasks_data.append({
                        "idx": idx,
                        "picture_item": picture_item,
                        "pil_image": pil_image,
                        "enhanced_bbox": enhanced_bbox,
                    })

                except Exception as e:
                    logger.warning(
                        "vlm_image_preparation_error",
                        picture_index=idx,
                        error=str(e),
                        action="skipping_image",
                    )
                    continue

            logger.info(
                "vlm_parallel_processing_prepared",
                images_prepared=len(image_tasks_data),
                images_total=pictures_count,
                max_concurrent=MAX_CONCURRENT_VLM,
            )

            # Step 3b: Process images in parallel batches using asyncio.Semaphore
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_VLM)

            async def process_single_image(task_data: dict) -> dict | None:
                """Process single image with semaphore concurrency control."""
                async with semaphore:
                    idx = task_data["idx"]
                    pil_image = task_data["pil_image"]
                    enhanced_bbox = task_data["enhanced_bbox"]

                    try:
                        description = await processor.process_image(
                            image=pil_image,
                            picture_index=idx,
                        )

                        if description is None:
                            logger.debug(
                                "vlm_image_filtered",
                                picture_index=idx,
                                reason="failed_filter_check",
                            )
                            return None

                        return {
                            "idx": idx,
                            "description": description,
                            "enhanced_bbox": enhanced_bbox,
                        }

                    except Exception as e:
                        logger.warning(
                            "vlm_image_processing_error",
                            picture_index=idx,
                            error=str(e),
                            action="skipping_image",
                        )
                        return None

            # Execute all VLM tasks in parallel (bounded by semaphore)
            vlm_tasks = [process_single_image(data) for data in image_tasks_data]
            vlm_results = await asyncio.gather(*vlm_tasks, return_exceptions=True)

            # Step 3c: Process results and update DoclingDocument
            for task_data, result in zip(image_tasks_data, vlm_results):
                # Handle exceptions from gather
                if isinstance(result, Exception):
                    logger.warning(
                        "vlm_parallel_task_exception",
                        picture_index=task_data["idx"],
                        error=str(result),
                    )
                    continue

                if result is None:
                    continue

                idx = result["idx"]
                description = result["description"]
                enhanced_bbox = result["enhanced_bbox"]
                picture_item = task_data["picture_item"]

                # INSERT INTO DoclingDocument (CRITICAL!)
                if hasattr(picture_item, "caption") and picture_item.caption:
                    picture_item.text = f"{picture_item.caption}\n\n{description}"
                else:
                    picture_item.text = description

                # Store VLM metadata
                vlm_metadata.append(
                    {
                        "picture_index": idx,
                        "picture_ref": f"#/pictures/{idx}",
                        "description": description,
                        "bbox_full": enhanced_bbox,
                        "vlm_model": "qwen3-vl:4b-instruct",
                        "timestamp": time.time(),
                    }
                )

                logger.debug(
                    "vlm_image_processed",
                    picture_index=idx,
                    description_length=len(description),
                    has_bbox=enhanced_bbox is not None,
                )

            vlm_duration = time.time() - vlm_start_time
            logger.info(
                "vlm_parallel_processing_complete",
                images_total=pictures_count,
                images_processed=len(vlm_metadata),
                duration_seconds=round(vlm_duration, 2),
                images_per_second=round(len(vlm_metadata) / vlm_duration, 2) if vlm_duration > 0 else 0,
                max_concurrent=MAX_CONCURRENT_VLM,
            )

        finally:
            # Cleanup temp files
            processor.cleanup()

        # 4. Update state
        state["document"] = doc  # Enriched document
        state["vlm_metadata"] = vlm_metadata
        state["enrichment_status"] = "completed"
        state["overall_progress"] = calculate_progress(state)

        logger.info(
            "node_vlm_enrichment_complete",
            document_id=state["document_id"],
            images_processed=len(vlm_metadata),
            images_total=pictures_count,
        )

        return state

    except Exception as e:
        logger.error("node_vlm_enrichment_error", document_id=state["document_id"], error=str(e))
        add_error(state, "vlm_enrichment", str(e), "warning")
        state["enrichment_status"] = "failed"
        state["vlm_metadata"] = []
        # Don't raise - allow pipeline to continue without VLM enrichment
        return state


# =============================================================================
# NODE 3: CHUNKING
# =============================================================================


def merge_small_chunks(
    enhanced_chunks: list[dict],
    tokenizer,
    target_tokens: int = 1800,
    min_tokens: int = 300,
) -> list[dict]:
    """Merge consecutive small chunks to reach target token count.

    Feature 31.12: Post-processing merger after HybridChunker to address
    the issue of very small chunks (8.7 tokens/chunk) when processing
    hierarchical documents like PowerPoint slides.

    Strategy:
    - Merge consecutive chunks until reaching target_tokens
    - Preserve all VLM metadata (image_bboxes) from merged chunks
    - Only merge if chunk is below min_tokens (avoid breaking good chunks)
    - Stop merging if next chunk would exceed target by >20%

    Args:
        enhanced_chunks: List of {chunk, image_bboxes} dicts
        tokenizer: HuggingFaceTokenizer for token counting
        target_tokens: Target chunk size (default 1800)
        min_tokens: Minimum size to trigger merge (default 300)

    Returns:
        List of merged enhanced chunks with same structure

    Example:
        >>> # Input: 124 chunks @ 8.7 tokens/chunk
        >>> merged = merge_small_chunks(enhanced_chunks, tokenizer, 1800)
        >>> # Output: ~6 chunks @ ~175 tokens/chunk (124 * 8.7 / 6)
    """
    if not enhanced_chunks:
        return []

    # Helper: Count tokens in chunk text
    def count_tokens(chunk_obj) -> int:
        try:
            # Get text from chunk (use .text attribute)
            if hasattr(chunk_obj, "text"):
                text = chunk_obj.text
            elif hasattr(chunk_obj, "contextualize"):
                text = chunk_obj.contextualize()
            else:
                text = str(chunk_obj)

            # Count tokens using tokenizer
            tokens = tokenizer.tokenizer.encode(text, add_special_tokens=False)
            return len(tokens)
        except Exception:
            # Fallback: approximate token count (avg 4 chars/token)
            text = chunk_obj.text if hasattr(chunk_obj, "text") else str(chunk_obj)
            return max(1, len(text) // 4)

    # Helper: Merge two chunk objects into one
    def merge_chunk_objects(chunk1, chunk2):
        """Merge two Docling chunk objects by concatenating text."""

        # Create a new chunk with merged text
        merged_text = chunk1.text + "\n\n" + chunk2.text

        # Create a simple merged chunk (we'll use the first chunk as base)
        # and update its text
        merged_chunk = chunk1  # Keep first chunk's structure
        # Override text attribute
        merged_chunk.text = merged_text

        return merged_chunk

    merged = []
    current_group = None
    current_tokens = 0
    current_bboxes = []

    for enhanced_chunk in enhanced_chunks:
        chunk_obj = enhanced_chunk["chunk"]
        chunk_tokens = count_tokens(chunk_obj)
        chunk_bboxes = enhanced_chunk["image_bboxes"]

        # Start new group if none exists
        if current_group is None:
            current_group = chunk_obj
            current_tokens = chunk_tokens
            current_bboxes = list(chunk_bboxes)  # Copy list
            continue

        # Check if we should merge this chunk
        would_be_tokens = current_tokens + chunk_tokens
        should_merge = (
            # Current group is below minimum
            (current_tokens < min_tokens)
            or
            # Would reach target without exceeding by >20%
            (would_be_tokens <= target_tokens * 1.2)
        )

        if should_merge:
            # Merge into current group
            current_group = merge_chunk_objects(current_group, chunk_obj)
            current_tokens = would_be_tokens
            current_bboxes.extend(chunk_bboxes)  # Preserve all bboxes
        else:
            # Save current group and start new one
            merged.append({"chunk": current_group, "image_bboxes": current_bboxes})
            current_group = chunk_obj
            current_tokens = chunk_tokens
            current_bboxes = list(chunk_bboxes)

    # Don't forget last group
    if current_group is not None:
        merged.append({"chunk": current_group, "image_bboxes": current_bboxes})

    logger.info(
        "chunk_merger_complete",
        original_chunks=len(enhanced_chunks),
        merged_chunks=len(merged),
        reduction_ratio=round(len(merged) / len(enhanced_chunks), 2) if enhanced_chunks else 0,
        target_tokens=target_tokens,
    )

    return merged


async def chunking_node(state: IngestionState) -> IngestionState:
    """Node 3: Chunk document with HybridChunker + BBox mapping (Feature 21.6).

    Feature 21.6 Changes:
    - Uses Docling HybridChunker instead of ChunkingService
    - BGE-M3 tokenizer (8192 context window)
    - Maps VLM-enriched images to chunks via BBox
    - Creates enhanced chunks with image annotations

    Args:
        state: Current ingestion state

    Returns:
        Updated state with enhanced chunks (list of {chunk, image_bboxes})

    Raises:
        IngestionError: If chunking fails

    Example:
        >>> state = await chunking_node(state)
        >>> len(state["chunks"])
        8  # 8 enhanced chunks
        >>> state["chunks"][0]["image_bboxes"]
        [...]  # BBox info for images in this chunk
    """
    chunking_start = time.perf_counter()
    logger.info(
        "TIMING_chunking_start",
        stage="chunking",
        document_id=state["document_id"],
    )

    state["chunking_status"] = "running"
    state["chunking_start_time"] = time.time()

    try:
        # Feature 21.6: Use enriched DoclingDocument
        enriched_doc = state.get("document")

        # Fallback to parsed_content for backward compatibility
        if enriched_doc is None:
            logger.warning(
                "chunking_fallback_to_text",
                document_id=state["document_id"],
                reason="no_docling_document",
            )
            content = state.get("parsed_content", "")
            if not content or not content.strip():
                raise IngestionError(
                    document_id=state.get("document_id", "unknown"),
                    reason="No content to chunk (both document and parsed_content empty)",
                )

            # Use legacy ChunkingService as fallback
            chunk_strategy = ChunkStrategy(
                method="adaptive",
                chunk_size=1800,
                overlap=300,
            )
            chunking_service = get_chunking_service(strategy=chunk_strategy)
            legacy_chunks = chunking_service.chunk_document(
                document_id=state["document_id"],
                content=content,
                metadata=state.get("parsed_metadata", {}),
            )
            # Convert to enhanced format (no image annotations)
            state["chunks"] = [{"chunk": c, "image_bboxes": []} for c in legacy_chunks]
            state["chunking_status"] = "completed"
            state["chunking_end_time"] = time.time()
            state["overall_progress"] = calculate_progress(state)
            logger.info("node_chunking_complete_legacy", chunks_created=len(legacy_chunks))
            return state

        # Sprint 32 Feature 32.1 & 32.2: Adaptive Section-Aware Chunking (ADR-039)
        # Extract section hierarchy from Docling JSON
        section_extraction_start = time.perf_counter()
        from src.components.ingestion.section_extraction import extract_section_hierarchy

        sections = extract_section_hierarchy(enriched_doc, SectionMetadata)
        section_extraction_end = time.perf_counter()
        section_extraction_ms = (section_extraction_end - section_extraction_start) * 1000

        # CRITICAL LOGGING: Section extraction results
        logger.info(
            "TIMING_chunking_section_extraction",
            stage="chunking",
            substage="section_extraction",
            duration_ms=round(section_extraction_ms, 2),
            document_id=state["document_id"],
            sections_found=len(sections),
            total_section_text_length=sum(len(s.text) for s in sections),
        )

        # FALLBACK: If no sections found, create single default section from document text
        if not sections:
            logger.warning(
                "chunking_no_sections_found_fallback",
                document_id=state["document_id"],
                reason="extract_section_hierarchy returned empty list",
                fallback_action="creating single section from document text",
            )

            # Extract all text from DoclingDocument
            doc_text = ""
            if hasattr(enriched_doc, "export_to_markdown"):
                doc_text = enriched_doc.export_to_markdown()
            elif hasattr(enriched_doc, "text"):
                doc_text = enriched_doc.text
            elif hasattr(enriched_doc, "pages"):
                # Fallback: concatenate text from all pages
                doc_text = "\n\n".join(
                    " ".join(item.text for item in page.items if hasattr(item, "text"))
                    for page in enriched_doc.pages
                )

            if not doc_text or not doc_text.strip():
                raise IngestionError(
                    document_id=state.get("document_id", "unknown"),
                    reason="No sections found AND document text is empty (cannot create fallback section)",
                )

            # Create single default section (use SectionMetadata defined above)
            # Count tokens for fallback section
            try:
                from transformers import AutoTokenizer

                tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")
                tokens = tokenizer.encode(doc_text.strip(), add_special_tokens=False)
                token_count = len(tokens)
            except Exception:
                # Fallback: approximate token count (avg 4 chars/token)
                token_count = max(1, len(doc_text) // 4)

            default_section = SectionMetadata(
                heading="Document",  # Default heading (singular, not list)
                level=1,  # Top-level section
                page_no=1,  # Assume page 1
                bbox={"l": 0.0, "t": 0.0, "r": 0.0, "b": 0.0},  # No bbox info
                text=doc_text.strip(),
                token_count=token_count,
                metadata={},  # Empty metadata
            )
            sections = [default_section]

            logger.info(
                "chunking_fallback_section_created",
                document_id=state["document_id"],
                fallback_section_length=len(doc_text),
                fallback_section_preview=doc_text[:200] + "..." if len(doc_text) > 200 else doc_text,
            )

        # Apply adaptive chunking (800-1800 tokens, section-aware)
        adaptive_chunking_start = time.perf_counter()
        adaptive_chunks = adaptive_section_chunking(
            sections=sections, min_chunk=800, max_chunk=1800, large_section_threshold=1200
        )
        adaptive_chunking_end = time.perf_counter()
        adaptive_chunking_ms = (adaptive_chunking_end - adaptive_chunking_start) * 1000

        logger.info(
            "TIMING_chunking_adaptive_merge",
            stage="chunking",
            substage="adaptive_merge",
            duration_ms=round(adaptive_chunking_ms, 2),
            input_sections=len(sections),
            output_chunks=len(adaptive_chunks),
            compression_ratio=round(len(sections) / len(adaptive_chunks), 2) if adaptive_chunks else 0,
        )

        # Convert AdaptiveChunk to enhanced_chunks format (backward compatible)
        # Map VLM metadata to chunks
        vlm_metadata = state.get("vlm_metadata", [])
        vlm_lookup = {vm["picture_ref"]: vm for vm in vlm_metadata}

        merged_chunks = []
        for adaptive_chunk in adaptive_chunks:
            # Create chunk object compatible with downstream processing
            chunk_obj = type(
                "Chunk",
                (),
                {
                    "text": adaptive_chunk.text,
                    "meta": type(
                        "Meta",
                        (),
                        {
                            "section_headings": adaptive_chunk.section_headings,
                            "section_pages": adaptive_chunk.section_pages,
                            "section_bboxes": adaptive_chunk.section_bboxes,
                            "primary_section": adaptive_chunk.primary_section,
                            "token_count": adaptive_chunk.token_count,
                        },
                    )(),
                },
            )()

            # VLM metadata mapping (if available)
            # Note: Section-aware chunking may not have picture refs
            # This is OK - VLM metadata is optional
            chunk_bboxes = []

            enhanced_chunk = {"chunk": chunk_obj, "image_bboxes": chunk_bboxes}
            merged_chunks.append(enhanced_chunk)

        state["chunks"] = merged_chunks
        # Sprint 32 Feature 32.4: Store sections and adaptive_chunks for Neo4j section node creation
        state["sections"] = sections  # SectionMetadata list for section hierarchy
        state["adaptive_chunks"] = adaptive_chunks  # AdaptiveChunk list for multi-section metadata
        state["chunking_status"] = "completed"
        state["chunking_end_time"] = time.time()
        state["overall_progress"] = calculate_progress(state)

        chunking_end = time.perf_counter()
        total_chunking_ms = (chunking_end - chunking_start) * 1000
        total_tokens = sum(ac.token_count for ac in adaptive_chunks)

        logger.info(
            "TIMING_chunking_complete",
            stage="chunking",
            duration_ms=round(total_chunking_ms, 2),
            document_id=state["document_id"],
            original_sections=len(sections),
            adaptive_chunks=len(adaptive_chunks),
            final_chunks=len(merged_chunks),
            total_tokens=total_tokens,
            avg_tokens_per_chunk=round(total_tokens / len(merged_chunks), 1) if merged_chunks else 0,
            chunks_with_images=sum(1 for c in merged_chunks if c["image_bboxes"]),
            total_image_annotations=sum(len(c["image_bboxes"]) for c in merged_chunks),
            timing_breakdown={
                "section_extraction_ms": round(section_extraction_ms, 2),
                "adaptive_merge_ms": round(adaptive_chunking_ms, 2),
            },
        )

        return state

    except Exception as e:
        logger.error("node_chunking_error", document_id=state["document_id"], error=str(e))
        add_error(state, "chunking", str(e), "error")
        state["chunking_status"] = "failed"
        state["chunking_end_time"] = time.time()
        raise


# =============================================================================
# NODE 4: EMBEDDING
# =============================================================================


async def embedding_node(state: IngestionState) -> IngestionState:
    """Node 4: Generate embeddings + upload to Qdrant with full provenance (Feature 21.6).

    Feature 21.6 Changes:
    - Handles enhanced chunks (with image_bboxes)
    - Uses chunk.contextualize() for hierarchical context
    - Stores full BBox provenance in Qdrant payload
    - Includes page dimensions for frontend rendering

    Workflow:
    1. Extract contextualized text from chunks
    2. Generate BGE-M3 embeddings (1024D) via Ollama
    3. Create Qdrant payloads with full provenance
    4. Upload to Qdrant vector database

    Args:
        state: Current ingestion state

    Returns:
        Updated state with embedded chunk IDs

    Raises:
        IngestionError: If embedding or upload fails

    Example:
        >>> state = await embedding_node(state)
        >>> len(state["embedded_chunk_ids"])
        8  # 8 chunks uploaded to Qdrant
        >>> state["embedding_status"]
        'completed'
    """
    embedding_node_start = time.perf_counter()
    logger.info(
        "TIMING_embedding_start",
        stage="embedding",
        document_id=state["document_id"],
    )

    state["embedding_status"] = "running"
    state["embedding_start_time"] = time.time()

    try:
        # Get enhanced chunks (Feature 21.6: list of {chunk, image_bboxes})
        chunk_data_list = state.get("chunks", [])
        if not chunk_data_list:
            raise IngestionError(
                document_id=state.get("document_id", "unknown"),
                reason="No chunks to embed (chunks list is empty)",
            )

        # Get embedding service (BGE-M3, 1024D)
        embedding_service = get_embedding_service()

        # Feature 21.6: Extract contextualized text (includes headings, captions, page)
        texts = []
        for chunk_data in chunk_data_list:
            chunk = chunk_data["chunk"] if isinstance(chunk_data, dict) else chunk_data
            # Use contextualize() for hierarchical context
            if hasattr(chunk, "contextualize"):
                contextualized_text = chunk.contextualize()
                texts.append(contextualized_text)
            else:
                # Fallback for legacy chunks
                texts.append(chunk.content if hasattr(chunk, "content") else str(chunk))

        # Generate embeddings
        embedding_gen_start = time.perf_counter()
        logger.info(
            "TIMING_embedding_generation_start",
            stage="embedding",
            substage="embedding_generation",
            chunk_count=len(texts),
            total_chars=sum(len(t) for t in texts),
        )
        embeddings = await embedding_service.embed_batch(texts)
        embedding_gen_end = time.perf_counter()
        embedding_gen_ms = (embedding_gen_end - embedding_gen_start) * 1000
        embeddings_per_sec = len(texts) / (embedding_gen_ms / 1000) if embedding_gen_ms > 0 else 0

        logger.info(
            "TIMING_embedding_generation_complete",
            stage="embedding",
            substage="embedding_generation",
            duration_ms=round(embedding_gen_ms, 2),
            embeddings_generated=len(embeddings),
            throughput_embeddings_per_sec=round(embeddings_per_sec, 2),
            embedding_dim=len(embeddings[0]) if embeddings else 0,
        )

        # Upload to Qdrant
        qdrant = QdrantClientWrapper()
        collection_name = settings.qdrant_collection

        # Ensure collection exists
        await qdrant.create_collection(
            collection_name=collection_name,
            vector_size=1024,  # BGE-M3 dimension
        )

        # Create Qdrant points with full provenance
        import hashlib

        from qdrant_client.models import PointStruct

        page_dimensions = state.get("page_dimensions", {})
        points = []
        chunk_ids = []

        for chunk_data, embedding, contextualized_text in zip(
            chunk_data_list, embeddings, texts, strict=False
        ):
            # Handle both enhanced and legacy chunk formats
            if isinstance(chunk_data, dict):
                chunk = chunk_data["chunk"]
                image_bboxes = chunk_data.get("image_bboxes", [])
            else:
                chunk = chunk_data
                image_bboxes = []

            # Generate deterministic chunk ID (Sprint 30: Use UUID format for Qdrant)
            chunk_text = chunk.text if hasattr(chunk, "text") else str(chunk)
            chunk_name = f"{state['document_id']}_chunk_{hashlib.sha256(chunk_text.encode()).hexdigest()[:8]}"
            # Convert to UUID using uuid5 (deterministic, namespace-based)
            import uuid

            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_name))
            chunk_ids.append(chunk_id)

            # Feature 21.6: Create payload with full provenance
            page_no = (
                chunk.meta.page_no
                if hasattr(chunk, "meta") and hasattr(chunk.meta, "page_no")
                else None
            )
            headings = (
                chunk.meta.headings
                if hasattr(chunk, "meta") and hasattr(chunk.meta, "headings")
                else []
            )

            payload = {
                # Content
                "content": chunk_text,
                "contextualized_content": contextualized_text,
                # Document Provenance
                "document_id": state["document_id"],
                "document_path": str(state["document_path"]),
                "page_no": page_no,
                "headings": headings,
                "chunk_id": chunk_id,
                # Page Dimensions (for frontend rendering)
                "page_dimensions": page_dimensions.get(page_no) if page_no else None,
                # Image Annotations with BBox (CRITICAL for Feature 21.6!)
                "contains_images": len(image_bboxes) > 0,
                "image_annotations": [
                    {
                        "description": img["description"],
                        "vlm_model": img["vlm_model"],
                        "bbox_absolute": (
                            img["bbox_full"]["bbox_absolute"] if img["bbox_full"] else None
                        ),
                        "page_context": (
                            img["bbox_full"]["page_context"] if img["bbox_full"] else None
                        ),
                        "bbox_normalized": (
                            img["bbox_full"]["bbox_normalized"] if img["bbox_full"] else None
                        ),
                    }
                    for img in image_bboxes
                ],
                # Timestamps
                "ingestion_timestamp": time.time(),
            }

            point = PointStruct(
                id=chunk_id,
                vector=embedding,
                payload=payload,
            )
            points.append(point)

        # Upload batch
        qdrant_upsert_start = time.perf_counter()
        await qdrant.upsert_points(
            collection_name=collection_name,
            points=points,
            batch_size=100,
        )
        qdrant_upsert_end = time.perf_counter()
        qdrant_upsert_ms = (qdrant_upsert_end - qdrant_upsert_start) * 1000

        logger.info(
            "TIMING_qdrant_upsert_complete",
            stage="embedding",
            substage="qdrant_upsert",
            duration_ms=round(qdrant_upsert_ms, 2),
            points_uploaded=len(points),
            batch_size=100,
            collection=collection_name,
        )

        # Store point IDs
        state["embedded_chunk_ids"] = chunk_ids
        state["embedding_status"] = "completed"
        state["embedding_end_time"] = time.time()
        state["overall_progress"] = calculate_progress(state)

        embedding_node_end = time.perf_counter()
        total_embedding_ms = (embedding_node_end - embedding_node_start) * 1000

        logger.info(
            "TIMING_embedding_complete",
            stage="embedding",
            duration_ms=round(total_embedding_ms, 2),
            document_id=state["document_id"],
            points_uploaded=len(points),
            points_with_images=sum(1 for p in points if p.payload.get("contains_images")),
            collection=collection_name,
            timing_breakdown={
                "embedding_generation_ms": round(embedding_gen_ms, 2),
                "qdrant_upsert_ms": round(qdrant_upsert_ms, 2),
            },
        )

        return state

    except Exception as e:
        logger.error("node_embedding_error", document_id=state["document_id"], error=str(e))
        add_error(state, "embedding", str(e), "error")
        state["embedding_status"] = "failed"
        state["embedding_end_time"] = time.time()
        raise


# =============================================================================
# NODE 5: GRAPH EXTRACTION
# =============================================================================


async def graph_extraction_node(state: IngestionState) -> IngestionState:
    """Node 5: Extract entities/relations → Neo4j with minimal provenance (Feature 21.6).

    Feature 21.6 Changes:
    - Handles enhanced chunks (with image_bboxes)
    - Adds minimal provenance: qdrant_point_id, has_image_annotation
    - Image page numbers for quick filtering
    - NO full BBox data (stored only in Qdrant)

    Uses ThreePhaseExtractor (SpaCy + Semantic Dedup + Gemma 3 4B)
    via LightRAG wrapper for Neo4j storage.

    Workflow:
    1. Get enhanced chunks from state
    2. Add minimal provenance to metadata
    3. Extract entities/relations via LightRAG
    4. Store in Neo4j graph database

    Args:
        state: Current ingestion state

    Returns:
        Updated state with graph extraction results

    Raises:
        IngestionError: If graph extraction fails

    Example:
        >>> state = await graph_extraction_node(state)
        >>> state["graph_status"]
        'completed'
    """
    graph_node_start = time.perf_counter()

    logger.info(
        "TIMING_graph_extraction_start",
        stage="graph_extraction",
        document_id=state["document_id"],
        chunks_available=len(state.get("chunks", [])),
        embedding_status=state.get("embedding_status"),
        chunking_status=state.get("chunking_status"),
    )

    state["graph_status"] = "running"
    state["graph_start_time"] = time.time()

    try:
        # Get enhanced chunks (Feature 21.6: list of {chunk, image_bboxes})
        chunk_data_list = state.get("chunks", [])
        if not chunk_data_list:
            raise IngestionError(
                document_id=state.get("document_id", "unknown"),
                reason="No chunks for graph extraction (chunks list is empty)",
            )

        # Get embedded chunk IDs (from embedding_node)
        embedded_chunk_ids = state.get("embedded_chunk_ids", [])

        # Get LightRAG wrapper
        lightrag = await get_lightrag_wrapper_async()

        # Convert chunks to LightRAG document format with minimal provenance
        lightrag_docs = []
        for idx, chunk_data in enumerate(chunk_data_list):
            # Handle both enhanced and legacy chunk formats
            if isinstance(chunk_data, dict):
                chunk = chunk_data["chunk"]
                image_bboxes = chunk_data.get("image_bboxes", [])
            else:
                chunk = chunk_data
                image_bboxes = []

            # Get chunk ID (from embedded_chunk_ids if available)
            chunk_id = embedded_chunk_ids[idx] if idx < len(embedded_chunk_ids) else f"chunk_{idx}"
            chunk_text = chunk.text if hasattr(chunk, "text") else str(chunk)

            # Feature 21.6: Add minimal provenance to metadata
            metadata = {}
            if hasattr(chunk, "metadata"):
                metadata = (
                    chunk.metadata.copy()
                    if hasattr(chunk.metadata, "copy")
                    else dict(chunk.metadata)
                )

            # Add Qdrant reference + image flags (NO full BBox!)
            metadata.update(
                {
                    "qdrant_point_id": chunk_id,  # Reference to Qdrant for full BBox
                    "has_image_annotation": len(image_bboxes) > 0,
                    "image_page_nos": (
                        [
                            bbox["bbox_full"]["page_context"]["page_no"]
                            for bbox in image_bboxes
                            if bbox.get("bbox_full") and bbox["bbox_full"].get("page_context")
                        ]
                        if image_bboxes
                        else []
                    ),
                }
            )

            lightrag_docs.append(
                {
                    "text": chunk_text,
                    "id": chunk_id,
                    "metadata": metadata,
                }
            )

        # Insert into LightRAG (extracts entities/relations, stores in Neo4j)
        lightrag_insert_start = time.perf_counter()
        logger.info(
            "TIMING_lightrag_insert_start",
            stage="graph_extraction",
            substage="lightrag_insert",
            chunk_count=len(lightrag_docs),
        )
        graph_stats = await lightrag.insert_documents_optimized(lightrag_docs)
        lightrag_insert_end = time.perf_counter()
        lightrag_insert_ms = (lightrag_insert_end - lightrag_insert_start) * 1000

        logger.info(
            "TIMING_lightrag_insert_complete",
            stage="graph_extraction",
            substage="lightrag_insert",
            duration_ms=round(lightrag_insert_ms, 2),
            chunks_processed=len(lightrag_docs),
            entities_extracted=graph_stats.get("stats", {}).get("total_entities", 0),
            relations_extracted=graph_stats.get("stats", {}).get("total_relations", 0),
        )

        # Sprint 34 Feature 34.1 & 34.2: Extract and store RELATES_TO relationships
        # After LightRAG stores entities, extract relations between them
        relation_extraction_start = time.perf_counter()
        total_relations_created = 0

        logger.info(
            "TIMING_relation_extraction_start",
            stage="graph_extraction",
            substage="relation_extraction",
            chunks_to_process=len(lightrag_docs),
        )

        # Import RelationExtractor
        from src.components.graph_rag.relation_extractor import RelationExtractor

        relation_extractor = RelationExtractor()

        # Process each chunk: extract relations and store to Neo4j
        for doc in lightrag_docs:
            chunk_text = doc["text"]
            chunk_id = doc["id"]

            # Get entities that were stored for this chunk
            # These are the entities extracted by LightRAG that we need to relate
            chunk_stats = [r for r in graph_stats.get("results", []) if r.get("doc_id") == chunk_id]
            if not chunk_stats:
                logger.debug("no_entities_for_chunk", chunk_id=chunk_id[:8])
                continue

            # Extract entities list (we need entity names for RelationExtractor)
            # This is a simplified approach - we assume entities were already extracted
            # In real implementation, we'd query Neo4j or use the extraction results
            # For now, we'll extract relations from all entities in the document
            # TODO: Query Neo4j for entities associated with this chunk
            entities = []  # Will be populated from LightRAG extraction results

            if not entities:
                # Fallback: Extract relations using entity names from chunk metadata
                # In production, this should query Neo4j for actual entities
                logger.debug("extracting_relations_without_entity_list", chunk_id=chunk_id[:8])
                continue

            try:
                # Extract relations between entities in this chunk
                relations = await relation_extractor.extract(chunk_text, entities)

                # Store relations to Neo4j with RELATES_TO relationships
                if relations:
                    relations_created = await lightrag._store_relations_to_neo4j(
                        relations=relations, chunk_id=chunk_id
                    )
                    total_relations_created += relations_created

                    logger.debug(
                        "chunk_relations_stored",
                        chunk_id=chunk_id[:8],
                        relations_extracted=len(relations),
                        relations_created=relations_created,
                    )

            except Exception as e:
                logger.warning(
                    "chunk_relation_extraction_failed",
                    chunk_id=chunk_id[:8],
                    error=str(e),
                    action="continuing_with_next_chunk",
                )
                continue

        relation_extraction_end = time.perf_counter()
        relation_extraction_ms = (relation_extraction_end - relation_extraction_start) * 1000

        # Store relations count in state
        state["relations_count"] = total_relations_created

        logger.info(
            "TIMING_relation_extraction_complete",
            stage="graph_extraction",
            substage="relation_extraction",
            duration_ms=round(relation_extraction_ms, 2),
            chunks_processed=len(lightrag_docs),
            total_relations_created=total_relations_created,
        )

        # Sprint 32 Feature 32.4: Create Section nodes in Neo4j (ADR-039)
        # Extract sections and chunks from state for section node creation
        sections = state.get("sections", [])
        adaptive_chunks = state.get("adaptive_chunks", [])

        section_nodes_ms = 0.0
        if sections and adaptive_chunks:
            try:
                section_nodes_start = time.perf_counter()
                logger.info(
                    "TIMING_section_nodes_start",
                    stage="graph_extraction",
                    substage="section_nodes",
                    document_id=state["document_id"],
                    sections_count=len(sections),
                    chunks_count=len(adaptive_chunks),
                )

                # Import Neo4j client
                from src.components.graph_rag.neo4j_client import get_neo4j_client

                neo4j_client = get_neo4j_client()

                # Create section nodes with hierarchical relationships
                section_stats = await neo4j_client.create_section_nodes(
                    document_id=state["document_id"],
                    sections=sections,
                    chunks=adaptive_chunks,
                )

                section_nodes_end = time.perf_counter()
                section_nodes_ms = (section_nodes_end - section_nodes_start) * 1000

                logger.info(
                    "TIMING_section_nodes_complete",
                    stage="graph_extraction",
                    substage="section_nodes",
                    duration_ms=round(section_nodes_ms, 2),
                    document_id=state["document_id"],
                    sections_created=section_stats["sections_created"],
                    has_section_rels=section_stats["has_section_rels"],
                    contains_chunk_rels=section_stats["contains_chunk_rels"],
                    defines_entity_rels=section_stats["defines_entity_rels"],
                )

                # Store section stats in state for analytics
                state["section_node_stats"] = section_stats

            except Exception as e:
                # Log error but don't fail entire ingestion (section nodes are optional enhancement)
                logger.warning(
                    "section_nodes_creation_failed",
                    document_id=state["document_id"],
                    error=str(e),
                    note="Continuing ingestion without section nodes",
                )
                state["section_node_stats"] = {"error": str(e)}
        else:
            logger.info(
                "section_nodes_skipped",
                document_id=state["document_id"],
                reason="no_sections_or_chunks_available",
                has_sections=bool(sections),
                has_chunks=bool(adaptive_chunks),
            )

        # Store statistics
        state["entities"] = []  # Full entities stored in Neo4j
        state["relations"] = []  # Full relations stored in Neo4j
        state["graph_status"] = "completed"
        state["graph_end_time"] = time.time()
        state["overall_progress"] = calculate_progress(state)

        # Extract stats from nested structure (Sprint 32 Fix)
        stats = graph_stats.get("stats", {})
        graph_node_end = time.perf_counter()
        total_graph_ms = (graph_node_end - graph_node_start) * 1000

        logger.info(
            "TIMING_graph_extraction_complete",
            stage="graph_extraction",
            duration_ms=round(total_graph_ms, 2),
            document_id=state["document_id"],
            total_entities=stats.get("total_entities", 0),
            total_relations=stats.get("total_relations", 0),
            total_chunks=stats.get("total_chunks", 0),
            chunks_with_images=sum(
                1 for doc in lightrag_docs if doc["metadata"].get("has_image_annotation")
            ),
            section_nodes_created=state.get("section_node_stats", {}).get("sections_created", 0),
            timing_breakdown={
                "lightrag_insert_ms": round(lightrag_insert_ms, 2),
                "section_nodes_ms": round(section_nodes_ms, 2),
            },
        )

        return state

    except Exception as e:
        logger.error("node_graph_extraction_error", document_id=state["document_id"], error=str(e))
        add_error(state, "graph_extraction", str(e), "error")
        state["graph_status"] = "failed"
        state["graph_end_time"] = time.time()
        raise
