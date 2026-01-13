#!/usr/bin/env python3
"""Sprint 86 Feature Evaluation Script.

This script evaluates the impact of Sprint 86 features on extraction quality.
Each feature is evaluated independently to measure its contribution.

Features evaluated:
- 86.7: Coreference Resolution (pronoun → antecedent)
- 86.8: Cross-Sentence Extraction (relations spanning sentences)
- 86.6: Entity Quality Filter (filter low-quality entities)
- 86.5: Relation Weight Filtering (filter weak relations)

Usage:
    poetry run python scripts/evaluate_sprint86_features.py --feature 86.7
    poetry run python scripts/evaluate_sprint86_features.py --all
"""

import argparse
import asyncio
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Set feature flags before importing extraction service
# These can be overridden by command-line args
os.environ.setdefault("AEGIS_USE_COREFERENCE", "1")

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ExtractionMetrics:
    """Metrics for a single extraction run."""

    sample_id: str
    text_length: int
    entity_count: int
    relation_count: int
    er_ratio: float
    extraction_time_ms: float

    # Coreference-specific metrics
    coreference_enabled: bool = False
    coreference_resolutions: int = 0

    # Entity quality metrics
    unique_entity_types: int = 0
    avg_entity_name_length: float = 0.0

    # Relation quality metrics
    unique_relation_types: int = 0


@dataclass
class EvalResult:
    """Result of a full evaluation run."""

    feature_name: str
    feature_enabled: bool
    timestamp: str

    # Aggregate metrics
    total_samples: int = 0
    avg_entity_count: float = 0.0
    avg_relation_count: float = 0.0
    avg_er_ratio: float = 0.0
    avg_extraction_time_ms: float = 0.0

    # Coreference metrics
    total_coreference_resolutions: int = 0
    samples_with_coreferences: int = 0

    # Per-sample details
    samples: list[ExtractionMetrics] = field(default_factory=list)


# Diverse test samples for broad evaluation
TEST_SAMPLES = [
    {
        "id": "tech_pronouns",
        "domain": "technical",
        "text": """
        Microsoft was founded by Bill Gates and Paul Allen in 1975.
        It later became one of the largest technology companies in the world.
        They revolutionized personal computing with Windows.
        The company acquired GitHub in 2018. It paid $7.5 billion for the acquisition.
        GitHub was created by Chris Wanstrath. He started it in 2008.
        """,
    },
    {
        "id": "person_narrative",
        "domain": "general",
        "text": """
        Albert Einstein was born in Germany in 1879.
        He developed the theory of relativity while working at the Swiss Patent Office.
        Einstein received the Nobel Prize in Physics in 1921.
        He later emigrated to the United States.
        His work laid the foundation for quantum mechanics.
        """,
    },
    {
        "id": "company_relations",
        "domain": "business",
        "text": """
        Tesla Inc. was founded in 2003 by Martin Eberhard and Marc Tarpenning.
        Elon Musk joined as chairman in 2004. He later became CEO.
        The company produces electric vehicles and energy storage systems.
        Its headquarters is located in Austin, Texas.
        Tesla acquired SolarCity in 2016 to expand into solar energy.
        """,
    },
    {
        "id": "research_complex",
        "domain": "research",
        "text": """
        The BERT model was introduced by Google in 2018.
        It revolutionized natural language processing with bidirectional training.
        The researchers published their findings in a paper titled "BERT: Pre-training of Deep Bidirectional Transformers".
        They achieved state-of-the-art results on multiple benchmarks.
        The model uses transformer architecture. It has 340 million parameters.
        """,
    },
    {
        "id": "mixed_entities",
        "domain": "general",
        "text": """
        Amazon was founded by Jeff Bezos in his garage in 1994.
        The company started as an online bookstore.
        It quickly expanded to sell electronics, software, and cloud services.
        Bezos served as CEO until 2021 when Andy Jassy took over.
        AWS, their cloud computing platform, generates the majority of profits.
        """,
    },
    {
        "id": "no_pronouns_baseline",
        "domain": "technical",
        "text": """
        Python is a programming language created by Guido van Rossum.
        NumPy provides numerical computing capabilities for Python.
        Pandas builds on NumPy for data manipulation.
        TensorFlow is a machine learning framework developed by Google.
        PyTorch is an alternative framework maintained by Meta.
        """,
    },
    {
        "id": "german_text",
        "domain": "general",
        "text": """
        Die Fraunhofer-Gesellschaft wurde 1949 gegründet.
        Sie ist die größte Organisation für angewandte Forschung in Europa.
        Die Organisation betreibt über 70 Institute in Deutschland.
        Max Planck war ein bedeutender deutscher Physiker.
        Er begründete die Quantenphysik mit seiner Arbeit zur Schwarzkörperstrahlung.
        """,
    },
    {
        "id": "multi_hop",
        "domain": "research",
        "text": """
        OpenAI developed GPT-4, a large language model.
        The company was co-founded by Sam Altman and Elon Musk.
        GPT-4 succeeded GPT-3, which was released in 2020.
        It demonstrates improved reasoning capabilities.
        Researchers used RLHF to align the model with human preferences.
        The technique was pioneered by Anthropic, founded by former OpenAI employees.
        """,
    },
]


