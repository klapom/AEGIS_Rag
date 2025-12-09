"""Tests for RAGAS evaluation module.

Note: Requires langchain_openai which may have version conflicts.
Skipped automatically if import fails.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

# Skip if langchain dependencies have version conflicts
pytest.importorskip("langchain_openai", reason="langchain_openai not available or version conflict")

from src.evaluation.ragas_eval import (
    EvaluationDataset,
    EvaluationResult,
    RAGASEvaluator,
)


class TestEvaluationDataset:
    """Tests for EvaluationDataset model."""

    def test_evaluation_dataset_creation(self):
        """Test creating an evaluation dataset."""
        dataset = EvaluationDataset(
            question="What is RAG?",
            ground_truth="RAG is Retrieval-Augmented Generation",
            contexts=["Context 1", "Context 2"],
            answer="RAG combines retrieval with generation",
            metadata={"difficulty": "easy"},
        )

        assert dataset.question == "What is RAG?"
        assert dataset.ground_truth == "RAG is Retrieval-Augmented Generation"
        assert len(dataset.contexts) == 2
        assert dataset.answer == "RAG combines retrieval with generation"
        assert dataset.metadata["difficulty"] == "easy"

    def test_evaluation_dataset_optional_answer(self):
        """Test that answer field is optional."""
        dataset = EvaluationDataset(
            question="What is RAG?",
            ground_truth="RAG is Retrieval-Augmented Generation",
            contexts=["Context 1"],
        )

        assert dataset.answer == ""
        assert dataset.metadata == {}

    def test_evaluation_dataset_from_dict(self):
        """Test creating dataset from dictionary."""
        data = {
            "question": "Test question",
            "ground_truth": "Test answer",
            "contexts": ["Context"],
            "metadata": {"type": "test"},
        }

        dataset = EvaluationDataset(**data)
        assert dataset.question == "Test question"
        assert dataset.metadata["type"] == "test"


class TestEvaluationResult:
    """Tests for EvaluationResult model."""

    def test_evaluation_result_creation(self):
        """Test creating an evaluation result."""
        result = EvaluationResult(
            scenario="vector-only",
            context_precision=0.85,
            context_recall=0.90,
            faithfulness=0.88,
            num_samples=10,
            duration_seconds=45.2,
        )

        assert result.scenario == "vector-only"
        assert result.context_precision == 0.85
        assert result.context_recall == 0.90
        assert result.faithfulness == 0.88
        assert result.num_samples == 10
        assert result.duration_seconds == 45.2
        assert result.timestamp is not None

    def test_evaluation_result_with_metadata(self):
        """Test evaluation result with metadata."""
        result = EvaluationResult(
            scenario="hybrid-reranked",
            context_precision=0.92,
            context_recall=0.88,
            faithfulness=0.95,
            num_samples=20,
            duration_seconds=60.0,
            metadata={"llm_model": "llama3.2", "metrics": ["precision", "recall"]},
        )

        assert result.metadata["llm_model"] == "llama3.2"
        assert "precision" in result.metadata["metrics"]


class TestRAGASEvaluator:
    """Tests for RAGASEvaluator class."""

    def test_evaluator_initialization(self):
        """Test evaluator initialization with defaults."""
        evaluator = RAGASEvaluator()

        assert evaluator.llm_model is not None
        assert evaluator.llm_base_url is not None
        assert len(evaluator.metrics_list) > 0

    def test_evaluator_initialization_custom_params(self):
        """Test evaluator initialization with custom parameters."""
        evaluator = RAGASEvaluator(
            llm_model="custom-model",
            llm_base_url="http://localhost:11434",
            metrics=["context_precision", "faithfulness"],
        )

        assert evaluator.llm_model == "custom-model"
        assert evaluator.llm_base_url == "http://localhost:11434"
        assert len(evaluator.metrics_list) == 2
        assert "context_precision" in evaluator.metrics_list

    def test_get_metrics(self):
        """Test getting RAGAS metrics."""
        evaluator = RAGASEvaluator(metrics=["context_precision", "context_recall"])
        metrics = evaluator._get_metrics()

        assert len(metrics) == 2
        # RAGAS metrics are classes/instances, not necessarily callables
        assert all(m is not None for m in metrics)

    def test_get_metrics_unknown_metric(self):
        """Test handling unknown metric names."""
        evaluator = RAGASEvaluator(metrics=["context_precision", "unknown_metric", "faithfulness"])
        metrics = evaluator._get_metrics()

        # Should only include known metrics
        assert len(metrics) == 2

    def test_load_dataset_success(self, tmp_path):
        """Test loading dataset from JSONL file."""
        # Create test dataset file
        dataset_file = tmp_path / "test_dataset.jsonl"
        test_data = [
            {
                "question": "Q1",
                "ground_truth": "A1",
                "contexts": ["C1"],
                "metadata": {"type": "test"},
            },
            {
                "question": "Q2",
                "ground_truth": "A2",
                "contexts": ["C2", "C3"],
                "answer": "Generated A2",
            },
        ]

        with open(dataset_file, "w") as f:
            for item in test_data:
                f.write(json.dumps(item) + "\n")

        evaluator = RAGASEvaluator()
        dataset = evaluator.load_dataset(dataset_file)

        assert len(dataset) == 2
        assert dataset[0].question == "Q1"
        assert dataset[1].answer == "Generated A2"
        assert len(dataset[1].contexts) == 2

    def test_load_dataset_file_not_found(self):
        """Test loading dataset from non-existent file."""
        evaluator = RAGASEvaluator()

        with pytest.raises(FileNotFoundError):
            evaluator.load_dataset("nonexistent_file.jsonl")

    def test_load_dataset_invalid_format(self, tmp_path):
        """Test loading dataset with invalid JSON lines."""
        dataset_file = tmp_path / "invalid_dataset.jsonl"

        with open(dataset_file, "w") as f:
            f.write('{"question": "Q1", "ground_truth": "A1", "contexts": ["C1"]}\n')
            f.write("invalid json line\n")  # Invalid line
            f.write('{"question": "Q2", "ground_truth": "A2", "contexts": ["C2"]}\n')

        evaluator = RAGASEvaluator()
        dataset = evaluator.load_dataset(dataset_file)

        # Should skip invalid line and load valid ones
        assert len(dataset) == 2

    def test_load_dataset_empty_file(self, tmp_path):
        """Test loading empty dataset file."""
        dataset_file = tmp_path / "empty_dataset.jsonl"
        dataset_file.write_text("")

        evaluator = RAGASEvaluator()

        with pytest.raises(ValueError, match="No valid examples found"):
            evaluator.load_dataset(dataset_file)

    @pytest.mark.asyncio
    async def test_evaluate_retrieval_mock(self):
        """Test evaluation with mocked RAGAS."""
        evaluator = RAGASEvaluator()

        test_dataset = [
            EvaluationDataset(
                question="Q1",
                ground_truth="A1",
                contexts=["C1"],
                answer="Generated A1",
            ),
            EvaluationDataset(
                question="Q2",
                ground_truth="A2",
                contexts=["C2"],
                answer="Generated A2",
            ),
        ]

        # Mock the evaluate function
        mock_result = MagicMock()
        mock_df = MagicMock()
        mock_df.to_dict.return_value = {
            "context_precision": [0.85],
            "context_recall": [0.90],
            "faithfulness": [0.88],
        }
        mock_result.to_pandas.return_value = mock_df

        with (
            patch("src.evaluation.ragas_eval.evaluate", return_value=mock_result),
            patch.object(evaluator, "_get_langchain_llm"),
        ):
            result = await evaluator.evaluate_retrieval(
                dataset=test_dataset, scenario="test-scenario"
            )

        assert result.scenario == "test-scenario"
        assert result.context_precision == 0.85
        assert result.context_recall == 0.90
        assert result.faithfulness == 0.88
        assert result.num_samples == 2
        assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_run_benchmark_mock(self):
        """Test running benchmark across scenarios."""
        evaluator = RAGASEvaluator()

        test_dataset = [
            EvaluationDataset(question="Q1", ground_truth="A1", contexts=["C1"], answer="A1")
        ]

        # Mock evaluate_retrieval to return different results per scenario
        async def mock_evaluate(dataset, scenario):
            return EvaluationResult(
                scenario=scenario,
                context_precision=0.85,
                context_recall=0.90,
                faithfulness=0.88,
                num_samples=len(dataset),
                duration_seconds=10.0,
            )

        with patch.object(evaluator, "evaluate_retrieval", side_effect=mock_evaluate):
            results = await evaluator.run_benchmark(
                dataset=test_dataset, scenarios=["vector-only", "hybrid-base"]
            )

        assert len(results) == 2
        assert "vector-only" in results
        assert "hybrid-base" in results
        assert results["vector-only"].scenario == "vector-only"

    def test_generate_json_report(self):
        """Test generating JSON report."""
        evaluator = RAGASEvaluator()

        results = {
            "vector-only": EvaluationResult(
                scenario="vector-only",
                context_precision=0.85,
                context_recall=0.90,
                faithfulness=0.88,
                num_samples=10,
                duration_seconds=45.0,
            ),
            "hybrid-base": EvaluationResult(
                scenario="hybrid-base",
                context_precision=0.90,
                context_recall=0.92,
                faithfulness=0.91,
                num_samples=10,
                duration_seconds=50.0,
            ),
        }

        report = evaluator.generate_report(results, format="json")

        assert report is not None
        report_data = json.loads(report)
        assert "scenarios" in report_data
        assert "summary" in report_data
        assert len(report_data["scenarios"]) == 2
        assert report_data["summary"]["best_context_precision"] == 0.90

    def test_generate_markdown_report(self):
        """Test generating Markdown report."""
        evaluator = RAGASEvaluator()

        results = {
            "vector-only": EvaluationResult(
                scenario="vector-only",
                context_precision=0.85,
                context_recall=0.90,
                faithfulness=0.88,
                num_samples=10,
                duration_seconds=45.0,
            )
        }

        report = evaluator.generate_report(results, format="markdown")

        assert report is not None
        assert "# RAGAS Evaluation Report" in report
        assert "vector-only" in report
        assert "0.85" in report  # precision score
        assert "## Summary" in report

    def test_generate_html_report(self):
        """Test generating HTML report."""
        evaluator = RAGASEvaluator()

        results = {
            "vector-only": EvaluationResult(
                scenario="vector-only",
                context_precision=0.85,
                context_recall=0.90,
                faithfulness=0.88,
                num_samples=10,
                duration_seconds=45.0,
            ),
            "hybrid-base": EvaluationResult(
                scenario="hybrid-base",
                context_precision=0.90,
                context_recall=0.92,
                faithfulness=0.91,
                num_samples=10,
                duration_seconds=50.0,
            ),
        }

        report = evaluator.generate_report(results, format="html")

        assert report is not None
        assert "<!DOCTYPE html>" in report
        assert "RAGAS Evaluation Report" in report
        assert "vector-only" in report
        assert "hybrid-base" in report
        assert "0.85" in report
        assert "Context Precision" in report

    def test_generate_report_with_output_path(self, tmp_path):
        """Test generating report and saving to file."""
        evaluator = RAGASEvaluator()

        results = {
            "test-scenario": EvaluationResult(
                scenario="test-scenario",
                context_precision=0.85,
                context_recall=0.90,
                faithfulness=0.88,
                num_samples=10,
                duration_seconds=45.0,
            )
        }

        output_file = tmp_path / "report.html"
        report = evaluator.generate_report(results, output_path=output_file, format="html")

        assert output_file.exists()
        assert output_file.read_text() == report
        assert "<!DOCTYPE html>" in report


class TestIntegration:
    """Integration tests for complete evaluation workflow."""

    def test_complete_workflow_mock(self, tmp_path):
        """Test complete evaluation workflow with mocked components."""
        # Create test dataset
        dataset_file = tmp_path / "test_dataset.jsonl"
        test_data = [
            {
                "question": "What is RAG?",
                "ground_truth": "Retrieval-Augmented Generation",
                "contexts": ["RAG combines retrieval with generation"],
                "answer": "RAG is a technique...",
            }
        ]

        with open(dataset_file, "w") as f:
            for item in test_data:
                f.write(json.dumps(item) + "\n")

        # Initialize evaluator and load dataset
        evaluator = RAGASEvaluator()
        dataset = evaluator.load_dataset(dataset_file)

        assert len(dataset) == 1
        assert dataset[0].question == "What is RAG?"

        # Test report generation
        mock_results = {
            "test": EvaluationResult(
                scenario="test",
                context_precision=0.85,
                context_recall=0.90,
                faithfulness=0.88,
                num_samples=1,
                duration_seconds=10.0,
            )
        }

        report_file = tmp_path / "report.json"
        evaluator.generate_report(mock_results, output_path=report_file, format="json")

        assert report_file.exists()
        report_data = json.loads(report_file.read_text())
        assert "scenarios" in report_data
        assert "test" in report_data["scenarios"]
