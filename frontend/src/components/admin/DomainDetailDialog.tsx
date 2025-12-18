/**
 * DomainDetailDialog Component
 * Sprint 51 Feature: Domain View Dialog
 * Sprint 51 Feature 51.4: Domain deletion from detail dialog
 *
 * Shows domain details and training status in a modal dialog
 */

import { useState } from 'react';
import { useTrainingStatus, useDeleteDomain, type Domain } from '../../hooks/useDomainTraining';

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

  // Delete functionality
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const { mutateAsync: deleteDomain, isLoading: isDeleting } = useDeleteDomain();

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

  if (!isOpen || !domain) return null;

  const statusColors: Record<Domain['status'], string> = {
    ready: 'bg-green-100 text-green-800',
    training: 'bg-yellow-100 text-yellow-800',
    pending: 'bg-gray-100 text-gray-800',
    failed: 'bg-red-100 text-red-800',
  };

  const statusColor = statusColors[domain.status] || 'bg-gray-100 text-gray-800';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
      data-testid="domain-detail-dialog"
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
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
          {/* Domain Info Section */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Domain Information</h3>
            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <InfoRow label="Name" value={domain.name} />
              <InfoRow label="Description" value={domain.description || '-'} />
              <InfoRow label="LLM Model" value={domain.llm_model || 'Not configured'} />
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
                  <div>
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