async def run_extraction(text: str, document_id: str, domain: str) -> dict[str, Any]:
    """Run entity and relationship extraction on text.

    Args:
        text: Input text
        document_id: Document identifier
        domain: Domain for prompt selection

    Returns:
        Dictionary with entities, relationships, and timing
    """
    from src.components.graph_rag.extraction_service import get_extraction_service

    service = get_extraction_service()

    start_time = time.time()

    # Extract entities
    entities = await service.extract_entities(
        text=text,
        document_id=document_id,
        domain=domain,
        gleaning_steps=0,  # Disable gleaning for faster evaluation
    )

    # Extract relationships
    relationships = await service.extract_relationships(
        text=text,
        entities=entities,
        document_id=document_id,
        domain=domain,
    )

    extraction_time_ms = (time.time() - start_time) * 1000

    return {
        "entities": entities,
        "relationships": relationships,
        "extraction_time_ms": extraction_time_ms,
    }


def calculate_metrics(
    sample: dict,
    extraction_result: dict,
    coreference_enabled: bool,
) -> ExtractionMetrics:
    """Calculate metrics for a single sample extraction.

    Args:
        sample: Test sample dictionary
        extraction_result: Result from run_extraction
        coreference_enabled: Whether coreference was enabled

    Returns:
        ExtractionMetrics object
    """
    entities = extraction_result["entities"]
    relationships = extraction_result["relationships"]

    entity_count = len(entities)
    relation_count = len(relationships)
    er_ratio = relation_count / entity_count if entity_count > 0 else 0.0

    # Entity quality metrics
    entity_types = set(e.type for e in entities)
    entity_name_lengths = [len(e.name) for e in entities]
    avg_name_length = sum(entity_name_lengths) / len(entity_name_lengths) if entity_name_lengths else 0

    # Relation quality metrics
    relation_types = set(r.type for r in relationships)

    return ExtractionMetrics(
        sample_id=sample["id"],
        text_length=len(sample["text"]),
        entity_count=entity_count,
        relation_count=relation_count,
        er_ratio=er_ratio,
        extraction_time_ms=extraction_result["extraction_time_ms"],
        coreference_enabled=coreference_enabled,
        coreference_resolutions=0,  # Will be populated from logs
        unique_entity_types=len(entity_types),
        avg_entity_name_length=avg_name_length,
        unique_relation_types=len(relation_types),
    )


