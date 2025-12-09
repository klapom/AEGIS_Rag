#!/usr/bin/env python3
"""Run RAGAS evaluation on AEGIS RAG system.

Sprint 41 Feature 41.7: RAGAS Evaluation Pipeline

This script runs RAGAS-based evaluation on the AEGIS RAG system with:
- Namespace-scoped evaluation (benchmark data isolation)
- All 4 RAGAS metrics (context precision, context recall, faithfulness, answer relevancy)
- Per-intent metric breakdown
- Batch evaluation with progress tracking
- JSON output format for results

Usage:
    # Evaluate on HotpotQA benchmark (50 samples)
    python scripts/run_evaluation.py \\
        --benchmark hotpotqa \\
        --namespace eval_hotpotqa \\
        --sample-size 50 \\
        --output-dir reports/evaluation

    # Full evaluation on all samples
    python scripts/run_evaluation.py \\
        --benchmark hotpotqa \\
        --namespace eval_hotpotqa \\
        --output-dir reports/evaluation

    # Custom dataset
    python scripts/run_evaluation.py \\
        --dataset data/custom_benchmark.jsonl \\
        --namespace eval_custom \\
        --sample-size 100 \\
        --batch-size 10 \\
        --output-dir reports/custom

Arguments:
    --benchmark: Pre-defined benchmark name (hotpotqa, musique, etc.)
    --dataset: Path to custom dataset JSONL file
    --namespace: Namespace containing benchmark documents (default: eval_benchmark)
    --sample-size: Number of samples to evaluate (default: all)
    --batch-size: Batch size for evaluation (default: 10)
    --top-k: Number of contexts to retrieve per query (default: 10)
    --output-dir: Output directory for results (default: reports/evaluation)
    --format: Output format (json, markdown, html) (default: json)

Dataset Format (JSONL):
    Each line is a JSON object with:
    {
        "question": "What is the capital of France?",
        "ground_truth": "Paris is the capital of France.",
        "contexts": ["Paris is the capital..."],  // Optional
        "answer": "Paris",  // Optional
        "metadata": {"intent": "factual", "difficulty": "easy"}  // Optional
    }
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import structlog

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.ragas_evaluator import RAGASEvaluator

logger = structlog.get_logger(__name__)


# =============================================================================
# Pre-defined Benchmark Datasets
# =============================================================================

BENCHMARK_DATASETS = {
    "hotpotqa": {
        "path": "data/benchmarks/hotpotqa.jsonl",
        "namespace": "eval_hotpotqa",
        "description": "HotpotQA multi-hop reasoning benchmark",
    },
    "musique": {
        "path": "data/benchmarks/musique.jsonl",
        "namespace": "eval_musique",
        "description": "MuSiQue multi-hop QA benchmark",
    },
    "squad": {
        "path": "data/benchmarks/squad.jsonl",
        "namespace": "eval_squad",
        "description": "SQuAD single-hop QA benchmark",
    },
}


# =============================================================================
# Main Evaluation Function
# =============================================================================


async def run_evaluation(
    dataset_path: str,
    namespace: str,
    sample_size: int | None,
    batch_size: int,
    top_k: int,
    output_dir: str,
    output_format: str,
) -> dict:
    """Run RAGAS evaluation on dataset.

    Args:
        dataset_path: Path to benchmark dataset JSONL file
        namespace: Namespace for benchmark documents
        sample_size: Number of samples to evaluate (None = all)
        batch_size: Batch size for evaluation
        top_k: Number of contexts to retrieve per query
        output_dir: Output directory for results
        output_format: Output format (json, markdown, html)

    Returns:
        Evaluation results dictionary
    """
    logger.info(
        "starting_evaluation",
        dataset_path=dataset_path,
        namespace=namespace,
        sample_size=sample_size,
        batch_size=batch_size,
    )

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize evaluator
    evaluator = RAGASEvaluator(namespace=namespace)

    # Load dataset
    try:
        dataset = evaluator.load_dataset(dataset_path)
        logger.info("dataset_loaded", num_samples=len(dataset))
    except FileNotFoundError:
        logger.error("dataset_not_found", path=dataset_path)
        raise
    except Exception as e:
        logger.error("failed_to_load_dataset", error=str(e))
        raise

    # Run evaluation
    try:
        results = await evaluator.evaluate_rag_pipeline(
            dataset=dataset,
            sample_size=sample_size,
            batch_size=batch_size,
            top_k=top_k,
        )
        logger.info(
            "evaluation_complete",
            sample_count=results.sample_count,
            duration_seconds=round(results.duration_seconds, 2),
        )
    except Exception as e:
        logger.error("evaluation_failed", error=str(e))
        raise

    # Generate report
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"ragas_eval_{timestamp}.{output_format}"

    report = evaluator.generate_report(
        results=results,
        output_path=output_file,
        format=output_format,
    )

    logger.info("report_saved", path=str(output_file))

    # Print summary to console
    print("\n" + "=" * 80)
    print("RAGAS EVALUATION RESULTS")
    print("=" * 80)
    print(f"\nDataset: {dataset_path}")
    print(f"Namespace: {namespace}")
    print(f"Samples Evaluated: {results.sample_count}")
    print(f"Duration: {results.duration_seconds:.2f}s")
    print(f"Output: {output_file}")
    print("\n" + "-" * 80)
    print("OVERALL METRICS")
    print("-" * 80)
    print(f"  Context Precision: {results.overall_metrics.context_precision:.3f}")
    print(f"  Context Recall:    {results.overall_metrics.context_recall:.3f}")
    print(f"  Faithfulness:      {results.overall_metrics.faithfulness:.3f}")
    print(f"  Answer Relevancy:  {results.overall_metrics.answer_relevancy:.3f}")

    if results.per_intent_metrics:
        print("\n" + "-" * 80)
        print("PER-INTENT BREAKDOWN")
        print("-" * 80)
        print(f"{'Intent':<15} {'Samples':<10} {'Precision':<12} {'Recall':<12} {'Faith':<12} {'Relevancy':<12}")
        print("-" * 80)

        for intent_metrics in results.per_intent_metrics:
            print(
                f"{intent_metrics.intent:<15} "
                f"{intent_metrics.sample_count:<10} "
                f"{intent_metrics.metrics.context_precision:<12.3f} "
                f"{intent_metrics.metrics.context_recall:<12.3f} "
                f"{intent_metrics.metrics.faithfulness:<12.3f} "
                f"{intent_metrics.metrics.answer_relevancy:<12.3f}"
            )

    print("=" * 80 + "\n")

    return {
        "dataset_path": dataset_path,
        "namespace": namespace,
        "sample_count": results.sample_count,
        "duration_seconds": results.duration_seconds,
        "overall_metrics": {
            "context_precision": results.overall_metrics.context_precision,
            "context_recall": results.overall_metrics.context_recall,
            "faithfulness": results.overall_metrics.faithfulness,
            "answer_relevancy": results.overall_metrics.answer_relevancy,
        },
        "output_file": str(output_file),
    }


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """Main entry point for evaluation script."""
    parser = argparse.ArgumentParser(
        description="Run RAGAS evaluation on AEGIS RAG system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Dataset selection (mutually exclusive)
    dataset_group = parser.add_mutually_exclusive_group(required=True)
    dataset_group.add_argument(
        "--benchmark",
        type=str,
        choices=list(BENCHMARK_DATASETS.keys()),
        help=f"Pre-defined benchmark dataset: {', '.join(BENCHMARK_DATASETS.keys())}",
    )
    dataset_group.add_argument(
        "--dataset",
        type=str,
        help="Path to custom dataset JSONL file",
    )

    # Namespace configuration
    parser.add_argument(
        "--namespace",
        type=str,
        default=None,
        help="Namespace for benchmark documents (auto-detected for pre-defined benchmarks)",
    )

    # Evaluation parameters
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Number of samples to evaluate (default: all)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for evaluation (default: 10)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of contexts to retrieve per query (default: 10)",
    )

    # Output configuration
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/evaluation",
        help="Output directory for results (default: reports/evaluation)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "markdown", "html"],
        default="json",
        help="Output format (default: json)",
    )

    args = parser.parse_args()

    # Resolve dataset path and namespace
    if args.benchmark:
        benchmark_info = BENCHMARK_DATASETS[args.benchmark]
        dataset_path = benchmark_info["path"]
        namespace = args.namespace or benchmark_info["namespace"]

        print(f"\n==> Using benchmark: {args.benchmark}")
        print(f"    Description: {benchmark_info['description']}")
        print(f"    Dataset: {dataset_path}")
        print(f"    Namespace: {namespace}\n")
    else:
        dataset_path = args.dataset
        namespace = args.namespace or "eval_benchmark"

        print(f"\n==> Using custom dataset: {dataset_path}")
        print(f"    Namespace: {namespace}\n")

    # Check if dataset exists
    if not Path(dataset_path).exists():
        print(f"\nERROR: Dataset not found: {dataset_path}")
        print("\nPlease ensure the benchmark data has been ingested.")
        print(f"Expected location: {dataset_path}")
        sys.exit(1)

    # Run evaluation
    try:
        results = asyncio.run(
            run_evaluation(
                dataset_path=dataset_path,
                namespace=namespace,
                sample_size=args.sample_size,
                batch_size=args.batch_size,
                top_k=args.top_k,
                output_dir=args.output_dir,
                output_format=args.format,
            )
        )

        logger.info("evaluation_complete", output_dir=args.output_dir)
        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("evaluation_interrupted")
        sys.exit(1)

    except Exception as e:
        logger.error("evaluation_error", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Configure logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
    )

    main()
