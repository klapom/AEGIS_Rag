"""Qwen3-VL Image Processor - Feature 21.6.

This module provides image processing capabilities using the Qwen3-VL-4B-Instruct model
via Ollama for generating intelligent image descriptions.

Key Decisions:
- Simple, natural language prompts (Qwen3-VL best practice)
- NOT complex JSON instructions
- Default temperature: 0.7 (Qwen3-VL default)
- Image filtering by size and aspect ratio

Architecture:
- Qwen3-VL via Ollama (local, ~5-6GB VRAM)
- Image filtering before VLM processing
- Temporary file handling for PIL images
- Error handling with retry logic
"""

import asyncio
import os
import tempfile
from pathlib import Path

import ollama
import structlog
from PIL import Image

from src.core.config import get_settings

logger = structlog.get_logger(__name__)

# Sprint 23: Import DashScope VLM Client for cloud VLM routing
try:
    from src.components.llm_proxy.dashscope_vlm import get_dashscope_vlm_client
    DASHSCOPE_VLM_AVAILABLE = True
except ImportError:
    DASHSCOPE_VLM_AVAILABLE = False
    logger.warning("DashScope VLM not available, using direct Ollama only")


# =============================================================================
# Configuration
# =============================================================================

class ImageProcessorConfig:
    """Configuration for image processing.

    Attributes:
        vlm_model: Ollama model identifier
        temperature: Sampling temperature (0.0-1.0)
        top_p: Nucleus sampling parameter
        top_k: Top-k sampling parameter
        num_ctx: Context window size
        num_gpu: Number of GPU layers (rest offloaded to CPU)
        min_size: Minimum image size (width or height)
        min_aspect_ratio: Minimum aspect ratio
        max_aspect_ratio: Maximum aspect ratio
    """

    def __init__(self):
        settings = get_settings()

        # VLM Settings (from config or defaults)
        self.vlm_model = getattr(settings, "qwen3vl_model", "qwen3-vl:4b-instruct")
        self.temperature = getattr(settings, "qwen3vl_temperature", 0.7)
        self.top_p = getattr(settings, "qwen3vl_top_p", 0.8)
        self.top_k = getattr(settings, "qwen3vl_top_k", 20)
        self.num_ctx = getattr(settings, "qwen3vl_num_ctx", 4096)

        # GPU Layer Offloading (Sprint 21 Feature 21.6)
        # For RTX 3060 6GB: Use 10 GPU layers to reduce VRAM requirement
        # Set to -1 to use all GPU layers (default), or specify layer count for CPU offloading
        self.num_gpu = getattr(settings, "qwen3vl_num_gpu", 10)

        # Image Filtering
        self.min_size = getattr(settings, "image_min_size", 100)
        self.min_aspect_ratio = getattr(settings, "image_min_aspect_ratio", 0.1)
        self.max_aspect_ratio = getattr(settings, "image_max_aspect_ratio", 10.0)


# =============================================================================
# Image Filtering
# =============================================================================

def should_process_image(
    image: Image.Image,
    min_size: int = 100,
    min_aspect_ratio: float = 0.1,
    max_aspect_ratio: float = 10.0,
) -> tuple[bool, str]:
    """Determine if an image should be processed by VLM.

    Args:
        image: PIL Image object
        min_size: Minimum width or height in pixels
        min_aspect_ratio: Minimum aspect ratio (width/height)
        max_aspect_ratio: Maximum aspect ratio

    Returns:
        Tuple of (should_process: bool, reason: str)

    Examples:
        >>> img = Image.new('RGB', (200, 200))
        >>> should_process_image(img)
        (True, 'valid')

        >>> small_img = Image.new('RGB', (50, 50))
        >>> should_process_image(small_img)
        (False, 'too_small')
    """
    width, height = image.size

    # Check minimum size
    if width < min_size or height < min_size:
        return False, f"too_small: {width}x{height} < {min_size}px"

    # Check aspect ratio
    aspect_ratio = width / height
    if aspect_ratio < min_aspect_ratio:
        return False, f"aspect_ratio_too_low: {aspect_ratio:.2f} < {min_aspect_ratio}"

    if aspect_ratio > max_aspect_ratio:
        return False, f"aspect_ratio_too_high: {aspect_ratio:.2f} > {max_aspect_ratio}"

    return True, "valid"


# =============================================================================
# VLM Description Generation
# =============================================================================

