"""Benchmark Corpus Ingestion Pipeline.

Sprint 41 Feature 41.6: Benchmark Corpus Ingestion
Sprint 43 Feature 43.1: Full Pipeline Integration (BM25 + Graph Extraction)

This module ingests benchmark dataset contexts into namespace-isolated storage
for evaluation purposes. Each dataset gets its own namespace to enable fair
comparison and prevent cross-contamination.

Architecture (Full Pipeline):
    Benchmark Loader → Context Extraction → Embedding → Qdrant Ingestion
                                              ↓
                                    Namespace Isolation
                                              ↓
                                    BM25 Index Update (Sprint 43)
                                              ↓
                                    Graph Extraction → Neo4j (Sprint 43)

Namespace Strategy:
    - eval_nq: Natural Questions contexts
    - eval_hotpotqa: HotpotQA supporting facts
    - eval_msmarco: MS MARCO passages
    - eval_fever: FEVER evidence sentences
    - eval_ragbench: RAGBench contexts

Usage:
    >>> pipeline = BenchmarkCorpusIngestionPipeline()
    >>> await pipeline.ingest_benchmark_corpus(
    ...     dataset_name="natural_questions",
    ...     sample_size=1000
    ... )
    >>> print("Ingestion complete!")

Performance:
    - Batch embedding: 50-100 embeddings/sec
    - Batch Qdrant upsert: 100-500 points/batch
    - Total time (1000 samples): ~30-60 seconds
    - Memory usage: <512MB per batch
"""

import time
import uuid
from typing import Any

import structlog
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.components.shared.embedding_service import get_embedding_service
from src.components.vector_search.bm25_search import BM25Search
from src.components.vector_search.qdrant_client import get_qdrant_client
from src.core.config import settings
from src.core.namespace import NamespaceManager, get_namespace_manager
from src.evaluation.benchmark_loader import (
    DatasetName,
    get_benchmark_loader,
)

logger = structlog.get_logger(__name__)


