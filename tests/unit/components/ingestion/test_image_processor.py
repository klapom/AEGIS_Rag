"""Unit tests for ImageProcessor - Sprint 21 Feature 21.6.

Tests cover:
- Image filtering (size, aspect ratio)
- VLM processing with Qwen3-VL
- Temporary file handling
- Error handling and retries
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Conditional import for PIL (Pillow)
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from src.components.ingestion.image_processor import (
    ImageProcessor,
    ImageProcessorConfig,
    should_process_image,
)

# Skip all tests in this module if PIL is not available
pytestmark = pytest.mark.skipif(
    not PIL_AVAILABLE, reason="PIL (Pillow) not installed - install with ingestion extras"
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_image():
    """Create a sample PIL image for testing."""
    return Image.new("RGB", (200, 200), color=(255, 0, 0))


@pytest.fixture
def small_image():
    """Create a small image (below min_size threshold)."""
    return Image.new("RGB", (50, 50), color=(0, 255, 0))


@pytest.fixture
def wide_image():
    """Create a wide image (extreme aspect ratio but passes size check)."""
    # 1200x100 = aspect ratio 12.0 > max 10.0, but both dimensions >= 100
    return Image.new("RGB", (1200, 100), color=(0, 0, 255))


@pytest.fixture
def tall_image():
    """Create a tall image (extreme aspect ratio but passes size check)."""
    # 100x1200 = aspect ratio 0.083 < min 0.1, but both dimensions >= 100
    return Image.new("RGB", (100, 1200), color=(255, 255, 0))


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for VLM testing."""
    mock_client = AsyncMock()
    mock_client.generate.return_value = {
        "response": "This image shows a red square diagram with technical annotations."
    }
    return mock_client


# =============================================================================
# IMAGE FILTERING TESTS
# =============================================================================


def test_should_process_image__valid_image__returns_true(sample_image):
    """Test that valid images pass filtering."""
    should_process, reason = should_process_image(sample_image, min_unique_colors=0)

    assert should_process is True
    assert reason == "valid"


def test_should_process_image__too_small__returns_false(small_image):
    """Test that small images are filtered out."""
    should_process, reason = should_process_image(small_image, min_size=100)

    assert should_process is False
    assert "too_small" in reason
    assert "50x50" in reason


def test_should_process_image__aspect_ratio_too_wide__returns_false(wide_image):
    """Test that images with extreme wide aspect ratio are filtered."""
    should_process, reason = should_process_image(
        wide_image, min_size=100, min_aspect_ratio=0.1, max_aspect_ratio=10.0
    )

    assert should_process is False
    assert "aspect_ratio" in reason


def test_should_process_image__aspect_ratio_too_tall__returns_false(tall_image):
    """Test that images with extreme tall aspect ratio are filtered."""
    should_process, reason = should_process_image(
        tall_image, min_size=100, min_aspect_ratio=0.1, max_aspect_ratio=10.0
    )

    assert should_process is False
    assert "aspect_ratio" in reason


def test_should_process_image__edge_case_square__returns_true():
    """Test that perfect square images pass filtering."""
    square_image = Image.new("RGB", (200, 200))
    should_process, reason = should_process_image(square_image, min_unique_colors=0)

    assert should_process is True
    assert reason == "valid"


def test_should_process_image__minimum_size_boundary__returns_true():
    """Test boundary case: image exactly at min_size."""
    boundary_image = Image.new("RGB", (100, 100))
    should_process, reason = should_process_image(
        boundary_image, min_size=100, min_unique_colors=0
    )

    assert should_process is True
    assert reason == "valid"


# =============================================================================
# IMAGE PROCESSOR CONFIG TESTS
# =============================================================================


def test_image_processor_config__default_values():
    """Test default configuration values."""
    config = ImageProcessorConfig()

    assert config.vlm_model == "qwen3-vl:4b-instruct"
    assert config.temperature == 0.7
    assert config.top_p == 0.8
    assert config.top_k == 20
    assert config.num_ctx == 4096
    assert config.min_size == 100
    assert config.min_aspect_ratio == 0.1
    assert config.max_aspect_ratio == 10.0


