#!/usr/bin/env python3
"""
Sprint 20 Feature 20.1 Extended: Comprehensive Model Evaluation

Evaluates LLMs across ALL use cases:
1. Entity & Relation Extraction (Graph Construction)
2. RAG Chat Generation (Question Answering)

Usage:
    # Evaluate both use cases
    python scripts/evaluate_models_comprehensive.py --mode all

    # Only extraction
    python scripts/evaluate_models_comprehensive.py --mode extraction

    # Only chat
    python scripts/evaluate_models_comprehensive.py --mode chat

    # Specific model
    python scripts/evaluate_models_comprehensive.py --mode all --model gemma

Requirements:
    - Test documents in data/test_documents/
    - Ground truth annotations in scripts/ground_truth.yaml
    - Ollama running with models available
    - Qdrant running for chat evaluation
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "aegis_documents"

# Models to evaluate
MODELS = {
    "llama3.2:3b": "llama3.2:3b",
    "gemma": "gemma-3-4b-it-Q8_0",
}


# ============================================================================
# USE CASE 1: ENTITY & RELATION EXTRACTION EVALUATION
# ============================================================================


async def load_ground_truth() -> Dict:
    """Load ground truth annotations for entity/relation extraction."""
    gt_file = Path(__file__).parent / "ground_truth.yaml"

    if not gt_file.exists():
        console.print(f"[yellow]Warning: {gt_file} not found[/yellow]")
        console.print("[yellow]Creating template ground_truth.yaml...[/yellow]")
        create_ground_truth_template(gt_file)
        console.print(f"[green]Template created at {gt_file}[/green]")
        console.print("[yellow]Please fill in ground truth data and run again.[/yellow]")
        return {"test_cases": []}

    with open(gt_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_ground_truth_template(output_path: Path):
    """Create template ground truth file for annotation."""
    template = {
        "version": "1.0",
        "description": "Ground truth annotations for entity/relation extraction evaluation",
        "test_cases": [
            {
                "id": "test_001",
                "text": "VBScript is a scripting language developed by Microsoft. "
                        "It is used for automation in Windows environments.",
                "ground_truth_entities": [
                    {
                        "name": "VBScript",
                        "type": "PRODUCT",
                        "description": "VBScript is a scripting language"
                    },
                    {
                        "name": "Microsoft",
                        "type": "ORGANIZATION",
                        "description": "Microsoft is a company"
                    },
                    {
                        "name": "Windows",
                        "type": "PRODUCT",
                        "description": "Windows is an operating system"
                    }
                ],
                "ground_truth_relations": [
                    {
                        "source": "VBScript",
                        "target": "Microsoft",
                        "description": "VBScript was developed by Microsoft",
                        "strength": 9
                    },
                    {
                        "source": "VBScript",
                        "target": "Windows",
                        "description": "VBScript is used in Windows environments",
                        "strength": 8
                    }
                ]
            },
            {
                "id": "test_002",
                "text": "TODO: Add more test cases with your domain-specific text",
                "ground_truth_entities": [],
                "ground_truth_relations": []
            }
        ]
    }

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(template, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


async def extract_entities_relations(text: str, model: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Extract entities and relations using Three-Phase Pipeline.

    Returns:
        Tuple of (entities, relations)
    """
    try:
        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

        # Initialize extractor
        extractor = ThreePhaseExtractor()

        # Extract
        entities, relations = await extractor.extract(text, document_id="eval_test")

        return entities, relations

    except Exception as e:
        console.print(f"[red]Error in extraction: {e}[/red]")
        return [], []


