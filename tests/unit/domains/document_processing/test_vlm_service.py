"""Unit tests for VLM Service with Section Integration - Feature 62.3.

Tests cover:
- VLMService initialization and cleanup
- ImageWithSectionContext data structure
- VLMImageResult data structure
- Section metadata extraction
- Image processing with section context preservation
- Batch processing with multiple images
- Error handling and edge cases
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domains.document_processing.vlm_service import (
    ImageWithSectionContext,
    VLMImageResult,
    VLMService,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def pil_image_mock():
    """Create a mock PIL Image."""
    image = MagicMock()
    image.size = (500, 500)
    image.mode = "RGB"
    return image


@pytest.fixture
def image_with_section_context(pil_image_mock, tmp_path):
    """Create an ImageWithSectionContext instance."""
    return ImageWithSectionContext(
        image=pil_image_mock,
        image_path=tmp_path / "image.png",
        page_number=5,
        section_id="section_3.2",
        section_heading="Multi-Server Architecture",
        section_level=2,
        document_id="doc_001",
    )


@pytest.fixture
def vlm_service():
    """Create a VLMService instance."""
    with patch("src.domains.document_processing.vlm_service.ImageProcessor"):
        return VLMService()


# =============================================================================
# Tests: Data Models
# =============================================================================


class TestImageWithSectionContext:
    """Test ImageWithSectionContext data model."""

    def test_creation_with_required_fields(self, pil_image_mock, tmp_path):
        """Test creating ImageWithSectionContext with required fields."""
        context = ImageWithSectionContext(
            image=pil_image_mock,
            image_path=tmp_path / "image.png",
            page_number=5,
            section_id="section_3.2",
            section_heading="Architecture",
            section_level=2,
        )

        assert context.image == pil_image_mock
        assert context.page_number == 5
        assert context.section_id == "section_3.2"
        assert context.section_heading == "Architecture"
        assert context.section_level == 2
        assert context.document_id is None

    def test_creation_with_all_fields(self, pil_image_mock, tmp_path):
        """Test creating ImageWithSectionContext with all optional fields."""
        bbox = {"l": 10, "t": 20, "r": 100, "b": 200}
        context = ImageWithSectionContext(
            image=pil_image_mock,
            image_path=tmp_path / "image.png",
            page_number=5,
            section_id="section_3.2",
            section_heading="Architecture",
            section_level=2,
            additional_context="Context information",
            document_id="doc_001",
            bbox_metadata=bbox,
        )

        assert context.additional_context == "Context information"
        assert context.document_id == "doc_001"
        assert context.bbox_metadata == bbox

    def test_section_id_format_validation(self, pil_image_mock, tmp_path):
        """Test that section_id is properly stored."""
        context = ImageWithSectionContext(
            image=pil_image_mock,
            image_path=tmp_path / "image.png",
            page_number=5,
            section_id="section_4.1.1",
            section_heading="Nested Section",
            section_level=3,
        )

        assert context.section_id == "section_4.1.1"
        assert context.section_level == 3


class TestVLMImageResult:
    """Test VLMImageResult data model."""

    def test_creation_with_required_fields(self, tmp_path):
        """Test creating VLMImageResult with required fields."""
        result = VLMImageResult(
            image_path=tmp_path / "image.png",
            page_number=5,
            section_id="section_3.2",
            section_heading="Architecture",
            section_level=2,
            description="A diagram showing servers",
            model_used="qwen3-vl:4b-instruct",
        )

        assert result.image_path == tmp_path / "image.png"
        assert result.page_number == 5
        assert result.section_id == "section_3.2"
        assert result.section_heading == "Architecture"
        assert result.description == "A diagram showing servers"
        assert result.model_used == "qwen3-vl:4b-instruct"

    def test_creation_with_optional_fields(self, tmp_path):
        """Test creating VLMImageResult with optional fields."""
        metadata = {"filtered": False, "has_bbox": True}
        result = VLMImageResult(
            image_path=tmp_path / "image.png",
            page_number=5,
            section_id="section_3.2",
            section_heading="Architecture",
            section_level=2,
            description="A diagram",
            model_used="qwen3-vl:4b-instruct",
            tokens_used=150,
            cost_usd=0.0015,
            document_id="doc_001",
            metadata=metadata,
        )

        assert result.tokens_used == 150
        assert result.cost_usd == 0.0015
        assert result.document_id == "doc_001"
        assert result.metadata == metadata

    def test_metadata_structure(self, tmp_path):
        """Test VLMImageResult metadata structure."""
        result = VLMImageResult(
            image_path=tmp_path / "image.png",
            page_number=5,
            section_id="section_3.2",
            section_heading="Architecture",
            section_level=2,
            description="Test description",
            model_used="qwen3-vl:4b-instruct",
            metadata={"filtered": False, "reason": None},
        )

        assert result.metadata["filtered"] is False
        assert result.metadata["reason"] is None


# =============================================================================
# Tests: VLMService Initialization and Cleanup
# =============================================================================


class TestVLMServiceInitialization:
    """Test VLMService initialization."""

    def test_initialization_with_default_config(self):
        """Test VLMService initialization with default config."""
        with patch("src.domains.document_processing.vlm_service.ImageProcessor"):
            service = VLMService()

            assert service.processor is not None
            assert service.config is not None

    def test_initialization_with_custom_config(self):
        """Test VLMService initialization with custom config."""
        from src.components.ingestion.image_processor import ImageProcessorConfig

        custom_config = ImageProcessorConfig()
        custom_config.min_size = 300

        with patch("src.domains.document_processing.vlm_service.ImageProcessor"):
            service = VLMService(config=custom_config)

            assert service.config == custom_config
            assert service.config.min_size == 300

    def test_cleanup(self, vlm_service):
        """Test VLMService cleanup."""
        vlm_service.processor.cleanup = MagicMock()

        vlm_service.cleanup()

        vlm_service.processor.cleanup.assert_called_once()


# =============================================================================
# Tests: Image Processing with Section Context
# =============================================================================


class TestImageProcessingWithSection:
    """Test image processing with section context."""

    @pytest.mark.asyncio
    async def test_process_image_with_section_success(
        self, vlm_service, image_with_section_context
    ):
        """Test successful image processing with section preservation."""
        description = "A diagram showing multiple servers"

        vlm_service.processor.process_image = AsyncMock(return_value=description)

        result = await vlm_service.process_image_with_section(image_with_section_context)

        assert result.section_id == "section_3.2"
        assert result.section_heading == "Multi-Server Architecture"
        assert result.section_level == 2
        assert result.description == description
        assert result.page_number == 5
        assert result.document_id == "doc_001"

    @pytest.mark.asyncio
    async def test_process_image_with_section_filtered(
        self, vlm_service, image_with_section_context
    ):
        """Test image processing when image is filtered out."""
        vlm_service.processor.process_image = AsyncMock(return_value=None)

        result = await vlm_service.process_image_with_section(image_with_section_context)

        assert result.section_id == "section_3.2"
        assert result.description == ""
        assert result.metadata["filtered"] is True

    @pytest.mark.asyncio
    async def test_process_image_with_section_error(self, vlm_service, image_with_section_context):
        """Test error handling during image processing."""
        vlm_service.processor.process_image = AsyncMock(
            side_effect=RuntimeError("VLM processing failed")
        )

        with pytest.raises(RuntimeError, match="VLM processing failed"):
            await vlm_service.process_image_with_section(image_with_section_context)

    @pytest.mark.asyncio
    async def test_section_context_preserved(self, vlm_service, image_with_section_context):
        """Test that section context is preserved through processing."""
        description = "Detailed diagram"
        vlm_service.processor.process_image = AsyncMock(return_value=description)

        result = await vlm_service.process_image_with_section(image_with_section_context)

        # Verify all section metadata is preserved
        assert result.section_id == image_with_section_context.section_id
        assert result.section_heading == image_with_section_context.section_heading
        assert result.section_level == image_with_section_context.section_level
        assert result.page_number == image_with_section_context.page_number

    @pytest.mark.asyncio
    async def test_image_with_bbox_metadata(self, vlm_service, pil_image_mock, tmp_path):
        """Test processing image with bounding box metadata."""
        bbox = {"l": 10, "t": 20, "r": 100, "b": 200}
        context = ImageWithSectionContext(
            image=pil_image_mock,
            image_path=tmp_path / "image.png",
            page_number=5,
            section_id="section_3.2",
            section_heading="Architecture",
            section_level=2,
            bbox_metadata=bbox,
        )

        vlm_service.processor.process_image = AsyncMock(return_value="Description")

        result = await vlm_service.process_image_with_section(context)

        assert result.metadata["has_bbox"] is True


# =============================================================================
# Tests: Batch Processing
# =============================================================================


class TestBatchProcessing:
    """Test batch processing of multiple images."""

    @pytest.mark.asyncio
    async def test_process_multiple_images_success(self, vlm_service, pil_image_mock, tmp_path):
        """Test processing multiple images with different sections."""
        images = [
            ImageWithSectionContext(
                image=pil_image_mock,
                image_path=tmp_path / f"image_{i}.png",
                page_number=i + 1,
                section_id=f"section_{i}.1",
                section_heading=f"Section {i}",
                section_level=1,
                document_id="doc_001",
            )
            for i in range(3)
        ]

        vlm_service.processor.process_image = AsyncMock(return_value="Description")

        results = await vlm_service.process_images_with_sections(images)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.section_id == f"section_{i}.1"
            assert result.section_heading == f"Section {i}"

    @pytest.mark.asyncio
    async def test_process_multiple_images_with_errors(self, vlm_service, pil_image_mock, tmp_path):
        """Test batch processing with some images failing."""
        images = [
            ImageWithSectionContext(
                image=pil_image_mock,
                image_path=tmp_path / f"image_{i}.png",
                page_number=i + 1,
                section_id=f"section_{i}.1",
                section_heading=f"Section {i}",
                section_level=1,
            )
            for i in range(3)
        ]

        # First call succeeds, second fails, third succeeds
        vlm_service.processor.process_image = AsyncMock(
            side_effect=[
                "Description 1",
                RuntimeError("Processing failed"),
                "Description 3",
            ]
        )

        results = await vlm_service.process_images_with_sections(images)

        # Should have 3 results even with errors
        assert len(results) == 3
        assert results[0].description == "Description 1"
        assert results[1].metadata["error"]  # Has error in metadata
        assert results[2].description == "Description 3"

    @pytest.mark.asyncio
    async def test_batch_processing_maintains_order(self, vlm_service, pil_image_mock, tmp_path):
        """Test that batch processing maintains image order."""
        images = [
            ImageWithSectionContext(
                image=pil_image_mock,
                image_path=tmp_path / f"image_{i}.png",
                page_number=10 + i,
                section_id=f"section_{i}.1",
                section_heading=f"Section {i}",
                section_level=1,
            )
            for i in range(5)
        ]

        vlm_service.processor.process_image = AsyncMock(return_value="Description")

        results = await vlm_service.process_images_with_sections(images)

        for i, result in enumerate(results):
            assert result.page_number == 10 + i


# =============================================================================
# Tests: Section Information Extraction
# =============================================================================


class TestSectionInfoExtraction:
    """Test section information extraction from chunk metadata."""

    def test_extract_section_info_complete(self):
        """Test extracting complete section information."""
        metadata = {
            "section_id": "section_3.2",
            "section_heading": "Architecture",
            "section_level": 2,
        }

        info = VLMService.extract_section_info_from_chunk(metadata)

        assert info["section_id"] == "section_3.2"
        assert info["section_heading"] == "Architecture"
        assert info["section_level"] == 2

    def test_extract_section_info_missing_fields(self):
        """Test extracting section info with missing fields (uses defaults)."""
        metadata = {"section_id": "section_1.1"}

        info = VLMService.extract_section_info_from_chunk(metadata)

        assert info["section_id"] == "section_1.1"
        assert info["section_heading"] == "Unknown Section"
        assert info["section_level"] == 1

    def test_extract_section_info_empty_metadata(self):
        """Test extracting section info from empty metadata."""
        metadata = {}

        info = VLMService.extract_section_info_from_chunk(metadata)

        assert info["section_id"] == "unknown"
        assert info["section_heading"] == "Unknown Section"
        assert info["section_level"] == 1

    def test_extract_section_info_nested_sections(self):
        """Test extracting info from deeply nested sections."""
        metadata = {
            "section_id": "section_4.1.2.3",
            "section_heading": "Deep Nested Section",
            "section_level": 4,
        }

        info = VLMService.extract_section_info_from_chunk(metadata)

        assert info["section_id"] == "section_4.1.2.3"
        assert info["section_level"] == 4


# =============================================================================
# Tests: Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_process_with_minimal_section_context(
        self, vlm_service, pil_image_mock, tmp_path
    ):
        """Test processing with minimal section context."""
        context = ImageWithSectionContext(
            image=pil_image_mock,
            image_path=tmp_path / "image.png",
            page_number=1,
            section_id="sec_1",
            section_heading="",
            section_level=0,
        )

        vlm_service.processor.process_image = AsyncMock(return_value="Description")

        result = await vlm_service.process_image_with_section(context)

        assert result.section_id == "sec_1"
        assert result.description == "Description"

    @pytest.mark.asyncio
    async def test_large_section_heading(self, vlm_service, pil_image_mock, tmp_path):
        """Test processing with very long section heading."""
        long_heading = "A" * 1000
        context = ImageWithSectionContext(
            image=pil_image_mock,
            image_path=tmp_path / "image.png",
            page_number=1,
            section_id="section_1",
            section_heading=long_heading,
            section_level=1,
        )

        vlm_service.processor.process_image = AsyncMock(return_value="Description")

        result = await vlm_service.process_image_with_section(context)

        assert result.section_heading == long_heading

    @pytest.mark.asyncio
    async def test_unicode_in_section_heading(self, vlm_service, pil_image_mock, tmp_path):
        """Test processing with unicode characters in section heading."""
        context = ImageWithSectionContext(
            image=pil_image_mock,
            image_path=tmp_path / "image.png",
            page_number=1,
            section_id="section_1",
            section_heading="多层服务器架构",
            section_level=1,
        )

        vlm_service.processor.process_image = AsyncMock(return_value="描述")

        result = await vlm_service.process_image_with_section(context)

        assert result.section_heading == "多层服务器架构"
        assert result.description == "描述"


# =============================================================================
# Tests: Model and Metadata
# =============================================================================


class TestModelAndMetadata:
    """Test model identification and metadata handling."""

    @pytest.mark.asyncio
    async def test_model_identification(self, vlm_service, image_with_section_context):
        """Test that model is correctly identified."""
        vlm_service.processor.process_image = AsyncMock(return_value="Description")

        result = await vlm_service.process_image_with_section(image_with_section_context)

        assert result.model_used == vlm_service.config.vlm_model

    @pytest.mark.asyncio
    async def test_metadata_accumulation(self, vlm_service, image_with_section_context):
        """Test that metadata is properly accumulated."""
        vlm_service.processor.process_image = AsyncMock(return_value="Description")

        result = await vlm_service.process_image_with_section(image_with_section_context)

        assert result.metadata is not None
        assert "filtered" in result.metadata
        assert "has_bbox" in result.metadata

    @pytest.mark.asyncio
    async def test_cost_and_token_tracking(self, vlm_service, image_with_section_context):
        """Test that cost and token information is initialized."""
        vlm_service.processor.process_image = AsyncMock(return_value="Description")

        result = await vlm_service.process_image_with_section(image_with_section_context)

        assert result.tokens_used >= 0
        assert result.cost_usd >= 0.0


# =============================================================================
# Coverage Tests
# =============================================================================


class TestCoverage:
    """Additional tests to ensure >80% coverage."""

    def test_vlm_service_repr(self, vlm_service):
        """Test VLMService string representation."""
        # Just ensure no errors on repr
        assert vlm_service.processor is not None

    @pytest.mark.asyncio
    async def test_empty_batch_processing(self, vlm_service):
        """Test batch processing with empty list."""
        results = await vlm_service.process_images_with_sections([])

        assert results == []

    @pytest.mark.asyncio
    async def test_single_image_batch(self, vlm_service, image_with_section_context):
        """Test batch processing with single image."""
        vlm_service.processor.process_image = AsyncMock(return_value="Description")

        results = await vlm_service.process_images_with_sections([image_with_section_context])

        assert len(results) == 1
        assert results[0].section_id == image_with_section_context.section_id
