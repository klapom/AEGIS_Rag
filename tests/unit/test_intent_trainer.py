"""Unit tests for IntentTrainer.

Sprint 67 Feature 67.11: Test SetFit model training for intent classification.

Test Coverage:
    - Training data loading (valid/invalid JSONL)
    - Dataset conversion (intent labels, validation)
    - Train/validation split (stratification)
    - Model training (success/failure paths)
    - Evaluation metrics (accuracy, F1, quality gates)
    - Model persistence (save/load)

Quality Gates:
    - Coverage: >80%
    - All edge cases handled
    - Proper error handling
    - Mock external dependencies (SetFit, HuggingFace)
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from datasets import Dataset

from src.adaptation.intent_trainer import IntentTrainer, TrainingConfig


class TestTrainingConfig:
    """Test TrainingConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = TrainingConfig()

        assert config.base_model == "sentence-transformers/paraphrase-mpnet-base-v2"
        assert config.num_epochs == 3
        assert config.batch_size == 16
        assert config.learning_rate == 2e-5
        assert config.output_dir == "models/intent_classifier_v1"
        assert config.val_split == 0.2
        assert config.max_iter == 100
        assert config.device == "cuda"

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = TrainingConfig(
            base_model="custom-model",
            num_epochs=5,
            batch_size=32,
            output_dir="custom/path",
        )

        assert config.base_model == "custom-model"
        assert config.num_epochs == 5
        assert config.batch_size == 32
        assert config.output_dir == "custom/path"


