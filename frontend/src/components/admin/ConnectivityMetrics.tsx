/**
 * ConnectivityMetrics Component
 * Sprint 77 Feature 77.5 (TD-095): Entity Connectivity as Domain Training Metric
 *
 * Displays entity connectivity metrics with domain-specific benchmark comparison
 */

import { useConnectivityMetrics, type ConnectivityEvaluationResponse } from '../../hooks/useDomainTraining';
import { TrendingUp, TrendingDown, Check, AlertCircle } from 'lucide-react';

interface ConnectivityMetricsProps {
  /** Namespace ID to evaluate (e.g., "hotpotqa_large") */
  namespaceId: string;
  /** Domain type for benchmark (factual, narrative, technical, academic) */
  domainType?: 'factual' | 'narrative' | 'technical' | 'academic';
  /** Whether to show the section */
  enabled?: boolean;
}

export function ConnectivityMetrics({ namespaceId, domainType = 'factual', enabled = true }: ConnectivityMetricsProps) {
  const { data: metrics, isLoading, error } = useConnectivityMetrics(namespaceId, domainType, enabled);

  if (!enabled) {
    return null;
  }

  if (isLoading) {
    return (
      <section data-testid="connectivity-metrics-section">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Entity Connectivity</h3>
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <div className="inline-block w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="mt-2 text-sm text-gray-600">Loading connectivity metrics...</p>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section data-testid="connectivity-metrics-section">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Entity Connectivity</h3>
        <div className="bg-red-50 rounded-lg p-4 border border-red-200">
          <p className="text-sm text-red-700">Failed to load connectivity metrics</p>
          <p className="text-xs text-red-600 mt-1">{error.message}</p>
        </div>
      </section>
    );
  }

  if (!metrics) {
    return null;
  }

  return (
    <section data-testid="connectivity-metrics-section">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Entity Connectivity
        <span className="ml-2 text-xs font-normal text-gray-500">
          ({metrics.domain_type} domain)
        </span>
      </h3>

      <div className="bg-gray-50 rounded-lg p-4 space-y-4">
        {/* Key Metric: Relations per Entity */}
        <div className="pb-4 border-b border-gray-200">
          <ConnectivityGauge metrics={metrics} />
        </div>

        {/* Statistics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <MetricCard
            label="Entities"
            value={metrics.total_entities}
            testId="metric-entities"
          />
          <MetricCard
            label="Relationships"
            value={metrics.total_relationships}
            testId="metric-relationships"
          />
          <MetricCard
            label="Communities"
            value={metrics.total_communities}
            testId="metric-communities"
          />
        </div>

        {/* Recommendations */}
        {metrics.recommendations && metrics.recommendations.length > 0 && (
          <div className="pt-3 border-t border-gray-200">
            <h4 className="text-xs font-semibold text-gray-600 mb-2">Recommendations</h4>
            <ul className="space-y-1.5">
              {metrics.recommendations.map((recommendation, index) => (
                <li
                  key={index}
                  className="text-xs text-gray-700 flex items-start gap-2"
                  data-testid={`recommendation-${index}`}
                >
                  <span className="text-gray-400 select-none">•</span>
                  <span>{recommendation}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

/**
 * Connectivity Gauge Component
 * Shows relations_per_entity with benchmark range visualization
 */
function ConnectivityGauge({ metrics }: { metrics: ConnectivityEvaluationResponse }) {
  const { relations_per_entity, benchmark_min, benchmark_max, benchmark_status, within_benchmark } = metrics;

  // Calculate percentage for gauge (normalize to 0-100% based on benchmark range)
  const range = benchmark_max - benchmark_min;
  const relativeValue = relations_per_entity - benchmark_min;
  const percentage = Math.min(100, Math.max(0, (relativeValue / range) * 100));

  // Status colors
  const statusConfig = {
    below: {
      color: 'bg-yellow-500',
      textColor: 'text-yellow-700',
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200',
      icon: TrendingDown,
      label: 'Below Benchmark',
    },
    within: {
      color: 'bg-green-500',
      textColor: 'text-green-700',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      icon: Check,
      label: 'Within Benchmark',
    },
    above: {
      color: 'bg-orange-500',
      textColor: 'text-orange-700',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200',
      icon: TrendingUp,
      label: 'Above Benchmark',
    },
  };

  const config = statusConfig[benchmark_status];
  const Icon = config.icon;

  return (
    <div className="space-y-3">
      {/* Main Metric */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-2xl font-bold text-gray-900" data-testid="connectivity-value">
            {relations_per_entity.toFixed(2)}
          </div>
          <div className="text-xs text-gray-500 mt-0.5">
            relations per entity
          </div>
        </div>
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full ${config.bgColor} ${config.borderColor} border`}>
          <Icon className={`w-4 h-4 ${config.textColor}`} />
          <span className={`text-xs font-medium ${config.textColor}`}>
            {config.label}
          </span>
        </div>
      </div>

      {/* Benchmark Range */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>Benchmark Range</span>
          <span className="font-medium">
            {benchmark_min.toFixed(1)} - {benchmark_max.toFixed(1)}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`absolute top-0 left-0 h-full ${config.color} transition-all duration-300`}
            style={{ width: `${percentage}%` }}
            data-testid="connectivity-gauge"
          />
        </div>

        {/* Range Labels */}
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>{benchmark_min.toFixed(1)}</span>
          <span className="text-gray-400">Target Range</span>
          <span>{benchmark_max.toFixed(1)}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Metric Card Component
 * Displays a single metric value with label
 */
function MetricCard({ label, value, testId }: { label: string; value: number; testId: string }) {
  return (
    <div className="bg-white rounded-md px-3 py-2 border border-gray-200" data-testid={testId}>
      <div className="text-xs text-gray-500 mb-0.5">{label}</div>
      <div className="text-lg font-semibold text-gray-900">{value.toLocaleString()}</div>
    </div>
  );
}
