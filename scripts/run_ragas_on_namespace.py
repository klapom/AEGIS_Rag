#!/usr/bin/env python3
"""Run RAGAS evaluation on namespace-isolated domain.

Sprint 75: E2E User Journey - Step 4: RAGAS Evaluation

This script runs AFTER the Playwright E2E tests have:
1. Created the domain (namespace_id: "ragas_eval_domain")
2. Configured domain training settings (Hybrid + Reranking)
3. Ingested AEGIS RAG documentation (493 .md files)

Usage:
    # Run with default settings (20 samples)
    python scripts/run_ragas_on_namespace.py --namespace ragas_eval_domain

    # Run with custom dataset and sample count
    python scripts/run_ragas_on_namespace.py \
        --namespace ragas_eval_domain \
        --dataset data/benchmarks/sprint_75_evaluation_dataset.jsonl \
        --samples 50

Expected Results (Sprint 75 Targets):
    Context Precision:  > 0.80 (was 0.0 with wrong docs)
    Context Recall:     > 0.75 (was 0.0 with wrong docs)
    Faithfulness:       > 0.90 (was 0.75)
    Answer Relevancy:   > 0.85 (was 0.71)
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

from src.components.vector_search.hybrid_search import HybridSearch
from src.evaluation.ragas_evaluator import RAGASEvaluator

logger = structlog.get_logger(__name__)


async def verify_namespace_ready(namespace_id: str) -> dict[str, Any]:
    """Verify namespace exists and has documents.

    Args:
        namespace_id: Namespace to verify

    Returns:
        Dictionary with namespace stats

    Raises:
        ValueError: If namespace is not ready for evaluation
    """
    logger.info("verifying_namespace", namespace_id=namespace_id)

    hybrid_search = HybridSearch()

    # Test query to check namespace has documents
    test_results = await hybrid_search.hybrid_search(
        query="AEGIS RAG architecture",
        top_k=5,
        namespaces=[namespace_id],  # CRITICAL: Namespace isolation!
    )

    if not test_results.get("results"):
        logger.error("namespace_empty", namespace_id=namespace_id)
        raise ValueError(
            f"Namespace '{namespace_id}' has no documents.\n"
            f"Run the Playwright E2E test first:\n"
            f"  cd frontend && npm run test:e2e -- ragas-domain-setup.spec.ts"
        )

    doc_count = len(test_results["results"])

    if doc_count < 5:
        logger.warning(
            "namespace_low_document_count",
            namespace_id=namespace_id,
            document_count=doc_count,
            expected=">400",
        )

    stats = {
        "namespace_id": namespace_id,
        "document_count": doc_count,
        "sample_documents": [
            {
                "id": r.get("id"),
                "source": r.get("source", r.get("metadata", {}).get("source", "unknown")),
                "score": r.get("score", 0.0),
            }
            for r in test_results["results"][:3]
        ],
    }

    logger.info("namespace_verified", **stats)

    return stats


async def run_ragas_evaluation(
    namespace_id: str,
    dataset_path: str,
    num_samples: int = 20,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Run RAGAS evaluation on specific namespace.

    Args:
        namespace_id: Namespace for domain isolation
        dataset_path: Path to RAGAS test dataset (.jsonl)
        num_samples: Number of samples to evaluate (default: 20)
        output_path: Optional path to save detailed results

    Returns:
        Dictionary with RAGAS scores
    """
    logger.info(
        "ragas_namespace_evaluation_started",
        namespace_id=namespace_id,
        dataset_path=dataset_path,
        num_samples=num_samples,
    )

    # Verify namespace is ready
    namespace_stats = await verify_namespace_ready(namespace_id)

    # Initialize RAGAS evaluator
    evaluator = RAGASEvaluator(
        llm_model="gpt-oss:20b",
        embedding_model="bge-m3",
    )

    # Set default output path if not provided
    if output_path is None:
        output_path = f"reports/ragas_{namespace_id}_{num_samples}samples.json"

    # Run RAGAS evaluation
    scores = await evaluator.evaluate_from_file(
        dataset_path=dataset_path,
        num_samples=num_samples,
        namespace_id=namespace_id,  # Pass namespace to evaluation
        top_k=10,
        output_path=output_path,
    )

    logger.info(
        "ragas_evaluation_complete",
        namespace_id=namespace_id,
        output_path=output_path,
        **scores,
    )

    return scores


