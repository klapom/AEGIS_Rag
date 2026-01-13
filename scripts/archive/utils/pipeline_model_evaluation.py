#!/usr/bin/env python3
"""Sprint 44 Feature 44.11: Full Pipeline Model Evaluation.

Evaluates the complete ingestion pipeline with different LLM models:
- Chunking
- Entity Extraction
- Entity Deduplication
- Relation Deduplication
- Neo4j Storage (optional)

Uses the same HotPotQA dataset for all models to enable fair comparison.

Usage:
    poetry run python scripts/pipeline_model_evaluation.py --model qwen3:8b --samples 10
    poetry run python scripts/pipeline_model_evaluation.py --model qwen3:32b --samples 10

Author: Claude Code
Date: 2025-12-12
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

# Setup logging
os.environ.setdefault("LOG_LEVEL", "INFO")
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
)

logger = structlog.get_logger(__name__)


def load_hotpotqa_samples(jsonl_path: str, num_samples: int = 10) -> list[dict]:
    """Load HotPotQA samples from JSONL file.

    Args:
        jsonl_path: Path to hotpotqa_large.jsonl or hotpotqa_eval.jsonl
        num_samples: Number of samples to load

    Returns:
        List of sample dicts with contexts, question, ground_truth
    """
    samples = []
    with open(jsonl_path, encoding="utf-8") as f:
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


async def process_sample(
    sample: dict,
    sample_idx: int,
    model: str,
    monitor,
) -> dict:
    """Process a single sample through the full pipeline.

    Args:
        sample: HotPotQA sample dict
        sample_idx: Sample index
        model: LLM model name
        monitor: PipelineMonitor instance

    Returns:
        Result dict with metrics
    """
    # Import here to allow setting environment before import
    from src.components.graph_rag.extraction_service import ExtractionService
    from src.components.graph_rag.relation_deduplicator import RelationDeduplicator
    from src.components.graph_rag.semantic_deduplicator import create_deduplicator_from_config
    from src.core.chunking_service import ChunkingService
    from src.core.config import get_settings

    settings = get_settings()

    sample_id = f"sample_{sample_idx:04d}"
    question = sample.get("question", "")
    ground_truth = sample.get("ground_truth", "")
    contexts = sample.get("contexts", [])

    # Combine contexts into single text
    text = "\n\n".join(contexts)

    result = {
        "sample_id": sample_id,
        "question": question,
        "ground_truth": ground_truth,
        "input_chars": len(text),
        "status": "pending",
    }

    with monitor.sample(sample_id, question=question, ground_truth=ground_truth) as sample_result:
        try:
            # Stage 1: Chunking
            with monitor.stage("chunking") as stage:
                chunking_service = ChunkingService()
                chunk_objects = await chunking_service.chunk_document(
                    text=text,
                    document_id=sample_id,
                )
                # Convert Chunk objects to dicts for extraction
                chunks = [
                    {"content": c.content, "chunk_id": c.chunk_id, "metadata": c.metadata}
                    for c in chunk_objects
                ]

                stage.metrics["input_chars"] = len(text)
                stage.metrics["chunks_created"] = len(chunks)
                stage.metrics["chunk_sizes_chars"] = [len(c["content"]) for c in chunks]

                result["chunks_created"] = len(chunks)

            # Stage 2: Extraction
            all_entities = []
            all_relations = []

            with monitor.stage("extraction") as stage:
                extraction_service = ExtractionService(llm_model=model)

                for chunk in chunks:
                    chunk_text = chunk.get("content", "")
                    try:
                        # Extract entities (async) - returns GraphEntity objects
                        entities = await extraction_service.extract_entities(chunk_text)
                        # Convert to dicts for deduplication
                        entity_dicts = [
                            e.model_dump() if hasattr(e, "model_dump") else e
                            for e in entities
                        ]
                        all_entities.extend(entity_dicts)

                        # Extract relations (async) - returns GraphRelationship objects
                        relations = await extraction_service.extract_relationships(
                            chunk_text, entities
                        )
                        # Convert to dicts for deduplication
                        relation_dicts = [
                            r.model_dump() if hasattr(r, "model_dump") else r
                            for r in relations
                        ]
                        all_relations.extend(relation_dicts)
                    except Exception as e:
                        logger.warning(
                            "chunk_extraction_failed",
                            sample_id=sample_id,
                            error=str(e),
                        )

                stage.metrics["entities_raw"] = len(all_entities)
                stage.metrics["relations_raw"] = len(all_relations)

                # Count entity types
                entity_types: dict[str, int] = {}
                for ent in all_entities:
                    ent_type = ent.get("type", "UNKNOWN")
                    entity_types[ent_type] = entity_types.get(ent_type, 0) + 1
                stage.metrics["entity_types"] = entity_types

                result["entities_raw"] = len(all_entities)
                result["relations_raw"] = len(all_relations)

            # Stage 3: Entity Deduplication
            entity_mapping = {}
            with monitor.stage("entity_dedup") as stage:
                entities_before = len(all_entities)
                stage.metrics["entities_before"] = entities_before

                if all_entities:
                    deduplicator = create_deduplicator_from_config(settings)
                    if deduplicator:
                        # Sprint 49.9: Now async with BGE-M3 embeddings
                        all_entities, entity_mapping = await deduplicator.deduplicate_with_mapping(all_entities)

                entities_after = len(all_entities)
                stage.metrics["entities_after"] = entities_after
                stage.metrics["reduction_percent"] = round(
                    (1 - entities_after / entities_before) * 100, 1
                ) if entities_before > 0 else 0
                stage.metrics["mapping_size"] = len(entity_mapping)

                result["entities_deduped"] = entities_after
                result["entity_dedup_percent"] = stage.metrics["reduction_percent"]

            # Stage 4: Relation Deduplication
            with monitor.stage("relation_dedup") as stage:
                relations_before = len(all_relations)
                stage.metrics["relations_before"] = relations_before

                if all_relations:
                    relation_deduplicator = RelationDeduplicator()
                    all_relations = relation_deduplicator.deduplicate(
                        all_relations, entity_mapping=entity_mapping
                    )

                relations_after = len(all_relations)
                stage.metrics["relations_after"] = relations_after
                stage.metrics["reduction_percent"] = round(
                    (1 - relations_after / relations_before) * 100, 1
                ) if relations_before > 0 else 0

                result["relations_deduped"] = relations_after
                result["relation_dedup_percent"] = stage.metrics["reduction_percent"]

            result["status"] = "success"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(
                "sample_processing_failed",
                sample_id=sample_id,
                error=str(e),
            )

    return result


async def run_evaluation(
    model: str,
    samples: list[dict],
    output_dir: Path,
) -> dict:
    """Run full evaluation for a model.

    Args:
        model: LLM model name
        samples: List of HotPotQA samples
        output_dir: Directory for output reports

    Returns:
        Report dict
    """
    from src.monitoring.pipeline_monitor import PipelineMonitor

    # Set model in environment
    os.environ["GEMMA_MODEL"] = model
    os.environ["OLLAMA_MODEL_GENERATION"] = model

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"eval_{model.replace(':', '_')}_{timestamp}"

    monitor = PipelineMonitor(
        run_id=run_id,
        model=model,
        dataset="hotpotqa",
    )

    logger.info(
        "evaluation_started",
        model=model,
        samples=len(samples),
        run_id=run_id,
    )

    results = []
    for idx, sample in enumerate(samples):
        logger.info(
            "processing_sample",
            sample_idx=idx + 1,
            total=len(samples),
            model=model,
        )
        result = await process_sample(sample, idx, model, monitor)
        results.append(result)

    # Generate and save reports
    report = monitor.generate_report()

    # Save JSON report
    json_path = output_dir / f"pipeline_eval_{model.replace(':', '_')}_{timestamp}.json"
    monitor.save_json_report(json_path)

    # Save Markdown report
    md_path = output_dir / f"pipeline_eval_{model.replace(':', '_')}_{timestamp}.md"
    monitor.save_markdown_report(md_path)

    logger.info(
        "evaluation_complete",
        model=model,
        successful=report["metadata"]["successful"],
        failed=report["metadata"]["failed"],
        total_time=report["metadata"]["total_time_seconds"],
        json_report=str(json_path),
        md_report=str(md_path),
    )

    return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate full pipeline with different LLM models"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="qwen3:8b",
        help="LLM model for extraction (e.g., qwen3:8b, qwen2.5:7b, nuextract:3.8b)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=10,
        help="Number of samples to process",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="reports/track_a_evaluation/datasets/hotpotqa_large.jsonl",
        help="Path to HotPotQA JSONL dataset",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Output directory for reports",
    )

    args = parser.parse_args()

    # Load samples
    samples = load_hotpotqa_samples(args.dataset, args.samples)

    if not samples:
        logger.error("no_samples_loaded", dataset=args.dataset)
        sys.exit(1)

    # Run evaluation
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = asyncio.run(run_evaluation(args.model, samples, output_dir))

    # Print summary
    meta = report["metadata"]
    print("\n" + "=" * 60)
    print(f"Model: {args.model}")
    print(f"Samples: {meta['total_samples']} (Success: {meta['successful']}, Failed: {meta['failed']})")
    print(f"Total Time: {meta['total_time_seconds']:.1f}s")
    print(f"Avg Time/Sample: {meta['total_time_seconds'] / meta['total_samples']:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
