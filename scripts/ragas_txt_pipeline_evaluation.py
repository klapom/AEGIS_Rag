#!/usr/bin/env python3
"""Sprint 43 Feature 43.11: RAGAS TXT Pipeline Evaluation.

This script:
1. Saves RAGAS HotPotQA samples as TXT files
2. Runs them through the production ingestion pipeline
3. Collects metrics from Prometheus/logs
4. Generates an evaluation report

Usage:
    poetry run python scripts/ragas_txt_pipeline_evaluation.py --samples 10

Author: Claude Code
Date: 2025-12-11
"""

import argparse
import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import structlog

# Setup logging before other imports
os.environ["LOG_LEVEL"] = "INFO"
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

# Initialize logger
logger = structlog.get_logger(__name__)


def load_hotpotqa_samples(
    jsonl_path: str, num_samples: int = 10
) -> list[dict]:
    """Load HotPotQA samples from JSONL file.

    Args:
        jsonl_path: Path to hotpotqa_eval.jsonl
        num_samples: Number of samples to load

    Returns:
        List of sample dicts with question, ground_truth, contexts
    """
    samples = []
    with open(jsonl_path, "r") as f:
        for i, line in enumerate(f):
            if i >= num_samples:
                break
            sample = json.loads(line.strip())
            samples.append(sample)

    logger.info(
        "hotpotqa_samples_loaded",
        count=len(samples),
        path=jsonl_path,
    )
    return samples


