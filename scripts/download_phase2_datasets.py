#!/usr/bin/env python3
"""Sprint 88: Download Phase 2 Structured Datasets (Tables + Code).

Downloads 300 samples:
- 150 T2-RAGBench (FinQA) - Financial table questions
- 150 MBPP - Python code generation questions

Usage:
    poetry run python scripts/download_phase2_datasets.py
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from datasets import load_dataset

logger = structlog.get_logger(__name__)

# Configuration
OUTPUT_DIR = Path("data/evaluation/phase2_samples_300")
T2RAG_SAMPLES = 150
MBPP_SAMPLES = 150


def download_t2ragbench(num_samples: int = 150) -> list[dict[str, Any]]:
    """Download T2-RAGBench (FinQA) samples with financial tables."""
    logger.info(f"Downloading {num_samples} T2-RAGBench samples...")

    try:
        # G4KMU/t2-ragbench contains FinQA financial table questions
        # Available configs: 'FinQA', 'ConvFinQA', 'VQAonBD', 'TAT-DQA'
        dataset = load_dataset("G4KMU/t2-ragbench", "FinQA", split="train")
        logger.info(f"T2-RAGBench total samples: {len(dataset)}")

        samples = []
        for i, row in enumerate(dataset):
            if i >= num_samples:
                break

            # Extract table context (markdown format)
            table_context = row.get("table", "") or ""
            question = row.get("question", "")
            answer = row.get("answer", "")

            # Create document content (table + question context)
            doc_content = f"""# Financial Document {i+1}

## Question
{question}

## Data Table
{table_context}

## Answer Reference
{answer}
"""

            samples.append({
                "id": f"t2rag_{i:04d}",
                "question": question,
                "ground_truth": str(answer),
                "context": doc_content,
                "table_raw": table_context,
                "source": "t2ragbench",
                "doc_type": "financial_table",
            })

        logger.info(f"Downloaded {len(samples)} T2-RAGBench samples")
        return samples

    except Exception as e:
        logger.error(f"Failed to download T2-RAGBench: {e}")
        return []


def download_mbpp(num_samples: int = 150) -> list[dict[str, Any]]:
    """Download MBPP (Mostly Basic Python Problems) samples."""
    logger.info(f"Downloading {num_samples} MBPP samples...")

    try:
        # google-research-datasets/mbpp contains Python coding questions
        dataset = load_dataset("google-research-datasets/mbpp", "full", split="train")
        logger.info(f"MBPP total samples: {len(dataset)}")

        samples = []
        for i, row in enumerate(dataset):
            if i >= num_samples:
                break

            task_id = row.get("task_id", i)
            prompt = row.get("text", "")  # The question/description
            code = row.get("code", "")    # The solution code
            test_list = row.get("test_list", [])

            # Create document content (code + description)
            test_cases_str = "\n".join(test_list) if test_list else "No test cases"
            doc_content = f"""# Python Programming Task {task_id}

## Problem Description
{prompt}

## Solution Code
```python
{code}
```

## Test Cases
{test_cases_str}
"""

            samples.append({
                "id": f"mbpp_{i:04d}",
                "question": prompt,
                "ground_truth": code,
                "context": doc_content,
                "code_raw": code,
                "test_cases": test_list,
                "source": "mbpp",
                "doc_type": "python_code",
            })

        logger.info(f"Downloaded {len(samples)} MBPP samples")
        return samples

    except Exception as e:
        logger.error(f"Failed to download MBPP: {e}")
        return []


def export_samples(samples: list[dict], output_dir: Path, source_name: str) -> None:
    """Export samples as .txt files and metadata JSON."""
    doc_dir = output_dir / source_name
    doc_dir.mkdir(parents=True, exist_ok=True)

    # Export individual documents
    for sample in samples:
        doc_path = doc_dir / f"{sample['id']}.txt"
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(sample["context"])

    # Export metadata (questions + answers for RAGAS)
    metadata = {
        "source": source_name,
        "count": len(samples),
        "samples": [
            {
                "id": s["id"],
                "question": s["question"],
                "answer": s["ground_truth"],
                "doc_type": s["doc_type"],
            }
            for s in samples
        ],
    }

    meta_path = doc_dir / f"{source_name}_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(f"Exported {len(samples)} {source_name} samples to {doc_dir}")


def export_ragas_jsonl(all_samples: list[dict], output_dir: Path) -> None:
    """Export combined RAGAS evaluation JSONL file."""
    jsonl_path = output_dir / "phase2_ragas_300.jsonl"

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for sample in all_samples:
            ragas_entry = {
                "id": sample["id"],
                "question": sample["question"],
                "ground_truth": sample["ground_truth"],
                "contexts": [],  # Will be filled during retrieval
                "doc_type": sample["doc_type"],
                "source_dataset": sample["source"],
            }
            f.write(json.dumps(ragas_entry, ensure_ascii=False) + "\n")

    logger.info(f"Exported RAGAS JSONL to {jsonl_path}")


def main():
    """Main download and export flow."""
    print("\n" + "=" * 60)
    print("SPRINT 88: Phase 2 Dataset Download (300 Samples)")
    print("=" * 60 + "\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Download T2-RAGBench
    print("📊 Downloading T2-RAGBench (Financial Tables)...")
    t2rag_samples = download_t2ragbench(T2RAG_SAMPLES)
    if t2rag_samples:
        export_samples(t2rag_samples, OUTPUT_DIR, "t2ragbench")

    # Download MBPP
    print("\n💻 Downloading MBPP (Python Code)...")
    mbpp_samples = download_mbpp(MBPP_SAMPLES)
    if mbpp_samples:
        export_samples(mbpp_samples, OUTPUT_DIR, "mbpp")

    # Combine and export RAGAS JSONL
    all_samples = t2rag_samples + mbpp_samples
    if all_samples:
        export_ragas_jsonl(all_samples, OUTPUT_DIR)

    # Summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"📊 T2-RAGBench (Tables): {len(t2rag_samples)} samples")
    print(f"💻 MBPP (Code):          {len(mbpp_samples)} samples")
    print(f"📁 Output Directory:     {OUTPUT_DIR}")
    print(f"📝 Total Samples:        {len(all_samples)}")

    return 0 if all_samples else 1


if __name__ == "__main__":
    sys.exit(main())
