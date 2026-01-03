"""Unit tests for Document and Section Selection API endpoints.

Sprint 71 Feature 71.17: Document and Section Selection API
Sprint 71 Feature 71.17b: Qdrant-based document retrieval with filenames
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.v1.graph_communities import (
    DocumentMetadata,
    DocumentsResponse,
    DocumentSection,
    SectionsResponse,
    get_documents,
    get_document_sections,
)


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client for testing."""
    client = MagicMock()
    client.execute_query = AsyncMock()
    return client


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for testing."""
    client = MagicMock()
    client.async_client = MagicMock()
    client.async_client.scroll = AsyncMock()
    return client


@pytest.fixture
def sample_qdrant_points():
    """Sample Qdrant points for testing."""

    class Point:
        def __init__(self, doc_id, doc_path, timestamp):
            self.payload = {
                "document_id": doc_id,
                "document_path": doc_path,
                "ingestion_timestamp": timestamp,
                "content": "Sample content",
            }

    return [
        Point("doc_123", "/path/to/Machine_Learning_Basics.pdf", 1704106800.0),
        Point("doc_123", "/path/to/Machine_Learning_Basics.pdf", 1704106900.0),  # Same doc
        Point("doc_456", "/data/reports/Deep_Learning_Advanced.pdf", 1702636800.0),
    ]


@pytest.fixture
def sample_documents():
    """Sample documents for testing (legacy - for sections endpoint)."""
    return [
        {
            "id": "doc_123",
            "title": "Machine Learning Basics",
            "created_at": datetime(2026, 1, 1, 12, 0, 0),
            "updated_at": datetime(2026, 1, 2, 15, 30, 0),
        },
        {
            "id": "doc_456",
            "title": "Deep Learning Advanced",
            "created_at": datetime(2025, 12, 15, 10, 0, 0),
            "updated_at": datetime(2025, 12, 20, 14, 0, 0),
        },
    ]


@pytest.fixture
def sample_sections():
    """Sample sections for testing."""
    return [
        {
            "id": "sec_1",
            "heading": "Introduction",
            "level": 1,
            "entity_count": 15,
            "chunk_count": 8,
        },
        {
            "id": "sec_2",
            "heading": "Methods",
            "level": 1,
            "entity_count": 23,
            "chunk_count": 12,
        },
        {
            "id": "sec_3",
            "heading": "Results",
            "level": 1,
            "entity_count": 18,
            "chunk_count": 10,
        },
    ]


class TestGetDocuments:
    """Test GET /graph/documents endpoint (Qdrant-based)."""

    @pytest.mark.asyncio
    async def test_get_documents_success(self, mock_qdrant_client, sample_qdrant_points):
        """Test successful document retrieval from Qdrant."""
        # Setup mock - return points in first scroll, then None to end loop
        mock_qdrant_client.async_client.scroll.side_effect = [
            (sample_qdrant_points, None),  # All points in first batch, no next offset
        ]

        with patch(
            "src.api.v1.graph_communities.QdrantClient",
            return_value=mock_qdrant_client,
        ):
            # Execute
            response = await get_documents()

            # Verify
            assert isinstance(response, DocumentsResponse)
            assert len(response.documents) == 2  # 2 unique documents (doc_123 appears twice)

            # Check document data (sorted by timestamp, newest first)
            doc_1 = next(d for d in response.documents if d.id == "doc_123")
            doc_2 = next(d for d in response.documents if d.id == "doc_456")

            assert doc_1.title == "Machine_Learning_Basics.pdf"  # Extracted from path
            assert doc_2.title == "Deep_Learning_Advanced.pdf"

            # Verify timestamps are converted correctly
            assert isinstance(doc_1.created_at, datetime)
            assert isinstance(doc_2.created_at, datetime)

    @pytest.mark.asyncio
    async def test_get_documents_empty(self, mock_qdrant_client):
        """Test document retrieval when no documents exist."""
        # Setup mock - return empty list
        mock_qdrant_client.async_client.scroll.return_value = ([], None)

        with patch(
            "src.api.v1.graph_communities.QdrantClient",
            return_value=mock_qdrant_client,
        ):
            # Execute
            response = await get_documents()

            # Verify
            assert isinstance(response, DocumentsResponse)
            assert len(response.documents) == 0

    @pytest.mark.asyncio
    async def test_get_documents_pagination(self, mock_qdrant_client):
        """Test document retrieval with pagination."""

        class Point:
            def __init__(self, doc_id, doc_path, timestamp):
                self.payload = {
                    "document_id": doc_id,
                    "document_path": doc_path,
                    "ingestion_timestamp": timestamp,
                }

        # Setup mock - return points in multiple batches
        batch_1 = [Point("doc_1", "/path/doc1.pdf", 1704106800.0)]
        batch_2 = [Point("doc_2", "/path/doc2.pdf", 1704106900.0)]

        mock_qdrant_client.async_client.scroll.side_effect = [
            (batch_1, "offset_1"),  # First batch with next offset
            (batch_2, None),  # Second batch, no more offsets
        ]

        with patch(
            "src.api.v1.graph_communities.QdrantClient",
            return_value=mock_qdrant_client,
        ):
            # Execute
            response = await get_documents()

            # Verify
            assert len(response.documents) == 2
            assert response.documents[0].title in ["doc1.pdf", "doc2.pdf"]
            assert mock_qdrant_client.async_client.scroll.call_count == 2

    @pytest.mark.asyncio
    async def test_get_documents_missing_payload(self, mock_qdrant_client):
        """Test document retrieval when points have missing payload data."""

        class Point:
            def __init__(self, payload):
                self.payload = payload

        # Setup mock - include points with missing data
        points = [
            Point({"document_id": "doc_1", "document_path": "/path/doc1.pdf", "ingestion_timestamp": 1704106800.0}),
            Point({}),  # Missing all fields
            Point({"document_id": "doc_2"}),  # Missing document_path
            Point({"document_path": "/path/doc3.pdf"}),  # Missing document_id
        ]

        mock_qdrant_client.async_client.scroll.return_value = (points, None)

        with patch(
            "src.api.v1.graph_communities.QdrantClient",
            return_value=mock_qdrant_client,
        ):
            # Execute
            response = await get_documents()

            # Verify - should only return the valid document
            assert len(response.documents) == 1
            assert response.documents[0].id == "doc_1"

    @pytest.mark.asyncio
    async def test_get_documents_database_error(self, mock_qdrant_client):
        """Test document retrieval when database query fails."""
        # Setup mock to raise exception
        mock_qdrant_client.async_client.scroll.side_effect = Exception("Qdrant connection failed")

        with patch(
            "src.api.v1.graph_communities.QdrantClient",
            return_value=mock_qdrant_client,
        ):
            # Execute and verify exception
            with pytest.raises(HTTPException) as exc_info:
                await get_documents()

            assert exc_info.value.status_code == 500
            assert "Failed to retrieve documents" in exc_info.value.detail


class TestGetDocumentSections:
    """Test GET /graph/documents/{doc_id}/sections endpoint."""

    @pytest.mark.asyncio
    async def test_get_sections_success(self, mock_neo4j_client, sample_sections):
        """Test successful section retrieval."""
        # Setup mock
        # First call: document exists check
        # Second call: get sections
        mock_neo4j_client.execute_query.side_effect = [
            [{"id": "doc_123"}],  # Document exists
            sample_sections,  # Sections
        ]

        with patch(
            "src.api.v1.graph_communities.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            # Execute
            response = await get_document_sections("doc_123")

            # Verify
            assert isinstance(response, SectionsResponse)
            assert response.document_id == "doc_123"
            assert len(response.sections) == 3
            assert response.sections[0].heading == "Introduction"
            assert response.sections[0].entity_count == 15
            assert response.sections[1].heading == "Methods"
            assert response.sections[2].heading == "Results"

    @pytest.mark.asyncio
    async def test_get_sections_document_not_found(self, mock_neo4j_client):
        """Test section retrieval when document doesn't exist."""
        # Setup mock - document doesn't exist
        mock_neo4j_client.execute_query.return_value = []

        with patch(
            "src.api.v1.graph_communities.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            # Execute and verify exception
            with pytest.raises(HTTPException) as exc_info:
                await get_document_sections("nonexistent_doc")

            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_sections_no_sections(self, mock_neo4j_client):
        """Test section retrieval when document has no sections."""
        # Setup mock
        mock_neo4j_client.execute_query.side_effect = [
            [{"id": "doc_123"}],  # Document exists
            [],  # No sections
        ]

        with patch(
            "src.api.v1.graph_communities.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            # Execute
            response = await get_document_sections("doc_123")

            # Verify
            assert isinstance(response, SectionsResponse)
            assert response.document_id == "doc_123"
            assert len(response.sections) == 0

    @pytest.mark.asyncio
    async def test_get_sections_database_error(self, mock_neo4j_client):
        """Test section retrieval when database query fails."""
        # Setup mock to raise exception on first query
        mock_neo4j_client.execute_query.side_effect = Exception("Database connection failed")

        with patch(
            "src.api.v1.graph_communities.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            # Execute and verify exception
            with pytest.raises(HTTPException) as exc_info:
                await get_document_sections("doc_123")

            assert exc_info.value.status_code == 500
            assert "Failed to retrieve document sections" in exc_info.value.detail


class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_document_metadata_validation(self):
        """Test DocumentMetadata model validation."""
        doc = DocumentMetadata(
            id="doc_123",
            title="Test Document",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            updated_at=datetime(2026, 1, 2, 15, 30, 0),
        )

        assert doc.id == "doc_123"
        assert doc.title == "Test Document"
        assert isinstance(doc.created_at, datetime)
        assert isinstance(doc.updated_at, datetime)

    def test_document_section_validation(self):
        """Test DocumentSection model validation."""
        section = DocumentSection(
            id="sec_1",
            heading="Introduction",
            level=1,
            entity_count=15,
            chunk_count=8,
        )

        assert section.id == "sec_1"
        assert section.heading == "Introduction"
        assert section.level == 1
        assert section.entity_count == 15
        assert section.chunk_count == 8

    def test_document_section_defaults(self):
        """Test DocumentSection default values."""
        section = DocumentSection(id="sec_1", heading="Test", level=1)

        assert section.entity_count == 0
        assert section.chunk_count == 0

    def test_documents_response_validation(self):
        """Test DocumentsResponse model validation."""
        response = DocumentsResponse(
            documents=[
                DocumentMetadata(
                    id="doc_1",
                    title="Doc 1",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            ]
        )

        assert len(response.documents) == 1
        assert response.documents[0].id == "doc_1"

    def test_sections_response_validation(self):
        """Test SectionsResponse model validation."""
        response = SectionsResponse(
            document_id="doc_123",
            sections=[
                DocumentSection(id="sec_1", heading="Intro", level=1),
                DocumentSection(id="sec_2", heading="Methods", level=1),
            ],
        )

        assert response.document_id == "doc_123"
        assert len(response.sections) == 2
        assert response.sections[0].heading == "Intro"
        assert response.sections[1].heading == "Methods"
