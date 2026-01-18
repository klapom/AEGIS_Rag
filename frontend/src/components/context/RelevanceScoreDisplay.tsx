/**
 * RelevanceScoreDisplay Component
 * Sprint 111 Feature 111.1: Long Context UI
 *
 * Visualization component for displaying relevance scores:
 * - Overall document relevance
 * - Score distribution across chunks
 * - Visual bar charts for score comparison
 */

import { useMemo } from 'react';
import { TrendingUp, BarChart3 } from 'lucide-react';

interface RelevanceScore {
  chunkId: string;
  chunkIndex: number;
  score: number;
  label?: string;
}

interface RelevanceScoreDisplayProps {
  scores: RelevanceScore[];
  averageScore?: number;
  className?: string;
}

export function RelevanceScoreDisplay({
  scores,
  averageScore,
  className = '',
}: RelevanceScoreDisplayProps) {
  const computedAverage = useMemo(() => {
    if (averageScore !== undefined) return averageScore;
    if (scores.length === 0) return 0;
    const sum = scores.reduce((acc, s) => acc + s.score, 0);
    return sum / scores.length;
  }, [scores, averageScore]);

  const distribution = useMemo(() => {
    const bins = { high: 0, medium: 0, low: 0 };
    scores.forEach((s) => {
      if (s.score >= 0.8) bins.high++;
      else if (s.score >= 0.5) bins.medium++;
      else bins.low++;
    });
    return bins;
  }, [scores]);

  const topScores = useMemo(() => {
    return [...scores].sort((a, b) => b.score - a.score).slice(0, 5);
  }, [scores]);

  const getScoreBarColor = (score: number): string => {
    if (score >= 0.8) return 'bg-green-500';
    if (score >= 0.5) return 'bg-yellow-500';
    return 'bg-gray-400';
  };

  const getScoreTextColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-600 dark:text-green-400';
    if (score >= 0.5) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-4 ${className}`}
      data-testid="relevance-score-display"
    >
      {/* Header with Average */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            Relevance Scores
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500 dark:text-gray-400">Average:</span>
          <span
            className={`text-lg font-bold ${getScoreTextColor(computedAverage)}`}
            data-testid="average-score"
          >
            {(computedAverage * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Distribution Summary */}
      <div className="grid grid-cols-3 gap-3 mb-4" data-testid="score-distribution">
        <div className="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <div className="text-2xl font-bold text-green-600 dark:text-green-400" data-testid="high-score-count">
            {distribution.high}
          </div>
          <div className="text-xs text-green-700 dark:text-green-300">High (≥80%)</div>
        </div>
        <div className="text-center p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
          <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400" data-testid="medium-score-count">
            {distribution.medium}
          </div>
          <div className="text-xs text-yellow-700 dark:text-yellow-300">Medium (50-79%)</div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-2xl font-bold text-gray-600 dark:text-gray-400" data-testid="low-score-count">
            {distribution.low}
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400">Low (&lt;50%)</div>
        </div>
      </div>

      {/* Top Scoring Chunks */}
      {topScores.length > 0 && (
        <div data-testid="top-scores">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Top Scoring Chunks
            </span>
          </div>
          <div className="space-y-2">
            {topScores.map((score, idx) => (
              <div
                key={score.chunkId}
                className="flex items-center gap-2"
                data-testid={`top-score-${idx}`}
              >
                <span className="text-xs text-gray-500 w-6">#{score.chunkIndex + 1}</span>
                <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${getScoreBarColor(score.score)} transition-all`}
                    style={{ width: `${score.score * 100}%` }}
                  />
                </div>
                <span className={`text-xs font-medium w-12 text-right ${getScoreTextColor(score.score)}`}>
                  {(score.score * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {scores.length === 0 && (
        <div className="text-center py-4 text-gray-500 dark:text-gray-400" data-testid="no-scores">
          No relevance scores available
        </div>
      )}
    </div>
  );
}
