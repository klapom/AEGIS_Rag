#!/usr/bin/env python3
"""
Fetch additional questions from HuggingFace HotpotQA dataset.

This script fetches multi-hop questions from the HotpotQA dataset
and formats them for RAGAS evaluation.

Usage:
    python scripts/fetch_hotpotqa_questions.py --num-questions 10 --output data/evaluation/ragas_hotpotqa_extended.jsonl
"""

import argparse
import json
from pathlib import Path

from datasets import load_dataset


def fetch_hotpotqa_questions(
    num_questions: int = 10,
    start_index: int = 5,  # Skip first 5 already in ragas_hotpotqa_small.jsonl
    split: str = "validation",
) -> list[dict]:
    """
    Fetch questions from HotpotQA dataset.

    Args:
        num_questions: Number of questions to fetch
        start_index: Starting index (to skip existing questions)
        split: Dataset split to use ('train' or 'validation')

    Returns:
        List of formatted question dictionaries
    """
    print(f"Loading HotpotQA dataset (split={split})...")
    dataset = load_dataset("hotpot_qa", "distractor", split=split)

    questions = []

    for i in range(start_index, start_index + num_questions):
        if i >= len(dataset):
            print(f"Warning: Dataset only has {len(dataset)} examples, stopping at index {i}")
            break

        example = dataset[i]

        # Extract supporting facts - the contexts that contain the answer
        supporting_contexts = []
        for title, sentences in zip(example["context"]["title"], example["context"]["sentences"]):
            # Join sentences for this supporting document
            context_text = f"{title}\n\n" + " ".join(sentences)
            supporting_contexts.append(context_text)

        # Create question entry
        question_id = f"hotpot_{i:06d}"
        question_entry = {
            "question": example["question"],
            "ground_truth": example["answer"],
            "contexts": supporting_contexts[:3],  # Limit to 3 most relevant contexts
            "metadata": {
                "question_id": question_id,
                "source": f"{question_id}.txt",
                "text_length": sum(len(c) for c in supporting_contexts[:3]),
                "level": example.get("level", "unknown"),
                "type": example.get("type", "unknown"),
            }
        }

        questions.append(question_entry)
        print(f"  Fetched: {question_id} - {example['question'][:60]}...")

    return questions


def save_questions_jsonl(questions: list[dict], output_path: Path) -> None:
    """Save questions to JSONL format."""
    with open(output_path, "w") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"Saved {len(questions)} questions to {output_path}")


def create_context_files(questions: list[dict], output_dir: Path) -> None:
    """Create individual .txt files for each question's contexts (for ingestion)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for q in questions:
        question_id = q["metadata"]["question_id"]
        txt_path = output_dir / f"{question_id}.txt"

        # Combine contexts with separators
        content = f"# Question: {q['question']}\n\n"
        content += f"# Ground Truth: {q['ground_truth']}\n\n"
        content += "# Supporting Contexts:\n\n"

        for i, ctx in enumerate(q["contexts"], 1):
            content += f"## Context {i}\n{ctx}\n\n"

        with open(txt_path, "w") as f:
            f.write(content)

        print(f"  Created: {txt_path}")


def main():
    parser = argparse.ArgumentParser(description="Fetch HotpotQA questions for RAGAS evaluation")
    parser.add_argument("--num-questions", type=int, default=10, help="Number of questions to fetch")
    parser.add_argument("--start-index", type=int, default=5, help="Starting index (skip existing)")
    parser.add_argument("--output", type=str, default="data/evaluation/ragas_hotpotqa_extended.jsonl",
                        help="Output JSONL file path")
    parser.add_argument("--context-dir", type=str, default="data/evaluation/hotpotqa_contexts",
                        help="Directory for context .txt files")
    parser.add_argument("--split", type=str, default="validation", help="Dataset split")

    args = parser.parse_args()

    # Fetch questions
    questions = fetch_hotpotqa_questions(
        num_questions=args.num_questions,
        start_index=args.start_index,
        split=args.split,
    )

    if not questions:
        print("No questions fetched!")
        return

    # Save JSONL
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_questions_jsonl(questions, output_path)

    # Create context files for ingestion
    context_dir = Path(args.context_dir)
    create_context_files(questions, context_dir)

    print(f"\n✅ Done! Fetched {len(questions)} questions")
    print(f"   JSONL: {output_path}")
    print(f"   Contexts: {context_dir}/")


if __name__ == "__main__":
    main()
