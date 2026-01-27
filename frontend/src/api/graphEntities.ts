/**
 * Graph Entities API Client
 * Sprint 121 Feature 121.5e: Entity Management Frontend UI
 *
 * API functions for managing knowledge graph entities and relationships.
 * Provides CRUD operations for entity and relation management with pagination.
 */

import type {
  EntitySearchRequest,
  EntityListResponse,
  GraphEntityDetail,
  EntityDeleteResponse,
  RelationSearchRequest,
  RelationListResponse,
  RelationDeleteRequest,
} from '../types/admin';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Search/list entities with pagination and filtering
 * Sprint 121 Feature 121.5a: Entity List/Search API
 *
 * @param request Search parameters (search, entity_type, namespace_id, page, page_size)
 * @returns EntityListResponse with paginated entity results
 */
export async function searchEntities(
  request: EntitySearchRequest
): Promise<EntityListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/graph/entities/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Get entity details with all relationships
 * Sprint 121 Feature 121.5b: Entity Detail API
 *
 * @param entityId The entity ID to retrieve
 * @returns GraphEntityDetail with entity metadata and relationships
 */
export async function getEntityDetail(entityId: string): Promise<GraphEntityDetail> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/graph/entities/${encodeURIComponent(entityId)}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Delete an entity and all its relationships (GDPR Article 17 compliance)
 * Sprint 121 Feature 121.5c: Entity Delete API
 *
 * @param entityId The entity ID to delete
 * @param namespaceId Optional namespace filter for multi-tenant isolation
 * @returns EntityDeleteResponse with deletion status and affected relations count
 */
export async function deleteEntity(
  entityId: string,
  namespaceId?: string
): Promise<EntityDeleteResponse> {
  const params = new URLSearchParams();
  if (namespaceId) {
    params.append('namespace_id', namespaceId);
  }

  const url = `${API_BASE_URL}/api/v1/admin/graph/entities/${encodeURIComponent(entityId)}${
    params.toString() ? `?${params.toString()}` : ''
  }`;

  const response = await fetch(url, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Search/list relationships with pagination and filtering
 * Sprint 121 Feature 121.5d: Relation List API
 *
 * @param request Search parameters (entity_id, relation_type, namespace_id, page, page_size)
 * @returns RelationListResponse with paginated relation results
 */
export async function searchRelations(
  request: RelationSearchRequest
): Promise<RelationListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/graph/relations/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Delete specific relationship(s) between two entities
 * Sprint 121 Feature 121.5c: Relation Delete API
 *
 * @param request Relation delete parameters (source_entity_id, target_entity_id, relation_type)
 * @returns EntityDeleteResponse with deletion status and affected relations count
 */
export async function deleteRelation(
  request: RelationDeleteRequest
): Promise<EntityDeleteResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/graph/relations`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}