def calculate_entity_metrics(
    predicted: List[Dict],
    ground_truth: List[Dict],
    match_threshold: float = 0.8
) -> Dict:
    """
    Calculate Precision, Recall, F1 for entity extraction.

    Entities match if:
    - Names are similar (normalized string matching)
    - Types match (if specified in ground truth)

    Args:
        predicted: List of predicted entities
        ground_truth: List of ground truth entities
        match_threshold: Similarity threshold for name matching (0.0-1.0)

    Returns:
        Dict with precision, recall, f1, true_positives, false_positives, false_negatives
    """
    from difflib import SequenceMatcher

    def normalize(text: str) -> str:
        """Normalize entity name for comparison."""
        return text.lower().strip()

    def entities_match(pred: Dict, gt: Dict) -> bool:
        """Check if predicted entity matches ground truth entity."""
        pred_name = normalize(pred.get("name", ""))
        gt_name = normalize(gt.get("name", ""))

        # Calculate similarity
        similarity = SequenceMatcher(None, pred_name, gt_name).ratio()

        # Check type match (if specified)
        pred_type = pred.get("type", "").upper()
        gt_type = gt.get("type", "").upper()

        type_match = (gt_type == "" or pred_type == gt_type)

        return similarity >= match_threshold and type_match

    # Find matches
    true_positives = 0
    matched_gt = set()
    matched_pred = set()

    for i, pred_entity in enumerate(predicted):
        for j, gt_entity in enumerate(ground_truth):
            if j not in matched_gt and entities_match(pred_entity, gt_entity):
                true_positives += 1
                matched_gt.add(j)
                matched_pred.add(i)
                break

    false_positives = len(predicted) - true_positives
    false_negatives = len(ground_truth) - true_positives

    # Calculate metrics
    precision = true_positives / len(predicted) if predicted else 0.0
    recall = true_positives / len(ground_truth) if ground_truth else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "predicted_count": len(predicted),
        "ground_truth_count": len(ground_truth),
    }


def calculate_relation_metrics(
    predicted: List[Dict],
    ground_truth: List[Dict],
    match_threshold: float = 0.7
) -> Dict:
    """
    Calculate Precision, Recall, F1 for relation extraction.

    Relations match if:
    - Source entities match
    - Target entities match
    - (Optional) Description similarity above threshold

    Args:
        predicted: List of predicted relations
        ground_truth: List of ground truth relations
        match_threshold: Similarity threshold for description matching

    Returns:
        Dict with precision, recall, f1, and counts
    """
    from difflib import SequenceMatcher

    def normalize(text: str) -> str:
        return text.lower().strip()

    def relations_match(pred: Dict, gt: Dict) -> bool:
        """Check if predicted relation matches ground truth."""
        pred_src = normalize(pred.get("source", ""))
        pred_tgt = normalize(pred.get("target", ""))
        gt_src = normalize(gt.get("source", ""))
        gt_tgt = normalize(gt.get("target", ""))

        # Check entity matching (bidirectional)
        entities_match = (
            (pred_src == gt_src and pred_tgt == gt_tgt) or
            (pred_src == gt_tgt and pred_tgt == gt_src)  # Reversed direction
        )

        return entities_match

    # Find matches
    true_positives = 0
    matched_gt = set()

    for pred_rel in predicted:
        for j, gt_rel in enumerate(ground_truth):
            if j not in matched_gt and relations_match(pred_rel, gt_rel):
                true_positives += 1
                matched_gt.add(j)
                break

    false_positives = len(predicted) - true_positives
    false_negatives = len(ground_truth) - true_positives

    precision = true_positives / len(predicted) if predicted else 0.0
    recall = true_positives / len(ground_truth) if ground_truth else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "predicted_count": len(predicted),
        "ground_truth_count": len(ground_truth),
    }


