"""Image Enrichment Node with Section Integration - Feature 62.3.

This module extends the image enrichment node to preserve section metadata,
enabling images to be linked to their source document sections.

Key Enhancements:
- Images are associated with section_id from parent chunk
- Section metadata stored in VLM enrichment metadata
- Enables queries like "images in section 3.2"
- Complete metadata chain from document → section → image → description

Architecture:
- Integrates with existing ImageProcessor (backward compatible)
- Stores image_section_id in vector store payloads
- Maintains existing VLM metadata structure with section additions

Node: image_enrichment_node_with_sections
    - Uses Qwen3-VL for image descriptions (as before)
    - Extracts section context from chunks
    - Associates images with section_id
    - Stores section metadata in VLM result
"""

import asyncio
import time
from typing import Any

import structlog

from src.components.ingestion.image_processor import ImageProcessor
from src.components.ingestion.ingestion_state import (
    IngestionState,
    add_error,
    calculate_progress,
)

logger = structlog.get_logger(__name__)


async def image_enrichment_node_with_sections(state: IngestionState) -> IngestionState:
    """Enhanced VLM enrichment node with section integration (Feature 62.3).

    This node extends the existing image enrichment with section metadata preservation.

    Workflow:
    1. Get DoclingDocument from state
    2. Get chunks with section metadata from state
    3. For each picture_item in document.pictures:
       a. Filter image (size, aspect ratio)
       b. Extract BBox with page context
       c. Identify associated section from chunks
       d. Generate VLM description
       e. INSERT description INTO picture_item.text
       f. Store VLM metadata WITH section_id
    4. Update state with enriched document + enhanced VLM metadata

    Args:
        state: Current ingestion state

    Returns:
        Updated state with enriched document and section-linked VLM metadata

    Raises:
        IngestionError: If enrichment fails critically

    Example:
        >>> state = await image_enrichment_node_with_sections(state)
        >>> len(state["vlm_metadata"])
        5  # 5 images processed
        >>> state["vlm_metadata"][0]["section_id"]
        "section_3.2"
    """
    logger.info("node_vlm_enrichment_with_sections_start", document_id=state["document_id"])

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

        # 2. Get chunks with section metadata (Feature 62.3)
        chunks = state.get("chunks", [])
        section_map = _build_section_map_from_chunks(chunks)

        logger.info(
            "section_map_built",
            total_chunks=len(chunks),
            unique_sections=len(section_map),
        )

        page_dimensions = state.get("page_dimensions", {})
        vlm_metadata = []

        # 3. Initialize ImageProcessor
        processor = ImageProcessor()

        try:
            # 4. Process each picture
            pictures_count = len(doc.pictures) if hasattr(doc, "pictures") else 0
            logger.info("vlm_processing_with_sections_start", pictures_total=pictures_count)

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

            # Parallel processing with semaphore
            try:
                from src.core.config import settings

                max_concurrent_vlm = settings.ingestion_max_concurrent_vlm
            except Exception:
                max_concurrent_vlm = 5

            vlm_start_time = time.time()

            # Step 1: Prepare all images with section context
            image_tasks_data = []
            for idx, picture_item in enumerate(doc.pictures):
                try:
                    # Get PIL image
                    pil_image = picture_item.get_image()

                    # Extract enhanced BBox
                    enhanced_bbox = None
                    page_no = None
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

                    # Feature 62.3: Identify associated section
                    section_info = _identify_image_section(
                        page_no=page_no,
                        section_map=section_map,
                    )

                    image_tasks_data.append(
                        {
                            "idx": idx,
                            "picture_item": picture_item,
                            "pil_image": pil_image,
                            "enhanced_bbox": enhanced_bbox,
                            "section_info": section_info,
                        }
                    )

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
                max_concurrent=max_concurrent_vlm,
            )

            # Step 2: Process images in parallel batches
            semaphore = asyncio.Semaphore(max_concurrent_vlm)

            async def process_single_image(task_data: dict) -> dict | None:
                """Process single image with section context."""
                async with semaphore:
                    idx = task_data["idx"]
                    pil_image = task_data["pil_image"]
                    enhanced_bbox = task_data["enhanced_bbox"]
                    section_info = task_data["section_info"]

                    try:
                        description = await processor.process_image(
                            image=pil_image,
                            picture_index=idx,
                        )

                        if description is None:
                            logger.debug(
                                "vlm_image_filtered",
                                picture_index=idx,
                                section_id=section_info.get("section_id"),
                                reason="failed_filter_check",
                            )
                            return None

                        return {
                            "idx": idx,
                            "description": description,
                            "enhanced_bbox": enhanced_bbox,
                            "section_info": section_info,
                        }

                    except Exception as e:
                        logger.warning(
                            "vlm_image_processing_error",
                            picture_index=idx,
                            section_id=section_info.get("section_id"),
                            error=str(e),
                            action="skipping_image",
                        )
                        return None

            # Execute all VLM tasks in parallel
            vlm_tasks = [process_single_image(data) for data in image_tasks_data]
            vlm_results = await asyncio.gather(*vlm_tasks, return_exceptions=True)

            # Step 3: Process results and update DoclingDocument
            for task_data, result in zip(image_tasks_data, vlm_results, strict=True):
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
                section_info = result["section_info"]
                picture_item = task_data["picture_item"]

                # INSERT INTO DoclingDocument
                if hasattr(picture_item, "caption") and picture_item.caption:
                    picture_item.text = f"{picture_item.caption}\n\n{description}"
                else:
                    picture_item.text = description

                # Feature 62.3: Store VLM metadata WITH section_id
                vlm_metadata.append(
                    {
                        "picture_index": idx,
                        "picture_ref": f"#/pictures/{idx}",
                        "description": description,
                        "bbox_full": enhanced_bbox,
                        # Section metadata (Feature 62.3)
                        "section_id": section_info.get("section_id", "unknown"),
                        "section_heading": section_info.get("section_heading", "Unknown"),
                        "section_level": section_info.get("section_level", 1),
                        # Model metadata
                        "vlm_model": "qwen3-vl:4b-instruct",
                        "timestamp": time.time(),
                    }
                )

                logger.debug(
                    "vlm_image_processed_with_section",
                    picture_index=idx,
                    section_id=section_info.get("section_id"),
                    description_length=len(description),
                    has_bbox=enhanced_bbox is not None,
                )

            vlm_duration = time.time() - vlm_start_time
            logger.info(
                "vlm_parallel_processing_complete",
                images_total=pictures_count,
                images_processed=len(vlm_metadata),
                duration_seconds=round(vlm_duration, 2),
                images_per_second=(
                    round(len(vlm_metadata) / vlm_duration, 2) if vlm_duration > 0 else 0
                ),
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
            "node_vlm_enrichment_with_sections_complete",
            document_id=state["document_id"],
            images_processed=len(vlm_metadata),
            images_total=pictures_count,
        )

        return state

    except Exception as e:
        logger.error(
            "node_vlm_enrichment_with_sections_error",
            document_id=state["document_id"],
            error=str(e),
        )
        add_error(state, "vlm_enrichment_with_sections", str(e), "warning")
        state["enrichment_status"] = "failed"
        state["vlm_metadata"] = []
        return state


