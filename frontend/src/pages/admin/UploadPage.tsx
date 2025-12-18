/**
 * UploadPage Component
 * Sprint 45 Feature 45.7: Upload Page Domain Suggestion
 *
 * Document upload page with AI-powered domain classification
 */

import { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useClassifyDocument } from '../../hooks/useDomainTraining';
import { DomainSelector } from '../../components/admin/DomainSelector';
import { ConfidenceBadge } from '../../components/admin/ConfidenceBadge';
import type { ClassificationResult } from '../../hooks/useDomainTraining';

interface UploadFile {
  file: File;
  status: 'pending' | 'uploading' | 'uploaded' | 'failed';
  domain: string | null;
}

interface DomainSuggestion {
  recommended: string;
  confidence: number;
  alternatives: ClassificationResult[];
}

export function UploadPage() {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [domainSuggestions, setDomainSuggestions] = useState<Map<string, DomainSuggestion>>(
    new Map()
  );
  const fileInputRef = useRef<HTMLInputElement>(null);
  const classifyDocument = useClassifyDocument();

  const readFilePreview = async (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const text = reader.result as string;
        // Return first 1000 characters for classification
        resolve(text.slice(0, 1000));
      };
      reader.onerror = reject;
      reader.readAsText(file);
    });
  };

  const handleFilesSelected = async (selectedFiles: FileList | null) => {
    if (!selectedFiles || selectedFiles.length === 0) return;

    const newFiles = Array.from(selectedFiles).map((f) => ({
      file: f,
      status: 'pending' as const,
      domain: null,
    }));

    setFiles((prev) => [...prev, ...newFiles]);

    // Classify each file
    for (const uploadFile of newFiles) {
      try {
        // Read file preview
        const text = await readFilePreview(uploadFile.file);

        // Classify document
        const result = await classifyDocument.mutateAsync({ text });

        // Store suggestion
        setDomainSuggestions((prev) => {
          const updated = new Map(prev);
          updated.set(uploadFile.file.name, {
            recommended: result.recommended,
            confidence: result.confidence,
            alternatives: result.classifications,
          });
          return updated;
        });

        // Auto-select recommended domain
        setFiles((prev) =>
          prev.map((f) =>
            f.file.name === uploadFile.file.name
              ? { ...f, domain: result.recommended }
              : f
          )
        );
      } catch (error) {
        console.error(`Failed to classify ${uploadFile.file.name}:`, error);
        // Fallback: Set default domain when classification fails
        setFiles((prev) =>
          prev.map((f) =>
            f.file.name === uploadFile.file.name && !f.domain
              ? { ...f, domain: 'general' }
              : f
          )
        );
        // Add fallback suggestion
        setDomainSuggestions((prev) => {
          const updated = new Map(prev);
          updated.set(uploadFile.file.name, {
            recommended: 'general',
            confidence: 0,
            alternatives: [],
          });
          return updated;
        });
      }
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFilesSelected(e.target.files);
  };

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const updateFileDomain = (index: number, domain: string) => {
    setFiles((prev) => prev.map((f, i) => (i === index ? { ...f, domain } : f)));
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="upload-page">
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
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Document Upload</h1>
        <p className="text-gray-600 mt-1">
          Upload documents and let AI suggest the best domain for classification
        </p>
      </div>

      {/* File Dropzone */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileInputChange}
          className="hidden"
          id="file-input"
          data-testid="file-input"
        />
        <label
          htmlFor="file-input"
          className="flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-lg p-12 cursor-pointer hover:border-blue-500 transition-colors"
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
          <span className="text-lg font-medium text-gray-700 mb-2">
            Choose files or drag and drop
          </span>
          <span className="text-sm text-gray-500">
            PDF, DOCX, TXT, MD and more supported
          </span>
        </label>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Selected Files ({files.length})
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="file-list-table">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                    File
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                    Suggested Domain
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                    Confidence
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {files.map((file, idx) => {
                  const suggestion = domainSuggestions.get(file.file.name);
                  return (
                    <tr
                      key={idx}
                      className="border-t border-gray-200 hover:bg-gray-50"
                      data-testid={`file-row-${idx}`}
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center space-x-2">
                          <svg
                            className="w-5 h-5 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                            />
                          </svg>
                          <span className="text-sm font-medium text-gray-900 truncate max-w-xs">
                            {file.file.name}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {formatBytes(file.file.size)}
                      </td>
                      <td className="px-6 py-4">
                        <DomainSelector
                          suggested={suggestion?.recommended}
                          alternatives={suggestion?.alternatives}
                          onChange={(domain) => updateFileDomain(idx, domain)}
                        />
                      </td>
                      <td className="px-6 py-4">
                        {suggestion && <ConfidenceBadge score={suggestion.confidence} />}
                      </td>
                      <td className="px-6 py-4">
                        <button
                          onClick={() => handleRemoveFile(idx)}
                          className="text-red-600 hover:text-red-700 text-sm font-medium"
                          data-testid={`remove-file-${idx}`}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-4">
            <button
              onClick={() => setFiles([])}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Clear All
            </button>
            <button
              onClick={() => {
                // TODO: Implement upload logic
                console.log('Uploading files:', files);
              }}
              disabled={files.length === 0 || files.some((f) => !f.domain)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              data-testid="upload-button"
            >
              Upload {files.length} file{files.length !== 1 ? 's' : ''}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
