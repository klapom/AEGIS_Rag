/**
 * DomainList Component
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 * Sprint 51: View Dialog Integration
 * Sprint 51 Feature 51.4: Domain deletion with confirmation
 *
 * Displays a table of domains with status and actions
 */

import { useState } from 'react';
import type { Domain } from '../../hooks/useDomainTraining';
import { useDeleteDomain } from '../../hooks/useDomainTraining';
import { DomainDetailDialog } from './DomainDetailDialog';

interface DomainListProps {
  domains: Domain[] | null;
  isLoading: boolean;
  onRefresh?: () => void;
}

export function DomainList({ domains, isLoading, onRefresh }: DomainListProps) {
  const [selectedDomain, setSelectedDomain] = useState<Domain | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [deleteConfirmDomain, setDeleteConfirmDomain] = useState<Domain | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const { mutateAsync: deleteDomain, isLoading: isDeleting } = useDeleteDomain();

  const handleViewDomain = (domain: Domain) => {
    setSelectedDomain(domain);
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setSelectedDomain(null);
  };

  const handleDeleteClick = (domain: Domain) => {
    setDeleteError(null);
    setDeleteConfirmDomain(domain);
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmDomain(null);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteConfirmDomain?.id) return;

    try {
      await deleteDomain(deleteConfirmDomain.id);
      setDeleteConfirmDomain(null);
      setDeleteError(null);
      // Trigger refresh after successful deletion
      if (onRefresh) {
        onRefresh();
      }
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Failed to delete domain');
    }
  };

  const handleDomainDeleted = () => {
    // Called from detail dialog after successful deletion
    setIsDialogOpen(false);
    setSelectedDomain(null);
    if (onRefresh) {
      onRefresh();
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-md border p-6 text-center" data-testid="domain-list-loading">
        <div className="inline-block w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="mt-3 text-sm text-gray-600">Loading domains...</p>
      </div>
    );
  }

  if (!domains || domains.length === 0) {
    return (
      <div className="bg-white rounded-md border p-6 text-center" data-testid="domain-list-empty">
        <p className="text-sm text-gray-600">No domains found. Create a new domain to get started.</p>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white rounded-md border" data-testid="domain-list">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Name</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Description</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Model</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Status</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {domains.map((domain) => (
              <DomainRow
                key={domain.id || domain.name}
                domain={domain}
                onView={() => handleViewDomain(domain)}
                onDelete={() => handleDeleteClick(domain)}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Domain Detail Dialog */}
      <DomainDetailDialog
        domain={selectedDomain}
        isOpen={isDialogOpen}
        onClose={handleCloseDialog}
        onDeleted={handleDomainDeleted}
      />

      {/* Delete Confirmation Dialog */}
      {deleteConfirmDomain && (
        <DeleteConfirmDialog
          domainName={deleteConfirmDomain.name}
          isDeleting={isDeleting}
          error={deleteError}
          onConfirm={handleDeleteConfirm}
          onCancel={handleDeleteCancel}
        />
      )}
    </>
  );
}

interface DomainRowProps {
  domain: Domain;
  onView: () => void;
  onDelete: () => void;
}

function DomainRow({ domain, onView, onDelete }: DomainRowProps) {
  const statusColors: Record<Domain['status'], string> = {
    ready: 'bg-green-100 text-green-800',
    training: 'bg-yellow-100 text-yellow-800',
    pending: 'bg-gray-100 text-gray-800',
    failed: 'bg-red-100 text-red-800',
  };

  const statusColor = statusColors[domain.status] || 'bg-gray-100 text-gray-800';

  return (
    <tr className="border-t hover:bg-gray-50" data-testid={`domain-row-${domain.name}`}>
      <td className="px-3 py-2 text-sm font-medium text-gray-900">{domain.name}</td>
      <td className="px-3 py-2 text-xs text-gray-600 truncate max-w-xs" title={domain.description}>
        {domain.description}
      </td>
      <td className="px-3 py-2 text-xs text-gray-700">{domain.llm_model || '-'}</td>
      <td className="px-3 py-2">
        <span
          className={`px-1.5 py-0.5 rounded text-xs font-medium ${statusColor}`}
          data-testid={`domain-status-${domain.name}`}
        >
          {domain.status}
        </span>
      </td>
      <td className="px-3 py-2">
        <div className="flex items-center gap-2">
          <button
            onClick={onView}
            className="text-blue-600 hover:underline text-xs font-medium"
            data-testid={`domain-view-${domain.name}`}
          >
            View
          </button>
          <button
            onClick={onDelete}
            className="text-red-600 hover:text-red-800 hover:underline text-xs font-medium"
            data-testid={`domain-delete-${domain.name}`}
            aria-label={`Delete domain ${domain.name}`}
          >
            Delete
          </button>
        </div>
      </td>
    </tr>
  );
}

/**
 * Delete Confirmation Dialog
 * Sprint 51 Feature 51.4: Domain deletion confirmation
 */
interface DeleteConfirmDialogProps {
  domainName: string;
  isDeleting: boolean;
  error: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

function DeleteConfirmDialog({
  domainName,
  isDeleting,
  error,
  onConfirm,
  onCancel,
}: DeleteConfirmDialogProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onCancel}
      data-testid="delete-confirm-dialog"
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-md w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Warning Icon */}
        <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-red-100 rounded-full">
          <svg
            className="w-6 h-6 text-red-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>

        <h3 className="text-lg font-semibold text-gray-900 text-center mb-2">
          Delete Domain
        </h3>
        <p className="text-sm text-gray-600 text-center mb-4">
          Are you sure you want to delete domain <strong>{domainName}</strong>?
          This will remove all indexed documents.
        </p>

        {/* Error message */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
            data-testid="delete-cancel-button"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
            data-testid="delete-confirm-button"
          >
            {isDeleting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete Domain'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
