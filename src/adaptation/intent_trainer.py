"""SetFit Model Training for Intent Classification.

Sprint 67 Feature 67.11: Train SetFit model on C-LARA generated synthetic data
to improve intent classification accuracy from 60% (Semantic Router) to 85-92%.

Architecture:
    Synthetic Data (Feature 67.10) → SetFit Training → Fine-Tuned Model → Production

Training Pipeline:
    1. Load JSONL training data from intent_data_generator.py
    2. Convert to HuggingFace Dataset format
    3. Train/validation split (80/20)
    4. Fine-tune SetFit model with contrastive learning
    5. Evaluate on validation set
    6. Export model to models/intent_classifier_v1/

Model Architecture:
    - Base: sentence-transformers/paraphrase-mpnet-base-v2 (768-dim)
    - Head: Logistic Regression classifier (5 classes)
    - Training: Contrastive learning with in-batch negatives
    - Loss: CosineSimilarityLoss

Performance Targets (TD-079):
    - Validation Accuracy: ≥85%
    - Training Time: <10 minutes on DGX Spark
    - Inference Latency: P95 ≤100ms
    - Model Size: <500MB

References:
    - TD-079: LLM Intent Classifier (C-LARA)
    - SetFit Paper: https://arxiv.org/abs/2209.11055
    - C-LARA Framework: https://www.amazon.science/publications/intent-detection-in-the-age-of-llms
"""

import json
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
from datasets import Dataset, DatasetDict
from setfit import SetFitModel, Trainer, TrainingArguments
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