async def generate_vlm_description_with_dashscope(
    image_path: Path,
    prompt_template: str | None = None,
    vl_high_resolution_images: bool = False,
) -> str:
    """Generate image description using DashScope VLM (Cloud VLM).

    Sprint 23: Uses DashScope VLM API directly with best practices:
    - Primary: qwen3-vl-30b-a3b-instruct (cheaper output tokens)
    - Fallback: qwen3-vl-30b-a3b-thinking (on 403 errors)
    - Low-resolution mode (2,560 tokens) provides excellent results at lower cost

    Args:
        image_path: Path to image file
        prompt_template: Custom prompt (optional)
        vl_high_resolution_images: Use high-res processing (default: False, low-res sufficient)

    Returns:
        VLM-generated description text

    Raises:
        RuntimeError: If VLM generation fails
        FileNotFoundError: If image file doesn't exist
    """
    if not DASHSCOPE_VLM_AVAILABLE:
        raise RuntimeError("DashScope VLM not available, cannot use cloud VLM")

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Default prompt (Qwen3-VL best practice: simple and direct)
    if prompt_template is None:
        prompt = (
            "Describe this image from a document in detail, including any text, "
            "diagrams, charts, or important visual elements."
        )
    else:
        prompt = prompt_template

    try:
        logger.info(
            "Generating VLM description with DashScope",
            image_path=str(image_path),
            vl_high_res=vl_high_resolution_images,
        )

        # Get DashScope VLM client
        client = await get_dashscope_vlm_client()

        # Generate with automatic fallback (instruct → thinking on 403)
        description, metadata = await client.generate_with_fallback(
            image_path=image_path,
            prompt=prompt,
            primary_model="qwen3-vl-30b-a3b-instruct",
            fallback_model="qwen3-vl-30b-a3b-thinking",
            vl_high_resolution_images=vl_high_resolution_images,
        )

        logger.info(
            "VLM description generated via DashScope",
            model=metadata["model"],
            tokens_total=metadata["tokens_total"],
            description_length=len(description),
            fallback_used=metadata.get("fallback_used", False),
        )

        # Close client
        await client.close()

        return description

    except Exception as e:
        logger.error(
            "DashScope VLM description failed",
            error=str(e),
            image_path=str(image_path),
        )
        raise RuntimeError(f"DashScope VLM request failed: {e}") from e


