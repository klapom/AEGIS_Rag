/**
 * EntityManagementPage Component
 * Sprint 121 Feature 121.5e: Entity Management Frontend UI
 *
 * Main admin page for managing knowledge graph entities and relationships.
 * Features:
 * - Tab layout: Entities | Relations
 * - Entity search, filtering, and pagination
 * - Entity detail view with relationships
 * - Entity deletion (GDPR Article 17 compliance)
 * - Relation search and deletion
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Database,
  Search,
  Eye,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Network,
  AlertTriangle,
  X,
  Share2,
  FileText,
} from 'lucide-react';
import { ContextMenu } from '../../components/ui/ContextMenu';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';
import type {
  GraphEntity,
  GraphEntityDetail,
  GraphRelationship,
  EntityListResponse,
  RelationListResponse,
} from '../../types/admin';
import {
  searchEntities,
  getEntityDetail,
  deleteEntity,
  searchRelations,
  deleteRelation,
} from '../../api/graphEntities';
import { getNamespaces } from '../../api/admin';

/**
 * Tab type for the entity management page
 */
type EntityTab = 'entities' | 'relations';

/**
 * EntityManagementPage - Main entity management admin page
 */
export function EntityManagementPage() {
  const [activeTab, setActiveTab] = useState<EntityTab>('entities');

  return (
    <div
      className="min-h-screen bg-gray-50 dark:bg-gray-900"
      data-testid="entity-management-page"
    >
      {/* Admin Navigation */}
      <div className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <AdminNavigationBar />
      </div>

      {/* Page Header */}
      <div className="bg-white dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700 px-6 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Database className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            <div>
              <h1
                className="text-2xl font-bold text-gray-900 dark:text-gray-100"
                data-testid="page-title"
              >
                Entity Management
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Manage knowledge graph entities and relations
              </p>
            </div>
          </div>

          {/* Tabs */}
          <div
            className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1"
            role="tablist"
            data-testid="entity-tabs-container"
          >
            <button
              role="tab"
              aria-selected={activeTab === 'entities'}
              onClick={() => setActiveTab('entities')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'entities'
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
              data-testid="tab-entities"
            >
              <Database className="w-4 h-4" />
              Entities
            </button>
            <button
              role="tab"
              aria-selected={activeTab === 'relations'}
              onClick={() => setActiveTab('relations')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'relations'
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
              data-testid="tab-relations"
            >
              <Network className="w-4 h-4" />
              Relations
            </button>
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="p-6" data-testid="tab-content-wrapper">
        <div className="max-w-7xl mx-auto">
          {activeTab === 'entities' && <EntitiesTab />}
          {activeTab === 'relations' && <RelationsTab />}
        </div>
      </div>
    </div>
  );
}

/**
 * Entities Tab Component
 */
function EntitiesTab() {
  const [entities, setEntities] = useState<GraphEntity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [namespaceFilter, setNamespaceFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [selectedEntity, setSelectedEntity] = useState<GraphEntityDetail | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [namespaces, setNamespaces] = useState<Array<{ namespace_id: string }>>([]);
  const [entityTypes, setEntityTypes] = useState<string[]>([]);

  const pageSize = 20;

  // Load namespaces
  useEffect(() => {
    const loadNamespaces = async () => {
      try {
        const result = await getNamespaces();
        setNamespaces(result.namespaces);
      } catch (err) {
        console.error('Failed to load namespaces:', err);
      }
    };
    loadNamespaces();
  }, []);

  // Load entities
  const loadEntities = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result: EntityListResponse = await searchEntities({
        search: searchTerm || undefined,
        entity_type: entityTypeFilter || undefined,
        namespace_id: namespaceFilter || undefined,
        page,
        page_size: pageSize,
      });
      setEntities(result.entities);
      setTotalPages(result.total_pages);
      setTotalCount(result.total);

      // Extract unique entity types
      const types = [...new Set(result.entities.map((e) => e.entity_type))];
      setEntityTypes((prev) => [...new Set([...prev, ...types])]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load entities');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, entityTypeFilter, namespaceFilter, page]);

  useEffect(() => {
    loadEntities();
  }, [loadEntities]);

  // View entity detail
  const handleViewEntity = async (entityId: string) => {
    try {
      const detail = await getEntityDetail(entityId);
      setSelectedEntity(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load entity detail');
    }
  };

  // Delete entity
  const handleDeleteEntity = async (entityId: string) => {
    try {
      await deleteEntity(entityId, namespaceFilter || undefined);
      setDeleteConfirm(null);
      setSelectedEntity(null);
      loadEntities();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete entity');
    }
  };

  return (
    <div data-testid="entities-tab-content">
      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Search Entity Name
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setPage(1);
                }}
                placeholder="Search by name..."
                className="w-full pl-10 pr-4 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                data-testid="entity-search-input"
              />
            </div>
          </div>

          {/* Entity Type Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Entity Type
            </label>
            <select
              value={entityTypeFilter}
              onChange={(e) => {
                setEntityTypeFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-4 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              data-testid="entity-type-filter"
            >
              <option value="">All Types</option>
              {entityTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          {/* Namespace Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Namespace
            </label>
            <select
              value={namespaceFilter}
              onChange={(e) => {
                setNamespaceFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-4 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              data-testid="namespace-filter"
            >
              <option value="">All Namespaces</option>
              {namespaces.map((ns) => (
                <option key={ns.namespace_id} value={ns.namespace_id}>
                  {ns.namespace_id}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div
          className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg p-4 mb-6"
          data-testid="error-message"
        >
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12" data-testid="loading-state">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-600"></div>
          <p className="text-gray-600 dark:text-gray-400 mt-4">Loading entities...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && entities.length === 0 && (
        <div
          className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700"
          data-testid="empty-state"
        >
          <Database className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">No entities found</p>
          <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
            Try adjusting your filters or search term
          </p>
        </div>
      )}

      {/* Entities Table */}
      {!loading && entities.length > 0 && (
        <>
          <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 overflow-hidden">
            <table className="w-full" data-testid="entities-table">
              <thead className="bg-gray-50 dark:bg-gray-700 border-b-2 border-gray-200 dark:border-gray-600">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Relations
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Namespace
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {entities.map((entity) => (
                  <tr
                    key={entity.entity_id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700"
                    data-testid={`entity-row-${entity.entity_id}`}
                  >
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {entity.entity_name}
                      </div>
                      {entity.description && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {entity.description.slice(0, 80)}
                          {entity.description.length > 80 ? '...' : ''}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
                        {entity.entity_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-100">
                      {entity.relation_count}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      {entity.namespace_id || 'default'}
                    </td>
                    <td className="px-6 py-4 text-right text-sm font-medium">
                      <button
                        onClick={() => handleViewEntity(entity.entity_id)}
                        className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 mr-4"
                        data-testid={`view-entity-${entity.entity_id}`}
                      >
                        <Eye className="w-4 h-4 inline" />
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(entity.entity_id)}
                        className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
                        data-testid={`delete-entity-${entity.entity_id}`}
                      >
                        <Trash2 className="w-4 h-4 inline" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-6" data-testid="pagination">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, totalCount)} of{' '}
              {totalCount} entities
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="flex items-center gap-1 px-4 py-2 text-sm font-medium border-2 border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
                data-testid="prev-page"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>
              <div className="flex items-center px-4 text-sm text-gray-600 dark:text-gray-400">
                Page {page} of {totalPages}
              </div>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="flex items-center gap-1 px-4 py-2 text-sm font-medium border-2 border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
                data-testid="next-page"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      )}

      {/* Entity Detail Panel */}
      {selectedEntity && (
        <EntityDetailPanel
          entity={selectedEntity}
          onClose={() => setSelectedEntity(null)}
          onDelete={() => setDeleteConfirm(selectedEntity.entity.entity_id)}
        />
      )}

      {/* Delete Confirmation Dialog */}
      {deleteConfirm && (
        <DeleteConfirmDialog
          entityId={deleteConfirm}
          entityName={
            entities.find((e) => e.entity_id === deleteConfirm)?.entity_name || deleteConfirm
          }
          relationCount={
            entities.find((e) => e.entity_id === deleteConfirm)?.relation_count || 0
          }
          onConfirm={() => handleDeleteEntity(deleteConfirm)}
          onCancel={() => setDeleteConfirm(null)}
        />
      )}
    </div>
  );
}

/**
 * Relations Tab Component
 */
function RelationsTab() {
  const navigate = useNavigate();
  const [relations, setRelations] = useState<GraphRelationship[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entityIdFilter, setEntityIdFilter] = useState('');
  const [relationTypeFilter, setRelationTypeFilter] = useState('');
  const [namespaceFilter, setNamespaceFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [deleteConfirm, setDeleteConfirm] = useState<GraphRelationship | null>(null);
  const [namespaces, setNamespaces] = useState<Array<{ namespace_id: string }>>([]);
  const [relationTypes, setRelationTypes] = useState<string[]>([]);
  const [selectedEntityForDetail, setSelectedEntityForDetail] = useState<string | null>(null);
  const [entityDetailLoading, setEntityDetailLoading] = useState(false);
  const [entityDetail, setEntityDetail] = useState<import('../../types/admin').GraphEntityDetail | null>(null);

  // Helper: Navigate to graph visualization for an entity
  const showEntityInGraph = (entityName: string) => {
    navigate(`/admin/graph?entity=${encodeURIComponent(entityName)}&tab=visualization`);
  };

  // Helper: Navigate to graph visualization for a namespace
  const showNamespaceInGraph = (namespaceId: string) => {
    navigate(`/admin/graph?namespace=${encodeURIComponent(namespaceId)}&tab=visualization`);
  };

  // Helper: Load and show entity detail
  const showEntityDetail = async (entityId: string) => {
    setEntityDetailLoading(true);
    try {
      const detail = await getEntityDetail(entityId);
      setEntityDetail(detail);
      setSelectedEntityForDetail(entityId);
    } catch (err) {
      console.error('Failed to load entity detail:', err);
    } finally {
      setEntityDetailLoading(false);
    }
  };

  const pageSize = 20;

  // Load namespaces
  useEffect(() => {
    const loadNamespaces = async () => {
      try {
        const result = await getNamespaces();
        setNamespaces(result.namespaces);
      } catch (err) {
        console.error('Failed to load namespaces:', err);
      }
    };
    loadNamespaces();
  }, []);

  // Load relations
  const loadRelations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result: RelationListResponse = await searchRelations({
        entity_id: entityIdFilter || undefined,
        relation_type: relationTypeFilter || undefined,
        namespace_id: namespaceFilter || undefined,
        page,
        page_size: pageSize,
      });
      setRelations(result.relations);
      setTotalPages(result.total_pages);
      setTotalCount(result.total);

      // Extract unique relation types
      const types = [...new Set(result.relations.map((r) => r.relation_type))];
      setRelationTypes((prev) => [...new Set([...prev, ...types])]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load relations');
    } finally {
      setLoading(false);
    }
  }, [entityIdFilter, relationTypeFilter, namespaceFilter, page]);

  useEffect(() => {
    loadRelations();
  }, [loadRelations]);

  // Delete relation
  const handleDeleteRelation = async (relation: GraphRelationship) => {
    try {
      await deleteRelation({
        source_entity_id: relation.source_entity_id || relation.source_id || '',
        target_entity_id: relation.target_entity_id || relation.target_id || '',
        relation_type: relation.relation_type,
      });
      setDeleteConfirm(null);
      loadRelations();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete relation');
    }
  };

  return (
    <div data-testid="relations-tab-content">
      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Entity ID Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Entity ID
            </label>
            <input
              type="text"
              value={entityIdFilter}
              onChange={(e) => {
                setEntityIdFilter(e.target.value);
                setPage(1);
              }}
              placeholder="Filter by entity ID..."
              className="w-full px-4 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              data-testid="entity-id-filter"
            />
          </div>

          {/* Relation Type Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Relation Type
            </label>
            <select
              value={relationTypeFilter}
              onChange={(e) => {
                setRelationTypeFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-4 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              data-testid="relation-type-filter"
            >
              <option value="">All Types</option>
              {relationTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          {/* Namespace Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Namespace
            </label>
            <select
              value={namespaceFilter}
              onChange={(e) => {
                setNamespaceFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-4 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              data-testid="namespace-filter-relations"
            >
              <option value="">All Namespaces</option>
              {namespaces.map((ns) => (
                <option key={ns.namespace_id} value={ns.namespace_id}>
                  {ns.namespace_id}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div
          className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg p-4 mb-6"
          data-testid="error-message-relations"
        >
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12" data-testid="loading-state-relations">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-600"></div>
          <p className="text-gray-600 dark:text-gray-400 mt-4">Loading relations...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && relations.length === 0 && (
        <div
          className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700"
          data-testid="empty-state-relations"
        >
          <Network className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">No relations found</p>
          <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
            Try adjusting your filters
          </p>
        </div>
      )}

      {/* Relations Table */}
      {!loading && relations.length > 0 && (
        <>
          <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 overflow-hidden">
            <table className="w-full" data-testid="relations-table">
              <thead className="bg-gray-50 dark:bg-gray-700 border-b-2 border-gray-200 dark:border-gray-600">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Source Entity
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Relation Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Target Entity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Namespace
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {relations.map((relation, idx) => (
                  <tr
                    key={`${relation.source_id}-${relation.target_id}-${relation.relation_type}-${idx}`}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700"
                    data-testid={`relation-row-${idx}`}
                  >
                    {/* Source Entity with Context Menu */}
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {relation.source_entity_name || relation.source_name}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {relation.source_entity_id || relation.source_id}
                          </div>
                        </div>
                        <ContextMenu
                          data-testid={`source-menu-${idx}`}
                          items={[
                            {
                              label: 'Show in Graph',
                              icon: <Share2 className="w-4 h-4" />,
                              onClick: () => showEntityInGraph(relation.source_entity_name || relation.source_name || ''),
                            },
                            {
                              label: 'Show Entity Details',
                              icon: <FileText className="w-4 h-4" />,
                              onClick: () => showEntityDetail(relation.source_entity_id || relation.source_id || ''),
                            },
                          ]}
                        />
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                        {relation.relation_type}
                      </span>
                    </td>
                    {/* Target Entity with Context Menu */}
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {relation.target_entity_name || relation.target_name}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {relation.target_entity_id || relation.target_id}
                          </div>
                        </div>
                        <ContextMenu
                          data-testid={`target-menu-${idx}`}
                          items={[
                            {
                              label: 'Show in Graph',
                              icon: <Share2 className="w-4 h-4" />,
                              onClick: () => showEntityInGraph(relation.target_entity_name || relation.target_name || ''),
                            },
                            {
                              label: 'Show Entity Details',
                              icon: <FileText className="w-4 h-4" />,
                              onClick: () => showEntityDetail(relation.target_entity_id || relation.target_id || ''),
                            },
                          ]}
                        />
                      </div>
                    </td>
                    {/* Namespace with Context Menu */}
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                          {relation.namespace_id || namespaceFilter || 'default'}
                        </span>
                        <ContextMenu
                          data-testid={`namespace-menu-${idx}`}
                          items={[
                            {
                              label: 'Show Namespace in Graph',
                              icon: <Network className="w-4 h-4" />,
                              onClick: () => showNamespaceInGraph(relation.namespace_id || namespaceFilter || 'default'),
                            },
                          ]}
                        />
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right text-sm font-medium">
                      <button
                        onClick={() => setDeleteConfirm(relation)}
                        className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
                        data-testid={`delete-relation-${idx}`}
                      >
                        <Trash2 className="w-4 h-4 inline" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-6" data-testid="pagination-relations">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, totalCount)} of{' '}
              {totalCount} relations
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="flex items-center gap-1 px-4 py-2 text-sm font-medium border-2 border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
                data-testid="prev-page-relations"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>
              <div className="flex items-center px-4 text-sm text-gray-600 dark:text-gray-400">
                Page {page} of {totalPages}
              </div>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="flex items-center gap-1 px-4 py-2 text-sm font-medium border-2 border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
                data-testid="next-page-relations"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      )}

      {/* Delete Confirmation Dialog for Relations */}
      {deleteConfirm && (
        <RelationDeleteConfirmDialog
          relation={deleteConfirm}
          onConfirm={() => handleDeleteRelation(deleteConfirm)}
          onCancel={() => setDeleteConfirm(null)}
        />
      )}

      {/* Entity Detail Panel (from context menu) */}
      {entityDetail && (
        <EntityDetailPanel
          entity={entityDetail}
          onClose={() => {
            setEntityDetail(null);
            setSelectedEntityForDetail(null);
          }}
          onDelete={() => {
            // Close panel after noting the entity ID for potential deletion
            setEntityDetail(null);
            setSelectedEntityForDetail(null);
          }}
        />
      )}

      {/* Loading overlay for entity detail */}
      {entityDetailLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-40">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-xl">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-600"></div>
            <p className="text-gray-600 dark:text-gray-400 mt-4">Loading entity details...</p>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Entity Detail Panel Component
 */
interface EntityDetailPanelProps {
  entity: GraphEntityDetail;
  onClose: () => void;
  onDelete: () => void;
}

function EntityDetailPanel({ entity, onClose, onDelete }: EntityDetailPanelProps) {
  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      data-testid="entity-detail-panel"
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b-2 border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Database className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                {entity.entity.entity_name}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {entity.entity.entity_type}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            data-testid="close-detail-panel"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Entity Metadata */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Metadata
          </h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500 dark:text-gray-400">Entity ID:</span>
              <span className="ml-2 text-gray-900 dark:text-gray-100 font-mono">
                {entity.entity.entity_id}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Namespace:</span>
              <span className="ml-2 text-gray-900 dark:text-gray-100">
                {entity.entity.namespace_id || 'default'}
              </span>
            </div>
            {entity.entity.source_id && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">Source ID:</span>
                <span className="ml-2 text-gray-900 dark:text-gray-100 font-mono">
                  {entity.entity.source_id}
                </span>
              </div>
            )}
            {entity.entity.file_path && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">File Path:</span>
                <span className="ml-2 text-gray-900 dark:text-gray-100 font-mono text-xs">
                  {entity.entity.file_path}
                </span>
              </div>
            )}
          </div>
          {entity.entity.description && (
            <div className="mt-4">
              <span className="text-gray-500 dark:text-gray-400">Description:</span>
              <p className="text-gray-900 dark:text-gray-100 mt-1">
                {entity.entity.description}
              </p>
            </div>
          )}
        </div>

        {/* Relationships */}
        <div className="p-6">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Relationships ({entity.relationships.length})
          </h3>
          {entity.relationships.length === 0 ? (
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              No relationships found for this entity.
            </p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {entity.relationships.map((rel, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg text-sm"
                  data-testid={`relationship-${idx}`}
                >
                  <span className="text-gray-900 dark:text-gray-100 font-medium">
                    {rel.source_entity_name || rel.source_name}
                  </span>
                  <span className="text-gray-400">→</span>
                  <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded text-xs">
                    {rel.relation_type}
                  </span>
                  <span className="text-gray-400">→</span>
                  <span className="text-gray-900 dark:text-gray-100 font-medium">
                    {rel.target_entity_name || rel.target_name}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 p-6 border-t-2 border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium border-2 border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            data-testid="close-button"
          >
            Close
          </button>
          <button
            onClick={onDelete}
            className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700"
            data-testid="delete-button"
          >
            <Trash2 className="w-4 h-4 inline mr-2" />
            Delete Entity
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Delete Confirmation Dialog Component
 */
interface DeleteConfirmDialogProps {
  entityId: string;
  entityName: string;
  relationCount: number;
  onConfirm: () => void;
  onCancel: () => void;
}

function DeleteConfirmDialog({
  entityId,
  entityName,
  relationCount,
  onConfirm,
  onCancel,
}: DeleteConfirmDialogProps) {
  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      data-testid="delete-confirm-dialog"
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex items-start gap-4 mb-4">
          <div className="flex-shrink-0">
            <AlertTriangle className="w-6 h-6 text-red-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Delete Entity?
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Are you sure you want to delete the entity <strong>{entityName}</strong> (
              {entityId})?
            </p>
            <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg p-3 mb-4">
              <p className="text-sm text-red-800 dark:text-red-200">
                <strong>Warning:</strong> This action is permanent and cannot be undone.
              </p>
              <p className="text-sm text-red-800 dark:text-red-200 mt-2">
                This will also delete <strong>{relationCount} relationship(s)</strong>{' '}
                involving this entity.
              </p>
              <p className="text-xs text-red-700 dark:text-red-300 mt-2">
                GDPR Article 17: Right to Erasure
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium border-2 border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            data-testid="cancel-delete"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700"
            data-testid="confirm-delete"
          >
            Delete Entity
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Relation Delete Confirmation Dialog Component
 */
interface RelationDeleteConfirmDialogProps {
  relation: GraphRelationship;
  onConfirm: () => void;
  onCancel: () => void;
}

function RelationDeleteConfirmDialog({
  relation,
  onConfirm,
  onCancel,
}: RelationDeleteConfirmDialogProps) {
  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      data-testid="delete-relation-dialog"
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex items-start gap-4 mb-4">
          <div className="flex-shrink-0">
            <AlertTriangle className="w-6 h-6 text-red-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Delete Relation?
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Are you sure you want to delete this relationship?
            </p>
            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 mb-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {relation.source_entity_name || relation.source_name}
                </span>
                <span className="text-gray-400">→</span>
                <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded text-xs">
                  {relation.relation_type}
                </span>
                <span className="text-gray-400">→</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {relation.target_entity_name || relation.target_name}
                </span>
              </div>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg p-3">
              <p className="text-sm text-red-800 dark:text-red-200">
                <strong>Warning:</strong> This action is permanent and cannot be undone.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium border-2 border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            data-testid="cancel-delete-relation"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700"
            data-testid="confirm-delete-relation"
          >
            Delete Relation
          </button>
        </div>
      </div>
    </div>
  );
}

export default EntityManagementPage;
