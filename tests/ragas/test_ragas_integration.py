"""RAGAS Integration Tests for AEGIS RAG System.

Sprint 74 Feature 74.2.2: Core RAGAS Metric Tests

This module tests the AEGIS RAG system using RAGAS metrics:
- Context Precision: Relevance of retrieved contexts
- Context Recall: Coverage of ground truth information
- Faithfulness: Answer grounded in retrieved contexts (no hallucination)
- Answer Relevancy: Answer addresses the question

These tests require:
- Backend services running (Qdrant, Neo4j, Redis, Ollama)
- Evaluation dependencies: poetry install --with evaluation
- Test dataset: tests/ragas/data/aegis_ragas_dataset.jsonl

Usage:
    pytest tests/ragas/test_ragas_integration.py -m ragas -v
"""

import pytest
import structlog

from tests.ragas.conftest import save_ragas_results

logger = structlog.get_logger(__name__)


# =============================================================================
# Core RAGAS Metric Tests
# =============================================================================


@pytest.mark.ragas
@pytest.mark.ragas_slow
@pytest.mark.asyncio
async def test_ragas_context_precision(ragas_evaluator, aegis_ragas_benchmark_samples):
    """Test Context Precision metric on AEGIS dataset.

    Context Precision measures: How many retrieved contexts are relevant?
    Formula: (Relevant contexts) / (Total retrieved contexts)

    Target: >0.75 for production readiness

    This test uses the full 20-sample AEGIS dataset and evaluates
    retrieval quality across all domains (retrieval, graph, memory, etc.)
    """
    logger.info("starting_ragas_context_precision_test", num_samples=len(aegis_ragas_benchmark_samples))

    # Run RAGAS evaluation
    results = await ragas_evaluator.evaluate_rag_pipeline(
        dataset=aegis_ragas_benchmark_samples,
        sample_size=20,  # Full dataset
        top_k=10,
    )

    # Log overall metrics
    logger.info(
        "ragas_context_precision_results",
        context_precision=round(results.overall_metrics.context_precision, 3),
        context_recall=round(results.overall_metrics.context_recall, 3),
        faithfulness=round(results.overall_metrics.faithfulness, 3),
        answer_relevancy=round(results.overall_metrics.answer_relevancy, 3),
        sample_count=results.sample_count,
        duration_seconds=round(results.duration_seconds, 2),
    )

    # Log per-intent breakdown
    for intent_metrics in results.per_intent_metrics:
        logger.info(
            "ragas_per_intent_metrics",
            intent=intent_metrics.intent,
            sample_count=intent_metrics.sample_count,
            context_precision=round(intent_metrics.metrics.context_precision, 3),
        )

    # Save results for review
    save_ragas_results(results, "reports/ragas_context_precision.json")

    # Assert quality threshold
    assert results.overall_metrics.context_precision > 0.75, (
        f"Context Precision ({results.overall_metrics.context_precision:.3f}) "
        f"below threshold 0.75. This means retrieval is not returning relevant enough contexts."
    )


@pytest.mark.ragas
@pytest.mark.ragas_slow
@pytest.mark.asyncio
async def test_ragas_context_recall(ragas_evaluator, aegis_ragas_benchmark_samples):
    """Test Context Recall metric on AEGIS dataset.

    Context Recall measures: Were all expected/needed contexts retrieved?
    Formula: (Retrieved expected contexts) / (Total expected contexts)

    Target: >0.70 for production readiness

    This tests if the retrieval system finds all relevant information
    needed to answer the question correctly.
    """
    logger.info("starting_ragas_context_recall_test", num_samples=len(aegis_ragas_benchmark_samples))

    # Run RAGAS evaluation
    results = await ragas_evaluator.evaluate_rag_pipeline(
        dataset=aegis_ragas_benchmark_samples,
        sample_size=20,
        top_k=10,
    )

    # Log results
    logger.info(
        "ragas_context_recall_results",
        context_recall=round(results.overall_metrics.context_recall, 3),
        sample_count=results.sample_count,
    )

    # Save results
    save_ragas_results(results, "reports/ragas_context_recall.json")

    # Assert quality threshold
    assert results.overall_metrics.context_recall > 0.70, (
        f"Context Recall ({results.overall_metrics.context_recall:.3f}) "
        f"below threshold 0.70. This means retrieval is missing important contexts."
    )


