#!/usr/bin/env python3
"""CLI script to build training datasets from production traces.

Sprint 69 Feature 69.6: Dataset Builder implementation with 4 dataset types.

Supports 4 dataset types:
- intent: Query → Intent classification
- rerank: Query + Docs → Relevance scoring
- qa: Question → Context + Answer
- graph: Query → Cypher + Entities + Graph results

Usage:
    # Build all datasets
    python scripts/build_datasets.py --all --min-quality 0.8

    # Build specific datasets
    python scripts/build_datasets.py --intent --qa --min-quality 0.8
    python scripts/build_datasets.py --rerank --sampling hard_negatives
    python scripts/build_datasets.py --graph --min-quality 0.85

    # Export to Parquet
    python scripts/build_datasets.py --all --format parquet --version v2
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import structlog

from src.adaptation.dataset_builder import (
    DatasetBuilder,
    GraphExample,
    QAExample,
    RerankExample,
    TrainingExample,
)
from src.core.logging import setup_logging

logger = structlog.get_logger(__name__)


async def build_intent_dataset(
    trace_path: str,
    output_path: str,
    min_quality: float,
    deduplicate: bool,
) -> None:
    """Build intent classification dataset."""
    logger.info(
        "building_intent_dataset",
        trace_path=trace_path,
        output_path=output_path,
        min_quality=min_quality,
        deduplicate=deduplicate,
    )

    builder = DatasetBuilder(trace_path=trace_path)
    examples = await builder.build_intent_dataset(
        min_quality=min_quality,
        output_path=output_path,
        deduplicate=deduplicate,
    )

    logger.info(
        "intent_dataset_complete",
        total_examples=len(examples),
        output_path=output_path,
    )
    print(f"\nIntent dataset built: {len(examples)} examples")
    print(f"Output: {output_path}")


async def build_rerank_dataset(
    trace_path: str,
    output_path: str,
    sampling: str,
    min_score_diff: float,
) -> None:
    """Build reranking dataset."""
    logger.info(
        "building_rerank_dataset",
        trace_path=trace_path,
        output_path=output_path,
        sampling=sampling,
        min_score_diff=min_score_diff,
    )

    builder = DatasetBuilder(trace_path=trace_path)
    examples = await builder.build_rerank_dataset(
        sampling=sampling,
        min_score_diff=min_score_diff,
        output_path=output_path,
    )

    logger.info(
        "rerank_dataset_complete",
        total_examples=len(examples),
        output_path=output_path,
    )
    print(f"\nRerank dataset built: {len(examples)} pairs")
    print(f"Output: {output_path}")


async def build_qa_dataset(
    trace_path: str,
    output_path: str,
    min_quality: float,
    max_examples: int,
) -> None:
    """Build question-answering dataset."""
    logger.info(
        "building_qa_dataset",
        trace_path=trace_path,
        output_path=output_path,
        min_quality=min_quality,
        max_examples=max_examples,
    )

    builder = DatasetBuilder(trace_path=trace_path)
    examples = await builder.build_qa_dataset(
        min_quality=min_quality,
        output_path=output_path,
        max_examples=max_examples,
    )

    logger.info(
        "qa_dataset_complete",
        total_examples=len(examples),
        output_path=output_path,
    )
    print(f"\nQA dataset built: {len(examples)} examples")
    print(f"Output: {output_path}")


async def build_graph_dataset(
    trace_path: str,
    output_path: str,
    min_quality: float,
    max_examples: int,
) -> None:
    """Build graph RAG dataset."""
    logger.info(
        "building_graph_dataset",
        trace_path=trace_path,
        output_path=output_path,
        min_quality=min_quality,
        max_examples=max_examples,
    )

    builder = DatasetBuilder(trace_path=trace_path)
    examples = await builder.build_graph_dataset(
        min_quality=min_quality,
        output_path=output_path,
        max_examples=max_examples,
    )

    logger.info(
        "graph_dataset_complete",
        total_examples=len(examples),
        output_path=output_path,
    )
    print(f"\nGraph dataset built: {len(examples)} examples")
    print(f"Output: {output_path}")


async def main() -> None:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Build training datasets from production traces",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Input/output paths
    parser.add_argument(
        "--trace-path",
        type=str,
        default="data/traces",
        help="Path to traces JSONL file or directory",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/datasets/v1",
        help="Output directory for datasets",
    )

    # Dataset types
    parser.add_argument(
        "--intent",
        action="store_true",
        help="Build intent classification dataset",
    )
    parser.add_argument(
        "--rerank",
        action="store_true",
        help="Build reranking dataset",
    )
    parser.add_argument(
        "--qa",
        action="store_true",
        help="Build question-answering dataset",
    )
    parser.add_argument(
        "--graph",
        action="store_true",
        help="Build graph RAG dataset",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Build all dataset types",
    )

    # Intent dataset options
    parser.add_argument(
        "--min-quality",
        type=float,
        default=0.8,
        help="Minimum quality score (0.0-1.0) for intent dataset",
    )
    parser.add_argument(
        "--no-deduplicate",
        action="store_true",
        help="Disable query deduplication for intent dataset",
    )

    # Rerank dataset options
    parser.add_argument(
        "--sampling",
        type=str,
        choices=["hard_negatives", "in_batch"],
        default="hard_negatives",
        help="Sampling strategy for rerank dataset",
    )
    parser.add_argument(
        "--min-score-diff",
        type=float,
        default=0.3,
        help="Minimum score difference between pos/neg chunks",
    )

    # QA and Graph dataset options
    parser.add_argument(
        "--max-examples",
        type=int,
        default=10000,
        help="Maximum number of examples to include",
    )

    # Export options
    parser.add_argument(
        "--format",
        type=str,
        choices=["jsonl", "parquet"],
        default="jsonl",
        help="Export format (jsonl or parquet)",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v1",
        help="Dataset version for Parquet export",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(log_level=args.log_level, json_logs=False)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which datasets to build
    build_intent = args.intent or args.all
    build_rerank = args.rerank or args.all
    build_qa = args.qa or args.all
    build_graph = args.graph or args.all

    if not (build_intent or build_rerank or build_qa or build_graph):
        parser.error(
            "Must specify at least one dataset type: --intent, --rerank, --qa, --graph, or --all"
        )

    try:
        # Build intent dataset
        if build_intent:
            intent_output = output_dir / "intent_dataset.jsonl"
            await build_intent_dataset(
                trace_path=args.trace_path,
                output_path=str(intent_output),
                min_quality=args.min_quality,
                deduplicate=not args.no_deduplicate,
            )

        # Build rerank dataset
        if build_rerank:
            rerank_output = output_dir / "rerank_pairs.jsonl"
            await build_rerank_dataset(
                trace_path=args.trace_path,
                output_path=str(rerank_output),
                sampling=args.sampling,
                min_score_diff=args.min_score_diff,
            )

        # Build QA dataset
        if build_qa:
            qa_output = output_dir / "qa_dataset.jsonl"
            await build_qa_dataset(
                trace_path=args.trace_path,
                output_path=str(qa_output),
                min_quality=args.min_quality,
                max_examples=args.max_examples,
            )

        # Build graph dataset
        if build_graph:
            graph_output = output_dir / "graph_dataset.jsonl"
            await build_graph_dataset(
                trace_path=args.trace_path,
                output_path=str(graph_output),
                min_quality=args.min_quality,
                max_examples=args.max_examples,
            )

        # Export to Parquet if requested
        if args.format == "parquet":
            print("\nExporting datasets to Parquet format...")
            builder = DatasetBuilder(trace_path=args.trace_path)

            if build_intent and (output_dir / "intent_dataset.jsonl").exists():
                # Load JSONL and export to Parquet
                from src.adaptation.dataset_builder import TrainingExample
                import json

                examples = []
                with open(output_dir / "intent_dataset.jsonl") as f:
                    for line in f:
                        data = json.loads(line)
                        examples.append(
                            TrainingExample(
                                query=data["query"],
                                intent=data["intent"],
                                response="",  # Not in saved format
                                quality_score=data["quality_score"],
                                sources=[],
                                timestamp=datetime.fromisoformat(data["timestamp"]),
                                metadata=data.get("metadata"),
                            )
                        )
                await builder.export_to_parquet(
                    examples, "intent", str(output_dir.parent), args.version
                )

            # Similar for other dataset types if needed
            print(f"Parquet export complete (version: {args.version})")

        print("\nAll datasets built successfully!")
        print(f"Output directory: {output_dir}")
        print(f"Format: {args.format}")

    except Exception as e:
        logger.error("dataset_build_failed", error=str(e), exc_info=True)
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
