"""Domain Override Service for Manual Domain Classification Changes.

Sprint 117 Feature 117.11: Manual Domain Override.

This module provides functionality to manually override automatically detected
domain classifications, with full audit trail logging and optional re-extraction
of entities using the new domain's prompts.

Key Features:
- Manual domain override with audit logging
- Previous/new domain tracking
- User attribution (who, when, why)
- Optional re-extraction with new domain prompts
- Full transaction support for rollback safety

Architecture:
    DomainOverrideService → Neo4j (BELONGS_TO_DOMAIN update)
    ├── Audit trail (who, when, why, previous/new domains)
    ├── Background re-extraction (optional)
    └── Transaction support (rollback on failure)

Usage:
    >>> from src.components.domain_training import get_domain_override_service
    >>> service = get_domain_override_service()
    >>> result = await service.override_document_domain(
    ...     document_id="doc_abc123",
    ...     new_domain_id="medical",
    ...     reason="Document contains medical terminology",
    ...     reprocess_extraction=True,
    ...     user_id="admin"
    ... )
    >>> print(result)  # DomainOverrideResponse with audit trail
"""

import uuid
from datetime import datetime
from typing import Any

import structlog
from neo4j import AsyncTransaction

from src.components.domain_training.domain_repository import get_domain_repository
from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.core.exceptions import DatabaseConnectionError
from src.core.models.domain_override import (
    DomainInfo,
    DomainOverrideResponse,
    ReprocessingInfo,
)

logger = structlog.get_logger(__name__)


