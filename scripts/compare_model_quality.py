#!/usr/bin/env python3
"""Sprint 44: Model Quality Comparison Script.

Compares extraction quality between different LLM models by analyzing:
- Entity overlap (Precision/Recall vs reference model)
- Relation overlap
- Unique extractions per model

Uses qwen3:32b as the reference (gold standard) model.

Usage:
    poetry run python scripts/compare_model_quality.py --samples 3
    poetry run python scripts/compare_model_quality.py --samples 5 --reference qwen3:32b

Author: Claude Code
Date: 2025-12-12
"""

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

# Setup logging
os.environ.setdefault("LOG_LEVEL", "INFO")
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(20),
)
logger = structlog.get_logger(__name__)


def normalize_entity_name(name: str) -> str:
    """Normalize entity name for comparison.

    Handles variations like:
    - Case differences: "Scott Derrickson" vs "scott derrickson"
    - Extra whitespace
    - Punctuation variations
    """
    if not name:
        return ""
    # Lowercase, strip whitespace, remove common punctuation
    normalized = name.lower().strip()
    # Remove quotes
    normalized = normalized.replace('"', '').replace("'", "")
    # Collapse multiple spaces
    normalized = " ".join(normalized.split())
    return normalized


def normalize_relation(rel: dict) -> tuple:
    """Normalize relation for comparison.

    Returns tuple of (source, relation_type, target) normalized.
    """
    source = normalize_entity_name(rel.get("source", ""))
    target = normalize_entity_name(rel.get("target", ""))
    rel_type = rel.get("type", rel.get("relationship_type", "")).upper().strip()
    return (source, rel_type, target)


def calculate_overlap(set_a: set, set_b: set) -> dict:
    """Calculate overlap metrics between two sets.

    Args:
        set_a: First set (typically candidate model)
        set_b: Second set (typically reference model)

    Returns:
        Dict with intersection, precision, recall, f1
    """
    if not set_a and not set_b:
        return {
            "intersection": 0,
            "set_a_size": 0,
            "set_b_size": 0,
            "precision": 1.0,  # Both empty = perfect
            "recall": 1.0,
            "f1": 1.0,
            "unique_to_a": 0,
            "unique_to_b": 0,
        }

    intersection = set_a & set_b
    unique_to_a = set_a - set_b
    unique_to_b = set_b - set_a

    precision = len(intersection) / len(set_a) if set_a else 0.0
    recall = len(intersection) / len(set_b) if set_b else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "intersection": len(intersection),
        "set_a_size": len(set_a),
        "set_b_size": len(set_b),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "unique_to_a": len(unique_to_a),
        "unique_to_b": len(unique_to_b),
        "unique_to_a_items": sorted(list(unique_to_a))[:10],  # Sample
        "unique_to_b_items": sorted(list(unique_to_b))[:10],
    }


def load_hotpotqa_samples(jsonl_path: str, num_samples: int = 3) -> list[dict]:
    """Load HotPotQA samples from JSONL file."""
    samples = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= num_samples:
                break
            sample = json.loads(line.strip())
            samples.append(sample)
    logger.info("samples_loaded", count=len(samples), path=jsonl_path)
    return samples


async def extract_with_model(
    text: str,
    model: str,
    sample_id: str,
) -> tuple[list[dict], list[dict]]:
    """Extract entities and relations using specified model.

    Returns:
        Tuple of (entities, relations) as dicts
    """
    from src.components.graph_rag.extraction_service import ExtractionService

    # Set model in environment
    os.environ["OLLAMA_MODEL_GENERATION"] = model

    extraction_service = ExtractionService(llm_model=model)

    try:
        # Extract entities
        entities = await extraction_service.extract_entities(text)
        entity_dicts = [
            e.model_dump() if hasattr(e, "model_dump") else e
            for e in entities
        ]

        # Extract relations
        relations = await extraction_service.extract_relationships(text, entities)
        relation_dicts = [
            r.model_dump() if hasattr(r, "model_dump") else r
            for r in relations
        ]

        logger.info(
            "extraction_complete",
            model=model,
            sample_id=sample_id,
            entities=len(entity_dicts),
            relations=len(relation_dicts),
        )

        return entity_dicts, relation_dicts

    except Exception as e:
        logger.error("extraction_failed", model=model, sample_id=sample_id, error=str(e))
        return [], []