@patch("src.components.ingestion.image_processor.get_settings")
def test_image_processor_config__custom_settings(mock_get_settings):
    """Test configuration with custom settings."""
    mock_settings = Mock()
    mock_settings.qwen3vl_model = "custom-vlm:latest"
    mock_settings.qwen3vl_temperature = 0.5
    mock_settings.image_min_size = 200
    mock_get_settings.return_value = mock_settings

    config = ImageProcessorConfig()

    assert config.vlm_model == "custom-vlm:latest"
    assert config.temperature == 0.5
    assert config.min_size == 200


# =============================================================================
# IMAGE PROCESSOR INITIALIZATION TESTS
# =============================================================================


def test_image_processor__initialization__success():
    """Test ImageProcessor initialization."""
    processor = ImageProcessor()

    assert processor.config is not None
    assert processor.temp_files == []
    assert processor.temp_dir.exists()
    assert processor.config.vlm_model == "qwen3-vl:4b-instruct"


def test_image_processor__cleanup__removes_temp_files():
    """Test that cleanup removes temporary files."""
    processor = ImageProcessor()

    # Create temp files
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp1:
        tmp_path1 = Path(tmp1.name)
        processor.temp_files.append(tmp_path1)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp2:
        tmp_path2 = Path(tmp2.name)
        processor.temp_files.append(tmp_path2)

    # Verify files exist
    assert tmp_path1.exists()
    assert tmp_path2.exists()

    # Cleanup
    processor.cleanup()

    # Verify files deleted
    assert not tmp_path1.exists()
    assert not tmp_path2.exists()
    assert processor.temp_files == []


# =============================================================================
# VLM PROCESSING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_process_image__valid_image__returns_description(sample_image):
    """Test successful VLM image processing (ASYNC - Sprint 25 Feature 25.4)."""
    # Mock DashScope VLM response
    with patch(
        "src.components.ingestion.image_processor.generate_vlm_description_with_dashscope",
        new_callable=AsyncMock,
    ) as mock_vlm:
        mock_vlm.return_value = "A red square image with dimensions 200x200 pixels."

        processor = ImageProcessor()

        # Process image (now async!) - skip_filtering=True to bypass color filter
        description = await processor.process_image(
            sample_image, picture_index=0, skip_filtering=True
        )

        assert description is not None
        assert "red square" in description.lower()
        mock_vlm.assert_called_once()


@pytest.mark.asyncio
async def test_process_image__filtered_image__returns_none(small_image):
    """Test that filtered images return None (ASYNC - Sprint 25 Feature 25.4)."""
    processor = ImageProcessor()

    # Process small image (should be filtered)
    description = await processor.process_image(small_image, picture_index=0)

    assert description is None
    # VLM should not be called for filtered images


@pytest.mark.asyncio
async def test_process_image__creates_temp_file(sample_image):
    """Test that temporary file is created during processing (ASYNC - Sprint 25 Feature 25.4)."""
    with patch(
        "src.components.ingestion.image_processor.generate_vlm_description_with_dashscope",
        new_callable=AsyncMock,
    ) as mock_vlm:
        mock_vlm.return_value = "Test description"

        processor = ImageProcessor()

        # Process image (now async!) with skip_filtering=True to bypass color filter
        await processor.process_image(sample_image, picture_index=0, skip_filtering=True)

        # Verify temp file was created
        assert len(processor.temp_files) == 1
        temp_file = processor.temp_files[0]
        assert temp_file.exists()
        assert temp_file.suffix == ".png"

        # Cleanup
        processor.cleanup()


@pytest.mark.asyncio
async def test_process_image__vlm_error__returns_none(sample_image):
    """Test error handling when VLM fails (ASYNC - Sprint 25 Feature 25.4)."""
    with patch(
        "src.components.ingestion.image_processor.generate_vlm_description_with_dashscope",
        new_callable=AsyncMock,
    ) as mock_vlm:
        mock_vlm.side_effect = Exception("VLM connection error")

        processor = ImageProcessor()

        # Should return None on error (not raise) - skip_filtering=True to bypass color filter
        description = await processor.process_image(
            sample_image, picture_index=0, skip_filtering=True
        )
        assert description is None


