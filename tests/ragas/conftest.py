"""Pytest configuration and fixtures for RAGAS evaluation tests.

Sprint 74 Feature 74.2: RAGAS Backend Integration

This module provides fixtures for:
- Loading RAGAS test datasets
- Initializing RAGASEvaluator with test namespace
- Setting up test environment (requires backend services running)
"""

import json
from pathlib import Path
from typing import Any

import pytest
import structlog

from src.evaluation.ragas_evaluator import RAGASEvaluator, BenchmarkSample

logger = structlog.get_logger(__name__)


# =============================================================================
# Test Configuration
# =============================================================================

RAGAS_TEST_NAMESPACE = "default"  # Sprint 75: Using default namespace (has ADR-024 + CDays PDFs)
RAGAS_DATASET_PATH = Path(__file__).parent / "data" / "aegis_ragas_dataset.jsonl"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def aegis_ragas_dataset() -> list[dict[str, Any]]:
    """Load AEGIS RAG test dataset (20 questions).

    Returns:
        List of test samples with question, ground_truth, and metadata

    Example:
        >>> def test_something(aegis_ragas_dataset):
        ...     assert len(aegis_ragas_dataset) == 20
        ...     assert aegis_ragas_dataset[0]["question"] == "What is AEGIS RAG?"
    """
    if not RAGAS_DATASET_PATH.exists():
        pytest.skip(f"RAGAS dataset not found: {RAGAS_DATASET_PATH}")

    dataset = []
    with open(RAGAS_DATASET_PATH, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            try:
                data = json.loads(line)
                dataset.append(data)
            except json.JSONDecodeError as e:
                logger.warning("failed_to_parse_ragas_sample", line_num=line_num, error=str(e))

    logger.info("aegis_ragas_dataset_loaded", num_samples=len(dataset))
    return dataset


@pytest.fixture(scope="session")
def aegis_ragas_benchmark_samples(aegis_ragas_dataset) -> list[BenchmarkSample]:
    """Convert AEGIS dataset to BenchmarkSample format for RAGASEvaluator.

    Returns:
        List of BenchmarkSample objects

    Example:
        >>> def test_ragas(aegis_ragas_benchmark_samples):
        ...     sample = aegis_ragas_benchmark_samples[0]
        ...     assert sample.question == "What is AEGIS RAG?"
        ...     assert sample.ground_truth != ""
    """
    samples = []
    for data in aegis_ragas_dataset:
        sample = BenchmarkSample(
            question=data["question"],
            ground_truth=data["ground_truth"],
            contexts=[],  # Will be retrieved during evaluation
            answer="",  # Will be generated during evaluation
            metadata=data.get("metadata", {}),
        )
        samples.append(sample)

    return samples


@pytest.fixture(scope="session")
async def ragas_evaluator():
    """Initialize RAGASEvaluator for tests.

    IMPORTANT: This fixture requires backend services running:
    - Qdrant (localhost:6333)
    - Neo4j (bolt://localhost:7687)
    - Redis (localhost:6379)
    - Ollama (localhost:11434)

    Returns:
        RAGASEvaluator instance configured for testing

    Example:
        >>> @pytest.mark.asyncio
        >>> async def test_ragas(ragas_evaluator):
        ...     results = await ragas_evaluator.evaluate_rag_pipeline(...)
    """
    evaluator = RAGASEvaluator(
        namespace=RAGAS_TEST_NAMESPACE,
        llm_model="qwen2.5:7b",  # Sprint 75: qwen2.5 for RAGAS (JSON-compatible)
        embedding_model="bge-m3:latest",  # Uses native BGE-M3 service
    )

    logger.info("ragas_evaluator_initialized", namespace=RAGAS_TEST_NAMESPACE)

    yield evaluator

    # Cleanup: Could optionally delete test namespace data
    # For now, we keep it for debugging


@pytest.fixture(scope="function")
def ragas_small_dataset(aegis_ragas_benchmark_samples) -> list[BenchmarkSample]:
    """Small dataset (5 samples) for quick tests.

    Returns:
        First 5 samples from AEGIS dataset

    Example:
        >>> def test_quick_ragas(ragas_small_dataset):
        ...     assert len(ragas_small_dataset) == 5
    """
    return aegis_ragas_benchmark_samples[:5]


@pytest.fixture(scope="function")
def ragas_factual_dataset(aegis_ragas_benchmark_samples) -> list[BenchmarkSample]:
    """Dataset containing only factual questions (8 samples).

    Returns:
        Samples with metadata.intent == "factual"

    Example:
        >>> def test_factual_questions(ragas_factual_dataset):
        ...     for sample in ragas_factual_dataset:
        ...         assert sample.metadata["intent"] == "factual"
    """
    return [s for s in aegis_ragas_benchmark_samples if s.metadata.get("intent") == "factual"]


@pytest.fixture(scope="function")
def ragas_exploratory_dataset(aegis_ragas_benchmark_samples) -> list[BenchmarkSample]:
    """Dataset containing only exploratory questions (6 samples).

    Returns:
        Samples with metadata.intent == "exploratory"
    """
    return [
        s for s in aegis_ragas_benchmark_samples if s.metadata.get("intent") == "exploratory"
    ]


@pytest.fixture(scope="function")
def ragas_summary_dataset(aegis_ragas_benchmark_samples) -> list[BenchmarkSample]:
    """Dataset containing only summary questions (4 samples).

    Returns:
        Samples with metadata.intent == "summary"
    """
    return [s for s in aegis_ragas_benchmark_samples if s.metadata.get("intent") == "summary"]


@pytest.fixture(scope="function")
def ragas_multihop_dataset(aegis_ragas_benchmark_samples) -> list[BenchmarkSample]:
    """Dataset containing only multi-hop questions (2 samples).

    Returns:
        Samples with metadata.intent == "multi_hop"
    """
    return [s for s in aegis_ragas_benchmark_samples if s.metadata.get("intent") == "multi_hop"]


# =============================================================================
# Pytest Marks
# =============================================================================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "ragas: mark test as RAGAS evaluation test (requires backend services)",
    )
    config.addinivalue_line(
        "markers",
        "ragas_slow: mark test as slow RAGAS evaluation (>5 minutes)",
    )
    config.addinivalue_line(
        "markers",
        "ragas_quick: mark test as quick RAGAS evaluation (<1 minute)",
    )


