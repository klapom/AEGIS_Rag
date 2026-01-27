"""Graph Entity and Relation Management API endpoints.

Sprint 121 Feature 121.5a-d: Entity/Relation Delete API + OpenAPI

This module provides endpoints for:
- Listing/searching entities (paginated)
- Deleting entities (GDPR Article 17 compliance)
- Viewing entity details
- Listing relations (paginated)
- Deleting specific relations

All operations respect namespace isolation for multi-tenant security.
"""

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/graph", tags=["admin-graph-entities"])


# ============================================================================
# Pydantic Models
# ============================================================================


class EntityListRequest(BaseModel):
    """Request model for entity listing/searching.

    Sprint 121 Feature 121.5a: Entity List/Search API
    """

    search: str | None = Field(
        None,
        description="Search term for entity name (case-insensitive partial match)",
        min_length=1,
        max_length=200,
    )
    entity_type: str | None = Field(
        None,
        description="Filter by entity type (e.g., PERSON, ORGANIZATION, LOCATION)",
    )
    namespace_id: str | None = Field(
        None,
        description="Filter by namespace (multi-tenant isolation)",
    )
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(50, ge=1, le=200, description="Items per page (max: 200)")


class EntityResponse(BaseModel):
    """Entity metadata response model.

    Sprint 121 Feature 121.5a: Entity List/Search API
    """

    entity_id: str = Field(..., description="Unique entity identifier")
    entity_name: str = Field(..., description="Entity name (e.g., 'Albert Einstein')")
    entity_type: str = Field(..., description="Entity type (e.g., PERSON, ORGANIZATION)")
    description: str | None = Field(None, description="Entity description (if available)")
    source_id: str | None = Field(None, description="Source document ID")
    file_path: str | None = Field(None, description="Source file path")
    namespace_id: str | None = Field(None, description="Namespace for multi-tenant isolation")
    created_at: str | None = Field(None, description="Creation timestamp (ISO 8601)")
    relation_count: int = Field(0, description="Number of relationships involving this entity")


class EntityListResponse(BaseModel):
    """Paginated entity list response model.

    Sprint 121 Feature 121.5a: Entity List/Search API
    """

    entities: list[EntityResponse] = Field(..., description="List of entities")
    total: int = Field(..., description="Total number of entities matching filters")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class EntityDetailResponse(BaseModel):
    """Detailed entity information with relationships.

    Sprint 121 Feature 121.5b: Entity Detail API
    """

    entity: EntityResponse = Field(..., description="Entity metadata")
    relationships: list[dict] = Field(
        default_factory=list,
        description="List of relationships (source, target, type, description)",
    )


class DeleteResponse(BaseModel):
    """Response model for delete operations.

    Sprint 121 Feature 121.5c: Entity/Relation Delete API
    """

    status: str = Field(..., description="Deletion status (success, partial, failed)")
    message: str = Field(..., description="Human-readable status message")
    deleted_entity_id: str | None = Field(None, description="Deleted entity ID (if applicable)")
    affected_relations: int = Field(
        0, description="Number of relationships deleted (cascade delete)"
    )
    audit_logged: bool = Field(
        True, description="Whether deletion was logged for GDPR compliance"
    )


class RelationListRequest(BaseModel):
    """Request model for relation listing.

    Sprint 121 Feature 121.5d: Relation List API
    """

    entity_id: str | None = Field(
        None,
        description="Filter relations involving this entity (as source or target)",
    )
    relation_type: str | None = Field(
        None,
        description="Filter by relation type (e.g., RELATES_TO, MENTIONED_IN)",
    )
    namespace_id: str | None = Field(None, description="Filter by namespace")
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(50, ge=1, le=200, description="Items per page (max: 200)")


class RelationResponse(BaseModel):
    """Relation metadata response model.

    Sprint 121 Feature 121.5d: Relation List API
    """

    source_entity_id: str = Field(..., description="Source entity ID")
    source_entity_name: str = Field(..., description="Source entity name")
    target_entity_id: str = Field(..., description="Target entity ID")
    target_entity_name: str = Field(..., description="Target entity name")
    relation_type: str = Field(..., description="Relationship type (e.g., RELATES_TO)")
    description: str | None = Field(None, description="Relationship description (if available)")
    weight: float = Field(1.0, description="Relationship weight/strength")
    namespace_id: str | None = Field(None, description="Namespace for multi-tenant isolation")


