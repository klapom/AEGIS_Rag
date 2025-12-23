"""Analytics API Models for AegisRAG.

Sprint 62 Feature 62.9: Section Analytics Endpoint

This module provides Pydantic models for section-level analytics:
- SectionAnalyticsRequest: Request model for retrieving section statistics
- SectionStats: Individual section statistics
- SectionAnalyticsResponse: Aggregated section analytics response
"""

from pydantic import BaseModel, Field


class SectionAnalyticsRequest(BaseModel):
    """Request model for section analytics endpoint.

    Sprint 62 Feature 62.9: Section Analytics Endpoint

    Example:
        >>> request = SectionAnalyticsRequest(
        ...     document_id="doc_123",
        ...     namespace="default"
        ... )
    """

    document_id: str = Field(
        ...,
        description="Document ID to retrieve section analytics for",
        min_length=1,
    )
    namespace: str = Field(
        default="default",
        description="Namespace to query (default: 'default')",
        min_length=1,
    )


class SectionStats(BaseModel):
    """Individual section statistics.

    Sprint 62 Feature 62.9: Section Analytics Endpoint

    Contains metrics for a single section including entity count,
    chunk count, and relationship count.
    """

    section_id: str = Field(..., description="Unique section identifier")
    section_title: str = Field(..., description="Human-readable section title")
    section_level: int = Field(..., description="Section hierarchy level (1, 2, 3, etc.)", ge=1)
    entity_count: int = Field(..., description="Number of entities in this section", ge=0)
    chunk_count: int = Field(..., description="Number of chunks in this section", ge=0)
    relationship_count: int = Field(
        ..., description="Number of relationships connected to this section", ge=0
    )


class SectionAnalyticsResponse(BaseModel):
    """Aggregated section analytics response.

    Sprint 62 Feature 62.9: Section Analytics Endpoint

    Provides comprehensive statistics about all sections in a document:
    - Total section count
    - Distribution by hierarchy level
    - Average entities/chunks per section
    - Top sections by various metrics

    Example:
        >>> response = SectionAnalyticsResponse(
        ...     document_id="doc_123",
        ...     total_sections=15,
        ...     level_distribution={1: 3, 2: 8, 3: 4},
        ...     avg_entities_per_section=12.5,
        ...     avg_chunks_per_section=8.3,
        ...     top_sections=[...]
        ... )
    """

    document_id: str = Field(..., description="Document ID queried")
    total_sections: int = Field(..., description="Total number of sections in document", ge=0)
    level_distribution: dict[int, int] = Field(
        ...,
        description="Distribution of sections by level (e.g., {1: 3, 2: 8, 3: 4})",
    )
    avg_entities_per_section: float = Field(
        ..., description="Average number of entities per section", ge=0.0
    )
    avg_chunks_per_section: float = Field(
        ..., description="Average number of chunks per section", ge=0.0
    )
    top_sections: list[SectionStats] = Field(
        ...,
        description="Top 10 sections ranked by entity relationships",
        max_length=10,
    )