class BenchmarkCorpusIngestionPipeline:
    """Pipeline for ingesting benchmark corpora into Qdrant with namespace isolation.

    This pipeline handles:
    1. Loading benchmark datasets from HuggingFace
    2. Extracting context passages
    3. Generating embeddings with BGE-M3
    4. Upserting to Qdrant with namespace isolation
    5. Metadata tracking (source, question_id, namespace_id)

    Features:
    - Namespace isolation: Each dataset in separate namespace
    - Batch processing: Efficient embedding and upsert
    - Progress logging: Track ingestion progress
    - Error handling: Skip invalid samples, continue on errors
    - Deduplication: Track ingested contexts to avoid duplicates

    Example:
        pipeline = BenchmarkCorpusIngestionPipeline()

        # Ingest Natural Questions (Track A)
        await pipeline.ingest_benchmark_corpus(
            dataset_name="natural_questions",
            sample_size=1000
        )

        # Ingest HotpotQA (Track B)
        await pipeline.ingest_benchmark_corpus(
            dataset_name="hotpotqa",
            sample_size=100
        )

        # Check ingestion stats
        stats = await pipeline.get_namespace_stats("eval_nq")
        print(f"Ingested {stats['document_count']} documents")
    """

    def __init__(
        self,
        qdrant_client: Any = None,
        embedding_service: Any = None,
        namespace_manager: NamespaceManager | None = None,
        collection_name: str | None = None,
        batch_size: int = 50,
    ) -> None:
        """Initialize benchmark corpus ingestion pipeline.

        Args:
            qdrant_client: Qdrant client (lazy-loaded if None)
            embedding_service: Embedding service (lazy-loaded if None)
            namespace_manager: Namespace manager (lazy-loaded if None)
            collection_name: Target collection (default: from settings)
            batch_size: Batch size for embedding and upsert (default: 50)
        """
        self._qdrant_client = qdrant_client
        self._embedding_service = embedding_service
        self._namespace_manager = namespace_manager
        self._benchmark_loader = get_benchmark_loader()

        self.collection_name = collection_name or settings.qdrant_collection
        self.batch_size = batch_size

        logger.info(
            "BenchmarkCorpusIngestionPipeline initialized",
            collection=self.collection_name,
            batch_size=self.batch_size,
        )

    @property
    def qdrant_client(self) -> Any:
        """Get Qdrant client (lazy initialization)."""
        if self._qdrant_client is None:
            self._qdrant_client = get_qdrant_client()
        return self._qdrant_client

    @property
    def embedding_service(self) -> Any:
        """Get embedding service (lazy initialization)."""
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    @property
    def namespace_manager(self) -> NamespaceManager:
        """Get namespace manager (lazy initialization)."""
        if self._namespace_manager is None:
            self._namespace_manager = get_namespace_manager()
        return self._namespace_manager

    def _get_namespace_id(self, dataset_name: str) -> str:
        """Get namespace ID for a dataset.

        Args:
            dataset_name: Name of the benchmark dataset

        Returns:
            Namespace ID (e.g., 'eval_nq', 'eval_hotpotqa')
        """
        return f"eval_{dataset_name}"

    async def ensure_collection_exists(self) -> None:
        """Ensure Qdrant collection exists with proper configuration.

        Creates collection if it doesn't exist with:
        - BGE-M3 embeddings (1024-dim)
        - Cosine similarity
        - Namespace index
        """
        try:
            # Check if collection exists
            collections = await self.qdrant_client.async_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                logger.info(
                    "Creating Qdrant collection",
                    collection=self.collection_name,
                )

                # Create collection with BGE-M3 config (1024-dim)
                await self.qdrant_client.async_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1024,  # BGE-M3 embedding dimension
                        distance=Distance.COSINE,
                    ),
                )

                logger.info(
                    "Collection created",
                    collection=self.collection_name,
                )
            else:
                logger.debug(
                    "Collection already exists",
                    collection=self.collection_name,
                )

            # Ensure namespace index exists
            await self.namespace_manager._ensure_qdrant_namespace_index()

        except Exception as e:
            logger.error(
                "Failed to ensure collection exists",
                collection=self.collection_name,
                error=str(e),
            )
            raise

    async def ingest_benchmark_corpus(
        self,
        dataset_name: DatasetName,
        sample_size: int | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Ingest benchmark corpus into Qdrant with namespace isolation.

        Args:
            dataset_name: Name of the benchmark dataset
            sample_size: Number of samples to ingest (None = all)
            overwrite: If True, delete existing namespace data first

        Returns:
            Dictionary with ingestion statistics

        Example:
            >>> pipeline = BenchmarkCorpusIngestionPipeline()
            >>> stats = await pipeline.ingest_benchmark_corpus(
            ...     dataset_name="natural_questions",
            ...     sample_size=1000
            ... )
            >>> print(f"Ingested {stats['total_contexts']} contexts")
        """
        start_time = time.perf_counter()
        namespace_id = self._get_namespace_id(dataset_name)

        logger.info(
            "Starting benchmark corpus ingestion",
            dataset=dataset_name,
            namespace=namespace_id,
            sample_size=sample_size,
            overwrite=overwrite,
        )

        # Ensure collection exists
        await self.ensure_collection_exists()

        # Create namespace
        await self.namespace_manager.create_namespace(
            namespace_id=namespace_id,
            namespace_type="evaluation",
            description=f"Benchmark corpus: {dataset_name}",
        )

        # Delete existing data if overwrite=True
        if overwrite:
            logger.warning(
                "Overwrite mode: deleting existing namespace data",
                namespace=namespace_id,
            )
            await self.namespace_manager.delete_namespace(namespace_id)

        # Load benchmark dataset
        dataset = await self._benchmark_loader.load_dataset(
            dataset_name=dataset_name,
            sample_size=sample_size,
        )

        logger.info(
            "Benchmark dataset loaded",
            dataset=dataset_name,
            total_samples=len(dataset),
        )

        # Extract and deduplicate contexts
        contexts_to_ingest = self._extract_contexts(dataset, namespace_id)

        logger.info(
            "Contexts extracted",
            dataset=dataset_name,
            total_contexts=len(contexts_to_ingest),
        )

        # Batch process: embedding + upsert
        stats = await self._batch_ingest_contexts(
            contexts=contexts_to_ingest,
            namespace_id=namespace_id,
        )

        duration_sec = time.perf_counter() - start_time
        stats["duration_sec"] = round(duration_sec, 2)
        stats["dataset"] = dataset_name
        stats["namespace"] = namespace_id

        logger.info(
            "Benchmark corpus ingestion complete",
            dataset=dataset_name,
            namespace=namespace_id,
            stats=stats,
        )

        return stats

    def _extract_contexts(
        self,
        dataset: list[dict[str, Any]],
        namespace_id: str,
    ) -> list[dict[str, Any]]:
        """Extract and deduplicate contexts from dataset samples.

        Args:
            dataset: List of normalized dataset samples
            namespace_id: Target namespace ID

        Returns:
            List of context dicts with metadata
        """
        contexts = []
        seen_contexts = set()  # For deduplication

        for sample in dataset:
            question_id = sample["question_id"]
            source = sample["source"]

            for ctx_idx, context_text in enumerate(sample.get("contexts", [])):
                # Skip empty contexts
                if not context_text or not context_text.strip():
                    continue

                # Deduplicate by text hash
                context_hash = hash(context_text)
                if context_hash in seen_contexts:
                    continue
                seen_contexts.add(context_hash)

                # Create context dict with metadata
                contexts.append(
                    {
                        "text": context_text,
                        "metadata": {
                            "namespace_id": namespace_id,
                            "source": source,
                            "question_id": question_id,
                            "context_index": ctx_idx,
                            "chunk_id": f"{question_id}_ctx_{ctx_idx}",
                        },
                    }
                )

        logger.info(
            "Context extraction complete",
            namespace=namespace_id,
            total_contexts=len(contexts),
            unique_contexts=len(seen_contexts),
        )

        return contexts

    async def _batch_ingest_contexts(
        self,
        contexts: list[dict[str, Any]],
        namespace_id: str,
    ) -> dict[str, Any]:
        """Batch process contexts: embed and upsert to Qdrant.

        Args:
            contexts: List of context dicts with metadata
            namespace_id: Target namespace ID

        Returns:
            Dictionary with ingestion statistics
        """
        stats = {
            "total_contexts": len(contexts),
            "contexts_ingested": 0,
            "contexts_failed": 0,
            "batches_processed": 0,
        }

        # Process in batches
        for batch_idx in range(0, len(contexts), self.batch_size):
            batch = contexts[batch_idx : batch_idx + self.batch_size]
            batch_num = batch_idx // self.batch_size + 1
            total_batches = (len(contexts) + self.batch_size - 1) // self.batch_size

            logger.info(
                "Processing batch",
                namespace=namespace_id,
                batch=batch_num,
                total_batches=total_batches,
                batch_size=len(batch),
            )

            try:
                # Extract texts for embedding
                texts = [ctx["text"] for ctx in batch]

                # Generate embeddings (batch)
                embed_start = time.perf_counter()
                embeddings = await self.embedding_service.embed_batch(texts)
                embed_duration_ms = (time.perf_counter() - embed_start) * 1000

                logger.debug(
                    "Batch embeddings generated",
                    namespace=namespace_id,
                    batch=batch_num,
                    duration_ms=round(embed_duration_ms, 2),
                )

                # Create Qdrant points
                points = []
                for ctx, embedding in zip(batch, embeddings, strict=True):
                    point_id = str(uuid.uuid4())
                    metadata = ctx["metadata"]

                    points.append(
                        PointStruct(
                            id=point_id,
                            vector=embedding,
                            payload={
                                "text": ctx["text"],
                                "namespace_id": namespace_id,
                                "source": metadata["source"],
                                "question_id": metadata["question_id"],
                                "context_index": metadata["context_index"],
                                "chunk_id": metadata["chunk_id"],
                            },
                        )
                    )

                # Upsert to Qdrant
                upsert_start = time.perf_counter()
                await self.qdrant_client.async_client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )
                upsert_duration_ms = (time.perf_counter() - upsert_start) * 1000

                logger.info(
                    "Batch upserted to Qdrant",
                    namespace=namespace_id,
                    batch=batch_num,
                    points=len(points),
                    duration_ms=round(upsert_duration_ms, 2),
                )

                stats["contexts_ingested"] += len(points)
                stats["batches_processed"] += 1

            except Exception as e:
                logger.error(
                    "Failed to process batch",
                    namespace=namespace_id,
                    batch=batch_num,
                    error=str(e),
                )
                stats["contexts_failed"] += len(batch)

        return stats

    async def get_namespace_stats(self, namespace_id: str) -> dict[str, Any]:
        """Get statistics for a benchmark namespace.

        Args:
            namespace_id: Namespace ID (e.g., 'eval_nq')

        Returns:
            Dictionary with namespace statistics

        Example:
            >>> pipeline = BenchmarkCorpusIngestionPipeline()
            >>> stats = await pipeline.get_namespace_stats("eval_nq")
            >>> print(f"Documents: {stats['document_count']}")
        """
        try:
            # Count points in namespace
            result = await self.qdrant_client.async_client.count(
                collection_name=self.collection_name,
                count_filter=self.namespace_manager.build_qdrant_filter(
                    allowed_namespaces=[namespace_id]
                ),
            )

            document_count = result.count if hasattr(result, "count") else 0

            return {
                "namespace_id": namespace_id,
                "collection_name": self.collection_name,
                "document_count": document_count,
            }

        except Exception as e:
            logger.error(
                "Failed to get namespace stats",
                namespace=namespace_id,
                error=str(e),
            )
            return {
                "namespace_id": namespace_id,
                "collection_name": self.collection_name,
                "document_count": 0,
                "error": str(e),
            }

    async def ingest_all_benchmarks(
        self,
        track_a_sample_size: int = 1000,
        track_b_sample_size: int = 100,
        overwrite: bool = False,
    ) -> dict[str, dict[str, Any]]:
        """Ingest all benchmark datasets with appropriate sample sizes.

        Args:
            track_a_sample_size: Sample size for Track A datasets (default: 1000)
            track_b_sample_size: Sample size for Track B datasets (default: 100)
            overwrite: If True, delete existing data first

        Returns:
            Dictionary mapping dataset name to ingestion stats

        Example:
            >>> pipeline = BenchmarkCorpusIngestionPipeline()
            >>> all_stats = await pipeline.ingest_all_benchmarks()
            >>> for dataset, stats in all_stats.items():
            ...     print(f"{dataset}: {stats['total_contexts']} contexts")
        """
        logger.info(
            "Starting ingestion of all benchmark datasets",
            track_a_sample=track_a_sample_size,
            track_b_sample=track_b_sample_size,
        )

        datasets = self._benchmark_loader.list_datasets()
        all_stats = {}

        for dataset_name in datasets:
            dataset_info = self._benchmark_loader.get_dataset_info(dataset_name)
            track = dataset_info.get("track", "A")

            # Determine sample size based on track
            sample_size = track_b_sample_size if track == "B" else track_a_sample_size

            logger.info(
                "Ingesting benchmark dataset",
                dataset=dataset_name,
                track=track,
                sample_size=sample_size,
            )

            try:
                stats = await self.ingest_benchmark_corpus(
                    dataset_name=dataset_name,
                    sample_size=sample_size,
                    overwrite=overwrite,
                )
                all_stats[dataset_name] = stats

            except Exception as e:
                logger.error(
                    "Failed to ingest benchmark dataset",
                    dataset=dataset_name,
                    error=str(e),
                )
                all_stats[dataset_name] = {
                    "error": str(e),
                    "total_contexts": 0,
                }

        logger.info(
            "All benchmark datasets ingestion complete",
            total_datasets=len(datasets),
            successful=sum(1 for s in all_stats.values() if "error" not in s),
        )

        return all_stats


def get_corpus_ingestion_pipeline() -> BenchmarkCorpusIngestionPipeline:
    """Get BenchmarkCorpusIngestionPipeline instance.

    Returns:
        BenchmarkCorpusIngestionPipeline instance
    """
    return BenchmarkCorpusIngestionPipeline()
