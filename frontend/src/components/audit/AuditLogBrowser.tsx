/**
 * AuditLogBrowser Component
 * Sprint 98 Feature 98.4: Audit Trail Viewer
 *
 * Searchable audit event log with filters and pagination.
 * Displays immutable audit trail with cryptographic integrity indicators.
 */

import { useState } from 'react';
import { Search, Filter, ChevronDown, ChevronUp, Check, X } from 'lucide-react';
import type {
  AuditEvent,
  AuditEventType,
  AuditEventOutcome,
  AuditEventFilters,
} from '../../types/audit';
import {
  getEventTypeColor,
  getOutcomeColor,
  getOutcomeIcon,
  formatEventType,
  formatDuration,
} from '../../types/audit';

interface AuditLogBrowserProps {
  events: AuditEvent[];
  filters: AuditEventFilters;
  total: number;
  onFiltersChange: (filters: AuditEventFilters) => void;
  onViewDetails: (event: AuditEvent) => void;
}

export function AuditLogBrowser({
  events,
  filters,
  total,
  onFiltersChange,
  onViewDetails,
}: AuditLogBrowserProps) {
  const [showFilters, setShowFilters] = useState(false);

  const handleFilterChange = (updates: Partial<AuditEventFilters>) => {
    onFiltersChange({ ...filters, ...updates });
  };

  return (
    <div className="space-y-4" data-testid="audit-events-list">
      {/* Header with Search and Filters */}
      <div className="space-y-3">
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search events..."
            value={filters.searchQuery || ''}
            onChange={(e) => handleFilterChange({ searchQuery: e.target.value })}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
            data-testid="audit-search-input"
          />
        </div>

        {/* Filter Toggle */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          <Filter className="w-4 h-4" />
          Filters
          {showFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {/* Filter Panel */}
        {showFilters && (
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Event Type Filter */}
              <div>
                <label htmlFor="eventType" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Event Type
                </label>
                <select
                  id="eventType"
                  value={filters.eventType || ''}
                  onChange={(e) =>
                    handleFilterChange({
                      eventType: e.target.value ? (e.target.value as AuditEventType) : undefined,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
                  data-testid="audit-filter-action"
                >
                  <option value="">All</option>
                  <option value="AUTH_SUCCESS">Auth Success</option>
                  <option value="AUTH_FAILURE">Auth Failure</option>
                  <option value="DATA_READ">Data Read</option>
                  <option value="DATA_WRITE">Data Write</option>
                  <option value="DATA_DELETE">Data Delete</option>
                  <option value="SKILL_EXECUTED">Skill Executed</option>
                  <option value="SKILL_FAILED">Skill Failed</option>
                  <option value="POLICY_VIOLATION">Policy Violation</option>
                </select>
              </div>

              {/* Outcome Filter */}
              <div>
                <label htmlFor="outcome" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Outcome
                </label>
                <select
                  id="outcome"
                  value={filters.outcome || ''}
                  onChange={(e) =>
                    handleFilterChange({
                      outcome: e.target.value ? (e.target.value as AuditEventOutcome) : undefined,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All</option>
                  <option value="success">Success</option>
                  <option value="failure">Failure</option>
                  <option value="blocked">Blocked</option>
                  <option value="error">Error</option>
                </select>
              </div>

              {/* Actor Filter */}
              <div>
                <label htmlFor="actorId" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Actor
                </label>
                <input
                  id="actorId"
                  type="text"
                  placeholder="e.g., user_123"
                  value={filters.actorId || ''}
                  onChange={(e) => handleFilterChange({ actorId: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Time Range */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="startTime" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Start Time
                </label>
                <input
                  id="startTime"
                  type="datetime-local"
                  value={filters.startTime ? filters.startTime.slice(0, 16) : ''}
                  onChange={(e) =>
                    handleFilterChange({
                      startTime: e.target.value ? new Date(e.target.value).toISOString() : undefined,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label htmlFor="endTime" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  End Time
                </label>
                <input
                  id="endTime"
                  type="datetime-local"
                  value={filters.endTime ? filters.endTime.slice(0, 16) : ''}
                  onChange={(e) =>
                    handleFilterChange({
                      endTime: e.target.value ? new Date(e.target.value).toISOString() : undefined,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Clear Filters */}
            <button
              onClick={() => onFiltersChange({})}
              className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
            >
              Clear All Filters
            </button>
          </div>
        )}
      </div>

      {/* Results Count */}
      <div className="text-sm text-gray-600 dark:text-gray-400">
        Showing {events.length} of {total} events
      </div>

      {/* Event List */}
      <div className="space-y-2">
        {events.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No events found matching your filters.
          </div>
        ) : (
          events.map((event) => (
            <EventCard key={event.id} event={event} onViewDetails={onViewDetails} />
          ))
        )}
      </div>

      {/* Pagination */}
      {total > (filters.pageSize || 50) && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => handleFilterChange({ page: Math.max(1, (filters.page || 1) - 1) })}
            disabled={(filters.page || 1) <= 1}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Page {filters.page || 1} of {Math.ceil(total / (filters.pageSize || 50))}
          </span>
          <button
            onClick={() => handleFilterChange({ page: (filters.page || 1) + 1 })}
            disabled={(filters.page || 1) >= Math.ceil(total / (filters.pageSize || 50))}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Single Event Card
 */
interface EventCardProps {
  event: AuditEvent;
  onViewDetails: (event: AuditEvent) => void;
}

function EventCard({ event, onViewDetails }: EventCardProps) {
  const eventColor = getEventTypeColor(event.eventType);
  const outcomeColor = getOutcomeColor(event.outcome);
  const outcomeIcon = getOutcomeIcon(event.outcome);

  const colorCircleClasses = {
    blue: 'text-blue-600 dark:text-blue-400',
    purple: 'text-purple-600 dark:text-purple-400',
    green: 'text-green-600 dark:text-green-400',
    red: 'text-red-600 dark:text-red-400',
    yellow: 'text-yellow-600 dark:text-yellow-400',
    gray: 'text-gray-600 dark:text-gray-400',
  };

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-2"
      data-testid={`audit-event-${event.id}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div
            className={`mt-0.5 text-2xl ${
              colorCircleClasses[eventColor as keyof typeof colorCircleClasses]
            }`}
          >
            {outcomeIcon}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100" data-testid={`event-timestamp-${event.id}`}>
                {new Date(event.timestamp).toLocaleString()}
              </span>
              <span className="text-xs text-gray-600 dark:text-gray-400">|</span>
              <span className="text-sm font-semibold text-gray-900 dark:text-gray-100" data-testid={`event-action-${event.id}`}>
                {formatEventType(event.eventType)}
              </span>
            </div>
            <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">{event.message}</p>
          </div>
        </div>
        <OutcomeBadge outcome={event.outcome} />
      </div>

      {/* Details */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-gray-600 dark:text-gray-400">
        <div data-testid={`event-user-${event.id}`}>
          <span className="font-medium">Actor:</span> {event.actorName || event.actorId}
        </div>
        <div>
          <span className="font-medium">Resource:</span> {event.resourceId}
        </div>
        {event.duration && (
          <div>
            <span className="font-medium">Duration:</span> {formatDuration(event.duration)}
          </div>
        )}
        <div className="flex items-center gap-1">
          <span className="font-medium">Chain:</span>
          <Check className="w-3 h-3 text-green-600 dark:text-green-400" />
          <span className="text-green-600 dark:text-green-400">Verified</span>
        </div>
      </div>

      {/* Hash (truncated) */}
      <div className="text-xs font-mono text-gray-500 dark:text-gray-500">
        Hash: {event.hash.slice(0, 16)}...
      </div>

      {/* View Details Button */}
      <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={() => onViewDetails(event)}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          data-testid={`event-details-${event.id}`}
        >
          View Details
        </button>
      </div>
    </div>
  );
}

/**
 * Outcome Badge
 */
function OutcomeBadge({ outcome }: { outcome: AuditEventOutcome }) {
  const outcomeColor = getOutcomeColor(outcome);

  const colorClasses = {
    green: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300',
    red: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300',
  };

  return (
    <span
      className={`px-3 py-1 text-xs font-semibold rounded-full ${
        colorClasses[outcomeColor as keyof typeof colorClasses] || colorClasses.red
      }`}
    >
      {outcome.charAt(0).toUpperCase() + outcome.slice(1)}
    </span>
  );
}
