#!/usr/bin/env python3
"""Setup Amnesty QA dataset for RAGAS evaluation.

Sprint 76 Feature 76.4: RAGAS Default Evaluation Set

This script:
1. Downloads Amnesty QA dataset from HuggingFace
2. Converts to RAGAS JSONL format
3. Prepares contexts for ingestion
4. Creates evaluation-ready dataset

Dataset: explodinggradients/amnesty_qa (english_v2)
Reference: https://docs.ragas.io/en/stable/getstarted/evaluation.html
"""

import json
from pathlib import Path

from datasets import load_dataset


def download_amnesty_qa(config: str = "english_v2", split: str = "eval") -> dict:
    """Download Amnesty QA dataset from HuggingFace.

    Args:
        config: Dataset configuration (default: "english_v2")
        split: Dataset split (default: "eval")

    Returns:
        Dictionary with dataset samples
    """
    print(f"\n{'=' * 80}")
    print("DOWNLOADING AMNESTY QA DATASET")
    print("=" * 80)
    print(f"Dataset: explodinggradients/amnesty_qa")
    print(f"Config: {config}")
    print(f"Split: {split}")
    print()

    dataset = load_dataset("explodinggradients/amnesty_qa", config, split=split)

    print(f"✓ Downloaded {len(dataset)} samples")
    print(f"  Columns: {dataset.column_names}")
    print()

    return dataset


def create_ragas_jsonl(dataset, output_file: str, max_samples: int = -1):
    """Convert Amnesty QA to RAGAS JSONL format.

    RAGAS format:
    - question: str
    - ground_truth: str (or ground_truths: list)
    - contexts: list[str]

    Args:
        dataset: HuggingFace dataset
        output_file: Output JSONL path
        max_samples: Max samples to include (-1 = all)
    """
    print(f"\n{'=' * 80}")
    print("CREATING RAGAS JSONL")
    print("=" * 80)
    print(f"Output: {output_file}")
    print(f"Max samples: {max_samples if max_samples > 0 else 'all'}")
    print()

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    entries = []
    total_samples = len(dataset) if max_samples < 0 else min(max_samples, len(dataset))

    for i in range(total_samples):
        sample = dataset[i]

        # RAGAS format
        entry = {
            "question": sample.get("question", ""),
            "ground_truth": sample.get("ground_truth", ""),
            "contexts": sample.get("contexts", []),
        }

        entries.append(entry)

        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{total_samples} samples...")

    # Write JSONL
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print()
    print(f"✓ Created {len(entries)} RAGAS entries")
    print(f"✓ Saved to {output_file}")
    print()

    # Show sample
    if entries:
        print("Sample entry:")
        print(f"  Question: {entries[0]['question'][:100]}...")
        print(f"  Ground Truth: {entries[0]['ground_truth'][:100]}...")
        print(f"  Contexts: {len(entries[0]['contexts'])} context(s)")
        print()

    return entries


def create_ingestion_docs(entries, output_dir: str):
    """Create text files for ingestion from contexts.

    Args:
        entries: RAGAS entries with contexts
        output_dir: Output directory for text files
    """
    print(f"\n{'=' * 80}")
    print("CREATING INGESTION DOCUMENTS")
    print("=" * 80)
    print(f"Output directory: {output_dir}")
    print()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Collect unique contexts (avoid duplicates)
    unique_contexts = set()
    for entry in entries:
        for context in entry["contexts"]:
            if context.strip():
                unique_contexts.add(context.strip())

    print(f"Found {len(unique_contexts)} unique contexts")
    print()

    # Write each context as a separate document
    for i, context in enumerate(sorted(unique_contexts)):
        doc_file = output_path / f"amnesty_context_{i:04d}.txt"
        with open(doc_file, "w", encoding="utf-8") as f:
            f.write(context)

        if (i + 1) % 50 == 0:
            print(f"  Created {i + 1}/{len(unique_contexts)} documents...")

    print()
    print(f"✓ Created {len(unique_contexts)} context documents")
    print(f"✓ Saved to {output_dir}/")
    print()


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("AMNESTY QA RAGAS SETUP - Sprint 76 Feature 76.4")
    print("=" * 80)

    # Download dataset
    dataset = download_amnesty_qa(config="english_v2", split="eval")

    # Create small and full RAGAS JSONL in /tmp first (permission workaround)
    create_ragas_jsonl(
        dataset,
        output_file="/tmp/ragas_amnesty_small.jsonl",
        max_samples=10,
    )

    create_ragas_jsonl(
        dataset,
        output_file="/tmp/ragas_amnesty_full.jsonl",
        max_samples=-1,
    )

    # Create ingestion documents from small set
    small_entries = []
    with open("/tmp/ragas_amnesty_small.jsonl") as f:
        for line in f:
            small_entries.append(json.loads(line))

    create_ingestion_docs(
        small_entries,
        output_dir="/tmp/amnesty_qa_contexts",
    )

    print("\n" + "=" * 80)
    print("SETUP COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Ingest contexts: bash scripts/upload_ragas_documents.sh amnesty_qa data/amnesty_qa_contexts")
    print("2. Run evaluation: poetry run python scripts/run_ragas_evaluation.py \\")
    print("                      --dataset data/evaluation/ragas_amnesty_small.jsonl \\")
    print("                      --namespace amnesty_qa \\")
    print("                      --mode hybrid")
    print()


if __name__ == "__main__":
    main()