def print_results(namespace_id: str, num_samples: int, scores: dict[str, Any]) -> None:
    """Pretty-print RAGAS results with status indicators.

    Args:
        namespace_id: Evaluated namespace
        num_samples: Number of samples evaluated
        scores: RAGAS scores dictionary
    """
    print("\n" + "=" * 80)
    print("RAGAS EVALUATION RESULTS - Sprint 75")
    print("=" * 80)
    print(f"Namespace:          {namespace_id}")
    print(f"Samples:            {num_samples}")
    print(f"Model:              gpt-oss:20b (Ollama)")
    print(f"Context Window:     32K tokens (Sprint 75 fix)")
    print("-" * 80)

    # Sprint 75 targets
    targets = {
        "context_precision": 0.80,
        "context_recall": 0.75,
        "faithfulness": 0.90,
        "answer_relevancy": 0.85,
    }

    metrics = [
        ("Context Precision", "context_precision"),
        ("Context Recall", "context_recall"),
        ("Faithfulness", "faithfulness"),
        ("Answer Relevancy", "answer_relevancy"),
    ]

    all_passed = True

    for name, key in metrics:
        score = scores.get(key, 0.0)
        target = targets[key]
        status = "✓" if score >= target else "✗"

        if score < target:
            all_passed = False

        print(f"{name:20s}  {score:.3f}  (target: >{target:.2f})  {status}")

    print("=" * 80)

    if all_passed:
        print("🎉 ALL TARGETS MET! RAGAS evaluation passed.")
    else:
        print("⚠️  Some targets not met. See failures above.")

    print("\nDetailed results saved to: reports/ragas_*.json")
    print("=" * 80 + "\n")


async def main():
    parser = argparse.ArgumentParser(
        description="Run RAGAS evaluation on namespace-isolated domain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (20 samples)
  python scripts/run_ragas_on_namespace.py --namespace ragas_eval_domain

  # Run with more samples for thorough evaluation
  python scripts/run_ragas_on_namespace.py --namespace ragas_eval_domain --samples 50

  # Use custom dataset
  python scripts/run_ragas_on_namespace.py \\
      --namespace ragas_eval_domain \\
      --dataset data/benchmarks/custom_dataset.jsonl
        """,
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default="ragas_eval_domain",
        help="Namespace ID for evaluation (default: ragas_eval_domain)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/benchmarks/sprint_75_evaluation_dataset.jsonl",
        help="Path to RAGAS test dataset (.jsonl)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=20,
        help="Number of samples to evaluate (default: 20)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output path for detailed results (default: reports/ragas_<namespace>_<samples>samples.json)",
    )

    args = parser.parse_args()

    # Verify dataset exists
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        logger.error("dataset_not_found", path=str(dataset_path))
        print(f"Error: Dataset not found: {dataset_path}")
        print("Create dataset first or specify existing dataset with --dataset")
        sys.exit(1)

    # Run evaluation
    try:
        scores = await run_ragas_evaluation(
            namespace_id=args.namespace,
            dataset_path=str(dataset_path),
            num_samples=args.samples,
            output_path=args.output,
        )

        # Print results
        print_results(args.namespace, args.samples, scores)

        # Exit with error code if targets not met
        targets_met = (
            scores.get("context_precision", 0.0) >= 0.80
            and scores.get("context_recall", 0.0) >= 0.75
            and scores.get("faithfulness", 0.0) >= 0.90
            and scores.get("answer_relevancy", 0.0) >= 0.85
        )

        sys.exit(0 if targets_met else 1)

    except ValueError as e:
        logger.error("evaluation_failed", error=str(e))
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("unexpected_error", error=str(e))
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
