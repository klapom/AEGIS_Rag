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

import subprocess
import time
from contextlib import suppress
from pathlib import Path

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
        # Check system RAM usage (psutil)
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

        # Check if sufficient memory available
        # Sprint 30: Lowered to 500MB for small PDF testing (production should use 2000MB minimum)
        # TODO: Make threshold configurable via settings.min_required_ram_mb
        if ram_available_mb < 500:  # Less than 500MB RAM available
            raise IngestionError(
                document_id=state["document_id"],
                reason=f"Insufficient RAM: Only {ram_available_mb:.0f}MB available (need 500MB)",
            )

        # Mark check as passed
        state["memory_check_passed"] = True
        state["overall_progress"] = calculate_progress(state)

        logger.info(
            "node_memory_check_complete",
            document_id=state["document_id"],
            memory_check_passed=True,
            requires_restart=state.get("requires_container_restart", False),
        )

        return state

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
            raise IngestionError(f"Document not found: {doc_path}")

        # Initialize Docling client (Sprint 30: Configurable via settings.docling_base_url)
        from src.core.config import settings

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

            # Feature 21.6: Extract page dimensions for BBox normalization
            page_dimensions = {}
            if hasattr(parsed, "document") and hasattr(parsed.document, "pages"):
                for page in parsed.document.pages:
                    page_dimensions[page.page_no] = {
                        "width": page.size.width,
                        "height": page.size.height,
                        "unit": "pt",
                        "dpi": 72,
                    }
                # Store in state (only if document attribute exists)
                state["document"] = parsed.document  # Feature 21.6: DoclingDocument object
            else:
                state["document"] = None  # Sprint 30: No document attribute in response

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

        finally:
            # CRITICAL: Always stop container to free VRAM (6GB → 0GB)
            await docling.stop_container()
            logger.info("docling_container_stopped", vram_freed="~6GB")

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
            # 3. Process each picture
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

            for idx, picture_item in enumerate(doc.pictures):
                try:
                    # 3a. Get PIL image
                    pil_image = picture_item.get_image()

                    # 3b. Extract enhanced BBox (if available)
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

                    # 3c. Generate VLM description (Sprint 25 Feature 25.4: now async)
                    description = await processor.process_image(
                        image=pil_image,
                        picture_index=idx,
                    )

                    if description is None:
                        # Image filtered out (too small, wrong aspect ratio)
                        logger.debug(
                            "vlm_image_filtered",
                            picture_index=idx,
                            reason="failed_filter_check",
                        )
                        continue

                    # 3d. INSERT INTO DoclingDocument (CRITICAL!)
                    if hasattr(picture_item, "caption") and picture_item.caption:
                        picture_item.text = f"{picture_item.caption}\n\n{description}"
                    else:
                        picture_item.text = description

                    # 3e. Store VLM metadata
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

                    logger.info(
                        "vlm_image_processed",
                        picture_index=idx,
                        description_length=len(description),
                        has_bbox=enhanced_bbox is not None,
                    )

                except Exception as e:
                    logger.warning(
                        "vlm_image_processing_error",
                        picture_index=idx,
                        error=str(e),
                        action="skipping_image",
                    )
                    # Continue with next image instead of failing entire pipeline
                    continue

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
    logger.info("node_chunking_start", document_id=state["document_id"])

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
                raise IngestionError("No content to chunk (both document and parsed_content empty)")

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

        # Feature 21.6: HybridChunker with BGE-M3
        from docling.chunking import HybridChunker
        from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
        from transformers import AutoTokenizer

        # Initialize BGE-M3 tokenizer
        tokenizer = HuggingFaceTokenizer(
            tokenizer=AutoTokenizer.from_pretrained("BAAI/bge-m3"),
            max_tokens=8192,  # BGE-M3 context window
        )

        # Initialize HybridChunker
        chunker = HybridChunker(
            tokenizer=tokenizer,
            merge_peers=True,  # Merge adjacent chunks for better context
        )

        # Chunk enriched document
        base_chunks = list(chunker.chunk(enriched_doc))

        # Map VLM metadata to chunks
        vlm_metadata = state.get("vlm_metadata", [])
        vlm_lookup = {vm["picture_ref"]: vm for vm in vlm_metadata}

        enhanced_chunks = []
        for chunk in base_chunks:
            # Find picture references in chunk
            picture_refs = []
            if hasattr(chunk.meta, "doc_items") and chunk.meta.doc_items:
                picture_refs = [
                    ref for ref in chunk.meta.doc_items if ref.startswith("#/pictures/")
                ]

            # Collect BBox info for images in this chunk
            chunk_bboxes = []
            for pic_ref in picture_refs:
                if pic_ref in vlm_lookup:
                    vlm_info = vlm_lookup[pic_ref]
                    chunk_bboxes.append(
                        {
                            "picture_ref": pic_ref,
                            "description": vlm_info["description"],
                            "bbox_full": vlm_info["bbox_full"],
                            "vlm_model": vlm_info["vlm_model"],
                        }
                    )

            enhanced_chunk = {"chunk": chunk, "image_bboxes": chunk_bboxes}
            enhanced_chunks.append(enhanced_chunk)

        state["chunks"] = enhanced_chunks
        state["chunking_status"] = "completed"
        state["chunking_end_time"] = time.time()
        state["overall_progress"] = calculate_progress(state)

        logger.info(
            "node_chunking_complete",
            document_id=state["document_id"],
            chunks_created=len(enhanced_chunks),
            chunks_with_images=sum(1 for c in enhanced_chunks if c["image_bboxes"]),
            total_image_annotations=sum(len(c["image_bboxes"]) for c in enhanced_chunks),
            duration_seconds=round(state["chunking_end_time"] - state["chunking_start_time"], 2),
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
    logger.info("node_embedding_start", document_id=state["document_id"])

    state["embedding_status"] = "running"
    state["embedding_start_time"] = time.time()

    try:
        # Get enhanced chunks (Feature 21.6: list of {chunk, image_bboxes})
        chunk_data_list = state.get("chunks", [])
        if not chunk_data_list:
            raise IngestionError("No chunks to embed (chunks list is empty)")

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
        logger.info("embedding_batch_start", chunk_count=len(texts))
        embeddings = await embedding_service.embed_batch(texts)

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
        await qdrant.upsert_points(
            collection_name=collection_name,
            points=points,
            batch_size=100,
        )

        # Store point IDs
        state["embedded_chunk_ids"] = chunk_ids
        state["embedding_status"] = "completed"
        state["embedding_end_time"] = time.time()
        state["overall_progress"] = calculate_progress(state)

        logger.info(
            "node_embedding_complete",
            document_id=state["document_id"],
            points_uploaded=len(points),
            points_with_images=sum(1 for p in points if p.payload.get("contains_images")),
            collection=collection_name,
            duration_seconds=round(state["embedding_end_time"] - state["embedding_start_time"], 2),
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
    logger.info("node_graph_extraction_start", document_id=state["document_id"])

    state["graph_status"] = "running"
    state["graph_start_time"] = time.time()

    try:
        # Get enhanced chunks (Feature 21.6: list of {chunk, image_bboxes})
        chunk_data_list = state.get("chunks", [])
        if not chunk_data_list:
            raise IngestionError("No chunks for graph extraction (chunks list is empty)")

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
        logger.info("lightrag_insert_start", chunk_count=len(lightrag_docs))
        graph_stats = await lightrag.insert_documents_optimized(lightrag_docs)

        # Store statistics
        state["entities"] = []  # Full entities stored in Neo4j
        state["relations"] = []  # Full relations stored in Neo4j
        state["graph_status"] = "completed"
        state["graph_end_time"] = time.time()
        state["overall_progress"] = calculate_progress(state)

        logger.info(
            "node_graph_extraction_complete",
            document_id=state["document_id"],
            total_entities=graph_stats.get("total_entities", 0),
            total_relations=graph_stats.get("total_relations", 0),
            total_chunks=graph_stats.get("total_chunks", 0),
            chunks_with_images=sum(
                1 for doc in lightrag_docs if doc["metadata"].get("has_image_annotation")
            ),
            duration_seconds=round(state["graph_end_time"] - state["graph_start_time"], 2),
        )

        return state

    except Exception as e:
        logger.error("node_graph_extraction_error", document_id=state["document_id"], error=str(e))
        add_error(state, "graph_extraction", str(e), "error")
        state["graph_status"] = "failed"
        state["graph_end_time"] = time.time()
        raise
