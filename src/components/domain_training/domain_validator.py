"""Domain Validation Service for Quality Assurance.

Sprint 117 - Feature 117.7: Domain Validation (5 SP)

This module provides comprehensive domain validation to ensure data quality
and readiness for production use. It checks training samples, entity/relation
coverage, provenance links, model training status, and more.

Validation Checks:
    1. Training Samples Count - Minimum 20 samples
    2. Entity Type Coverage - All entity types have samples
    3. Relation Type Coverage - All relation types have samples
    4. MENTIONED_IN Relations - Provenance links exist
    5. Model Trained - DSPy prompts optimized
    6. Confidence Calibration - Threshold makes sense
    7. Recent Activity - Domain used recently

Health Score Calculation:
    - Pass = 100 points
    - Warning = 50 points
    - Fail = 0 points
    - Health Score = average of all checks

Example:
    >>> validator = get_domain_validator()
    >>> result = await validator.validate_domain("medical")
    >>> print(f"Health Score: {result['health_score']}")
    >>> print(f"Status: {result['validation_status']}")
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.components.domain_training.domain_repository import get_domain_repository
from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.core.exceptions import DatabaseConnectionError

logger = structlog.get_logger(__name__)

# Constants
MIN_TRAINING_SAMPLES = 20
MIN_ENTITY_TYPE_SAMPLES = 5
MIN_RELATION_TYPE_SAMPLES = 5
RECENT_ACTIVITY_DAYS = 30
MAX_RETRY_ATTEMPTS = 3


class ValidationStatus(str, Enum):
    """Validation status for individual checks and overall validation."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class IssueSeverity(str, Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueCategory(str, Enum):
    """Category of validation issue."""

    COVERAGE = "coverage"
    MODEL = "model"
    CALIBRATION = "calibration"
    ACTIVITY = "activity"
    PROVENANCE = "provenance"


class ValidationCheck:
    """Individual validation check result.

    Attributes:
        name: Check name (e.g., "training_samples_count")
        status: ValidationStatus (pass/warning/fail)
        message: Human-readable message
        details: Additional details (counts, lists, etc.)
    """

    def __init__(
        self,
        name: str,
        status: ValidationStatus,
        message: str,
        details: dict[str, Any],
    ) -> None:
        """Initialize validation check.

        Args:
            name: Check name
            status: ValidationStatus
            message: Human-readable message
            details: Additional details
        """
        self.name = name
        self.status = status
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
        }

    def score(self) -> int:
        """Calculate score for health calculation.

        Returns:
            100 for pass, 50 for warning, 0 for fail
        """
        if self.status == ValidationStatus.PASS:
            return 100
        elif self.status == ValidationStatus.WARNING:
            return 50
        else:
            return 0


class ValidationIssue:
    """Validation issue with severity and recommendation.

    Attributes:
        severity: IssueSeverity (error/warning/info)
        category: IssueCategory
        message: Human-readable message
        recommendation: Actionable recommendation
    """

    def __init__(
        self,
        severity: IssueSeverity,
        category: IssueCategory,
        message: str,
        recommendation: str,
    ) -> None:
        """Initialize validation issue.

        Args:
            severity: IssueSeverity
            category: IssueCategory
            message: Human-readable message
            recommendation: Actionable recommendation
        """
        self.severity = severity
        self.category = category
        self.message = message
        self.recommendation = recommendation

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "recommendation": self.recommendation,
        }


