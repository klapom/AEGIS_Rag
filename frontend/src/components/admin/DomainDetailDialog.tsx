/**
 * DomainDetailDialog Component
 * Sprint 51 Feature: Domain View Dialog
 * Sprint 51 Feature 51.4: Domain deletion from detail dialog
 * Sprint 52 Feature 52.2.2: Domain Management Enhancement
 * Sprint 77 Feature 77.5: Connectivity Metrics Display (TD-095)
 *
 * Shows domain details, statistics, health status, and bulk operations in a modal dialog
 */

import { useState } from 'react';
import {
  useTrainingStatus,
  useDeleteDomain,
  useDomainStats,
  useReindexDomain,
  useValidateDomain,
  useDomainDetails,
  type Domain,
  type ValidateDomainResponse,
} from '../../hooks/useDomainTraining';
import { ConnectivityMetrics } from './ConnectivityMetrics';

interface DomainDetailDialogProps {
  domain: Domain | null;
  isOpen: boolean;
  onClose: () => void;
  onDeleted?: () => void;
}

export function DomainDetailDialog({ domain, isOpen, onClose, onDeleted }: DomainDetailDialogProps) {
  // Fetch training status if dialog is open and domain exists
  const { data: trainingStatus, isLoading: statusLoading } = useTrainingStatus(
    domain?.name || '',
    isOpen && !!domain
  );

  // Fetch domain statistics (Sprint 52.2.2)
  const { data: domainStats, isLoading: statsLoading, refetch: refetchStats } = useDomainStats(
    domain?.name || '',
    isOpen && !!domain
  );

  // Fetch full domain details (Sprint 71 Feature 71.15)
  const { data: domainDetails } = useDomainDetails(
    domain?.name || '',
    isOpen && !!domain
  );

  // Delete functionality
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const { mutateAsync: deleteDomain, isLoading: isDeleting } = useDeleteDomain();

  // Bulk operations (Sprint 52.2.2)
  const { mutateAsync: reindexDomain, isLoading: isReindexing } = useReindexDomain();
  const { mutateAsync: validateDomain, isLoading: isValidating } = useValidateDomain();
  const [validationResult, setValidationResult] = useState<ValidateDomainResponse | null>(null);
  const [operationMessage, setOperationMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  const handleDeleteClick = () => {
    setDeleteError(null);
    setShowDeleteConfirm(true);
  };

  const handleDeleteCancel = () => {
    setShowDeleteConfirm(false);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async () => {
    if (!domain?.id) return;

    try {
      await deleteDomain(domain.id);
      setShowDeleteConfirm(false);
      setDeleteError(null);
      // Close dialog and notify parent of deletion
      if (onDeleted) {
        onDeleted();
      }
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Failed to delete domain');
    }
  };

  const handleReindex = async () => {
    if (!domain?.name) return;

    setOperationMessage(null);
    try {
      const result = await reindexDomain(domain.name);
      setOperationMessage({
        type: 'success',
        text: `Re-indexing started. ${result.documents_queued} documents queued.`
      });
      // Refresh stats after a delay
      setTimeout(refetchStats, 2000);
    } catch (err) {
      setOperationMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to start re-indexing'
      });
    }
  };

  const handleValidate = async () => {
    if (!domain?.name) return;

    setOperationMessage(null);
    setValidationResult(null);
    try {
      const result = await validateDomain(domain.name);
      setValidationResult(result);
    } catch (err) {
      setOperationMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to validate domain'
      });
    }
  };

  if (!isOpen || !domain) return null;

  const statusColors: Record<Domain['status'], string> = {
    ready: 'bg-green-100 text-green-800',
    training: 'bg-yellow-100 text-yellow-800',
    pending: 'bg-gray-100 text-gray-800',
    failed: 'bg-red-100 text-red-800',
  };

  const healthStatusColors: Record<string, string> = {
    healthy: 'bg-green-100 text-green-800',
    degraded: 'bg-yellow-100 text-yellow-800',
    error: 'bg-red-100 text-red-800',
    empty: 'bg-gray-100 text-gray-800',
    indexing: 'bg-blue-100 text-blue-800',
  };

  const statusColor = statusColors[domain.status] || 'bg-gray-100 text-gray-800';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
      data-testid="domain-detail-dialog"
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-gray-900">{domain.name}</h2>
            <span className={`px-2 py-0.5 rounded text-sm font-medium ${statusColor}`}>
              {domain.status}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* Operation Messages */}
          {operationMessage && (
            <div className={`p-3 rounded-md ${operationMessage.type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              <p className={`text-sm ${operationMessage.type === 'success' ? 'text-green-700' : 'text-red-700'}`}>
                {operationMessage.text}
              </p>
            </div>
          )}

          {/* Domain Statistics Section (Sprint 52.2.2) */}
          <section data-testid="domain-stats-section">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Domain Statistics</h3>
            {statsLoading ? (
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <div className="inline-block w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                <p className="mt-2 text-sm text-gray-600">Loading statistics...</p>
              </div>
            ) : domainStats ? (
              <div className="bg-gray-50 rounded-lg p-4">
                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <StatCard
                    label="Documents"
                    value={domainStats.documents}
                    testId="stat-documents"
                  />
                  <StatCard
                    label="Chunks"
                    value={domainStats.chunks}
                    testId="stat-chunks"
                  />
                  <StatCard
                    label="Entities"
                    value={domainStats.entities}
                    testId="stat-entities"
                  />
                  <StatCard
                    label="Relationships"
                    value={domainStats.relationships}
                    testId="stat-relationships"
                  />
                </div>

                {/* Health Status */}
                <div className="flex items-center justify-between py-2 border-t border-gray-200">
                  <span className="text-sm text-gray-600">Health Status</span>
                  <span
                    className={`px-2 py-0.5 rounded text-sm font-medium ${healthStatusColors[domainStats.health_status] || 'bg-gray-100 text-gray-800'}`}
                    data-testid="health-status"
                  >
                    {domainStats.health_status}
                  </span>
                </div>

                {/* Indexing Progress */}
                {domainStats.indexing_progress < 100 && domainStats.health_status === 'indexing' && (
                  <div className="py-2 border-t border-gray-200">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">Indexing Progress</span>
                      <span className="font-medium">{domainStats.indexing_progress.toFixed(0)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-600 transition-all"
                        style={{ width: `${domainStats.indexing_progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Last Indexed */}
                {domainStats.last_indexed && (
                  <div className="flex justify-between py-2 border-t border-gray-200">
                    <span className="text-sm text-gray-600">Last Indexed</span>
                    <span className="text-sm font-medium text-gray-900">
                      {formatDate(domainStats.last_indexed)}
                    </span>
                  </div>
                )}

                {/* Errors */}
                {domainStats.error_count > 0 && (
                  <div className="py-2 border-t border-gray-200">
                    <span className="text-sm text-red-600 font-medium">
                      {domainStats.error_count} error(s)
                    </span>
                    {domainStats.errors.length > 0 && (
                      <ul className="mt-1 text-xs text-red-600 list-disc list-inside">
                        {domainStats.errors.slice(0, 3).map((err, idx) => (
                          <li key={idx}>{err}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-gray-50 rounded-lg p-4 text-center text-sm text-gray-600">
                No statistics available
              </div>
            )}
          </section>

          {/* Connectivity Metrics Section (Sprint 77 Feature 77.5 - TD-095) */}
          {domainStats && domainStats.chunks > 0 && (
            <ConnectivityMetrics
              namespaceId={domain.name}
              domainType="factual"
              enabled={isOpen}
            />
          )}

          {/* Bulk Operations Section (Sprint 52.2.2) */}
          <section data-testid="bulk-operations-section">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Operations</h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={handleReindex}
                  disabled={isReindexing || domain.status === 'training'}
                  className="px-4 py-2 text-sm font-medium text-blue-700 bg-blue-100 rounded-lg hover:bg-blue-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  data-testid="reindex-button"
                >
                  {isReindexing ? (
                    <>
                      <div className="w-4 h-4 border-2 border-blue-700 border-t-transparent rounded-full animate-spin" />
                      Re-indexing...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      Re-index Domain
                    </>
                  )}
                </button>

                <button
                  onClick={handleValidate}
                  disabled={isValidating}
                  className="px-4 py-2 text-sm font-medium text-green-700 bg-green-100 rounded-lg hover:bg-green-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  data-testid="validate-button"
                >
                  {isValidating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-green-700 border-t-transparent rounded-full animate-spin" />
                      Validating...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Validate Domain
                    </>
                  )}
                </button>
              </div>

              {/* Validation Result */}
              {validationResult && (
                <div className="mt-4 p-3 rounded-md bg-white border border-gray-200" data-testid="validation-result">
                  <div className="flex items-center gap-2 mb-2">
                    {validationResult.is_valid ? (
                      <>
                        <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span className="text-sm font-medium text-green-700">Domain is valid</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        <span className="text-sm font-medium text-red-700">Validation failed</span>
                      </>
                    )}
                  </div>

                  {validationResult.validation_errors.length > 0 && (
                    <div className="mb-2">
                      <p className="text-xs font-medium text-red-600 mb-1">Errors:</p>
                      <ul className="text-xs text-red-600 list-disc list-inside">
                        {validationResult.validation_errors.map((err, idx) => (
                          <li key={idx}>{err}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {validationResult.recommendations.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-yellow-700 mb-1">Recommendations:</p>
                      <ul className="text-xs text-yellow-700 list-disc list-inside">
                        {validationResult.recommendations.map((rec, idx) => (
                          <li key={idx}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>

          {/* Domain Info Section */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Domain Information</h3>
            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <InfoRow label="Name" value={domain.name} />
              <InfoRow label="Description" value={domain.description || '-'} />
              <div className="flex justify-between" data-testid="domain-llm-model">
                <span className="text-sm text-gray-600">LLM Model</span>
                <span className="text-sm font-medium text-gray-900">{domain.llm_model || 'Not configured'}</span>
              </div>
              {domain.created_at && (
                <InfoRow label="Created" value={formatDate(domain.created_at)} />
              )}
              {domain.updated_at && (
                <InfoRow label="Last Updated" value={formatDate(domain.updated_at)} />
              )}
            </div>
          </section>

          {/* Training Status Section */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Training Status</h3>
            {statusLoading ? (
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <div className="inline-block w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                <p className="mt-2 text-sm text-gray-600">Loading training status...</p>
              </div>
            ) : trainingStatus ? (
              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <InfoRow label="Status" value={trainingStatus.status} />
                {trainingStatus.progress_percent !== undefined && (
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">Progress</span>
                      <span className="font-medium">{trainingStatus.progress_percent}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-600 transition-all"
                        style={{ width: `${trainingStatus.progress_percent}%` }}
                      />
                    </div>
                  </div>
                )}
                {trainingStatus.current_step && (
                  <InfoRow label="Current Step" value={trainingStatus.current_step} />
                )}
                {trainingStatus.error && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-sm text-red-700">{trainingStatus.error}</p>
                  </div>
                )}
                {trainingStatus.metrics && Object.keys(trainingStatus.metrics).length > 0 && (
                  <div data-testid="domain-training-metrics">
                    <p className="text-sm text-gray-600 mb-2">Metrics</p>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(trainingStatus.metrics).map(([key, value]) => (
                        <div key={key} className="text-xs bg-white p-2 rounded border border-gray-200">
                          <span className="text-gray-500">{key}:</span>{' '}
                          <span className="font-medium">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-gray-50 rounded-lg p-4 text-center text-sm text-gray-600">
                No training data available
              </div>
            )}
          </section>

          {/* Training Logs Section */}
          {trainingStatus?.logs && trainingStatus.logs.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Training Logs</h3>
              <div className="bg-gray-900 rounded-lg p-4 max-h-48 overflow-y-auto">
                <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
                  {trainingStatus.logs.join('\n')}
                </pre>
              </div>
            </section>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200">
          {showDeleteConfirm ? (
            /* Inline Delete Confirmation */
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-red-700">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                <span className="text-sm font-medium">
                  Delete this domain? This will remove all indexed documents.
                </span>
              </div>
              {deleteError && (
                <div className="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                  {deleteError}
                </div>
              )}
              <div className="flex gap-2 justify-end">
                <button
                  onClick={handleDeleteCancel}
                  disabled={isDeleting}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
                  data-testid="dialog-delete-cancel-button"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteConfirm}
                  disabled={isDeleting}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                  data-testid="dialog-delete-confirm-button"
                >
                  {isDeleting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Deleting...
                    </>
                  ) : (
                    'Yes, Delete'
                  )}
                </button>
              </div>
            </div>
          ) : (
            /* Normal Footer */
            <div className="flex justify-between">
              <button
                onClick={handleDeleteClick}
                className="px-4 py-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-colors font-medium text-sm"
                data-testid="dialog-delete-button"
              >
                Delete Domain
              </button>
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
              >
                Close
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Statistic card component for displaying domain metrics
 */
function StatCard({ label, value, testId }: { label: string; value: number; testId: string }) {
  return (
    <div className="bg-white p-3 rounded-lg border border-gray-200 text-center" data-testid={testId}>
      <p className="text-2xl font-bold text-gray-900">{value.toLocaleString()}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-sm text-gray-600">{label}</span>
      <span className="text-sm font-medium text-gray-900">{value}</span>
    </div>
  );
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleString('de-DE', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}
