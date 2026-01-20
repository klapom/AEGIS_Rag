/**
 * UploadResultCard Component
 * Sprint 117 Feature 117.10: Upload Dialog Classification Display
 * Sprint 117 Feature 117.11: Manual Domain Override Integration
 *
 * Displays upload result with domain classification and extraction summary.
 */

import { useState } from 'react';
import { CheckCircle, AlertTriangle, FileText } from 'lucide-react';
import { DomainClassificationBadge } from './DomainClassificationBadge';
import { ExtractionSummary } from './ExtractionSummary';
import { DomainOverrideButton } from './DomainOverrideButton';
import { DomainOverrideModal } from './DomainOverrideModal';

interface DomainClassification {
  domain_id: string;
  domain_name: string;
  confidence: number;
  classification_path: 'fast' | 'verified' | 'fallback';
  latency_ms: number;
  model_used: string;
  matched_entity_types: string[];
  matched_intent: string | null;
  requires_review: boolean;
  alternatives: Array<{ domain: string; confidence: number }>;
}

interface ExtractionSummaryData {
  entities_count: number;
  relations_count: number;
  chunks_count: number;
  mentioned_in_count: number;
}

interface UploadResultCardProps {
  filename: string;
  documentId?: string; // Sprint 117.11: Required for domain override
  status: 'success' | 'warning' | 'error';
  domainClassification?: DomainClassification;
  extractionSummary?: ExtractionSummaryData;
  message?: string;
  className?: string;
  onDomainOverride?: (domainId: string, reason: string, reprocess: boolean) => Promise<void>; // Sprint 117.11: Override handler
}

/**
 * Card component displaying upload result with classification and extraction data.
 *
 * Shows:
 * - Upload status (success/warning/error)
 * - Filename
 * - Domain classification badge (if available)
 * - Classification details (matched entities, latency)
 * - Extraction summary statistics (if available)
 * - Low confidence warning (if requires_review)
 *
 * @param filename - Uploaded file name
 * @param documentId - Document ID (required for domain override)
 * @param status - Upload status
 * @param domainClassification - Domain classification result
 * @param extractionSummary - Extraction statistics
 * @param message - Optional status message
 * @param className - Additional CSS classes
 * @param onDomainOverride - Handler for domain override (Sprint 117.11)
 */
export function UploadResultCard({
  filename,
  documentId,
  status,
  domainClassification,
  extractionSummary,
  message,
  className = '',
  onDomainOverride,
}: UploadResultCardProps) {
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState(false);
  const statusConfig = {
    success: {
      icon: CheckCircle,
      color: 'text-green-600',
      bg: 'bg-green-50',
      border: 'border-green-200',
      title: 'Upload Successful',
    },
    warning: {
      icon: AlertTriangle,
      color: 'text-yellow-600',
      bg: 'bg-yellow-50',
      border: 'border-yellow-200',
      title: 'Upload Completed with Warnings',
    },
    error: {
      icon: AlertTriangle,
      color: 'text-red-600',
      bg: 'bg-red-50',
      border: 'border-red-200',
      title: 'Upload Failed',
    },
  };

  const config = statusConfig[status];
  const StatusIcon = config.icon;

  return (
    <div
      className={`rounded-lg border ${config.border} ${config.bg} p-6 space-y-4 ${className}`}
      data-testid="upload-result-card"
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <StatusIcon className={`w-5 h-5 ${config.color} mt-0.5`} />
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900">{config.title}</h3>
          {message && <p className="text-sm text-gray-600 mt-1">{message}</p>}
        </div>
      </div>

      {/* Filename */}
      <div className="flex items-center gap-2 px-3 py-2 bg-white rounded border border-gray-200">
        <FileText className="w-4 h-4 text-gray-400" />
        <span className="text-sm font-medium text-gray-900">{filename}</span>
      </div>

      {/* Domain Classification */}
      {domainClassification && (
        <div className="space-y-3 p-4 bg-white rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-gray-700">Domain Classification</h4>
            {/* Sprint 117.11: Domain Override Button */}
            {documentId && (
              <DomainOverrideButton
                onClick={() => setIsOverrideModalOpen(true)}
                showAlways={true} // Always show edit button
                confidence={domainClassification.confidence}
              />
            )}
          </div>

          <DomainClassificationBadge
            domainName={domainClassification.domain_name}
            confidence={domainClassification.confidence}
            classificationPath={domainClassification.classification_path}
          />

          {/* Classification Details */}
          <div className="space-y-1 text-xs text-gray-600">
            {domainClassification.matched_entity_types.length > 0 && (
              <div>
                <span className="font-medium">Matched: </span>
                {domainClassification.matched_entity_types.join(', ')}
              </div>
            )}
            <div>
              <span className="font-medium">Latency: </span>
              {domainClassification.latency_ms}ms
            </div>
            <div>
              <span className="font-medium">Model: </span>
              {domainClassification.model_used}
            </div>
          </div>

          {/* Low Confidence Warning with Alternative Suggestions */}
          {domainClassification.requires_review && (
            <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded">
              <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5" />
              <div className="text-xs text-yellow-800 flex-1">
                <div className="font-semibold">Low Confidence - Please Review</div>
                <div>
                  Classification confidence is below threshold. Please review the suggested domain.
                </div>
                {domainClassification.alternatives.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <div className="font-medium">Alternative suggestions:</div>
                    {domainClassification.alternatives.map((alt, idx) => (
                      <div key={idx} className="flex items-center justify-between py-1">
                        <span>
                          {alt.domain} ({(alt.confidence * 100).toFixed(1)}%)
                        </span>
                        {/* Sprint 117.11: Quick "Use this" buttons for alternatives */}
                        {documentId && onDomainOverride && (
                          <button
                            onClick={async () => {
                              try {
                                await onDomainOverride(alt.domain, `Selected from alternatives (${(alt.confidence * 100).toFixed(1)}% confidence)`, false);
                              } catch (err) {
                                console.error('Failed to override domain:', err);
                              }
                            }}
                            className="text-xs px-2 py-1 bg-yellow-600 text-white rounded hover:bg-yellow-700 transition-colors"
                          >
                            Use this
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sprint 117.11: Domain Override Modal */}
      {documentId && domainClassification && onDomainOverride && (
        <DomainOverrideModal
          isOpen={isOverrideModalOpen}
          onClose={() => setIsOverrideModalOpen(false)}
          onOverride={onDomainOverride}
          documentId={documentId}
          currentDomain={domainClassification.domain_name}
          currentConfidence={domainClassification.confidence}
        />
      )}

      {/* Extraction Summary */}
      {extractionSummary && (
        <div className="p-4 bg-white rounded-lg border border-gray-200">
          <ExtractionSummary
            entitiesCount={extractionSummary.entities_count}
            relationsCount={extractionSummary.relations_count}
            chunksCount={extractionSummary.chunks_count}
            mentionedInCount={extractionSummary.mentioned_in_count}
          />
        </div>
      )}
    </div>
  );
}
