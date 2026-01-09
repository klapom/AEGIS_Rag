#!/usr/bin/env python3
"""
Prepare RAGAS Phase 1 dataset for ingestion via Frontend API.

This script:
1. Reads the Phase 1 JSONL (500 samples)
2. Exports contexts as .txt files (for upload via Frontend API)
3. Creates a questions-only JSONL (for RAGAS evaluation after ingestion)

Sprint 82: Phase 1 - Text-Only Benchmark
ADR Reference: ADR-048

Usage:
    poetry run python scripts/ragas_benchmark/prepare_phase1_ingestion.py
    poetry run python scripts/ragas_benchmark/prepare_phase1_ingestion.py --max-samples 10  # Test with 10
"""

import argparse
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def prepare_ingestion(
    input_jsonl: str = "data/evaluation/ragas_phase1_500.jsonl",
    output_dir: str = "data/ragas_phase1_contexts",
    questions_output: str = "data/evaluation/ragas_phase1_questions.jsonl",
    namespace: str = "ragas_phase1",
    max_samples: int = -1,
):
    """
    Prepare Phase 1 dataset for Frontend API ingestion.

    Args:
        input_jsonl: Path to Phase 1 JSONL with samples
        output_dir: Directory for .txt context files
        questions_output: Path for questions-only JSONL
        namespace: Target namespace for ingestion
        max_samples: Max samples to process (-1 for all)
    """
    input_path = Path(input_jsonl)
    output_path = Path(output_dir)
    questions_path = Path(questions_output)

    if not input_path.exists():
        logger.error(f"Input file not found: {input_jsonl}")
        return

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("RAGAS Phase 1 Ingestion Preparation")
    print("=" * 60)
    print(f"Input: {input_jsonl}")
    print(f"Context output: {output_dir}/")
    print(f"Questions output: {questions_output}")
    print(f"Target namespace: {namespace}")
    print("=" * 60)

    # Load samples
    samples = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    if max_samples > 0:
        samples = samples[:max_samples]

    logger.info(f"Processing {len(samples)} samples")

    # Prepare context files and questions
    questions_data = []
    answerable_count = 0
    unanswerable_count = 0
    total_context_chars = 0

    for i, sample in enumerate(samples):
        sample_id = sample['id']
        question = sample['question']
        ground_truth = sample['ground_truth']
        contexts = sample['contexts']
        answerable = sample.get('answerable', True)
        doc_type = sample.get('doc_type', 'clean_text')
        question_type = sample.get('question_type', 'lookup')
        difficulty = sample.get('difficulty', 'D1')

        # Track stats
        if answerable:
            answerable_count += 1
        else:
            unanswerable_count += 1

        # Combine contexts into single document
        combined_text = f"# Document: {sample_id}\n\n"
        combined_text += f"Source: RAGAS Phase 1 Benchmark\n"
        combined_text += f"Doc Type: {doc_type}\n"
        combined_text += f"Difficulty: {difficulty}\n\n"
        combined_text += "---\n\n"

        for j, ctx in enumerate(contexts, 1):
            combined_text += f"## Context {j}\n\n"
            combined_text += ctx.strip()
            combined_text += "\n\n"

        total_context_chars += len(combined_text)

        # Generate unique filename
        filename = f"{sample_id}.txt"
        filepath = output_path / filename

        # Write context file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(combined_text)

        # Prepare question entry for RAGAS evaluation
        question_entry = {
            "id": sample_id,
            "question": question,
            "ground_truth": ground_truth,
            "answerable": answerable,
            "doc_type": doc_type,
            "question_type": question_type,
            "difficulty": difficulty,
            "source_document": filename,
            "namespace": namespace,
            "metadata": sample.get('metadata', {})
        }
        questions_data.append(question_entry)

        if (i + 1) % 50 == 0:
            logger.info(f"  Processed {i + 1}/{len(samples)} samples")

    # Write questions JSONL
    questions_path.parent.mkdir(parents=True, exist_ok=True)
    with open(questions_path, 'w', encoding='utf-8') as f:
        for entry in questions_data:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    # Summary
    print("\n" + "=" * 60)
    print("PREPARATION COMPLETE")
    print("=" * 60)
    print(f"Context files created: {len(samples)}")
    print(f"  Location: {output_dir}/")
    print(f"  Total size: {total_context_chars / 1024:.1f} KB")
    print(f"\nQuestions JSONL created: {questions_path}")
    print(f"  Answerable: {answerable_count}")
    print(f"  Unanswerable: {unanswerable_count}")
    print(f"\nTarget namespace: {namespace}")
    print("=" * 60)

    # Generate upload commands
    print("\n### NEXT STEPS ###")
    print(f"""
1. Upload contexts via Frontend API:

   ./scripts/upload_ragas_phase1.sh

   Or manually:

   for file in {output_dir}/*.txt; do
       curl -X POST "http://localhost:8000/api/v1/retrieval/upload" \\
           -H "Authorization: Bearer $TOKEN" \\
           -F "file=@$file" \\
           -F "namespace_id={namespace}"
   done

2. Run RAGAS evaluation:

   poetry run python scripts/run_ragas_evaluation.py \\
       --dataset {questions_output} \\
       --namespace {namespace} \\
       --mode hybrid \\
       --output-dir data/evaluation/results/phase1/
""")

    return len(samples)


def main():
    parser = argparse.ArgumentParser(
        description="Prepare RAGAS Phase 1 dataset for Frontend API ingestion"
    )
    parser.add_argument(
        "--input",
        default="data/evaluation/ragas_phase1_500.jsonl",
        help="Path to Phase 1 JSONL"
    )
    parser.add_argument(
        "--output-dir",
        default="data/ragas_phase1_contexts",
        help="Directory for .txt context files"
    )
    parser.add_argument(
        "--questions-output",
        default="data/evaluation/ragas_phase1_questions.jsonl",
        help="Path for questions-only JSONL"
    )
    parser.add_argument(
        "--namespace",
        default="ragas_phase1",
        help="Target namespace for ingestion"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=-1,
        help="Max samples to process (-1 for all)"
    )

    args = parser.parse_args()

    prepare_ingestion(
        input_jsonl=args.input,
        output_dir=args.output_dir,
        questions_output=args.questions_output,
        namespace=args.namespace,
        max_samples=args.max_samples,
    )


if __name__ == "__main__":
    main()
