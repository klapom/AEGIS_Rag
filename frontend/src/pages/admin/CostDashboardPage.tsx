/**
 * CostDashboardPage Component
 * Sprint 31 Feature 31.10b: Cost Dashboard UI Implementation
 *
 * Features:
 * - 4 summary cards: Total Cost, Total Tokens, Total Calls, Avg Cost/Call
 * - Budget status bars with alerts (warning/critical)
 * - Provider cost breakdown
 * - Top 5 models by cost
 * - Time range selector (7d/30d/all)
 * - Real-time cost tracking
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Loader2,
  AlertTriangle,
  DollarSign,
  Activity,
  Hash,
  TrendingUp,
  RefreshCw,
} from 'lucide-react';

interface ProviderCost {
  cost_usd: number;
  tokens: number;
  calls: number;
  avg_cost_per_call: number;
}

interface ModelCost {
  provider: string;
  cost_usd: number;
  tokens: number;
  calls: number;
}

interface BudgetStatus {
  limit_usd: number;
  spent_usd: number;
  utilization_percent: number;
  status: 'ok' | 'warning' | 'critical';
  remaining_usd: number;
}

interface CostStats {
  total_cost_usd: number;
  total_tokens: number;
  total_calls: number;
  avg_cost_per_call: number;
  by_provider: Record<string, ProviderCost>;
  by_model: Record<string, ModelCost>;
  budgets: Record<string, BudgetStatus>;
  time_range: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function CostDashboardPage() {
  const [stats, setStats] = useState<CostStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | 'all'>('7d');

  useEffect(() => {
    fetchCostStats();
  }, [timeRange]);

  const fetchCostStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(
        `${API_BASE_URL}/api/v1/admin/costs/stats?time_range=${timeRange}`
      );
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Failed to fetch cost stats`);
      }
      const data = await response.json();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading cost statistics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="max-w-md w-full p-6 bg-red-50 border-2 border-red-200 rounded-lg">
          <div className="flex items-center mb-4">
            <AlertTriangle className="h-6 w-6 text-red-600 mr-2" />
            <h2 className="text-lg font-semibold text-red-900">Error Loading Data</h2>
          </div>
          <p className="text-red-700 mb-4">{error}</p>
          <button
            onClick={fetchCostStats}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  // Budget alerts
  const criticalBudgets = Object.entries(stats.budgets).filter(
    ([, budget]) => budget.status === 'critical'
  );
  const warningBudgets = Object.entries(stats.budgets).filter(
    ([, budget]) => budget.status === 'warning'
  );

  return (
    <div
      className="min-h-screen bg-gray-50 p-6"
      data-testid="cost-dashboard"
    >
      {/* Back Link */}
      <Link
        to="/admin"
        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 mb-4"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to Admin
      </Link>

      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Cost Dashboard</h1>
          <p className="text-sm text-gray-600 mt-1">
            Monitor LLM costs, budgets, and usage across providers
          </p>
        </div>
        <div className="flex gap-3 items-center">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as '7d' | '30d' | 'all')}
            className="px-4 py-2 border-2 border-gray-300 rounded-lg bg-white text-gray-900 font-medium
                       hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="time-range-selector"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="all">All time</option>
          </select>
          <button
            onClick={fetchCostStats}
            className="p-2 border-2 border-gray-300 rounded-lg bg-white hover:bg-gray-50 transition-colors"
            title="Refresh data"
          >
            <RefreshCw className="h-5 w-5 text-gray-700" />
          </button>
        </div>
      </div>

      {/* Budget Alerts */}
      {criticalBudgets.length > 0 && (
        <div
          className="mb-6 p-4 bg-red-50 border-2 border-red-300 rounded-lg"
          data-testid="budget-alert-critical"
        >
          <div className="flex items-center mb-2">
            <AlertTriangle className="h-5 w-5 text-red-600 mr-2" />
            <h3 className="font-semibold text-red-900">Budget Exceeded</h3>
          </div>
          {criticalBudgets.map(([provider, budget]) => (
            <p key={provider} className="text-red-800 text-sm">
              <strong className="capitalize">{provider.replace('_', ' ')}</strong>: Over
              budget! ${budget.spent_usd.toFixed(2)} / ${budget.limit_usd.toFixed(2)} (
              {budget.utilization_percent.toFixed(0)}%)
            </p>
          ))}
        </div>
      )}

      {warningBudgets.length > 0 && (
        <div
          className="mb-6 p-4 bg-yellow-50 border-2 border-yellow-300 rounded-lg"
          data-testid="budget-alert-warning"
        >
          <div className="flex items-center mb-2">
            <AlertTriangle className="h-5 w-5 text-yellow-600 mr-2" />
            <h3 className="font-semibold text-yellow-900">Budget Warning</h3>
          </div>
          {warningBudgets.map(([provider, budget]) => (
            <p key={provider} className="text-yellow-800 text-sm">
              <strong className="capitalize">{provider.replace('_', ' ')}</strong>: Approaching
              limit - ${budget.spent_usd.toFixed(2)} / ${budget.limit_usd.toFixed(2)} (
              {budget.utilization_percent.toFixed(0)}%)
            </p>
          ))}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <SummaryCard
          title="Total Cost"
          value={`$${stats.total_cost_usd.toFixed(2)}`}
          icon={<DollarSign className="h-6 w-6 text-green-600" />}
          subtitle={`${timeRange} period`}
          testId="card-total-cost"
        />
        <SummaryCard
          title="Total Tokens"
          value={stats.total_tokens.toLocaleString()}
          icon={<Hash className="h-6 w-6 text-blue-600" />}
          subtitle={`${timeRange} period`}
          testId="card-total-tokens"
        />
        <SummaryCard
          title="Total Calls"
          value={stats.total_calls.toLocaleString()}
          icon={<Activity className="h-6 w-6 text-purple-600" />}
          subtitle={`${timeRange} period`}
          testId="card-total-calls"
        />
        <SummaryCard
          title="Avg Cost/Call"
          value={`$${stats.avg_cost_per_call.toFixed(4)}`}
          icon={<TrendingUp className="h-6 w-6 text-orange-600" />}
          subtitle="Per API call"
          testId="card-avg-cost"
        />
      </div>

      {/* Budget Status Bars */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6 border-2 border-gray-200">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Budget Status</h2>
        <div className="space-y-4">
          {Object.entries(stats.budgets).map(([provider, budget]) => (
            <div key={provider} data-testid={`budget-${provider}`}>
              <div className="flex justify-between mb-2">
                <span className="font-medium text-gray-900 capitalize">
                  {provider.replace('_', ' ')}
                </span>
                <span className="text-sm text-gray-700 font-medium">
                  ${budget.spent_usd.toFixed(2)} / ${budget.limit_usd.toFixed(2)}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full transition-all ${
                    budget.status === 'critical'
                      ? 'bg-red-500'
                      : budget.status === 'warning'
                      ? 'bg-yellow-500'
                      : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(budget.utilization_percent, 100)}%` }}
                  data-testid={`budget-progress-${provider}`}
                />
              </div>
              <p className="text-xs text-gray-600 mt-1">
                {budget.utilization_percent.toFixed(1)}% used, ${budget.remaining_usd.toFixed(2)}{' '}
                remaining
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Provider & Model Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6 border-2 border-gray-200">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Cost by Provider</h2>
          <div className="space-y-3">
            {Object.entries(stats.by_provider).map(([provider, data]) => (
              <div
                key={provider}
                className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-200"
                data-testid={`provider-${provider}`}
              >
                <div>
                  <p className="font-medium text-gray-900 capitalize">
                    {provider.replace('_', ' ')}
                  </p>
                  <p className="text-xs text-gray-600">
                    {data.calls.toLocaleString()} calls, {data.tokens.toLocaleString()} tokens
                  </p>
                </div>
                <span className="text-lg font-bold text-gray-900">
                  ${data.cost_usd.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 border-2 border-gray-200">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Top Models by Cost</h2>
          <div className="space-y-3">
            {Object.entries(stats.by_model)
              .sort((a, b) => b[1].cost_usd - a[1].cost_usd)
              .slice(0, 5)
              .map(([model, data]) => (
                <div
                  key={model}
                  className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-200"
                  data-testid={`model-${model}`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{model}</p>
                    <p className="text-xs text-gray-600">
                      {data.calls.toLocaleString()} calls, {data.tokens.toLocaleString()} tokens
                    </p>
                  </div>
                  <span className="text-lg font-bold text-gray-900 ml-4">
                    ${data.cost_usd.toFixed(2)}
                  </span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}

interface SummaryCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  subtitle: string;
  testId: string;
}

function SummaryCard({ title, value, icon, subtitle, testId }: SummaryCardProps) {
  return (
    <div
      className="bg-white rounded-lg shadow-md p-6 border-2 border-gray-200 hover:shadow-lg transition-shadow"
      data-testid={testId}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        {icon}
      </div>
      <p className="text-3xl font-bold text-gray-900 mb-1">{value}</p>
      <p className="text-xs text-gray-500">{subtitle}</p>
    </div>
  );
}