async def evaluate_feature(
    feature_name: str,
    feature_enabled: bool,
    samples: list[dict],
) -> EvalResult:
    """Evaluate a specific feature configuration.

    Args:
        feature_name: Name of the feature (e.g., "86.7_coreference")
        feature_enabled: Whether the feature is enabled
        samples: List of test samples

    Returns:
        EvalResult with aggregate and per-sample metrics
    """
    logger.info(
        "starting_feature_evaluation",
        feature=feature_name,
        enabled=feature_enabled,
        sample_count=len(samples),
    )

    result = EvalResult(
        feature_name=feature_name,
        feature_enabled=feature_enabled,
        timestamp=datetime.now().isoformat(),
    )

    for sample in samples:
        try:
            logger.info(
                "evaluating_sample",
                sample_id=sample["id"],
                domain=sample["domain"],
            )

            extraction_result = await run_extraction(
                text=sample["text"],
                document_id=f"eval_{sample['id']}",
                domain=sample["domain"],
            )

            metrics = calculate_metrics(
                sample=sample,
                extraction_result=extraction_result,
                coreference_enabled=feature_enabled and "coreference" in feature_name.lower(),
            )

            result.samples.append(metrics)

            logger.info(
                "sample_evaluated",
                sample_id=sample["id"],
                entities=metrics.entity_count,
                relations=metrics.relation_count,
                er_ratio=round(metrics.er_ratio, 2),
                time_ms=round(metrics.extraction_time_ms, 1),
            )

        except Exception as e:
            logger.error(
                "sample_evaluation_failed",
                sample_id=sample["id"],
                error=str(e),
            )

    # Calculate aggregates
    if result.samples:
        result.total_samples = len(result.samples)
        result.avg_entity_count = sum(s.entity_count for s in result.samples) / len(result.samples)
        result.avg_relation_count = sum(s.relation_count for s in result.samples) / len(result.samples)
        result.avg_er_ratio = sum(s.er_ratio for s in result.samples) / len(result.samples)
        result.avg_extraction_time_ms = sum(s.extraction_time_ms for s in result.samples) / len(result.samples)
        result.total_coreference_resolutions = sum(s.coreference_resolutions for s in result.samples)
        result.samples_with_coreferences = sum(1 for s in result.samples if s.coreference_resolutions > 0)

    logger.info(
        "feature_evaluation_complete",
        feature=feature_name,
        enabled=feature_enabled,
        total_samples=result.total_samples,
        avg_entities=round(result.avg_entity_count, 2),
        avg_relations=round(result.avg_relation_count, 2),
        avg_er_ratio=round(result.avg_er_ratio, 3),
        avg_time_ms=round(result.avg_extraction_time_ms, 1),
    )

    return result


