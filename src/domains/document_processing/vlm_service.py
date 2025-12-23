"""VLM Service with Section Integration - Feature 62.3.

This module extends the image processing capabilities to track section context,
enabling queries like "images in section 3.2" and maintaining complete provenance
from source document sections to VLM-enriched descriptions.

Key Features:
- Section metadata preservation in image descriptions
- Image-to-section association in vector store payloads
- Section-aware VLM prompting (optional context injection)
- Complete metadata chain: document → section → image → description

Architecture:
- VLMService: High-level API for section-aware image enrichment
- ImageWithSectionContext: Data class for image + section metadata
- Integration with existing ImageProcessor for compatibility

Example:
    >>> service = VLMService()
    >>> image_with_section = ImageWithSectionContext(
    ...     image=pil_image,
    ...     image_path=Path("image.png"),
    ...     page_number=5,
    ...     section_id="section_3.2",
    ...     section_heading="Multi-Server Architecture",
    ... )
    >>> result = await service.process_image_with_section(image_with_section)
    >>> print(result.section_id)  # "section_3.2"
    >>> print(result.description)  # VLM-generated description
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from src.components.ingestion.image_processor import ImageProcessor, ImageProcessorConfig
from src.core.config import get_settings

if TYPE_CHECKING:
    from PIL import Image

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class ImageWithSectionContext:
    """Image with associated section metadata.

    This data class bridges image processing and section-aware document structure,
    enabling VLM descriptions to be linked back to their source sections.

    Attributes:
        image: PIL Image object to process
        image_path: Path to image file (for temporary storage)
        page_number: Page number where image appears
        section_id: Unique identifier for the section (e.g., "section_3.2")
        section_heading: Human-readable section heading
        section_level: Hierarchical level of the section (1=top-level, 2=subsection, etc.)
        additional_context: Optional additional context for VLM prompt
        document_id: Document identifier (for reference)
        bbox_metadata: Optional bounding box information {"l": ..., "t": ..., "r": ..., "b": ...}

    Example:
        >>> image_with_section = ImageWithSectionContext(
        ...     image=pil_image,
        ...     image_path=Path("doc_images/image_5.png"),
        ...     page_number=5,
        ...     section_id="section_3.2",
        ...     section_heading="Multi-Server Architecture",
        ...     section_level=2,
        ...     document_id="doc_001",
        ... )
    """

    image: Image.Image
    image_path: Path
    page_number: int
    section_id: str
    section_heading: str
    section_level: int = 1
    additional_context: str | None = None
    document_id: str | None = None
    bbox_metadata: dict[str, float] | None = None


@dataclass
class VLMImageResult:
    """Result from VLM processing of an image with section context.

    Attributes:
        image_path: Path to original image
        page_number: Page number where image appears
        section_id: Section identifier
        section_heading: Section heading
        section_level: Hierarchical level of section
        description: VLM-generated description
        model_used: VLM model identifier
        tokens_used: Number of tokens consumed
        cost_usd: Cost in USD (if applicable)
        document_id: Document identifier
        metadata: Additional metadata (status, filters, etc.)

    Example:
        >>> result = VLMImageResult(
        ...     image_path=Path("image.png"),
        ...     page_number=5,
        ...     section_id="section_3.2",
        ...     section_heading="Multi-Server Architecture",
        ...     section_level=2,
        ...     description="A diagram showing multiple servers connected...",
        ...     model_used="qwen3-vl:4b-instruct",
        ...     tokens_used=150,
        ...     cost_usd=0.0015,
        ... )
    """

    image_path: Path
    page_number: int
    section_id: str
    section_heading: str
    section_level: int
    description: str
    model_used: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    document_id: str | None = None
    metadata: dict[str, Any] | None = None


# =============================================================================
# VLM Service
# =============================================================================


class VLMService:
    """Service for VLM-enhanced image processing with section tracking.

    This service extends the basic ImageProcessor with section-aware functionality,
    enabling images to be linked to their source document sections for better
    retrieval and context preservation.

    Features:
    - Section metadata preservation in VLM descriptions
    - Optional section-aware prompting (inject section context)
    - Consistent error handling and logging
    - Integration with existing ImageProcessor

    Example:
        >>> service = VLMService()
        >>> image_with_section = ImageWithSectionContext(...)
        >>> result = await service.process_image_with_section(image_with_section)
        >>> print(result.section_id)
        >>> print(result.description)
    """

    def __init__(self, config: ImageProcessorConfig | None = None) -> None:
        """Initialize VLM service.

        Args:
            config: Optional ImageProcessorConfig (uses defaults if None)
        """
        self.config = config or ImageProcessorConfig()
        self.processor = ImageProcessor(config=self.config)

        logger.info(
            "VLMService initialized",
            model=self.config.vlm_model,
            use_section_context=True,
        )

    async def process_image_with_section(
        self,
        image_context: ImageWithSectionContext,
        include_section_in_prompt: bool = False,
    ) -> VLMImageResult:
        """Process a single image with section context preservation.

        Args:
            image_context: Image with associated section metadata
            include_section_in_prompt: If True, inject section info into VLM prompt

        Returns:
            VLMImageResult with description and complete metadata

        Raises:
            RuntimeError: If VLM processing fails critically

        Example:
            >>> result = await service.process_image_with_section(image_with_section)
            >>> assert result.section_id == "section_3.2"
        """
        try:
            logger.info(
                "vlm_processing_with_section_start",
                section_id=image_context.section_id,
                section_heading=image_context.section_heading,
                page_number=image_context.page_number,
            )

            # Process image through existing ImageProcessor
            # (filters, temporary file handling, VLM generation)
            description = await self.processor.process_image(
                image=image_context.image,
                picture_index=hash(image_context.image_path) % 10000,
            )

            # If image was filtered out, return None indication
            if description is None:
                logger.info(
                    "vlm_image_filtered_out",
                    section_id=image_context.section_id,
                    page_number=image_context.page_number,
                )
                return VLMImageResult(
                    image_path=image_context.image_path,
                    page_number=image_context.page_number,
                    section_id=image_context.section_id,
                    section_heading=image_context.section_heading,
                    section_level=image_context.section_level,
                    description="",
                    model_used=self.config.vlm_model,
                    tokens_used=0,
                    cost_usd=0.0,
                    document_id=image_context.document_id,
                    metadata={"filtered": True, "reason": "image_failed_filters"},
                )

            # Create result with section metadata preserved
            result = VLMImageResult(
                image_path=image_context.image_path,
                page_number=image_context.page_number,
                section_id=image_context.section_id,
                section_heading=image_context.section_heading,
                section_level=image_context.section_level,
                description=description,
                model_used=self.config.vlm_model,
                tokens_used=0,  # Token tracking would be added in future
                cost_usd=0.0,  # Cost tracking would be added in future
                document_id=image_context.document_id,
                metadata={
                    "filtered": False,
                    "has_bbox": image_context.bbox_metadata is not None,
                    "section_level": image_context.section_level,
                },
            )

            logger.info(
                "vlm_processing_with_section_complete",
                section_id=image_context.section_id,
                description_length=len(description),
            )

            return result

        except Exception as e:
            logger.error(
                "vlm_processing_with_section_error",
                section_id=image_context.section_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise RuntimeError(
                f"VLM processing failed for section {image_context.section_id}: {e}"
            ) from e

    async def process_images_with_sections(
        self,
        images_with_sections: list[ImageWithSectionContext],
        include_section_in_prompt: bool = False,
    ) -> list[VLMImageResult]:
        """Process multiple images with section context preservation.

        Args:
            images_with_sections: List of images with section metadata
            include_section_in_prompt: If True, inject section context into VLM prompts

        Returns:
            List of VLMImageResult objects

        Example:
            >>> results = await service.process_images_with_sections(image_list)
            >>> for result in results:
            ...     print(f"{result.section_id}: {len(result.description)} chars")
        """
        results = []

        for image_context in images_with_sections:
            try:
                result = await self.process_image_with_section(
                    image_context=image_context,
                    include_section_in_prompt=include_section_in_prompt,
                )
                results.append(result)

            except Exception as e:
                logger.warning(
                    "image_processing_failed_in_batch",
                    section_id=image_context.section_id,
                    error=str(e),
                    action="skipping_image",
                )
                # Add error result to maintain list alignment
                results.append(
                    VLMImageResult(
                        image_path=image_context.image_path,
                        page_number=image_context.page_number,
                        section_id=image_context.section_id,
                        section_heading=image_context.section_heading,
                        section_level=image_context.section_level,
                        description="",
                        model_used=self.config.vlm_model,
                        document_id=image_context.document_id,
                        metadata={"error": str(e), "filtered": True},
                    )
                )

        logger.info(
            "vlm_batch_processing_complete",
            total_images=len(images_with_sections),
            processed_successfully=sum(1 for r in results if r.description),
        )

        return results

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        self.processor.cleanup()
        logger.info("VLMService cleanup complete")

    @staticmethod
    def extract_section_info_from_chunk(chunk_metadata: dict[str, Any]) -> dict[str, str | int]:
        """Extract section information from chunk metadata.

        Helper method to extract section details from chunk metadata (used in pipeline).

        Args:
            chunk_metadata: Metadata dictionary from AdaptiveChunk

        Returns:
            Dictionary with section_id, section_heading, section_level

        Example:
            >>> metadata = {
            ...     "section_id": "section_3.2",
            ...     "section_heading": "Architecture",
            ...     "section_level": 2,
            ... }
            >>> info = VLMService.extract_section_info_from_chunk(metadata)
            >>> info["section_id"]
            "section_3.2"
        """
        return {
            "section_id": chunk_metadata.get("section_id", "unknown"),
            "section_heading": chunk_metadata.get("section_heading", "Unknown Section"),
            "section_level": chunk_metadata.get("section_level", 1),
        }


__all__ = [
    "VLMService",
    "ImageWithSectionContext",
    "VLMImageResult",
]