# =============================================================================
# Helper Functions
# =============================================================================


def load_ragas_dataset(dataset_path: str | Path) -> list[dict[str, Any]]:
    """Load RAGAS dataset from JSONL file.

    Args:
        dataset_path: Path to JSONL file

    Returns:
        List of test samples

    Example:
        >>> dataset = load_ragas_dataset("data/test.jsonl")
        >>> print(len(dataset))
        10
    """
    dataset_path = Path(dataset_path)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    dataset = []
    with open(dataset_path, encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                dataset.append(data)
            except json.JSONDecodeError:
                continue

    return dataset


def save_ragas_results(results: Any, output_path: str | Path) -> None:
    """Save RAGAS evaluation results to JSON file.

    Args:
        results: EvaluationResults object
        output_path: Output file path

    Example:
        >>> save_ragas_results(results, "reports/ragas_results.json")
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import json
    from datetime import datetime

    report_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "namespace": results.namespace,
        "sample_count": results.sample_count,
        "duration_seconds": results.duration_seconds,
        "overall_metrics": {
            "context_precision": results.overall_metrics.context_precision,
            "context_recall": results.overall_metrics.context_recall,
            "faithfulness": results.overall_metrics.faithfulness,
            "answer_relevancy": results.overall_metrics.answer_relevancy,
        },
        "per_intent_metrics": [
            {
                "intent": im.intent,
                "sample_count": im.sample_count,
                "context_precision": im.metrics.context_precision,
                "context_recall": im.metrics.context_recall,
                "faithfulness": im.metrics.faithfulness,
                "answer_relevancy": im.metrics.answer_relevancy,
            }
            for im in results.per_intent_metrics
        ],
        "metadata": results.metadata,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    logger.info("ragas_results_saved", path=str(output_path))
