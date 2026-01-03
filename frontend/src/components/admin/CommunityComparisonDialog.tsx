/**
 * CommunityComparisonDialog Component
 * Sprint 71 Feature 71.16: Community Comparison Across Sections
 *
 * Dialog for comparing communities across multiple document sections
 * with searchable document and section selection
 */

import { useState, useEffect } from 'react';
import { X, Plus, Trash2 } from 'lucide-react';
import { useCompareCommunities } from '../../hooks/useGraphCommunities';
import { useDocuments, useDocumentSections } from '../../hooks/useDocuments';
import { SearchableSelect } from '../ui/SearchableSelect';
import type { CommunityComparisonRequest } from '../../types/graph';

interface CommunityComparisonDialogProps {
  isOpen: boolean;
  onClose: () => void;
  documentId?: string;
}

export function CommunityComparisonDialog({
  isOpen,
  onClose,
  documentId: initialDocumentId,
}: CommunityComparisonDialogProps) {
  const { data, isLoading, error, compareCommunities } = useCompareCommunities();
  const { data: documents, isLoading: documentsLoading } = useDocuments();

  const [selectedDocumentId, setSelectedDocumentId] = useState(initialDocumentId || '');
  const { data: sections, isLoading: sectionsLoading } = useDocumentSections(selectedDocumentId);

  const [formData, setFormData] = useState<CommunityComparisonRequest>({
    document_id: initialDocumentId || '',
    sections: ['', ''],
    algorithm: 'louvain',
    resolution: 1.0,
  });

  // Update formData when selectedDocumentId changes
  useEffect(() => {
    setFormData((prev) => ({
      ...prev,
      document_id: selectedDocumentId,
      sections: ['', ''], // Reset sections when document changes
    }));
  }, [selectedDocumentId]);

  const handleAddSection = () => {
    setFormData({
      ...formData,
      sections: [...formData.sections, ''],
    });
  };

  const handleRemoveSection = (index: number) => {
    if (formData.sections.length > 2) {
      setFormData({
        ...formData,
        sections: formData.sections.filter((_, i) => i !== index),
      });
    }
  };

  const handleSectionChange = (index: number, value: string) => {
    const newSections = [...formData.sections];
    newSections[index] = value;
    setFormData({ ...formData, sections: newSections });
  };

  const handleCompare = async () => {
    const validSections = formData.sections.filter((s) => s.trim() !== '');
    if (!formData.document_id || validSections.length < 2) {
      return;
    }

    try {
      await compareCommunities({
        ...formData,
        sections: validSections,
      });
    } catch (err) {
      // Error is handled by hook
    }
  };

  const validSections = formData.sections.filter((s) => s.trim() !== '');
  const canCompare = formData.document_id && validSections.length >= 2;

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
      data-testid="community-comparison-dialog"
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Compare Section Communities
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

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Sections to Compare (minimum 2)
              </label>
              <button
                onClick={handleAddSection}
                disabled={!selectedDocumentId}
                className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="add-section-button"
              >
                <Plus className="w-4 h-4" />
                Add Section
              </button>
            </div>
            <div className="space-y-2">
              {formData.sections.map((section, index) => (
                <div key={index} className="flex gap-2">
                  <SearchableSelect
                    options={sections.map((sec) => ({
                      value: sec.id,
                      label: sec.heading,
                    }))}
                    value={section}
                    onChange={(value) => handleSectionChange(index, value)}
                    placeholder={
                      !selectedDocumentId
                        ? 'Select document first'
                        : sectionsLoading
                        ? 'Loading sections...'
                        : `Section ${index + 1}`
                    }
                    disabled={!selectedDocumentId || sectionsLoading}
                    data-testid={`section-select-${index}`}
                    className="flex-1"
                  />
                  {formData.sections.length > 2 && (
                    <button
                      onClick={() => handleRemoveSection(index)}
                      className="px-3 py-2 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20
                                 rounded-lg transition-colors"
                      aria-label={`Remove section ${index + 1}`}
                      data-testid={`remove-section-${index}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
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
          </div>

          <button
            onClick={handleCompare}
            disabled={isLoading || !canCompare}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700
                       disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors
                       flex items-center justify-center gap-2"
            data-testid="compare-button"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Comparing Sections...
              </>
            ) : (
              `Compare ${validSections.length} Sections`
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
                  <div className="text-sm text-gray-500 dark:text-gray-400">Sections Compared</div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {data.section_count}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Shared Communities</div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {data.total_shared_communities}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">Comparison Time</div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {data.comparison_time_ms.toFixed(0)}ms
                  </div>
                </div>
              </div>

              {/* Sections List */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                  Sections Analyzed
                </h3>
                <div className="flex flex-wrap gap-2">
                  {data.sections.map((section, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300
                                 rounded-lg text-sm font-medium"
                    >
                      {section}
                    </span>
                  ))}
                </div>
              </div>

              {/* Shared Entities */}
              {Object.keys(data.shared_entities).length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                    Shared Entities
                  </h3>
                  <div className="space-y-2">
                    {Object.entries(data.shared_entities).map(([pair, entities]) => (
                      <div
                        key={pair}
                        className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3"
                      >
                        <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          {pair} ({entities.length} shared)
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {entities.slice(0, 10).map((entity, index) => (
                            <span
                              key={index}
                              className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300
                                         rounded text-xs"
                            >
                              {entity}
                            </span>
                          ))}
                          {entities.length > 10 && (
                            <span className="px-2 py-0.5 text-xs text-gray-500 dark:text-gray-400">
                              +{entities.length - 10} more
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Overlap Matrix */}
              {Object.keys(data.overlap_matrix).length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                    Overlap Matrix
                  </h3>
                  <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-gray-50 dark:bg-gray-700">
                        <tr>
                          <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700 dark:text-gray-300">
                            Section
                          </th>
                          {data.sections.map((section, index) => (
                            <th
                              key={index}
                              className="px-4 py-2 text-center text-sm font-semibold text-gray-700 dark:text-gray-300"
                            >
                              {section}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(data.overlap_matrix).map(([section, overlaps], rowIndex) => (
                          <tr
                            key={rowIndex}
                            className="border-t border-gray-200 dark:border-gray-700"
                          >
                            <td className="px-4 py-2 text-sm font-medium text-gray-900 dark:text-white">
                              {section}
                            </td>
                            {data.sections.map((targetSection, colIndex) => {
                              const count = overlaps[targetSection] || 0;
                              const isSelf = section === targetSection;
                              return (
                                <td
                                  key={colIndex}
                                  className={`px-4 py-2 text-center text-sm ${
                                    isSelf
                                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-400'
                                      : count > 0
                                      ? 'text-blue-600 dark:text-blue-400 font-medium'
                                      : 'text-gray-500'
                                  }`}
                                >
                                  {isSelf ? '-' : count}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {data.total_shared_communities === 0 && (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No shared communities found between the selected sections
                </div>
              )}
            </div>
          )}

          {!data && !isLoading && !error && (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              <p className="mb-2">Enter document and section information above to compare communities</p>
              <p className="text-sm">
                This will analyze how communities overlap and share entities across sections
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
