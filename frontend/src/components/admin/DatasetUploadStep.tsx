/**
 * DatasetUploadStep Component
 * Sprint 45 Feature 45.4, 45.13: Domain Training Admin UI with JSONL Log Export
 *
 * Step 2 of domain wizard: Upload JSONL dataset with preview
 * Includes optional log path for saving training events to JSONL
 */

import { useState, useRef } from 'react';
import type { TrainingSample } from '../../hooks/useDomainTraining';

interface DatasetUploadStepProps {
  dataset: TrainingSample[];
  onUpload: (samples: TrainingSample[]) => void;
  onBack: () => void;
  onNext: (logPath?: string) => void;
  isLoading?: boolean;
  error?: string | null;
}

export function DatasetUploadStep({ dataset, onUpload, onBack, onNext, isLoading = false, error: submitError }: DatasetUploadStepProps) {
  const [parseError, setParseError] = useState<string | null>(null);
  const [logPath, setLogPath] = useState<string>('');
  const [showLogPathInput, setShowLogPathInput] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setParseError(null);

    try {
      const text = await file.text();
      const lines = text.trim().split('\n');
      const samples: TrainingSample[] = [];

      for (const line of lines) {
        if (!line.trim()) continue;

        try {
          const sample = JSON.parse(line);

          // Validate sample structure - must have text and entities (API format)
          if (!sample.text || !Array.isArray(sample.entities)) {
            throw new Error('Each sample must have "text" (string) and "entities" (array) fields');
          }

          samples.push({
            text: sample.text,
            entities: sample.entities,
            relations: sample.relations || [],
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
      setParseError(err instanceof Error ? err.message : 'Failed to parse JSONL file');
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
            Format: {'{"text": "...", "entities": ["..."], "relations": [...]}'}
          </span>
        </label>
      </div>

      {/* Error Display */}
      {(parseError || submitError) && (
        <div
          className="p-4 bg-red-50 border border-red-200 rounded-lg"
          data-testid="dataset-upload-error"
        >
          <p className="text-sm text-red-800">{parseError || submitError}</p>
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
                    <span className="text-xs font-semibold text-gray-500 uppercase">Text</span>
                    <p className="text-sm text-gray-900 mt-1 whitespace-pre-wrap line-clamp-3">
                      {sample.text}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-gray-500 uppercase">Entities ({sample.entities.length})</span>
                    <p className="text-sm text-gray-700 mt-1">
                      {sample.entities.slice(0, 8).join(', ')}
                      {sample.entities.length > 8 && ` +${sample.entities.length - 8} more`}
                    </p>
                  </div>
                  {sample.relations && sample.relations.length > 0 && (
                    <div>
                      <span className="text-xs font-semibold text-gray-500 uppercase">Relations ({sample.relations.length})</span>
                      <p className="text-sm text-gray-600 mt-1">
                        {sample.relations.slice(0, 3).map((r, i) => (
                          <span key={i} className="block">{r.subject} → {r.predicate} → {r.object}</span>
                        ))}
                        {sample.relations.length > 3 && <span className="text-gray-400">+{sample.relations.length - 3} more</span>}
                      </p>
                    </div>
                  )}
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

      {/* Log Path Input (Feature 45.13) */}
      {dataset.length > 0 && (
        <div className="space-y-2">
          <button
            onClick={() => setShowLogPathInput(!showLogPathInput)}
            className="text-sm text-gray-600 hover:text-gray-800 flex items-center gap-1"
          >
            <span>{showLogPathInput ? '▼' : '▶'}</span>
            Advanced: JSONL Training Log Export
          </button>
          {showLogPathInput && (
            <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 space-y-2">
              <label htmlFor="log-path" className="block text-sm font-medium text-gray-700">
                Training Log Path (optional)
              </label>
              <input
                id="log-path"
                type="text"
                value={logPath}
                onChange={(e) => setLogPath(e.target.value)}
                placeholder="/var/log/aegis/training/domain_2025-12-12.jsonl"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                data-testid="log-path-input"
              />
              <p className="text-xs text-gray-500">
                Save all training events (prompts, responses, scores) to a JSONL file for later DSPy evaluation.
                Leave empty to skip logging.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-between pt-4 border-t">
        <button
          onClick={onBack}
          disabled={isLoading}
          className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          data-testid="dataset-upload-back"
        >
          Back
        </button>
        <div className="flex items-center gap-3">
          {logPath && (
            <span className="text-xs text-green-600 flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Log to: {logPath.split('/').pop()}
            </span>
          )}
          <button
            onClick={() => onNext(logPath || undefined)}
            disabled={!isValid || isLoading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
            data-testid="dataset-upload-next"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Starting Training...
              </>
            ) : (
              'Start Training'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