def save_results(results: list[EvalResult], output_dir: str = "docs/ragas") -> str:
    """Save evaluation results to JSON file.

    Args:
        results: List of evaluation results
        output_dir: Directory to save results

    Returns:
        Path to saved file
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sprint86_eval_{timestamp}.json"
    filepath = output_path / filename

    # Convert to dict for JSON serialization
    results_dict = [asdict(r) for r in results]
    for r in results_dict:
        r["samples"] = [asdict(s) if hasattr(s, "__dict__") else s for s in r.get("samples", [])]

    with open(filepath, "w") as f:
        json.dump(results_dict, f, indent=2, default=str)

    logger.info("results_saved", path=str(filepath))
    return str(filepath)


def print_comparison(baseline: EvalResult, feature: EvalResult):
    """Print comparison between baseline and feature-enabled runs."""
    print("\n" + "=" * 70)
    print(f"COMPARISON: {baseline.feature_name} vs {feature.feature_name}")
    print("=" * 70)

    def delta(a: float, b: float) -> str:
        diff = b - a
        pct = (diff / a * 100) if a != 0 else 0
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff:.2f} ({sign}{pct:.1f}%)"

    print(f"\n{'Metric':<25} {'Baseline':>15} {'Feature':>15} {'Delta':>20}")
    print("-" * 70)
    print(f"{'Avg Entities':<25} {baseline.avg_entity_count:>15.2f} {feature.avg_entity_count:>15.2f} {delta(baseline.avg_entity_count, feature.avg_entity_count):>20}")
    print(f"{'Avg Relations':<25} {baseline.avg_relation_count:>15.2f} {feature.avg_relation_count:>15.2f} {delta(baseline.avg_relation_count, feature.avg_relation_count):>20}")
    print(f"{'Avg E/R Ratio':<25} {baseline.avg_er_ratio:>15.3f} {feature.avg_er_ratio:>15.3f} {delta(baseline.avg_er_ratio, feature.avg_er_ratio):>20}")
    print(f"{'Avg Time (ms)':<25} {baseline.avg_extraction_time_ms:>15.1f} {feature.avg_extraction_time_ms:>15.1f} {delta(baseline.avg_extraction_time_ms, feature.avg_extraction_time_ms):>20}")

    print("\n" + "=" * 70)


async def main():
    """Main evaluation entry point."""
    parser = argparse.ArgumentParser(description="Sprint 86 Feature Evaluation")
    parser.add_argument("--feature", type=str, default="86.7", help="Feature to evaluate (86.5, 86.6, 86.7, 86.8)")
    parser.add_argument("--all", action="store_true", help="Run all feature evaluations")
    parser.add_argument("--samples", type=int, default=0, help="Number of samples (0=all)")
    parser.add_argument("--output", type=str, default="docs/ragas", help="Output directory")
    args = parser.parse_args()

    samples = TEST_SAMPLES[:args.samples] if args.samples > 0 else TEST_SAMPLES

    print(f"\n🔬 Sprint 86 Feature Evaluation")
    print(f"   Samples: {len(samples)}")
    print(f"   Feature: {args.feature if not args.all else 'ALL'}")
    print()

    results = []

    if args.feature == "86.7" or args.all:
        # Evaluate 86.7: Coreference Resolution
        print("\n📊 Evaluating Feature 86.7: Coreference Resolution")
        print("-" * 50)

        from src.components.graph_rag import extraction_service

        # Baseline (coreference disabled)
        os.environ["AEGIS_USE_COREFERENCE"] = "0"
        extraction_service.USE_COREFERENCE = False
        extraction_service._coreference_resolver = None

        baseline = await evaluate_feature(
            feature_name="86.7_baseline_no_coreference",
            feature_enabled=False,
            samples=samples,
        )
        results.append(baseline)

        # With feature enabled
        os.environ["AEGIS_USE_COREFERENCE"] = "1"
        extraction_service.USE_COREFERENCE = True

        feature_result = await evaluate_feature(
            feature_name="86.7_with_coreference",
            feature_enabled=True,
            samples=samples,
        )
        results.append(feature_result)

        print_comparison(baseline, feature_result)

    if args.feature == "86.8" or args.all:
        # Evaluate 86.8: Cross-Sentence Extraction
        print("\n📊 Evaluating Feature 86.8: Cross-Sentence Extraction")
        print("-" * 50)

        from src.components.graph_rag import extraction_service

        # Baseline (cross-sentence disabled)
        os.environ["AEGIS_USE_CROSS_SENTENCE"] = "0"
        extraction_service.USE_CROSS_SENTENCE = False

        baseline = await evaluate_feature(
            feature_name="86.8_baseline_no_cross_sentence",
            feature_enabled=False,
            samples=samples,
        )
        results.append(baseline)

        # With feature enabled
        os.environ["AEGIS_USE_CROSS_SENTENCE"] = "1"
        extraction_service.USE_CROSS_SENTENCE = True

        feature_result = await evaluate_feature(
            feature_name="86.8_with_cross_sentence",
            feature_enabled=True,
            samples=samples,
        )
        results.append(feature_result)

        print_comparison(baseline, feature_result)

    if args.feature == "86.6" or args.all:
        # Evaluate 86.6: Entity Quality Filter
        print("\n📊 Evaluating Feature 86.6: Entity Quality Filter")
        print("-" * 50)

        from src.components.graph_rag import entity_quality_filter

        # Baseline (entity filter disabled)
        os.environ["AEGIS_USE_ENTITY_FILTER"] = "0"
        entity_quality_filter.USE_ENTITY_FILTER = False

        baseline = await evaluate_feature(
            feature_name="86.6_baseline_no_entity_filter",
            feature_enabled=False,
            samples=samples,
        )
        results.append(baseline)

        # With feature enabled
        os.environ["AEGIS_USE_ENTITY_FILTER"] = "1"
        entity_quality_filter.USE_ENTITY_FILTER = True

        feature_result = await evaluate_feature(
            feature_name="86.6_with_entity_filter",
            feature_enabled=True,
            samples=samples,
        )
        results.append(feature_result)

        print_comparison(baseline, feature_result)

    # Save results
    output_path = save_results(results, args.output)
    print(f"\n📁 Results saved to: {output_path}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
