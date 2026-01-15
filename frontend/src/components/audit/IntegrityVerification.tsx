/**
 * IntegrityVerification Component
 * Sprint 98 Feature 98.4: Audit Trail Viewer
 *
 * Verify cryptographic integrity of audit log chain.
 */

import { useState } from 'react';
import { Shield, Check, X, AlertCircle } from 'lucide-react';
import type { IntegrityVerificationResult } from '../../types/audit';

interface IntegrityVerificationProps {
  onVerify: (startTime?: string, endTime?: string) => Promise<IntegrityVerificationResult>;
}

export function IntegrityVerification({ onVerify }: IntegrityVerificationProps) {
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState<IntegrityVerificationResult | null>(null);

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const verificationResult = await onVerify();
      setResult(verificationResult);
    } catch (error) {
      console.error('Verification failed:', error);
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Integrity Verification
          </h3>
        </div>
        <button
          onClick={handleVerify}
          disabled={verifying}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {verifying ? 'Verifying...' : 'Verify Chain'}
        </button>
      </div>

      {result && (
        <div
          className={`rounded-lg border p-4 ${
            result.verified
              ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
              : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
          }`}
        >
          <div className="flex items-start gap-3">
            {result.verified ? (
              <Check className="w-6 h-6 text-green-600 dark:text-green-400 flex-shrink-0" />
            ) : (
              <X className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0" />
            )}
            <div className="flex-1 space-y-2">
              <h4
                className={`font-semibold ${
                  result.verified
                    ? 'text-green-900 dark:text-green-100'
                    : 'text-red-900 dark:text-red-100'
                }`}
              >
                {result.verified ? 'Integrity Verified' : 'Integrity Verification Failed'}
              </h4>
              <div className="text-sm space-y-1">
                <div className={result.verified ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}>
                  <span className="font-medium">Total Events:</span> {result.totalEvents}
                </div>
                <div className={result.verified ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}>
                  <span className="font-medium">Verified:</span> {result.verifiedEvents}
                </div>
                {result.failedEvents > 0 && (
                  <div className="text-red-700 dark:text-red-300">
                    <span className="font-medium">Failed:</span> {result.failedEvents}
                  </div>
                )}
                <div className={result.verified ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}>
                  <span className="font-medium">Verified At:</span>{' '}
                  {new Date(result.verifiedAt).toLocaleString()}
                </div>
              </div>

              {result.brokenChains.length > 0 && (
                <div className="mt-3 space-y-2">
                  <h5 className="font-medium text-red-900 dark:text-red-100 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    Broken Chains ({result.brokenChains.length})
                  </h5>
                  <div className="space-y-1">
                    {result.brokenChains.map((chain, idx) => (
                      <div
                        key={idx}
                        className="text-xs bg-red-100 dark:bg-red-900/20 p-2 rounded border border-red-200 dark:border-red-800"
                      >
                        <div className="font-medium">Event: {chain.eventId}</div>
                        <div>Timestamp: {new Date(chain.timestamp).toLocaleString()}</div>
                        <div>Reason: {chain.reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {!result && !verifying && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          Click "Verify Chain" to check the cryptographic integrity of the audit log.
        </div>
      )}
    </div>
  );
}
