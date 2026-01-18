/**
 * ContextCompressionPanel Component
 * Sprint 111 Feature 111.1: Long Context UI
 *
 * UI for selecting and applying context compression strategies:
 * - Summarization: LLM-based content summarization
 * - Filtering: Remove low-relevance chunks
 * - Truncation: Keep top-N relevant chunks
 * - Hybrid: Combination of strategies
 */

import { useState } from 'react';
import { Minimize2, Wand2, Filter, Scissors, Layers } from 'lucide-react';

export type CompressionStrategy = 'summarization' | 'filtering' | 'truncation' | 'hybrid';

interface CompressionSettings {
  strategy: CompressionStrategy;
  targetReduction: number; // 0-100 percentage
  minRelevanceThreshold: number; // 0-1
  maxChunks?: number;
}

interface ContextCompressionPanelProps {
  currentTokens: number;
  maxTokens: number;
  onCompress: (settings: CompressionSettings) => void;
  isCompressing?: boolean;
  className?: string;
}

const strategies: {
  id: CompressionStrategy;
  name: string;
  description: string;
  icon: typeof Wand2;
}[] = [
  {
    id: 'summarization',
    name: 'Summarization',
    description: 'Use LLM to summarize content while preserving key information',
    icon: Wand2,
  },
  {
    id: 'filtering',
    name: 'Relevance Filtering',
    description: 'Remove chunks below relevance threshold',
    icon: Filter,
  },
  {
    id: 'truncation',
    name: 'Top-K Truncation',
    description: 'Keep only the top N most relevant chunks',
    icon: Scissors,
  },
  {
    id: 'hybrid',
    name: 'Hybrid',
    description: 'Combine filtering + summarization for optimal compression',
    icon: Layers,
  },
];

export function ContextCompressionPanel({
  currentTokens,
  maxTokens,
  onCompress,
  isCompressing = false,
  className = '',
}: ContextCompressionPanelProps) {
  const [selectedStrategy, setSelectedStrategy] = useState<CompressionStrategy>('filtering');
  const [targetReduction, setTargetReduction] = useState(50);
  const [relevanceThreshold, setRelevanceThreshold] = useState(0.3);
  const [maxChunks, setMaxChunks] = useState(20);

  const estimatedTokensAfter = Math.round(currentTokens * (1 - targetReduction / 100));
  const utilizationAfter = Math.round((estimatedTokensAfter / maxTokens) * 100);

  const handleCompress = () => {
    onCompress({
      strategy: selectedStrategy,
      targetReduction,
      minRelevanceThreshold: relevanceThreshold,
      maxChunks: selectedStrategy === 'truncation' ? maxChunks : undefined,
    });
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border-2 border-gray-200 dark:border-gray-700 p-4 ${className}`}
      data-testid="context-compression-panel"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Minimize2 className="w-5 h-5 text-purple-600 dark:text-purple-400" />
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">
          Context Compression
        </h3>
      </div>

      {/* Strategy Selection */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Compression Strategy
        </label>
        <div className="grid grid-cols-2 gap-2" data-testid="strategy-options">
          {strategies.map((strategy) => {
            const Icon = strategy.icon;
            const isSelected = selectedStrategy === strategy.id;
            return (
              <button
                key={strategy.id}
                onClick={() => setSelectedStrategy(strategy.id)}
                className={`p-3 rounded-lg text-left transition-all ${
                  isSelected
                    ? 'bg-purple-100 dark:bg-purple-900/30 border-2 border-purple-500'
                    : 'bg-gray-50 dark:bg-gray-700 border-2 border-transparent hover:border-gray-300 dark:hover:border-gray-600'
                }`}
                data-testid={`strategy-${strategy.id}`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <Icon className={`w-4 h-4 ${isSelected ? 'text-purple-600 dark:text-purple-400' : 'text-gray-500'}`} />
                  <span className={`text-sm font-medium ${isSelected ? 'text-purple-700 dark:text-purple-300' : 'text-gray-700 dark:text-gray-300'}`}>
                    {strategy.name}
                  </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {strategy.description}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Target Reduction Slider */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Target Reduction: <span className="text-purple-600 dark:text-purple-400">{targetReduction}%</span>
        </label>
        <input
          type="range"
          min="10"
          max="90"
          step="5"
          value={targetReduction}
          onChange={(e) => setTargetReduction(Number(e.target.value))}
          className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
          data-testid="target-reduction-slider"
        />
        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
          <span>10%</span>
          <span>90%</span>
        </div>
      </div>

      {/* Strategy-specific settings */}
      {selectedStrategy === 'filtering' && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Min Relevance Threshold: <span className="text-purple-600 dark:text-purple-400">{(relevanceThreshold * 100).toFixed(0)}%</span>
          </label>
          <input
            type="range"
            min="0"
            max="0.8"
            step="0.05"
            value={relevanceThreshold}
            onChange={(e) => setRelevanceThreshold(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
            data-testid="relevance-threshold-slider"
          />
        </div>
      )}

      {selectedStrategy === 'truncation' && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Maximum Chunks: <span className="text-purple-600 dark:text-purple-400">{maxChunks}</span>
          </label>
          <input
            type="range"
            min="5"
            max="50"
            step="5"
            value={maxChunks}
            onChange={(e) => setMaxChunks(Number(e.target.value))}
            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
            data-testid="max-chunks-slider"
          />
        </div>
      )}

      {/* Estimated Result */}
      <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg mb-4" data-testid="compression-estimate">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-600 dark:text-gray-400">Current:</span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {currentTokens.toLocaleString()} tokens
          </span>
        </div>
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-600 dark:text-gray-400">Estimated after:</span>
          <span className="font-medium text-green-600 dark:text-green-400">
            ~{estimatedTokensAfter.toLocaleString()} tokens
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-400">Utilization after:</span>
          <span className={`font-medium ${utilizationAfter < 60 ? 'text-green-600 dark:text-green-400' : 'text-yellow-600 dark:text-yellow-400'}`}>
            {utilizationAfter}%
          </span>
        </div>
      </div>

      {/* Compress Button */}
      <button
        onClick={handleCompress}
        disabled={isCompressing}
        className="w-full py-2.5 px-4 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
        data-testid="compress-button"
      >
        {isCompressing ? (
          <>
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Compressing...
          </>
        ) : (
          <>
            <Minimize2 className="w-4 h-4" />
            Apply Compression
          </>
        )}
      </button>
    </div>
  );
}