class TestIntentTrainer:
    """Test IntentTrainer class."""

    @pytest.fixture
    def trainer(self) -> IntentTrainer:
        """Create IntentTrainer instance for testing."""
        config = TrainingConfig(output_dir="test_output")
        return IntentTrainer(config=config)

    @pytest.fixture
    def sample_training_data(self) -> list[dict]:
        """Sample training data in JSONL format."""
        return [
            {
                "query": "What is RAG?",
                "intent": "factual",
                "confidence": 0.95,
                "language": "en",
            },
            {
                "query": "How to configure Docker?",
                "intent": "procedural",
                "confidence": 0.92,
                "language": "en",
            },
            {
                "query": "Compare Postgres vs MySQL",
                "intent": "comparison",
                "confidence": 0.88,
                "language": "en",
            },
            {
                "query": "What is the best approach?",
                "intent": "recommendation",
                "confidence": 0.90,
                "language": "en",
            },
            {
                "query": "Where is the config file?",
                "intent": "navigation",
                "confidence": 0.93,
                "language": "en",
            },
        ] * 20  # 100 examples total (20 per class)

    @pytest.fixture
    def jsonl_file(self, sample_training_data: list[dict], tmp_path: Path) -> Path:
        """Create temporary JSONL file with training data."""
        file_path = tmp_path / "training_data.jsonl"
        with file_path.open("w") as f:
            for example in sample_training_data:
                f.write(json.dumps(example) + "\n")
        return file_path

    def test_initialization(self, trainer: IntentTrainer) -> None:
        """Test trainer initialization."""
        assert trainer.config.output_dir == "test_output"
        assert len(trainer.INTENT_LABELS) == 5
        assert trainer.INTENT_LABELS["factual"] == 0
        assert trainer.LABEL_TO_INTENT[0] == "factual"

    def test_load_training_data_success(
        self, trainer: IntentTrainer, jsonl_file: Path
    ) -> None:
        """Test successful loading of training data."""
        examples = trainer._load_training_data(jsonl_file)

        assert len(examples) == 100
        assert all("query" in ex for ex in examples)
        assert all("intent" in ex for ex in examples)

    def test_load_training_data_file_not_found(self, trainer: IntentTrainer) -> None:
        """Test error when training data file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            trainer._load_training_data("nonexistent.jsonl")

    def test_load_training_data_invalid_jsonl(
        self, trainer: IntentTrainer, tmp_path: Path
    ) -> None:
        """Test handling of invalid JSONL format."""
        file_path = tmp_path / "invalid.jsonl"
        with file_path.open("w") as f:
            f.write("valid json line\n")  # Invalid JSON
            f.write('{"valid": "json"}\n')  # Valid JSON

        examples = trainer._load_training_data(file_path)

        # Should skip invalid line, load valid one
        assert len(examples) == 1

    def test_convert_to_dataset(
        self, trainer: IntentTrainer, sample_training_data: list[dict]
    ) -> None:
        """Test conversion of examples to HuggingFace Dataset."""
        dataset = trainer._convert_to_dataset(sample_training_data)

        assert isinstance(dataset, Dataset)
        assert len(dataset) == 100
        assert "text" in dataset.column_names
        assert "label" in dataset.column_names

        # Check label mapping
        first_example = dataset[0]
        assert first_example["text"] == "What is RAG?"
        assert first_example["label"] == 0  # factual

    def test_convert_to_dataset_skip_invalid(self, trainer: IntentTrainer) -> None:
        """Test skipping of invalid examples during conversion."""
        invalid_examples = [
            {"query": "", "intent": "factual"},  # Empty query
            {"query": "Valid query", "intent": "unknown_intent"},  # Unknown intent
            {"query": "Valid query", "intent": "factual"},  # Valid
        ]

        dataset = trainer._convert_to_dataset(invalid_examples)

        # Should only have 1 valid example
        assert len(dataset) == 1

    def test_split_dataset(
        self, trainer: IntentTrainer, sample_training_data: list[dict]
    ) -> None:
        """Test dataset splitting."""
        dataset = trainer._convert_to_dataset(sample_training_data)
        split_dataset = trainer._split_dataset(dataset)

        assert "train" in split_dataset
        assert "test" in split_dataset

        # Check split ratio (20% validation)
        total = len(dataset)
        val_size = len(split_dataset["test"])
        expected_val_size = int(total * trainer.config.val_split)

        assert abs(val_size - expected_val_size) <= 2  # Allow small variance

    @patch("src.adaptation.intent_trainer.SetFitModel")
    @patch("src.adaptation.intent_trainer.Trainer")
    def test_train_success(
        self,
        mock_trainer_class: Mock,
        mock_setfit_model: Mock,
        trainer: IntentTrainer,
        jsonl_file: Path,
    ) -> None:
        """Test successful model training."""
        # Mock SetFit model
        mock_model = MagicMock()
        mock_model.predict.return_value = [0, 1, 2, 3, 4] * 4  # 20 predictions
        mock_setfit_model.from_pretrained.return_value = mock_model

        # Mock trainer
        mock_trainer_instance = MagicMock()
        mock_trainer_class.return_value = mock_trainer_instance

        # Train model
        model, metrics = trainer.train(train_data_path=str(jsonl_file))

        # Verify model was initialized
        mock_setfit_model.from_pretrained.assert_called_once()

        # Verify trainer was created
        mock_trainer_class.assert_called_once()

        # Verify training was called
        mock_trainer_instance.train.assert_called_once()

        # Verify model was saved
        mock_model.save_pretrained.assert_called_once()

        # Check metrics
        assert "accuracy" in metrics
        assert "training_time_sec" in metrics
        assert "per_class_f1" in metrics
        assert "quality_gates_passed" in metrics

    def test_train_insufficient_data(
        self, trainer: IntentTrainer, tmp_path: Path
    ) -> None:
        """Test error with insufficient training data."""
        # Create file with only 50 examples (< 100 minimum)
        small_file = tmp_path / "small.jsonl"
        with small_file.open("w") as f:
            for i in range(50):
                f.write(
                    json.dumps(
                        {"query": f"query {i}", "intent": "factual", "confidence": 0.9}
                    )
                    + "\n"
                )

        with pytest.raises(ValueError, match="Insufficient training data"):
            trainer.train(train_data_path=str(small_file))

    @patch("src.adaptation.intent_trainer.SetFitModel")
    def test_evaluate(self, mock_setfit_model: Mock, trainer: IntentTrainer) -> None:
        """Test model evaluation."""
        # Create mock model
        mock_model = MagicMock()

        # Mock predictions (100% accuracy)
        mock_model.predict.return_value = [0, 1, 2, 3, 4] * 4

        # Create test dataset
        test_data = {
            "text": ["query"] * 20,
            "label": [0, 1, 2, 3, 4] * 4,  # Perfect predictions
        }
        test_dataset = Dataset.from_dict(test_data)

        # Evaluate
        metrics = trainer._evaluate(mock_model, test_dataset)

        # Check metrics
        assert metrics["accuracy"] == 1.0  # 100% accuracy
        assert metrics["quality_gates_passed"] is True
        assert len(metrics["per_class_f1"]) == 5
        assert all(f1 == 1.0 for f1 in metrics["per_class_f1"].values())

    @patch("src.adaptation.intent_trainer.SetFitModel")
    def test_evaluate_low_accuracy(
        self, mock_setfit_model: Mock, trainer: IntentTrainer
    ) -> None:
        """Test quality gate failure with low accuracy."""
        # Create mock model with poor predictions
        mock_model = MagicMock()
        mock_model.predict.return_value = [0] * 20  # All predict class 0

        # Create test dataset with varied labels
        test_data = {
            "text": ["query"] * 20,
            "label": [0, 1, 2, 3, 4] * 4,  # True labels
        }
        test_dataset = Dataset.from_dict(test_data)

        # Evaluate
        metrics = trainer._evaluate(mock_model, test_dataset)

        # Check quality gate failure
        assert metrics["accuracy"] < 0.85  # Below threshold
        assert metrics["quality_gates_passed"] is False
        assert len(metrics["quality_issues"]) > 0

    def test_get_model_size_mb(self, trainer: IntentTrainer, tmp_path: Path) -> None:
        """Test model size calculation."""
        # Create dummy model files
        model_dir = tmp_path / "model"
        model_dir.mkdir()

        (model_dir / "model.safetensors").write_bytes(b"x" * 1024 * 1024)  # 1 MB
        (model_dir / "config.json").write_bytes(b"x" * 1024)  # 1 KB

        size_mb = trainer._get_model_size_mb(model_dir)

        assert size_mb >= 1.0  # At least 1 MB
        assert size_mb < 1.1  # Less than 1.1 MB


class TestIntentLabels:
    """Test intent label mappings."""

    def test_label_mapping_consistency(self) -> None:
        """Test that label mappings are consistent."""
        trainer = IntentTrainer()

        # Forward mapping
        for intent, label in trainer.INTENT_LABELS.items():
            # Reverse mapping should match
            assert trainer.LABEL_TO_INTENT[label] == intent

        # All 5 intents present
        assert len(trainer.INTENT_LABELS) == 5
        assert len(trainer.LABEL_TO_INTENT) == 5

    def test_label_mapping_values(self) -> None:
        """Test specific label values."""
        trainer = IntentTrainer()

        assert trainer.INTENT_LABELS["factual"] == 0
        assert trainer.INTENT_LABELS["procedural"] == 1
        assert trainer.INTENT_LABELS["comparison"] == 2
        assert trainer.INTENT_LABELS["recommendation"] == 3
        assert trainer.INTENT_LABELS["navigation"] == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
