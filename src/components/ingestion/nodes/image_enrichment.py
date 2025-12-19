"""Image Enrichment Node for LangGraph Ingestion Pipeline.

Sprint 54 Feature 54.4: Extracted from langgraph_nodes.py

This module handles VLM (Vision Language Model) image enrichment.
For each image in a document, it generates AI descriptions that
are inserted back into the DoclingDocument for better retrieval.

Node: image_enrichment_node
    - Uses Qwen3-VL to generate image descriptions
    - Extracts BBox coordinates with page context
    - Parallel processing with semaphore concurrency control
"""

import asyncio
import time

import structlog

from src.components.ingestion.image_processor import ImageProcessor
from src.components.ingestion.ingestion_state import (
    IngestionState,
    add_error,
    calculate_progress,
)

logger = structlog.get_logger(__name__)


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

                max_concurrent_vlm = settings.ingestion_max_concurrent_vlm
            except Exception:
                max_concurrent_vlm = 5  # Conservative default

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

                    image_tasks_data.append(
                        {
                            "idx": idx,
                            "picture_item": picture_item,
                            "pil_image": pil_image,
                            "enhanced_bbox": enhanced_bbox,
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

            # Step 3b: Process images in parallel batches using asyncio.Semaphore
            semaphore = asyncio.Semaphore(max_concurrent_vlm)

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
                images_per_second=(
                    round(len(vlm_metadata) / vlm_duration, 2) if vlm_duration > 0 else 0
                ),
                max_concurrent=max_concurrent_vlm,
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