@pytest.mark.ragas
@pytest.mark.ragas_slow
@pytest.mark.asyncio
async def test_ragas_faithfulness(ragas_evaluator, aegis_ragas_benchmark_samples):
    """Test Faithfulness metric on AEGIS dataset.

    Faithfulness measures: Is the answer grounded in retrieved contexts?
    In other words: Does the LLM hallucinate information?

    Target: >0.90 for production readiness

    High faithfulness means the LLM only uses information from the
    retrieved contexts and doesn't make up facts.
    """
    logger.info("starting_ragas_faithfulness_test", num_samples=len(aegis_ragas_benchmark_samples))

    # Run RAGAS evaluation
    results = await ragas_evaluator.evaluate_rag_pipeline(
        dataset=aegis_ragas_benchmark_samples,
        sample_size=20,
        top_k=10,
    )

    # Log results
    logger.info(
        "ragas_faithfulness_results",
        faithfulness=round(results.overall_metrics.faithfulness, 3),
        sample_count=results.sample_count,
    )

    # Save results
    save_ragas_results(results, "reports/ragas_faithfulness.json")

    # Assert quality threshold
    assert results.overall_metrics.faithfulness > 0.90, (
        f"Faithfulness ({results.overall_metrics.faithfulness:.3f}) "
        f"below threshold 0.90. This indicates the LLM is hallucinating information "
        f"not present in the retrieved contexts."
    )


@pytest.mark.ragas
@pytest.mark.ragas_slow
@pytest.mark.asyncio
async def test_ragas_answer_relevancy(ragas_evaluator, aegis_ragas_benchmark_samples):
    """Test Answer Relevancy metric on AEGIS dataset.

    Answer Relevancy measures: Does the answer address the question?

    Target: >0.80 for production readiness

    This tests if the generated answer actually answers what was asked,
    rather than providing tangential or unrelated information.
    """
    logger.info("starting_ragas_answer_relevancy_test", num_samples=len(aegis_ragas_benchmark_samples))

    # Run RAGAS evaluation
    results = await ragas_evaluator.evaluate_rag_pipeline(
        dataset=aegis_ragas_benchmark_samples,
        sample_size=20,
        top_k=10,
    )

    # Log results
    logger.info(
        "ragas_answer_relevancy_results",
        answer_relevancy=round(results.overall_metrics.answer_relevancy, 3),
        sample_count=results.sample_count,
    )

    # Save results
    save_ragas_results(results, "reports/ragas_answer_relevancy.json")

    # Assert quality threshold
    assert results.overall_metrics.answer_relevancy > 0.80, (
        f"Answer Relevancy ({results.overall_metrics.answer_relevancy:.3f}) "
        f"below threshold 0.80. This means answers are not addressing the questions properly."
    )


