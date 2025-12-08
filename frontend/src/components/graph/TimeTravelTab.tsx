/**
 * TimeTravelTab Component
 * Sprint 39 Feature 39.5: Time Travel Tab (8 SP)
 *
 * Features:
 * - Date slider with quick jumps (1 week ago, 1 month ago)
 * - Date picker input
 * - Temporal graph visualization
 * - Entity count statistics (total, changed, new)
 * - Compare with Today, Export Snapshot, Show Changes Only actions
 */

import { useState, useMemo } from 'react';
import { Calendar, Clock, Download, GitCompare, Filter } from 'lucide-react';
import type { GraphData } from '../../types/graph';
import { useTemporalQuery } from '../../hooks/useTemporalQuery';
import { GraphViewer } from './GraphViewer';

interface TimeTravelTabProps {
  graphData?: GraphData;
  onDateChange?: (date: Date) => void;
}

export function TimeTravelTab({ graphData, onDateChange }: TimeTravelTabProps) {
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [appliedDate, setAppliedDate] = useState<Date | null>(null);

  const { data: temporalData, loading, error } = useTemporalQuery(appliedDate);

  // Calculate date range from graph data or use defaults
  const { minDate, maxDate } = useMemo(() => {
    if (graphData?.nodes && graphData.nodes.length > 0) {
      const dates = graphData.nodes
        .map((n) => n.metadata?.created_at)
        .filter((d): d is string => Boolean(d))
        .map((d) => new Date(d));

      if (dates.length > 0) {
        return {
          minDate: new Date(Math.min(...dates.map((d) => d.getTime()))),
          maxDate: new Date(),
        };
      }
    }

    // Default to 1 year ago
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
    return {
      minDate: oneYearAgo,
      maxDate: new Date(),
    };
  }, [graphData]);

  const handleApply = () => {
    setAppliedDate(selectedDate);
    onDateChange?.(selectedDate);
  };

  const handleQuickJump = (daysAgo: number) => {
    const date = new Date();
    date.setDate(date.getDate() - daysAgo);
    setSelectedDate(date);
  };

  const handleExportSnapshot = () => {
    if (!temporalData) return;

    const dataStr = JSON.stringify(temporalData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);

    const exportFileDefaultName = `graph-snapshot-${selectedDate.toISOString().split('T')[0]}.json`;

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  return (
    <div className="time-travel-tab p-4" data-testid="time-travel-tab">
      {/* Time Travel Controls */}
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 mb-4 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-amber-600" />
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">Time Travel Mode</h3>
          </div>
          <span className="px-2 py-1 bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200 rounded text-sm font-medium">
            Active
          </span>
        </div>

        {/* Date Slider */}
        <div className="mb-4">
          <label className="text-sm text-gray-600 dark:text-gray-400 mb-2 block font-medium">
            Timeline
          </label>
          <input
            type="range"
            min={minDate.getTime()}
            max={maxDate.getTime()}
            value={selectedDate.getTime()}
            onChange={(e) => setSelectedDate(new Date(Number(e.target.value)))}
            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
            data-testid="time-slider"
          />
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
            <span>{minDate.toLocaleDateString('de-DE')}</span>
            <span>Heute</span>
          </div>
        </div>

        {/* Date Picker */}
        <div className="flex flex-wrap items-center gap-4 mb-4">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-500" />
            <label className="text-sm text-gray-600 dark:text-gray-400 font-medium">
              Selected Date:
            </label>
          </div>
          <input
            type="date"
            value={selectedDate.toISOString().split('T')[0]}
            onChange={(e) => setSelectedDate(new Date(e.target.value))}
            max={new Date().toISOString().split('T')[0]}
            className="border border-gray-300 dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            data-testid="date-picker"
          />
          <button
            onClick={handleApply}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            data-testid="apply-date-button"
          >
            {loading ? 'Loading...' : 'Apply'}
          </button>
        </div>

        {/* Quick Jumps */}
        <div className="flex flex-wrap gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-400 font-medium mr-2">
            Quick Jumps:
          </span>
          <button
            onClick={() => handleQuickJump(7)}
            className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            data-testid="quick-jump-1-week"
          >
            1 Week Ago
          </button>
          <button
            onClick={() => handleQuickJump(30)}
            className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            data-testid="quick-jump-1-month"
          >
            1 Month Ago
          </button>
          <button
            onClick={() => handleQuickJump(90)}
            className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            data-testid="quick-jump-3-months"
          >
            3 Months Ago
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-4">
          <p className="text-red-800 dark:text-red-200 text-sm">
            Error loading temporal data: {error.message}
          </p>
        </div>
      )}

      {/* Temporal Graph View */}
      {temporalData && (
        <>
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-4">
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
              Graph Snapshot - {appliedDate?.toLocaleDateString('de-DE')}
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 text-sm">
              <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded">
                <p className="text-gray-600 dark:text-gray-400">Entities shown:</p>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {temporalData.total_count}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  as of {appliedDate?.toLocaleDateString('de-DE')}
                </p>
              </div>
              <div className="bg-amber-50 dark:bg-amber-900/20 p-3 rounded">
                <p className="text-gray-600 dark:text-gray-400">Changed since then:</p>
                <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">
                  {temporalData.changed_count ?? 0}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">entities modified</p>
              </div>
              <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded">
                <p className="text-gray-600 dark:text-gray-400">New since then:</p>
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {temporalData.new_count ?? 0}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">entities created</p>
              </div>
            </div>

            {/* Graph Visualization */}
            {temporalData.graphData && (
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                <GraphViewer
                  data={temporalData.graphData}
                  loading={false}
                  maxNodes={100}
                />
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            <button
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
              data-testid="compare-with-today"
            >
              <GitCompare className="w-4 h-4" />
              Compare with Today
            </button>
            <button
              onClick={handleExportSnapshot}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
              data-testid="export-snapshot"
            >
              <Download className="w-4 h-4" />
              Export Snapshot
            </button>
            <button
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
              data-testid="show-changes-only"
            >
              <Filter className="w-4 h-4" />
              Show Changes Only
            </button>
          </div>
        </>
      )}

      {/* Empty State */}
      {!appliedDate && !loading && (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <Clock className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Select a date and click Apply to view the graph state at that point in time</p>
        </div>
      )}
    </div>
  );
}