# =============================================================================
# Helper Functions
# =============================================================================


def _build_section_map_from_chunks(chunks: list[Any]) -> dict[int, dict[str, Any]]:
    """Build a mapping of page numbers to section information from chunks.

    Args:
        chunks: List of Chunk objects with metadata

    Returns:
        Dictionary mapping page_no to section info

    Example:
        >>> section_map = _build_section_map_from_chunks(chunks)
        >>> section_map[5]
        {'section_id': 'section_3.2', 'section_heading': 'Architecture', ...}
    """
    section_map = {}

    try:
        for chunk in chunks:
            if not hasattr(chunk, "metadata"):
                continue

            metadata = chunk.metadata
            if not metadata:
                continue

            # Extract section information from metadata
            section_id = metadata.get("section_id", "unknown")
            section_heading = metadata.get("section_heading", "Unknown")
            section_level = metadata.get("section_level", 1)

            # Get page numbers from chunk (may have multiple)
            pages = metadata.get("pages", [])
            if not pages and hasattr(chunk, "page_numbers"):
                pages = chunk.page_numbers

            # Map each page to this section
            for page_no in pages:
                section_map[page_no] = {
                    "section_id": section_id,
                    "section_heading": section_heading,
                    "section_level": section_level,
                }

    except Exception as e:
        logger.warning("section_map_build_error", error=str(e))

    return section_map


def _identify_image_section(
    page_no: int | None,
    section_map: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Identify the section associated with an image based on page number.

    Args:
        page_no: Page number where image appears
        section_map: Mapping of page numbers to section info

    Returns:
        Dictionary with section_id, section_heading, section_level

    Example:
        >>> section_info = _identify_image_section(5, section_map)
        >>> section_info["section_id"]
        "section_3.2"
    """
    if page_no is None:
        return {
            "section_id": "unknown",
            "section_heading": "Unknown Section",
            "section_level": 0,
        }

    # Try exact match first
    if page_no in section_map:
        return section_map[page_no]

    # Try to find section from nearby pages (backward search)
    for search_page in range(page_no, 0, -1):
        if search_page in section_map:
            return section_map[search_page]

    # Fallback
    return {
        "section_id": "unknown",
        "section_heading": "Unknown Section",
        "section_level": 0,
    }


__all__ = [
    "image_enrichment_node_with_sections",
]
