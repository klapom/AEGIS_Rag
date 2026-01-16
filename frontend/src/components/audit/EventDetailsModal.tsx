/**
 * EventDetailsModal Component
 * Sprint 98 Feature 98.4: Audit Trail Viewer
 *
 * Modal dialog for viewing detailed audit event information.
 */

import { X, Shield, User, Clock, Hash } from 'lucide-react';
import type { AuditEvent } from '../../types/audit';
import {
  getEventTypeColor,
  getOutcomeColor,
  getOutcomeIcon,
  formatEventType,
  formatDuration,
} from '../../types/audit';

interface EventDetailsModalProps {
  event: AuditEvent | null;
  onClose: () => void;
}

export function EventDetailsModal({ event, onClose }: EventDetailsModalProps) {
  if (!event) return null;

  const eventColor = getEventTypeColor(event.eventType);
  const outcomeColor = getOutcomeColor(event.outcome);
  const outcomeIcon = getOutcomeIcon(event.outcome);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
      data-testid="event-details-modal"
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Event Details
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {formatEventType(event.eventType)}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            data-testid="close-modal"
          >
            <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Basic Information */}
          <section>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Basic Information
            </h3>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Event ID
                </dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 font-mono">
                  {event.id}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Timestamp
                </dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                  {new Date(event.timestamp).toLocaleString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    timeZoneName: 'short',
                  })}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Event Type
                </dt>
                <dd className="mt-1">
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-full bg-${eventColor}-100 dark:bg-${eventColor}-900/30 text-${eventColor}-800 dark:text-${eventColor}-300`}
                  >
                    {formatEventType(event.eventType)}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Outcome
                </dt>
                <dd className="mt-1">
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-full ${
                      outcomeColor === 'green'
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                    }`}
                  >
                    {outcomeIcon} {event.outcome.charAt(0).toUpperCase() + event.outcome.slice(1)}
                  </span>
                </dd>
              </div>
              {event.duration !== null && (
                <div>
                  <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                    Duration
                  </dt>
                  <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                    {formatDuration(event.duration)}
                  </dd>
                </div>
              )}
            </dl>
          </section>

          {/* Actor Information */}
          <section>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
              <User className="w-4 h-4" />
              Actor Information
            </h3>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Actor ID
                </dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 font-mono">
                  {event.actorId}
                </dd>
              </div>
              {event.actorName && (
                <div>
                  <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                    Actor Name
                  </dt>
                  <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                    {event.actorName}
                  </dd>
                </div>
              )}
            </dl>
          </section>

          {/* Resource Information */}
          <section>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
              Resource Information
            </h3>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Resource ID
                </dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 font-mono break-all">
                  {event.resourceId}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Resource Type
                </dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                  {event.resourceType}
                </dd>
              </div>
            </dl>
          </section>

          {/* Message */}
          <section>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Message
            </h3>
            <p className="text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
              {event.message}
            </p>
          </section>

          {/* Metadata */}
          {event.metadata && Object.keys(event.metadata).length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
                Metadata
              </h3>
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <dl className="space-y-3">
                  {event.metadata.ipAddress && (
                    <div>
                      <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                        IP Address
                      </dt>
                      <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 font-mono">
                        {event.metadata.ipAddress}
                      </dd>
                    </div>
                  )}
                  {event.metadata.userAgent && (
                    <div>
                      <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                        User Agent
                      </dt>
                      <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 break-all">
                        {event.metadata.userAgent}
                      </dd>
                    </div>
                  )}
                  {event.metadata.skillName && (
                    <div>
                      <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                        Skill Name
                      </dt>
                      <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                        {event.metadata.skillName}
                        {event.metadata.skillVersion && (
                          <span className="ml-2 text-xs text-gray-600 dark:text-gray-400">
                            v{event.metadata.skillVersion}
                          </span>
                        )}
                      </dd>
                    </div>
                  )}
                  {event.metadata.dataCategories &&
                    Array.isArray(event.metadata.dataCategories) &&
                    event.metadata.dataCategories.length > 0 && (
                      <div>
                        <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                          Data Categories (GDPR)
                        </dt>
                        <dd className="mt-1 flex flex-wrap gap-1">
                          {event.metadata.dataCategories.map((category, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 rounded"
                            >
                              {category}
                            </span>
                          ))}
                        </dd>
                      </div>
                    )}
                  {event.metadata.errorMessage && (
                    <div>
                      <dt className="text-xs font-medium text-red-600 dark:text-red-400">
                        Error Message
                      </dt>
                      <dd className="mt-1 text-sm text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/20 p-2 rounded">
                        {event.metadata.errorMessage}
                        {event.metadata.errorCode && (
                          <span className="ml-2 text-xs font-mono">
                            ({event.metadata.errorCode})
                          </span>
                        )}
                      </dd>
                    </div>
                  )}
                  {/* Show any other metadata fields */}
                  {Object.entries(event.metadata)
                    .filter(
                      ([key]) =>
                        ![
                          'ipAddress',
                          'userAgent',
                          'skillName',
                          'skillVersion',
                          'dataCategories',
                          'errorMessage',
                          'errorCode',
                        ].includes(key)
                    )
                    .map(([key, value]) => (
                      <div key={key}>
                        <dt className="text-xs font-medium text-gray-600 dark:text-gray-400">
                          {key}
                        </dt>
                        <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 font-mono">
                          {typeof value === 'object'
                            ? JSON.stringify(value, null, 2)
                            : String(value)}
                        </dd>
                      </div>
                    ))}
                </dl>
              </div>
            </section>
          )}

          {/* Cryptographic Integrity */}
          <section>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
              <Hash className="w-4 h-4" />
              Cryptographic Integrity
            </h3>
            <div className="space-y-3">
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                <dt className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  Event Hash (SHA-256)
                </dt>
                <dd className="text-xs text-gray-900 dark:text-gray-100 font-mono break-all">
                  {event.hash}
                </dd>
              </div>
              {event.previousHash && (
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                  <dt className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                    Previous Event Hash
                  </dt>
                  <dd className="text-xs text-gray-900 dark:text-gray-100 font-mono break-all">
                    {event.previousHash}
                  </dd>
                </div>
              )}
              <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-900/20 p-3 rounded-lg">
                <Shield className="w-4 h-4" />
                <span className="font-medium">Chain Verified</span>
              </div>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 p-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