def save_samples_as_txt(
    samples: list[dict],
    output_dir: str,
) -> list[dict]:
    """Save RAGAS samples as TXT files for pipeline ingestion.

    Each TXT file contains the concatenated contexts from the sample.
    A metadata JSON file is saved alongside for evaluation.

    Args:
        samples: List of HotPotQA samples
        output_dir: Directory to save TXT files

    Returns:
        List of file info dicts with path, question, ground_truth
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_infos = []
    for i, sample in enumerate(samples):
        # Create TXT content from contexts
        contexts = sample.get("contexts", [])
        text_content = "\n\n".join(contexts)

        # Generate filename
        question_id = sample.get("metadata", {}).get("question_id", f"sample_{i:04d}")
        txt_filename = f"{question_id}.txt"
        txt_path = output_path / txt_filename

        # Save TXT file
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text_content)

        # Save metadata JSON for evaluation
        meta_path = output_path / f"{question_id}_meta.json"
        metadata = {
            "question_id": question_id,
            "question": sample.get("question"),
            "ground_truth": sample.get("ground_truth"),
            "contexts_count": len(contexts),
            "text_length": len(text_content),
            "txt_path": str(txt_path),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        file_infos.append({
            "txt_path": str(txt_path),
            "question_id": question_id,
            "question": sample.get("question"),
            "ground_truth": sample.get("ground_truth"),
            "text_length": len(text_content),
        })

        logger.info(
            "sample_saved_as_txt",
            question_id=question_id,
            txt_path=str(txt_path),
            text_length=len(text_content),
        )

    logger.info(
        "all_samples_saved_as_txt",
        count=len(file_infos),
        output_dir=output_dir,
    )
    return file_infos


async def run_pipeline_on_txt_files(
    file_infos: list[dict],
) -> list[dict]:
    """Run production pipeline on TXT files.

    Uses the LangGraph ingestion pipeline with:
    - ChunkingService for chunking
    - ExtractionPipeline for entity/relation extraction
    - MultiCriteriaDeduplicator for deduplication

    Args:
        file_infos: List of file info dicts from save_samples_as_txt

    Returns:
        List of pipeline results per file
    """
    # Import pipeline components
    from src.core.chunking_service import ChunkingConfig, ChunkStrategyEnum, get_chunking_service
    from src.components.graph_rag.extraction_factory import create_extraction_pipeline_from_config
    from src.components.graph_rag.semantic_deduplicator import create_deduplicator_from_config
    from src.core.config import settings

    # Initialize services
    chunking_config = ChunkingConfig(
        strategy=ChunkStrategyEnum.FIXED,
        max_tokens=1500,  # ~6000 chars
        overlap_tokens=100,
    )
    chunking_service = get_chunking_service(chunking_config)
    extractor = create_extraction_pipeline_from_config()
    deduplicator = create_deduplicator_from_config(settings) if settings.enable_multi_criteria_dedup else None

    results = []

    for file_info in file_infos:
        txt_path = file_info["txt_path"]
        question_id = file_info["question_id"]

        logger.info(
            "processing_txt_file",
            question_id=question_id,
            txt_path=txt_path,
        )

        start_time = time.time()

        try:
            # Read TXT file
            with open(txt_path, "r", encoding="utf-8") as f:
                text_content = f.read()

            # Step 1: Chunking
            chunk_start = time.time()
            chunks = await chunking_service.chunk_document(
                text=text_content,
                document_id=question_id,
            )
            chunk_time = time.time() - chunk_start

            chunk_stats = {
                "input_chars": len(text_content),
                "chunks_created": len(chunks),
                "chunk_sizes_chars": [len(c.content) for c in chunks],
                "chunk_sizes_tokens": [c.token_count for c in chunks],
                "duration_seconds": round(chunk_time, 3),
            }

            logger.info(
                "chunking_complete",
                question_id=question_id,
                **chunk_stats,
            )

            # Step 2: Extraction (per chunk)
            extract_start = time.time()
            all_entities = []
            all_relations = []

            for chunk in chunks:
                try:
                    entities, relations = await extractor.extract(
                        text=chunk.content,
                        document_id=f"{question_id}#{chunk.chunk_index}",
                    )
                    all_entities.extend(entities)
                    all_relations.extend(relations)
                except Exception as e:
                    logger.warning(
                        "chunk_extraction_failed",
                        chunk_id=chunk.chunk_id,
                        error=str(e),
                    )

            extract_time = time.time() - extract_start

            # Count entity/relation types
            entity_type_counts = defaultdict(int)
            for entity in all_entities:
                ent_type = entity.get("type", entity.get("entity_type", "UNKNOWN"))
                entity_type_counts[ent_type] += 1

            relation_type_counts = defaultdict(int)
            for relation in all_relations:
                rel_type = relation.get("type", relation.get("relation_type", "RELATES_TO"))
                relation_type_counts[rel_type] += 1

            extract_stats = {
                "entities_raw": len(all_entities),
                "relations_raw": len(all_relations),
                "entity_types": dict(entity_type_counts),
                "relation_types": dict(relation_type_counts),
                "duration_seconds": round(extract_time, 3),
            }

            logger.info(
                "extraction_complete",
                question_id=question_id,
                **extract_stats,
            )

            # Step 3: Deduplication
            dedup_stats = {}
            if deduplicator and all_entities:
                dedup_start = time.time()
                deduplicated_entities = deduplicator.deduplicate(all_entities)
                dedup_time = time.time() - dedup_start

                dedup_stats = {
                    "entities_before": len(all_entities),
                    "entities_after": len(deduplicated_entities),
                    "reduction_percent": round(
                        (1 - len(deduplicated_entities) / len(all_entities)) * 100, 1
                    ) if all_entities else 0,
                    "duration_seconds": round(dedup_time, 3),
                }
                all_entities = deduplicated_entities

                logger.info(
                    "deduplication_complete",
                    question_id=question_id,
                    **dedup_stats,
                )

            total_time = time.time() - start_time

            result = {
                "question_id": question_id,
                "question": file_info["question"],
                "ground_truth": file_info["ground_truth"],
                "status": "success",
                "chunking": chunk_stats,
                "extraction": extract_stats,
                "deduplication": dedup_stats,
                "final_entities": len(all_entities),
                "final_relations": len(all_relations),
                "total_time_seconds": round(total_time, 3),
            }

            results.append(result)

            logger.info(
                "file_processing_complete",
                question_id=question_id,
                entities=len(all_entities),
                relations=len(all_relations),
                total_time=round(total_time, 3),
            )

        except Exception as e:
            logger.error(
                "file_processing_failed",
                question_id=question_id,
                error=str(e),
            )
            results.append({
                "question_id": question_id,
                "status": "error",
                "error": str(e),
            })

    return results


def generate_evaluation_report(
    results: list[dict],
    output_path: str,
) -> dict:
    """Generate evaluation report from pipeline results.

    Args:
        results: List of pipeline results
        output_path: Path to save JSON report

    Returns:
        Report dict
    """
    successful = [r for r in results if r.get("status") == "success"]
    failed = [r for r in results if r.get("status") == "error"]

    # Aggregate chunking stats
    total_input_chars = sum(r["chunking"]["input_chars"] for r in successful)
    total_chunks = sum(r["chunking"]["chunks_created"] for r in successful)
    all_chunk_sizes = []
    for r in successful:
        all_chunk_sizes.extend(r["chunking"]["chunk_sizes_chars"])

    # Aggregate extraction stats
    total_entities_raw = sum(r["extraction"]["entities_raw"] for r in successful)
    total_relations = sum(r["extraction"]["relations_raw"] for r in successful)

    # Aggregate entity types
    entity_type_totals = defaultdict(int)
    for r in successful:
        for etype, count in r["extraction"]["entity_types"].items():
            entity_type_totals[etype] += count

    # Aggregate deduplication
    total_entities_deduped = sum(r.get("final_entities", 0) for r in successful)
    dedup_samples_with_reduction = [
        r for r in successful
        if r.get("deduplication", {}).get("reduction_percent", 0) > 0
    ]

    # Timing
    total_time = sum(r["total_time_seconds"] for r in successful)
    avg_time_per_file = total_time / len(successful) if successful else 0

    report = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_samples": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "sprint": "43",
            "feature": "43.11",
        },
        "chunking_summary": {
            "total_input_chars": total_input_chars,
            "total_chunks_created": total_chunks,
            "avg_chunk_size_chars": sum(all_chunk_sizes) / len(all_chunk_sizes) if all_chunk_sizes else 0,
            "min_chunk_size_chars": min(all_chunk_sizes) if all_chunk_sizes else 0,
            "max_chunk_size_chars": max(all_chunk_sizes) if all_chunk_sizes else 0,
        },
        "extraction_summary": {
            "total_entities_raw": total_entities_raw,
            "total_relations": total_relations,
            "entity_types": dict(entity_type_totals),
            "avg_entities_per_sample": total_entities_raw / len(successful) if successful else 0,
            "avg_relations_per_sample": total_relations / len(successful) if successful else 0,
        },
        "deduplication_summary": {
            "total_entities_before": total_entities_raw,
            "total_entities_after": total_entities_deduped,
            "overall_reduction_percent": round(
                (1 - total_entities_deduped / total_entities_raw) * 100, 1
            ) if total_entities_raw > 0 else 0,
            "samples_with_reduction": len(dedup_samples_with_reduction),
        },
        "timing_summary": {
            "total_time_seconds": round(total_time, 2),
            "avg_time_per_sample_seconds": round(avg_time_per_file, 2),
        },
        "results": results,
    }

    # Save report
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(
        "evaluation_report_generated",
        output_path=output_path,
        samples=len(results),
        successful=len(successful),
        failed=len(failed),
    )

    return report


def print_summary(report: dict) -> None:
    """Print human-readable summary of evaluation."""
    print("\n" + "=" * 70)
    print("RAGAS TXT PIPELINE EVALUATION - SUMMARY")
    print("=" * 70)

    meta = report["metadata"]
    print(f"\nSamples: {meta['successful']}/{meta['total_samples']} successful")
    print(f"Sprint: {meta['sprint']} Feature: {meta['feature']}")
    print(f"Timestamp: {meta['timestamp']}")

    print("\n--- CHUNKING ---")
    chunk = report["chunking_summary"]
    print(f"Total Input: {chunk['total_input_chars']:,} chars")
    print(f"Chunks Created: {chunk['total_chunks_created']}")
    print(f"Avg Chunk Size: {chunk['avg_chunk_size_chars']:.0f} chars")
    print(f"Range: {chunk['min_chunk_size_chars']}-{chunk['max_chunk_size_chars']} chars")

    print("\n--- EXTRACTION ---")
    ext = report["extraction_summary"]
    print(f"Total Entities (raw): {ext['total_entities_raw']}")
    print(f"Total Relations: {ext['total_relations']}")
    print(f"Avg per Sample: {ext['avg_entities_per_sample']:.1f} entities, {ext['avg_relations_per_sample']:.1f} relations")
    print("Entity Types:")
    for etype, count in sorted(ext["entity_types"].items(), key=lambda x: -x[1])[:10]:
        print(f"  {etype}: {count}")

    print("\n--- DEDUPLICATION ---")
    dedup = report["deduplication_summary"]
    print(f"Before: {dedup['total_entities_before']} entities")
    print(f"After: {dedup['total_entities_after']} entities")
    print(f"Reduction: {dedup['overall_reduction_percent']:.1f}%")
    print(f"Samples with Reduction: {dedup['samples_with_reduction']}")

    print("\n--- TIMING ---")
    timing = report["timing_summary"]
    print(f"Total Time: {timing['total_time_seconds']:.1f}s")
    print(f"Avg per Sample: {timing['avg_time_per_sample_seconds']:.1f}s")

    print("\n" + "=" * 70)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="RAGAS TXT Pipeline Evaluation")
    parser.add_argument(
        "--samples",
        type=int,
        default=10,
        help="Number of samples to process (default: 10)",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="reports/track_a_evaluation/datasets/hotpotqa_eval.jsonl",
        help="Path to HotPotQA JSONL file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/ragas_eval_txt",
        help="Directory to save TXT files",
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Path for output report (default: auto-generated)",
    )
    args = parser.parse_args()

    # Generate report path if not specified
    if args.report is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.report = f"reports/ragas_txt_pipeline_eval_{timestamp}.json"

    print(f"\nRAGAS TXT Pipeline Evaluation - Sprint 43 Feature 43.11")
    print(f"{'=' * 60}")
    print(f"Samples: {args.samples}")
    print(f"Input: {args.input}")
    print(f"Output Dir: {args.output_dir}")
    print(f"Report: {args.report}")
    print(f"{'=' * 60}\n")

    # Step 1: Load samples
    print("Step 1: Loading HotPotQA samples...")
    samples = load_hotpotqa_samples(args.input, args.samples)

    # Step 2: Save as TXT files
    print("\nStep 2: Saving samples as TXT files...")
    file_infos = save_samples_as_txt(samples, args.output_dir)

    # Step 3: Run pipeline
    print("\nStep 3: Running production pipeline on TXT files...")
    results = await run_pipeline_on_txt_files(file_infos)

    # Step 4: Generate report
    print("\nStep 4: Generating evaluation report...")
    report = generate_evaluation_report(results, args.report)

    # Print summary
    print_summary(report)

    print(f"\nReport saved to: {args.report}")


if __name__ == "__main__":
    asyncio.run(main())