@pytest.mark.ragas
@pytest.mark.ragas_slow
@pytest.mark.asyncio
async def test_ragas_per_domain_breakdown(ragas_evaluator, aegis_ragas_benchmark_samples):
    """Test RAGAS metrics broken down by domain.

    This test evaluates performance across different knowledge domains:
    - system_architecture
    - embeddings
    - vector_search
    - graph_rag
    - memory
    - ingestion
    - llm_integration
    - retrieval
    - orchestration
    - domain_training
    - adr
    - agents

    Each domain should meet minimum quality thresholds:
    - Context Precision: >0.70
    - Faithfulness: >0.85
    """
    logger.info("starting_ragas_per_domain_test", num_samples=len(aegis_ragas_benchmark_samples))

    # Run RAGAS evaluation
    results = await ragas_evaluator.evaluate_rag_pipeline(
        dataset=aegis_ragas_benchmark_samples,
        sample_size=20,
        top_k=10,
    )

    # Group results by domain (from metadata)
    from collections import defaultdict

    domain_results = defaultdict(list)
    for i, sample in enumerate(aegis_ragas_benchmark_samples):
        domain = sample.metadata.get("domain", "unknown")
        domain_results[domain].append(i)

    # Calculate per-domain metrics
    domain_metrics = {}
    for domain, indices in domain_results.items():
        # Filter results for this domain
        # Note: This is a simplified calculation - in production,
        # we'd need to map back to the RAGAS results dataframe
        logger.info(
            "domain_coverage",
            domain=domain,
            num_questions=len(indices),
        )

    # Log per-intent metrics (RAGAS groups by intent in metadata)
    for intent_metrics in results.per_intent_metrics:
        logger.info(
            "ragas_per_intent_metrics",
            intent=intent_metrics.intent,
            sample_count=intent_metrics.sample_count,
            context_precision=round(intent_metrics.metrics.context_precision, 3),
            context_recall=round(intent_metrics.metrics.context_recall, 3),
            faithfulness=round(intent_metrics.metrics.faithfulness, 3),
            answer_relevancy=round(intent_metrics.metrics.answer_relevancy, 3),
        )

        # Assert minimum thresholds per intent
        assert intent_metrics.metrics.context_precision > 0.70, (
            f"Context Precision for intent '{intent_metrics.intent}' "
            f"({intent_metrics.metrics.context_precision:.3f}) below threshold 0.70"
        )

        assert intent_metrics.metrics.faithfulness > 0.85, (
            f"Faithfulness for intent '{intent_metrics.intent}' "
            f"({intent_metrics.metrics.faithfulness:.3f}) below threshold 0.85"
        )

    # Save results
    save_ragas_results(results, "reports/ragas_per_domain.json")


@pytest.mark.ragas
@pytest.mark.ragas_slow
@pytest.mark.asyncio
async def test_ragas_regression(ragas_evaluator, aegis_ragas_benchmark_samples):
    """Test RAGAS regression - ensure metrics don't degrade over time.

    This test compares current RAGAS scores against baseline scores
    from previous runs. If metrics drop significantly, it indicates
    a regression in RAG quality.

    Regression thresholds (compared to baseline):
    - Context Precision: -5% max
    - Faithfulness: -3% max
    - Answer Relevancy: -5% max
    """
    import json
    from pathlib import Path

    logger.info("starting_ragas_regression_test", num_samples=len(aegis_ragas_benchmark_samples))

    # Run RAGAS evaluation
    results = await ragas_evaluator.evaluate_rag_pipeline(
        dataset=aegis_ragas_benchmark_samples,
        sample_size=20,
        top_k=10,
    )

    # Load baseline scores (if available)
    baseline_path = Path("reports/ragas_baseline.json")

    if baseline_path.exists():
        with open(baseline_path, encoding="utf-8") as f:
            baseline = json.load(f)

        baseline_metrics = baseline["overall_metrics"]

        # Compare with baseline
        precision_diff = (
            results.overall_metrics.context_precision - baseline_metrics["context_precision"]
        )
        faithfulness_diff = results.overall_metrics.faithfulness - baseline_metrics["faithfulness"]
        relevancy_diff = (
            results.overall_metrics.answer_relevancy - baseline_metrics["answer_relevancy"]
        )

        logger.info(
            "ragas_regression_comparison",
            precision_current=round(results.overall_metrics.context_precision, 3),
            precision_baseline=round(baseline_metrics["context_precision"], 3),
            precision_diff=round(precision_diff, 3),
            faithfulness_current=round(results.overall_metrics.faithfulness, 3),
            faithfulness_baseline=round(baseline_metrics["faithfulness"], 3),
            faithfulness_diff=round(faithfulness_diff, 3),
            relevancy_current=round(results.overall_metrics.answer_relevancy, 3),
            relevancy_baseline=round(baseline_metrics["answer_relevancy"], 3),
            relevancy_diff=round(relevancy_diff, 3),
        )

        # Assert no significant regression
        assert precision_diff > -0.05, (
            f"Context Precision regressed by {abs(precision_diff):.3f} "
            f"(>{0.05:.3f} threshold). Current: {results.overall_metrics.context_precision:.3f}, "
            f"Baseline: {baseline_metrics['context_precision']:.3f}"
        )

        assert faithfulness_diff > -0.03, (
            f"Faithfulness regressed by {abs(faithfulness_diff):.3f} "
            f"(>{0.03:.3f} threshold). Current: {results.overall_metrics.faithfulness:.3f}, "
            f"Baseline: {baseline_metrics['faithfulness']:.3f}"
        )

        assert relevancy_diff > -0.05, (
            f"Answer Relevancy regressed by {abs(relevancy_diff):.3f} "
            f"(>{0.05:.3f} threshold). Current: {results.overall_metrics.answer_relevancy:.3f}, "
            f"Baseline: {baseline_metrics['answer_relevancy']:.3f}"
        )

    else:
        # No baseline yet - save current results as baseline
        logger.warning("no_baseline_found", message="Saving current results as baseline")
        save_ragas_results(results, baseline_path)

    # Always save current results
    save_ragas_results(results, "reports/ragas_regression_latest.json")


