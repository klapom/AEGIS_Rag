"""Bi-Temporal Query API for Knowledge Graph Time Travel.

Sprint Context: Sprint 39 (2025-12-08) - Features 39.2-39.4: Bi-Temporal Backend

This module provides REST API endpoints for bi-temporal queries, allowing users to:
- Query the knowledge graph at a specific point in time (Feature 39.2)
- Retrieve entity history and version timelines (Feature 39.2)
- View entity changelogs with audit trail (Feature 39.3)
- Compare entity versions and rollback to previous states (Feature 39.4)

All endpoints require:
- JWT authentication (Sprint 38 dependency)
- temporal_queries_enabled = true (ADR-042 opt-in feature flag)

Endpoints:
    POST /api/v1/temporal/point-in-time - Query graph at timestamp
    POST /api/v1/temporal/entity-history - Get entity version history
    GET /api/v1/temporal/entities/{id}/changelog - Get entity changelog
    GET /api/v1/temporal/entities/{id}/versions - List entity versions
    GET /api/v1/temporal/entities/{id}/versions/{v1}/compare/{v2} - Compare versions
    POST /api/v1/temporal/entities/{id}/versions/{version_id}/revert - Rollback

Example Usage:
    # Point-in-time query
    >>> response = requests.post(
    ...     "/api/v1/temporal/point-in-time",
    ...     json={"timestamp": "2024-11-15T00:00:00Z", "limit": 100},
    ...     headers={"Authorization": f"Bearer {token}"}
    ... )
    >>> entities = response.json()["entities"]

    # Entity history
    >>> response = requests.post(
    ...     "/api/v1/temporal/entity-history",
    ...     json={"entity_id": "kubernetes", "start_date": "2024-11-01", "end_date": "2024-12-01"},
    ...     headers={"Authorization": f"Bearer {token}"}
    ... )
    >>> versions = response.json()["versions"]

See Also:
    - src/components/graph_rag/temporal_query_builder.py: Temporal query builder
    - src/components/graph_rag/evolution_tracker.py: Change tracking
    - src/components/graph_rag/version_manager.py: Version management
    - docs/adr/ADR-042_BITEMPORAL_OPT_IN_STRATEGY.md: Feature flag strategy
"""

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.components.graph_rag.evolution_tracker import get_evolution_tracker
from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.components.graph_rag.temporal_query_builder import get_temporal_query_builder
from src.components.graph_rag.version_manager import get_version_manager
from src.core.auth import User
from src.core.config import settings

router = APIRouter(prefix="/api/v1/temporal", tags=["Temporal Queries"])
logger = structlog.get_logger(__name__)


# Feature Flag Dependency
def check_temporal_enabled() -> None:
    """Check if temporal queries are enabled.

    Raises:
        HTTPException: 400 Bad Request if temporal_queries_enabled = false
    """
    if not settings.temporal_queries_enabled:
        logger.warning("temporal_query_rejected", reason="Feature not enabled")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Temporal queries not enabled. Enable temporal_queries_enabled "
                "in Admin Settings and create temporal indexes."
            ),
        )


# Pydantic Models


class PointInTimeRequest(BaseModel):
    """Point-in-time query request.

    Attributes:
        timestamp: Point in time to query (ISO 8601 format)
        entity_filter: Optional Cypher filter (e.g., "e.type = 'TECHNOLOGY'")
        limit: Maximum entities to return (default: 100, max: 1000)

    Example:
        >>> request = PointInTimeRequest(
        ...     timestamp=datetime(2024, 11, 15),
        ...     entity_filter="e.type = 'TECHNOLOGY'",
        ...     limit=50
        ... )
    """

    timestamp: datetime = Field(..., description="Point in time to query (ISO 8601)")
    entity_filter: str | None = Field(None, description="Optional Cypher filter for entities")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum entities to return")