class DomainOverrideService:
    """Service for manual domain override with audit logging.

    This service manages manual overrides of automatically detected domain
    classifications. It provides full audit trail logging and supports
    optional re-extraction of entities using the new domain's prompts.

    Attributes:
        neo4j_client: Neo4j client for database operations
        domain_repository: Domain repository for domain lookups
    """

    def __init__(self) -> None:
        """Initialize domain override service."""
        self.neo4j_client = get_neo4j_client()
        self.domain_repository = get_domain_repository()
        logger.info("domain_override_service_initialized")

    async def override_document_domain(
        self,
        document_id: str,
        new_domain_id: str,
        reason: str | None = None,
        reprocess_extraction: bool = False,
        user_id: str = "system",
    ) -> DomainOverrideResponse:
        """Override document domain classification with audit logging.

        This method updates the document's BELONGS_TO_DOMAIN relationship to
        point to a new domain, logs the override for audit purposes, and
        optionally triggers re-extraction with the new domain's prompts.

        Args:
            document_id: Document ID to override
            new_domain_id: New domain ID to assign
            reason: Optional reason for override (audit trail)
            reprocess_extraction: Whether to re-run entity extraction
            user_id: User performing the override (default: "system")

        Returns:
            DomainOverrideResponse with previous/new domain info and reprocessing status

        Raises:
            ValueError: If document or domain not found
            DatabaseConnectionError: If database operation fails
        """
        logger.info(
            "overriding_document_domain",
            document_id=document_id,
            new_domain_id=new_domain_id,
            reprocess_extraction=reprocess_extraction,
            user_id=user_id,
        )

        # 1. Validate that new domain exists
        new_domain = await self.domain_repository.get_domain(new_domain_id)
        if not new_domain:
            raise ValueError(f"Domain '{new_domain_id}' not found")

        # 2. Get current document and domain info
        previous_domain_info = await self._get_document_domain_info(document_id)
        if not previous_domain_info:
            raise ValueError(f"Document '{document_id}' not found")

        # 3. Perform domain override in transaction
        try:
            async with self.domain_repository.transaction() as tx:
                await self._update_domain_relationship(
                    document_id=document_id,
                    new_domain_id=new_domain_id,
                    user_id=user_id,
                    reason=reason,
                    tx=tx,
                )

                # Log audit trail
                await self._log_domain_override_audit(
                    document_id=document_id,
                    previous_domain_id=previous_domain_info["domain_id"],
                    new_domain_id=new_domain_id,
                    user_id=user_id,
                    reason=reason,
                    tx=tx,
                )

            logger.info(
                "document_domain_overridden",
                document_id=document_id,
                previous_domain=previous_domain_info["domain_id"],
                new_domain=new_domain_id,
            )

        except Exception as e:
            logger.error(
                "domain_override_failed",
                document_id=document_id,
                new_domain_id=new_domain_id,
                error=str(e),
            )
            raise DatabaseConnectionError("Neo4j", f"Domain override failed: {e}") from e

        # 4. Build response with previous/new domain info
        now = datetime.utcnow()

        previous_domain = DomainInfo(
            domain_id=previous_domain_info["domain_id"],
            domain_name=previous_domain_info["domain_name"],
            confidence=previous_domain_info.get("confidence"),
            classification_path=previous_domain_info.get("classification_path", "auto"),
            overridden_by=None,
            overridden_at=None,
        )

        new_domain_info = DomainInfo(
            domain_id=new_domain_id,
            domain_name=new_domain["name"],
            confidence=None,  # Manual override has no confidence score
            classification_path="manual_override",
            overridden_by=user_id,
            overridden_at=now,
        )

        # 5. Trigger re-extraction if requested
        reprocessing_info = None
        if reprocess_extraction:
            job_id = await self._trigger_reextraction(document_id, new_domain_id)
            reprocessing_info = ReprocessingInfo(
                status="pending",
                job_id=job_id,
            )

        return DomainOverrideResponse(
            document_id=document_id,
            previous_domain=previous_domain,
            new_domain=new_domain_info,
            reprocessing=reprocessing_info,
        )

    async def _get_document_domain_info(self, document_id: str) -> dict[str, Any] | None:
        """Get current domain information for a document.

        Args:
            document_id: Document ID

        Returns:
            Dictionary with domain_id, domain_name, confidence, classification_path
            or None if document not found

        Raises:
            DatabaseConnectionError: If query fails
        """
        logger.info("getting_document_domain_info", document_id=document_id)

        try:
            result = await self.neo4j_client.execute_read(
                """
                MATCH (doc:Document {id: $document_id})-[:BELONGS_TO_DOMAIN]->(d:Domain)
                RETURN d.id as domain_id, d.name as domain_name,
                       doc.domain_confidence as confidence,
                       doc.domain_classification_path as classification_path
                """,
                {"document_id": document_id},
            )

            if not result:
                logger.warning("document_not_found", document_id=document_id)
                return None

            domain_info = {
                "domain_id": result[0]["domain_name"],  # Use domain name as ID
                "domain_name": result[0]["domain_name"],
                "confidence": result[0].get("confidence"),
                "classification_path": result[0].get("classification_path", "auto"),
            }

            logger.info(
                "document_domain_info_retrieved", document_id=document_id, domain=domain_info
            )
            return domain_info

        except Exception as e:
            logger.error("get_document_domain_info_failed", document_id=document_id, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Get document domain info failed: {e}") from e

    async def _update_domain_relationship(
        self,
        document_id: str,
        new_domain_id: str,
        user_id: str,
        reason: str | None,
        tx: AsyncTransaction,
    ) -> None:
        """Update document's BELONGS_TO_DOMAIN relationship to new domain.

        Args:
            document_id: Document ID
            new_domain_id: New domain ID
            user_id: User performing the override
            reason: Optional reason for override
            tx: Neo4j transaction for rollback support

        Raises:
            DatabaseConnectionError: If update fails
        """
        logger.info(
            "updating_domain_relationship",
            document_id=document_id,
            new_domain_id=new_domain_id,
        )

        now = datetime.utcnow().isoformat()

        try:
            # Delete old BELONGS_TO_DOMAIN relationship and create new one
            query = """
            MATCH (doc:Document {id: $document_id})-[r:BELONGS_TO_DOMAIN]->(old_domain:Domain)
            MATCH (new_domain:Domain {name: $new_domain_id})
            DELETE r
            CREATE (doc)-[:BELONGS_TO_DOMAIN {
                created_at: datetime($created_at),
                overridden_by: $user_id,
                override_reason: $reason,
                classification_path: 'manual_override'
            }]->(new_domain)
            SET doc.domain_classification_path = 'manual_override',
                doc.domain_override_at = datetime($created_at),
                doc.domain_override_by = $user_id,
                doc.updated_at = datetime($created_at)
            RETURN doc.id as id
            """

            await tx.run(
                query,
                {
                    "document_id": document_id,
                    "new_domain_id": new_domain_id,
                    "user_id": user_id,
                    "reason": reason,
                    "created_at": now,
                },
            )

            logger.info(
                "domain_relationship_updated",
                document_id=document_id,
                new_domain=new_domain_id,
            )

        except Exception as e:
            logger.error(
                "update_domain_relationship_failed",
                document_id=document_id,
                new_domain_id=new_domain_id,
                error=str(e),
            )
            raise DatabaseConnectionError("Neo4j", f"Update domain relationship failed: {e}") from e

    async def _log_domain_override_audit(
        self,
        document_id: str,
        previous_domain_id: str,
        new_domain_id: str,
        user_id: str,
        reason: str | None,
        tx: AsyncTransaction,
    ) -> None:
        """Log domain override to audit trail.

        Creates a DomainOverrideAudit node for compliance and tracking.

        Args:
            document_id: Document ID
            previous_domain_id: Previous domain ID
            new_domain_id: New domain ID
            user_id: User performing the override
            reason: Optional reason for override
            tx: Neo4j transaction for rollback support

        Raises:
            DatabaseConnectionError: If audit logging fails
        """
        logger.info(
            "logging_domain_override_audit",
            document_id=document_id,
            previous_domain=previous_domain_id,
            new_domain=new_domain_id,
        )

        audit_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        try:
            query = """
            MATCH (doc:Document {id: $document_id})
            CREATE (audit:DomainOverrideAudit {
                id: $audit_id,
                document_id: $document_id,
                previous_domain: $previous_domain_id,
                new_domain: $new_domain_id,
                user_id: $user_id,
                reason: $reason,
                timestamp: datetime($timestamp)
            })
            CREATE (doc)-[:HAS_AUDIT_LOG]->(audit)
            RETURN audit.id as id
            """

            await tx.run(
                query,
                {
                    "audit_id": audit_id,
                    "document_id": document_id,
                    "previous_domain_id": previous_domain_id,
                    "new_domain_id": new_domain_id,
                    "user_id": user_id,
                    "reason": reason,
                    "timestamp": now,
                },
            )

            logger.info(
                "domain_override_audit_logged",
                audit_id=audit_id,
                document_id=document_id,
            )

        except Exception as e:
            logger.error(
                "log_domain_override_audit_failed",
                document_id=document_id,
                error=str(e),
            )
            raise DatabaseConnectionError("Neo4j", f"Audit logging failed: {e}") from e

    async def _trigger_reextraction(self, document_id: str, new_domain_id: str) -> str:
        """Trigger background re-extraction with new domain prompts.

        Args:
            document_id: Document ID
            new_domain_id: New domain ID

        Returns:
            Job ID for tracking re-extraction

        Raises:
            DatabaseConnectionError: If re-extraction trigger fails
        """
        logger.info(
            "triggering_reextraction",
            document_id=document_id,
            new_domain_id=new_domain_id,
        )

        # TODO Sprint 117.11: Implement background re-extraction job
        # This would integrate with BackgroundJobManager from background_jobs.py
        # For now, return a placeholder job ID
        job_id = f"reextract_{document_id}_{uuid.uuid4().hex[:8]}"

        logger.info(
            "reextraction_triggered",
            document_id=document_id,
            new_domain_id=new_domain_id,
            job_id=job_id,
        )

        return job_id

    async def get_domain_override_history(
        self, document_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get domain override history for a document.

        Args:
            document_id: Document ID
            limit: Maximum number of audit entries to return (default: 10)

        Returns:
            List of audit entries sorted by timestamp (newest first)

        Raises:
            DatabaseConnectionError: If query fails
        """
        logger.info("getting_domain_override_history", document_id=document_id, limit=limit)

        try:
            result = await self.neo4j_client.execute_read(
                """
                MATCH (doc:Document {id: $document_id})-[:HAS_AUDIT_LOG]->(audit:DomainOverrideAudit)
                RETURN audit.id as id, audit.previous_domain as previous_domain,
                       audit.new_domain as new_domain, audit.user_id as user_id,
                       audit.reason as reason, audit.timestamp as timestamp
                ORDER BY audit.timestamp DESC
                LIMIT $limit
                """,
                {"document_id": document_id, "limit": limit},
            )

            logger.info(
                "domain_override_history_retrieved",
                document_id=document_id,
                entries_count=len(result),
            )

            return result

        except Exception as e:
            logger.error(
                "get_domain_override_history_failed",
                document_id=document_id,
                error=str(e),
            )
            raise DatabaseConnectionError("Neo4j", f"Get override history failed: {e}") from e


# Global instance (singleton pattern)
_domain_override_service: DomainOverrideService | None = None


def get_domain_override_service() -> DomainOverrideService:
    """Get global domain override service instance (singleton).

    Returns:
        DomainOverrideService instance
    """
    global _domain_override_service
    if _domain_override_service is None:
        _domain_override_service = DomainOverrideService()
    return _domain_override_service
