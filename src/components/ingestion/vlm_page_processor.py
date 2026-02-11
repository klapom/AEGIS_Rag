"""VLM parallel page processor for table extraction.

Sprint 129.6g: Sends ALL document pages to Nemotron VL v1 via asyncio.gather()
for parallel table extraction. Results are stored in ingestion state and used
by the cross-validator to compare with Docling's heuristic extraction.

Architecture:
    1. Render all pages as PNG (PyMuPDF, ~20ms/page)
    2. Send all pages to VLM in parallel (asyncio.gather, ~12-15s/page)
    3. Collect VLM-extracted tables per page
    4. Store in state["vlm_page_results"] for downstream use

The VLM container (aegis-vlm-table, port 8002) runs the same base image
as the extraction vLLM (aegis-vllm-eugr) — zero additional disk space.
"""

import asyncio
import time
from dataclasses import dataclass, field

import structlog

from src.components.ingestion.vlm_table_clients import NemotronVLClient

logger = structlog.get_logger(__name__)


@dataclass
class VLMPageResult:
    """VLM extraction result for a single page."""

    page_no: int
    tables: list[list[list[str]]]  # List of tables, each as 2D cell grid
    processing_time_ms: float = 0.0
    error: str | None = None


@dataclass
class VLMProcessingResult:
    """Aggregate result of VLM processing across all pages."""

    page_results: dict[int, VLMPageResult] = field(default_factory=dict)
    total_pages: int = 0
    pages_with_tables: int = 0
    total_tables: int = 0
    total_processing_time_ms: float = 0.0
    vlm_available: bool = False


class VLMPageProcessor:
    """Processes all document pages through VLM for table extraction.

    Renders all pages as PNG, sends them to VLM in parallel via asyncio.gather(),
    and returns structured results per page.
    """

    def __init__(self, vlm_url: str = "http://localhost:8002"):
        self._client = NemotronVLClient(base_url=vlm_url)

    async def check_availability(self) -> bool:
        """Check if VLM service is reachable."""
        available = await self._client.health_check()
        logger.info("vlm_page_processor_availability", available=available)
        return available

    async def process_all_pages(
        self,
        page_images: dict[int, bytes],
        max_concurrent: int = 4,
    ) -> VLMProcessingResult:
        """Send all page images to VLM for table extraction in parallel.

        Args:
            page_images: Dict mapping 1-based page numbers to PNG bytes
            max_concurrent: Maximum concurrent VLM requests (default 4,
                limited by VLM GPU memory for concurrent image processing)

        Returns:
            VLMProcessingResult with per-page table extraction results
        """
        start = time.perf_counter()
        result = VLMProcessingResult(total_pages=len(page_images))

        if not page_images:
            return result

        # Check VLM availability
        result.vlm_available = await self.check_availability()
        if not result.vlm_available:
            logger.warning("vlm_page_processor_unavailable")
            return result

        # Use semaphore to limit concurrent VLM requests
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _process_page(page_no: int, image_bytes: bytes) -> VLMPageResult:
            async with semaphore:
                page_start = time.perf_counter()
                try:
                    tables = await self._client.extract_tables_from_page(image_bytes)
                    elapsed_ms = (time.perf_counter() - page_start) * 1000
                    return VLMPageResult(
                        page_no=page_no,
                        tables=tables,
                        processing_time_ms=round(elapsed_ms, 1),
                    )
                except Exception as e:
                    elapsed_ms = (time.perf_counter() - page_start) * 1000
                    logger.warning(
                        "vlm_page_processing_error",
                        page_no=page_no,
                        error=repr(e),
                    )
                    return VLMPageResult(
                        page_no=page_no,
                        tables=[],
                        processing_time_ms=round(elapsed_ms, 1),
                        error=repr(e),
                    )

        # Process all pages in parallel (bounded by semaphore)
        tasks = [
            _process_page(page_no, image_bytes)
            for page_no, image_bytes in sorted(page_images.items())
        ]
        page_results = await asyncio.gather(*tasks)

        # Aggregate results
        for pr in page_results:
            result.page_results[pr.page_no] = pr
            if pr.tables:
                result.pages_with_tables += 1
                result.total_tables += len(pr.tables)

        total_ms = (time.perf_counter() - start) * 1000
        result.total_processing_time_ms = round(total_ms, 1)

        logger.info(
            "vlm_page_processing_complete",
            total_pages=result.total_pages,
            pages_with_tables=result.pages_with_tables,
            total_tables=result.total_tables,
            total_time_ms=result.total_processing_time_ms,
            avg_time_per_page_ms=(round(total_ms / len(page_images), 1) if page_images else 0),
        )

        return result