async def compare_models(
    samples: list[dict],
    models: list[str],
    reference_model: str,
) -> dict:
    """Compare extraction quality across models.

    Args:
        samples: HotPotQA samples
        models: List of models to compare
        reference_model: Model to use as gold standard

    Returns:
        Comparison report dict
    """
    results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "reference_model": reference_model,
            "candidate_models": [m for m in models if m != reference_model],
            "num_samples": len(samples),
        },
        "per_sample": [],
        "aggregated": {},
    }

    # Extract from all models for all samples
    all_extractions = defaultdict(dict)  # model -> sample_idx -> {entities, relations}

    for sample_idx, sample in enumerate(samples):
        sample_id = f"sample_{sample_idx:04d}"
        text = "\n\n".join(sample.get("contexts", []))

        logger.info("processing_sample", sample_idx=sample_idx + 1, total=len(samples))

        for model in models:
            logger.info("extracting", model=model, sample_id=sample_id)
            entities, relations = await extract_with_model(text, model, sample_id)
            all_extractions[model][sample_idx] = {
                "entities": entities,
                "relations": relations,
            }

    # Compare each candidate model to reference
    for sample_idx, sample in enumerate(samples):
        sample_id = f"sample_{sample_idx:04d}"
        question = sample.get("question", "")

        sample_comparison = {
            "sample_id": sample_id,
            "question": question,
            "comparisons": {},
        }

        # Get reference extractions
        ref_data = all_extractions[reference_model][sample_idx]
        ref_entities = set(normalize_entity_name(e.get("name", "")) for e in ref_data["entities"])
        ref_relations = set(normalize_relation(r) for r in ref_data["relations"])

        sample_comparison["reference"] = {
            "model": reference_model,
            "entities_count": len(ref_entities),
            "relations_count": len(ref_relations),
            "entity_names": sorted(list(ref_entities)),
        }

        # Compare each candidate
        for model in models:
            if model == reference_model:
                continue

            cand_data = all_extractions[model][sample_idx]
            cand_entities = set(normalize_entity_name(e.get("name", "")) for e in cand_data["entities"])
            cand_relations = set(normalize_relation(r) for r in cand_data["relations"])

            entity_comparison = calculate_overlap(cand_entities, ref_entities)
            relation_comparison = calculate_overlap(cand_relations, ref_relations)

            sample_comparison["comparisons"][model] = {
                "entities": entity_comparison,
                "relations": relation_comparison,
                "entity_names": sorted(list(cand_entities)),
            }

        results["per_sample"].append(sample_comparison)

    # Aggregate results
    for model in models:
        if model == reference_model:
            continue

        entity_precisions = []
        entity_recalls = []
        entity_f1s = []
        relation_precisions = []
        relation_recalls = []
        relation_f1s = []

        for sample in results["per_sample"]:
            comp = sample["comparisons"].get(model, {})
            if comp:
                entity_precisions.append(comp["entities"]["precision"])
                entity_recalls.append(comp["entities"]["recall"])
                entity_f1s.append(comp["entities"]["f1"])
                relation_precisions.append(comp["relations"]["precision"])
                relation_recalls.append(comp["relations"]["recall"])
                relation_f1s.append(comp["relations"]["f1"])

        results["aggregated"][model] = {
            "vs_reference": reference_model,
            "entity_metrics": {
                "avg_precision": round(sum(entity_precisions) / len(entity_precisions), 3) if entity_precisions else 0,
                "avg_recall": round(sum(entity_recalls) / len(entity_recalls), 3) if entity_recalls else 0,
                "avg_f1": round(sum(entity_f1s) / len(entity_f1s), 3) if entity_f1s else 0,
            },
            "relation_metrics": {
                "avg_precision": round(sum(relation_precisions) / len(relation_precisions), 3) if relation_precisions else 0,
                "avg_recall": round(sum(relation_recalls) / len(relation_recalls), 3) if relation_recalls else 0,
                "avg_f1": round(sum(relation_f1s) / len(relation_f1s), 3) if relation_f1s else 0,
            },
        }

    return results


