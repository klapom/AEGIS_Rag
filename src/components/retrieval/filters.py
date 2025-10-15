"""Metadata filtering for targeted search.

This module implements metadata-based filtering for Qdrant vector search.
Supports date ranges, source filtering, document type filtering, and tag-based
filtering.

Typical usage:
    filter_engine = MetadataFilterEngine()
    filters = MetadataFilters(
        created_after=datetime(2024, 1, 1),
        doc_type_in=["pdf", "md"],
        tags_contains=["tutorial"]
    )
    qdrant_filter = filter_engine.build_qdrant_filter(filters)
"""

from datetime import datetime

import structlog
from pydantic import BaseModel, Field, field_validator
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    Range,
)

logger = structlog.get_logger(__name__)


class MetadataFilters(BaseModel):
    """Metadata filter options for retrieval.

    All filters are optional and combined with AND logic.

    Attributes:
        created_after: Filter docs created after this date (inclusive)
        created_before: Filter docs created before this date (inclusive)
        source_in: Include only these sources (OR logic)
        source_not_in: Exclude these sources
        doc_type_in: Include only these document types (OR logic)
        tags_contains: Documents must have ALL these tags (AND logic)
    """

    created_after: datetime | None = Field(
        None, description="Filter docs created after this date (inclusive)"
    )
    created_before: datetime | None = Field(
        None, description="Filter docs created before this date (inclusive)"
    )
    source_in: list[str] | None = Field(
        None, description="Include only these sources (e.g., ['docs.rag.com', 'arxiv.org'])"
    )
    source_not_in: list[str] | None = Field(
        None, description="Exclude these sources"
    )
    doc_type_in: list[str] | None = Field(
        None, description="Include only these document types (e.g., ['pdf', 'md', 'txt'])"
    )
    tags_contains: list[str] | None = Field(
        None, description="Documents must have ALL these tags (AND logic)"
    )

    @field_validator("doc_type_in")
    @classmethod
    def validate_doc_types(cls, v: list[str] | None) -> list[str] | None:
        """Validate document types."""
        if v is None:
            return None
        allowed = {"pdf", "txt", "md", "docx", "html", "json", "csv"}
        for doc_type in v:
            if doc_type.lower() not in allowed:
                raise ValueError(
                    f"Invalid doc_type: {doc_type}. Allowed: {allowed}"
                )
        return [dt.lower() for dt in v]

    @field_validator("created_after", "created_before")
    @classmethod
    def validate_dates(cls, v: datetime | None) -> datetime | None:
        """Validate dates are not in the future."""
        if v is not None and v > datetime.now():
            raise ValueError("Date cannot be in the future")
        return v

    def is_empty(self) -> bool:
        """Check if all filters are None/empty.

        Returns:
            True if no filters are set
        """
        return all(
            getattr(self, field) is None or getattr(self, field) == []
            for field in self.model_fields
        )

    def get_active_filters(self) -> list[str]:
        """Get list of active filter names.

        Returns:
            List of filter field names that are set
        """
        active = []
        for field in self.model_fields:
            value = getattr(self, field)
            if value is not None and value != []:
                active.append(field)
        return active


