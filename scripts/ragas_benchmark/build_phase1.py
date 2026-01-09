#!/usr/bin/env python3
"""
Build RAGAS Phase 1 Dataset.

Generates a 500-sample text-only benchmark from:
- HotpotQA (multi-hop QA)
- RAGBench (comprehensive RAG benchmark)
- LogQA (log-based QA)

With:
- Stratified sampling by doc_type and question_type
- 10% unanswerable questions (50 samples)
- AegisRAG-compatible JSONL export

Sprint 82: Phase 1 - Text-Only Benchmark
ADR Reference: ADR-048

Usage:
    poetry run python scripts/ragas_benchmark/build_phase1.py
    poetry run python scripts/ragas_benchmark/build_phase1.py --output custom_output.jsonl
    poetry run python scripts/ragas_benchmark/build_phase1.py --seed 123 --dry-run
"""

import argparse
import logging
import sys
import random
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.ragas_benchmark.dataset_loader import DatasetLoader
from scripts.ragas_benchmark.sampling import (
    stratified_sample,
    rebalance_difficulty,
    validate_distribution,
)
from scripts.ragas_benchmark.unanswerable import UnanswerableGenerator
from scripts.ragas_benchmark.export import (
    export_jsonl,
    export_manifest,
    export_statistics_report,
    print_distribution_summary,
)
from scripts.ragas_benchmark.config import (
    DOC_TYPE_QUOTAS_PHASE1,
    QUESTION_TYPE_QUOTAS_PHASE1,
    DIFFICULTY_DISTRIBUTION,
    PHASE1_UNANSWERABLE_COUNT,
    PHASE1_ANSWERABLE_COUNT,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Build RAGAS Phase 1 benchmark dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--output",
        default="data/evaluation/ragas_phase1_500.jsonl",
        help="Output JSONL file path"
    )
    parser.add_argument(
        "--manifest",
        default="data/evaluation/ragas_phase1_manifest.csv",
        help="Output manifest CSV path"
    )
    parser.add_argument(
        "--report",
        default="data/evaluation/ragas_phase1_stats.md",
        help="Output statistics report path"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--max-samples-per-dataset",
        type=int,
        default=5000,
        help="Maximum samples to load per dataset"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and sample without exporting"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--skip-unanswerables",
        action="store_true",
        help="Skip unanswerable generation"
    )

    return parser.parse_args()


def progress_callback(current: int, total: int):
    """Print progress updates."""
    if current % 500 == 0:
        pct = current / total * 100
        print(f"  Processing: {current}/{total} ({pct:.1f}%)", flush=True)