class EntitySnapshot(BaseModel):
    """Entity snapshot at a specific point in time.

    Attributes:
        id: Entity ID
        name: Entity name
        type: Entity type (e.g., TECHNOLOGY, PERSON, ORGANIZATION)
        properties: Entity properties as dict
        valid_from: When entity became valid (real-world time)
        valid_to: When entity became invalid (None = still valid)
        version_number: Version number
        changed_by: User who made the change
    """

    id: str
    name: str
    type: str
    properties: dict[str, Any]
    valid_from: datetime
    valid_to: datetime | None
    version_number: int
    changed_by: str = "system"


class TemporalQueryResponse(BaseModel):
    """Response for point-in-time query.

    Attributes:
        entities: List of entity snapshots at the queried timestamp
        as_of: The timestamp that was queried
        total_count: Total number of entities found
    """

    entities: list[EntitySnapshot]
    as_of: datetime
    total_count: int


class EntityHistoryRequest(BaseModel):
    """Entity history request.

    Attributes:
        entity_id: Entity ID to retrieve history for
        start_date: Optional start date for history range
        end_date: Optional end date for history range
        limit: Maximum versions to return (default: 50, max: 200)

    Example:
        >>> request = EntityHistoryRequest(
        ...     entity_id="kubernetes",
        ...     start_date=datetime(2024, 11, 1),
        ...     end_date=datetime(2024, 12, 1),
        ...     limit=50
        ... )
    """

    entity_id: str = Field(..., description="Entity ID")
    start_date: datetime | None = Field(None, description="Start date (optional)")
    end_date: datetime | None = Field(None, description="End date (optional)")
    limit: int = Field(default=50, ge=1, le=200, description="Maximum versions to return")


class EntityHistoryResponse(BaseModel):
    """Response for entity history query.

    Attributes:
        entity_id: Entity ID
        versions: List of entity versions (newest to oldest)
        total_versions: Total number of versions
        first_seen: When entity was first created
        last_updated: When entity was last updated
    """

    entity_id: str
    versions: list[EntitySnapshot]
    total_versions: int
    first_seen: datetime | None
    last_updated: datetime | None


class ChangelogResponse(BaseModel):
    """Response for entity changelog.

    Attributes:
        entity_id: Entity ID
        changes: List of change events (newest to oldest)
        total_changes: Total number of changes
    """

    entity_id: str
    changes: list[dict[str, Any]]
    total_changes: int


class VersionListResponse(BaseModel):
    """Response for version listing.

    Attributes:
        entity_id: Entity ID
        versions: List of versions with metadata
        current_version: Current version number
    """

    entity_id: str
    versions: list[dict[str, Any]]
    current_version: int | None


class VersionCompareResponse(BaseModel):
    """Response for version comparison.

    Attributes:
        entity_id: Entity ID
        version_a: First version number
        version_b: Second version number
        changed_fields: List of fields that changed
        differences: Dict of field differences
        change_count: Number of changed fields
    """

    entity_id: str
    version_a: int
    version_b: int
    changed_fields: list[str]
    differences: dict[str, Any]
    change_count: int


class RevertRequest(BaseModel):
    """Request to revert entity to a previous version.

    Attributes:
        reason: Reason for reverting (required for audit trail)

    Example:
        >>> request = RevertRequest(reason="Reverting incorrect update")
    """

    reason: str = Field(..., description="Reason for reverting (audit trail)", min_length=5)


# Feature 39.2: Bi-Temporal Query API


