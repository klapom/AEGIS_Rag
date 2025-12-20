#!/usr/bin/env python3
"""RAGAS benchmark script for evaluating retrieval quality across scenarios.

This script runs RAGAS evaluation on multiple retrieval scenarios:
- vector-only: Pure semantic search
- bm25-only: Pure keyword search
- hybrid-base: Vector + BM25 with RRF
- hybrid-reranked: Hybrid + cross-encoder reranking
- hybrid-decomposed: Hybrid + query decomposition
- hybrid-full: All advanced features enabled

Usage:
    python scripts/run_ragas_benchmark.py [--dataset PATH] [--output DIR] [--scenarios LIST]

Example:
    python scripts/run_ragas_benchmark.py --dataset data/evaluation/ragas_dataset.jsonl --output reports
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import structlog

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.ragas_eval import RAGASEvaluator

logger = structlog.get_logger(__name__)


async def run_benchmark(
    dataset_path: str,
    output_dir: str,
    scenarios: list[str] | None = None,
    html_report: bool = True,
    json_report: bool = True,
) -> dict:
    """Run RAGAS benchmark across multiple scenarios.

    Args:
        dataset_path: Path to evaluation dataset (JSONL)
        output_dir: Output directory for reports
        scenarios: List of scenarios to evaluate (default: all)
        html_report: Generate HTML report
        json_report: Generate JSON report

    Returns:
        Dictionary with benchmark results
    """
    logger.info(
        "starting_ragas_benchmark",
        dataset_path=dataset_path,
        output_dir=output_dir,
        scenarios=scenarios,
    )

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize evaluator
    evaluator = RAGASEvaluator()

    # Load dataset
    try:
        dataset = evaluator.load_dataset(dataset_path)
        logger.info("dataset_loaded", num_examples=len(dataset))
    except Exception as e:
        logger.error("failed_to_load_dataset", error=str(e))
        raise

    # Define scenarios if not provided
    if scenarios is None:
        scenarios = [
            "vector-only",
            "bm25-only",
            "hybrid-base",
            "hybrid-reranked",
            "hybrid-decomposed",
            "hybrid-full",
        ]

    # Run benchmark
    try:
        results = await evaluator.run_benchmark(dataset=dataset, scenarios=scenarios)
        logger.info("benchmark_complete", num_scenarios=len(results))
    except Exception as e:
        logger.error("benchmark_failed", error=str(e))
        raise

    # Generate reports
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if html_report:
        html_path = output_path / f"ragas_evaluation_{timestamp}.html"
        html_content = evaluator.generate_report(results, output_path=html_path, format="html")
        logger.info("html_report_generated", path=str(html_path))

    if json_report:
        json_path = output_path / f"ragas_evaluation_{timestamp}.json"
        json_content = evaluator.generate_report(results, output_path=json_path, format="json")
        logger.info("json_report_generated", path=str(json_path))

    # Print summary to console
    print("\n" + "=" * 80)
    print("RAGAS BENCHMARK RESULTS")
    print("=" * 80)
    print(f"\nDataset: {dataset_path}")
    print(f"Samples: {len(dataset)}")
    print(f"Timestamp: {timestamp}")
    print("\nResults by Scenario:")
    print("-" * 80)
    print(f"{'Scenario':<20} {'Ctx Precision':<15} {'Ctx Recall':<15} {'Faithfulness':<15}")
    print("-" * 80)

    for scenario, result in sorted(results.items()):
        print(
            f"{scenario:<20} {result.context_precision:>14.3f} "
            f"{result.context_recall:>14.3f} {result.faithfulness:>14.3f}"
        )

    print("-" * 80)
    print("\nBest Scores:")
    print(f"  Context Precision: {max(r.context_precision for r in results.values()):.3f}")
    print(f"  Context Recall:    {max(r.context_recall for r in results.values()):.3f}")
    print(f"  Faithfulness:      {max(r.faithfulness for r in results.values()):.3f}")
    print("=" * 80 + "\n")

    return {
        "results": {scenario: result.model_dump() for scenario, result in results.items()},
        "summary": {
            "num_scenarios": len(results),
            "num_samples": len(dataset),
            "best_context_precision": max(r.context_precision for r in results.values()),
            "best_context_recall": max(r.context_recall for r in results.values()),
            "best_faithfulness": max(r.faithfulness for r in results.values()),
            "timestamp": timestamp,
        },
    }


def main():
    """Main entry point for benchmark script."""
    parser = argparse.ArgumentParser(
        description="Run RAGAS evaluation benchmark on RAG retrieval system"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/evaluation/ragas_dataset.jsonl",
        help="Path to evaluation dataset (JSONL format)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports",
        help="Output directory for reports",
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        nargs="+",
        default=None,
        help="List of scenarios to evaluate (default: all)",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Disable HTML report generation",
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Disable JSON report generation",
    )

    args = parser.parse_args()

    # Run benchmark
    try:
        results = asyncio.run(
            run_benchmark(
                dataset_path=args.dataset,
                output_dir=args.output,
                scenarios=args.scenarios,
                html_report=not args.no_html,
                json_report=not args.no_json,
            )
        )

        logger.info("benchmark_complete", output_dir=args.output)
        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("benchmark_interrupted")
        sys.exit(1)

    except Exception as e:
        logger.error("benchmark_error", error=str(e), exc_info=True)
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
