"""Index Consistency Validation for AegisRAG.

Sprint 49 Feature 49.6: Index Consistency Validation (TD-048)

This module provides validation to ensure consistency between vector store
(Qdrant) and knowledge graph (Neo4j). It detects:
- Orphaned entities (no source chunk in Qdrant)
- Orphaned chunks (no entities extracted in Neo4j)
- Missing source_chunk_id properties

Usage:
    from src.components.validation import validate_index_consistency

    report = await validate_index_consistency()
    print(f"Consistency Score: {report.consistency_score:.2f}")
    print(f"Orphaned Entities: {report.orphaned_entities_count}")

Author: Claude Code
Date: 2025-12-16
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog
from neo4j import AsyncGraphDatabase
from qdrant_client import AsyncQdrantClient

from src.core.config import settings

logger = structlog.get_logger(__name__)


class IssueType(str, Enum):
    """Types of consistency issues."""

    ORPHANED_ENTITY = "orphaned_entity"
    ORPHANED_CHUNK = "orphaned_chunk"
    MISSING_SOURCE_CHUNK_ID = "missing_source_chunk_id"
    CHUNK_NOT_IN_QDRANT = "chunk_not_in_qdrant"
    ENTITY_WITHOUT_CHUNK = "entity_without_chunk"


@dataclass
class ValidationIssue:
    """A single validation issue."""

    issue_type: IssueType
    severity: str  # "critical", "warning", "info"
    entity_id: str | None = None
    entity_name: str | None = None
    chunk_id: str | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "chunk_id": self.chunk_id,
            "message": self.message,
            "metadata": self.metadata,
        }


@dataclass
class ValidationReport:
    """Comprehensive validation report."""

    # Counts
    total_chunks: int = 0
    total_entities: int = 0
    total_relationships: int = 0

    # Issue counts
    orphaned_entities_count: int = 0
    orphaned_chunks_count: int = 0
    missing_source_chunk_id_count: int = 0

    # Consistency score (0.0 to 1.0)
    consistency_score: float = 0.0

    # Detailed issues
    issues: list[ValidationIssue] = field(default_factory=list)

    # Execution metadata
    execution_time_ms: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_chunks": self.total_chunks,
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships,
            "orphaned_entities_count": self.orphaned_entities_count,
            "orphaned_chunks_count": self.orphaned_chunks_count,
            "missing_source_chunk_id_count": self.missing_source_chunk_id_count,
            "consistency_score": self.consistency_score,
            "issues": [issue.to_dict() for issue in self.issues],
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp,
        }


class IndexConsistencyValidator:
    """Validator for consistency between Qdrant and Neo4j indexes."""

    def __init__(self):
        """Initialize validator."""
        self.qdrant_client = None
        self.neo4j_driver = None

    async def connect(self):
        """Connect to Qdrant and Neo4j."""
        # Qdrant connection
        self.qdrant_client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=30,
        )

        # Neo4j connection
        # Note: neo4j_password is SecretStr, need .get_secret_value()
        self.neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        )

        logger.info("validator_connected", qdrant_host=settings.qdrant_host)

    async def close(self):
        """Close connections."""
        if self.neo4j_driver:
            await self.neo4j_driver.close()
        logger.info("validator_connections_closed")

    async def validate(
        self,
        include_chunk_check: bool = True,
        max_issues: int = 1000,
    ) -> ValidationReport:
        """Validate index consistency.

        Args:
            include_chunk_check: Whether to check if chunks exist in Qdrant
            max_issues: Maximum number of issues to report (to prevent huge reports)

        Returns:
            ValidationReport with consistency metrics and detected issues
        """
        import time
        from datetime import datetime

        start_time = time.time()
        report = ValidationReport(timestamp=datetime.utcnow().isoformat())

        try:
            await self.connect()

            # Get counts
            report.total_chunks = await self._count_qdrant_chunks()
            report.total_entities = await self._count_neo4j_entities()
            report.total_relationships = await self._count_neo4j_relationships()

            logger.info(
                "validation_started",
                total_chunks=report.total_chunks,
                total_entities=report.total_entities,
                total_relationships=report.total_relationships,
            )

            # Check 1: Orphaned entities (entities without MENTIONED_IN relationships)
            orphaned_entities = await self._find_orphaned_entities(limit=max_issues)
            report.orphaned_entities_count = len(orphaned_entities)
            report.issues.extend(orphaned_entities)

            # Check 2: Orphaned chunks (chunks with no entities)
            if include_chunk_check:
                orphaned_chunks = await self._find_orphaned_chunks(limit=max_issues)
                report.orphaned_chunks_count = len(orphaned_chunks)
                report.issues.extend(orphaned_chunks)

            # Check 3: Missing source_chunk_id on relationships
            missing_source_chunk_id = await self._find_missing_source_chunk_id(limit=max_issues)
            report.missing_source_chunk_id_count = len(missing_source_chunk_id)
            report.issues.extend(missing_source_chunk_id)

            # Calculate consistency score
            report.consistency_score = self._calculate_consistency_score(report)

            report.execution_time_ms = (time.time() - start_time) * 1000

            logger.info(
                "validation_completed",
                consistency_score=report.consistency_score,
                orphaned_entities=report.orphaned_entities_count,
                orphaned_chunks=report.orphaned_chunks_count,
                missing_source_chunk_id=report.missing_source_chunk_id_count,
                execution_time_ms=report.execution_time_ms,
            )

            return report

        except Exception as e:
            logger.error("validation_failed", error=str(e), error_type=type(e).__name__)
            raise
        finally:
            await self.close()

    async def _count_qdrant_chunks(self) -> int:
        """Count total chunks in Qdrant."""
        try:
            collection_info = await self.qdrant_client.get_collection(
                settings.qdrant_collection
            )
            return collection_info.points_count
        except Exception as e:
            logger.warning("count_qdrant_chunks_failed", error=str(e))
            return 0

    async def _count_neo4j_entities(self) -> int:
        """Count total entities in Neo4j."""
        async with self.neo4j_driver.session() as session:
            result = await session.run("MATCH (e:base) RETURN count(e) AS count")
            record = await result.single()
            return record["count"] if record else 0

    async def _count_neo4j_relationships(self) -> int:
        """Count total relationships in Neo4j."""
        async with self.neo4j_driver.session() as session:
            result = await session.run("MATCH ()-[r]->() RETURN count(r) AS count")
            record = await result.single()
            return record["count"] if record else 0

    async def _find_orphaned_entities(self, limit: int = 1000) -> list[ValidationIssue]:
        """Find entities that have no MENTIONED_IN relationships.

        These are entities that were extracted but have no provenance link
        to a source chunk. This indicates a data integrity issue.

        Args:
            limit: Maximum number of issues to return

        Returns:
            List of ValidationIssue objects
        """
        issues = []

        async with self.neo4j_driver.session() as session:
            result = await session.run(
                f"""
                MATCH (e:base)
                WHERE NOT (e)-[:MENTIONED_IN]->(:chunk)
                RETURN e.entity_id AS entity_id,
                       e.entity_name AS entity_name,
                       e.entity_type AS entity_type,
                       labels(e) AS labels
                LIMIT {limit}
            """
            )

            async for record in result:
                issue = ValidationIssue(
                    issue_type=IssueType.ENTITY_WITHOUT_CHUNK,
                    severity="critical",
                    entity_id=record["entity_id"],
                    entity_name=record["entity_name"],
                    message=f"Entity '{record['entity_name']}' has no MENTIONED_IN relationship",
                    metadata={
                        "entity_type": record["entity_type"],
                        "labels": record["labels"],
                    },
                )
                issues.append(issue)

        return issues

    async def _find_orphaned_chunks(self, limit: int = 1000) -> list[ValidationIssue]:
        """Find chunks that have no entities mentioning them.

        These are chunks that were indexed but no entities were extracted.
        This could indicate:
        - Empty/noise chunks
        - Extraction failure
        - Chunks with only relations (no entities)

        Args:
            limit: Maximum number of issues to return

        Returns:
            List of ValidationIssue objects
        """
        issues = []

        async with self.neo4j_driver.session() as session:
            result = await session.run(
                f"""
                MATCH (c:chunk)
                WHERE NOT ()-[:MENTIONED_IN]->(c)
                RETURN c.chunk_id AS chunk_id,
                       c.document_id AS document_id,
                       c.chunk_index AS chunk_index,
                       substring(c.text, 0, 100) AS text_preview
                LIMIT {limit}
            """
            )

            async for record in result:
                issue = ValidationIssue(
                    issue_type=IssueType.ORPHANED_CHUNK,
                    severity="warning",
                    chunk_id=record["chunk_id"],
                    message=f"Chunk {record['chunk_id'][:16]}... has no entities",
                    metadata={
                        "document_id": record["document_id"],
                        "chunk_index": record["chunk_index"],
                        "text_preview": record["text_preview"],
                    },
                )
                issues.append(issue)

        return issues

    async def _find_missing_source_chunk_id(self, limit: int = 1000) -> list[ValidationIssue]:
        """Find relationships without source_chunk_id property.

        This indicates relationships created before Sprint 49 Feature 49.5.

        Args:
            limit: Maximum number of issues to return

        Returns:
            List of ValidationIssue objects
        """
        issues = []

        async with self.neo4j_driver.session() as session:
            # Check MENTIONED_IN relationships
            result = await session.run(
                f"""
                MATCH (e:base)-[r:MENTIONED_IN]->(c:chunk)
                WHERE r.source_chunk_id IS NULL
                RETURN e.entity_id AS entity_id,
                       e.entity_name AS entity_name,
                       c.chunk_id AS chunk_id,
                       'MENTIONED_IN' AS rel_type
                LIMIT {limit // 2}
            """
            )

            async for record in result:
                issue = ValidationIssue(
                    issue_type=IssueType.MISSING_SOURCE_CHUNK_ID,
                    severity="warning",
                    entity_id=record["entity_id"],
                    entity_name=record["entity_name"],
                    chunk_id=record["chunk_id"],
                    message="MENTIONED_IN relationship missing source_chunk_id",
                    metadata={"rel_type": record["rel_type"]},
                )
                issues.append(issue)

            # Check RELATES_TO relationships
            result = await session.run(
                f"""
                MATCH (e1:base)-[r:RELATES_TO]->(e2:base)
                WHERE r.source_chunk_id IS NULL
                RETURN e1.entity_id AS entity_id,
                       e1.entity_name AS entity_name,
                       e2.entity_name AS target_name,
                       'RELATES_TO' AS rel_type
                LIMIT {limit // 2}
            """
            )

            async for record in result:
                issue = ValidationIssue(
                    issue_type=IssueType.MISSING_SOURCE_CHUNK_ID,
                    severity="warning",
                    entity_id=record["entity_id"],
                    entity_name=record["entity_name"],
                    message="RELATES_TO relationship missing source_chunk_id",
                    metadata={
                        "rel_type": record["rel_type"],
                        "target_entity": record["target_name"],
                    },
                )
                issues.append(issue)

        return issues

    def _calculate_consistency_score(self, report: ValidationReport) -> float:
        """Calculate overall consistency score (0.0 to 1.0).

        Formula:
            score = 1.0 - (weighted_issues / total_elements)

        Weights:
            - Orphaned entity: 1.0 (critical)
            - Orphaned chunk: 0.3 (warning, less critical)
            - Missing source_chunk_id: 0.5 (should be fixed but not urgent)

        Args:
            report: Validation report with issue counts

        Returns:
            Consistency score between 0.0 (bad) and 1.0 (perfect)
        """
        total_elements = report.total_entities + report.total_chunks

        if total_elements == 0:
            return 1.0  # Empty index is consistent

        weighted_issues = (
            report.orphaned_entities_count * 1.0
            + report.orphaned_chunks_count * 0.3
            + report.missing_source_chunk_id_count * 0.5
        )

        score = max(0.0, 1.0 - (weighted_issues / total_elements))
        return round(score, 3)


async def validate_index_consistency(
    include_chunk_check: bool = True,
    max_issues: int = 1000,
) -> ValidationReport:
    """Convenience function to validate index consistency.

    Args:
        include_chunk_check: Whether to check if chunks exist in Qdrant
        max_issues: Maximum number of issues to report

    Returns:
        ValidationReport with consistency metrics

    Example:
        >>> report = await validate_index_consistency()
        >>> print(f"Consistency: {report.consistency_score:.2%}")
        >>> if report.orphaned_entities_count > 0:
        >>>     print(f"⚠ {report.orphaned_entities_count} orphaned entities found")
    """
    validator = IndexConsistencyValidator()
    return await validator.validate(
        include_chunk_check=include_chunk_check,
        max_issues=max_issues,
    )


async def fix_orphaned_entities(dry_run: bool = True) -> dict[str, int]:
    """Delete orphaned entities (entities without MENTIONED_IN relationships).

    Args:
        dry_run: If True, only report what would be deleted

    Returns:
        Statistics dictionary with counts
    """
    neo4j_driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
    )

    try:
        async with neo4j_driver.session() as session:
            # Count orphaned entities
            result = await session.run(
                """
                MATCH (e:base)
                WHERE NOT (e)-[:MENTIONED_IN]->(:chunk)
                RETURN count(e) AS count
            """
            )
            record = await result.single()
            orphaned_count = record["count"] if record else 0

            logger.info("orphaned_entities_found", count=orphaned_count, dry_run=dry_run)

            if dry_run:
                return {"orphaned_count": orphaned_count, "deleted": 0}

            # Delete orphaned entities
            result = await session.run(
                """
                MATCH (e:base)
                WHERE NOT (e)-[:MENTIONED_IN]->(:chunk)
                DETACH DELETE e
                RETURN count(e) AS deleted
            """
            )
            record = await result.single()
            deleted = record["deleted"] if record else 0

            logger.info("orphaned_entities_deleted", deleted=deleted)

            return {"orphaned_count": orphaned_count, "deleted": deleted}

    finally:
        await neo4j_driver.close()


async def fix_orphaned_chunks(dry_run: bool = True) -> dict[str, int]:
    """Delete orphaned chunks (chunks with no entities).

    Args:
        dry_run: If True, only report what would be deleted

    Returns:
        Statistics dictionary with counts
    """
    neo4j_driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
    )

    try:
        async with neo4j_driver.session() as session:
            # Count orphaned chunks
            result = await session.run(
                """
                MATCH (c:chunk)
                WHERE NOT ()-[:MENTIONED_IN]->(c)
                RETURN count(c) AS count
            """
            )
            record = await result.single()
            orphaned_count = record["count"] if record else 0

            logger.info("orphaned_chunks_found", count=orphaned_count, dry_run=dry_run)

            if dry_run:
                return {"orphaned_count": orphaned_count, "deleted": 0}

            # Delete orphaned chunks
            result = await session.run(
                """
                MATCH (c:chunk)
                WHERE NOT ()-[:MENTIONED_IN]->(c)
                DELETE c
                RETURN count(c) AS deleted
            """
            )
            record = await result.single()
            deleted = record["deleted"] if record else 0

            logger.info("orphaned_chunks_deleted", deleted=deleted)

            return {"orphaned_count": orphaned_count, "deleted": deleted}

    finally:
        await neo4j_driver.close()