logger = structlog.get_logger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for SetFit intent classifier training.

    Attributes:
        base_model: Sentence-transformer model to use as base encoder
        num_epochs: Number of training epochs
        batch_size: Training batch size
        learning_rate: Learning rate for classifier head
        output_dir: Directory to save trained model
        val_split: Validation set split ratio (0.0-1.0)
        max_iter: Maximum iterations for logistic regression
        device: Device to train on ("cuda" or "cpu")
    """

    base_model: str = "sentence-transformers/paraphrase-mpnet-base-v2"
    num_epochs: int = 3
    batch_size: int = 16
    learning_rate: float = 2e-5
    output_dir: str = "models/intent_classifier_v1"
    val_split: float = 0.2
    max_iter: int = 100
    device: str = "cuda"


class IntentTrainer:
    """Train SetFit model for intent classification.

    Sprint 67 Feature 67.11: Fine-tune SetFit on synthetic C-LARA data
    to improve intent classification from 60% to 85-92% accuracy.

    Example:
        trainer = IntentTrainer(config=TrainingConfig())
        model, metrics = await trainer.train(
            train_data_path="data/intent_training_v1.jsonl"
        )
        print(f"Validation Accuracy: {metrics['accuracy']:.2%}")
    """

    # Intent label mapping (consistent with intent_classifier.py)
    INTENT_LABELS = {
        "factual": 0,
        "procedural": 1,
        "comparison": 2,
        "recommendation": 3,
        "navigation": 4,
    }

    LABEL_TO_INTENT = {v: k for k, v in INTENT_LABELS.items()}

    def __init__(self, config: TrainingConfig | None = None):
        """Initialize intent trainer.

        Args:
            config: Training configuration (uses defaults if None)
        """
        self.config = config or TrainingConfig()
        self.logger = logger.bind(
            base_model=self.config.base_model,
            output_dir=self.config.output_dir,
        )

        self.logger.info(
            "intent_trainer_initialized",
            config={
                "base_model": self.config.base_model,
                "num_epochs": self.config.num_epochs,
                "batch_size": self.config.batch_size,
                "learning_rate": self.config.learning_rate,
                "val_split": self.config.val_split,
            },
        )

    def _load_training_data(self, path: str | Path) -> list[dict[str, Any]]:
        """Load JSONL training data from intent_data_generator.

        Args:
            path: Path to JSONL file with format:
                {"query": "...", "intent": "factual", "confidence": 0.95, ...}

        Returns:
            List of training examples

        Raises:
            FileNotFoundError: If training data file doesn't exist
            ValueError: If JSONL parsing fails
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Training data not found: {path}")

        examples = []
        with path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    example = json.loads(line.strip())
                    examples.append(example)
                except json.JSONDecodeError as e:
                    self.logger.warning(
                        "jsonl_parse_error",
                        line_num=line_num,
                        error=str(e),
                        line_preview=line[:100],
                    )
                    continue

        self.logger.info(
            "training_data_loaded",
            path=str(path),
            examples_count=len(examples),
        )

        return examples

    def _convert_to_dataset(self, examples: list[dict[str, Any]]) -> Dataset:
        """Convert training examples to HuggingFace Dataset.

        Args:
            examples: List of dicts with "query" and "intent" keys

        Returns:
            HuggingFace Dataset with "text" and "label" columns

        Raises:
            ValueError: If intent label is unknown
        """
        from datasets import ClassLabel, Features, Value

        dataset_dict = {"text": [], "label": []}

        for example in examples:
            query = example.get("query", "").strip()
            intent = example.get("intent", "").lower()

            if not query or intent not in self.INTENT_LABELS:
                self.logger.warning(
                    "invalid_example_skipped",
                    query=query[:50] if query else None,
                    intent=intent,
                )
                continue

            dataset_dict["text"].append(query)
            dataset_dict["label"].append(self.INTENT_LABELS[intent])

        # Define features with ClassLabel for stratification support
        features = Features(
            {
                "text": Value("string"),
                "label": ClassLabel(
                    names=list(self.INTENT_LABELS.keys())
                ),
            }
        )

        dataset = Dataset.from_dict(dataset_dict, features=features)

        self.logger.info(
            "dataset_converted",
            total_examples=len(dataset),
            label_distribution=dict(Counter(dataset["label"])),
        )

        return dataset

    def _split_dataset(self, dataset: Dataset) -> DatasetDict:
        """Split dataset into train and validation sets.

        Args:
            dataset: Full dataset to split

        Returns:
            DatasetDict with "train" and "test" splits

        Strategy:
            - Stratified split to maintain class balance
            - Validation split ratio from config.val_split
        """
        split_dataset = dataset.train_test_split(
            test_size=self.config.val_split,
            stratify_by_column="label",
            seed=42,  # Fixed seed for reproducibility
        )

        self.logger.info(
            "dataset_split",
            train_size=len(split_dataset["train"]),
            val_size=len(split_dataset["test"]),
            val_split=self.config.val_split,
        )

        return split_dataset

    def train(
        self,
        train_data_path: str = "data/intent_training_v1.jsonl",
        checkpoint_path: str | None = None,
    ) -> tuple[SetFitModel, dict[str, Any]]:
        """Train SetFit model on labeled intent data.

        Args:
            train_data_path: Path to JSONL training data
            checkpoint_path: Optional path to resume from checkpoint

        Returns:
            Tuple of (trained_model, evaluation_metrics)

        Raises:
            FileNotFoundError: If training data doesn't exist
            RuntimeError: If training fails

        Training Steps:
            1. Load and validate training data
            2. Convert to HuggingFace Dataset format
            3. Train/validation split (stratified)
            4. Initialize SetFit model (or load checkpoint)
            5. Configure trainer with contrastive learning
            6. Train model
            7. Evaluate on validation set
            8. Save model to output_dir

        Performance:
            - Expected training time: 5-10 minutes on DGX Spark
            - Target validation accuracy: ≥85%
            - Model size: ~420MB (MPNet base)
        """
        start_time = time.perf_counter()

        self.logger.info(
            "training_started",
            train_data_path=train_data_path,
            checkpoint_path=checkpoint_path,
        )

        # 1. Load training data
        examples = self._load_training_data(train_data_path)

        if len(examples) < 100:
            raise ValueError(
                f"Insufficient training data: {len(examples)} examples "
                "(minimum 100 required for robust training)"
            )

        # 2. Convert to Dataset
        dataset = self._convert_to_dataset(examples)

        # 3. Train/val split
        split_dataset = self._split_dataset(dataset)

        # 4. Initialize SetFit model
        if checkpoint_path and Path(checkpoint_path).exists():
            self.logger.info("loading_checkpoint", checkpoint_path=checkpoint_path)
            model = SetFitModel.from_pretrained(checkpoint_path)
        else:
            self.logger.info("initializing_base_model", base_model=self.config.base_model)
            model = SetFitModel.from_pretrained(
                self.config.base_model,
                labels=[self.LABEL_TO_INTENT[i] for i in range(len(self.INTENT_LABELS))],
            )

        # 5. Configure training arguments
        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            num_epochs=self.config.num_epochs,
            batch_size=self.config.batch_size,
            body_learning_rate=self.config.learning_rate,  # SetFit uses body_learning_rate
            head_learning_rate=0.01,  # Default head learning rate
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="accuracy",
        )

        # 6. Create trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=split_dataset["train"],
            eval_dataset=split_dataset["test"],
            metric="accuracy",
        )

        # 7. Train
        self.logger.info(
            "training_in_progress",
            train_size=len(split_dataset["train"]),
            val_size=len(split_dataset["test"]),
            epochs=self.config.num_epochs,
        )

        trainer.train()

        training_time_sec = time.perf_counter() - start_time

        # 8. Evaluate on validation set
        self.logger.info("evaluating_model")
        metrics = self._evaluate(model, split_dataset["test"])

        metrics["training_time_sec"] = round(training_time_sec, 2)
        metrics["training_time_min"] = round(training_time_sec / 60, 2)

        self.logger.info(
            "training_complete",
            accuracy=metrics["accuracy"],
            training_time_min=metrics["training_time_min"],
            output_dir=self.config.output_dir,
        )

        # 9. Save model
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(output_path))

        self.logger.info(
            "model_saved",
            output_path=str(output_path),
            model_size_mb=self._get_model_size_mb(output_path),
        )

        return model, metrics

    def _evaluate(self, model: SetFitModel, eval_dataset: Dataset) -> dict[str, Any]:
        """Evaluate model on validation set.

        Args:
            model: Trained SetFit model
            eval_dataset: Validation dataset

        Returns:
            Evaluation metrics including:
                - accuracy: Overall accuracy (0.0-1.0)
                - precision: Per-class precision
                - recall: Per-class recall
                - f1: Per-class F1 score
                - confusion_matrix: Confusion matrix
                - classification_report: Detailed report

        Quality Gates:
            - Accuracy ≥0.85 (target from TD-079)
            - No class with F1 <0.80
        """
        # Get predictions
        predictions = model.predict(eval_dataset["text"])
        true_labels = eval_dataset["label"]

        # Calculate metrics
        accuracy = accuracy_score(true_labels, predictions)

        # Classification report
        report = classification_report(
            true_labels,
            predictions,
            target_names=[self.LABEL_TO_INTENT[i] for i in range(len(self.INTENT_LABELS))],
            output_dict=True,
            zero_division=0,
        )

        # Confusion matrix
        cm = confusion_matrix(
            true_labels,
            predictions,
            labels=list(range(len(self.INTENT_LABELS))),
        )

        metrics = {
            "accuracy": round(accuracy, 4),
            "classification_report": report,
            "confusion_matrix": cm.tolist(),
            "per_class_f1": {
                intent: round(report.get(intent, {}).get("f1-score", 0.0), 4)
                for intent in self.INTENT_LABELS
            },
        }

        # Quality gate checks
        quality_issues = []
        if accuracy < 0.85:
            quality_issues.append(f"Accuracy {accuracy:.2%} below target (≥85%)")

        for intent, f1 in metrics["per_class_f1"].items():
            if f1 < 0.80:
                quality_issues.append(f"Class '{intent}' F1 {f1:.2%} below threshold (≥80%)")

        if quality_issues:
            self.logger.warning(
                "quality_gates_failed",
                issues=quality_issues,
            )
            metrics["quality_gates_passed"] = False
        else:
            self.logger.info("quality_gates_passed")
            metrics["quality_gates_passed"] = True

        metrics["quality_issues"] = quality_issues

        return metrics

    def _get_model_size_mb(self, model_path: Path) -> float:
        """Calculate total model size in MB.

        Args:
            model_path: Path to model directory

        Returns:
            Total size in megabytes
        """
        total_size = sum(
            f.stat().st_size for f in model_path.rglob("*") if f.is_file()
        )
        return round(total_size / (1024 * 1024), 2)


