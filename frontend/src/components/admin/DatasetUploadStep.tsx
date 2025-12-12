/**
 * DatasetUploadStep Component
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 *
 * Step 2 of domain wizard: Upload JSONL dataset with preview
 */

import { useState, useRef } from 'react';
import type { TrainingSample } from '../../hooks/useDomainTraining';

interface DatasetUploadStepProps {
  dataset: TrainingSample[];
  onUpload: (samples: TrainingSample[]) => void;
  onBack: () => void;
  onNext: () => void;
}

export function DatasetUploadStep({ dataset, onUpload, onBack, onNext }: DatasetUploadStepProps) {
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setError(null);

    try {
      const text = await file.text();
      const lines = text.trim().split('\n');
      const samples: TrainingSample[] = [];

      for (const line of lines) {
        if (!line.trim()) continue;

        try {
          const sample = JSON.parse(line);

          // Validate sample structure
          if (!sample.input || !sample.output) {
            throw new Error('Each sample must have "input" and "output" fields');
          }

          samples.push({
            input: sample.input,
            output: sample.output,
            metadata: sample.metadata,
          });
        } catch (err) {
          throw new Error(
            `Invalid JSONL format: ${err instanceof Error ? err.message : 'Parse error'}`
          );
        }
      }

      if (samples.length === 0) {
        throw new Error('No valid samples found in file');
      }

      onUpload(samples);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse JSONL file');
      onUpload([]);
    }
  };

  const handleClearDataset = () => {
    onUpload([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const isValid = dataset.length > 0;

  return (
    <div className="space-y-6" data-testid="dataset-upload-step">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">Upload Training Dataset</h2>
        <p className="text-gray-600">Step 2 of 3: Upload a JSONL file with training samples</p>
      </div>

      {/* File Upload */}
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8">
        <input
          ref={fileInputRef}
          type="file"
          accept=".jsonl,.json"
          onChange={handleFileChange}
          className="hidden"
          id="dataset-file-input"
          data-testid="dataset-file-input"
        />
        <label
          htmlFor="dataset-file-input"
          className="flex flex-col items-center cursor-pointer"
        >
          <svg
            className="w-12 h-12 text-gray-400 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <span className="text-lg font-medium text-gray-700">Choose JSONL file</span>
          <span className="text-sm text-gray-500 mt-2">
            Each line should be: {'{'}
            "input": "question", "output": "answer"{'}'}
          </span>
        </label>
      </div>

      {/* Error Display */}
      {error && (
        <div
          className="p-4 bg-red-50 border border-red-200 rounded-lg"
          data-testid="dataset-upload-error"
        >
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Dataset Preview */}
      {dataset.length > 0 && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900">
              Dataset Preview ({dataset.length} samples)
            </h3>
            <button
              onClick={handleClearDataset}
              className="text-sm text-red-600 hover:text-red-700 font-medium"
              data-testid="clear-dataset-button"
            >
              Clear
            </button>
          </div>

          <div className="border border-gray-200 rounded-lg max-h-96 overflow-y-auto">
            {dataset.slice(0, 5).map((sample, idx) => (
              <div
                key={idx}
                className="p-4 border-b border-gray-200 last:border-b-0"
                data-testid={`dataset-sample-${idx}`}
              >
                <div className="space-y-2">
                  <div>
                    <span className="text-xs font-semibold text-gray-500 uppercase">Input</span>
                    <p className="text-sm text-gray-900 mt-1">{sample.input}</p>
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-gray-500 uppercase">Output</span>
                    <p className="text-sm text-gray-700 mt-1">{sample.output}</p>
                  </div>
                </div>
              </div>
            ))}
            {dataset.length > 5 && (
              <div className="p-4 text-center text-sm text-gray-500">
                + {dataset.length - 5} more samples
              </div>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-between pt-4 border-t">
        <button
          onClick={onBack}
          className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
          data-testid="dataset-upload-back"
        >
          Back
        </button>
        <button
          onClick={onNext}
          disabled={!isValid}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          data-testid="dataset-upload-next"
        >
          Start Training
        </button>
      </div>
    </div>
  );
}
