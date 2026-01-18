/**
 * ChartControls Component
 * Sprint 111 Feature 111.2: Token Usage Chart
 *
 * Control panel for chart display options:
 * - Aggregation selector (daily/weekly/monthly)
 * - Provider filter
 * - Scale toggle (linear/logarithmic)
 */

import { BarChart3, Filter, Scale } from 'lucide-react';

export type AggregationType = 'daily' | 'weekly' | 'monthly';
export type ScaleType = 'linear' | 'log';

interface ChartControlsProps {
  aggregation: AggregationType;
  onAggregationChange: (agg: AggregationType) => void;
  providers: string[];
  selectedProvider: string;
  onProviderChange: (provider: string) => void;
  scale: ScaleType;
  onScaleChange: (scale: ScaleType) => void;
  className?: string;
}

export function ChartControls({
  aggregation,
  onAggregationChange,
  providers,
  selectedProvider,
  onProviderChange,
  scale,
  onScaleChange,
  className = '',
}: ChartControlsProps) {
  return (
    <div
      className={`flex flex-wrap items-center gap-4 ${className}`}
      data-testid="chart-controls"
    >
      {/* Provider Filter */}
      <div className="flex items-center gap-2">
        <Filter className="w-4 h-4 text-gray-500" />
        <select
          value={selectedProvider}
          onChange={(e) => onProviderChange(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
          data-testid="provider-filter"
        >
          <option value="all">All Providers</option>
          {providers.map((provider) => (
            <option key={provider} value={provider}>
              {provider.charAt(0).toUpperCase() + provider.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Aggregation Selector */}
      <div className="flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-gray-500" />
        <select
          value={aggregation}
          onChange={(e) => onAggregationChange(e.target.value as AggregationType)}
          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
          data-testid="aggregation-selector"
        >
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </select>
      </div>

      {/* Scale Toggle */}
      <div className="flex items-center gap-2" data-testid="scale-toggle">
        <Scale className="w-4 h-4 text-gray-500" />
        <div className="flex rounded-lg overflow-hidden border border-gray-300 dark:border-gray-600">
          <button
            onClick={() => onScaleChange('linear')}
            className={`px-3 py-1.5 text-sm font-medium transition-colors ${
              scale === 'linear'
                ? 'bg-blue-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
            data-testid="scale-linear"
          >
            Lin
          </button>
          <button
            onClick={() => onScaleChange('log')}
            className={`px-3 py-1.5 text-sm font-medium transition-colors ${
              scale === 'log'
                ? 'bg-blue-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
            data-testid="scale-log"
          >
            Log
          </button>
        </div>
      </div>
    </div>
  );
}
