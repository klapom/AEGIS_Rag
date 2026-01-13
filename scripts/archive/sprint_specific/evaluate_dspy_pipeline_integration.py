#!/usr/bin/env python3
"""Evaluate DSPy Pipeline Integration - Sprint 86.

This script evaluates the DSPy-optimized prompts integrated into the production pipeline.
Compares baseline (generic prompts) vs DSPy-optimized prompts.

Key metrics tracked:
- Entity count & F1
- Relation count & F1
- E/R ratio
- Latency (P50, P95)
- Pipeline compatibility

Usage:
    # Baseline evaluation (default)
    poetry run python scripts/evaluate_dspy_pipeline_integration.py

    # DSPy-optimized evaluation
    AEGIS_USE_DSPY_PROMPTS=1 poetry run python scripts/evaluate_dspy_pipeline_integration.py
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.components.graph_rag.extraction_service import ExtractionService
from src.prompts.extraction_prompts import USE_DSPY_PROMPTS


# Test samples - subset of DSPy training data
TEST_SAMPLES = [
    {
        "id": "tensorflow_sample",
        "text": "TensorFlow is an open-source machine learning framework developed by Google Brain team. It was released in November 2015 and supports both Python and C++ programming languages.",
        "domain": "technical",
        "expected_entities": ["TensorFlow", "Google Brain team", "November 2015", "Python", "C++"],
        "expected_relations": [
            ("TensorFlow", "Google Brain team", "DEVELOPED"),
            ("TensorFlow", "November 2015", "RELEASED_IN"),
            ("TensorFlow", "Python", "SUPPORTS"),
            ("TensorFlow", "C++", "SUPPORTS"),
        ],
    },
    {
        "id": "microsoft_sample",
        "text": "Microsoft was founded by Bill Gates and Paul Allen in 1975 in Albuquerque, New Mexico. The company later moved its headquarters to Redmond, Washington.",
        "domain": "organizational",
        "expected_entities": ["Microsoft", "Bill Gates", "Paul Allen", "1975", "Albuquerque, New Mexico", "Redmond, Washington"],
        "expected_relations": [
            ("Bill Gates", "Microsoft", "FOUNDED"),
            ("Paul Allen", "Microsoft", "FOUNDED"),
            ("Microsoft", "1975", "FOUNDED_IN"),
            ("Microsoft", "Albuquerque, New Mexico", "FOUNDED_IN"),
            ("Microsoft", "Redmond, Washington", "MOVED_TO"),
        ],
    },
    {
        "id": "neo4j_sample",
        "text": "Neo4j is a graph database management system developed by Neo4j, Inc. It uses the Cypher query language for data manipulation. Neo4j supports ACID transactions and is written in Java. The database is commonly used for recommendation engines, fraud detection, and knowledge graphs.",
        "domain": "technical",
        "expected_entities": ["Neo4j", "Neo4j, Inc.", "Cypher", "Java", "ACID"],
        "expected_relations": [
            ("Neo4j, Inc.", "Neo4j", "DEVELOPED"),
            ("Neo4j", "Cypher", "USES"),
            ("Neo4j", "Java", "WRITTEN_IN"),
            ("Neo4j", "ACID", "SUPPORTS"),
        ],
    },
    {
        "id": "einstein_sample",
        "text": "Albert Einstein was born in Ulm, Germany in 1879. He developed the theory of relativity while working at the Swiss Patent Office in Bern. In 1921, he received the Nobel Prize in Physics.",
        "domain": "scientific",
        "expected_entities": ["Albert Einstein", "Ulm", "Germany", "1879", "theory of relativity", "Swiss Patent Office", "Bern", "1921", "Nobel Prize in Physics"],
        "expected_relations": [
            ("Albert Einstein", "Ulm", "BORN_IN"),
            ("Albert Einstein", "Germany", "BORN_IN"),
            ("Albert Einstein", "1879", "BORN_IN"),
            ("Albert Einstein", "theory of relativity", "DEVELOPED"),
            ("Albert Einstein", "Swiss Patent Office", "WORKED_AT"),
            ("Albert Einstein", "Nobel Prize in Physics", "RECEIVED"),
        ],
    },
]


def calculate_entity_f1(extracted: list, expected: list) -> float:
    """Calculate F1 score for entity extraction."""
    extracted_names = {e.name.lower() for e in extracted}
    expected_names = {e.lower() for e in expected}

    if not expected_names:
        return 1.0 if not extracted_names else 0.0

    tp = len(extracted_names & expected_names)
    precision = tp / len(extracted_names) if extracted_names else 0.0
    recall = tp / len(expected_names) if expected_names else 0.0

    if precision + recall == 0:
        return 0.0

    return 2 * precision * recall / (precision + recall)


def calculate_relation_f1(extracted: list, expected: list) -> float:
    """Calculate F1 score for relation extraction."""
    def normalize_rel(source, target, rel_type):
        return (source.lower(), target.lower(), rel_type.upper().replace(" ", "_")[:20])

    extracted_set = {normalize_rel(r.source, r.target, r.type) for r in extracted}
    expected_set = {normalize_rel(s, t, rt) for s, t, rt in expected}

    if not expected_set:
        return 1.0 if not extracted_set else 0.0

    tp = len(extracted_set & expected_set)
    precision = tp / len(extracted_set) if extracted_set else 0.0
    recall = tp / len(expected_set) if expected_set else 0.0

    if precision + recall == 0:
        return 0.0

    return 2 * precision * recall / (precision + recall)


async def evaluate_sample(
    service: ExtractionService,
    sample: dict,
) -> dict:
    """Evaluate a single sample."""
    start_time = time.time()

    # Extract entities
    entities = await service.extract_entities(
        text=sample["text"],
        document_id=sample["id"],
        domain=sample["domain"],
    )

    # Extract relationships
    relationships = await service.extract_relationships(
        text=sample["text"],
        entities=entities,
        document_id=sample["id"],
        domain=sample["domain"],
    )

    latency_ms = (time.time() - start_time) * 1000

    # Calculate metrics
    entity_f1 = calculate_entity_f1(entities, sample["expected_entities"])
    relation_f1 = calculate_relation_f1(relationships, sample["expected_relations"])
    er_ratio = len(relationships) / len(entities) if entities else 0.0

    return {
        "sample_id": sample["id"],
        "domain": sample["domain"],
        "entity_count": len(entities),
        "relation_count": len(relationships),
        "entity_f1": entity_f1,
        "relation_f1": relation_f1,
        "er_ratio": er_ratio,
        "latency_ms": latency_ms,
        "entities": [{"name": e.name, "type": e.type} for e in entities],
        "relations": [{"source": r.source, "target": r.target, "type": r.type} for r in relationships],
    }


async def run_evaluation():
    """Run full evaluation."""
    print("=" * 80)
    print("🧪 DSPy Pipeline Integration Evaluation - Sprint 86")
    print("=" * 80)
    print()

    # Check mode
    mode = "DSPy-Optimized" if USE_DSPY_PROMPTS else "Baseline (Generic)"
    print(f"📋 Mode: {mode}")
    print(f"📊 Samples: {len(TEST_SAMPLES)}")
    print(f"🕐 Started: {datetime.now().isoformat()}")
    print()

    # Initialize service
    service = ExtractionService()

    # Run evaluations
    results = []
    for i, sample in enumerate(TEST_SAMPLES, 1):
        print(f"\n--- Sample {i}/{len(TEST_SAMPLES)}: {sample['id']} ---")

        try:
            result = await evaluate_sample(service, sample)
            results.append(result)

            print(f"  Entities: {result['entity_count']} (F1: {result['entity_f1']:.2f})")
            print(f"  Relations: {result['relation_count']} (F1: {result['relation_f1']:.2f})")
            print(f"  E/R Ratio: {result['er_ratio']:.2f}")
            print(f"  Latency: {result['latency_ms']:.0f}ms")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                "sample_id": sample["id"],
                "error": str(e),
                "entity_count": 0,
                "relation_count": 0,
                "entity_f1": 0.0,
                "relation_f1": 0.0,
                "er_ratio": 0.0,
                "latency_ms": 0.0,
            })

    # Calculate aggregates
    print("\n" + "=" * 80)
    print("📊 AGGREGATE RESULTS")
    print("=" * 80)

    successful = [r for r in results if "error" not in r]
    if successful:
        avg_entity_f1 = mean([r["entity_f1"] for r in successful])
        avg_relation_f1 = mean([r["relation_f1"] for r in successful])
        avg_er_ratio = mean([r["er_ratio"] for r in successful])
        total_entities = sum([r["entity_count"] for r in successful])
        total_relations = sum([r["relation_count"] for r in successful])
        latencies = [r["latency_ms"] for r in successful]

        print(f"\n| Metric | Value |")
        print(f"|--------|-------|")
        print(f"| Mode | **{mode}** |")
        print(f"| Samples | {len(successful)}/{len(TEST_SAMPLES)} |")
        print(f"| Avg Entity F1 | **{avg_entity_f1:.2f}** |")
        print(f"| Avg Relation F1 | **{avg_relation_f1:.2f}** |")
        print(f"| Avg E/R Ratio | **{avg_er_ratio:.2f}** |")
        print(f"| Total Entities | {total_entities} |")
        print(f"| Total Relations | {total_relations} |")
        print(f"| Latency P50 | {median(latencies):.0f}ms |")
        print(f"| Latency P95 | {sorted(latencies)[int(len(latencies) * 0.95)]:.0f}ms |" if len(latencies) >= 3 else f"| Latency Avg | {mean(latencies):.0f}ms |")

    # Save results
    output_dir = Path("logs/dspy_pipeline_eval")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_suffix = "dspy" if USE_DSPY_PROMPTS else "baseline"
    output_file = output_dir / f"eval_{mode_suffix}_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump({
            "mode": mode,
            "timestamp": datetime.now().isoformat(),
            "samples": len(TEST_SAMPLES),
            "successful": len(successful),
            "aggregate": {
                "avg_entity_f1": avg_entity_f1 if successful else 0.0,
                "avg_relation_f1": avg_relation_f1 if successful else 0.0,
                "avg_er_ratio": avg_er_ratio if successful else 0.0,
                "total_entities": total_entities if successful else 0,
                "total_relations": total_relations if successful else 0,
                "latency_p50_ms": median(latencies) if successful else 0,
            },
            "results": results,
        }, f, indent=2, default=str)

    print(f"\n📁 Results saved: {output_file}")
    print()

    return results


if __name__ == "__main__":
    asyncio.run(run_evaluation())
