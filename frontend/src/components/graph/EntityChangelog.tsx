/**
 * EntityChangelog Component
 * Sprint 39 Feature 39.6: Entity Changelog Panel (5 SP)
 *
 * Features:
 * - List changes with timestamp, user, change type
 * - Change type badges (create, update, delete, relation_added, relation_removed)
 * - Filter by user dropdown
 * - View Version / Revert to Previous buttons
 * - Pagination (Load More)
 */

import { useState, useMemo } from 'react';
import { Clock, User, ArrowRight, ChevronDown, RotateCcw, Eye } from 'lucide-react';
import type { ChangeEvent } from '../../types/graph';
import { useEntityChangelog } from '../../hooks/useEntityChangelog';

interface EntityChangelogProps {
  entityId: string;
  onViewVersion?: (version: number) => void;
  onRevert?: (version: number) => void;
}

export function EntityChangelog({ entityId, onViewVersion, onRevert }: EntityChangelogProps) {
  const { data: changelog, loading, error, hasMore, fetchMore } = useEntityChangelog(entityId);
  const [userFilter, setUserFilter] = useState<string | null>(null);

  // Get unique users from changelog
  const uniqueUsers = useMemo(() => {
    if (!changelog) return [];
    return [...new Set(changelog.map((e) => e.changedBy))];
  }, [changelog]);

  // Filter changes by user
  const filteredChanges = useMemo(() => {
    if (!changelog) return [];
    if (!userFilter) return changelog;
    return changelog.filter((e) => e.changedBy === userFilter);
  }, [changelog, userFilter]);

  if (loading && !changelog) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-red-800 dark:text-red-200 text-sm">
          Error loading changelog: {error.message}
        </p>
      </div>
    );
  }

  return (
    <div className="changelog" data-testid="entity-changelog">
      {/* Header with Filter */}
      <div className="flex flex-wrap justify-between items-center mb-4 gap-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Change History ({filteredChanges.length} changes)
        </h3>
        <div className="flex items-center gap-2">
          <User className="w-4 h-4 text-gray-500" />
          <select
            value={userFilter || ''}
            onChange={(e) => setUserFilter(e.target.value || null)}
            className="border border-gray-300 dark:border-gray-600 rounded px-3 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
            data-testid="user-filter"
          >
            <option value="">All Users</option>
            {uniqueUsers.map((user) => (
              <option key={user} value={user}>
                {user}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Changes List */}
      <div className="space-y-4">
        {filteredChanges.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <Clock className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No changes found for this entity</p>
          </div>
        ) : (
          filteredChanges.map((event) => (
            <ChangelogEntry
              key={event.id}
              event={event}
              onViewVersion={onViewVersion}
              onRevert={onRevert}
            />
          ))
        )}
      </div>

      {/* Load More */}
      {hasMore && (
        <button
          onClick={fetchMore}
          disabled={loading}
          className="w-full mt-4 py-2 text-blue-600 dark:text-blue-400 hover:underline disabled:text-gray-400 flex items-center justify-center gap-2"
          data-testid="load-more-button"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              Loading...
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              Load More...
            </>
          )}
        </button>
      )}
    </div>
  );
}

interface ChangelogEntryProps {
  event: ChangeEvent;
  onViewVersion?: (version: number) => void;
  onRevert?: (version: number) => void;
}

function ChangelogEntry({ event, onViewVersion, onRevert }: ChangelogEntryProps) {
  const changeTypeColors: Record<string, string> = {
    create: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    update: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    delete: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    relation_added: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    relation_removed: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  };

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value;
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  return (
    <div
      className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-800"
      data-testid="changelog-entry"
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-3 text-sm">
          <Clock className="w-4 h-4 text-gray-500" />
          <span className="text-gray-600 dark:text-gray-400">
            {new Date(event.timestamp).toLocaleString('de-DE')}
          </span>
          <span className="text-gray-400">-</span>
          <div className="flex items-center gap-1">
            <User className="w-4 h-4 text-gray-500" />
            <span className="font-medium text-gray-900 dark:text-gray-100">
              {event.changedBy}
            </span>
          </div>
        </div>
        <span
          className={`px-2 py-1 rounded text-xs font-medium ${
            changeTypeColors[event.changeType]
          }`}
        >
          {event.changeType.replace('_', ' ')}
        </span>
      </div>

      {/* Changes */}
      {event.changedFields.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded p-3 text-sm font-mono mb-3 max-h-64 overflow-y-auto">
          {event.changedFields.map((field) => (
            <div key={field} className="mb-2 last:mb-0">
              <div className="text-gray-500 dark:text-gray-400 text-xs mb-1">{field}:</div>
              <div className="flex items-start gap-2 flex-wrap">
                {event.oldValues[field] !== undefined && (
                  <span className="line-through text-red-600 dark:text-red-400 break-all">
                    {formatValue(event.oldValues[field])}
                  </span>
                )}
                {event.oldValues[field] !== undefined && event.newValues[field] !== undefined && (
                  <ArrowRight className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                )}
                {event.newValues[field] !== undefined && (
                  <span className="text-green-600 dark:text-green-400 break-all">
                    {formatValue(event.newValues[field])}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Reason */}
      {event.reason && (
        <div className="text-sm text-gray-600 dark:text-gray-400 italic mb-3">
          Reason: {event.reason}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => onViewVersion?.(event.version)}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
          data-testid="view-version-button"
        >
          <Eye className="w-4 h-4" />
          View Version {event.version}
        </button>
        {event.changeType !== 'create' && (
          <button
            onClick={() => onRevert?.(event.version - 1)}
            className="text-sm text-amber-600 dark:text-amber-400 hover:underline flex items-center gap-1"
            data-testid="revert-button"
          >
            <RotateCcw className="w-4 h-4" />
            Revert to Previous
          </button>
        )}
      </div>
    </div>
  );
}