def main() -> None:
    """CLI entry point for training intent classifier."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Train SetFit intent classifier on C-LARA synthetic data"
    )
    parser.add_argument(
        "--data",
        default="data/intent_training_v1.jsonl",
        help="Path to JSONL training data",
    )
    parser.add_argument(
        "--base-model",
        default="sentence-transformers/paraphrase-mpnet-base-v2",
        help="Base sentence-transformer model",
    )
    parser.add_argument(
        "--output",
        default="models/intent_classifier_v1",
        help="Output directory for trained model",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Training batch size",
    )
    parser.add_argument(
        "--val-split",
        type=float,
        default=0.2,
        help="Validation set split ratio",
    )
    parser.add_argument(
        "--checkpoint",
        help="Resume from checkpoint path",
    )

    args = parser.parse_args()

    # Configure training
    config = TrainingConfig(
        base_model=args.base_model,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        output_dir=args.output,
        val_split=args.val_split,
    )

    # Train model
    trainer = IntentTrainer(config=config)
    model, metrics = trainer.train(
        train_data_path=args.data,
        checkpoint_path=args.checkpoint,
    )

    # Print results
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Validation Accuracy: {metrics['accuracy']:.2%}")
    print(f"Training Time: {metrics['training_time_min']:.2f} minutes")
    print(f"Model Saved: {args.output}")
    print("\nPer-Class F1 Scores:")
    for intent, f1 in metrics["per_class_f1"].items():
        status = "✓" if f1 >= 0.80 else "✗"
        print(f"  {status} {intent:15s}: {f1:.2%}")

    if metrics["quality_gates_passed"]:
        print("\n✓ All quality gates passed!")
    else:
        print("\n✗ Quality gate failures:")
        for issue in metrics["quality_issues"]:
            print(f"  - {issue}")

    print("=" * 60)


if __name__ == "__main__":
    main()
