#!/usr/bin/env python3
"""Create RAGAS evaluation JSONL from meta.json files.

Sprint 77+: Generate RAGAS evaluation dataset from ingested HotpotQA files.

This script:
1. Scans ragas_eval_txt and ragas_eval_txt_large directories
2. Reads meta.json files (contain questions and ground_truth)
3. Reads corresponding .txt files (contain context)
4. Creates JSONL in RAGAS format for evaluation

Output Format:
{
    "question": "Which magazine was started first Arthur's Magazine or First for Women?",
    "ground_truth": "Arthur's Magazine",
    "contexts": ["Arthur's Magazine (1844–1846) was...", "First for Women is a..."]
}
"""

import json
from pathlib import Path
from typing import Any


def create_ragas_jsonl(
    source_dirs: list[str],
    output_file: str,
) -> None:
    """Create RAGAS JSONL from meta.json files.

    Args:
        source_dirs: List of directories containing meta.json files
        output_file: Path to output JSONL file
    """
    print("=" * 80)
    print("RAGAS JSONL GENERATOR")
    print("=" * 80)

    all_entries = []

    for source_dir in source_dirs:
        source_path = Path(source_dir)
        if not source_path.exists():
            print(f"⚠️  Directory not found: {source_dir}")
            continue

        print(f"\nScanning: {source_dir}")

        # Find all meta.json files
        meta_files = sorted(source_path.glob("*_meta.json"))
        print(f"Found {len(meta_files)} meta.json files")

        for meta_file in meta_files:
            # Read meta.json
            with open(meta_file) as f:
                meta = json.load(f)

            # Get corresponding .txt file
            txt_file = meta_file.parent / meta_file.name.replace("_meta.json", ".txt")

            if not txt_file.exists():
                print(f"  ⚠️  Missing .txt file: {txt_file.name}")
                continue

            # Read context from .txt file
            with open(txt_file) as f:
                context_text = f.read().strip()

            # Split context by double newlines (paragraph boundaries)
            # This matches how the original RAGAS datasets structure contexts
            contexts = [ctx.strip() for ctx in context_text.split("\n\n") if ctx.strip()]

            # If no paragraph breaks, use the whole text as one context
            if not contexts:
                contexts = [context_text]

            # Create RAGAS entry
            entry = {
                "question": meta["question"],
                "ground_truth": meta["ground_truth"],
                "contexts": contexts,
            }

            all_entries.append(entry)
            print(f"  ✓ {meta_file.name}: {meta['question'][:60]}...")

    # Write JSONL
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for entry in all_entries:
            f.write(json.dumps(entry) + "\n")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total entries: {len(all_entries)}")
    print(f"Output file: {output_file}")
    print(f"✓ RAGAS JSONL created successfully!")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create RAGAS JSONL from meta.json files"
    )
    parser.add_argument(
        "--output",
        default="data/evaluation/ragas_hotpot_dataset.jsonl",
        help="Output JSONL file (default: data/evaluation/ragas_hotpot_dataset.jsonl)",
    )
    parser.add_argument(
        "--include-large",
        action="store_true",
        help="Include ragas_eval_txt_large dataset (default: only ragas_eval_txt)",
    )

    args = parser.parse_args()

    # Default: small dataset only
    source_dirs = ["data/ragas_eval_txt"]

    # Add large dataset if requested
    if args.include_large:
        source_dirs.append("data/ragas_eval_txt_large")

    create_ragas_jsonl(
        source_dirs=source_dirs,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()