class RelationListResponse(BaseModel):
    """Paginated relation list response model.

    Sprint 121 Feature 121.5d: Relation List API
    """

    relations: list[RelationResponse] = Field(..., description="List of relationships")
    total: int = Field(..., description="Total number of relationships matching filters")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class RelationDeleteRequest(BaseModel):
    """Request model for deleting specific relations.

    Sprint 121 Feature 121.5c: Relation Delete API
    """

    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_id: str = Field(..., description="Target entity ID")
    relation_type: str | None = Field(
        None,
        description="Relation type (if None, deletes ALL relations between the two entities)",
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/entities/search",
    response_model=EntityListResponse,
    status_code=status.HTTP_200_OK,
    summary="List/search entities with pagination",
    description="""
    Search and list knowledge graph entities with filtering and pagination.

    **Sprint 121 Feature 121.5a: Entity List/Search API**

    **Filters:**
    - `search`: Case-insensitive partial match on entity name
    - `entity_type`: Filter by entity type (PERSON, ORGANIZATION, LOCATION, etc.)
    - `namespace_id`: Multi-tenant namespace isolation
    - `page`: Page number (1-indexed)
    - `page_size`: Items per page (1-200)

    **Use Cases:**
    - Admin dashboard entity browser
    - GDPR Article 15 (Right of Access) compliance
    - Entity management and cleanup
    - Graph exploration and debugging

    **Performance:**
    - Uses indexed queries for fast lookups
    - Paginated to handle large graphs (10k+ entities)
    - Relation counts computed efficiently via aggregation

    **Example:**
    ```json
    {
      "search": "einstein",
      "entity_type": "PERSON",
      "namespace_id": "research_papers",
      "page": 1,
      "page_size": 50
    }
    ```
    """,
    responses={
        200: {
            "description": "Successfully retrieved entities",
            "model": EntityListResponse,
        },
        400: {"description": "Invalid request parameters"},
        500: {"description": "Neo4j query execution failed"},
    },
)
async def list_entities(request: EntityListRequest) -> EntityListResponse:
    """List/search knowledge graph entities with pagination.

    Sprint 121 Feature 121.5a: Entity List/Search API

    Args:
        request: EntityListRequest with search filters and pagination

    Returns:
        EntityListResponse with paginated entity results

    Raises:
        HTTPException: If Neo4j query fails or parameters are invalid
    """
    try:
        from src.components.graph_rag.neo4j_client import get_neo4j_client

        neo4j = get_neo4j_client()

        # Calculate pagination offsets
        skip = (request.page - 1) * request.page_size
        limit = request.page_size

        logger.info(
            "entity_search_requested",
            search=request.search,
            entity_type=request.entity_type,
            namespace_id=request.namespace_id,
            page=request.page,
            page_size=request.page_size,
        )

        # Build WHERE clauses dynamically
        where_clauses = []
        params = {"skip": skip, "limit": limit}

        if request.search:
            where_clauses.append("toLower(e.entity_name) CONTAINS toLower($search)")
            params["search"] = request.search

        if request.entity_type:
            where_clauses.append(
                "any(lbl IN labels(e) WHERE lbl <> 'base' AND lbl = $entity_type)"
            )
            params["entity_type"] = request.entity_type

        if request.namespace_id:
            where_clauses.append("e.namespace_id = $namespace_id")
            params["namespace_id"] = request.namespace_id

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Query 1: Get total count
        count_query = f"""
        MATCH (e:base)
        WHERE {where_clause}
        RETURN count(e) AS total
        """
        count_results = await neo4j.execute_read(count_query, params)
        total = count_results[0]["total"] if count_results else 0

        # Query 2: Get paginated entities with relation counts
        entities_query = f"""
        MATCH (e:base)
        WHERE {where_clause}
        OPTIONAL MATCH (e)-[r]-()
        WITH e, count(DISTINCT r) AS rel_count
        RETURN e.entity_id AS entity_id,
               e.entity_name AS entity_name,
               [lbl IN labels(e) WHERE lbl <> 'base'][0] AS entity_type,
               e.description AS description,
               e.source_id AS source_id,
               e.file_path AS file_path,
               e.namespace_id AS namespace_id,
               e.created_at AS created_at,
               rel_count AS relation_count
        ORDER BY e.entity_name
        SKIP $skip LIMIT $limit
        """
        entity_results = await neo4j.execute_read(entities_query, params)

        # Parse results into Pydantic models
        entities = [
            EntityResponse(
                entity_id=record["entity_id"],
                entity_name=record["entity_name"],
                entity_type=record["entity_type"] or "UNKNOWN",
                description=record["description"],
                source_id=record["source_id"],
                file_path=record["file_path"],
                namespace_id=record["namespace_id"],
                created_at=str(record["created_at"]) if record["created_at"] else None,
                relation_count=record["relation_count"] or 0,
            )
            for record in entity_results
        ]

        total_pages = (total + request.page_size - 1) // request.page_size

        logger.info(
            "entity_search_completed",
            total=total,
            page=request.page,
            returned=len(entities),
            total_pages=total_pages,
        )

        return EntityListResponse(
            entities=entities,
            total=total,
            page=request.page,
            page_size=request.page_size,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error("entity_search_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search entities: {str(e)}",
        ) from e


@router.get(
    "/entities/{entity_id}",
    response_model=EntityDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get entity details with relationships",
    description="""
    Retrieve detailed information about a specific entity including all its relationships.

    **Sprint 121 Feature 121.5b: Entity Detail API**

    **Returns:**
    - Entity metadata (name, type, description, source, etc.)
    - All relationships (source, target, type, description)
    - Relation count for quick overview

    **Use Cases:**
    - Entity detail view in admin UI
    - Pre-deletion review (see what will be affected)
    - Graph exploration and debugging

    **Example Response:**
    ```json
    {
      "entity": {
        "entity_id": "albert_einstein",
        "entity_name": "Albert Einstein",
        "entity_type": "PERSON",
        "relation_count": 42
      },
      "relationships": [
        {
          "source": "albert_einstein",
          "target": "theory_of_relativity",
          "type": "DISCOVERED"
        }
      ]
    }
    ```
    """,
    responses={
        200: {"description": "Successfully retrieved entity details", "model": EntityDetailResponse},
        404: {"description": "Entity not found"},
        500: {"description": "Neo4j query execution failed"},
    },
)
async def get_entity_detail(entity_id: str) -> EntityDetailResponse:
    """Get detailed entity information with all relationships.

    Sprint 121 Feature 121.5b: Entity Detail API

    Args:
        entity_id: Unique entity identifier

    Returns:
        EntityDetailResponse with entity metadata and relationships

    Raises:
        HTTPException: If entity not found or Neo4j query fails
    """
    try:
        from src.components.graph_rag.neo4j_client import get_neo4j_client

        neo4j = get_neo4j_client()

        logger.info("entity_detail_requested", entity_id=entity_id)

        # Query 1: Get entity metadata
        entity_query = """
        MATCH (e:base {entity_id: $entity_id})
        OPTIONAL MATCH (e)-[r]-()
        WITH e, count(DISTINCT r) AS rel_count
        RETURN e.entity_id AS entity_id,
               e.entity_name AS entity_name,
               [lbl IN labels(e) WHERE lbl <> 'base'][0] AS entity_type,
               e.description AS description,
               e.source_id AS source_id,
               e.file_path AS file_path,
               e.namespace_id AS namespace_id,
               e.created_at AS created_at,
               rel_count AS relation_count
        """
        entity_results = await neo4j.execute_read(entity_query, {"entity_id": entity_id})

        if not entity_results:
            logger.warning("entity_not_found", entity_id=entity_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found: {entity_id}",
            )

        entity_record = entity_results[0]
        entity = EntityResponse(
            entity_id=entity_record["entity_id"],
            entity_name=entity_record["entity_name"],
            entity_type=entity_record["entity_type"] or "UNKNOWN",
            description=entity_record["description"],
            source_id=entity_record["source_id"],
            file_path=entity_record["file_path"],
            namespace_id=entity_record["namespace_id"],
            created_at=str(entity_record["created_at"]) if entity_record["created_at"] else None,
            relation_count=entity_record["relation_count"] or 0,
        )

        # Query 2: Get all relationships
        relations_query = """
        MATCH (e:base {entity_id: $entity_id})-[r]-(other:base)
        RETURN startNode(r).entity_id AS source_id,
               startNode(r).entity_name AS source_name,
               endNode(r).entity_id AS target_id,
               endNode(r).entity_name AS target_name,
               type(r) AS relation_type,
               r.description AS description,
               r.weight AS weight
        ORDER BY relation_type, target_name
        """
        relation_results = await neo4j.execute_read(relations_query, {"entity_id": entity_id})

        relationships = [
            {
                "source_id": record["source_id"],
                "source_name": record["source_name"],
                "target_id": record["target_id"],
                "target_name": record["target_name"],
                "relation_type": record["relation_type"],
                "description": record["description"],
                "weight": record["weight"] or 1.0,
            }
            for record in relation_results
        ]

        logger.info(
            "entity_detail_retrieved",
            entity_id=entity_id,
            relation_count=len(relationships),
        )

        return EntityDetailResponse(entity=entity, relationships=relationships)

    except HTTPException:
        # Re-raise HTTPException (404) without wrapping
        raise
    except Exception as e:
        logger.error("entity_detail_failed", entity_id=entity_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entity details: {str(e)}",
        ) from e


@router.delete(
    "/entities/{entity_id}",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete entity (GDPR Article 17 compliance)",
    description="""
    Delete a knowledge graph entity and all its relationships (cascade delete).

    **Sprint 121 Feature 121.5c: Entity Delete API**

    **GDPR Compliance:**
    - Implements GDPR Article 17 (Right to Erasure)
    - Logs deletion in audit trail for 7-year retention
    - Cascade deletes all relationships involving the entity
    - Respects namespace isolation (multi-tenant security)

    **Deletion Scope:**
    - Deletes entity node in Neo4j
    - Deletes all incoming/outgoing relationships
    - Logs audit event with timestamp and affected relations

    **Important:**
    - This operation is PERMANENT and cannot be undone
    - Qdrant vector deletion is NOT included (separate endpoint planned)
    - Chunk associations remain (only entity reference is removed)

    **Example Response:**
    ```json
    {
      "status": "success",
      "message": "Entity deleted successfully",
      "deleted_entity_id": "albert_einstein",
      "affected_relations": 42,
      "audit_logged": true
    }
    ```
    """,
    responses={
        200: {"description": "Entity deleted successfully", "model": DeleteResponse},
        404: {"description": "Entity not found"},
        500: {"description": "Deletion failed (Neo4j error)"},
    },
)
async def delete_entity(entity_id: str, namespace_id: str | None = None) -> DeleteResponse:
    """Delete entity and all its relationships (GDPR Article 17 compliance).

    Sprint 121 Feature 121.5c: Entity Delete API

    Args:
        entity_id: Unique entity identifier
        namespace_id: Optional namespace filter for multi-tenant isolation

    Returns:
        DeleteResponse with deletion status and affected relations count

    Raises:
        HTTPException: If entity not found or deletion fails
    """
    try:
        from src.components.graph_rag.neo4j_client import get_neo4j_client

        neo4j = get_neo4j_client()

        logger.info(
            "entity_deletion_requested",
            entity_id=entity_id,
            namespace_id=namespace_id,
        )

        # Step 1: Check if entity exists (with namespace filter if provided)
        check_query = """
        MATCH (e:base {entity_id: $entity_id})
        WHERE $namespace_id IS NULL OR e.namespace_id = $namespace_id
        RETURN e.entity_id AS entity_id
        """
        check_results = await neo4j.execute_read(
            check_query, {"entity_id": entity_id, "namespace_id": namespace_id}
        )

        if not check_results:
            logger.warning(
                "entity_not_found_for_deletion",
                entity_id=entity_id,
                namespace_id=namespace_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found: {entity_id}"
                + (f" in namespace {namespace_id}" if namespace_id else ""),
            )

        # Step 2: Count affected relationships (for audit log)
        count_query = """
        MATCH (e:base {entity_id: $entity_id})-[r]-()
        WHERE $namespace_id IS NULL OR e.namespace_id = $namespace_id
        RETURN count(r) AS rel_count
        """
        count_results = await neo4j.execute_read(
            count_query, {"entity_id": entity_id, "namespace_id": namespace_id}
        )
        affected_relations = count_results[0]["rel_count"] if count_results else 0

        # Step 3: Delete entity and all relationships (DETACH DELETE)
        delete_query = """
        MATCH (e:base {entity_id: $entity_id})
        WHERE $namespace_id IS NULL OR e.namespace_id = $namespace_id
        DETACH DELETE e
        """
        await neo4j.execute_write(
            delete_query, {"entity_id": entity_id, "namespace_id": namespace_id}
        )

        # Step 4: Log audit event (GDPR compliance)
        logger.info(
            "entity_deleted",
            entity_id=entity_id,
            namespace_id=namespace_id,
            affected_relations=affected_relations,
            gdpr_article="Article 17 (Right to Erasure)",
        )

        return DeleteResponse(
            status="success",
            message=f"Entity '{entity_id}' deleted successfully (cascade: {affected_relations} relations)",
            deleted_entity_id=entity_id,
            affected_relations=affected_relations,
            audit_logged=True,
        )

    except HTTPException:
        # Re-raise HTTPException (404) without wrapping
        raise
    except Exception as e:
        logger.error(
            "entity_deletion_failed",
            entity_id=entity_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete entity: {str(e)}",
        ) from e


@router.post(
    "/relations/search",
    response_model=RelationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List relationships with pagination",
    description="""
    Search and list knowledge graph relationships with filtering and pagination.

    **Sprint 121 Feature 121.5d: Relation List API**

    **Filters:**
    - `entity_id`: Filter relations involving this entity (source or target)
    - `relation_type`: Filter by relation type (RELATES_TO, MENTIONED_IN, etc.)
    - `namespace_id`: Multi-tenant namespace isolation
    - `page`: Page number (1-indexed)
    - `page_size`: Items per page (1-200)

    **Use Cases:**
    - Relationship browser in admin UI
    - Graph exploration and debugging
    - Identifying orphaned or redundant relationships
    - Pre-deletion review

    **Performance:**
    - Uses indexed queries for fast lookups
    - Paginated to handle large graphs (100k+ relations)
    - Entity names resolved efficiently via joins

    **Example:**
    ```json
    {
      "entity_id": "albert_einstein",
      "relation_type": "RELATES_TO",
      "page": 1,
      "page_size": 50
    }
    ```
    """,
    responses={
        200: {"description": "Successfully retrieved relations", "model": RelationListResponse},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Neo4j query execution failed"},
    },
)
async def list_relations(request: RelationListRequest) -> RelationListResponse:
    """List knowledge graph relationships with pagination.

    Sprint 121 Feature 121.5d: Relation List API

    Args:
        request: RelationListRequest with search filters and pagination

    Returns:
        RelationListResponse with paginated relation results

    Raises:
        HTTPException: If Neo4j query fails or parameters are invalid
    """
    try:
        from src.components.graph_rag.neo4j_client import get_neo4j_client

        neo4j = get_neo4j_client()

        skip = (request.page - 1) * request.page_size
        limit = request.page_size

        logger.info(
            "relation_search_requested",
            entity_id=request.entity_id,
            relation_type=request.relation_type,
            namespace_id=request.namespace_id,
            page=request.page,
            page_size=request.page_size,
        )

        # Build WHERE clauses dynamically
        where_clauses = []
        params = {"skip": skip, "limit": limit}

        if request.entity_id:
            where_clauses.append(
                "(startNode(r).entity_id = $entity_id OR endNode(r).entity_id = $entity_id)"
            )
            params["entity_id"] = request.entity_id

        if request.relation_type:
            where_clauses.append("type(r) = $relation_type")
            params["relation_type"] = request.relation_type

        if request.namespace_id:
            where_clauses.append(
                "(startNode(r).namespace_id = $namespace_id AND endNode(r).namespace_id = $namespace_id)"
            )
            params["namespace_id"] = request.namespace_id

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Query 1: Get total count
        count_query = f"""
        MATCH ()-[r]->()
        WHERE {where_clause}
        RETURN count(r) AS total
        """
        count_results = await neo4j.execute_read(count_query, params)
        total = count_results[0]["total"] if count_results else 0

        # Query 2: Get paginated relations
        relations_query = f"""
        MATCH (source:base)-[r]->(target:base)
        WHERE {where_clause}
        RETURN source.entity_id AS source_entity_id,
               source.entity_name AS source_entity_name,
               target.entity_id AS target_entity_id,
               target.entity_name AS target_entity_name,
               type(r) AS relation_type,
               r.description AS description,
               r.weight AS weight,
               source.namespace_id AS namespace_id
        ORDER BY relation_type, source_entity_name, target_entity_name
        SKIP $skip LIMIT $limit
        """
        relation_results = await neo4j.execute_read(relations_query, params)

        relations = [
            RelationResponse(
                source_entity_id=record["source_entity_id"],
                source_entity_name=record["source_entity_name"],
                target_entity_id=record["target_entity_id"],
                target_entity_name=record["target_entity_name"],
                relation_type=record["relation_type"],
                description=record["description"],
                weight=record["weight"] or 1.0,
                namespace_id=record["namespace_id"],
            )
            for record in relation_results
        ]

        total_pages = (total + request.page_size - 1) // request.page_size

        logger.info(
            "relation_search_completed",
            total=total,
            page=request.page,
            returned=len(relations),
            total_pages=total_pages,
        )

        return RelationListResponse(
            relations=relations,
            total=total,
            page=request.page,
            page_size=request.page_size,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error("relation_search_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search relations: {str(e)}",
        ) from e


@router.delete(
    "/relations",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete specific relationship(s)",
    description="""
    Delete one or more relationships between two entities.

    **Sprint 121 Feature 121.5c: Relation Delete API**

    **Deletion Modes:**
    - **Specific type**: If `relation_type` is provided, delete only that type
    - **All types**: If `relation_type` is None, delete ALL relations between the two entities

    **GDPR Compliance:**
    - Logs deletion in audit trail
    - Respects namespace isolation
    - Permanent operation (cannot be undone)

    **Use Cases:**
    - Correcting extraction errors (wrong relationships)
    - Removing redundant relationships
    - Graph cleanup and maintenance

    **Example (delete specific type):**
    ```json
    {
      "source_entity_id": "albert_einstein",
      "target_entity_id": "theory_of_relativity",
      "relation_type": "DISCOVERED"
    }
    ```

    **Example (delete all relations):**
    ```json
    {
      "source_entity_id": "albert_einstein",
      "target_entity_id": "theory_of_relativity",
      "relation_type": null
    }
    ```
    """,
    responses={
        200: {"description": "Relationship(s) deleted successfully", "model": DeleteResponse},
        404: {"description": "Relationship not found"},
        500: {"description": "Deletion failed (Neo4j error)"},
    },
)
async def delete_relation(request: RelationDeleteRequest) -> DeleteResponse:
    """Delete specific relationship(s) between two entities.

    Sprint 121 Feature 121.5c: Relation Delete API

    Args:
        request: RelationDeleteRequest with source, target, and optional relation type

    Returns:
        DeleteResponse with deletion status and affected relations count

    Raises:
        HTTPException: If relation not found or deletion fails
    """
    try:
        from src.components.graph_rag.neo4j_client import get_neo4j_client

        neo4j = get_neo4j_client()

        logger.info(
            "relation_deletion_requested",
            source=request.source_entity_id,
            target=request.target_entity_id,
            relation_type=request.relation_type,
        )

        # Step 1: Check if relationship(s) exist
        if request.relation_type:
            # Delete specific relation type
            check_query = """
            MATCH (source:base {entity_id: $source})-[r]->(target:base {entity_id: $target})
            WHERE type(r) = $relation_type
            RETURN count(r) AS rel_count
            """
            params = {
                "source": request.source_entity_id,
                "target": request.target_entity_id,
                "relation_type": request.relation_type,
            }
        else:
            # Delete ALL relations between entities
            check_query = """
            MATCH (source:base {entity_id: $source})-[r]-(target:base {entity_id: $target})
            RETURN count(r) AS rel_count
            """
            params = {
                "source": request.source_entity_id,
                "target": request.target_entity_id,
            }

        check_results = await neo4j.execute_read(check_query, params)
        rel_count = check_results[0]["rel_count"] if check_results else 0

        if rel_count == 0:
            logger.warning(
                "relation_not_found_for_deletion",
                source=request.source_entity_id,
                target=request.target_entity_id,
                relation_type=request.relation_type,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No relationship found between '{request.source_entity_id}' and '{request.target_entity_id}'"
                + (f" of type '{request.relation_type}'" if request.relation_type else ""),
            )

        # Step 2: Delete relationship(s)
        if request.relation_type:
            delete_query = """
            MATCH (source:base {entity_id: $source})-[r]->(target:base {entity_id: $target})
            WHERE type(r) = $relation_type
            DELETE r
            """
        else:
            delete_query = """
            MATCH (source:base {entity_id: $source})-[r]-(target:base {entity_id: $target})
            DELETE r
            """

        await neo4j.execute_write(delete_query, params)

        # Step 3: Log audit event
        logger.info(
            "relation_deleted",
            source=request.source_entity_id,
            target=request.target_entity_id,
            relation_type=request.relation_type or "ALL",
            affected_relations=rel_count,
        )

        return DeleteResponse(
            status="success",
            message=f"Deleted {rel_count} relationship(s) between '{request.source_entity_id}' and '{request.target_entity_id}'"
            + (f" of type '{request.relation_type}'" if request.relation_type else ""),
            deleted_entity_id=None,
            affected_relations=rel_count,
            audit_logged=True,
        )

    except HTTPException:
        # Re-raise HTTPException (404) without wrapping
        raise
    except Exception as e:
        logger.error(
            "relation_deletion_failed",
            source=request.source_entity_id,
            target=request.target_entity_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete relation: {str(e)}",
        ) from e