async def evaluate_extraction(model: str) -> Dict:
    """
    Evaluate entity and relation extraction for a model.

    Args:
        model: Model name to evaluate

    Returns:
        Dict with evaluation results
    """
    console.print(f"\n[bold cyan]Evaluating Extraction: {model}[/bold cyan]")

    # Load ground truth
    ground_truth_data = await load_ground_truth()
    test_cases = ground_truth_data.get("test_cases", [])

    if not test_cases or not test_cases[0].get("ground_truth_entities"):
        console.print("[yellow]No ground truth data available. Skipping extraction evaluation.[/yellow]")
        return {"skipped": True, "reason": "no_ground_truth"}

    all_entity_metrics = []
    all_relation_metrics = []
    results_per_case = []

    for test_case in test_cases:
        test_id = test_case.get("id", "unknown")
        text = test_case.get("text", "")
        gt_entities = test_case.get("ground_truth_entities", [])
        gt_relations = test_case.get("ground_truth_relations", [])

        if not text or text.startswith("TODO"):
            continue

        console.print(f"\n[cyan]Test Case: {test_id}[/cyan]")
        console.print(f"[dim]{text[:100]}...[/dim]" if len(text) > 100 else f"[dim]{text}[/dim]")

        # Extract
        start_time = time.perf_counter()
        pred_entities, pred_relations = await extract_entities_relations(text, model)
        extraction_time = time.perf_counter() - start_time

        # Calculate metrics
        entity_metrics = calculate_entity_metrics(pred_entities, gt_entities)
        relation_metrics = calculate_relation_metrics(pred_relations, gt_relations)

        console.print(f"[green]Entities: P={entity_metrics['precision']:.2f}, R={entity_metrics['recall']:.2f}, F1={entity_metrics['f1']:.2f}[/green]")
        console.print(f"[green]Relations: P={relation_metrics['precision']:.2f}, R={relation_metrics['recall']:.2f}, F1={relation_metrics['f1']:.2f}[/green]")
        console.print(f"[dim]Time: {extraction_time:.2f}s[/dim]")

        all_entity_metrics.append(entity_metrics)
        all_relation_metrics.append(relation_metrics)

        results_per_case.append({
            "test_id": test_id,
            "text": text,
            "extraction_time_seconds": extraction_time,
            "predicted_entities": pred_entities,
            "predicted_relations": pred_relations,
            "entity_metrics": entity_metrics,
            "relation_metrics": relation_metrics,
        })

    # Aggregate metrics
    avg_entity_precision = sum(m["precision"] for m in all_entity_metrics) / len(all_entity_metrics) if all_entity_metrics else 0.0
    avg_entity_recall = sum(m["recall"] for m in all_entity_metrics) / len(all_entity_metrics) if all_entity_metrics else 0.0
    avg_entity_f1 = sum(m["f1"] for m in all_entity_metrics) / len(all_entity_metrics) if all_entity_metrics else 0.0

    avg_relation_precision = sum(m["precision"] for m in all_relation_metrics) / len(all_relation_metrics) if all_relation_metrics else 0.0
    avg_relation_recall = sum(m["recall"] for m in all_relation_metrics) / len(all_relation_metrics) if all_relation_metrics else 0.0
    avg_relation_f1 = sum(m["f1"] for m in all_relation_metrics) / len(all_relation_metrics) if all_relation_metrics else 0.0

    return {
        "model": model,
        "test_cases_evaluated": len(results_per_case),
        "entity_metrics": {
            "avg_precision": avg_entity_precision,
            "avg_recall": avg_entity_recall,
            "avg_f1": avg_entity_f1,
        },
        "relation_metrics": {
            "avg_precision": avg_relation_precision,
            "avg_recall": avg_relation_recall,
            "avg_f1": avg_relation_f1,
        },
        "detailed_results": results_per_case,
    }


# ============================================================================
# USE CASE 2: RAG CHAT GENERATION EVALUATION
# ============================================================================


