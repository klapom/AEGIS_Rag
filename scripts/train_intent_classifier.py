#!/usr/bin/env python3
"""Training Script for SetFit Intent Classifier.

Sprint 67 Feature 67.11: Train SetFit model on C-LARA synthetic data.

Usage:
    # Basic training (default settings)
    python scripts/train_intent_classifier.py

    # Custom data and model
    python scripts/train_intent_classifier.py \
        --data data/intent_training_v1.jsonl \
        --base-model sentence-transformers/paraphrase-mpnet-base-v2 \
        --output models/intent_classifier_v1

    # Resume from checkpoint
    python scripts/train_intent_classifier.py \
        --checkpoint models/intent_classifier_v1_checkpoint

    # Full configuration
    python scripts/train_intent_classifier.py \
        --data data/intent_training_v1.jsonl \
        --base-model sentence-transformers/paraphrase-mpnet-base-v2 \
        --output models/intent_classifier_v1 \
        --epochs 3 \
        --batch-size 16 \
        --val-split 0.2

Expected Output:
    - Trained model in models/intent_classifier_v1/
    - Validation accuracy ≥85%
    - Training time <10 minutes on DGX Spark
    - Model size ~420MB

Quality Gates:
    - Overall accuracy ≥85%
    - Per-class F1 ≥80%
    - No critical quality issues

References:
    - TD-079: LLM Intent Classifier (C-LARA)
    - Sprint 67 Plan: Feature 67.11
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adaptation.intent_trainer import IntentTrainer, TrainingConfig


def main() -> None:
    """Train SetFit intent classifier."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Train SetFit intent classifier on C-LARA synthetic data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic training
  python scripts/train_intent_classifier.py

  # Custom configuration
  python scripts/train_intent_classifier.py --epochs 5 --batch-size 32

  # Resume training
  python scripts/train_intent_classifier.py --checkpoint models/checkpoint
        """,
    )

    parser.add_argument(
        "--data",
        default="data/intent_training_v1.jsonl",
        help="Path to JSONL training data (default: data/intent_training_v1.jsonl)",
    )

    parser.add_argument(
        "--base-model",
        default="sentence-transformers/paraphrase-mpnet-base-v2",
        help="Base sentence-transformer model (default: paraphrase-mpnet-base-v2)",
    )

    parser.add_argument(
        "--output",
        default="models/intent_classifier_v1",
        help="Output directory for trained model (default: models/intent_classifier_v1)",
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs (default: 3)",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Training batch size (default: 16)",
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-5,
        help="Learning rate for classifier head (default: 2e-5)",
    )

    parser.add_argument(
        "--val-split",
        type=float,
        default=0.2,
        help="Validation set split ratio (default: 0.2)",
    )

    parser.add_argument(
        "--checkpoint",
        help="Resume from checkpoint path",
    )

    parser.add_argument(
        "--device",
        choices=["cuda", "cpu"],
        default="cuda",
        help="Device to train on (default: cuda)",
    )

    args = parser.parse_args()

    # Validate data file exists
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"ERROR: Training data not found: {data_path}")
        print("\nPlease run data generation first:")
        print("  python scripts/generate_intent_training_data.py")
        sys.exit(1)

    # Create training configuration
    config = TrainingConfig(
        base_model=args.base_model,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        output_dir=args.output,
        val_split=args.val_split,
        device=args.device,
    )

    # Display configuration
    print("=" * 80)
    print("SETFIT INTENT CLASSIFIER TRAINING")
    print("=" * 80)
    print(f"Training Data:     {args.data}")
    print(f"Base Model:        {args.base_model}")
    print(f"Output Directory:  {args.output}")
    print(f"Epochs:            {args.epochs}")
    print(f"Batch Size:        {args.batch_size}")
    print(f"Learning Rate:     {args.learning_rate}")
    print(f"Validation Split:  {args.val_split:.1%}")
    print(f"Device:            {args.device}")
    if args.checkpoint:
        print(f"Checkpoint:        {args.checkpoint}")
    print("=" * 80)
    print()

    # Train model
    trainer = IntentTrainer(config=config)

    try:
        model, metrics = trainer.train(
            train_data_path=args.data,
            checkpoint_path=args.checkpoint,
        )
    except Exception as e:
        print(f"\nERROR: Training failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Display results
    print("\n" + "=" * 80)
    print("TRAINING COMPLETE")
    print("=" * 80)
    print(f"Validation Accuracy: {metrics['accuracy']:.2%}")
    print(f"Training Time:       {metrics['training_time_min']:.2f} minutes")
    print(f"Model Saved:         {args.output}")

    print("\nPer-Class F1 Scores:")
    for intent, f1 in metrics["per_class_f1"].items():
        status = "✓" if f1 >= 0.80 else "✗"
        print(f"  {status} {intent:15s}: {f1:.2%}")

    # Quality gates
    print("\nQuality Gates:")
    if metrics["quality_gates_passed"]:
        print("  ✓ All quality gates passed!")
    else:
        print("  ✗ Quality gate failures:")
        for issue in metrics["quality_issues"]:
            print(f"    - {issue}")

    # Recommendations
    print("\nNext Steps:")
    if metrics["quality_gates_passed"]:
        print(
            f"  1. Test model: python scripts/validate_intent_model.py --model {args.output}"
        )
        print(
            "  2. Integrate: Update src/components/retrieval/intent_classifier.py (Feature 67.12)"
        )
    else:
        print("  1. Review training data quality")
        print("  2. Increase training epochs (--epochs 5)")
        print("  3. Try different base model")
        print("  4. Generate more training examples")

    print("=" * 80)

    # Exit with appropriate code
    sys.exit(0 if metrics["quality_gates_passed"] else 1)


if __name__ == "__main__":
    main()
