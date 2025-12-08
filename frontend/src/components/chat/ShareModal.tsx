/**
 * ShareModal Component
 * Sprint 38 Feature 38.3: Share Conversation Links
 *
 * Features:
 * - Generate public share link for conversation
 * - Configurable expiry duration (1h, 24h, 3d, 7d)
 * - Copy to clipboard functionality
 * - URL display after generation
 * - Loading and error states
 */

import { useState } from 'react';
import { X, Share2, Copy, Check, Clock, Link2, AlertCircle } from 'lucide-react';
import { createShareLink } from '../../api/chat';

interface ShareModalProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface ExpiryOption {
  label: string;
  hours: number;
}

const EXPIRY_OPTIONS: ExpiryOption[] = [
  { label: '1 hour', hours: 1 },
  { label: '24 hours', hours: 24 },
  { label: '3 days', hours: 72 },
  { label: '7 days', hours: 168 },
];

export function ShareModal({ sessionId, isOpen, onClose }: ShareModalProps) {
  const [selectedExpiry, setSelectedExpiry] = useState<number>(24);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await createShareLink(sessionId, selectedExpiry);
      setShareUrl(response.share_url);
      setExpiresAt(response.expires_at);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create share link');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!shareUrl) return;

    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleClose = () => {
    setShareUrl(null);
    setExpiresAt(null);
    setCopied(false);
    setError(null);
    onClose();
  };

  const formatExpiryDate = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Share2 className="w-5 h-5 text-blue-500" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Share Conversation
            </h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {!shareUrl ? (
            <>
              {/* Expiry Selection */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                  <Clock className="w-4 h-4" />
                  Link expires in
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {EXPIRY_OPTIONS.map((option) => (
                    <button
                      key={option.hours}
                      onClick={() => setSelectedExpiry(option.hours)}
                      className={`px-4 py-2 rounded-lg border-2 transition-colors ${
                        selectedExpiry === option.hours
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                          : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 text-gray-700 dark:text-gray-300'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Error Display */}
              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <AlertCircle className="w-4 h-4 text-red-500" />
                  <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
                </div>
              )}

              {/* Generate Button */}
              <button
                onClick={handleGenerate}
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white rounded-lg transition-colors font-medium"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Link2 className="w-4 h-4" />
                    Generate Share Link
                  </>
                )}
              </button>
            </>
          ) : (
            <>
              {/* Success Message */}
              <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                <p className="text-sm text-green-700 dark:text-green-400">
                  Share link created successfully!
                </p>
              </div>

              {/* Share URL Display */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Share Link
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={shareUrl}
                    readOnly
                    className="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-gray-100 font-mono"
                  />
                  <button
                    onClick={handleCopy}
                    className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors flex items-center gap-2"
                    aria-label="Copy to clipboard"
                  >
                    {copied ? (
                      <>
                        <Check className="w-4 h-4" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4" />
                        Copy
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Expiry Information */}
              {expiresAt && (
                <div className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <Clock className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Link expires on {formatExpiryDate(expiresAt)}
                  </p>
                </div>
              )}

              {/* Close Button */}
              <button
                onClick={handleClose}
                className="w-full px-4 py-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg transition-colors font-medium"
              >
                Done
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