def generate_vlm_description(
    image_path: Path,
    model: str = "qwen3-vl:4b-instruct",
    temperature: float = 0.7,
    top_p: float = 0.8,
    top_k: int = 20,
    num_ctx: int = 4096,
    num_gpu: int = 15,
    prompt_template: str | None = None,
) -> str:
    """Generate image description using Qwen3-VL via Ollama.

    Qwen3-VL Best Practice:
    - Use simple, natural language prompts
    - Do NOT use complex JSON instructions
    - Default temperature: 0.7 (model default)

    Args:
        image_path: Path to image file
        model: Ollama model identifier
        temperature: Sampling temperature (0.0-1.0)
        top_p: Nucleus sampling parameter
        top_k: Top-k sampling parameter
        num_ctx: Context window size
        num_gpu: Number of GPU layers (rest offloaded to CPU, default 15 for RTX 3060 6GB)
        prompt_template: Custom prompt (optional)

    Returns:
        VLM-generated description text

    Raises:
        RuntimeError: If Ollama request fails
        FileNotFoundError: If image file doesn't exist

    Examples:
        >>> desc = generate_vlm_description(
        ...     Path("/tmp/image.png"),
        ...     model="qwen3-vl:4b-instruct"
        ... )
        >>> assert len(desc) > 0
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Default prompt (Qwen3-VL best practice: simple and direct)
    if prompt_template is None:
        prompt = (
            "Describe this image from a document in detail, including any text, "
            "diagrams, charts, or important visual elements."
        )
    else:
        prompt = prompt_template

    try:
        logger.info(
            "Generating VLM description",
            image_path=str(image_path),
            model=model,
            temperature=temperature,
            num_gpu=num_gpu,
        )

        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [str(image_path)],
                }
            ],
            options={
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "num_ctx": num_ctx,
                "num_gpu": num_gpu,
            },
        )

        description = response["message"]["content"]

        logger.info(
            "VLM description generated",
            description_length=len(description),
            first_100_chars=description[:100],
        )

        return description

    except Exception as e:
        logger.error(
            "VLM description failed",
            error=str(e),
            image_path=str(image_path),
        )
        raise RuntimeError(f"Ollama VLM request failed: {e}") from e


# =============================================================================
# Image Processor Class
# =============================================================================

class ImageProcessor:
    """Image processor for VLM-enhanced document ingestion.

    This class handles:
    - Image filtering (size, aspect ratio)
    - Temporary file management
    - VLM description generation via Ollama
    - Error handling and logging

    Example:
        >>> processor = ImageProcessor()
        >>> image = Image.open("document_image.png")
        >>> description = processor.process_image(image)
        >>> print(description)
    """

    def __init__(self, config: ImageProcessorConfig | None = None):
        """Initialize image processor.

        Args:
            config: Optional configuration (uses defaults if None)
        """
        self.config = config or ImageProcessorConfig()
        self.temp_dir = Path(tempfile.gettempdir()) / "aegis_vlm_images"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Track temporary files for cleanup
        self.temp_files: list[Path] = []

        logger.info(
            "ImageProcessor initialized",
            model=self.config.vlm_model,
            temp_dir=str(self.temp_dir),
        )

    def process_image(
        self,
        image: Image.Image,
        picture_index: int,
        skip_filtering: bool = False,
        use_proxy: bool = True,
    ) -> str | None:
        """Process a single image with VLM.

        Args:
            image: PIL Image object
            picture_index: Index of image (for temp file naming)
            skip_filtering: If True, skip size/aspect ratio checks
            use_proxy: If True, use AegisLLMProxy for cloud VLM routing (default)

        Returns:
            VLM description or None if image filtered out

        Example:
            >>> processor = ImageProcessor()
            >>> img = Image.new('RGB', (500, 500))
            >>> desc = processor.process_image(img, picture_index=0)
        """
        # Image filtering
        if not skip_filtering:
            should_process, reason = should_process_image(
                image,
                min_size=self.config.min_size,
                min_aspect_ratio=self.config.min_aspect_ratio,
                max_aspect_ratio=self.config.max_aspect_ratio,
            )

            if not should_process:
                logger.info(
                    "Image filtered out",
                    picture_index=picture_index,
                    reason=reason,
                    size=f"{image.size[0]}x{image.size[1]}",
                )
                return None

        # Save image temporarily
        temp_path = self.temp_dir / f"image_{picture_index}.png"

        try:
            image.save(temp_path, format="PNG")
            self.temp_files.append(temp_path)  # Track for cleanup
            logger.debug(
                "Image saved temporarily",
                path=str(temp_path),
                total_temp_files=len(self.temp_files),
            )

            # Generate VLM description
            # Sprint 23: Use DashScope VLM for cloud routing (instruct primary, thinking fallback)
            if use_proxy and DASHSCOPE_VLM_AVAILABLE:
                logger.info(
                    "Using DashScope VLM for description",
                    picture_index=picture_index,
                    routing="cloud_vlm_with_fallback",
                )
                # Run async function in sync context
                # Check if we're already in an event loop
                try:
                    asyncio.get_running_loop()
                    # Already in event loop - use ThreadPoolExecutor to avoid nested loop error
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            generate_vlm_description_with_dashscope(
                                image_path=temp_path,
                                vl_high_resolution_images=False,
                            )
                        )
                        description = future.result()
                except RuntimeError:
                    # Not in event loop - use asyncio.run
                    description = asyncio.run(
                        generate_vlm_description_with_dashscope(
                            image_path=temp_path,
                            vl_high_resolution_images=False,
                        )
                    )
            else:
                logger.info(
                    "Using direct Ollama for VLM description",
                    picture_index=picture_index,
                    routing="local_only",
                    reason="proxy_disabled" if not use_proxy else "proxy_unavailable",
                )
                description = generate_vlm_description(
                    image_path=temp_path,
                    model=self.config.vlm_model,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    top_k=self.config.top_k,
                    num_ctx=self.config.num_ctx,
                    num_gpu=self.config.num_gpu,
                )

            logger.info(
                "Image processed successfully",
                picture_index=picture_index,
                description_length=len(description) if description else 0,
            )

            return description

        except Exception as e:
            logger.error(
                "Image processing failed",
                picture_index=picture_index,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def cleanup(self):
        """Clean up temporary files and directory."""
        # First, clean up tracked temp files
        files_deleted = 0
        files_failed = 0

        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    os.remove(temp_file)
                    files_deleted += 1
                    logger.debug("Temp file deleted", path=str(temp_file))
            except Exception as e:
                files_failed += 1
                logger.warning(
                    "Failed to delete temp file",
                    path=str(temp_file),
                    error=str(e),
                )

        # Clear the temp_files list
        self.temp_files.clear()

        logger.info(
            "Temp files cleanup complete",
            files_deleted=files_deleted,
            files_failed=files_failed,
        )

        # Then, clean up the temp directory
        try:
            import shutil

            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info("Temp directory cleaned up", path=str(self.temp_dir))
        except Exception as e:
            logger.warning(
                "Failed to cleanup temp directory",
                path=str(self.temp_dir),
                error=str(e),
            )


# =============================================================================
# Convenience Function
# =============================================================================

def process_image_with_vlm(
    image: Image.Image,
    picture_index: int = 0,
    model: str = "qwen3-vl:4b-instruct",
    skip_filtering: bool = False,
    use_proxy: bool = True,
) -> str | None:
    """Convenience function to process a single image.

    Args:
        image: PIL Image object
        picture_index: Index for temp file naming
        model: Ollama model identifier (used only if use_proxy=False)
        skip_filtering: Skip size/aspect checks
        use_proxy: Use AegisLLMProxy for cloud VLM routing (default: True)

    Returns:
        VLM description or None if filtered out

    Example:
        >>> img = Image.open("diagram.png")
        >>> desc = process_image_with_vlm(img)  # Uses cloud VLM via proxy
        >>> print(desc)
    """
    config = ImageProcessorConfig()
    config.vlm_model = model

    processor = ImageProcessor(config=config)

    try:
        return processor.process_image(
            image=image,
            picture_index=picture_index,
            skip_filtering=skip_filtering,
            use_proxy=use_proxy,
        )
    finally:
        processor.cleanup()
