#!/usr/bin/env python3
"""Track A RAGAS Evaluation - Combined Ingestion + Evaluation Script.

This script performs end-to-end RAGAS evaluation for Track A benchmarks:
1. Loads datasets from HuggingFace (Natural Questions, HotpotQA, MS MARCO)
2. Ingests contexts into Qdrant with namespace isolation
3. Runs RAGAS evaluation (retrieval + generation)
4. Generates reports with metrics

Designed for DGX Spark (ARM64, CUDA 13.0, Ollama local).

Usage:
    python scripts/run_track_a_evaluation.py --sample-size 10

Arguments:
    --sample-size: Number of samples per dataset (default: 10)
    --datasets: Comma-separated list of datasets (default: all Track A)
    --skip-ingestion: Skip ingestion if data already exists
    --output-dir: Output directory for reports
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging first
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Track A Dataset Configuration
# =============================================================================

TRACK_A_DATASETS = {
    "natural_questions": {
        "namespace": "eval_nq",
        "description": "Google Natural Questions - Open-domain QA",
        "hf_path": "google-research-datasets/natural_questions",
    },
    "hotpotqa": {
        "namespace": "eval_hotpotqa",
        "description": "HotpotQA - Multi-hop reasoning",
        "hf_path": "hotpot_qa",
    },
    "msmarco": {
        "namespace": "eval_msmarco",
        "description": "MS MARCO - Passage ranking",
        "hf_path": "microsoft/ms_marco",
    },
}


# =============================================================================
# Service Health Check
# =============================================================================

async def check_services() -> dict[str, bool]:
    """Check if all required services are running.

    Returns:
        Dictionary with service status
    """
    import httpx

    services = {
        "qdrant": False,
        "ollama": False,
        "neo4j": False,
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        # Check Qdrant
        try:
            resp = await client.get("http://localhost:6333/collections")
            services["qdrant"] = resp.status_code == 200
        except Exception as e:
            logger.error("qdrant_check_failed", error=str(e))

        # Check Ollama
        try:
            resp = await client.get("http://localhost:11434/api/tags")
            services["ollama"] = resp.status_code == 200
        except Exception as e:
            logger.error("ollama_check_failed", error=str(e))

        # Check Neo4j
        try:
            resp = await client.get("http://localhost:7474")
            services["neo4j"] = resp.status_code == 200
        except Exception as e:
            logger.error("neo4j_check_failed", error=str(e))

    return services


# =============================================================================
# Dataset Loading & Ingestion
# =============================================================================

async def load_and_ingest_dataset(
    dataset_name: str,
    sample_size: int,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Load dataset from HuggingFace and ingest into Qdrant.

    Args:
        dataset_name: Name of dataset (natural_questions, hotpotqa, msmarco)
        sample_size: Number of samples to load
        overwrite: Whether to overwrite existing data

    Returns:
        Dictionary with ingestion statistics
    """
    from src.evaluation.corpus_ingestion import BenchmarkCorpusIngestionPipeline

    config = TRACK_A_DATASETS[dataset_name]
    namespace = config["namespace"]

    logger.info(
        "loading_dataset",
        dataset=dataset_name,
        namespace=namespace,
        sample_size=sample_size,
    )

    # Initialize pipeline
    pipeline = BenchmarkCorpusIngestionPipeline(batch_size=10)

    # Ingest benchmark corpus
    stats = await pipeline.ingest_benchmark_corpus(
        dataset_name=dataset_name,
        sample_size=sample_size,
        overwrite=overwrite,
    )

    logger.info(
        "ingestion_complete",
        dataset=dataset_name,
        namespace=namespace,
        contexts_ingested=stats.get("contexts_ingested", 0),
        duration_sec=stats.get("duration_sec", 0),
    )

    return stats


async def save_evaluation_dataset(
    dataset_name: str,
    sample_size: int,
    output_dir: Path,
) -> Path:
    """Save dataset samples as JSONL for evaluation.

    Args:
        dataset_name: Name of dataset
        sample_size: Number of samples
        output_dir: Output directory

    Returns:
        Path to saved JSONL file
    """
    from src.evaluation.benchmark_loader import BenchmarkDatasetLoader

    loader = BenchmarkDatasetLoader()

    logger.info(
        "loading_dataset_for_eval",
        dataset=dataset_name,
        sample_size=sample_size,
    )

    # Load dataset
    samples = await loader.load_dataset(
        dataset_name=dataset_name,
        sample_size=sample_size,
    )

    # Save as JSONL
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{dataset_name}_eval.jsonl"

    with open(output_file, "w", encoding="utf-8") as f:
        for sample in samples:
            # Convert to RAGAS format
            eval_sample = {
                "question": sample["question"],
                "ground_truth": sample["answer"],
                "contexts": sample.get("contexts", []),
                "metadata": {
                    "source": sample["source"],
                    "question_id": sample["question_id"],
                },
            }
            f.write(json.dumps(eval_sample, ensure_ascii=False) + "\n")

    logger.info(
        "eval_dataset_saved",
        dataset=dataset_name,
        path=str(output_file),
        num_samples=len(samples),
    )

    return output_file