def main():
    """Main entry point."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("=" * 60)
    print("RAGAS Phase 1 Dataset Builder")
    print("=" * 60)
    print(f"Seed: {args.seed}")
    print(f"Output: {args.output}")
    print(f"Target: {PHASE1_ANSWERABLE_COUNT} answerable + {PHASE1_UNANSWERABLE_COUNT} unanswerable")
    print("=" * 60)

    # Initialize components
    loader = DatasetLoader()
    rng = random.Random(args.seed)

    # =========================================================================
    # Step 1: Load Datasets
    # =========================================================================
    print("\n[1/5] Loading datasets from HuggingFace...")

    all_samples = []

    # Load HotpotQA (primary clean_text source)
    print("\n  Loading HotpotQA...")
    try:
        hotpotqa_samples = loader.load_dataset(
            "hotpot_qa",
            max_samples=args.max_samples_per_dataset,
            progress_callback=progress_callback
        )
        print(f"  ✓ HotpotQA: {len(hotpotqa_samples)} samples")
        all_samples.extend(hotpotqa_samples)
    except Exception as e:
        logger.error(f"Failed to load HotpotQA: {e}")
        print(f"  ✗ HotpotQA: FAILED - {e}")

    # Load RAGBench subsets for diversity
    ragbench_subsets = [
        ("ragbench_covidqa", "CovidQA"),
        ("ragbench_techqa", "TechQA"),
        ("ragbench_msmarco", "MSMarco"),
    ]

    for config_name, display_name in ragbench_subsets:
        print(f"\n  Loading RAGBench {display_name}...")
        try:
            subset_samples = loader.load_dataset(
                config_name,
                max_samples=500,
                progress_callback=progress_callback
            )
            print(f"  ✓ RAGBench {display_name}: {len(subset_samples)} samples")
            all_samples.extend(subset_samples)
        except Exception as e:
            logger.warning(f"Failed to load RAGBench {display_name}: {e}")
            print(f"  ⚠ RAGBench {display_name}: FAILED - {e}")

    # Load log_ticket data from RAGBench emanual
    print("\n  Loading RAGBench Emanual (as log_ticket)...")
    try:
        emanual_samples = loader.load_dataset(
            "ragbench_emanual",
            max_samples=1000,
            progress_callback=progress_callback
        )
        print(f"  ✓ RAGBench Emanual: {len(emanual_samples)} samples")
        all_samples.extend(emanual_samples)
    except Exception as e:
        logger.warning(f"Failed to load RAGBench Emanual: {e}")
        print(f"  ⚠ RAGBench Emanual: FAILED - {e}")

    print(f"\n  Total pool: {len(all_samples)} samples")

    if len(all_samples) < PHASE1_ANSWERABLE_COUNT:
        logger.error(
            f"Not enough samples loaded ({len(all_samples)}) "
            f"for target ({PHASE1_ANSWERABLE_COUNT})"
        )
        print("\n✗ ERROR: Insufficient samples. Aborting.")
        return 1

    # =========================================================================
    # Step 2: Stratified Sampling
    # =========================================================================
    print("\n[2/5] Performing stratified sampling...")

    sampled = stratified_sample(
        pool=all_samples,
        doc_type_quotas=DOC_TYPE_QUOTAS_PHASE1,
        qtype_quotas=QUESTION_TYPE_QUOTAS_PHASE1,
        seed=args.seed
    )

    print(f"  ✓ Sampled {len(sampled)} answerable samples")

    # =========================================================================
    # Step 3: Rebalance Difficulty
    # =========================================================================
    print("\n[3/5] Rebalancing difficulty distribution...")

    sampled = rebalance_difficulty(
        sampled,
        DIFFICULTY_DISTRIBUTION,
        seed=args.seed
    )

    print(f"  ✓ Difficulty rebalanced")

    # =========================================================================
    # Step 4: Generate Unanswerables
    # =========================================================================
    if not args.skip_unanswerables:
        print(f"\n[4/5] Generating {PHASE1_UNANSWERABLE_COUNT} unanswerable questions...")

        generator = UnanswerableGenerator(seed=args.seed)
        unanswerables = generator.generate_batch(
            sampled,
            target_count=PHASE1_UNANSWERABLE_COUNT
        )

        print(f"  ✓ Generated {len(unanswerables)} unanswerables")
        print(f"    Method distribution: {generator.get_stats()['by_method']}")

        # Combine and shuffle
        final_samples = sampled + unanswerables
    else:
        print("\n[4/5] Skipping unanswerable generation (--skip-unanswerables)")
        final_samples = sampled

    # Shuffle final dataset
    rng.shuffle(final_samples)

    print(f"\n  Total final samples: {len(final_samples)}")

    # =========================================================================
    # Step 5: Validate Distribution
    # =========================================================================
    print("\n[5/5] Validating distribution...")

    is_valid, validation_msg = validate_distribution(
        [s for s in final_samples if s.answerable],  # Only validate answerables
        DOC_TYPE_QUOTAS_PHASE1,
        QUESTION_TYPE_QUOTAS_PHASE1,
        tolerance_pct=10.0  # Allow 10% tolerance
    )

    if is_valid:
        print(f"  ✓ {validation_msg}")
    else:
        print(f"  ⚠ {validation_msg}")

    # =========================================================================
    # Export
    # =========================================================================
    if args.dry_run:
        print("\n[DRY RUN] Skipping export...")
        print("\nDistribution Summary:")
        print_distribution_summary(final_samples)
        return 0

    print("\nExporting...")

    # Export JSONL
    output_path = Path(args.output)
    sha256 = export_jsonl(final_samples, str(output_path))
    print(f"  ✓ JSONL: {output_path}")
    print(f"    SHA256: {sha256}")

    # Export manifest
    manifest_path = Path(args.manifest)
    export_manifest(final_samples, str(manifest_path))
    print(f"  ✓ Manifest: {manifest_path}")

    # Export statistics report
    report_path = Path(args.report)
    export_statistics_report(
        final_samples,
        str(report_path),
        dataset_name="RAGAS Phase 1 (500 samples)"
    )
    print(f"  ✓ Report: {report_path}")

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    print(f"Total samples: {len(final_samples)}")
    print(f"  - Answerable: {sum(1 for s in final_samples if s.answerable)}")
    print(f"  - Unanswerable: {sum(1 for s in final_samples if not s.answerable)}")
    print(f"\nOutputs:")
    print(f"  - Dataset: {args.output}")
    print(f"  - Manifest: {args.manifest}")
    print(f"  - Report: {args.report}")
    print(f"\nSHA256: {sha256}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
