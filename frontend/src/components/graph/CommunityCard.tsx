/**
 * CommunityCard Component
 * Sprint 116 Feature 116.7: Graph Communities UI
 *
 * Features:
 * - Display community metadata (name, size, density)
 * - Visual indicators for community health
 * - Compact and full-size variants
 * - Hover effects and clickable
 * - Accessibility support
 */

import { Users, TrendingUp, Info } from 'lucide-react';
import type { Community } from '../../types/graph';

interface CommunityCardProps {
  community: Community;
  onClick?: () => void;
  compact?: boolean;
  selected?: boolean;
}

/**
 * Card component for displaying a single community
 *
 * @param community Community data
 * @param onClick Callback when card is clicked
 * @param compact Whether to use compact layout (for list view)
 * @param selected Whether this card is currently selected
 */
export function CommunityCard({
  community,
  onClick,
  compact = false,
  selected = false,
}: CommunityCardProps) {
  // Calculate health indicator based on size and density
  const healthScore = calculateHealthScore(community);

  if (compact) {
    return <CompactCard community={community} onClick={onClick} selected={selected} />;
  }

  return (
    <div
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={`
        bg-white rounded-lg border-2 transition-all cursor-pointer
        ${
          selected
            ? 'border-purple-500 shadow-lg ring-2 ring-purple-200'
            : 'border-gray-200 hover:border-purple-300 hover:shadow-md'
        }
        ${onClick ? 'cursor-pointer' : ''}
      `}
      data-testid="community-card"
    >
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 line-clamp-1 mb-1">
              {community.topic}
            </h3>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Users className="w-4 h-4" />
              <span>{community.size} members</span>
            </div>
          </div>
          {/* Health Indicator */}
          <div
            className={`
              w-3 h-3 rounded-full flex-shrink-0 mt-1
              ${
                healthScore >= 0.7
                  ? 'bg-green-500'
                  : healthScore >= 0.4
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }
            `}
            title={`Health: ${Math.round(healthScore * 100)}%`}
            aria-label={`Community health: ${Math.round(healthScore * 100)}%`}
          />
        </div>

        {/* Description */}
        {community.description && (
          <p className="text-sm text-gray-600 line-clamp-2 mb-3">
            {community.description}
          </p>
        )}

        {/* Metrics */}
        <div className="space-y-2">
          {/* Density Bar */}
          {community.density !== undefined && (
            <div>
              <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                <div className="flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" />
                  <span>Density</span>
                </div>
                <span className="font-medium">{(community.density * 100).toFixed(1)}%</span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-purple-500 rounded-full transition-all"
                  style={{ width: `${community.density * 100}%` }}
                  aria-label={`Density: ${(community.density * 100).toFixed(1)}%`}
                />
              </div>
            </div>
          )}

          {/* Community ID Badge */}
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Info className="w-3 h-3" />
            <code className="px-1.5 py-0.5 bg-gray-100 rounded font-mono">{community.id}</code>
          </div>
        </div>

        {/* Footer */}
        {onClick && (
          <div className="mt-4 pt-3 border-t border-gray-100">
            <button
              className="text-sm font-medium text-purple-600 hover:text-purple-700 transition-colors"
              aria-label={`View details for ${community.topic}`}
            >
              View Details →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Compact variant for list view
 */
function CompactCard({
  community,
  onClick,
  selected,
}: {
  community: Community;
  onClick?: () => void;
  selected: boolean;
}) {
  const healthScore = calculateHealthScore(community);

  return (
    <div
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={`
        bg-white rounded-lg border-2 transition-all p-4
        ${
          selected
            ? 'border-purple-500 shadow-md ring-2 ring-purple-200'
            : 'border-gray-200 hover:border-purple-300 hover:shadow-sm'
        }
        ${onClick ? 'cursor-pointer' : ''}
      `}
      data-testid="community-card-compact"
    >
      <div className="flex items-center justify-between">
        {/* Left: Topic and Members */}
        <div className="flex items-center gap-4 flex-1 min-w-0">
          <div
            className={`
              w-2 h-2 rounded-full flex-shrink-0
              ${
                healthScore >= 0.7
                  ? 'bg-green-500'
                  : healthScore >= 0.4
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }
            `}
            title={`Health: ${Math.round(healthScore * 100)}%`}
          />
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 truncate">{community.topic}</h3>
            {community.description && (
              <p className="text-sm text-gray-600 truncate">{community.description}</p>
            )}
          </div>
        </div>

        {/* Right: Metrics */}
        <div className="flex items-center gap-6 flex-shrink-0">
          <div className="text-right">
            <div className="text-sm font-medium text-gray-900">{community.size}</div>
            <div className="text-xs text-gray-500">members</div>
          </div>
          {community.density !== undefined && (
            <div className="text-right">
              <div className="text-sm font-medium text-gray-900">
                {(community.density * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-500">density</div>
            </div>
          )}
          {onClick && (
            <div className="text-purple-600">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Calculate health score based on size and density
 * Health = 0.6 * normalized_size + 0.4 * density
 *
 * @param community Community data
 * @returns Health score between 0 and 1
 */
function calculateHealthScore(community: Community): number {
  // Normalize size (assume max community size is 100, but cap at 1.0)
  const normalizedSize = Math.min(community.size / 100, 1.0);

  // Use density if available, otherwise default to 0.5
  const density = community.density ?? 0.5;

  // Weighted average: 60% size, 40% density
  return normalizedSize * 0.6 + density * 0.4;
}

/**
 * Summary variant for showing key stats only
 */
interface CommunitySummaryProps {
  community: Community;
  showDescription?: boolean;
}

export function CommunitySummary({ community, showDescription = false }: CommunitySummaryProps) {
  return (
    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
      <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
        <Users className="w-5 h-5 text-purple-600" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-gray-900 truncate">{community.topic}</div>
        {showDescription && community.description && (
          <div className="text-xs text-gray-600 truncate">{community.description}</div>
        )}
        <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
          <span>{community.size} members</span>
          {community.density !== undefined && (
            <>
              <span>•</span>
              <span>{(community.density * 100).toFixed(1)}% density</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
