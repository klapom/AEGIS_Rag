"""Unit tests for Domain Discovery Service.

Sprint 117 - Feature 117.3: Domain Auto-Discovery (8 SP)

Tests cover:
1. Document embedding and clustering
2. LLM-based domain analysis
3. Entity/relation type extraction
4. MENTIONED_IN relation inclusion
5. Confidence scoring
6. Error handling
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.components.domain_discovery.discovery_service import (
    DomainDiscoveryService,
    DiscoveredDomain,
    DomainDiscoveryResult,
)


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        "Patient with Type 2 diabetes presenting with elevated fasting glucose levels.",
        "COVID-19 treatment protocols updated by WHO include new antiviral medications.",
        "The stock price of AAPL increased 3% on strong earnings report from Q4 2025.",
        "Tesla stock surged after announcing record deliveries in the automotive sector.",
    ]


@pytest.fixture
def mock_embeddings():
    """Mock embeddings for documents."""
    # Create realistic embeddings that cluster medical vs finance docs
    medical_base = np.random.rand(1024)
    finance_base = np.random.rand(1024)

    return np.array([
        medical_base + np.random.rand(1024) * 0.1,  # Medical doc 1
        medical_base + np.random.rand(1024) * 0.1,  # Medical doc 2
        finance_base + np.random.rand(1024) * 0.1,  # Finance doc 1
        finance_base + np.random.rand(1024) * 0.1,  # Finance doc 2
    ])


@pytest.fixture
def mock_llm_response_medical():
    """Mock LLM response for medical domain."""
    return json.dumps({
        "name": "medical_records",
        "description": "Medical domain covering diseases, treatments, and clinical terminology",
        "entity_types": ["Disease", "Symptom", "Treatment", "Medication"],
        "relation_types": ["TREATS", "CAUSES", "DIAGNOSED_WITH"],
        "intent_classes": ["symptom_inquiry", "treatment_request", "diagnosis_query"],
        "sample_entities": {
            "Disease": ["Type 2 diabetes", "COVID-19"],
            "Treatment": ["antiviral medications", "insulin therapy"]
        },
        "recommended_model_family": "medical",
        "confidence": 0.92,
        "reasoning": "Documents contain clinical terminology and medical concepts"
    })


@pytest.fixture
def mock_llm_response_finance():
    """Mock LLM response for finance domain."""
    return json.dumps({
        "name": "financial_reports",
        "description": "Financial domain for stock prices, earnings, and market data",
        "entity_types": ["Company", "StockTicker", "Currency", "Amount"],
        "relation_types": ["LISTED_ON", "TRADED_AT", "EARNINGS_FROM"],
        "intent_classes": ["price_inquiry", "earnings_query"],
        "sample_entities": {
            "StockTicker": ["AAPL", "TSLA"],
            "Company": ["Tesla"]
        },
        "recommended_model_family": "finance",
        "confidence": 0.87,
        "reasoning": "Documents reference stock tickers and financial metrics"
    })


class TestDomainDiscoveryService:
    """Test suite for DomainDiscoveryService."""

    def test_initialization(self):
        """Test service initialization."""
        service = DomainDiscoveryService(
            llm_model="qwen3:32b",
            min_samples=3,
            max_samples=10
        )

        assert service.llm_model == "qwen3:32b"
        assert service.min_samples == 3
        assert service.max_samples == 10
        assert service.embedding_service is not None

    @pytest.mark.asyncio
    async def test_discover_domains_insufficient_samples(self):
        """Test error when less than min_samples provided."""
        service = DomainDiscoveryService(min_samples=3)

        with pytest.raises(ValueError, match="At least 3 sample documents required"):
            await service.discover_domains(
                sample_documents=["Doc 1", "Doc 2"],  # Only 2 docs
                suggested_count=1
            )

    @pytest.mark.asyncio
    async def test_discover_domains_truncates_excess_samples(self, sample_documents):
        """Test that excess samples are truncated to max_samples."""
        service = DomainDiscoveryService(max_samples=3)

        # Create 10 documents
        many_docs = sample_documents * 3  # 12 documents

        with patch.object(
            service.embedding_service, "embed_batch", new_callable=AsyncMock
        ) as mock_embed:
            mock_embed.return_value = [
                {"dense": np.random.rand(1024).tolist()} for _ in range(3)
            ]

            with patch.object(service, "_analyze_clusters", new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = []

                result = await service.discover_domains(
                    sample_documents=many_docs,
                    suggested_count=1
                )

                # Should only embed 3 documents (max_samples)
                assert mock_embed.call_count == 1
                embedded_docs = mock_embed.call_args[0][0]
                assert len(embedded_docs) == 3

    @pytest.mark.asyncio
    async def test_embed_documents(self, sample_documents, mock_embeddings):
        """Test document embedding using BGE-M3."""
        service = DomainDiscoveryService()

        with patch.object(
            service.embedding_service, "embed_batch", new_callable=AsyncMock
        ) as mock_embed:
            # Mock BGE-M3 response
            mock_embed.return_value = [
                {"dense": emb.tolist()} for emb in mock_embeddings
            ]

            embeddings = await service._embed_documents(sample_documents)

            assert embeddings.shape == (4, 1024)
            assert mock_embed.call_count == 1
            assert len(mock_embed.call_args[0][0]) == 4

    def test_cluster_documents_single_cluster(self, mock_embeddings):
        """Test clustering with only 1 document."""
        service = DomainDiscoveryService()

        single_embedding = mock_embeddings[:1]
        labels = service._cluster_documents(single_embedding, suggested_count=5)

        # Single document should form single cluster
        assert len(labels) == 1
        assert labels[0] == 0

    def test_cluster_documents_multiple_clusters(self, mock_embeddings):
        """Test K-means clustering identifies distinct groups."""
        service = DomainDiscoveryService()

        labels = service._cluster_documents(mock_embeddings, suggested_count=2)

        assert len(labels) == 4
        assert len(set(labels)) == 2  # Should identify 2 clusters

        # Medical docs should cluster together
        assert labels[0] == labels[1]

        # Finance docs should cluster together
        assert labels[2] == labels[3]

        # Medical and finance should be different clusters
        assert labels[0] != labels[2]

    @pytest.mark.asyncio
    async def test_analyze_single_cluster(
        self, sample_documents, mock_llm_response_medical
    ):
        """Test LLM analysis of a single cluster."""
        service = DomainDiscoveryService()

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response_medical

            domain = await service._analyze_single_cluster(
                cluster_id=0,
                cluster_documents=sample_documents[:2]  # Medical docs
            )

            assert domain is not None
            assert domain.name == "medical_records"
            assert domain.confidence == 0.92
            assert "Disease" in domain.entity_types
            assert "TREATS" in domain.relation_types

            # MENTIONED_IN should be automatically added
            assert "MENTIONED_IN" in domain.relation_types

    @pytest.mark.asyncio
    async def test_analyze_clusters_parallel(
        self, sample_documents, mock_llm_response_medical, mock_llm_response_finance
    ):
        """Test parallel analysis of multiple clusters."""
        service = DomainDiscoveryService()

        cluster_labels = np.array([0, 0, 1, 1])  # 2 clusters

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            # Return different responses for different clusters
            mock_llm.side_effect = [
                mock_llm_response_medical,
                mock_llm_response_finance
            ]

            domains = await service._analyze_clusters(sample_documents, cluster_labels)

            assert len(domains) == 2
            assert mock_llm.call_count == 2

            # Check both domains were discovered
            domain_names = {d.name for d in domains}
            assert "medical_records" in domain_names
            assert "financial_reports" in domain_names

    def test_parse_llm_response_success(self, mock_llm_response_medical):
        """Test successful parsing of LLM response."""
        service = DomainDiscoveryService()

        domain = service._parse_llm_response(mock_llm_response_medical, cluster_id=0)

        assert domain.name == "medical_records"
        assert domain.confidence == 0.92
        assert domain.suggested_description.startswith("Medical domain")
        assert len(domain.entity_types) == 4
        assert len(domain.relation_types) == 3
        assert domain.recommended_model_family == "medical"

    def test_parse_llm_response_normalizes_name(self):
        """Test domain name normalization."""
        service = DomainDiscoveryService()

        response = json.dumps({
            "name": "Medical Reports & Clinical Data!",  # Invalid characters
            "description": "Test domain",
            "confidence": 0.8,
            "entity_types": [],
            "relation_types": [],
        })

        domain = service._parse_llm_response(response, cluster_id=0)

        # Should normalize to lowercase alphanumeric with underscores
        assert domain.name == "medical_reports_clinical_data"

    def test_parse_llm_response_no_json(self):
        """Test error handling when no JSON in response."""
        service = DomainDiscoveryService()

        response = "This is just plain text without any JSON"

        with pytest.raises(ValueError, match="Could not parse LLM response as JSON"):
            service._parse_llm_response(response, cluster_id=0)

    def test_parse_llm_response_malformed_json(self):
        """Test error handling for malformed JSON."""
        service = DomainDiscoveryService()

        response = '{"name": "test", "confidence": INVALID}'  # Invalid JSON

        with pytest.raises(json.JSONDecodeError):
            service._parse_llm_response(response, cluster_id=0)

    @pytest.mark.asyncio
    async def test_discover_domains_full_flow(
        self, sample_documents, mock_embeddings,
        mock_llm_response_medical, mock_llm_response_finance
    ):
        """Test complete discovery flow end-to-end."""
        service = DomainDiscoveryService()

        with patch.object(
            service.embedding_service, "embed_batch", new_callable=AsyncMock
        ) as mock_embed:
            mock_embed.return_value = [
                {"dense": emb.tolist()} for emb in mock_embeddings
            ]

            with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
                mock_llm.side_effect = [
                    mock_llm_response_medical,
                    mock_llm_response_finance
                ]

                result = await service.discover_domains(
                    sample_documents=sample_documents,
                    suggested_count=2
                )

                # Verify result structure
                assert isinstance(result, DomainDiscoveryResult)
                assert result.documents_analyzed == 4
                assert result.clusters_found == 2
                assert len(result.discovered_domains) == 2
                assert result.processing_time_ms > 0

                # Verify domains
                domain_names = {d.name for d in result.discovered_domains}
                assert "medical_records" in domain_names
                assert "financial_reports" in domain_names

                # Verify MENTIONED_IN is included
                for domain in result.discovered_domains:
                    assert "MENTIONED_IN" in domain.relation_types

    @pytest.mark.asyncio
    async def test_discover_domains_single_cluster_fallback(
        self, mock_llm_response_medical
    ):
        """Test discovery with very similar documents (single cluster)."""
        service = DomainDiscoveryService()

        # All documents are very similar (medical)
        similar_docs = [
            "Patient with diabetes",
            "Patient with hypertension",
            "Patient with chronic pain"
        ]

        with patch.object(
            service.embedding_service, "embed_batch", new_callable=AsyncMock
        ) as mock_embed:
            # Mock similar embeddings (would cluster into 1 group)
            base_emb = np.random.rand(1024)
            mock_embed.return_value = [
                {"dense": (base_emb + np.random.rand(1024) * 0.01).tolist()}
                for _ in range(3)
            ]

            with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = mock_llm_response_medical

                result = await service.discover_domains(
                    sample_documents=similar_docs,
                    suggested_count=3  # Request 3 but should get 1
                )

                # Should still work with 1 cluster
                assert result.clusters_found >= 1
                assert len(result.discovered_domains) >= 1

    @pytest.mark.asyncio
    async def test_mentioned_in_always_included(self, mock_llm_response_medical):
        """Test that MENTIONED_IN is always added to relation_types."""
        service = DomainDiscoveryService()

        # Response without MENTIONED_IN
        response_without = json.loads(mock_llm_response_medical)
        response_without["relation_types"] = ["TREATS", "CAUSES"]  # No MENTIONED_IN
        response_text = json.dumps(response_without)

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = response_text

            domain = await service._analyze_single_cluster(
                cluster_id=0,
                cluster_documents=["Doc 1", "Doc 2"]
            )

            # MENTIONED_IN should be automatically added
            assert "MENTIONED_IN" in domain.relation_types
            assert "TREATS" in domain.relation_types
            assert "CAUSES" in domain.relation_types


class TestDiscoveredDomain:
    """Test suite for DiscoveredDomain model."""

    def test_discovered_domain_validation(self):
        """Test Pydantic validation for DiscoveredDomain."""
        domain = DiscoveredDomain(
            name="test_domain",
            suggested_description="Test description for validation",
            confidence=0.85,
            entity_types=["Person", "Organization"],
            relation_types=["WORKS_FOR", "MENTIONED_IN"],
            intent_classes=["inquiry", "request"],
            sample_entities={"Person": ["Alice", "Bob"]},
            recommended_model_family="general",
            reasoning="Test reasoning"
        )

        assert domain.name == "test_domain"
        assert domain.confidence == 0.85
        assert len(domain.entity_types) == 2

    def test_discovered_domain_confidence_bounds(self):
        """Test confidence is bounded between 0 and 1."""
        with pytest.raises(ValueError):
            DiscoveredDomain(
                name="test",
                suggested_description="Test",
                confidence=1.5,  # Invalid: > 1.0
                entity_types=[],
                relation_types=[],
                intent_classes=[],
            )

        with pytest.raises(ValueError):
            DiscoveredDomain(
                name="test",
                suggested_description="Test",
                confidence=-0.1,  # Invalid: < 0.0
                entity_types=[],
                relation_types=[],
                intent_classes=[],
            )


class TestDomainDiscoveryResult:
    """Test suite for DomainDiscoveryResult model."""

    def test_result_validation(self):
        """Test Pydantic validation for result."""
        result = DomainDiscoveryResult(
            discovered_domains=[],
            processing_time_ms=1234.56,
            documents_analyzed=5,
            clusters_found=2
        )

        assert result.processing_time_ms == 1234.56
        assert result.documents_analyzed == 5
        assert result.clusters_found == 2
        assert result.discovered_domains == []
