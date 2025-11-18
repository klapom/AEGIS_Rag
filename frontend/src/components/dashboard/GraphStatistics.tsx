/**
 * GraphStatistics Component
 * Sprint 29 Feature 29.4: Knowledge Graph Dashboard
 *
 * Displays high-level graph statistics in a responsive grid of stat cards
 */

import type { GraphStatistics as GraphStatisticsType } from '../../types/graph';

interface GraphStatisticsProps {
  stats: GraphStatisticsType;
  className?: string;
}

interface StatCardProps {
  title: string;
  value: number | string;
  icon: string; // Using emoji icons for simplicity (no lucide-react dependency)
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
  className?: string;
}

function StatCard({ title, value, icon, trend, className = '' }: StatCardProps) {
  return (
    <div
      className={`p-6 bg-white border-2 border-gray-200 rounded-xl hover:shadow-lg
                  hover:border-primary/50 transition-all duration-200 ${className}`}
    >
      {/* Icon and Title */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-3xl">{icon}</span>
        {trend && (
          <div
            className={`flex items-center space-x-1 text-sm font-medium ${
              trend.direction === 'up' ? 'text-green-600' : 'text-red-600'
            }`}
          >
            <span>{trend.direction === 'up' ? '↑' : '↓'}</span>
            <span>{Math.abs(trend.value)}%</span>
          </div>
        )}
      </div>

      {/* Value */}
      <div className="mb-2">
        <div className="text-3xl font-bold text-gray-900">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
      </div>

      {/* Title */}
      <div className="text-sm font-medium text-gray-500">{title}</div>
    </div>
  );
}

export function GraphStatistics({ stats, className = '' }: GraphStatisticsProps) {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}>
      {/* Total Nodes */}
      <StatCard
        title="Total Nodes"
        value={stats.node_count}
        icon="⚫"
      />

      {/* Total Edges */}
      <StatCard
        title="Total Edges"
        value={stats.edge_count}
        icon="🔗"
      />

      {/* Communities */}
      <StatCard
        title="Communities"
        value={stats.community_count}
        icon="👥"
      />

      {/* Average Degree */}
      <StatCard
        title="Avg Degree"
        value={stats.avg_degree.toFixed(2)}
        icon="📊"
      />
    </div>
  );
}