class DomainValidator:
    """Domain validator for quality assurance.

    Provides comprehensive validation of domain configurations to ensure
    data quality and readiness for production use.
    """

    def __init__(self) -> None:
        """Initialize domain validator with Neo4j client and repository."""
        self.neo4j_client = get_neo4j_client()
        self.domain_repo = get_domain_repository()
        logger.info("domain_validator_initialized")

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DatabaseConnectionError),
    )
    async def validate_domain(self, domain_name: str) -> dict[str, Any]:
        """Validate a domain comprehensively.

        Args:
            domain_name: Domain name to validate

        Returns:
            Validation result dictionary with:
                - domain_name: str
                - validation_status: str (pass/warning/fail)
                - health_score: int (0-100)
                - checks: List[ValidationCheck]
                - issues: List[ValidationIssue]
                - recommendations: List[str]

        Raises:
            ValueError: If domain not found
            DatabaseConnectionError: If validation fails after retries
        """
        logger.info("validating_domain", domain_name=domain_name)

        # Get domain configuration
        domain = await self.domain_repo.get_domain(domain_name)
        if not domain:
            raise ValueError(f"Domain '{domain_name}' not found")

        # Run all validation checks
        checks: list[ValidationCheck] = []
        checks.append(await self._check_training_samples_count(domain_name, domain))
        checks.append(await self._check_entity_type_coverage(domain_name, domain))
        checks.append(await self._check_relation_type_coverage(domain_name, domain))
        checks.append(await self._check_mentioned_in_relations(domain_name))
        checks.append(await self._check_model_trained(domain_name, domain))
        checks.append(await self._check_confidence_calibration(domain_name, domain))
        checks.append(await self._check_recent_activity(domain_name))

        # Calculate health score
        health_score = self._calculate_health_score(checks)

        # Generate issues and recommendations
        issues = self._generate_issues(checks, domain)
        recommendations = self._generate_recommendations(issues)

        # Determine overall validation status
        validation_status = self._determine_overall_status(checks)

        result = {
            "domain_name": domain_name,
            "validation_status": validation_status.value,
            "health_score": health_score,
            "checks": [check.to_dict() for check in checks],
            "issues": [issue.to_dict() for issue in issues],
            "recommendations": recommendations,
        }

        logger.info(
            "domain_validated",
            domain_name=domain_name,
            validation_status=validation_status.value,
            health_score=health_score,
            issues_count=len(issues),
        )

        return result

    async def _check_training_samples_count(
        self, domain_name: str, domain: dict[str, Any]
    ) -> ValidationCheck:
        """Check if domain has minimum training samples.

        Args:
            domain_name: Domain name
            domain: Domain configuration dict

        Returns:
            ValidationCheck for training samples count
        """
        training_samples = domain.get("training_samples", 0)

        if training_samples >= MIN_TRAINING_SAMPLES:
            status = ValidationStatus.PASS
            message = f"{training_samples} training samples (minimum: {MIN_TRAINING_SAMPLES})"
        elif training_samples > 0:
            status = ValidationStatus.WARNING
            message = (
                f"Only {training_samples} training samples "
                f"(minimum recommended: {MIN_TRAINING_SAMPLES})"
            )
        else:
            status = ValidationStatus.FAIL
            message = "No training samples available"

        return ValidationCheck(
            name="training_samples_count",
            status=status,
            message=message,
            details={"count": training_samples, "minimum": MIN_TRAINING_SAMPLES},
        )

    async def _check_entity_type_coverage(
        self, domain_name: str, domain: dict[str, Any]
    ) -> ValidationCheck:
        """Check if all entity types have training samples.

        Args:
            domain_name: Domain name
            domain: Domain configuration dict

        Returns:
            ValidationCheck for entity type coverage
        """
        # Query entity type coverage from Neo4j
        try:
            result = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain {name: $domain_name})
                OPTIONAL MATCH (e:Entity)-[:BELONGS_TO_DOMAIN]->(d)
                WITH d, collect(DISTINCT e.type) AS covered_entity_types
                RETURN d.entity_types AS all_entity_types, covered_entity_types
                """,
                {"domain_name": domain_name},
            )

            if not result:
                return ValidationCheck(
                    name="entity_type_coverage",
                    status=ValidationStatus.FAIL,
                    message="Unable to determine entity type coverage",
                    details={"covered": 0, "total": 0, "missing": []},
                )

            all_entity_types_json = result[0].get("all_entity_types", "[]")
            covered_entity_types = result[0].get("covered_entity_types", [])

            # Parse entity types JSON
            import json

            all_entity_types = json.loads(all_entity_types_json) if all_entity_types_json else []

            if not all_entity_types:
                return ValidationCheck(
                    name="entity_type_coverage",
                    status=ValidationStatus.WARNING,
                    message="No entity types configured",
                    details={"covered": 0, "total": 0, "missing": []},
                )

            covered_count = len([et for et in all_entity_types if et in covered_entity_types])
            total_count = len(all_entity_types)
            missing_types = [et for et in all_entity_types if et not in covered_entity_types]

            if covered_count == total_count:
                status = ValidationStatus.PASS
                message = "All entity types have samples"
            elif covered_count >= total_count * 0.8:
                status = ValidationStatus.WARNING
                message = f"{covered_count}/{total_count} entity types have samples"
            else:
                status = ValidationStatus.FAIL
                message = f"Only {covered_count}/{total_count} entity types have samples"

            return ValidationCheck(
                name="entity_type_coverage",
                status=status,
                message=message,
                details={
                    "covered": covered_count,
                    "total": total_count,
                    "missing": missing_types,
                },
            )

        except Exception as e:
            logger.error("entity_type_coverage_check_failed", domain_name=domain_name, error=str(e))
            return ValidationCheck(
                name="entity_type_coverage",
                status=ValidationStatus.FAIL,
                message=f"Coverage check failed: {str(e)}",
                details={"covered": 0, "total": 0, "missing": [], "error": str(e)},
            )

    async def _check_relation_type_coverage(
        self, domain_name: str, domain: dict[str, Any]
    ) -> ValidationCheck:
        """Check if all relation types have training samples.

        Args:
            domain_name: Domain name
            domain: Domain configuration dict

        Returns:
            ValidationCheck for relation type coverage
        """
        # Query relation type coverage from Neo4j
        try:
            result = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain {name: $domain_name})
                OPTIONAL MATCH (:Entity)-[r:RELATES_TO]->(:Entity)
                WHERE EXISTS {
                    MATCH (r)-[:BELONGS_TO_DOMAIN]->(d)
                }
                WITH d, collect(DISTINCT type(r)) AS covered_relation_types
                RETURN d.relation_types AS all_relation_types, covered_relation_types
                """,
                {"domain_name": domain_name},
            )

            if not result:
                return ValidationCheck(
                    name="relation_type_coverage",
                    status=ValidationStatus.FAIL,
                    message="Unable to determine relation type coverage",
                    details={"covered": 0, "total": 0, "missing": []},
                )

            all_relation_types_json = result[0].get("all_relation_types", "[]")
            covered_relation_types = result[0].get("covered_relation_types", [])

            # Parse relation types JSON
            import json

            all_relation_types = (
                json.loads(all_relation_types_json) if all_relation_types_json else []
            )

            if not all_relation_types:
                return ValidationCheck(
                    name="relation_type_coverage",
                    status=ValidationStatus.WARNING,
                    message="No relation types configured",
                    details={"covered": 0, "total": 0, "missing": []},
                )

            covered_count = len([rt for rt in all_relation_types if rt in covered_relation_types])
            total_count = len(all_relation_types)
            missing_types = [rt for rt in all_relation_types if rt not in covered_relation_types]

            if covered_count == total_count:
                status = ValidationStatus.PASS
                message = "All relation types have samples"
            elif covered_count >= total_count * 0.8:
                status = ValidationStatus.WARNING
                message = f"{covered_count}/{total_count} relation types have samples"
            else:
                status = ValidationStatus.FAIL
                message = f"Only {covered_count}/{total_count} relation types have samples"

            return ValidationCheck(
                name="relation_type_coverage",
                status=status,
                message=message,
                details={
                    "covered": covered_count,
                    "total": total_count,
                    "missing": missing_types,
                },
            )

        except Exception as e:
            logger.error(
                "relation_type_coverage_check_failed", domain_name=domain_name, error=str(e)
            )
            return ValidationCheck(
                name="relation_type_coverage",
                status=ValidationStatus.FAIL,
                message=f"Coverage check failed: {str(e)}",
                details={"covered": 0, "total": 0, "missing": [], "error": str(e)},
            )

    async def _check_mentioned_in_relations(self, domain_name: str) -> ValidationCheck:
        """Check if MENTIONED_IN provenance relations exist.

        Args:
            domain_name: Domain name

        Returns:
            ValidationCheck for MENTIONED_IN relations
        """
        try:
            result = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain {name: $domain_name})
                OPTIONAL MATCH (e:Entity)-[r:MENTIONED_IN]->(:Chunk)
                WHERE EXISTS {
                    MATCH (e)-[:BELONGS_TO_DOMAIN]->(d)
                }
                RETURN count(r) AS mentioned_in_count
                """,
                {"domain_name": domain_name},
            )

            if not result:
                return ValidationCheck(
                    name="mentioned_in_relations",
                    status=ValidationStatus.FAIL,
                    message="Unable to determine MENTIONED_IN count",
                    details={"count": 0},
                )

            mentioned_in_count = result[0].get("mentioned_in_count", 0)

            if mentioned_in_count > 0:
                status = ValidationStatus.PASS
                message = "MENTIONED_IN relations present"
            else:
                status = ValidationStatus.FAIL
                message = "No MENTIONED_IN relations (provenance missing)"

            return ValidationCheck(
                name="mentioned_in_relations",
                status=status,
                message=message,
                details={"count": mentioned_in_count},
            )

        except Exception as e:
            logger.error("mentioned_in_check_failed", domain_name=domain_name, error=str(e))
            return ValidationCheck(
                name="mentioned_in_relations",
                status=ValidationStatus.FAIL,
                message=f"MENTIONED_IN check failed: {str(e)}",
                details={"count": 0, "error": str(e)},
            )

    async def _check_model_trained(
        self, domain_name: str, domain: dict[str, Any]
    ) -> ValidationCheck:
        """Check if DSPy model has been trained.

        Args:
            domain_name: Domain name
            domain: Domain configuration dict

        Returns:
            ValidationCheck for model training status
        """
        trained_at = domain.get("trained_at")
        domain_status = domain.get("status", "pending")

        if trained_at and domain_status == "ready":
            status = ValidationStatus.PASS
            message = "DSPy model trained and ready"
            details = {"last_trained": str(trained_at), "status": domain_status}
        elif domain_status == "training":
            status = ValidationStatus.WARNING
            message = "DSPy model training in progress"
            details = {"last_trained": None, "status": domain_status}
        else:
            status = ValidationStatus.FAIL
            message = "DSPy model not trained"
            details = {"last_trained": None, "status": domain_status}

        return ValidationCheck(
            name="model_trained",
            status=status,
            message=message,
            details=details,
        )

    async def _check_confidence_calibration(
        self, domain_name: str, domain: dict[str, Any]
    ) -> ValidationCheck:
        """Check if confidence threshold is calibrated.

        Args:
            domain_name: Domain name
            domain: Domain configuration dict

        Returns:
            ValidationCheck for confidence calibration
        """
        # Query average confidence scores from Neo4j
        try:
            result = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain {name: $domain_name})
                OPTIONAL MATCH (e:Entity)-[:BELONGS_TO_DOMAIN]->(d)
                WHERE e.confidence IS NOT NULL
                RETURN d.confidence_threshold AS threshold,
                       avg(e.confidence) AS avg_confidence,
                       count(e) AS entity_count
                """,
                {"domain_name": domain_name},
            )

            if not result:
                return ValidationCheck(
                    name="confidence_calibration",
                    status=ValidationStatus.WARNING,
                    message="Unable to determine confidence calibration",
                    details={"threshold": None, "avg_confidence": None},
                )

            threshold = result[0].get("threshold")
            avg_confidence = result[0].get("avg_confidence")
            entity_count = result[0].get("entity_count", 0)

            if threshold is None:
                return ValidationCheck(
                    name="confidence_calibration",
                    status=ValidationStatus.WARNING,
                    message="No confidence threshold configured",
                    details={"threshold": None, "avg_confidence": avg_confidence},
                )

            if entity_count == 0:
                return ValidationCheck(
                    name="confidence_calibration",
                    status=ValidationStatus.WARNING,
                    message="No entities with confidence scores",
                    details={"threshold": threshold, "avg_confidence": None},
                )

            # Check if threshold is reasonable (within 20% of average confidence)
            if avg_confidence and abs(threshold - avg_confidence) <= 0.2:
                status = ValidationStatus.PASS
                message = "Confidence threshold calibrated"
            else:
                status = ValidationStatus.WARNING
                message = (
                    f"Confidence threshold ({threshold:.2f}) may need calibration "
                    f"(avg: {avg_confidence:.2f})"
                )

            return ValidationCheck(
                name="confidence_calibration",
                status=status,
                message=message,
                details={
                    "threshold": threshold,
                    "avg_confidence": round(avg_confidence, 3) if avg_confidence else None,
                    "entity_count": entity_count,
                },
            )

        except Exception as e:
            logger.error(
                "confidence_calibration_check_failed", domain_name=domain_name, error=str(e)
            )
            return ValidationCheck(
                name="confidence_calibration",
                status=ValidationStatus.WARNING,
                message=f"Calibration check failed: {str(e)}",
                details={"threshold": None, "avg_confidence": None, "error": str(e)},
            )

    async def _check_recent_activity(self, domain_name: str) -> ValidationCheck:
        """Check if domain has been used recently.

        Args:
            domain_name: Domain name

        Returns:
            ValidationCheck for recent activity
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=RECENT_ACTIVITY_DAYS)).isoformat()

            result = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain {name: $domain_name})
                OPTIONAL MATCH (e:Entity)-[:BELONGS_TO_DOMAIN]->(d)
                WHERE e.created_at > datetime($cutoff_date)
                WITH d, count(e) AS recent_entities
                OPTIONAL MATCH (doc:Document)-[:BELONGS_TO_DOMAIN]->(d)
                WHERE doc.created_at > datetime($cutoff_date)
                RETURN recent_entities, count(doc) AS recent_documents,
                       d.updated_at AS last_updated
                """,
                {"domain_name": domain_name, "cutoff_date": cutoff_date},
            )

            if not result:
                return ValidationCheck(
                    name="recent_activity",
                    status=ValidationStatus.WARNING,
                    message="Unable to determine recent activity",
                    details={"recent_entities": 0, "recent_documents": 0},
                )

            recent_entities = result[0].get("recent_entities", 0)
            recent_documents = result[0].get("recent_documents", 0)
            last_updated = result[0].get("last_updated")

            if recent_entities > 0 or recent_documents > 0:
                status = ValidationStatus.PASS
                message = f"Active domain ({recent_documents} docs, {recent_entities} entities in last {RECENT_ACTIVITY_DAYS} days)"
            else:
                status = ValidationStatus.WARNING
                message = f"No activity in last {RECENT_ACTIVITY_DAYS} days"

            return ValidationCheck(
                name="recent_activity",
                status=status,
                message=message,
                details={
                    "recent_entities": recent_entities,
                    "recent_documents": recent_documents,
                    "last_updated": str(last_updated) if last_updated else None,
                    "cutoff_days": RECENT_ACTIVITY_DAYS,
                },
            )

        except Exception as e:
            logger.error("recent_activity_check_failed", domain_name=domain_name, error=str(e))
            return ValidationCheck(
                name="recent_activity",
                status=ValidationStatus.WARNING,
                message=f"Activity check failed: {str(e)}",
                details={"recent_entities": 0, "recent_documents": 0, "error": str(e)},
            )

    def _calculate_health_score(self, checks: list[ValidationCheck]) -> int:
        """Calculate overall health score from validation checks.

        Args:
            checks: List of validation checks

        Returns:
            Health score (0-100)
        """
        if not checks:
            return 0

        total_score = sum(check.score() for check in checks)
        health_score = total_score // len(checks)

        logger.info(
            "health_score_calculated",
            total_score=total_score,
            check_count=len(checks),
            health_score=health_score,
        )

        return health_score

    def _generate_issues(
        self, checks: list[ValidationCheck], domain: dict[str, Any]
    ) -> list[ValidationIssue]:
        """Generate issues from validation checks.

        Args:
            checks: List of validation checks
            domain: Domain configuration dict

        Returns:
            List of validation issues
        """
        issues: list[ValidationIssue] = []

        for check in checks:
            if check.status == ValidationStatus.FAIL:
                severity = IssueSeverity.ERROR
            elif check.status == ValidationStatus.WARNING:
                severity = IssueSeverity.WARNING
            else:
                continue  # No issues for PASS status

            # Generate issue based on check name
            if check.name == "training_samples_count":
                issues.append(
                    ValidationIssue(
                        severity=severity,
                        category=IssueCategory.COVERAGE,
                        message=f"Domain has insufficient training samples ({check.details['count']} < {MIN_TRAINING_SAMPLES})",
                        recommendation=f"Add at least {MIN_TRAINING_SAMPLES - check.details['count']} more training samples",
                    )
                )

            elif check.name == "entity_type_coverage":
                missing_types = check.details.get("missing", [])
                if missing_types:
                    issues.append(
                        ValidationIssue(
                            severity=severity,
                            category=IssueCategory.COVERAGE,
                            message=f"Entity types {', '.join(repr(t) for t in missing_types)} have no training samples",
                            recommendation=f"Add training samples for missing entity types: {', '.join(missing_types)}",
                        )
                    )

            elif check.name == "relation_type_coverage":
                missing_types = check.details.get("missing", [])
                if missing_types:
                    issues.append(
                        ValidationIssue(
                            severity=severity,
                            category=IssueCategory.COVERAGE,
                            message=f"Relation types {', '.join(repr(t) for t in missing_types)} have no training samples",
                            recommendation=f"Add training samples for missing relation types: {', '.join(missing_types)}",
                        )
                    )

            elif check.name == "mentioned_in_relations":
                issues.append(
                    ValidationIssue(
                        severity=severity,
                        category=IssueCategory.PROVENANCE,
                        message="No MENTIONED_IN relations found (provenance missing)",
                        recommendation="Ensure entity extraction creates MENTIONED_IN links to source chunks",
                    )
                )

            elif check.name == "model_trained":
                issues.append(
                    ValidationIssue(
                        severity=severity,
                        category=IssueCategory.MODEL,
                        message="Domain model not trained",
                        recommendation=f"Run POST /api/v1/admin/domains/{domain['name']}/train to optimize prompts",
                    )
                )

            elif check.name == "confidence_calibration":
                threshold = check.details.get("threshold")
                avg_confidence = check.details.get("avg_confidence")
                if threshold and avg_confidence:
                    issues.append(
                        ValidationIssue(
                            severity=severity,
                            category=IssueCategory.CALIBRATION,
                            message=f"Confidence threshold ({threshold:.2f}) differs from average ({avg_confidence:.2f})",
                            recommendation=f"Consider adjusting confidence threshold to {avg_confidence:.2f}",
                        )
                    )

            elif check.name == "recent_activity":
                issues.append(
                    ValidationIssue(
                        severity=severity,
                        category=IssueCategory.ACTIVITY,
                        message=f"No activity in last {RECENT_ACTIVITY_DAYS} days",
                        recommendation="Domain may be inactive - consider archiving or updating with new documents",
                    )
                )

        logger.info("issues_generated", issue_count=len(issues))
        return issues

    def _generate_recommendations(self, issues: list[ValidationIssue]) -> list[str]:
        """Generate actionable recommendations from issues.

        Args:
            issues: List of validation issues

        Returns:
            List of actionable recommendations
        """
        # Sort issues by severity (error first, then warning)
        sorted_issues = sorted(
            issues,
            key=lambda i: (i.severity != IssueSeverity.ERROR, i.severity != IssueSeverity.WARNING),
        )

        # Extract unique recommendations
        recommendations = [issue.recommendation for issue in sorted_issues]

        logger.info("recommendations_generated", recommendation_count=len(recommendations))
        return recommendations

    def _determine_overall_status(self, checks: list[ValidationCheck]) -> ValidationStatus:
        """Determine overall validation status from checks.

        Args:
            checks: List of validation checks

        Returns:
            Overall validation status (pass/warning/fail)
        """
        has_fail = any(check.status == ValidationStatus.FAIL for check in checks)
        has_warning = any(check.status == ValidationStatus.WARNING for check in checks)

        if has_fail:
            return ValidationStatus.FAIL
        elif has_warning:
            return ValidationStatus.WARNING
        else:
            return ValidationStatus.PASS


# Global instance (singleton pattern)
_domain_validator: DomainValidator | None = None


def get_domain_validator() -> DomainValidator:
    """Get global domain validator instance (singleton).

    Returns:
        DomainValidator instance
    """
    global _domain_validator
    if _domain_validator is None:
        _domain_validator = DomainValidator()
    return _domain_validator
