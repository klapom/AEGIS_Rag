"""Integration tests for Domain Discovery API.

Sprint 117 - Feature 117.3: Domain Auto-Discovery API (8 SP)

Tests cover:
1. POST /api/v1/admin/domains/discover endpoint
2. Request validation
3. Response schema validation
4. Error handling (insufficient samples, LLM failures)
5. MENTIONED_IN inclusion
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestDomainDiscoveryAPI:
    """Integration tests for /api/v1/admin/domains/discover endpoint."""

    def test_discover_domains_success(self, client: TestClient):
        """Test successful domain discovery with sample documents."""
        request_data = {
            "sample_documents": [
                "Patient with Type 2 diabetes presenting with elevated glucose levels.",
                "COVID-19 treatment protocols updated by WHO.",
                "The stock price of AAPL increased 3% on strong earnings.",
                "Tesla stock surged after announcing record deliveries."
            ],
            "min_samples": 3,
            "max_samples": 10,
            "suggested_count": 2
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "discovered_domains" in data
        assert "processing_time_ms" in data
        assert "documents_analyzed" in data
        assert "clusters_found" in data

        # Verify data types
        assert isinstance(data["discovered_domains"], list)
        assert isinstance(data["processing_time_ms"], (int, float))
        assert data["processing_time_ms"] > 0
        assert data["documents_analyzed"] == 4
        assert data["clusters_found"] >= 1

        # Verify discovered domain structure
        if data["discovered_domains"]:
            domain = data["discovered_domains"][0]
            assert "name" in domain
            assert "suggested_description" in domain
            assert "confidence" in domain
            assert "entity_types" in domain
            assert "relation_types" in domain
            assert "intent_classes" in domain
            assert "sample_entities" in domain
            assert "recommended_model_family" in domain
            assert "reasoning" in domain

            # Verify MENTIONED_IN is always included
            assert "MENTIONED_IN" in domain["relation_types"]

            # Verify confidence bounds
            assert 0.0 <= domain["confidence"] <= 1.0

    def test_discover_domains_insufficient_samples(self, client: TestClient):
        """Test error when less than min_samples provided."""
        request_data = {
            "sample_documents": [
                "Document 1",
                "Document 2"  # Only 2 documents, need 3
            ],
            "min_samples": 3,
            "suggested_count": 1
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        # Should return 400 Bad Request
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "3 sample documents required" in data["detail"]

    def test_discover_domains_minimum_valid_request(self, client: TestClient):
        """Test with minimum valid sample count (3 documents)."""
        request_data = {
            "sample_documents": [
                "Document about medical treatments and patient care.",
                "Discussion of clinical trials and medical research.",
                "Healthcare policy and insurance coverage details."
            ],
            # min_samples defaults to 3
            # max_samples defaults to 10
            # suggested_count defaults to 5
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["documents_analyzed"] == 3
        assert len(data["discovered_domains"]) >= 1

    def test_discover_domains_max_samples_truncation(self, client: TestClient):
        """Test that excess samples are truncated to max_samples."""
        # Create 15 documents but set max_samples=5
        request_data = {
            "sample_documents": [f"Document {i}" for i in range(15)],
            "min_samples": 3,
            "max_samples": 5,
            "suggested_count": 2
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Should only analyze 5 documents (max_samples)
        assert data["documents_analyzed"] == 5

    def test_discover_domains_empty_documents(self, client: TestClient):
        """Test error with empty document list."""
        request_data = {
            "sample_documents": [],
            "suggested_count": 1
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        # Should fail validation (min_length=3)
        assert response.status_code == 422  # Unprocessable Entity

    def test_discover_domains_response_schema(self, client: TestClient):
        """Test detailed response schema validation."""
        request_data = {
            "sample_documents": [
                "Technical documentation for software API endpoints.",
                "Database schema design and SQL queries.",
                "Cloud infrastructure deployment with Kubernetes.",
                "Frontend React components and state management."
            ],
            "suggested_count": 2
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Detailed schema validation
        assert isinstance(data["discovered_domains"], list)
        assert isinstance(data["processing_time_ms"], (int, float))
        assert isinstance(data["documents_analyzed"], int)
        assert isinstance(data["clusters_found"], int)

        for domain in data["discovered_domains"]:
            # Required fields
            assert isinstance(domain["name"], str)
            assert len(domain["name"]) >= 2
            assert len(domain["name"]) <= 50

            assert isinstance(domain["suggested_description"], str)
            assert len(domain["suggested_description"]) >= 10

            assert isinstance(domain["confidence"], (int, float))
            assert 0.0 <= domain["confidence"] <= 1.0

            assert isinstance(domain["entity_types"], list)
            assert isinstance(domain["relation_types"], list)
            assert isinstance(domain["intent_classes"], list)
            assert isinstance(domain["sample_entities"], dict)

            assert isinstance(domain["recommended_model_family"], str)
            assert isinstance(domain["reasoning"], str)

            # MENTIONED_IN must always be present
            assert "MENTIONED_IN" in domain["relation_types"]

    def test_discover_domains_mentioned_in_inclusion(self, client: TestClient):
        """Test that MENTIONED_IN is always included in relation_types."""
        request_data = {
            "sample_documents": [
                "Document 1 with entities.",
                "Document 2 with more entities.",
                "Document 3 with relations."
            ],
            "suggested_count": 1
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Every discovered domain must have MENTIONED_IN
        for domain in data["discovered_domains"]:
            assert "MENTIONED_IN" in domain["relation_types"], (
                f"Domain '{domain['name']}' missing MENTIONED_IN relation"
            )

    def test_discover_domains_multiple_clusters(self, client: TestClient):
        """Test discovery identifies multiple distinct clusters."""
        # Mix clearly different document types
        request_data = {
            "sample_documents": [
                # Medical cluster
                "Patient diagnosed with diabetes and hypertension.",
                "Treatment protocol for COVID-19 infection.",

                # Finance cluster
                "Apple stock price increased by 5% this quarter.",
                "Tesla announces record earnings and stock buyback.",

                # Legal cluster
                "Contract agreement between parties for service delivery.",
                "Terms and conditions for software license agreement."
            ],
            "min_samples": 3,
            "max_samples": 10,
            "suggested_count": 3  # Request 3 clusters
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Should identify multiple clusters
        assert data["clusters_found"] >= 2
        assert len(data["discovered_domains"]) >= 2

        # Cluster names should be different
        domain_names = [d["name"] for d in data["discovered_domains"]]
        assert len(set(domain_names)) == len(domain_names)  # All unique

    def test_discover_domains_confidence_ordering(self, client: TestClient):
        """Test that domains are ordered by confidence (highest first)."""
        request_data = {
            "sample_documents": [
                "Medical patient records and treatment plans.",
                "Clinical trial results and pharmaceutical research.",
                "Healthcare insurance claims and billing.",
                "Financial statements and stock market analysis."
            ],
            "suggested_count": 2
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        assert response.status_code == 200
        data = response.json()

        if len(data["discovered_domains"]) >= 2:
            # Domains should be ordered by confidence (descending)
            confidences = [d["confidence"] for d in data["discovered_domains"]]
            assert confidences == sorted(confidences, reverse=True)

    @pytest.mark.skip(reason="Requires Ollama service running")
    def test_discover_domains_ollama_unavailable(self, client: TestClient):
        """Test error handling when Ollama service is unavailable."""
        # This test requires mocking Ollama connection failure
        # Skip in CI/CD, run manually for testing error paths
        pass


@pytest.mark.integration
class TestDomainDiscoveryEdgeCases:
    """Edge case tests for domain discovery."""

    def test_discover_domains_very_short_documents(self, client: TestClient):
        """Test discovery with very short documents."""
        request_data = {
            "sample_documents": [
                "Short doc 1",
                "Short doc 2",
                "Short doc 3"
            ],
            "suggested_count": 1
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        # Should still work, even with short docs
        assert response.status_code == 200
        data = response.json()
        assert data["documents_analyzed"] == 3

    def test_discover_domains_identical_documents(self, client: TestClient):
        """Test discovery with identical documents."""
        request_data = {
            "sample_documents": [
                "Identical document text",
                "Identical document text",
                "Identical document text"
            ],
            "suggested_count": 1
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Should form single cluster
        assert data["clusters_found"] == 1
        assert len(data["discovered_domains"]) == 1

    def test_discover_domains_special_characters(self, client: TestClient):
        """Test discovery handles documents with special characters."""
        request_data = {
            "sample_documents": [
                "Document with émojis 🏥 and spëcial çharacters!",
                "Text with #hashtags and @mentions",
                "Content with URLs: https://example.com"
            ],
            "suggested_count": 1
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        # Should handle gracefully
        assert response.status_code == 200

    def test_discover_domains_multilingual(self, client: TestClient):
        """Test discovery with mixed language documents."""
        request_data = {
            "sample_documents": [
                "English document about technology",
                "Deutsches Dokument über Technologie",
                "Document français sur la technologie"
            ],
            "suggested_count": 1
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        assert response.status_code == 200
        # BGE-M3 supports multilingual, should work


@pytest.mark.integration
class TestDomainDiscoveryPerformance:
    """Performance tests for domain discovery."""

    def test_discover_domains_processing_time(self, client: TestClient):
        """Test that processing completes within reasonable time."""
        request_data = {
            "sample_documents": [
                "Document 1 with technical content",
                "Document 2 with business content",
                "Document 3 with scientific content"
            ],
            "suggested_count": 1
        }

        response = client.post("/api/v1/admin/domains/discover", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Should complete in reasonable time (< 30s for 3 docs)
        # Processing time is in milliseconds
        assert data["processing_time_ms"] < 30000, (
            f"Discovery took {data['processing_time_ms']}ms, expected < 30000ms"
        )