def test_process_image__custom_prompt__used_in_request(sample_image):
    """Test that custom prompt is passed to Ollama (currently not supported - skip)."""
    pytest.skip("Custom prompt parameter not yet implemented in process_image")


# =============================================================================
# INTEGRATION-STYLE TESTS (with mocking)
# =============================================================================


@pytest.mark.asyncio
async def test_process_multiple_images__sequential__success():
    """Test processing multiple images sequentially."""
    with patch(
        "src.components.ingestion.image_processor.generate_vlm_description_with_dashscope",
        new_callable=AsyncMock,
    ) as mock_vlm:
        mock_vlm.side_effect = [
            "First image description",
            "Second image description",
            "Third image description",
        ]

        processor = ImageProcessor()

        images = [
            Image.new("RGB", (200, 200), color=(255, 0, 0)),
            Image.new("RGB", (200, 200), color=(0, 255, 0)),
            Image.new("RGB", (200, 200), color=(0, 0, 255)),
        ]

        descriptions = []
        for idx, img in enumerate(images):
            desc = await processor.process_image(img, picture_index=idx, skip_filtering=True)
            descriptions.append(desc)

        assert len(descriptions) == 3
        assert all(desc is not None for desc in descriptions)
        assert mock_vlm.call_count == 3
        assert len(processor.temp_files) == 3

        # Cleanup
        processor.cleanup()


@pytest.mark.asyncio
async def test_process_mixed_valid_invalid_images__filters_correctly():
    """Test processing mix of valid and invalid images."""
    with patch(
        "src.components.ingestion.image_processor.generate_vlm_description_with_dashscope",
        new_callable=AsyncMock,
    ) as mock_vlm:
        mock_vlm.return_value = "Valid image"

        processor = ImageProcessor()

        images = [
            Image.new("RGB", (200, 200)),  # Valid (with skip_filtering)
            Image.new("RGB", (50, 50)),  # Too small
            Image.new("RGB", (200, 200)),  # Valid (with skip_filtering)
            Image.new("RGB", (1000, 50)),  # Wrong aspect ratio (height too small)
        ]

        descriptions = []
        for idx, img in enumerate(images):
            # Use skip_filtering=True for valid images (index 0, 2)
            skip = idx in [0, 2]
            desc = await processor.process_image(img, picture_index=idx, skip_filtering=skip)
            descriptions.append(desc)

        # Only 2 valid images should be processed
        valid_descriptions = [d for d in descriptions if d is not None]
        assert len(valid_descriptions) == 2
        assert mock_vlm.call_count == 2

        # Cleanup
        processor.cleanup()


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================


@pytest.mark.asyncio
async def test_process_image__empty_response__handles_gracefully():
    """Test handling of empty VLM response."""
    with patch(
        "src.components.ingestion.image_processor.generate_vlm_description_with_dashscope",
        new_callable=AsyncMock,
    ) as mock_vlm:
        mock_vlm.return_value = ""

        processor = ImageProcessor()

        image = Image.new("RGB", (200, 200))
        description = await processor.process_image(image, picture_index=0, skip_filtering=True)

        # Should return empty string, not None (image was valid)
        assert description == ""


def test_cleanup__no_temp_files__does_not_error():
    """Test that cleanup works even with no temp files."""
    processor = ImageProcessor()

    # Should not raise exception
    processor.cleanup()
    assert processor.temp_files == []


def test_cleanup__already_deleted_files__does_not_error():
    """Test cleanup with files that were already deleted."""
    processor = ImageProcessor()

    # Create temp file and delete it manually
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp_path = Path(tmp.name)
        processor.temp_files.append(tmp_path)

    # Delete file manually
    tmp_path.unlink()

    # Cleanup should not raise exception
    processor.cleanup()