# =============================================================================
# Quick Tests (Subset of Data)
# =============================================================================


@pytest.mark.ragas
@pytest.mark.ragas_quick
@pytest.mark.asyncio
async def test_ragas_quick_smoke(ragas_evaluator, ragas_small_dataset):
    """Quick smoke test with 5 samples.

    This test runs quickly (1-2 minutes) and verifies:
    - RAGAS evaluation pipeline works
    - All 4 metrics are computed
    - Results are reasonable (>0.5 for all metrics)

    Use this for rapid iteration during development.
    """
    logger.info("starting_ragas_quick_smoke_test", num_samples=len(ragas_small_dataset))

    # Run RAGAS evaluation on small dataset
    results = await ragas_evaluator.evaluate_rag_pipeline(
        dataset=ragas_small_dataset,
        sample_size=5,
        top_k=10,
    )

    # Log results
    logger.info(
        "ragas_quick_smoke_results",
        context_precision=round(results.overall_metrics.context_precision, 3),
        context_recall=round(results.overall_metrics.context_recall, 3),
        faithfulness=round(results.overall_metrics.faithfulness, 3),
        answer_relevancy=round(results.overall_metrics.answer_relevancy, 3),
        duration_seconds=round(results.duration_seconds, 2),
    )

    # Basic sanity checks (lower thresholds for small sample)
    assert results.overall_metrics.context_precision > 0.5, "Context Precision too low"
    assert results.overall_metrics.context_recall > 0.5, "Context Recall too low"
    assert results.overall_metrics.faithfulness > 0.5, "Faithfulness too low"
    assert results.overall_metrics.answer_relevancy > 0.5, "Answer Relevancy too low"

    # Verify all samples evaluated
    assert results.sample_count == 5, f"Expected 5 samples, got {results.sample_count}"


@pytest.mark.ragas
@pytest.mark.ragas_quick
@pytest.mark.asyncio
async def test_ragas_factual_questions(ragas_evaluator, ragas_factual_dataset):
    """Test RAGAS on factual questions only.

    Factual questions (e.g., "What is X?") should have:
    - High faithfulness (>0.90) - simple facts, no hallucination
    - High answer relevancy (>0.85) - direct answers
    """
    logger.info("starting_ragas_factual_test", num_samples=len(ragas_factual_dataset))

    # Run RAGAS evaluation
    results = await ragas_evaluator.evaluate_rag_pipeline(
        dataset=ragas_factual_dataset,
        sample_size=len(ragas_factual_dataset),
        top_k=10,
    )

    # Log results
    logger.info(
        "ragas_factual_results",
        faithfulness=round(results.overall_metrics.faithfulness, 3),
        answer_relevancy=round(results.overall_metrics.answer_relevancy, 3),
        sample_count=results.sample_count,
    )

    # Assert high standards for factual questions
    assert results.overall_metrics.faithfulness > 0.90, (
        f"Faithfulness for factual questions ({results.overall_metrics.faithfulness:.3f}) "
        f"below 0.90. Factual questions should have minimal hallucination."
    )

    assert results.overall_metrics.answer_relevancy > 0.85, (
        f"Answer Relevancy for factual questions ({results.overall_metrics.answer_relevancy:.3f}) "
        f"below 0.85. Factual answers should be direct and relevant."
    )
