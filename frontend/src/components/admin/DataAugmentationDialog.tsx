/**
 * DataAugmentationDialog Component
 * Sprint 71 Feature 71.13: Data Augmentation UI
 *
 * Dialog for augmenting training datasets using LLM-based generation.
 * Expands small datasets (5-10 samples) into larger ones (20+).
 */

import { useState } from 'react';
import { Loader2, Sparkles, CheckCircle2, AlertCircle, X } from 'lucide-react';
import {
  useAugmentTrainingData,
  type TrainingSample,
  type AugmentationResponse,
} from '../../hooks/useDomainTraining';

interface DataAugmentationDialogProps {
  seedSamples: TrainingSample[];
  onAugmented: (augmentedSamples: TrainingSample[]) => void;
  onClose: () => void;
}

export function DataAugmentationDialog({
  seedSamples,
  onAugmented,
  onClose,
}: DataAugmentationDialogProps) {
  const [targetCount, setTargetCount] = useState(20);
  const [result, setResult] = useState<AugmentationResponse | null>(null);
  const { mutateAsync: augmentData, isLoading, error } = useAugmentTrainingData();

  const handleAugment = async () => {
    try {
      const response = await augmentData({
        seed_samples: seedSamples,
        target_count: targetCount,
      });
      setResult(response);
    } catch (err) {
      // Error is handled by hook
    }
  };

  const handleAccept = () => {
    if (result) {
      // Combine seed samples + generated samples
      const allSamples = [...seedSamples, ...result.generated_samples];
      onAugmented(allSamples);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Sparkles className="w-6 h-6 text-purple-600" />
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Augment Training Data
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {!result ? (
            <>
              {/* Info */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  <strong>Data Augmentation</strong> uses LLM to expand your dataset by generating
                  variations of your seed samples. This improves training quality for small datasets.
                </p>
              </div>

              {/* Current Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Current Samples</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {seedSamples.length}
                  </p>
                </div>
                <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                  <p className="text-sm text-purple-600 dark:text-purple-400">Target Samples</p>
                  <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                    {targetCount}
                  </p>
                </div>
              </div>

              {/* Target Count Slider */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Target Sample Count: {targetCount}
                </label>
                <input
                  type="range"
                  min={seedSamples.length + 5}
                  max={50}
                  value={targetCount}
                  onChange={(e) => setTargetCount(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-600"
                  disabled={isLoading}
                  data-testid="target-count-slider"
                />
                <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                  <span>{seedSamples.length + 5}</span>
                  <span>50</span>
                </div>
              </div>

              {/* Error */}
              {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-800 dark:text-red-200">
                      Augmentation Failed
                    </p>
                    <p className="text-sm text-red-600 dark:text-red-400 mt-1">{error.message}</p>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <button
                  onClick={handleAugment}
                  disabled={isLoading}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                  data-testid="generate-samples-button"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5" />
                      Generate {targetCount - seedSamples.length} Samples
                    </>
                  )}
                </button>
                <button
                  onClick={onClose}
                  disabled={isLoading}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <>
              {/* Success Result */}
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 flex items-start gap-3">
                <CheckCircle2 className="w-6 h-6 text-green-600 dark:text-green-400 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-green-800 dark:text-green-200">
                    Augmentation Complete!
                  </p>
                  <p className="text-sm text-green-600 dark:text-green-400 mt-1">
                    Successfully generated {result.generated_count} new samples from {result.seed_count} seeds
                    (validation rate: {Math.round(result.validation_rate * 100)}%)
                  </p>
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-center">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Seed Samples</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {result.seed_count}
                  </p>
                </div>
                <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4 text-center">
                  <p className="text-sm text-purple-600 dark:text-purple-400">Generated</p>
                  <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                    {result.generated_count}
                  </p>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 text-center">
                  <p className="text-sm text-green-600 dark:text-green-400">Total</p>
                  <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {result.seed_count + result.generated_count}
                  </p>
                </div>
              </div>

              {/* Sample Preview */}
              <div data-testid="augmentation-preview">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Sample Preview (first 3 generated samples):
                </p>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {result.generated_samples.slice(0, 3).map((sample, idx) => (
                    <div
                      key={idx}
                      className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 text-sm"
                      data-testid={`augmented-sample-${idx}`}
                    >
                      <p className="text-gray-900 dark:text-gray-100 font-medium mb-1">
                        {sample.text.slice(0, 100)}...
                      </p>
                      <p className="text-gray-600 dark:text-gray-400 text-xs">
                        Entities: {sample.entities.join(', ')}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <button
                  onClick={handleAccept}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium transition-colors"
                  data-testid="use-augmented-button"
                >
                  <CheckCircle2 className="w-5 h-5" />
                  Use Augmented Dataset ({result.seed_count + result.generated_count} samples)
                </button>
                <button
                  onClick={onClose}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default DataAugmentationDialog;
