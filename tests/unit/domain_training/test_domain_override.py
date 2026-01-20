"""Unit tests for Domain Override Service.

Sprint 117 Feature 117.11: Manual Domain Override.

Tests cover:
- Domain override with audit logging
- Previous/new domain info tracking
- Validation of document and domain existence
- Re-extraction trigger
- Override history retrieval
- Error handling and rollback
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.domain_training.domain_override_service import (
    DomainOverrideService,
    get_domain_override_service,
)
from src.core.exceptions import DatabaseConnectionError
from src.core.models.domain_override import DomainInfo, DomainOverrideResponse, ReprocessingInfo


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client for database operations."""
    client = MagicMock()
    client.execute_read = AsyncMock()
    client.execute_write = AsyncMock()
    client.execute_query = AsyncMock()
    return client


@pytest.fixture
def mock_domain_repository():
    """Mock domain repository for domain lookups."""
    repo = MagicMock()
    repo.get_domain = AsyncMock()
    repo.transaction = MagicMock()
    return repo


@pytest.fixture
def mock_transaction():
    """Mock Neo4j transaction for rollback support."""
    tx = AsyncMock()
    tx.run = AsyncMock()
    return tx


@pytest.fixture
def service(mock_neo4j_client, mock_domain_repository):
    """Create DomainOverrideService with mocked dependencies."""
    with (
        patch(
            "src.components.domain_training.domain_override_service.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.domain_training.domain_override_service.get_domain_repository",
            return_value=mock_domain_repository,
        ),
    ):
        return DomainOverrideService()


