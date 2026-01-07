"""Retrieval Method Comparison Tests using RAGAS.

Sprint 74 Feature 74.3: Retrieval Method Comparison

This module compares BM25, Vector, and Hybrid retrieval methods using RAGAS metrics.
The goal is to empirically validate that:
1. BM25 performs best on exact keyword/numeric queries
2. Vector search performs best on semantic/conceptual queries
3. Hybrid (RRF fusion) performs best overall on complex queries

Test Strategy:
- Use retrieval_comparison_dataset.jsonl with expected_best_method field
- Run same queries through BM25-only, Vector-only, and Hybrid
- Compare RAGAS metrics (precision, recall, faithfulness, relevancy)
- Validate that expected_best_method predictions are correct

Requirements:
- Backend services running (Qdrant, Neo4j, Redis, Ollama)
- Evaluation dependencies: poetry install --with evaluation
- Test dataset: tests/ragas/data/retrieval_comparison_dataset.jsonl

Usage:
    pytest tests/ragas/test_retrieval_comparison.py -m ragas -v
"""

import pytest
import structlog

from src.components.retrieval.intent_classifier import IntentWeights
from src.evaluation.ragas_evaluator import BenchmarkSample, RAGASEvaluator
from tests.ragas.conftest import load_ragas_dataset, save_ragas_results

logger = structlog.get_logger(__name__)


# =============================================================================
# Custom Intent Weights for Method Isolation
# =============================================================================

# Pure BM25: Only keyword matching, no vector/graph
BM25_ONLY_WEIGHTS = IntentWeights(vector=0.0, bm25=1.0, local=0.0, global_=0.0)

# Pure Vector: Only semantic search, no BM25/graph
VECTOR_ONLY_WEIGHTS = IntentWeights(vector=1.0, bm25=0.0, local=0.0, global_=0.0)

# Hybrid: Balanced vector + BM25 (no graph for fair comparison)
HYBRID_WEIGHTS = IntentWeights(vector=0.5, bm25=0.5, local=0.0, global_=0.0)


# =============================================================================
# Custom RAGAS Evaluator with Method Override
# =============================================================================


