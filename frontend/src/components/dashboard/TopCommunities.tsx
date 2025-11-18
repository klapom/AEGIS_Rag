/**
 * TopCommunities Component
 * Sprint 29 Feature 29.4: Knowledge Graph Dashboard
 *
 * Displays the top N communities by member count in a table or card list
 */

import type { Community } from '../../types/graph';

interface TopCommunitiesProps {
  communities: Community[];
  onCommunityClick?: (communityId: string) => void;
  className?: string;
}

export function TopCommunities({
  communities,
  onCommunityClick,
  className = '',
}: TopCommunitiesProps) {
  if (communities.length === 0) {
    return (
      <div className={`p-8 text-center text-gray-500 ${className}`}>
        <p className="text-lg">No communities found</p>
        <p className="text-sm mt-2">Communities will appear after graph indexing</p>
      </div>
    );
  }

  return (
    <div className={`overflow-hidden ${className}`}>
      {/* Table View for larger screens */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b-2 border-gray-200">
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                Rank
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                Topic
              </th>
              <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">
                Members
              </th>
              {communities.some((c) => c.density !== undefined) && (
                <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">
                  Density
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {communities.map((community, index) => (
              <tr
                key={community.id}
                onClick={() => onCommunityClick?.(community.id)}
                className={`border-b border-gray-100 transition-colors ${
                  onCommunityClick
                    ? 'hover:bg-gray-50 cursor-pointer'
                    : ''
                }`}
              >
                <td className="px-4 py-4">
                  <div className="flex items-center justify-center w-8 h-8 bg-primary/10 rounded-lg">
                    <span className="text-sm font-bold text-primary">
                      {index + 1}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-4">
                  <div className="text-sm font-medium text-gray-900">
                    {community.topic || `Community ${community.id}`}
                  </div>
                </td>
                <td className="px-4 py-4 text-right">
                  <span className="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                    {(community.size || community.member_count || 0).toLocaleString()}
                  </span>
                </td>
                {community.density !== undefined && (
                  <td className="px-4 py-4 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-500 rounded-full"
                          style={{ width: `${community.density * 100}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-600">
                        {(community.density * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Card View for mobile */}
      <div className="md:hidden space-y-3">
        {communities.map((community, index) => (
          <div
            key={community.id}
            onClick={() => onCommunityClick?.(community.id)}
            className={`p-4 bg-white border-2 border-gray-200 rounded-xl transition-all ${
              onCommunityClick
                ? 'hover:shadow-lg hover:border-primary/50 cursor-pointer'
                : ''
            }`}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                  <span className="text-sm font-bold text-primary">
                    {index + 1}
                  </span>
                </div>
                <div>
                  <div className="text-sm font-semibold text-gray-900">
                    {community.topic || `Community ${community.id}`}
                  </div>
                </div>
              </div>
              <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                {community.size || community.member_count || 0}
              </span>
            </div>
            {community.density !== undefined && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Density:</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500 rounded-full"
                        style={{ width: `${community.density * 100}%` }}
                      />
                    </div>
                    <span className="text-gray-700">
                      {(community.density * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
