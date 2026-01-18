/**
 * TokenUsageChart Component
 * Sprint 111 Feature 111.2: Token Usage Chart
 *
 * Line chart showing token usage over time with:
 * - Recharts library for visualization
 * - Responsive container
 * - Tooltips with detailed info
 * - Legend for multiple providers
 * - Export as PNG functionality
 */

import { useState, useRef, useCallback, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import { Download, Image, Loader2 } from 'lucide-react';
import { TimeRangeSlider } from './TimeRangeSlider';
import { ChartControls } from './ChartControls';
import type { AggregationType, ScaleType } from './ChartControls';

export interface TokenUsageDataPoint {
  date: string;
  tokens: number;
  cost_usd: number;
  provider: string;
}

interface TokenUsageChartProps {
  data: TokenUsageDataPoint[];
  isLoading?: boolean;
  error?: string | null;
  onTimeRangeChange?: (days: number) => void;
  onAggregationChange?: (agg: AggregationType) => void;
  onProviderChange?: (provider: string) => void;
  className?: string;
}

// Color palette for providers
const PROVIDER_COLORS: Record<string, string> = {
  ollama: '#8884d8',
  alibaba_cloud: '#82ca9d',
  openai: '#ffc658',
  azure: '#ff7300',
  anthropic: '#ff6b6b',
  google: '#4ecdc4',
};

const DEFAULT_COLOR = '#8884d8';

export function TokenUsageChart({
  data,
  isLoading = false,
  error = null,
  onTimeRangeChange,
  onAggregationChange,
  onProviderChange,
  className = '',
}: TokenUsageChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [timeRange, setTimeRange] = useState(30);
  const [aggregation, setAggregation] = useState<AggregationType>('daily');
  const [selectedProvider, setSelectedProvider] = useState('all');
  const [scale, setScale] = useState<ScaleType>('linear');
  const [isExporting, setIsExporting] = useState(false);

  // Get unique providers from data
  const providers = useMemo(() => {
    const uniqueProviders = new Set(data.map((d) => d.provider));
    return Array.from(uniqueProviders);
  }, [data]);

  // Filter and aggregate data
  const chartData = useMemo(() => {
    // Filter by provider
    let filtered = selectedProvider === 'all'
      ? data
      : data.filter((d) => d.provider === selectedProvider);

    // Group by date
    const grouped = new Map<string, { tokens: number; cost_usd: number; [key: string]: number }>();

    filtered.forEach((point) => {
      const existing = grouped.get(point.date) || { tokens: 0, cost_usd: 0 };
      existing.tokens += point.tokens;
      existing.cost_usd += point.cost_usd;

      // Track by provider for multi-line chart
      const providerKey = `tokens_${point.provider}`;
      existing[providerKey] = (existing[providerKey] || 0) + point.tokens;

      grouped.set(point.date, existing);
    });

    // Convert to array and sort by date
    return Array.from(grouped.entries())
      .map(([date, values]) => ({ date, ...values }))
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [data, selectedProvider]);

  // Calculate totals
  const totals = useMemo(() => {
    return chartData.reduce(
      (acc, point) => ({
        tokens: acc.tokens + point.tokens,
        cost_usd: acc.cost_usd + point.cost_usd,
      }),
      { tokens: 0, cost_usd: 0 }
    );
  }, [chartData]);

  // Format number for display
  const formatNumber = (value: number): string => {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
    return value.toString();
  };

  // Handle time range change
  const handleTimeRangeChange = useCallback((days: number) => {
    setTimeRange(days);
    onTimeRangeChange?.(days);
  }, [onTimeRangeChange]);

  // Handle aggregation change
  const handleAggregationChange = useCallback((agg: AggregationType) => {
    setAggregation(agg);
    onAggregationChange?.(agg);
  }, [onAggregationChange]);

  // Handle provider change
  const handleProviderChange = useCallback((provider: string) => {
    setSelectedProvider(provider);
    onProviderChange?.(provider);
  }, [onProviderChange]);

  // Export chart as PNG
  const handleExport = useCallback(async () => {
    if (!chartRef.current) return;

    setIsExporting(true);
    try {
      // Use html2canvas if available, or create a simple download
      const svgElement = chartRef.current.querySelector('svg');
      if (!svgElement) {
        throw new Error('No chart SVG found');
      }

      // Create a canvas
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const svgData = new XMLSerializer().serializeToString(svgElement);
      const img = new Image();

      // Set dimensions
      const rect = svgElement.getBoundingClientRect();
      canvas.width = rect.width * 2;
      canvas.height = rect.height * 2;

      // Draw background
      if (ctx) {
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.scale(2, 2);
      }

      // Convert SVG to image
      const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
      const svgUrl = URL.createObjectURL(svgBlob);

      img.onload = () => {
        ctx?.drawImage(img, 0, 0);
        URL.revokeObjectURL(svgUrl);

        // Download
        const a = document.createElement('a');
        a.href = canvas.toDataURL('image/png');
        a.download = `token-usage-${new Date().toISOString().split('T')[0]}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setIsExporting(false);
      };

      img.onerror = () => {
        URL.revokeObjectURL(svgUrl);
        setIsExporting(false);
      };

      img.src = svgUrl;
    } catch (err) {
      console.error('Export error:', err);
      setIsExporting(false);
    }
  }, []);

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;

    return (
      <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
        <p className="font-medium text-gray-900 dark:text-gray-100 mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-600 dark:text-gray-400">{entry.name}:</span>
            <span className="font-medium text-gray-900 dark:text-gray-100">
              {formatNumber(entry.value)}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-6 ${className}`}
      data-testid="token-usage-chart"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Token Usage Over Time
        </h3>
        <button
          onClick={handleExport}
          disabled={isExporting || isLoading}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors disabled:opacity-50"
          data-testid="export-chart-button"
        >
          {isExporting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Image className="w-4 h-4" />
          )}
          Export
        </button>
      </div>

      {/* Time Range Slider */}
      <div className="mb-4">
        <TimeRangeSlider
          value={timeRange}
          onChange={handleTimeRangeChange}
        />
      </div>

      {/* Chart Controls */}
      <div className="mb-4">
        <ChartControls
          aggregation={aggregation}
          onAggregationChange={handleAggregationChange}
          providers={providers}
          selectedProvider={selectedProvider}
          onProviderChange={handleProviderChange}
          scale={scale}
          onScaleChange={setScale}
        />
      </div>

      {/* Chart Area */}
      <div ref={chartRef} className="h-80" data-testid="chart-container">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full text-red-500" data-testid="chart-error">
            {error}
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400" data-testid="chart-empty">
            No data available for the selected time range
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorTokens" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                stroke="#9ca3af"
              />
              <YAxis
                scale={scale === 'log' ? 'log' : 'auto'}
                domain={scale === 'log' ? ['auto', 'auto'] : [0, 'auto']}
                tickFormatter={(value) => formatNumber(value)}
                tick={{ fontSize: 12 }}
                stroke="#9ca3af"
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Area
                type="monotone"
                dataKey="tokens"
                name="Tokens"
                stroke="#8884d8"
                fillOpacity={1}
                fill="url(#colorTokens)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Summary */}
      {!isLoading && !error && chartData.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between text-sm" data-testid="chart-summary">
          <span className="text-gray-600 dark:text-gray-400">
            Total: <span className="font-bold text-gray-900 dark:text-gray-100">{formatNumber(totals.tokens)} tokens</span>
          </span>
          <span className="text-gray-600 dark:text-gray-400">
            Cost: <span className="font-bold text-green-600 dark:text-green-400">${totals.cost_usd.toFixed(2)}</span>
          </span>
          <span className="text-gray-600 dark:text-gray-400">
            Last {timeRange} days
          </span>
        </div>
      )}
    </div>
  );
}
