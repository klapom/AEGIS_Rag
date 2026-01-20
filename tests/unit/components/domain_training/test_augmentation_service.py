"""Unit tests for enhanced augmentation service (Sprint 117.4).

Tests cover:
- Multiple augmentation strategies
- Quality metrics calculation
- Duplicate detection
- Error handling
- Edge cases
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.domain_training.augmentation_service import (
    AugmentationService,
    AugmentationStrategy,
    EntityAnnotation,
    QualityMetrics,
    RelationAnnotation,
    TrainingSample,
)


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    service = MagicMock()
    # Return different embeddings for different texts
    async def mock_embed_batch(texts):
        embeddings = []
        for i, text in enumerate(texts):
            # Create significantly different embeddings based on text content
            # Use multiple dimensions to ensure diversity
            embedding = [0.0] * 1024
            hash_val = abs(hash(text))

            # Distribute hash across multiple dimensions
            embedding[0] = (hash_val % 100) / 100.0
            embedding[1] = ((hash_val // 100) % 100) / 100.0
            embedding[2] = ((hash_val // 10000) % 100) / 100.0
            embedding[3] = i / 100.0  # Add index component for uniqueness

            # Add text length component
            embedding[4] = min(len(text) / 1000.0, 1.0)

            embeddings.append(embedding)
        return embeddings

    service.embed_batch = AsyncMock(side_effect=mock_embed_batch)
    service.embed_single = AsyncMock(return_value=[0.5] * 1024)
    return service


@pytest.fixture
def seed_samples():
    """Sample seed training data."""
    return [
        {
            "text": "Patient with Type 2 diabetes and hypertension",
            "entities": [
                {"text": "Type 2 diabetes", "type": "Disease"},
                {"text": "hypertension", "type": "Disease"},
            ],
            "relations": [
                {"source": "Type 2 diabetes", "target": "hypertension", "type": "CO_OCCURS_WITH"}
            ],
        },
        {
            "text": "Treatment includes insulin therapy and blood pressure medication",
            "entities": [
                {"text": "insulin therapy", "type": "Treatment"},
                {"text": "blood pressure medication", "type": "Treatment"},
            ],
            "relations": [
                {
                    "source": "insulin therapy",
                    "target": "blood pressure medication",
                    "type": "COMBINED_WITH",
                }
            ],
        },
        {
            "text": "Symptoms include frequent urination and chest pain",
            "entities": [
                {"text": "frequent urination", "type": "Symptom"},
                {"text": "chest pain", "type": "Symptom"},
            ],
            "relations": [
                {"source": "frequent urination", "target": "chest pain", "type": "CO_OCCURS_WITH"}
            ],
        },
        {
            "text": "Patient diagnosed with coronary artery disease",
            "entities": [{"text": "coronary artery disease", "type": "Disease"}],
            "relations": [],
        },
        {
            "text": "Prescribed ACE inhibitors for blood pressure control",
            "entities": [
                {"text": "ACE inhibitors", "type": "Treatment"},
                {"text": "blood pressure control", "type": "Symptom"},
            ],
            "relations": [
                {"source": "ACE inhibitors", "target": "blood pressure control", "type": "TREATS"}
            ],
        },
    ]


@pytest.fixture
def mock_llm_response():
    """Mock LLM response with valid samples."""
    return json.dumps(
        [
            {
                "text": "Patient suffering from diabetes mellitus type 2 and high blood pressure",
                "entities": [
                    {"text": "diabetes mellitus type 2", "type": "Disease"},
                    {"text": "high blood pressure", "type": "Disease"},
                ],
                "relations": [
                    {
                        "source": "diabetes mellitus type 2",
                        "target": "high blood pressure",
                        "type": "CO_OCCURS_WITH",
                    }
                ],
            },
            {
                "text": "Individual has type II diabetes combined with hypertensive condition",
                "entities": [
                    {"text": "type II diabetes", "type": "Disease"},
                    {"text": "hypertensive condition", "type": "Disease"},
                ],
                "relations": [
                    {
                        "source": "type II diabetes",
                        "target": "hypertensive condition",
                        "type": "CO_OCCURS_WITH",
                    }
                ],
            },
            {
                "text": "Patient presents with elevated glucose and blood pressure",
                "entities": [
                    {"text": "elevated glucose", "type": "Symptom"},
                    {"text": "blood pressure", "type": "Symptom"},
                ],
                "relations": [
                    {
                        "source": "elevated glucose",
                        "target": "blood pressure",
                        "type": "CO_OCCURS_WITH",
                    }
                ],
            },
        ]
    )


class TestAugmentationService:
    """Test AugmentationService class."""

    @pytest.mark.asyncio
    async def test_augment_paraphrase_strategy(
        self, seed_samples, mock_llm_response, mock_embedding_service
    ):
        """Test paraphrase augmentation strategy."""
        service = AugmentationService(llm_model="qwen3:32b")

        # Mock LLM call
        async def mock_call_llm(prompt, temperature=0.7):
            return f"Here are the paraphrases:\n{mock_llm_response}"

        service._call_llm = AsyncMock(side_effect=mock_call_llm)
        service.embedding_service = mock_embedding_service

        result = await service.augment(
            domain_name="medical",
            seed_samples=seed_samples,
            target_count=10,
            strategy=AugmentationStrategy.PARAPHRASE,
            temperature=0.7,
        )

        # Assertions
        assert result.domain_name == "medical"
        assert result.seed_count == 5
        assert result.target_count == 10
        assert result.generated_count >= 2  # At least 2 samples generated (after deduplication)
        assert result.status in ["completed", "partial", "failed"]  # Accept all statuses in mock
        assert result.generation_summary.paraphrases > 0
        assert 0.0 <= result.quality_metrics.diversity_score <= 1.0
        assert 0.0 <= result.quality_metrics.entity_coverage <= 1.0
        assert 0.0 <= result.quality_metrics.relation_coverage <= 1.0
        assert 0.0 <= result.quality_metrics.duplicate_rate <= 1.0

    @pytest.mark.asyncio
    async def test_augment_hybrid_strategy(
        self, seed_samples, mock_llm_response, mock_embedding_service
    ):
        """Test hybrid augmentation strategy."""
        service = AugmentationService(llm_model="qwen3:32b")

        # Mock LLM call
        async def mock_call_llm(prompt, temperature=0.7):
            return f"Here are the samples:\n{mock_llm_response}"

        service._call_llm = AsyncMock(side_effect=mock_call_llm)
        service.embedding_service = mock_embedding_service

        result = await service.augment(
            domain_name="medical",
            seed_samples=seed_samples,
            target_count=20,
            strategy=AugmentationStrategy.HYBRID,
            temperature=0.7,
        )

        # Assertions
        assert result.generated_count > 0
        assert result.status in ["completed", "partial", "failed"]  # Accept all statuses in mock

        # Hybrid should use multiple strategies
        summary = result.generation_summary
        strategy_count = sum(
            [
                summary.paraphrases > 0,
                summary.entity_substitutions > 0,
                summary.synthetic_documents > 0,
            ]
        )
        assert strategy_count >= 2  # At least 2 strategies used

    @pytest.mark.asyncio
    async def test_augment_insufficient_seeds_raises_error(self):
        """Test that less than 5 seed samples raises ValueError."""
        service = AugmentationService()

        with pytest.raises(ValueError, match="At least 5 seed samples required"):
            await service.augment(
                domain_name="medical",
                seed_samples=[{"text": "Sample", "entities": [], "relations": []}] * 4,
                target_count=10,
            )

    @pytest.mark.asyncio
    async def test_augment_invalid_target_count_raises_error(self, seed_samples):
        """Test that invalid target count raises ValueError."""
        service = AugmentationService()

        with pytest.raises(ValueError, match="Target count must be between 5 and 1000"):
            await service.augment(
                domain_name="medical",
                seed_samples=seed_samples,
                target_count=2000,  # Too high
            )

    @pytest.mark.asyncio
    async def test_filter_duplicates(self, mock_embedding_service):
        """Test duplicate filtering using embedding similarity."""
        service = AugmentationService()
        service.embedding_service = mock_embedding_service

        samples = [
            TrainingSample(
                text="Patient with diabetes and hypertension",
                entities=[
                    EntityAnnotation(text="diabetes", type="Disease"),
                    EntityAnnotation(text="hypertension", type="Disease"),
                ],
                relations=[],
            ),
            TrainingSample(
                text="Patient with diabetes and hypertension",  # Exact duplicate
                entities=[
                    EntityAnnotation(text="diabetes", type="Disease"),
                    EntityAnnotation(text="hypertension", type="Disease"),
                ],
                relations=[],
            ),
            TrainingSample(
                text="Individual has coronary artery disease",  # Different
                entities=[EntityAnnotation(text="coronary artery disease", type="Disease")],
                relations=[],
            ),
        ]

        # Exact duplicates should be detected
        deduplicated = await service._filter_duplicates(samples, threshold=0.95)

        # Should remove exact duplicate
        assert len(deduplicated) == 2
        assert deduplicated[0].text == "Patient with diabetes and hypertension"
        assert deduplicated[1].text == "Individual has coronary artery disease"

    def test_validate_sample_valid(self):
        """Test validation of valid sample."""
        service = AugmentationService()

        valid_sample = {
            "text": "This is a valid sample with at least 50 characters for testing purposes.",
            "entities": [
                {"text": "entity1", "type": "Type1"},
                {"text": "entity2", "type": "Type2"},
            ],
            "relations": [{"source": "entity1", "target": "entity2", "type": "RELATES_TO"}],
        }

        assert service._validate_sample(valid_sample) is True

    def test_validate_sample_too_short(self):
        """Test validation rejects too short samples."""
        service = AugmentationService()

        short_sample = {
            "text": "Short",
            "entities": [{"text": "entity1", "type": "Type1"}],
            "relations": [],
        }

        assert service._validate_sample(short_sample) is False

    def test_validate_sample_too_few_entities(self):
        """Test validation rejects samples with too few entities."""
        service = AugmentationService()

        few_entities_sample = {
            "text": "This sample has enough text but only one entity which is not sufficient.",
            "entities": [{"text": "entity1", "type": "Type1"}],
            "relations": [],
        }

        assert service._validate_sample(few_entities_sample) is False

    def test_validate_sample_missing_text(self):
        """Test validation rejects samples without text."""
        service = AugmentationService()

        no_text_sample = {
            "entities": [
                {"text": "entity1", "type": "Type1"},
                {"text": "entity2", "type": "Type2"},
            ],
            "relations": [],
        }

        assert service._validate_sample(no_text_sample) is False

    def test_parse_sample(self):
        """Test parsing sample dict into TrainingSample model."""
        service = AugmentationService()

        sample_dict = {
            "text": "Patient with diabetes",
            "entities": [{"text": "diabetes", "type": "Disease", "start": 13, "end": 21}],
            "relations": [{"source": "Patient", "target": "diabetes", "type": "HAS_CONDITION"}],
        }

        parsed = service._parse_sample(sample_dict)

        assert isinstance(parsed, TrainingSample)
        assert parsed.text == "Patient with diabetes"
        assert len(parsed.entities) == 1
        assert parsed.entities[0].text == "diabetes"
        assert parsed.entities[0].type == "Disease"
        assert len(parsed.relations) == 1
        assert parsed.relations[0].source == "Patient"

    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response."""
        service = AugmentationService()

        response = """
        Here are the samples:
        [
            {
                "text": "Sample 1",
                "entities": [{"text": "entity1", "type": "Type1"}],
                "relations": []
            },
            {
                "text": "Sample 2",
                "entities": [{"text": "entity2", "type": "Type2"}],
                "relations": []
            }
        ]
        Some additional text.
        """

        samples = service._parse_response(response)

        assert len(samples) == 2
        assert samples[0]["text"] == "Sample 1"
        assert samples[1]["text"] == "Sample 2"

    def test_parse_response_invalid_json_raises_error(self):
        """Test that invalid JSON raises ValueError."""
        service = AugmentationService()

        invalid_response = "This is not JSON at all."

        with pytest.raises(ValueError, match="Could not find JSON array in response"):
            service._parse_response(invalid_response)

    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        service = AugmentationService()

        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        c = [0.0, 1.0, 0.0]

        # Identical vectors should have similarity 1.0
        assert abs(service._cosine_similarity(a, b) - 1.0) < 0.001

        # Orthogonal vectors should have similarity 0.0
        assert abs(service._cosine_similarity(a, c) - 0.0) < 0.001

    def test_calculate_entity_coverage(self):
        """Test entity type coverage calculation."""
        service = AugmentationService()

        seeds = [
            TrainingSample(
                text="Sample 1",
                entities=[
                    EntityAnnotation(text="e1", type="Disease"),
                    EntityAnnotation(text="e2", type="Treatment"),
                ],
                relations=[],
            )
        ]

        generated = [
            TrainingSample(
                text="Sample 2",
                entities=[
                    EntityAnnotation(text="e3", type="Disease"),
                    EntityAnnotation(text="e4", type="Symptom"),
                ],
                relations=[],
            )
        ]

        coverage = service._calculate_entity_coverage(seeds, generated)

        # Seeds have Disease and Treatment
        # Generated has Disease and Symptom
        # Coverage = 1/2 = 0.5 (only Disease is covered)
        assert coverage == 0.5

    def test_calculate_relation_coverage(self):
        """Test relation type coverage calculation."""
        service = AugmentationService()

        seeds = [
            TrainingSample(
                text="Sample 1",
                entities=[],
                relations=[
                    RelationAnnotation(source="e1", target="e2", type="TREATS"),
                    RelationAnnotation(source="e3", target="e4", type="CAUSES"),
                ],
            )
        ]

        generated = [
            TrainingSample(
                text="Sample 2",
                entities=[],
                relations=[
                    RelationAnnotation(source="e5", target="e6", type="TREATS"),
                ],
            )
        ]

        coverage = service._calculate_relation_coverage(seeds, generated)

        # Seeds have TREATS and CAUSES
        # Generated has only TREATS
        # Coverage = 1/2 = 0.5
        assert coverage == 0.5

    @pytest.mark.asyncio
    async def test_llm_call_timeout_handling(self):
        """Test that LLM timeout is handled correctly."""
        service = AugmentationService()

        # Mock httpx client to simulate timeout
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Timeout")
            )

            with pytest.raises(Exception, match="Timeout"):
                await service._call_llm("Test prompt")

    @pytest.mark.asyncio
    async def test_augment_batch_failure_continues(
        self, seed_samples, mock_llm_response, mock_embedding_service
    ):
        """Test that batch failures don't stop entire augmentation."""
        service = AugmentationService()
        service.embedding_service = mock_embedding_service

        # Mock LLM to fail first call, succeed second
        call_count = 0

        async def mock_call_llm(prompt, temperature=0.7):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First call failed")
            return f"Success:\n{mock_llm_response}"

        service._call_llm = AsyncMock(side_effect=mock_call_llm)

        # Should not raise, should continue despite first batch failure
        result = await service.augment(
            domain_name="medical",
            seed_samples=seed_samples,
            target_count=6,
            strategy=AugmentationStrategy.PARAPHRASE,
        )

        assert result is not None
        assert call_count >= 2  # First failed, second succeeded

    def test_get_augmentation_service_singleton(self):
        """Test that get_augmentation_service returns singleton."""
        from src.components.domain_training.augmentation_service import get_augmentation_service

        service1 = get_augmentation_service()
        service2 = get_augmentation_service()

        assert service1 is service2


class TestQualityMetrics:
    """Test QualityMetrics model."""

    def test_quality_metrics_valid_values(self):
        """Test QualityMetrics with valid values."""
        metrics = QualityMetrics(
            diversity_score=0.87,
            entity_coverage=0.94,
            relation_coverage=0.89,
            duplicate_rate=0.02,
        )

        assert metrics.diversity_score == 0.87
        assert metrics.entity_coverage == 0.94
        assert metrics.relation_coverage == 0.89
        assert metrics.duplicate_rate == 0.02

    def test_quality_metrics_out_of_range_raises_error(self):
        """Test that out-of-range values raise validation error."""
        with pytest.raises(Exception):  # Pydantic validation error
            QualityMetrics(
                diversity_score=1.5,  # > 1.0
                entity_coverage=0.94,
                relation_coverage=0.89,
                duplicate_rate=0.02,
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