@router.post("/point-in-time", response_model=TemporalQueryResponse, status_code=status.HTTP_200_OK)
async def query_at_point_in_time(
    request: PointInTimeRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_temporal_enabled),
) -> TemporalQueryResponse:
    """Query knowledge graph state at a specific point in time.

    Returns entities that were valid and present in the database at the specified timestamp.
    Uses bi-temporal model: valid_time (real-world) + transaction_time (database).

    Args:
        request: Point-in-time query parameters
        current_user: Authenticated user from JWT token
        _: Feature flag check dependency

    Returns:
        TemporalQueryResponse with entities at timestamp

    Raises:
        HTTPException: 400 if temporal queries disabled
        HTTPException: 401 if authentication fails
        HTTPException: 500 if query execution fails

    Example:
        >>> # Query graph as of November 15, 2024
        >>> response = await query_at_point_in_time(
        ...     PointInTimeRequest(
        ...         timestamp=datetime(2024, 11, 15),
        ...         entity_filter="e.type = 'TECHNOLOGY'",
        ...         limit=100
        ...     ),
        ...     current_user=user
        ... )
        >>> print(f"Found {response.total_count} entities")

    Use Cases:
        - "What did we know about Project X on launch day?"
        - "Show entity state before the last update"
        - Compliance: "What was recorded on audit date?"
    """
    logger.info(
        "point_in_time_query",
        timestamp=request.timestamp.isoformat(),
        user=current_user.username,
        limit=request.limit,
    )

    try:
        builder = get_temporal_query_builder()
        neo4j = get_neo4j_client()

        # Build temporal query
        builder.reset()
        query_parts = builder.match("(e:base)").as_of(request.timestamp)

        # Add optional filter
        if request.entity_filter:
            query_parts = query_parts.where(request.entity_filter)

        query_parts = query_parts.return_clause("e").limit(request.limit)

        query, params = query_parts.build()

        # Execute query
        results = await neo4j.execute_read(query, params)

        # Parse results
        entities = []
        for record in results:
            entity_data = dict(record["e"])

            # Convert datetime fields
            for field in ["valid_from", "valid_to", "transaction_from", "transaction_to"]:
                if (
                    field in entity_data
                    and entity_data[field]
                    and hasattr(entity_data[field], "isoformat")
                ):
                    entity_data[field] = entity_data[field].isoformat()

            entities.append(
                EntitySnapshot(
                    id=entity_data.get("id", ""),
                    name=entity_data.get("name", ""),
                    type=entity_data.get("type", ""),
                    properties=entity_data,
                    valid_from=datetime.fromisoformat(entity_data.get("valid_from", "")),
                    valid_to=(
                        datetime.fromisoformat(entity_data["valid_to"])
                        if entity_data.get("valid_to")
                        else None
                    ),
                    version_number=entity_data.get("version_number", 1),
                    changed_by=entity_data.get("changed_by", "system"),
                )
            )

        logger.info(
            "point_in_time_query_success",
            timestamp=request.timestamp.isoformat(),
            count=len(entities),
            user=current_user.username,
        )

        return TemporalQueryResponse(
            entities=entities,
            as_of=request.timestamp,
            total_count=len(entities),
        )

    except Exception as e:
        logger.error(
            "point_in_time_query_error",
            timestamp=request.timestamp.isoformat(),
            error=str(e),
            user=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute point-in-time query: {e}",
        ) from e


