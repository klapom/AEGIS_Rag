/**
 * Indexing Detail Dialog Component
 * Sprint 33 Feature 33.4: Detail-Dialog (13 SP)
 *
 * Extended progress details dialog with 5 main sections:
 * 1. Document & Page Preview - Thumbnail, detected elements, parser info
 * 2. VLM Image Analysis - List of all images with status and descriptions
 * 3. Chunk Processing - Current chunk preview with navigation
 * 4. Pipeline Status - Status of all pipeline phases with icons
 * 5. Extracted Entities - Live entity and relation extraction
 *
 * All data-testid attributes for E2E testing
 */

import type { FileInfo, DetailedProgress, VLMImageStatus, PipelinePhaseStatus } from '../../types/admin';

interface IndexingDetailDialogProps {
  isOpen: boolean;
  onClose: () => void;
  currentFile: FileInfo | null;
  progress: DetailedProgress | null;
}

export function IndexingDetailDialog({
  isOpen,
  onClose,
  currentFile,
  progress,
}: IndexingDetailDialogProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      onClick={onClose}
    >
      <div
        data-testid="detail-dialog"
        className="bg-white rounded-xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-y-auto m-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
          <h2 className="text-2xl font-bold text-gray-900">
            Indexing Details
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            aria-label="Close dialog"
          >
            <CloseIcon />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Loading State - shown when progress data not yet available */}
          {!progress && (
            <div className="flex flex-col items-center justify-center py-16 space-y-4">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-indigo-600"></div>
              <div className="text-center">
                <p className="text-lg font-medium text-gray-700">Warte auf Detaildaten...</p>
                <p className="text-sm text-gray-500 mt-1">
                  Detaillierte Fortschrittsinformationen werden angezeigt, sobald die Pipeline-Verarbeitung beginnt.
                </p>
              </div>
            </div>
          )}

          {/* All sections only shown when progress data is available */}
          {progress && (
            <>
          {/* Section 1: Document & Page Preview */}
          <section data-testid="detail-page-preview" className="space-y-4">
            <h3 className="text-xl font-semibold text-gray-900 border-b pb-2">
              Document & Page Preview
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Page Thumbnail */}
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-gray-700">Page Thumbnail</h4>
                {progress?.page_thumbnail_url ? (
                  <div className="border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
                    <img
                      src={progress.page_thumbnail_url}
                      alt={`Page ${progress.current_page} thumbnail`}
                      className="w-full h-auto"
                    />
                  </div>
                ) : (
                  <div className="border border-gray-200 rounded-lg p-8 bg-gray-50 flex items-center justify-center">
                    <span className="text-gray-400">No preview available</span>
                  </div>
                )}
                <div className="text-sm text-gray-600">
                  Page {progress?.current_page || 0} of {progress?.total_pages || 0}
                </div>
              </div>

              {/* Document Info */}
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Document Info</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">File:</span>
                      <span className="font-medium text-gray-900">{currentFile?.file_name || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Parser:</span>
                      <span className="font-medium text-gray-900 uppercase">{currentFile?.parser_type || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Size:</span>
                      <span className="font-medium text-gray-900">
                        {currentFile ? formatFileSize(currentFile.file_size_bytes) : 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Detected Elements</h4>
                  <div className="grid grid-cols-3 gap-2">
                    <ElementBadge
                      label="Tables"
                      value={progress?.page_elements.tables || 0}
                      color="bg-blue-100 text-blue-700"
                    />
                    <ElementBadge
                      label="Images"
                      value={progress?.page_elements.images || 0}
                      color="bg-purple-100 text-purple-700"
                    />
                    <ElementBadge
                      label="Words"
                      value={progress?.page_elements.word_count || 0}
                      color="bg-green-100 text-green-700"
                    />
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Section 2: VLM Image Analysis */}
          <section data-testid="detail-vlm-images" className="space-y-4">
            <h3 className="text-xl font-semibold text-gray-900 border-b pb-2">
              VLM Image Analysis
            </h3>

            {progress?.vlm_images && progress.vlm_images.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {progress.vlm_images.map((image) => (
                  <VLMImageCard key={image.image_id} image={image} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-400">
                No images detected on this page
              </div>
            )}
          </section>

          {/* Section 3: Chunk Processing */}
          <section data-testid="detail-chunk-preview" className="space-y-4">
            <h3 className="text-xl font-semibold text-gray-900 border-b pb-2">
              Chunk Processing
            </h3>

            {progress?.current_chunk ? (
              <div className="space-y-4">
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-gray-700">Current Chunk</h4>
                    <div className="flex items-center space-x-4 text-sm">
                      <span className="text-gray-600">
                        Tokens: <span className="font-semibold text-gray-900">{progress.current_chunk.token_count}</span>
                      </span>
                      {progress.current_chunk.has_image && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-semibold">
                          Has Image
                        </span>
                      )}
                    </div>
                  </div>

                  {progress.current_chunk.section_name && (
                    <div className="mb-3 text-sm">
                      <span className="text-gray-600">Section: </span>
                      <span className="font-medium text-gray-900">{progress.current_chunk.section_name}</span>
                    </div>
                  )}

                  <div className="font-mono text-xs text-gray-700 whitespace-pre-wrap bg-white rounded p-3 border border-gray-200 max-h-40 overflow-y-auto">
                    {progress.current_chunk.text_preview}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-400">
                No chunk being processed
              </div>
            )}
          </section>

          {/* Section 4: Pipeline Status */}
          <section data-testid="detail-pipeline-status" className="space-y-4">
            <h3 className="text-xl font-semibold text-gray-900 border-b pb-2">
              Pipeline Status
            </h3>

            {progress?.pipeline_status && progress.pipeline_status.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {progress.pipeline_status.map((phase) => (
                  <PipelinePhaseCard key={phase.phase} phase={phase} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-400">
                Pipeline not started
              </div>
            )}
          </section>

          {/* Section 5: Extracted Entities */}
          <section data-testid="detail-entities" className="space-y-4">
            <h3 className="text-xl font-semibold text-gray-900 border-b pb-2">
              Extracted Entities (Live)
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* New Entities from Current Page */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-gray-700">New Entities</h4>
                  <span className="text-xs text-gray-500">
                    From current page
                  </span>
                </div>
                <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 max-h-48 overflow-y-auto">
                  {progress?.entities.new_entities && progress.entities.new_entities.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {progress.entities.new_entities.map((entity, idx) => (
                        <span key={idx} className="px-2 py-1 bg-blue-200 text-blue-800 rounded text-xs font-medium">
                          {entity}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center text-blue-400 text-sm">
                      No new entities yet
                    </div>
                  )}
                </div>
              </div>

              {/* New Relations from Current Page */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-gray-700">New Relations</h4>
                  <span className="text-xs text-gray-500">
                    From current page
                  </span>
                </div>
                <div className="bg-green-50 rounded-lg p-4 border border-green-200 max-h-48 overflow-y-auto">
                  {progress?.entities.new_relations && progress.entities.new_relations.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {progress.entities.new_relations.map((relation, idx) => (
                        <span key={idx} className="px-2 py-1 bg-green-200 text-green-800 rounded text-xs font-medium">
                          {relation}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center text-green-400 text-sm">
                      No new relations yet
                    </div>
                  )}
                </div>
              </div>

              {/* Total Counters */}
              <div className="md:col-span-2 grid grid-cols-2 gap-4">
                <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-200">
                  <div className="text-sm text-indigo-600 mb-1">Total Entities</div>
                  <div className="text-3xl font-bold text-indigo-900">
                    {progress?.entities.total_entities || 0}
                  </div>
                </div>
                <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                  <div className="text-sm text-purple-600 mb-1">Total Relations</div>
                  <div className="text-3xl font-bold text-purple-900">
                    {progress?.entities.total_relations || 0}
                  </div>
                </div>
              </div>
            </div>
          </section>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Utility Components
// ============================================================================

interface ElementBadgeProps {
  label: string;
  value: number;
  color: string;
}

function ElementBadge({ label, value, color }: ElementBadgeProps) {
  return (
    <div className={`${color} rounded-lg p-3 text-center`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs font-medium uppercase">{label}</div>
    </div>
  );
}

interface VLMImageCardProps {
  image: VLMImageStatus;
}

function VLMImageCard({ image }: VLMImageCardProps) {
  const statusConfig = {
    pending: { color: 'bg-gray-100 text-gray-700', icon: '⏳', label: 'Pending' },
    processing: { color: 'bg-yellow-100 text-yellow-700', icon: '⚙️', label: 'Processing' },
    completed: { color: 'bg-green-100 text-green-700', icon: '✅', label: 'Completed' },
    failed: { color: 'bg-red-100 text-red-700', icon: '❌', label: 'Failed' },
  };

  const config = statusConfig[image.status];

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      {/* Image Thumbnail */}
      {image.thumbnail_url ? (
        <div className="h-32 bg-gray-50 flex items-center justify-center">
          <img
            src={image.thumbnail_url}
            alt={`Image ${image.image_id}`}
            className="max-h-full max-w-full object-contain"
          />
        </div>
      ) : (
        <div className="h-32 bg-gray-100 flex items-center justify-center">
          <span className="text-gray-400 text-sm">No thumbnail</span>
        </div>
      )}

      {/* Status Badge */}
      <div className="p-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-600 truncate" title={image.image_id}>
            {image.image_id}
          </span>
          <span className={`px-2 py-1 rounded text-xs font-semibold ${config.color}`}>
            {config.icon} {config.label}
          </span>
        </div>

        {/* VLM Description */}
        {image.description && (
          <div className="text-xs text-gray-700 bg-gray-50 rounded p-2 max-h-20 overflow-y-auto">
            {image.description}
          </div>
        )}
      </div>
    </div>
  );
}

interface PipelinePhaseCardProps {
  phase: PipelinePhaseStatus;
}

function PipelinePhaseCard({ phase }: PipelinePhaseCardProps) {
  const statusIcons = {
    pending: '⏳',
    in_progress: '⚙️',
    completed: '✅',
    failed: '❌',
  };

  const statusColors = {
    pending: 'bg-gray-100 text-gray-700 border-gray-300',
    in_progress: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    completed: 'bg-green-100 text-green-700 border-green-300',
    failed: 'bg-red-100 text-red-700 border-red-300',
  };

  const phaseLabels: Record<string, string> = {
    parsing: 'Parsing (Docling)',
    vlm_analysis: 'VLM Analysis',
    chunking: 'Chunking',
    embeddings: 'Embeddings',
    bm25_index: 'BM25 Index',
    graph: 'Graph (Neo4j)',
  };

  return (
    <div className={`border-2 rounded-lg p-4 ${statusColors[phase.status]}`}>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-sm">{phaseLabels[phase.phase] || phase.phase}</h4>
        <span className="text-2xl">{statusIcons[phase.status]}</span>
      </div>

      <div className="text-xs uppercase font-medium opacity-80">
        {phase.status.replace('_', ' ')}
      </div>

      {phase.duration_ms != null && phase.duration_ms > 0 && (
        <div className="text-xs mt-1 opacity-70">
          {phase.duration_ms < 1000
            ? `${phase.duration_ms}ms`
            : `${(phase.duration_ms / 1000).toFixed(2)}s`}
        </div>
      )}
    </div>
  );
}

function CloseIcon() {
  return (
    <svg
      className="w-6 h-6 text-gray-600"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}