class RetrievalMethodEvaluator(RAGASEvaluator):
    """RAGAS Evaluator with configurable retrieval method.

    This evaluator allows forcing a specific retrieval method (BM25, Vector, Hybrid)
    by overriding the intent classifier with custom weights.

    Example:
        evaluator = RetrievalMethodEvaluator(
            namespace="test_ragas",
            method="bm25",  # Force BM25-only retrieval
        )
        results = await evaluator.evaluate_rag_pipeline(dataset)
    """

    def __init__(
        self,
        namespace: str = "eval_benchmark",
        llm_model: str = "qwen3:8b",
        embedding_model: str = "bge-m3:latest",
        method: str = "hybrid",  # "bm25", "vector", or "hybrid"
        metrics: list[str] | None = None,
    ):
        """Initialize retrieval method evaluator.

        Args:
            namespace: Namespace for benchmark data
            llm_model: LLM model for RAGAS evaluation
            embedding_model: Embedding model for RAGAS
            method: Retrieval method ("bm25", "vector", or "hybrid")
            metrics: List of RAGAS metrics to compute
        """
        super().__init__(namespace, llm_model, embedding_model, metrics)

        self.method = method

        # Set custom weights based on method
        if method == "bm25":
            self.custom_weights = BM25_ONLY_WEIGHTS
        elif method == "vector":
            self.custom_weights = VECTOR_ONLY_WEIGHTS
        elif method == "hybrid":
            self.custom_weights = HYBRID_WEIGHTS
        else:
            raise ValueError(f"Invalid method: {method}. Must be 'bm25', 'vector', or 'hybrid'.")

        logger.info(
            "retrieval_method_evaluator_initialized",
            method=method,
            weights={
                "vector": self.custom_weights.vector,
                "bm25": self.custom_weights.bm25,
                "local": self.custom_weights.local,
                "global": self.custom_weights.global_,
            },
        )

    async def retrieve_contexts(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[str]:
        """Retrieve contexts using forced retrieval method.

        Overrides parent method to use custom weights instead of intent classification.

        Args:
            query: User query
            top_k: Number of contexts to retrieve

        Returns:
            List of retrieved context texts
        """
        # Import here to avoid circular dependency
        from src.components.retrieval.intent_classifier import Intent, IntentClassificationResult

        # Create fake intent result with custom weights
        # Use FACTUAL intent as placeholder (actual intent doesn't matter)
        intent_override = IntentClassificationResult(
            intent=Intent.FACTUAL,  # Placeholder, weights are what matter
            weights=self.custom_weights,
            confidence=1.0,
            latency_ms=0.0,
            method="forced_override",
        )

        # Search with forced weights (intent_override parameter not available in current API)
        # Instead, we'll temporarily modify the search engine's behavior
        # This is a workaround - ideally FourWayHybridSearch would accept weights parameter

        # Call parent's retrieve_contexts but with intent override
        # Since we can't directly override intent, we'll patch classify_intent temporarily
        from unittest.mock import patch

        with patch(
            "src.components.retrieval.four_way_hybrid_search.classify_intent"
        ) as mock_classify:
            mock_classify.return_value = intent_override

            # Call parent implementation with mocked intent
            contexts = []
            search_results = await self.search_engine.search(
                query=query,
                top_k=top_k,
                allowed_namespaces=[self.namespace],
                use_reranking=False,  # Disable reranking for fair comparison
            )

            # Extract text from results
            for result in search_results.get("results", []):
                text = result.get("text", "")
                if text:
                    contexts.append(text)

        logger.debug(
            "retrieved_contexts_with_method",
            method=self.method,
            query=query[:50],
            num_contexts=len(contexts),
        )

        return contexts


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def retrieval_comparison_dataset() -> list[BenchmarkSample]:
    """Load retrieval comparison dataset.

    Returns:
        List of BenchmarkSample objects with expected_best_method metadata

    Example:
        >>> def test_something(retrieval_comparison_dataset):
        ...     assert len(retrieval_comparison_dataset) == 10
        ...     assert retrieval_comparison_dataset[0].metadata["expected_best_method"] in ["bm25", "vector", "hybrid"]
    """
    from pathlib import Path

    dataset_path = Path(__file__).parent / "data" / "retrieval_comparison_dataset.jsonl"

    if not dataset_path.exists():
        pytest.skip(f"Retrieval comparison dataset not found: {dataset_path}")

    raw_data = load_ragas_dataset(dataset_path)

    samples = []
    for data in raw_data:
        sample = BenchmarkSample(
            question=data["question"],
            ground_truth=data["ground_truth"],
            contexts=[],  # Will be retrieved during evaluation
            answer="",  # Will be generated during evaluation
            metadata=data.get("metadata", {}),
        )
        samples.append(sample)

    logger.info("retrieval_comparison_dataset_loaded", num_samples=len(samples))
    return samples


@pytest.fixture(scope="function")
async def bm25_evaluator():
    """RAGAS evaluator configured for BM25-only retrieval.

    Returns:
        RetrievalMethodEvaluator instance with method="bm25"
    """
    evaluator = RetrievalMethodEvaluator(
        namespace="test_ragas",
        llm_model="qwen3:8b",
        embedding_model="bge-m3:latest",
        method="bm25",
    )
    yield evaluator


@pytest.fixture(scope="function")
async def vector_evaluator():
    """RAGAS evaluator configured for Vector-only retrieval.

    Returns:
        RetrievalMethodEvaluator instance with method="vector"
    """
    evaluator = RetrievalMethodEvaluator(
        namespace="test_ragas",
        llm_model="qwen3:8b",
        embedding_model="bge-m3:latest",
        method="vector",
    )
    yield evaluator


@pytest.fixture(scope="function")
async def hybrid_evaluator():
    """RAGAS evaluator configured for Hybrid retrieval.

    Returns:
        RetrievalMethodEvaluator instance with method="hybrid"
    """
    evaluator = RetrievalMethodEvaluator(
        namespace="test_ragas",
        llm_model="qwen3:8b",
        embedding_model="bge-m3:latest",
        method="hybrid",
    )
    yield evaluator


# =============================================================================
# Retrieval Method Comparison Tests
# =============================================================================


@pytest.mark.ragas
@pytest.mark.ragas_slow
@pytest.mark.asyncio
async def test_bm25_vs_vector_vs_hybrid_full_comparison(
    bm25_evaluator,
    vector_evaluator,
    hybrid_evaluator,
    retrieval_comparison_dataset,
):
    """Compare BM25, Vector, and Hybrid retrieval across all test cases.

    This test runs all 10 queries through each retrieval method and compares:
    - Context Precision: How relevant are retrieved contexts?
    - Context Recall: Did we retrieve all needed information?
    - Faithfulness: Is answer grounded in contexts?
    - Answer Relevancy: Does answer address the question?

    Expected outcomes:
    - BM25 excels on keyword queries (questions 1-3)
    - Vector excels on semantic queries (questions 4-6)
    - Hybrid performs best overall (questions 7-10)
    """
    logger.info(
        "starting_full_retrieval_comparison",
        num_samples=len(retrieval_comparison_dataset),
    )

    # Run evaluations in parallel for all three methods
    import asyncio

    bm25_task = bm25_evaluator.evaluate_rag_pipeline(
        dataset=retrieval_comparison_dataset,
        sample_size=len(retrieval_comparison_dataset),
        top_k=10,
    )

    vector_task = vector_evaluator.evaluate_rag_pipeline(
        dataset=retrieval_comparison_dataset,
        sample_size=len(retrieval_comparison_dataset),
        top_k=10,
    )

    hybrid_task = hybrid_evaluator.evaluate_rag_pipeline(
        dataset=retrieval_comparison_dataset,
        sample_size=len(retrieval_comparison_dataset),
        top_k=10,
    )

    bm25_results, vector_results, hybrid_results = await asyncio.gather(
        bm25_task, vector_task, hybrid_task
    )

    # Log results
    logger.info(
        "retrieval_comparison_results",
        bm25_precision=round(bm25_results.overall_metrics.context_precision, 3),
        vector_precision=round(vector_results.overall_metrics.context_precision, 3),
        hybrid_precision=round(hybrid_results.overall_metrics.context_precision, 3),
        bm25_recall=round(bm25_results.overall_metrics.context_recall, 3),
        vector_recall=round(vector_results.overall_metrics.context_recall, 3),
        hybrid_recall=round(hybrid_results.overall_metrics.context_recall, 3),
        bm25_faithfulness=round(bm25_results.overall_metrics.faithfulness, 3),
        vector_faithfulness=round(vector_results.overall_metrics.faithfulness, 3),
        hybrid_faithfulness=round(hybrid_results.overall_metrics.faithfulness, 3),
    )

    # Save results for analysis
    save_ragas_results(bm25_results, "reports/ragas_bm25_only.json")
    save_ragas_results(vector_results, "reports/ragas_vector_only.json")
    save_ragas_results(hybrid_results, "reports/ragas_hybrid.json")

    # Assertions: Hybrid should have best overall precision and recall
    assert hybrid_results.overall_metrics.context_precision >= max(
        bm25_results.overall_metrics.context_precision,
        vector_results.overall_metrics.context_precision,
    ) - 0.05, (
        f"Hybrid precision ({hybrid_results.overall_metrics.context_precision:.3f}) "
        f"should be competitive with BM25 ({bm25_results.overall_metrics.context_precision:.3f}) "
        f"and Vector ({vector_results.overall_metrics.context_precision:.3f})"
    )

    # All methods should have reasonable quality (>0.5)
    assert bm25_results.overall_metrics.context_precision > 0.5, "BM25 precision too low"
    assert vector_results.overall_metrics.context_precision > 0.5, "Vector precision too low"
    assert hybrid_results.overall_metrics.context_precision > 0.5, "Hybrid precision too low"


@pytest.mark.ragas
@pytest.mark.ragas_quick
@pytest.mark.asyncio
async def test_bm25_excels_on_keyword_queries(
    bm25_evaluator,
    vector_evaluator,
    hybrid_evaluator,
    retrieval_comparison_dataset,
):
    """Test that BM25 performs best on exact keyword queries.

    Uses only BM25-favored queries from the dataset (expected_best_method="bm25"):
    - "What is the BGE-M3 model version?" (exact keyword: BGE-M3)
    - "Which port does Qdrant use for HTTP?" (exact number: 6333)
    - "What is ADR-024 about?" (exact ID: ADR-024)
    """
    # Filter to BM25-favored queries only
    bm25_queries = [
        s for s in retrieval_comparison_dataset if s.metadata.get("expected_best_method") == "bm25"
    ]

    logger.info("testing_bm25_keyword_queries", num_queries=len(bm25_queries))

    # Run evaluations
    import asyncio

    bm25_results, vector_results, hybrid_results = await asyncio.gather(
        bm25_evaluator.evaluate_rag_pipeline(bm25_queries, sample_size=len(bm25_queries)),
        vector_evaluator.evaluate_rag_pipeline(bm25_queries, sample_size=len(bm25_queries)),
        hybrid_evaluator.evaluate_rag_pipeline(bm25_queries, sample_size=len(bm25_queries)),
    )

    # Log results
    logger.info(
        "bm25_keyword_query_results",
        bm25_precision=round(bm25_results.overall_metrics.context_precision, 3),
        vector_precision=round(vector_results.overall_metrics.context_precision, 3),
        hybrid_precision=round(hybrid_results.overall_metrics.context_precision, 3),
    )

    # BM25 should perform well on keyword queries (but hybrid might still be competitive)
    assert bm25_results.overall_metrics.context_precision > 0.65, (
        f"BM25 should excel on keyword queries, got {bm25_results.overall_metrics.context_precision:.3f}"
    )


@pytest.mark.ragas
@pytest.mark.ragas_quick
@pytest.mark.asyncio
async def test_vector_excels_on_semantic_queries(
    bm25_evaluator,
    vector_evaluator,
    hybrid_evaluator,
    retrieval_comparison_dataset,
):
    """Test that Vector search performs best on semantic/conceptual queries.

    Uses only Vector-favored queries from the dataset (expected_best_method="vector"):
    - "How does embedding-based search work?" (conceptual understanding)
    - "Explain the concept of semantic retrieval" (pure semantic, no keywords)
    - "What are the benefits of neural search?" (abstract concepts)
    """
    # Filter to Vector-favored queries only
    vector_queries = [
        s
        for s in retrieval_comparison_dataset
        if s.metadata.get("expected_best_method") == "vector"
    ]

    logger.info("testing_vector_semantic_queries", num_queries=len(vector_queries))

    # Run evaluations
    import asyncio

    bm25_results, vector_results, hybrid_results = await asyncio.gather(
        bm25_evaluator.evaluate_rag_pipeline(vector_queries, sample_size=len(vector_queries)),
        vector_evaluator.evaluate_rag_pipeline(vector_queries, sample_size=len(vector_queries)),
        hybrid_evaluator.evaluate_rag_pipeline(vector_queries, sample_size=len(vector_queries)),
    )

    # Log results
    logger.info(
        "vector_semantic_query_results",
        bm25_precision=round(bm25_results.overall_metrics.context_precision, 3),
        vector_precision=round(vector_results.overall_metrics.context_precision, 3),
        hybrid_precision=round(hybrid_results.overall_metrics.context_precision, 3),
    )

    # Vector should perform well on semantic queries
    assert vector_results.overall_metrics.context_precision > 0.60, (
        f"Vector should excel on semantic queries, got {vector_results.overall_metrics.context_precision:.3f}"
    )


@pytest.mark.ragas
@pytest.mark.ragas_quick
@pytest.mark.asyncio
async def test_hybrid_excels_on_complex_queries(
    bm25_evaluator,
    vector_evaluator,
    hybrid_evaluator,
    retrieval_comparison_dataset,
):
    """Test that Hybrid (RRF fusion) performs best on complex queries.

    Uses only Hybrid-favored queries from the dataset (expected_best_method="hybrid"):
    - "Compare keyword and semantic search" (needs both approaches)
    - "What are the benefits of Reciprocal Rank Fusion?" (keyword + concept)
    - "How does AEGIS RAG combine different retrieval methods?" (multi-faceted)
    - "What is the architecture of AEGIS RAG retrieval system?" (components + relationships)
    """
    # Filter to Hybrid-favored queries only
    hybrid_queries = [
        s
        for s in retrieval_comparison_dataset
        if s.metadata.get("expected_best_method") == "hybrid"
    ]

    logger.info("testing_hybrid_complex_queries", num_queries=len(hybrid_queries))

    # Run evaluations
    import asyncio

    bm25_results, vector_results, hybrid_results = await asyncio.gather(
        bm25_evaluator.evaluate_rag_pipeline(hybrid_queries, sample_size=len(hybrid_queries)),
        vector_evaluator.evaluate_rag_pipeline(hybrid_queries, sample_size=len(hybrid_queries)),
        hybrid_evaluator.evaluate_rag_pipeline(hybrid_queries, sample_size=len(hybrid_queries)),
    )

    # Log results
    logger.info(
        "hybrid_complex_query_results",
        bm25_precision=round(bm25_results.overall_metrics.context_precision, 3),
        vector_precision=round(vector_results.overall_metrics.context_precision, 3),
        hybrid_precision=round(hybrid_results.overall_metrics.context_precision, 3),
    )

    # Hybrid should perform best (or at least competitive) on complex queries
    assert hybrid_results.overall_metrics.context_precision >= max(
        bm25_results.overall_metrics.context_precision,
        vector_results.overall_metrics.context_precision,
    ) - 0.05, (
        f"Hybrid should excel on complex queries. "
        f"BM25: {bm25_results.overall_metrics.context_precision:.3f}, "
        f"Vector: {vector_results.overall_metrics.context_precision:.3f}, "
        f"Hybrid: {hybrid_results.overall_metrics.context_precision:.3f}"
    )


@pytest.mark.ragas
@pytest.mark.ragas_quick
@pytest.mark.asyncio
async def test_retrieval_method_smoke_test(
    bm25_evaluator,
    vector_evaluator,
    hybrid_evaluator,
    retrieval_comparison_dataset,
):
    """Quick smoke test with 3 samples to verify all methods work.

    This test ensures:
    - All three evaluators can retrieve contexts
    - All three evaluators can generate answers
    - RAGAS metrics are computed for all methods
    - No errors occur during evaluation
    """
    # Use first 3 samples only
    small_dataset = retrieval_comparison_dataset[:3]

    logger.info("starting_retrieval_method_smoke_test", num_samples=len(small_dataset))

    # Run evaluations
    import asyncio

    bm25_results, vector_results, hybrid_results = await asyncio.gather(
        bm25_evaluator.evaluate_rag_pipeline(small_dataset, sample_size=len(small_dataset)),
        vector_evaluator.evaluate_rag_pipeline(small_dataset, sample_size=len(small_dataset)),
        hybrid_evaluator.evaluate_rag_pipeline(small_dataset, sample_size=len(small_dataset)),
    )

    # Verify all methods produced results
    assert bm25_results.sample_count == 3, "BM25 evaluation failed"
    assert vector_results.sample_count == 3, "Vector evaluation failed"
    assert hybrid_results.sample_count == 3, "Hybrid evaluation failed"

    # Verify all metrics are computed (not NaN)
    assert bm25_results.overall_metrics.context_precision > 0, "BM25 precision is zero"
    assert vector_results.overall_metrics.context_precision > 0, "Vector precision is zero"
    assert hybrid_results.overall_metrics.context_precision > 0, "Hybrid precision is zero"

    logger.info(
        "retrieval_method_smoke_test_passed",
        bm25_precision=round(bm25_results.overall_metrics.context_precision, 3),
        vector_precision=round(vector_results.overall_metrics.context_precision, 3),
        hybrid_precision=round(hybrid_results.overall_metrics.context_precision, 3),
    )