@router.post(
    "/entity-history", response_model=EntityHistoryResponse, status_code=status.HTTP_200_OK
)
async def get_entity_history(
    request: EntityHistoryRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_temporal_enabled),
) -> EntityHistoryResponse:
    """Get complete version history of an entity.

    Returns all versions of the specified entity, optionally filtered by date range.

    Args:
        request: Entity history query parameters
        current_user: Authenticated user from JWT token
        _: Feature flag check dependency

    Returns:
        EntityHistoryResponse with version history

    Raises:
        HTTPException: 400 if temporal queries disabled
        HTTPException: 401 if authentication fails
        HTTPException: 404 if entity not found
        HTTPException: 500 if query execution fails

    Example:
        >>> # Get history of "kubernetes" entity
        >>> response = await get_entity_history(
        ...     EntityHistoryRequest(
        ...         entity_id="kubernetes",
        ...         start_date=datetime(2024, 11, 1),
        ...         end_date=datetime(2024, 12, 1),
        ...         limit=50
        ...     ),
        ...     current_user=user
        ... )
        >>> print(f"Found {response.total_versions} versions")
    """
    logger.info(
        "entity_history_query",
        entity_id=request.entity_id,
        user=current_user.username,
        start_date=request.start_date.isoformat() if request.start_date else None,
        end_date=request.end_date.isoformat() if request.end_date else None,
    )

    try:
        version_manager = get_version_manager()

        # Get all versions
        versions_data = await version_manager.get_versions(
            entity_id=request.entity_id,
            limit=request.limit,
        )

        if not versions_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity '{request.entity_id}' not found",
            )

        # Filter by date range if provided
        if request.start_date or request.end_date:
            filtered_versions = []
            for version in versions_data:
                valid_from_str = version.get("valid_from")
                if not valid_from_str:
                    continue

                valid_from = datetime.fromisoformat(valid_from_str)

                if request.start_date and valid_from < request.start_date:
                    continue
                if request.end_date and valid_from > request.end_date:
                    continue

                filtered_versions.append(version)

            versions_data = filtered_versions

        # Convert to EntitySnapshot objects
        versions = []
        for version_data in versions_data:
            versions.append(
                EntitySnapshot(
                    id=version_data.get("id", ""),
                    name=version_data.get("name", ""),
                    type=version_data.get("type", ""),
                    properties=version_data,
                    valid_from=datetime.fromisoformat(version_data.get("valid_from", "")),
                    valid_to=(
                        datetime.fromisoformat(version_data["valid_to"])
                        if version_data.get("valid_to")
                        else None
                    ),
                    version_number=version_data.get("version_number", 1),
                    changed_by=version_data.get("changed_by", "system"),
                )
            )

        # Determine first_seen and last_updated
        first_seen = (
            datetime.fromisoformat(versions_data[-1]["valid_from"]) if versions_data else None
        )
        last_updated = (
            datetime.fromisoformat(versions_data[0]["valid_from"]) if versions_data else None
        )

        logger.info(
            "entity_history_query_success",
            entity_id=request.entity_id,
            versions_count=len(versions),
            user=current_user.username,
        )

        return EntityHistoryResponse(
            entity_id=request.entity_id,
            versions=versions,
            total_versions=len(versions),
            first_seen=first_seen,
            last_updated=last_updated,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "entity_history_query_error",
            entity_id=request.entity_id,
            error=str(e),
            user=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entity history: {e}",
        ) from e


# Feature 39.3: Entity Change Tracking