class TestDomainOverrideService:
    """Test suite for DomainOverrideService."""

    @pytest.mark.asyncio
    async def test_override_document_domain_success(self, service, mock_domain_repository, mock_transaction):
        """Test successful domain override with audit logging."""
        # Setup
        document_id = "doc_abc123"
        new_domain_id = "medical"
        reason = "Document contains medical terminology"
        user_id = "admin"

        # Mock domain existence check
        mock_domain_repository.get_domain.return_value = {
            "id": "medical_id",
            "name": "medical",
            "description": "Medical domain",
            "status": "ready",
        }

        # Mock document domain info retrieval
        service._get_document_domain_info = AsyncMock(
            return_value={
                "domain_id": "general",
                "domain_name": "general",
                "confidence": 0.42,
                "classification_path": "auto",
            }
        )

        # Mock transaction context manager
        mock_domain_repository.transaction.return_value.__aenter__.return_value = mock_transaction

        # Mock update and audit methods
        service._update_domain_relationship = AsyncMock()
        service._log_domain_override_audit = AsyncMock()

        # Execute
        result = await service.override_document_domain(
            document_id=document_id,
            new_domain_id=new_domain_id,
            reason=reason,
            reprocess_extraction=False,
            user_id=user_id,
        )

        # Assert
        assert isinstance(result, DomainOverrideResponse)
        assert result.document_id == document_id
        assert result.previous_domain.domain_id == "general"
        assert result.previous_domain.confidence == 0.42
        assert result.new_domain.domain_id == new_domain_id
        assert result.new_domain.classification_path == "manual_override"
        assert result.new_domain.overridden_by == user_id
        assert result.reprocessing is None

        # Verify domain existence check
        mock_domain_repository.get_domain.assert_called_once_with(new_domain_id)

        # Verify document domain info retrieval
        service._get_document_domain_info.assert_called_once_with(document_id)

        # Verify update and audit calls
        service._update_domain_relationship.assert_called_once()
        service._log_domain_override_audit.assert_called_once()

    @pytest.mark.asyncio
    async def test_override_document_domain_with_reprocessing(
        self, service, mock_domain_repository, mock_transaction
    ):
        """Test domain override with re-extraction trigger."""
        # Setup
        document_id = "doc_abc123"
        new_domain_id = "medical"

        # Mock domain existence check
        mock_domain_repository.get_domain.return_value = {"name": "medical"}

        # Mock document domain info retrieval
        service._get_document_domain_info = AsyncMock(
            return_value={
                "domain_id": "general",
                "domain_name": "general",
                "confidence": 0.42,
                "classification_path": "auto",
            }
        )

        # Mock transaction context manager
        mock_domain_repository.transaction.return_value.__aenter__.return_value = mock_transaction

        # Mock update, audit, and reprocessing methods
        service._update_domain_relationship = AsyncMock()
        service._log_domain_override_audit = AsyncMock()
        service._trigger_reextraction = AsyncMock(return_value="job_123")

        # Execute
        result = await service.override_document_domain(
            document_id=document_id,
            new_domain_id=new_domain_id,
            reprocess_extraction=True,
        )

        # Assert
        assert result.reprocessing is not None
        assert result.reprocessing.status == "pending"
        assert result.reprocessing.job_id == "job_123"

        # Verify re-extraction trigger
        service._trigger_reextraction.assert_called_once_with(document_id, new_domain_id)

    @pytest.mark.asyncio
    async def test_override_document_domain_invalid_domain(self, service, mock_domain_repository):
        """Test domain override with non-existent domain."""
        # Setup
        document_id = "doc_abc123"
        new_domain_id = "nonexistent"

        # Mock domain not found
        mock_domain_repository.get_domain.return_value = None

        # Execute & Assert
        with pytest.raises(ValueError, match="Domain 'nonexistent' not found"):
            await service.override_document_domain(
                document_id=document_id,
                new_domain_id=new_domain_id,
            )

    @pytest.mark.asyncio
    async def test_override_document_domain_invalid_document(
        self, service, mock_domain_repository
    ):
        """Test domain override with non-existent document."""
        # Setup
        document_id = "nonexistent_doc"
        new_domain_id = "medical"

        # Mock domain exists
        mock_domain_repository.get_domain.return_value = {"name": "medical"}

        # Mock document not found
        service._get_document_domain_info = AsyncMock(return_value=None)

        # Execute & Assert
        with pytest.raises(ValueError, match="Document 'nonexistent_doc' not found"):
            await service.override_document_domain(
                document_id=document_id,
                new_domain_id=new_domain_id,
            )

    @pytest.mark.asyncio
    async def test_get_document_domain_info_success(self, service):
        """Test successful document domain info retrieval."""
        # Setup
        document_id = "doc_abc123"

        service.neo4j_client.execute_read.return_value = [
            {
                "domain_name": "medical",
                "confidence": 0.85,
                "classification_path": "auto",
            }
        ]

        # Execute
        result = await service._get_document_domain_info(document_id)

        # Assert
        assert result is not None
        assert result["domain_id"] == "medical"
        assert result["domain_name"] == "medical"
        assert result["confidence"] == 0.85
        assert result["classification_path"] == "auto"

    @pytest.mark.asyncio
    async def test_get_document_domain_info_not_found(self, service):
        """Test document domain info retrieval for non-existent document."""
        # Setup
        document_id = "nonexistent_doc"

        service.neo4j_client.execute_read.return_value = []

        # Execute
        result = await service._get_document_domain_info(document_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_domain_relationship_success(self, service, mock_transaction):
        """Test successful domain relationship update."""
        # Setup
        document_id = "doc_abc123"
        new_domain_id = "medical"
        user_id = "admin"
        reason = "Medical terminology"

        # Execute
        await service._update_domain_relationship(
            document_id=document_id,
            new_domain_id=new_domain_id,
            user_id=user_id,
            reason=reason,
            tx=mock_transaction,
        )

        # Assert
        mock_transaction.run.assert_called_once()
        call_args = mock_transaction.run.call_args
        assert document_id in str(call_args)
        assert new_domain_id in str(call_args)

    @pytest.mark.asyncio
    async def test_log_domain_override_audit_success(self, service, mock_transaction):
        """Test successful audit trail logging."""
        # Setup
        document_id = "doc_abc123"
        previous_domain_id = "general"
        new_domain_id = "medical"
        user_id = "admin"
        reason = "Medical terminology"

        # Execute
        await service._log_domain_override_audit(
            document_id=document_id,
            previous_domain_id=previous_domain_id,
            new_domain_id=new_domain_id,
            user_id=user_id,
            reason=reason,
            tx=mock_transaction,
        )

        # Assert
        mock_transaction.run.assert_called_once()
        call_args = mock_transaction.run.call_args
        assert "DomainOverrideAudit" in str(call_args)
        assert document_id in str(call_args)

    @pytest.mark.asyncio
    async def test_trigger_reextraction(self, service):
        """Test re-extraction job trigger."""
        # Setup
        document_id = "doc_abc123"
        new_domain_id = "medical"

        # Execute
        job_id = await service._trigger_reextraction(document_id, new_domain_id)

        # Assert
        assert job_id is not None
        assert job_id.startswith("reextract_")
        assert document_id in job_id

    @pytest.mark.asyncio
    async def test_get_domain_override_history_success(self, service):
        """Test domain override history retrieval."""
        # Setup
        document_id = "doc_abc123"

        service.neo4j_client.execute_read.return_value = [
            {
                "id": "audit_1",
                "previous_domain": "general",
                "new_domain": "medical",
                "user_id": "admin",
                "reason": "Medical terminology",
                "timestamp": datetime.utcnow(),
            },
            {
                "id": "audit_2",
                "previous_domain": "legal",
                "new_domain": "general",
                "user_id": "admin",
                "reason": "Incorrect classification",
                "timestamp": datetime.utcnow(),
            },
        ]

        # Execute
        result = await service.get_domain_override_history(document_id, limit=10)

        # Assert
        assert len(result) == 2
        assert result[0]["previous_domain"] == "general"
        assert result[0]["new_domain"] == "medical"

    @pytest.mark.asyncio
    async def test_get_domain_override_history_empty(self, service):
        """Test domain override history retrieval with no history."""
        # Setup
        document_id = "doc_abc123"

        service.neo4j_client.execute_read.return_value = []

        # Execute
        result = await service.get_domain_override_history(document_id, limit=10)

        # Assert
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_database_error_handling(self, service, mock_domain_repository, mock_transaction):
        """Test database error handling with rollback."""
        # Setup
        document_id = "doc_abc123"
        new_domain_id = "medical"

        # Mock domain exists
        mock_domain_repository.get_domain.return_value = {"name": "medical"}

        # Mock document domain info retrieval
        service._get_document_domain_info = AsyncMock(
            return_value={
                "domain_id": "general",
                "domain_name": "general",
                "confidence": 0.42,
                "classification_path": "auto",
            }
        )

        # Mock transaction context manager that raises exception
        mock_domain_repository.transaction.return_value.__aenter__.return_value = mock_transaction
        service._update_domain_relationship = AsyncMock(
            side_effect=DatabaseConnectionError("Neo4j", "Connection failed")
        )

        # Execute & Assert
        with pytest.raises(DatabaseConnectionError):
            await service.override_document_domain(
                document_id=document_id,
                new_domain_id=new_domain_id,
            )


class TestSingletonPattern:
    """Test singleton pattern for DomainOverrideService."""

    def test_get_domain_override_service_singleton(self):
        """Test that get_domain_override_service returns same instance."""
        with (
            patch(
                "src.components.domain_training.domain_override_service.get_neo4j_client"
            ),
            patch(
                "src.components.domain_training.domain_override_service.get_domain_repository"
            ),
        ):
            service1 = get_domain_override_service()
            service2 = get_domain_override_service()

            assert service1 is service2
