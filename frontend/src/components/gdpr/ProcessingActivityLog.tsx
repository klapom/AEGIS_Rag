/**
 * ProcessingActivityLog Component
 * Sprint 98 Feature 98.3: GDPR Consent Manager UI
 *
 * Displays processing activities log (GDPR Article 30).
 * Shows all data processing activities with timestamps, purposes, and legal basis.
 */

import { useState } from 'react';
import { Clock, Search } from 'lucide-react';
import type { ProcessingActivity } from '../../types/gdpr';
import { getLegalBasisText } from '../../types/gdpr';

interface ProcessingActivityLogProps {
  activities: ProcessingActivity[];
  onLoadMore: () => void;
  hasMore: boolean;
}

export function ProcessingActivityLog({
  activities,
  onLoadMore,
  hasMore,
}: ProcessingActivityLogProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredActivities = activities.filter(
    (activity) =>
      searchQuery === '' ||
      activity.userId?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      activity.activity.toLowerCase().includes(searchQuery.toLowerCase()) ||
      activity.purpose.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Processing Activities (Art. 30)
        </h3>
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {activities.length} total activities
        </span>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search activities..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Activity Timeline */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {filteredActivities.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No activities found.
          </div>
        ) : (
          filteredActivities.map((activity) => (
            <div
              key={activity.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3 space-y-2"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {new Date(activity.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
                    <span className="font-medium">{activity.userId || 'System'}</span> •{' '}
                    {activity.activity}
                  </p>
                </div>
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                <div>
                  <span className="font-medium">Purpose:</span> {activity.purpose}
                </div>
                <div>
                  <span className="font-medium">Legal Basis:</span>{' '}
                  {getLegalBasisText(activity.legalBasis)}
                </div>
                {activity.skillName && (
                  <div>
                    <span className="font-medium">Skill:</span> {activity.skillName}
                  </div>
                )}
                {activity.duration && (
                  <div>
                    <span className="font-medium">Duration:</span> {activity.duration}ms
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Load More */}
      {hasMore && (
        <button
          onClick={onLoadMore}
          className="w-full px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
        >
          Load More
        </button>
      )}
    </div>
  );
}