@router.get(
    "/entities/{entity_id}/changelog",
    response_model=ChangelogResponse,
    status_code=status.HTTP_200_OK,
)
async def get_entity_changelog(
    entity_id: str = Path(..., description="Entity ID"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum changes to return"),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_temporal_enabled),
) -> ChangelogResponse:
    """Get change history for an entity with audit trail.

    Returns all change events for the specified entity, showing who changed what and when.
    Includes changed_by field populated from JWT authentication context.

    Args:
        entity_id: Entity ID to retrieve changelog for
        limit: Maximum number of changes to return
        current_user: Authenticated user from JWT token
        _: Feature flag check dependency

    Returns:
        ChangelogResponse with list of change events

    Raises:
        HTTPException: 400 if temporal queries disabled
        HTTPException: 401 if authentication fails
        HTTPException: 500 if query execution fails

    Example:
        >>> # Get changelog for "kubernetes" entity
        >>> response = await get_entity_changelog(
        ...     entity_id="kubernetes",
        ...     limit=50,
        ...     current_user=user
        ... )
        >>> for change in response.changes:
        ...     print(f"{change['timestamp']}: {change['change_type']} by {change['changed_by']}")

    Use Cases:
        - Audit trail: "Who changed this entity?"
        - Compliance: "Show all modifications by user X"
        - Debugging: "When did this field change?"
    """
    logger.info(
        "entity_changelog_query",
        entity_id=entity_id,
        limit=limit,
        user=current_user.username,
    )

    try:
        tracker = get_evolution_tracker()

        # Get changelog
        changes = await tracker.get_change_log(entity_id=entity_id, limit=limit)

        logger.info(
            "entity_changelog_query_success",
            entity_id=entity_id,
            changes_count=len(changes),
            user=current_user.username,
        )

        return ChangelogResponse(
            entity_id=entity_id,
            changes=changes,
            total_changes=len(changes),
        )

    except Exception as e:
        logger.error(
            "entity_changelog_query_error",
            entity_id=entity_id,
            error=str(e),
            user=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entity changelog: {e}",
        ) from e


# Feature 39.4: Entity Version Management


@router.get(
    "/entities/{entity_id}/versions",
    response_model=VersionListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_entity_versions(
    entity_id: str = Path(..., description="Entity ID"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum versions to return"),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_temporal_enabled),
) -> VersionListResponse:
    """List all versions of an entity.

    Returns version metadata for the specified entity, ordered by version number descending.

    Args:
        entity_id: Entity ID to retrieve versions for
        limit: Maximum number of versions to return
        current_user: Authenticated user from JWT token
        _: Feature flag check dependency

    Returns:
        VersionListResponse with list of versions

    Raises:
        HTTPException: 400 if temporal queries disabled
        HTTPException: 401 if authentication fails
        HTTPException: 404 if entity not found
        HTTPException: 500 if query execution fails

    Example:
        >>> # List versions of "kubernetes" entity
        >>> response = await get_entity_versions(
        ...     entity_id="kubernetes",
        ...     limit=10,
        ...     current_user=user
        ... )
        >>> print(f"Current version: {response.current_version}")
    """
    logger.info(
        "entity_versions_query",
        entity_id=entity_id,
        limit=limit,
        user=current_user.username,
    )

    try:
        version_manager = get_version_manager()

        # Get versions
        versions = await version_manager.get_versions(entity_id=entity_id, limit=limit)

        if not versions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity '{entity_id}' not found",
            )

        # Current version is the first (highest version_number)
        current_version = versions[0].get("version_number") if versions else None

        logger.info(
            "entity_versions_query_success",
            entity_id=entity_id,
            versions_count=len(versions),
            current_version=current_version,
            user=current_user.username,
        )

        return VersionListResponse(
            entity_id=entity_id,
            versions=versions,
            current_version=current_version,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "entity_versions_query_error",
            entity_id=entity_id,
            error=str(e),
            user=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entity versions: {e}",
        ) from e


@router.get(
    "/entities/{entity_id}/versions/{version_a}/compare/{version_b}",
    response_model=VersionCompareResponse,
    status_code=status.HTTP_200_OK,
)
async def compare_entity_versions(
    entity_id: str = Path(..., description="Entity ID"),
    version_a: int = Path(..., description="First version number", ge=1),
    version_b: int = Path(..., description="Second version number", ge=1),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_temporal_enabled),
) -> VersionCompareResponse:
    """Compare two versions of an entity.

    Returns field-level differences between two versions of the same entity.

    Args:
        entity_id: Entity ID to compare versions for
        version_a: First version number
        version_b: Second version number
        current_user: Authenticated user from JWT token
        _: Feature flag check dependency

    Returns:
        VersionCompareResponse with differences

    Raises:
        HTTPException: 400 if temporal queries disabled or same version compared
        HTTPException: 401 if authentication fails
        HTTPException: 404 if versions not found
        HTTPException: 500 if query execution fails

    Example:
        >>> # Compare version 2 and 3 of "kubernetes" entity
        >>> response = await compare_entity_versions(
        ...     entity_id="kubernetes",
        ...     version_a=2,
        ...     version_b=3,
        ...     current_user=user
        ... )
        >>> print(f"Changed {response.change_count} fields")
        >>> for field, diff in response.differences.items():
        ...     print(f"{field}: {diff['from']} -> {diff['to']}")
    """
    if version_a == version_b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare version with itself",
        )

    logger.info(
        "version_compare_query",
        entity_id=entity_id,
        version_a=version_a,
        version_b=version_b,
        user=current_user.username,
    )

    try:
        version_manager = get_version_manager()

        # Compare versions
        comparison = await version_manager.compare_versions(
            entity_id=entity_id,
            version1=version_a,
            version2=version_b,
        )

        # Check for error in comparison
        if "error" in comparison:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=comparison["error"],
            )

        logger.info(
            "version_compare_query_success",
            entity_id=entity_id,
            version_a=version_a,
            version_b=version_b,
            changes_count=comparison["change_count"],
            user=current_user.username,
        )

        return VersionCompareResponse(
            entity_id=comparison["entity_id"],
            version_a=comparison["version1"],
            version_b=comparison["version2"],
            changed_fields=comparison["changed_fields"],
            differences=comparison["differences"],
            change_count=comparison["change_count"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "version_compare_query_error",
            entity_id=entity_id,
            version_a=version_a,
            version_b=version_b,
            error=str(e),
            user=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare versions: {e}",
        ) from e


@router.post(
    "/entities/{entity_id}/versions/{version_id}/revert",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def revert_entity_to_version(
    entity_id: str = Path(..., description="Entity ID"),
    version_id: str = Path(..., description="Version ID to revert to"),
    request: RevertRequest = Body(...),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_temporal_enabled),
) -> dict[str, Any]:
    """Revert entity to a previous version (creates new version, no history loss).

    Creates a new version with the data from the specified version. This is a non-destructive
    operation that preserves full audit trail.

    Args:
        entity_id: Entity ID to revert
        version_id: Version ID to revert to
        request: Revert request with reason (required for audit trail)
        current_user: Authenticated user from JWT token
        _: Feature flag check dependency

    Returns:
        New version data after revert

    Raises:
        HTTPException: 400 if temporal queries disabled
        HTTPException: 401 if authentication fails
        HTTPException: 404 if entity or version not found
        HTTPException: 500 if revert operation fails

    Example:
        >>> # Revert "kubernetes" entity to version abc123
        >>> response = await revert_entity_to_version(
        ...     entity_id="kubernetes",
        ...     version_id="abc123",
        ...     request=RevertRequest(reason="Reverting incorrect update"),
        ...     current_user=user
        ... )
        >>> print(f"Reverted to version {response['version_id']}")

    Security Notes:
        - Requires JWT authentication
        - changed_by field populated from current_user.username
        - Reason is required for audit trail
        - Original version is preserved (no data loss)
    """
    logger.info(
        "entity_revert",
        entity_id=entity_id,
        version_id=version_id,
        user=current_user.username,
        reason=request.reason,
    )

    try:
        version_manager = get_version_manager()

        # Revert to version (creates new version)
        new_version = await version_manager.revert_to_version(
            entity_id=entity_id,
            version_id=version_id,
            changed_by=current_user.username,  # JWT auth integration
            change_reason=request.reason,
        )

        logger.info(
            "entity_revert_success",
            entity_id=entity_id,
            target_version_id=version_id,
            new_version_id=new_version["version_id"],
            new_version_number=new_version["version_number"],
            user=current_user.username,
        )

        return {
            "message": "Entity reverted successfully",
            "entity_id": entity_id,
            "reverted_to_version_id": version_id,
            "new_version": new_version,
        }

    except ValueError as e:
        logger.warning(
            "entity_revert_failed",
            entity_id=entity_id,
            version_id=version_id,
            error=str(e),
            user=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "entity_revert_error",
            entity_id=entity_id,
            version_id=version_id,
            error=str(e),
            user=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revert entity: {e}",
        ) from e