# =============================================================================
# RAGAS Evaluation
# =============================================================================

async def run_ragas_evaluation(
    dataset_path: Path,
    namespace: str,
    sample_size: int | None = None,
) -> dict[str, Any]:
    """Run RAGAS evaluation on dataset.

    Args:
        dataset_path: Path to evaluation JSONL file
        namespace: Namespace containing ingested documents
        sample_size: Number of samples to evaluate

    Returns:
        Evaluation results dictionary
    """
    from src.evaluation.ragas_evaluator import RAGASEvaluator

    logger.info(
        "starting_ragas_evaluation",
        dataset_path=str(dataset_path),
        namespace=namespace,
    )

    # Initialize evaluator
    evaluator = RAGASEvaluator(
        namespace=namespace,
        llm_model="qwen3:8b",  # Available on DGX Spark
    )

    # Load dataset
    dataset = evaluator.load_dataset(str(dataset_path))

    logger.info(
        "evaluation_dataset_loaded",
        num_samples=len(dataset),
    )

    # Run evaluation
    results = await evaluator.evaluate_rag_pipeline(
        dataset=dataset,
        sample_size=sample_size,
        batch_size=5,
        top_k=5,
    )

    return {
        "namespace": namespace,
        "sample_count": results.sample_count,
        "duration_seconds": results.duration_seconds,
        "metrics": {
            "context_precision": results.overall_metrics.context_precision,
            "context_recall": results.overall_metrics.context_recall,
            "faithfulness": results.overall_metrics.faithfulness,
            "answer_relevancy": results.overall_metrics.answer_relevancy,
        },
        "per_intent": [
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
    }


# =============================================================================
# Main Pipeline
# =============================================================================

async def run_track_a_pipeline(
    sample_size: int = 10,
    ingest_size: int | None = None,
    eval_size: int | None = None,
    datasets: list[str] | None = None,
    skip_ingestion: bool = False,
    output_dir: str = "reports/track_a_evaluation",
) -> dict[str, Any]:
    """Run complete Track A evaluation pipeline.

    Args:
        sample_size: Number of samples per dataset (default for both ingest and eval)
        ingest_size: Number of samples to ingest (overrides sample_size)
        eval_size: Number of samples to evaluate (overrides sample_size)
        datasets: List of datasets to evaluate (default: all Track A)
        skip_ingestion: Skip ingestion step
        output_dir: Output directory for reports

    Returns:
        Complete evaluation results
    """
    # Determine actual sizes
    actual_ingest_size = ingest_size if ingest_size is not None else sample_size
    actual_eval_size = eval_size if eval_size is not None else sample_size

    start_time = time.perf_counter()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Default to all Track A datasets
    if datasets is None:
        datasets = list(TRACK_A_DATASETS.keys())

    print("\n" + "=" * 80)
    print("AEGIS RAG - Track A RAGAS Evaluation")
    print("=" * 80)
    print(f"Ingest Size: {actual_ingest_size} samples per dataset")
    print(f"Eval Size: {actual_eval_size} samples per dataset")
    print(f"Datasets: {', '.join(datasets)}")
    print(f"Output: {output_dir}")
    print("=" * 80 + "\n")

    # Step 1: Check services
    print("[1/4] Checking services...")
    services = await check_services()

    all_ok = all(services.values())
    for service, status in services.items():
        status_str = "✓" if status else "✗"
        print(f"  {status_str} {service}: {'OK' if status else 'FAILED'}")

    if not all_ok:
        print("\nERROR: Some services are not running. Please start them first.")
        return {"error": "Services not available", "services": services}

    print()

    # Step 2: Load and ingest datasets
    ingestion_stats = {}
    eval_datasets = {}

    if not skip_ingestion:
        print("[2/4] Loading and ingesting datasets...")
        for dataset_name in datasets:
            config = TRACK_A_DATASETS[dataset_name]
            print(f"\n  → {dataset_name} ({config['description']})")

            try:
                # Ingest contexts into Qdrant
                stats = await load_and_ingest_dataset(
                    dataset_name=dataset_name,
                    sample_size=actual_ingest_size,
                    overwrite=True,
                )
                ingestion_stats[dataset_name] = stats
                print(f"    ✓ Ingested {stats.get('contexts_ingested', 0)} contexts")

                # Save evaluation dataset (same size as ingest for Q&A pairs)
                eval_path = await save_evaluation_dataset(
                    dataset_name=dataset_name,
                    sample_size=actual_ingest_size,
                    output_dir=output_path / "datasets",
                )
                eval_datasets[dataset_name] = eval_path
                print(f"    ✓ Saved eval dataset: {eval_path.name}")

            except Exception as e:
                logger.error(
                    "dataset_processing_failed",
                    dataset=dataset_name,
                    error=str(e),
                )
                print(f"    ✗ FAILED: {e}")
                ingestion_stats[dataset_name] = {"error": str(e)}
    else:
        print("[2/4] Skipping ingestion (--skip-ingestion)")
        # Load existing eval datasets
        for dataset_name in datasets:
            eval_path = output_path / "datasets" / f"{dataset_name}_eval.jsonl"
            if eval_path.exists():
                eval_datasets[dataset_name] = eval_path
            else:
                print(f"  ✗ Missing eval dataset: {eval_path}")

    print()

    # Step 3: Run RAGAS evaluation
    print("[3/4] Running RAGAS evaluation...")
    evaluation_results = {}

    for dataset_name, eval_path in eval_datasets.items():
        config = TRACK_A_DATASETS[dataset_name]
        namespace = config["namespace"]

        print(f"\n  → Evaluating {dataset_name} (namespace: {namespace})")

        try:
            results = await run_ragas_evaluation(
                dataset_path=eval_path,
                namespace=namespace,
                sample_size=actual_eval_size,
            )
            evaluation_results[dataset_name] = results

            metrics = results["metrics"]
            print(f"    ✓ Evaluated {results['sample_count']} samples in {results['duration_seconds']:.1f}s")
            print(f"      Context Precision: {metrics['context_precision']:.3f}")
            print(f"      Context Recall:    {metrics['context_recall']:.3f}")
            print(f"      Faithfulness:      {metrics['faithfulness']:.3f}")
            print(f"      Answer Relevancy:  {metrics['answer_relevancy']:.3f}")

        except Exception as e:
            logger.error(
                "evaluation_failed",
                dataset=dataset_name,
                error=str(e),
                exc_info=True,
            )
            print(f"    ✗ FAILED: {e}")
            evaluation_results[dataset_name] = {"error": str(e)}

    print()

    # Step 4: Generate report
    print("[4/4] Generating report...")

    total_duration = time.perf_counter() - start_time
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    report = {
        "metadata": {
            "timestamp": timestamp,
            "total_duration_seconds": round(total_duration, 2),
            "ingest_size_per_dataset": actual_ingest_size,
            "eval_size_per_dataset": actual_eval_size,
            "datasets": datasets,
            "track": "A",
        },
        "services": services,
        "ingestion": ingestion_stats,
        "evaluation": evaluation_results,
        "summary": {},
    }

    # Calculate summary
    valid_results = [r for r in evaluation_results.values() if "error" not in r]
    if valid_results:
        avg_metrics = {
            "context_precision": sum(r["metrics"]["context_precision"] for r in valid_results) / len(valid_results),
            "context_recall": sum(r["metrics"]["context_recall"] for r in valid_results) / len(valid_results),
            "faithfulness": sum(r["metrics"]["faithfulness"] for r in valid_results) / len(valid_results),
            "answer_relevancy": sum(r["metrics"]["answer_relevancy"] for r in valid_results) / len(valid_results),
        }
        report["summary"] = {
            "datasets_evaluated": len(valid_results),
            "average_metrics": avg_metrics,
        }

    # Save JSON report
    report_path = output_path / f"track_a_report_{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Report saved: {report_path}")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Duration: {total_duration:.1f}s")
    print(f"Datasets Evaluated: {len(valid_results)}/{len(datasets)}")

    if report["summary"]:
        print("\nAverage Metrics (Track A):")
        for metric, value in report["summary"]["average_metrics"].items():
            print(f"  {metric.replace('_', ' ').title()}: {value:.3f}")

    print("=" * 80 + "\n")

    return report


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Track A RAGAS Evaluation on AEGIS RAG"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=10,
        help="Number of samples per dataset for BOTH ingestion and evaluation (default: 10)",
    )
    parser.add_argument(
        "--ingest-size",
        type=int,
        default=None,
        help="Number of samples to ingest (overrides --sample-size for ingestion)",
    )
    parser.add_argument(
        "--eval-size",
        type=int,
        default=None,
        help="Number of samples to evaluate (overrides --sample-size for evaluation)",
    )
    parser.add_argument(
        "--datasets",
        type=str,
        default=None,
        help="Comma-separated list of datasets (default: all Track A)",
    )
    parser.add_argument(
        "--skip-ingestion",
        action="store_true",
        help="Skip ingestion step (use existing data)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/track_a_evaluation",
        help="Output directory for reports",
    )

    args = parser.parse_args()

    # Parse datasets
    datasets = None
    if args.datasets:
        datasets = [d.strip() for d in args.datasets.split(",")]
        # Validate
        for d in datasets:
            if d not in TRACK_A_DATASETS:
                print(f"ERROR: Unknown dataset '{d}'")
                print(f"Available: {', '.join(TRACK_A_DATASETS.keys())}")
                sys.exit(1)

    # Run pipeline
    try:
        result = asyncio.run(
            run_track_a_pipeline(
                sample_size=args.sample_size,
                ingest_size=args.ingest_size,
                eval_size=args.eval_size,
                datasets=datasets,
                skip_ingestion=args.skip_ingestion,
                output_dir=args.output_dir,
            )
        )

        if "error" in result:
            sys.exit(1)

        sys.exit(0)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("pipeline_failed", error=str(e), exc_info=True)
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
