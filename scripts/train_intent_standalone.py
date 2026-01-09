#!/usr/bin/env python3
"""Standalone SetFit intent classifier training script for NGC container.

Sprint 81: Runs without full AegisRAG dependencies for GPU training in NGC container.

Usage (in NGC container):
    python scripts/train_intent_standalone.py \
        --data data/intent_training_multi_teacher_v1.jsonl \
        --output models/intent_classifier
"""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from datasets import ClassLabel, Dataset, Features, Value
from setfit import SetFitModel, Trainer, TrainingArguments
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


# Intent label mapping
INTENT_LABELS = {
    "factual": 0,
    "procedural": 1,
    "comparison": 2,
    "recommendation": 3,
    "navigation": 4,
}
LABEL_TO_INTENT = {v: k for k, v in INTENT_LABELS.items()}


def load_training_data(path: str) -> list[dict]:
    """Load JSONL training data."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Training data not found: {path}")

    examples = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                example = json.loads(line.strip())
                examples.append(example)
            except json.JSONDecodeError:
                continue

    print(f"Loaded {len(examples)} examples from {path}")
    return examples


def convert_to_dataset(examples: list[dict]) -> Dataset:
    """Convert to HuggingFace Dataset."""
    dataset_dict = {"text": [], "label": []}

    for example in examples:
        query = example.get("query", "").strip()
        intent = example.get("intent", "").lower()

        if not query or intent not in INTENT_LABELS:
            continue

        dataset_dict["text"].append(query)
        dataset_dict["label"].append(INTENT_LABELS[intent])

    features = Features({
        "text": Value("string"),
        "label": ClassLabel(names=list(INTENT_LABELS.keys())),
    })

    dataset = Dataset.from_dict(dataset_dict, features=features)
    print(f"Dataset: {len(dataset)} examples")
    print(f"Label distribution: {dict(Counter(dataset['label']))}")
    return dataset


def train(
    data_path: str,
    output_dir: str,
    base_model: str = "sentence-transformers/paraphrase-mpnet-base-v2",
    num_epochs: int = 1,
    batch_size: int = 32,
    val_split: float = 0.2,
):
    """Train SetFit model."""
    start_time = time.perf_counter()

    # Load and convert data
    examples = load_training_data(data_path)
    dataset = convert_to_dataset(examples)

    # Split
    split_dataset = dataset.train_test_split(
        test_size=val_split,
        stratify_by_column="label",
        seed=42,
    )
    print(f"Train: {len(split_dataset['train'])}, Val: {len(split_dataset['test'])}")

    # Initialize model
    print(f"Initializing model: {base_model}")
    model = SetFitModel.from_pretrained(
        base_model,
        labels=[LABEL_TO_INTENT[i] for i in range(len(INTENT_LABELS))],
    )

    # Training arguments (simplified - no checkpoint saving during training)
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_epochs=num_epochs,
        batch_size=batch_size,
        body_learning_rate=2e-5,
        head_learning_rate=0.01,
        eval_strategy="no",  # Disable eval during training
        save_strategy="no",  # Save manually after training
    )

    # Trainer (no eval during training - we evaluate manually after)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=split_dataset["train"],
    )

    # Train
    print(f"\nTraining for {num_epochs} epoch(s)...")
    trainer.train()

    training_time = time.perf_counter() - start_time

    # Evaluate
    print("\nEvaluating...")
    predictions = model.predict(split_dataset["test"]["text"])
    true_labels = split_dataset["test"]["label"]

    # Convert predictions to int if they are strings (SetFit returns label names)
    if isinstance(predictions[0], str):
        predictions = [INTENT_LABELS[p] for p in predictions]

    accuracy = accuracy_score(true_labels, predictions)

    report = classification_report(
        true_labels,
        predictions,
        target_names=[LABEL_TO_INTENT[i] for i in range(len(INTENT_LABELS))],
        output_dict=True,
        zero_division=0,
    )

    # Save model
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_path))

    # Print results
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Validation Accuracy: {accuracy:.2%}")
    print(f"Training Time: {training_time / 60:.2f} minutes")
    print(f"Model Saved: {output_dir}")
    print("\nPer-Class F1 Scores:")
    for intent in INTENT_LABELS:
        f1 = report.get(intent, {}).get("f1-score", 0.0)
        status = "✓" if f1 >= 0.80 else "✗"
        print(f"  {status} {intent:15s}: {f1:.2%}")

    if accuracy >= 0.85:
        print("\n✓ Target accuracy (≥85%) achieved!")
    else:
        print(f"\n✗ Target accuracy (≥85%) not reached: {accuracy:.2%}")

    print("=" * 60)

    return accuracy


def main():
    parser = argparse.ArgumentParser(description="Train SetFit intent classifier")
    parser.add_argument("--data", required=True, help="Training data JSONL path")
    parser.add_argument("--output", default="models/intent_classifier", help="Output dir")
    parser.add_argument("--base-model", default="sentence-transformers/paraphrase-mpnet-base-v2")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--val-split", type=float, default=0.2)

    args = parser.parse_args()

    train(
        data_path=args.data,
        output_dir=args.output,
        base_model=args.base_model,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        val_split=args.val_split,
    )


if __name__ == "__main__":
    main()
