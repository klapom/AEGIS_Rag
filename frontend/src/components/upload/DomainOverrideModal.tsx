/**
 * DomainOverrideModal Component
 * Sprint 117 Feature 117.11: Manual Domain Override Modal
 *
 * Modal dialog for manually overriding document domain classification.
 */

import { useState, useEffect } from 'react';
import { X, AlertTriangle } from 'lucide-react';

interface Domain {
  id: string;
  name: string;
  description: string;
  status: string;
}

interface DomainOverrideModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOverride: (domainId: string, reason: string, reprocess: boolean) => Promise<void>;
  documentId: string;
  currentDomain: string;
  currentConfidence: number;
}

/**
 * Modal dialog for domain override functionality.
 *
 * Features:
 * - Domain selector dropdown (fetches from /api/v1/admin/domains)
 * - Optional reason textarea (audit trail)
 * - Checkbox for re-extraction with new domain prompts
 * - Cancel / Apply Override buttons
 * - Loading state during API call
 * - Error handling
 *
 * @param isOpen - Whether modal is visible
 * @param onClose - Handler for closing modal
 * @param onOverride - Handler for applying override (domainId, reason, reprocess)
 * @param documentId - Document ID being overridden
 * @param currentDomain - Current domain classification
 * @param currentConfidence - Current classification confidence
 */
export function DomainOverrideModal({
  isOpen,
  onClose,
  onOverride,
  documentId,
  currentDomain,
  currentConfidence,
}: DomainOverrideModalProps) {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [reprocess, setReprocess] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchingDomains, setFetchingDomains] = useState<boolean>(false);

  // Fetch available domains when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchDomains();
      // Reset form state
      setSelectedDomain('');
      setReason('');
      setReprocess(false);
      setError(null);
    }
  }, [isOpen]);

  const fetchDomains = async () => {
    setFetchingDomains(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/admin/domains/');
      if (!response.ok) {
        throw new Error('Failed to fetch domains');
      }

      const data = await response.json();
      // Extract domains from ApiResponse wrapper
      const domainList = data.data || [];
      setDomains(domainList.filter((d: Domain) => d.status === 'ready' || d.status === 'active'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load domains');
    } finally {
      setFetchingDomains(false);
    }
  };

  const handleOverride = async () => {
    if (!selectedDomain) {
      setError('Please select a domain');
      return;
    }

    if (selectedDomain === currentDomain) {
      setError('Selected domain is the same as current domain');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await onOverride(selectedDomain, reason, reprocess);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to override domain');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      data-testid="domain-override-modal"
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Change Domain Classification</h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded"
            data-testid="close-modal-button"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          {/* Current Domain Info */}
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="text-sm text-gray-600">
              <span className="font-medium">Current Domain: </span>
              {currentDomain}
              <span className="ml-2 text-xs text-gray-500">
                ({(currentConfidence * 100).toFixed(1)}%)
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Document ID: {documentId}
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5" />
              <div className="text-sm text-red-800">{error}</div>
            </div>
          )}

          {/* Domain Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select New Domain
            </label>
            <select
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value)}
              disabled={fetchingDomains || loading}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              data-testid="domain-selector"
            >
              <option value="">
                {fetchingDomains ? 'Loading domains...' : '-- Select a domain --'}
              </option>
              {domains.map((domain) => (
                <option key={domain.name} value={domain.name}>
                  {domain.name} - {domain.description}
                </option>
              ))}
            </select>
          </div>

          {/* Reason Textarea */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Reason for Override (optional)
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={loading}
              placeholder="e.g., Document contains medical terminology not detected by classifier..."
              rows={3}
              maxLength={500}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              data-testid="reason-textarea"
            />
            <div className="text-xs text-gray-500 mt-1">{reason.length}/500 characters</div>
          </div>

          {/* Re-extraction Checkbox */}
          <div className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <input
              type="checkbox"
              checked={reprocess}
              onChange={(e) => setReprocess(e.target.checked)}
              disabled={loading}
              className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 disabled:cursor-not-allowed"
              data-testid="reprocess-checkbox"
            />
            <div>
              <label className="text-sm font-medium text-gray-900 cursor-pointer">
                Re-extract entities with new domain prompts
              </label>
              <p className="text-xs text-gray-600 mt-1">
                This will re-run entity extraction using the new domain's specialized prompts.
                Recommended if the domain mismatch affects entity recognition.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="cancel-button"
          >
            Cancel
          </button>
          <button
            onClick={handleOverride}
            disabled={loading || !selectedDomain || fetchingDomains}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="apply-override-button"
          >
            {loading ? 'Applying...' : 'Apply Override'}
          </button>
        </div>
      </div>
    </div>
  );
}
