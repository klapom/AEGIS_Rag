/**
 * DetailPanel Component
 * Sprint 35 Feature 35.2: Admin Indexing Side-by-Side Layout
 *
 * Displays live indexing details in the right panel:
 * - Current file name
 * - Page progress with progress bar
 * - Chunks created count
 * - Entities extracted count
 * - Pipeline stage indicator
 *
 * This panel is always visible during indexing (no modal required)
 */

import { PipelineStages } from './PipelineStages';
import type { DetailedProgress } from '../../types/admin';

interface DetailPanelProps {
  progress: DetailedProgress | null;
  currentFile?: string;
  chunksCreated?: number;
  entitiesExtracted?: number;
  pipelineStage?: string;
}

export function DetailPanel({
  progress,
  currentFile,
  chunksCreated,
  entitiesExtracted,
  pipelineStage,
}: DetailPanelProps) {
  // If no progress data is available yet
  if (!progress && !currentFile) {
    return (
      <div className="text-gray-500 text-center py-8" data-testid="detail-panel">
        <div className="mb-2">
          <svg
            className="w-12 h-12 mx-auto text-gray-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>
        <p className="text-sm">Waiting for indexing to start...</p>
      </div>
    );
  }

  // Extract data from progress or use fallback props
  const fileName = progress?.current_file?.file_name || currentFile || '-';
  const currentPage = progress?.current_page ?? 0;
  const totalPages = progress?.total_pages ?? 0;
  const chunks = chunksCreated ?? 0;
  const entities = progress?.entities?.total_entities ?? entitiesExtracted ?? 0;
  const stage = pipelineStage || 'unknown';

  // Calculate page progress percentage
  const pageProgress = totalPages > 0 ? (currentPage / totalPages) * 100 : 0;

  return (
    <div className="space-y-4" data-testid="detail-panel">
      {/* Current File */}
      <div>
        <label className="text-xs text-gray-500 uppercase font-medium">File</label>
        <div className="font-medium text-gray-900 truncate mt-1" data-testid="current-file">
          {fileName}
        </div>
      </div>

      {/* Page Progress */}
      {totalPages > 0 && (
        <div>
          <label className="text-xs text-gray-500 uppercase font-medium">Page Progress</label>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm font-semibold text-gray-900" data-testid="page-progress">
              {currentPage} / {totalPages}
            </span>
            <div className="flex-1 bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${pageProgress}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Chunks & Entities Grid */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs text-gray-500 uppercase font-medium">Chunks</label>
          <div className="text-2xl font-bold text-gray-900 mt-1" data-testid="chunks-count">
            {chunks}
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-500 uppercase font-medium">Entities</label>
          <div className="text-2xl font-bold text-gray-900 mt-1" data-testid="entities-count">
            {entities}
          </div>
        </div>
      </div>

      {/* Page Elements (if available from DetailedProgress) */}
      {progress?.page_elements && (
        <div>
          <label className="text-xs text-gray-500 uppercase font-medium">Current Page Elements</label>
          <div className="grid grid-cols-3 gap-2 mt-2">
            <ElementBadge
              label="Tables"
              value={progress.page_elements.tables}
              color="bg-blue-50 text-blue-700"
            />
            <ElementBadge
              label="Images"
              value={progress.page_elements.images}
              color="bg-purple-50 text-purple-700"
            />
            <ElementBadge
              label="Words"
              value={progress.page_elements.word_count}
              color="bg-green-50 text-green-700"
            />
          </div>
        </div>
      )}

      {/* Pipeline Stage */}
      <div>
        <label className="text-xs text-gray-500 uppercase font-medium">Pipeline Stage</label>
        <PipelineStages current={stage} />
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
    <div className={`${color} rounded-lg p-2 text-center`}>
      <div className="text-lg font-bold">{value}</div>
      <div className="text-xs font-medium uppercase">{label}</div>
    </div>
  );
}