class MetadataFilterEngine:
    """Metadata filter engine for Qdrant.

    Converts MetadataFilters into Qdrant filter conditions.
    All filters are combined with AND logic.

    Metadata Schema Expected:
    - created_at: Unix timestamp (int) or ISO datetime string
    - source: Source URL or identifier (str)
    - doc_type: Document type (str): pdf, txt, md, docx, etc.
    - tags: List of tags (list[str])
    """

    def __init__(self):
        """Initialize filter engine."""
        logger.info("metadata_filter_engine_initialized")

    def build_qdrant_filter(self, filters: MetadataFilters) -> Filter | None:
        """Build Qdrant Filter from MetadataFilters.

        Args:
            filters: Metadata filters to apply

        Returns:
            Qdrant Filter object, or None if no filters set

        Example:
            >>> filters = MetadataFilters(
            ...     created_after=datetime(2024, 1, 1),
            ...     doc_type_in=["pdf", "md"]
            ... )
            >>> qdrant_filter = engine.build_qdrant_filter(filters)
        """
        if filters.is_empty():
            logger.debug("no_filters_applied")
            return None

        conditions = []

        # Date range filters
        if filters.created_after is not None:
            conditions.append(
                FieldCondition(
                    key="created_at",
                    range=Range(
                        gte=int(filters.created_after.timestamp()),
                    ),
                )
            )
            logger.debug(
                "filter_created_after",
                timestamp=filters.created_after.isoformat(),
            )

        if filters.created_before is not None:
            conditions.append(
                FieldCondition(
                    key="created_at",
                    range=Range(
                        lte=int(filters.created_before.timestamp()),
                    ),
                )
            )
            logger.debug(
                "filter_created_before",
                timestamp=filters.created_before.isoformat(),
            )

        # Source filters
        if filters.source_in is not None and len(filters.source_in) > 0:
            conditions.append(
                FieldCondition(
                    key="source",
                    match=MatchAny(any=filters.source_in),
                )
            )
            logger.debug("filter_source_in", sources=filters.source_in)

        if filters.source_not_in is not None and len(filters.source_not_in) > 0:
            # Qdrant doesn't have direct "not in" - use must_not in Filter
            # We'll handle this separately in the Filter construction
            pass

        # Document type filter
        if filters.doc_type_in is not None and len(filters.doc_type_in) > 0:
            conditions.append(
                FieldCondition(
                    key="doc_type",
                    match=MatchAny(any=filters.doc_type_in),
                )
            )
            logger.debug("filter_doc_type_in", doc_types=filters.doc_type_in)

        # Tags filter (must have ALL tags)
        if filters.tags_contains is not None and len(filters.tags_contains) > 0:
            for tag in filters.tags_contains:
                conditions.append(
                    FieldCondition(
                        key="tags",
                        match=MatchValue(value=tag),
                    )
                )
            logger.debug("filter_tags_contains", tags=filters.tags_contains)

        # Build must_not conditions
        must_not_conditions = []
        if filters.source_not_in is not None and len(filters.source_not_in) > 0:
            must_not_conditions.append(
                FieldCondition(
                    key="source",
                    match=MatchAny(any=filters.source_not_in),
                )
            )
            logger.debug("filter_source_not_in", sources=filters.source_not_in)

        # Construct final Filter
        if not conditions and not must_not_conditions:
            return None

        qdrant_filter = Filter(
            must=conditions if conditions else None,
            must_not=must_not_conditions if must_not_conditions else None,
        )

        logger.info(
            "qdrant_filter_built",
            num_must=len(conditions),
            num_must_not=len(must_not_conditions),
            active_filters=filters.get_active_filters(),
        )

        return qdrant_filter

    def validate_filter(self, filters: MetadataFilters) -> tuple[bool, str]:
        """Validate filter consistency.

        Args:
            filters: Filters to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check date range consistency
        if (
            filters.created_after is not None
            and filters.created_before is not None
            and filters.created_after > filters.created_before
        ):
            return False, "created_after must be before created_before"

        # Check source conflicts
        if filters.source_in is not None and filters.source_not_in is not None:
            overlap = set(filters.source_in) & set(filters.source_not_in)
            if overlap:
                return False, f"source_in and source_not_in overlap: {overlap}"

        return True, ""

    def estimate_selectivity(self, filters: MetadataFilters) -> float:
        """Estimate filter selectivity (fraction of docs that pass).

        Args:
            filters: Filters to estimate

        Returns:
            Estimated selectivity (0.0 to 1.0)

        Note:
            This is a heuristic estimate without actual data statistics.
            Used for query planning and logging.
        """
        if filters.is_empty():
            return 1.0

        # Rough heuristic: multiply selectivities
        selectivity = 1.0

        # Date filters: assume ~50% for typical ranges
        if filters.created_after is not None or filters.created_before is not None:
            selectivity *= 0.5

        # Source filters: assume ~30% per source
        if filters.source_in is not None:
            selectivity *= min(1.0, 0.3 * len(filters.source_in))

        # Doc type filters: assume ~40% per type
        if filters.doc_type_in is not None:
            selectivity *= min(1.0, 0.4 * len(filters.doc_type_in))

        # Tag filters: assume ~60% per tag (AND logic)
        if filters.tags_contains is not None:
            selectivity *= 0.6 ** len(filters.tags_contains)

        return max(0.01, selectivity)  # At least 1%
