/**
 * ArchiveButton Component
 * Sprint 38 Feature 38.2: Conversation Search UI
 *
 * Features:
 * - Archive icon button
 * - Confirmation dialog before archiving
 * - Toast notification on success/failure
 * - Loading state
 */

import { useState } from 'react';
import { Archive, Loader2 } from 'lucide-react';
import { archiveConversation } from '../../api/chat';

interface ArchiveButtonProps {
  sessionId: string;
  onArchived?: () => void;
  className?: string;
}

export function ArchiveButton({
  sessionId,
  onArchived,
  className = '',
}: ArchiveButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleArchiveClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowConfirm(true);
  };

  const handleConfirm = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsLoading(true);
    setError(null);
    setSuccess(false);

    try {
      await archiveConversation(sessionId);
      setSuccess(true);
      setShowConfirm(false);

      // Show success notification
      setTimeout(() => {
        setSuccess(false);
      }, 3000);

      // Notify parent component
      if (onArchived) {
        onArchived();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to archive');
      setTimeout(() => {
        setError(null);
      }, 3000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowConfirm(false);
  };

  return (
    <>
      {/* Archive Button */}
      <button
        onClick={handleArchiveClick}
        disabled={isLoading}
        className={`p-1 text-gray-400 hover:text-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
        aria-label="Archive conversation"
        data-testid="archive-button"
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" data-testid="archive-loading" />
        ) : (
          <Archive className="w-4 h-4" />
        )}
      </button>

      {/* Confirmation Dialog */}
      {showConfirm && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
          onClick={handleCancel}
          data-testid="archive-confirm-dialog"
        >
          <div
            className="bg-gray-800 rounded-lg p-6 max-w-sm mx-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-white mb-2">
              Archive Conversation?
            </h3>
            <p className="text-sm text-gray-400 mb-6">
              This conversation will be archived and removed from your active list. You
              can still search for it later.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={handleCancel}
                className="px-4 py-2 text-sm text-gray-300 hover:text-white bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                data-testid="archive-cancel"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={isLoading}
                className="px-4 py-2 text-sm text-white bg-amber-600 hover:bg-amber-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="archive-confirm"
              >
                {isLoading ? 'Archiving...' : 'Archive'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Success Toast */}
      {success && (
        <div
          className="fixed bottom-4 right-4 bg-green-600 text-white px-4 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2"
          data-testid="archive-success-toast"
        >
          <Archive className="w-4 h-4" />
          <span>Conversation archived successfully</span>
        </div>
      )}

      {/* Error Toast */}
      {error && (
        <div
          className="fixed bottom-4 right-4 bg-red-600 text-white px-4 py-3 rounded-lg shadow-lg z-50"
          data-testid="archive-error-toast"
        >
          <span>{error}</span>
        </div>
      )}
    </>
  );
}
