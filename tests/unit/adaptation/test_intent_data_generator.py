"""Unit tests for C-LARA intent data generator.

Sprint 67 Feature 67.10: Test synthetic data generation for intent classification.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adaptation.intent_data_generator import CLARADataGenerator, IntentExample


class TestIntentExample:
    """Test IntentExample dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        example = IntentExample(
            query="What is RAG?",
            intent="factual",
            confidence=0.95,
            language="en",
            domain="software",
        )

        result = example.to_dict()

        assert result == {
            "query": "What is RAG?",
            "intent": "factual",
            "confidence": 0.95,
            "language": "en",
            "domain": "software",
        }


class TestCLARADataGenerator:
    """Test CLARADataGenerator."""

    @pytest.fixture
    def generator(self):
        """Create data generator fixture."""
        return CLARADataGenerator(
            model="qwen2.5:7b",
            target_examples=100,
            examples_per_batch=10,
        )

    def test_initialization(self, generator):
        """Test generator initialization."""
        assert generator.model == "qwen2.5:7b"
        assert generator.target_examples == 100
        assert generator.examples_per_batch == 10
        assert generator.base_url == "http://localhost:11434"

    def test_intent_definitions(self, generator):
        """Test that all intent definitions are present."""
        expected_intents = {"factual", "procedural", "comparison", "recommendation", "navigation"}
        assert set(generator.INTENT_DEFINITIONS.keys()) == expected_intents

    def test_few_shot_examples(self, generator):
        """Test that few-shot examples exist for all intents."""
        expected_intents = {"factual", "procedural", "comparison", "recommendation", "navigation"}
        assert set(generator.FEW_SHOT_EXAMPLES.keys()) == expected_intents

        # Each intent should have at least 3 examples
        for intent, examples in generator.FEW_SHOT_EXAMPLES.items():
            assert len(examples) >= 3, f"Intent {intent} has fewer than 3 examples"

    def test_build_generation_prompt_english(self, generator):
        """Test prompt generation for English queries."""
        prompt = generator._build_generation_prompt(
            intent="factual",
            language="en",
            domain="software",
            num_examples=5,
        )

        assert "factual" in prompt
        assert "Generate queries in English" in prompt
        assert "software development" in prompt
        assert "5" in prompt
        assert "Few-shot Examples" in prompt

    def test_build_generation_prompt_german(self, generator):
        """Test prompt generation for German queries."""
        prompt = generator._build_generation_prompt(
            intent="procedural",
            language="de",
            domain="business",
            num_examples=10,
        )

        assert "procedural" in prompt
        assert "Generiere die Queries auf Deutsch" in prompt
        assert "business processes" in prompt
        assert "10" in prompt

    @pytest.mark.asyncio
    async def test_generate_batch_success(self, generator):
        """Test successful batch generation."""
        mock_response = {
            "response": json.dumps(
                [
                    {"query": "What is the capital of France?", "confidence": 0.95},
                    {"query": "Who invented Python?", "confidence": 0.92},
                    {"query": "When was Docker released?", "confidence": 0.90},
                ]
            )
        }

        with patch.object(
            generator.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_http_response = MagicMock()
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_http_response

            examples = await generator._generate_batch(
                intent="factual",
                language="en",
                domain="software",
                num_examples=3,
            )

            assert len(examples) == 3
            assert all(ex.intent == "factual" for ex in examples)
            assert all(ex.language == "en" for ex in examples)
            assert all(ex.domain == "software" for ex in examples)
            assert examples[0].query == "What is the capital of France?"
            assert examples[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_generate_batch_json_parse_error(self, generator):
        """Test handling of JSON parse errors."""
        mock_response = {"response": "Invalid JSON response"}

        with patch.object(
            generator.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_http_response = MagicMock()
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_http_response

            examples = await generator._generate_batch(
                intent="factual",
                language="en",
                domain="software",
                num_examples=3,
            )

            assert len(examples) == 0
            assert generator.stats["failed_batches"] == 0  # Not counted as failed batch

    @pytest.mark.asyncio
    async def test_generate_batch_http_error(self, generator):
        """Test handling of HTTP errors."""
        with patch.object(
            generator.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = Exception("Connection error")

            examples = await generator._generate_batch(
                intent="factual",
                language="en",
                domain="software",
                num_examples=3,
            )

            assert len(examples) == 0
            assert generator.stats["failed_batches"] == 1

    @pytest.mark.asyncio
    async def test_generate_batch_filters_invalid_queries(self, generator):
        """Test filtering of too short or too long queries."""
        mock_response = {
            "response": json.dumps(
                [
                    {"query": "Short", "confidence": 0.95},  # Too short (<10 chars)
                    {"query": "Valid query with enough length", "confidence": 0.92},
                    {"query": "x" * 301, "confidence": 0.90},  # Too long (>300 chars)
                ]
            )
        }

        with patch.object(
            generator.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_http_response = MagicMock()
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_http_response

            examples = await generator._generate_batch(
                intent="factual",
                language="en",
                domain="software",
                num_examples=3,
            )

            # Only the valid query should remain
            assert len(examples) == 1
            assert examples[0].query == "Valid query with enough length"

    def test_validate_dataset_balanced(self, generator):
        """Test validation of balanced dataset."""
        examples = []
        for intent in ["factual", "procedural", "comparison", "recommendation", "navigation"]:
            for i in range(20):  # 20 per class = 100 total = 20% each
                examples.append(
                    IntentExample(
                        query=f"Query {i} for {intent}",
                        intent=intent,
                        confidence=0.85,
                        language="en" if i % 2 == 0 else "de",
                        domain="software",
                    )
                )

        report = generator.validate_dataset(examples)

        assert report["valid"] is True
        assert report["total_examples"] == 100
        assert len(report["issues"]) == 0
        assert report["class_distribution"]["factual"] == 20
        assert report["high_confidence_pct"] == 100.0

    def test_validate_dataset_imbalanced_classes(self, generator):
        """Test validation detects class imbalance."""
        examples = []
        # 80% factual, 5% each for others
        for i in range(80):
            examples.append(
                IntentExample(
                    query=f"Factual query {i}",
                    intent="factual",
                    confidence=0.85,
                    language="en",
                    domain="software",
                )
            )
        for intent in ["procedural", "comparison", "recommendation", "navigation"]:
            for i in range(5):
                examples.append(
                    IntentExample(
                        query=f"Query {i} for {intent}",
                        intent=intent,
                        confidence=0.85,
                        language="en",
                        domain="software",
                    )
                )

        report = generator.validate_dataset(examples)

        assert report["valid"] is False
        assert len(report["issues"]) > 0
        assert any("imbalance" in issue.lower() for issue in report["issues"])

    def test_validate_dataset_low_confidence(self, generator):
        """Test validation detects low confidence examples."""
        examples = []
        for i in range(100):
            examples.append(
                IntentExample(
                    query=f"Query {i}",
                    intent="factual",
                    confidence=0.7,  # Below 0.8 threshold
                    language="en",
                    domain="software",
                )
            )

        report = generator.validate_dataset(examples)

        assert report["valid"] is False
        assert report["high_confidence_pct"] == 0.0
        assert any("Low confidence" in issue for issue in report["issues"])

    def test_validate_dataset_high_duplicates(self, generator):
        """Test validation detects high duplicate rate."""
        examples = []
        # Create 100 examples but only 10 unique queries
        for i in range(10):
            for j in range(10):
                examples.append(
                    IntentExample(
                        query=f"Query {i}",  # Same query repeated 10 times
                        intent="factual",
                        confidence=0.85,
                        language="en",
                        domain="software",
                    )
                )

        report = generator.validate_dataset(examples)

        assert report["valid"] is False
        assert report["duplicate_pct"] == 90.0  # 90% duplicates
        assert any("duplicate" in issue.lower() for issue in report["issues"])

    def test_validate_dataset_empty(self, generator):
        """Test validation of empty dataset."""
        report = generator.validate_dataset([])

        assert report["valid"] is False
        assert "error" in report
        assert "No examples generated" in report["error"]

    @pytest.mark.asyncio
    async def test_save_dataset(self, generator, tmp_path):
        """Test saving dataset to JSONL file."""
        examples = [
            IntentExample(
                query="What is RAG?",
                intent="factual",
                confidence=0.95,
                language="en",
                domain="software",
            ),
            IntentExample(
                query="How to install Docker?",
                intent="procedural",
                confidence=0.92,
                language="en",
                domain="software",
            ),
        ]

        output_path = tmp_path / "test_intent_data.jsonl"
        await generator.save_dataset(examples, output_path)

        assert output_path.exists()

        # Read and verify content
        with output_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 2

        # Parse first line
        line1 = json.loads(lines[0])
        assert line1["query"] == "What is RAG?"
        assert line1["intent"] == "factual"
        assert line1["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_save_dataset_creates_directory(self, generator, tmp_path):
        """Test that save_dataset creates parent directories."""
        output_path = tmp_path / "nested" / "dir" / "test.jsonl"
        examples = [
            IntentExample(
                query="Test query",
                intent="factual",
                confidence=0.85,
                language="en",
                domain="software",
            )
        ]

        await generator.save_dataset(examples, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()

    @pytest.mark.asyncio
    async def test_close(self, generator):
        """Test closing HTTP client."""
        with patch.object(generator.client, "aclose", new_callable=AsyncMock) as mock_close:
            await generator.close()
            mock_close.assert_called_once()


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(600)
class TestCLARADataGeneratorIntegration:
    """Integration tests requiring Ollama.

    These tests make real LLM calls and are slow (5+ minutes).
    Run with: pytest -m integration tests/unit/adaptation/test_intent_data_generator.py
    Skip with: pytest -m "not integration" tests/unit/adaptation/test_intent_data_generator.py
    """

    @pytest.mark.asyncio
    async def test_full_generation_workflow(self):
        """Test full workflow: generate → validate → save (requires Ollama).

        This test is marked as integration and will be skipped unless
        Ollama is running with qwen2.5:7b model.

        Expected time: 5-10 minutes (100+ LLM calls at ~4s each)
        """
        generator = CLARADataGenerator(
            model="qwen2.5:7b",
            target_examples=20,  # Small sample for testing
            examples_per_batch=5,
        )

        try:
            # Generate examples
            examples = await generator.generate_examples()

            # Validate
            assert len(examples) > 0, "Should generate at least some examples"
            assert all(isinstance(ex, IntentExample) for ex in examples)

            # Validate dataset
            report = generator.validate_dataset(examples)
            assert "total_examples" in report
            assert report["total_examples"] == len(examples)

        finally:
            await generator.close()