def generate_markdown_report(results: dict) -> str:
    """Generate markdown report from comparison results."""
    lines = [
        "# Model Quality Comparison Report",
        "",
        f"**Date:** {results['metadata']['timestamp'][:10]}",
        f"**Reference Model:** {results['metadata']['reference_model']}",
        f"**Samples:** {results['metadata']['num_samples']}",
        "",
        "---",
        "",
        "## Aggregated Results (vs Reference)",
        "",
        "### Entity Extraction Quality",
        "",
        "| Model | Precision | Recall | F1 Score |",
        "|-------|-----------|--------|----------|",
    ]

    for model, agg in results["aggregated"].items():
        em = agg["entity_metrics"]
        lines.append(f"| {model} | {em['avg_precision']:.1%} | {em['avg_recall']:.1%} | {em['avg_f1']:.1%} |")

    lines.extend([
        "",
        "### Relation Extraction Quality",
        "",
        "| Model | Precision | Recall | F1 Score |",
        "|-------|-----------|--------|----------|",
    ])

    for model, agg in results["aggregated"].items():
        rm = agg["relation_metrics"]
        lines.append(f"| {model} | {rm['avg_precision']:.1%} | {rm['avg_recall']:.1%} | {rm['avg_f1']:.1%} |")

    lines.extend([
        "",
        "---",
        "",
        "## Interpretation Guide",
        "",
        "- **Precision**: How many of the model's extractions are also in the reference? (Higher = fewer false positives)",
        "- **Recall**: How many of the reference's extractions does the model find? (Higher = fewer misses)",
        "- **F1 Score**: Harmonic mean of precision and recall (balanced metric)",
        "",
        "### Quality Thresholds",
        "",
        "| Quality Level | F1 Score |",
        "|---------------|----------|",
        "| Excellent | >= 80% |",
        "| Good | 60-80% |",
        "| Moderate | 40-60% |",
        "| Poor | < 40% |",
        "",
        "---",
        "",
        "## Per-Sample Details",
        "",
    ])

    for sample in results["per_sample"]:
        lines.extend([
            f"### {sample['sample_id']}",
            f"**Question:** {sample['question']}",
            "",
            f"**Reference ({sample['reference']['model']}):** {sample['reference']['entities_count']} entities",
            "",
        ])

        for model, comp in sample["comparisons"].items():
            ent = comp["entities"]
            rel = comp["relations"]
            lines.extend([
                f"**{model}:**",
                f"- Entities: {ent['set_a_size']} found, {ent['intersection']} overlap ({ent['recall']:.0%} recall)",
                f"- Relations: {rel['set_a_size']} found, {rel['intersection']} overlap ({rel['recall']:.0%} recall)",
            ])

            if ent["unique_to_a_items"]:
                unique_str = ", ".join(ent["unique_to_a_items"][:5])
                lines.append(f"- Unique entities: {unique_str}...")
            if ent["unique_to_b_items"]:
                missed_str = ", ".join(ent["unique_to_b_items"][:5])
                lines.append(f"- Missed entities: {missed_str}...")
            lines.append("")

    lines.extend([
        "---",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ])

    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Compare model extraction quality")
    parser.add_argument(
        "--samples",
        type=int,
        default=3,
        help="Number of samples to compare (default: 3)",
    )
    parser.add_argument(
        "--reference",
        type=str,
        default="qwen3:32b",
        help="Reference model (gold standard)",
    )
    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        default=["qwen3:32b", "qwen2.5:7b", "qwen2.5:3b", "qwen3:8b"],
        help="Models to compare",
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
        default="reports/sprint44_evaluation",
        help="Output directory for reports",
    )

    args = parser.parse_args()

    # Load samples
    samples = load_hotpotqa_samples(args.dataset, args.samples)
    if not samples:
        logger.error("no_samples_loaded")
        sys.exit(1)

    # Run comparison
    logger.info(
        "starting_comparison",
        reference=args.reference,
        models=args.models,
        samples=len(samples),
    )

    results = asyncio.run(compare_models(samples, args.models, args.reference))

    # Save reports
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON report
    json_path = output_dir / f"quality_comparison_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info("json_report_saved", path=str(json_path))

    # Markdown report
    md_content = generate_markdown_report(results)
    md_path = output_dir / f"quality_comparison_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info("markdown_report_saved", path=str(md_path))

    # Print summary
    print("\n" + "=" * 70)
    print("MODEL QUALITY COMPARISON RESULTS")
    print("=" * 70)
    print(f"\nReference Model: {args.reference}")
    print(f"Samples Compared: {len(samples)}")
    print("\n" + "-" * 70)
    print(f"{'Model':<20} {'Entity F1':>12} {'Relation F1':>12}")
    print("-" * 70)

    for model, agg in results["aggregated"].items():
        entity_f1 = agg["entity_metrics"]["avg_f1"]
        relation_f1 = agg["relation_metrics"]["avg_f1"]
        print(f"{model:<20} {entity_f1:>11.1%} {relation_f1:>12.1%}")

    print("-" * 70)
    print(f"\nReports saved to: {output_dir}")
    print(f"  - {json_path.name}")
    print(f"  - {md_path.name}")
    print("=" * 70)


if __name__ == "__main__":
    main()
