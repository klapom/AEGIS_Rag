"""Example usage of ReportGenerator for RAGAS evaluation results.

This script demonstrates how to:
1. Generate evaluation reports in multiple formats
2. Compare against baselines
3. Detect regressions
4. Save results as new baselines

Run this after running a RAGAS evaluation benchmark.
"""

import asyncio
from pathlib import Path

from src.evaluation.ragas_eval import EvaluationResult, RAGASEvaluator
from src.evaluation.report_generator import ReportGenerator


async def main():
    """Example usage of ReportGenerator."""

    # Example 1: Generate reports with mock data
    print("=" * 80)
    print("Example 1: Generate Reports from Mock Data")
    print("=" * 80)

    # Mock evaluation results (in practice, these come from RAGASEvaluator)
    mock_results = {
        "vector-only": EvaluationResult(
            scenario="vector-only",
            context_precision=0.89,
            context_recall=0.85,
            faithfulness=0.88,
            num_samples=1000,
            duration_seconds=45.2,
            metadata={"llm_model": "llama3.2:8b"},
        ),
        "graph-only": EvaluationResult(
            scenario="graph-only",
            context_precision=0.92,
            context_recall=0.88,
            faithfulness=0.90,
            num_samples=1000,
            duration_seconds=52.1,
            metadata={"llm_model": "llama3.2:8b"},
        ),
        "hybrid-reranked": EvaluationResult(
            scenario="hybrid-reranked",
            context_precision=0.93,
            context_recall=0.91,
            faithfulness=0.92,
            num_samples=1000,
            duration_seconds=67.5,
            metadata={"llm_model": "llama3.2:8b"},
        ),
    }

    # Initialize report generator (no baseline for first run)
    generator = ReportGenerator()

    # Generate all reports
    output_paths = generator.generate_all_reports(
        results=mock_results,
        benchmark="hotpotqa",
        output_dir="data/evaluation/reports",
        save_as_baseline=True,  # Save as baseline for future comparisons
    )

    print("\nGenerated reports:")
    for format_type, path in output_paths.items():
        print(f"  {format_type}: {path}")

    print("\n" + "=" * 80)
    print("Example 2: Generate Reports with Baseline Comparison")
    print("=" * 80)

    # Mock results with slight regression in one metric
    mock_results_with_regression = {
        "vector-only": EvaluationResult(
            scenario="vector-only",
            context_precision=0.89,
            context_recall=0.79,  # Dropped from 0.85 (>5% regression)
            faithfulness=0.88,
            num_samples=1000,
            duration_seconds=43.8,
            metadata={"llm_model": "llama3.2:8b"},
        ),
        "graph-only": EvaluationResult(
            scenario="graph-only",
            context_precision=0.92,
            context_recall=0.88,
            faithfulness=0.90,
            num_samples=1000,
            duration_seconds=51.3,
            metadata={"llm_model": "llama3.2:8b"},
        ),
        "hybrid-reranked": EvaluationResult(
            scenario="hybrid-reranked",
            context_precision=0.93,
            context_recall=0.91,
            faithfulness=0.92,
            num_samples=1000,
            duration_seconds=68.2,
            metadata={"llm_model": "llama3.2:8b"},
        ),
    }

    # Initialize with baseline from previous run
    baseline_path = Path("data/evaluation/baselines/hotpotqa_latest.json")

    if baseline_path.exists():
        generator_with_baseline = ReportGenerator(
            baseline_path=baseline_path,
            regression_threshold=0.05,  # 5% threshold
        )

        # Generate reports with baseline comparison
        output_paths = generator_with_baseline.generate_all_reports(
            results=mock_results_with_regression,
            benchmark="hotpotqa",
            output_dir="data/evaluation/reports",
            save_as_baseline=False,  # Don't overwrite baseline with regression
        )

        print("\nGenerated reports with baseline comparison:")
        for format_type, path in output_paths.items():
            print(f"  {format_type}: {path}")

        # Check for regressions
        alerts = generator_with_baseline.detect_regressions(mock_results_with_regression)
        if alerts:
            print("\nRegression Alerts:")
            for alert in alerts:
                print(
                    f"  ⚠️ {alert.scenario} - {alert.metric}: "
                    f"{alert.current:.3f} (was {alert.baseline:.3f}, "
                    f"delta: {alert.delta:.3f}, {alert.percentage_change:.1f}%)"
                )
    else:
        print(f"\nBaseline not found at {baseline_path}")
        print("Run Example 1 first to create a baseline.")

    print("\n" + "=" * 80)
    print("Example 3: Real Evaluation with RAGASEvaluator")
    print("=" * 80)

    # Check if dataset exists
    dataset_path = Path("data/evaluation/ragas_dataset.jsonl")

    if not dataset_path.exists():
        print(f"\nDataset not found at {dataset_path}")
        print("Skipping real evaluation example.")
        return

    # Initialize evaluator
    evaluator = RAGASEvaluator()

    # Load dataset
    print(f"\nLoading dataset from {dataset_path}...")
    dataset = evaluator.load_dataset(dataset_path)
    print(f"Loaded {len(dataset)} examples")

    # Run evaluation (use small subset for demo)
    print("\nRunning evaluation on first 10 samples...")
    small_dataset = dataset[:10]

    # Evaluate different scenarios
    scenarios = ["vector-only", "hybrid-reranked"]
    results = {}

    for scenario in scenarios:
        print(f"  Evaluating {scenario}...")
        result = await evaluator.evaluate_retrieval(
            dataset=small_dataset,
            scenario=scenario,
        )
        results[scenario] = result
        print(
            f"    Precision: {result.context_precision:.3f}, "
            f"Recall: {result.context_recall:.3f}, "
            f"Faithfulness: {result.faithfulness:.3f}"
        )

    # Generate reports
    print("\nGenerating reports...")
    generator = ReportGenerator()
    output_paths = generator.generate_all_reports(
        results=results,
        benchmark="ragas_demo",
        output_dir="data/evaluation/reports",
    )

    print("\nGenerated reports:")
    for format_type, path in output_paths.items():
        print(f"  {format_type}: {path}")


if __name__ == "__main__":
    asyncio.run(main())
