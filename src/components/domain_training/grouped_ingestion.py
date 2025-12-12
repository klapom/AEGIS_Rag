"""LLM-Grouped Batch Ingestion for Domain Training.

Sprint 45 - Feature 45.10: LLM-Grouped Ingestion (3 SP)

This module implements batch processing of documents grouped by LLM model to minimize
model switching overhead during ingestion. Documents are automatically grouped by their
target domain's LLM model configuration, enabling optimal GPU resource utilization.

Architecture:
    GroupedIngestionProcessor
    ├── Groups items by llm_model (largest batches first)
    ├── Loads each model once per batch
    ├── Processes all items for that model
    └── Reports progress and metrics by model/domain

Performance Benefits:
- Minimizes model loading overhead (load once per batch vs. per document)
- Optimal GPU memory utilization (sequential model loading)
- Reduced context switching between different models
- Predictable resource usage patterns

Example:
    >>> from src.components.domain_training import (
    ...     get_grouped_ingestion_processor,
    ...     IngestionItem
    ... )
    >>> processor = get_grouped_ingestion_processor()
    >>> items = [
    ...     IngestionItem(
    ...         file_path="/path/to/doc1.pdf",
    ...         text="Document text...",
    ...         domain="tech_docs",
    ...         llm_model="qwen3:32b"
    ...     ),
    ...     ...
    ... ]
    >>> results = await processor.process_batch(
    ...     items,
    ...     on_progress=lambda msg, pct: print(f"{msg}: {pct:.1f}%")
    ... )
    >>> print(results)
    {
        "processed": 100,
        "failed": 2,
        "by_model": {"qwen3:32b": 60, "llama3.2:8b": 40},
        "by_domain": {"tech_docs": 60, "legal_contracts": 40}
    }
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable

import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class IngestionItem:
    """Item to be ingested with domain and LLM model metadata.

    Attributes:
        file_path: Path to the source document
        text: Extracted text content to process
        domain: Target domain for extraction (e.g., "tech_docs")
        llm_model: LLM model to use for extraction (e.g., "qwen3:32b")
    """

    file_path: str
    text: str
    domain: str
    llm_model: str


@dataclass
class IngestionBatch:
    """Batch of items sharing the same LLM model.

    Groups items by model to enable sequential processing with a single
    model load operation per batch.

    Attributes:
        llm_model: Shared LLM model for all items in batch
        items: List of items to process with this model
    """

    llm_model: str
    items: list[IngestionItem]


class GroupedIngestionProcessor:
    """Processes documents grouped by LLM model to minimize model switching.

    This processor optimizes batch ingestion by grouping items by their target
    LLM model, then processing each group sequentially. This minimizes the
    overhead of loading and unloading models during extraction.

    Workflow:
    1. Group items by llm_model
    2. Sort groups by size (largest first)
    3. For each group:
       a. Load the model (warm-up)
       b. Process all items with that model
       c. Report progress
    4. Return aggregated metrics

    Attributes:
        _current_model: Currently loaded model name (for tracking)
    """

    def __init__(self) -> None:
        """Initialize grouped ingestion processor."""
        self._current_model: str | None = None
        logger.info("grouped_ingestion_processor_initialized")

    async def process_batch(
        self,
        items: list[IngestionItem],
        on_progress: Callable[[str, float], None] | None = None,
    ) -> dict[str, Any]:
        """Process items grouped by LLM model.

        Groups items by their target LLM model, then processes each group
        sequentially to avoid model switching overhead. Progress is reported
        via the callback function if provided.

        Args:
            items: List of items to process
            on_progress: Optional progress callback(message: str, percent: float)

        Returns:
            Dictionary with processing results:
            {
                "processed": int,           # Successfully processed items
                "failed": int,              # Failed items
                "by_model": dict[str, int], # Count per model
                "by_domain": dict[str, int] # Count per domain
            }

        Raises:
            Exception: Re-raises exceptions from individual item processing
        """
        # Group by LLM model
        batches = self._group_by_model(items)

        logger.info(
            "grouped_ingestion_start",
            total_items=len(items),
            model_groups=len(batches),
            models=[b.llm_model for b in batches],
        )

        results: dict[str, Any] = {
            "processed": 0,
            "failed": 0,
            "by_model": defaultdict(int),
            "by_domain": defaultdict(int),
        }

        total = len(items)
        processed = 0

        for batch in batches:
            batch_start_msg = f"Processing {len(batch.items)} items with {batch.llm_model}"
            if on_progress:
                on_progress(batch_start_msg, processed / total * 100)

            logger.info(
                "processing_batch",
                model=batch.llm_model,
                batch_size=len(batch.items),
                progress_percent=processed / total * 100,
            )

            # Load model once per batch
            await self._ensure_model_loaded(batch.llm_model)

            # Process all items in batch
            for item in batch.items:
                try:
                    await self._process_item(item)
                    results["processed"] += 1
                    results["by_model"][batch.llm_model] += 1
                    results["by_domain"][item.domain] += 1

                    logger.debug(
                        "item_processed",
                        file=item.file_path,
                        domain=item.domain,
                        model=item.llm_model,
                    )

                except Exception as e:
                    logger.error(
                        "item_processing_failed",
                        file=item.file_path,
                        domain=item.domain,
                        model=item.llm_model,
                        error=str(e),
                        exc_info=True,
                    )
                    results["failed"] += 1

                processed += 1
                if on_progress:
                    progress_pct = processed / total * 100
                    on_progress(f"Processed {item.file_path}", progress_pct)

        # Convert defaultdict to regular dict for JSON serialization
        results["by_model"] = dict(results["by_model"])
        results["by_domain"] = dict(results["by_domain"])

        logger.info(
            "grouped_ingestion_complete",
            total_items=len(items),
            processed=results["processed"],
            failed=results["failed"],
            model_groups=len(batches),
        )

        return results

    def _group_by_model(self, items: list[IngestionItem]) -> list[IngestionBatch]:
        """Group items by LLM model, sorted by group size descending.

        Sorts batches by size (largest first) to maximize efficiency by processing
        the largest model groups first, reducing the number of model switches.

        Args:
            items: List of items to group

        Returns:
            List of batches sorted by size (descending)
        """
        groups: dict[str, list[IngestionItem]] = defaultdict(list)
        for item in items:
            groups[item.llm_model].append(item)

        batches = [
            IngestionBatch(llm_model=model, items=items) for model, items in groups.items()
        ]

        # Sort by size descending (process largest batches first)
        batches.sort(key=lambda b: len(b.items), reverse=True)

        logger.debug(
            "items_grouped_by_model",
            total_items=len(items),
            model_count=len(batches),
            batch_sizes={b.llm_model: len(b.items) for b in batches},
        )

        return batches

    async def _ensure_model_loaded(self, model: str) -> None:
        """Ensure the specified model is loaded in Ollama.

        Performs a warm-up request to load the model into GPU memory if not
        already loaded. Subsequent requests with this model will be faster.

        Args:
            model: Model name (e.g., "qwen3:32b")

        Raises:
            httpx.HTTPError: If model loading fails
            httpx.TimeoutException: If warm-up request times out
        """
        if self._current_model == model:
            logger.debug("model_already_loaded", model=model)
            return

        logger.info(
            "switching_model",
            from_model=self._current_model,
            to_model=model,
        )

        try:
            from src.core.config import get_settings

            settings = get_settings()
            ollama_base_url = settings.ollama_base_url or "http://localhost:11434"

            async with httpx.AsyncClient(timeout=60.0) as client:
                # Warm up model by sending a simple request
                response = await client.post(
                    f"{ollama_base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": "Hello",
                        "stream": False,
                        "options": {"num_predict": 1},
                    },
                )
                response.raise_for_status()

            self._current_model = model
            logger.info("model_loaded", model=model)

        except httpx.TimeoutException as e:
            logger.error(
                "model_load_timeout",
                model=model,
                error=str(e),
            )
            raise

        except httpx.HTTPError as e:
            logger.error(
                "model_load_failed",
                model=model,
                error=str(e),
                exc_info=True,
            )
            raise

    async def _process_item(self, item: IngestionItem) -> None:
        """Process a single item (extraction + indexing).

        This method would integrate with the extraction service to:
        1. Get domain-specific prompts
        2. Extract entities and relations using the loaded LLM model
        3. Index results in Neo4j and Qdrant

        Currently a stub for Sprint 45.10, full integration in future sprints.

        Args:
            item: Item to process

        Raises:
            Exception: Re-raises any exceptions from extraction/indexing
        """
        # TODO: Integrate with ExtractionService and indexing pipeline
        # This is a placeholder for Sprint 45.10
        # Full implementation will be added in future sprints

        logger.debug(
            "processing_item",
            file=item.file_path,
            domain=item.domain,
            model=item.llm_model,
            text_length=len(item.text),
        )

        # Simulate processing delay (remove in production)
        await asyncio.sleep(0.01)

        # Future implementation:
        # from src.components.graph_rag import ExtractionService
        # from src.components.domain_training import DomainRepository
        #
        # # Get domain-specific prompts
        # repo = DomainRepository.get_instance()
        # domain = await repo.get_domain(item.domain)
        #
        # extraction_service = ExtractionService()
        # prompts = await extraction_service.get_extraction_prompts(item.domain)
        #
        # # Extract entities and relations
        # entities = await extraction_service.extract_entities(item.text, prompts)
        # relations = await extraction_service.extract_relations(item.text, prompts)
        #
        # # Index in Neo4j and Qdrant
        # await extraction_service.index_results(entities, relations)


# --- Singleton Pattern ---

_processor: GroupedIngestionProcessor | None = None


def get_grouped_ingestion_processor() -> GroupedIngestionProcessor:
    """Get the singleton grouped ingestion processor instance.

    Returns:
        Shared processor instance

    Example:
        >>> processor = get_grouped_ingestion_processor()
        >>> results = await processor.process_batch(items)
    """
    global _processor
    if _processor is None:
        _processor = GroupedIngestionProcessor()
        logger.debug("grouped_ingestion_processor_singleton_created")
    return _processor


def reset_processor() -> None:
    """Reset the singleton processor instance.

    Useful for testing to ensure clean state between tests.
    """
    global _processor
    _processor = None
    logger.debug("grouped_ingestion_processor_singleton_reset")
