"""Adaptive Chunking Node for LangGraph Ingestion Pipeline.

Sprint 54 Feature 54.5: Extracted from langgraph_nodes.py

This module handles document chunking with section-awareness.
Implements ADR-039 adaptive section-aware chunking strategy:
- Large sections (>1200 tokens) -> Keep as standalone chunks
- Small sections (<1200 tokens) -> Merge until 800-1800 tokens
- Track ALL sections in chunk metadata (multi-section support)

Node: chunking_node
Functions: adaptive_section_chunking, merge_small_chunks
"""

import time

import structlog

from src.components.ingestion.ingestion_state import (
    IngestionState,
    add_error,
    calculate_progress,
)
from src.components.ingestion.nodes.models import AdaptiveChunk, SectionMetadata
from src.core.chunking_service import get_chunking_service
from src.core.exceptions import IngestionError

logger = structlog.get_logger(__name__)


def adaptive_section_chunking(
    sections: list[SectionMetadata],
    min_chunk: int = 800,
    max_chunk: int = 1800,
    large_section_threshold: int = 1200,
) -> list[AdaptiveChunk]:
    """Chunk with section-awareness, merging small sections intelligently (Feature 32.2).

    Implements ADR-039 adaptive section-aware chunking strategy:
    - Large sections (>1200 tokens) -> Keep as standalone chunks
    - Small sections (<1200 tokens) -> Merge until 800-1800 tokens
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
        >>> # PowerPoint (15 slides @ 150-250 tokens) -> 6-8 chunks
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

        # Large section -> standalone chunk (preserve clean extraction)
        if section_tokens > large_section_threshold:
            # Flush any accumulated small sections first
            if current_sections:
                chunks.append(_merge_sections(current_sections))
                current_sections = []
                current_tokens = 0

            # Create standalone chunk for large section
            chunks.append(_create_chunk(section))

        # Small section -> merge with others (reduce fragmentation)
        elif current_tokens + section_tokens <= max_chunk:
            current_sections.append(section)
            current_tokens += section_tokens

        # Current batch full -> flush and start new
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
    """Create chunk from single section (large section -> standalone).

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
            from src.core.chunking_service import ChunkingConfig, ChunkStrategyEnum

            chunk_config = ChunkingConfig(
                strategy=ChunkStrategyEnum.ADAPTIVE,
                min_tokens=800,
                max_tokens=1800,
                overlap_tokens=300,
            )
            chunking_service = get_chunking_service(config=chunk_config)
            legacy_chunks = await chunking_service.chunk_document(
                text=content,
                document_id=state["document_id"],
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
                fallback_section_preview=(
                    doc_text[:200] + "..." if len(doc_text) > 200 else doc_text
                ),
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
            compression_ratio=(
                round(len(sections) / len(adaptive_chunks), 2) if adaptive_chunks else 0
            ),
        )

        # Convert AdaptiveChunk to enhanced_chunks format (backward compatible)
        # Map VLM metadata to chunks (currently unused as section-aware chunking doesn't have picture refs)
        # vlm_metadata = state.get("vlm_metadata", [])
        # Note: VLM metadata mapping can be added here when needed

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
            avg_tokens_per_chunk=(
                round(total_tokens / len(merged_chunks), 1) if merged_chunks else 0
            ),
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