async def load_chat_questions() -> List[Dict]:
    """Load chat evaluation questions."""
    questions_file = Path(__file__).parent / "test_questions.yaml"

    if not questions_file.exists():
        console.print(f"[yellow]Warning: {questions_file} not found[/yellow]")
        return []

    with open(questions_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data.get("questions", [])


async def evaluate_chat(model: str) -> Dict:
    """
    Evaluate RAG chat generation for a model.

    Uses existing evaluate_chat_models.py logic.
    """
    console.print(f"\n[bold cyan]Evaluating Chat: {model}[/bold cyan]")

    questions = await load_chat_questions()

    if not questions:
        console.print("[yellow]No chat questions available. Skipping chat evaluation.[/yellow]")
        return {"skipped": True, "reason": "no_questions"}

    console.print(f"[green]Loaded {len(questions)} chat questions[/green]")
    console.print("[yellow]Chat evaluation: Manual human evaluation required[/yellow]")
    console.print("[dim]See evaluate_chat_models.py for full chat evaluation[/dim]")

    # For now, just return placeholder
    # Full implementation would duplicate evaluate_chat_models.py logic
    return {
        "model": model,
        "questions_count": len(questions),
        "note": "Run evaluate_chat_models.py for full chat evaluation",
    }


# ============================================================================
# MAIN EVALUATION ORCHESTRATION
# ============================================================================


async def main():
    """Main evaluation orchestration."""
    import argparse

    parser = argparse.ArgumentParser(description="Comprehensive Model Evaluation")
    parser.add_argument(
        "--mode",
        choices=["all", "extraction", "chat"],
        default="all",
        help="Evaluation mode"
    )
    parser.add_argument(
        "--model",
        choices=list(MODELS.keys()) + ["all"],
        default="all",
        help="Model to evaluate"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/sprints/SPRINT_20_COMPREHENSIVE_EVAL.json"),
        help="Output file"
    )

    args = parser.parse_args()

    # Print header
    console.print(Panel.fit(
        "[bold cyan]Sprint 20 Feature 20.1 Extended[/bold cyan]\n"
        "[dim]Comprehensive Model Evaluation[/dim]\n\n"
        f"Mode: {args.mode}\n"
        f"Model: {args.model}",
        border_style="cyan"
    ))

    # Determine models to test
    if args.model == "all":
        models_to_test = list(MODELS.values())
    else:
        models_to_test = [MODELS[args.model]]

    # Run evaluations
    all_results = {}

    for model in models_to_test:
        model_results = {"model": model}

        # Extraction evaluation
        if args.mode in ["all", "extraction"]:
            extraction_results = await evaluate_extraction(model)
            model_results["extraction"] = extraction_results

        # Chat evaluation
        if args.mode in ["all", "chat"]:
            chat_results = await evaluate_chat(model)
            model_results["chat"] = chat_results

        all_results[model] = model_results

    # Print summary table
    print_summary_table(all_results, args.mode)

    # Save results
    output_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "mode": args.mode,
        "models_evaluated": models_to_test,
        "results": all_results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    console.print(f"\n[bold green]Results saved to {args.output}[/bold green]")


def print_summary_table(results: Dict, mode: str):
    """Print summary table of evaluation results."""
    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print("[bold cyan]EVALUATION SUMMARY[/bold cyan]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")

    if mode in ["all", "extraction"]:
        table = Table(title="Entity & Relation Extraction Metrics", show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan")
        table.add_column("Entity P", justify="right")
        table.add_column("Entity R", justify="right")
        table.add_column("Entity F1", justify="right")
        table.add_column("Relation P", justify="right")
        table.add_column("Relation R", justify="right")
        table.add_column("Relation F1", justify="right")

        for model, model_results in results.items():
            if "extraction" in model_results and not model_results["extraction"].get("skipped"):
                ext = model_results["extraction"]
                em = ext.get("entity_metrics", {})
                rm = ext.get("relation_metrics", {})

                table.add_row(
                    model,
                    f"{em.get('avg_precision', 0):.2f}",
                    f"{em.get('avg_recall', 0):.2f}",
                    f"{em.get('avg_f1', 0):.2f}",
                    f"{rm.get('avg_precision', 0):.2f}",
                    f"{rm.get('avg_recall', 0):.2f}",
                    f"{rm.get('avg_f1', 0):.2f}",
                )

        console.print(table)

    console.print("\n[bold yellow]Next Steps:[/bold yellow]")
    console.print("1. Review detailed results in output JSON file")
    console.print("2. Fill in more ground truth test cases in ground_truth.yaml")
    console.print("3. Run chat evaluation with evaluate_chat_models.py")
    console.print("4. Document findings in SPRINT_20_MODEL_EVALUATION.md")


if __name__ == "__main__":
    asyncio.run(main())
