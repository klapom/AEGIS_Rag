"""Debug script to analyze Docling image extraction.

Sprint 23 - Debugging base64 image availability in Docling output.
"""

import asyncio
import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from src.components.ingestion.docling_client import DoclingContainerClient

logger = structlog.get_logger(__name__)


def extract_base64_images_from_markdown(markdown: str) -> list[dict]:
    """Extract base64 images from markdown content.

    Returns:
        List of dicts with image info (format, data_length, preview)
    """
    # Pattern: ![alt](data:image/png;base64,iVBORw0KGgo...)
    pattern = r"!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)"

    matches = re.findall(pattern, markdown)

    images = []
    for alt_text, img_format, base64_data in matches:
        images.append(
            {
                "alt_text": alt_text,
                "format": img_format,
                "data_length": len(base64_data),
                "preview": base64_data[:50] + "...",  # First 50 chars
            }
        )

    return images


async def debug_docling_output():
    """Debug Docling parsed document structure."""
    pdf_path = project_root / "data" / "sample_documents" / "preview_mega.pdf"

    if not pdf_path.exists():
        logger.error("PDF not found", path=str(pdf_path))
        return

    logger.info("=" * 80)
    logger.info("DOCLING IMAGE EXTRACTION DEBUG")
    logger.info("=" * 80)
    logger.info("PDF", path=str(pdf_path))

    client = DoclingContainerClient(base_url="http://localhost:8080")

    try:
        async with client:
            logger.info("Parsing with Docling...")
            parsed = await client.parse_document(pdf_path)

            logger.info("=" * 80)
            logger.info("PARSED DOCUMENT STRUCTURE")
            logger.info("=" * 80)

            # Check attributes
            logger.info(
                "Attributes",
                has_text=hasattr(parsed, "text"),
                has_metadata=hasattr(parsed, "metadata"),
                has_tables=hasattr(parsed, "tables"),
                has_images=hasattr(parsed, "images"),
                has_layout=hasattr(parsed, "layout"),
                has_md_content=hasattr(parsed, "md_content"),
                has_json_content=hasattr(parsed, "json_content"),
                has_document=hasattr(parsed, "document"),
            )  # ❌ Should be False

            logger.info("=" * 80)
            logger.info("PARSED.IMAGES (references)")
            logger.info("=" * 80)
            logger.info("Count", count=len(parsed.images))

            if parsed.images:
                for i, img_ref in enumerate(parsed.images[:3]):  # Show first 3
                    logger.info(f"Image {i}", ref=img_ref)

            logger.info("=" * 80)
            logger.info("PARSED.MD_CONTENT (markdown with base64)")
            logger.info("=" * 80)
            logger.info("Markdown length", length=len(parsed.md_content))

            # Extract base64 images from markdown
            base64_images = extract_base64_images_from_markdown(parsed.md_content)
            logger.info("Base64 images found", count=len(base64_images))

            if base64_images:
                for i, img in enumerate(base64_images[:5]):  # Show first 5
                    logger.info(
                        f"Base64 Image {i}",
                        alt=img["alt_text"],
                        format=img["format"],
                        size_kb=img["data_length"] / 1024,
                        preview=img["preview"],
                    )

            # Check if we can decode base64 to PIL
            if base64_images:
                import base64
                from io import BytesIO
                from PIL import Image

                logger.info("=" * 80)
                logger.info("TEST: Decode first base64 image to PIL")
                logger.info("=" * 80)

                try:
                    first_img = base64_images[0]
                    img_data = base64.b64decode(first_img["preview"].replace("...", ""))
                    # Note: This will fail because we only have 50 chars, but shows the pattern

                    # Try with full data from regex
                    pattern = r"!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)"
                    match = re.search(pattern, parsed.md_content)
                    if match:
                        full_base64 = match.group(3)
                        img_data = base64.b64decode(full_base64)
                        pil_image = Image.open(BytesIO(img_data))
                        logger.info(
                            "SUCCESS: PIL Image created",
                            size=pil_image.size,
                            mode=pil_image.mode,
                            format=pil_image.format,
                        )
                except Exception as e:
                    logger.error("Failed to decode", error=str(e))

            logger.info("=" * 80)
            logger.info("CONCLUSION")
            logger.info("=" * 80)

            if base64_images:
                logger.info(
                    "✅ Base64 images ARE available in md_content!",
                    count=len(base64_images),
                    recommendation="Can extract and pass to VLM",
                )
            else:
                logger.info(
                    "❌ No base64 images found in md_content",
                    recommendation="Check Docling configuration or use different extraction method",
                )

    except Exception as e:
        logger.error("Debug failed", error=str(e), error_type=type(e).__name__)
        raise


if __name__ == "__main__":
    asyncio.run(debug_docling_output())
