/**
 * SectionCommunitiesDialog Component
 * Sprint 71 Feature 71.16: Section-Level Community Visualization
 *
 * Dialog for viewing communities within a specific document section
 * with searchable document and section selection
 */

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { useSectionCommunities } from '../../hooks/useGraphCommunities';
import { useDocuments, useDocumentSections } from '../../hooks/useDocuments';
import { SearchableSelect } from '../ui/SearchableSelect';
import type { SectionCommunitiesRequest, CommunityVisualization } from '../../types/graph';

interface SectionCommunitiesDialogProps {
  isOpen: boolean;
  onClose: () => void;
  documentId?: string;
  sectionId?: string;
}

export function SectionCommunitiesDialog({
  isOpen,
  onClose,
  documentId: initialDocumentId,
  sectionId: initialSectionId,
}: SectionCommunitiesDialogProps) {
  const { data, isLoading, error, fetchSectionCommunities } = useSectionCommunities();
  const { data: documents, isLoading: documentsLoading } = useDocuments();

  const [selectedDocumentId, setSelectedDocumentId] = useState(initialDocumentId || '');
  const { data: sections, isLoading: sectionsLoading } = useDocumentSections(selectedDocumentId);

  const [formData, setFormData] = useState<SectionCommunitiesRequest>({
    document_id: initialDocumentId || '',
    section_id: initialSectionId || '',
    algorithm: 'louvain',
    resolution: 1.0,
    include_layout: true,
    layout_algorithm: 'force-directed',
  });

  // Update formData when selectedDocumentId changes
  useEffect(() => {
    setFormData((prev) => ({
      ...prev,
      document_id: selectedDocumentId,
      section_id: '', // Reset section when document changes
    }));
  }, [selectedDocumentId]);

  const handleFetch = async () => {
    if (!formData.document_id || !formData.section_id) {
      return;
    }

    try {
      await fetchSectionCommunities(formData);
    } catch (err) {
      // Error is handled by hook
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
      data-testid="section-communities-dialog"
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Section Communities
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
            aria-label="Close dialog"
            data-testid="close-dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Document Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Document
              </label>
              <SearchableSelect
                options={documents.map((doc) => ({
                  value: doc.id,
                  label: doc.title,
                }))}
                value={selectedDocumentId}
                onChange={setSelectedDocumentId}
                placeholder={documentsLoading ? 'Loading documents...' : 'Select document...'}
                disabled={documentsLoading}
                data-testid="document-select"
              />
            </div>

            {/* Section Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Section
              </label>
              <SearchableSelect
                options={sections.map((section) => ({
                  value: section.id,
                  label: section.heading,
                }))}
                value={formData.section_id}
                onChange={(sectionId) => setFormData({ ...formData, section_id: sectionId })}
                placeholder={
                  !selectedDocumentId
                    ? 'Select document first'
                    : sectionsLoading
                    ? 'Loading sections...'
                    : 'Select section...'
                }
                disabled={!selectedDocumentId || sectionsLoading}
                data-testid="section-select"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Algorithm
              </label>
              <select
                value={formData.algorithm}
                onChange={(e) => setFormData({ ...formData, algorithm: e.target.value as 'louvain' | 'leiden' })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                           bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid="algorithm-select"
              >
                <option value="louvain">Louvain</option>
                <option value="leiden">Leiden</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Resolution
              </label>
              <input
                type="number"
                value={formData.resolution}
                onChange={(e) => setFormData({ ...formData, resolution: parseFloat(e.target.value) })}
                min="0.1"
                max="5.0"
                step="0.1"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                           bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid="resolution-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Layout
              </label>
              <select
                value={formData.layout_algorithm}
                onChange={(e) => setFormData({ ...formData, layout_algorithm: e.target.value as any })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                           bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid="layout-select"
              >
                <option value="force-directed">Force-Directed</option>
                <option value="circular">Circular</option>
                <option value="hierarchical">Hierarchical</option>
              </select>
            </div>
          </div>

          <button
            onClick={handleFetch}
            disabled={isLoading || !formData.document_id || !formData.section_id}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700
                       disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors
                       flex items-center justify-center gap-2"
            data-testid="fetch-communities-button"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Analyzing Section...
              </>
            ) : (
              'Analyze Communities'
            )}
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-4">
              <p className="text-sm text-red-700 dark:text-red-300">{error.message}</p>
            </div>
          )}

          {data && (
            <div className="space-y-6">
              {/* Summary */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 grid grid-cols-3 gap-4">
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Communities</div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {data.total_communities}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Total Entities</div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {data.total_entities}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Generation Time</div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {data.generation_time_ms.toFixed(0)}ms
                  </div>
                </div>
              </div>

              {/* Communities */}
              <div className="space-y-4">
                {data.communities.map((community, index) => (
                  <CommunityCard key={community.community_id} community={community} index={index} />
                ))}
              </div>

              {data.communities.length === 0 && (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No communities detected in this section
                </div>
              )}
            </div>
          )}

          {!data && !isLoading && !error && (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              <p className="mb-2">Enter document and section information above to analyze communities</p>
              <p className="text-sm">Communities are groups of closely related entities within a section</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Community Card Component
 */
interface CommunityCardProps {
  community: CommunityVisualization;
  index: number;
}

function CommunityCard({ community, index }: CommunityCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
      data-testid={`community-card-${index}`}
    >
      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Community {index + 1}
          </h3>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            data-testid={`expand-community-${index}`}
          >
            {expanded ? 'Hide Details' : 'Show Details'}
          </button>
        </div>

        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-500 dark:text-gray-400">Size:</span>{' '}
            <span className="font-medium text-gray-900 dark:text-white">{community.size} entities</span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Cohesion:</span>{' '}
            <span className="font-medium text-gray-900 dark:text-white">
              {(community.cohesion_score * 100).toFixed(1)}%
            </span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Edges:</span>{' '}
            <span className="font-medium text-gray-900 dark:text-white">{community.edges.length}</span>
          </div>
        </div>

        {expanded && (
          <div className="mt-4 space-y-3 border-t border-gray-200 dark:border-gray-700 pt-4">
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Entities</h4>
              <div className="flex flex-wrap gap-2">
                {community.nodes.slice(0, 10).map((node) => (
                  <span
                    key={node.entity_id}
                    className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300
                               rounded text-xs font-medium"
                    title={`${node.entity_name} (${node.entity_type}) - Centrality: ${node.centrality.toFixed(2)}`}
                  >
                    {node.entity_name}
                  </span>
                ))}
                {community.nodes.length > 10 && (
                  <span className="px-2 py-1 text-xs text-gray-500 dark:text-gray-400">
                    +{community.nodes.length - 10} more
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-gray-500 dark:text-gray-400">Algorithm:</span>{' '}
                <span className="text-gray-900 dark:text-white">{community.algorithm}</span>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">Layout:</span>{' '}
                <span className="text-gray-900 dark:text-white">{community.layout_type}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
