/**
 * UploadPage Component (V2)
 * Sprint 125 Feature 125.9a: Domain Detection at Upload
 *
 * Document upload page with AI-powered domain classification via /detect-domain API
 */

import { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Upload, Loader2, FileText, CheckCircle, AlertTriangle, X } from 'lucide-react';
import { detectDomain, uploadDocument } from '../../api/upload';
import type { DomainDetectionResult } from '../../api/upload';

interface UploadFile {
  file: File;
  status: 'pending' | 'detecting' | 'detected' | 'uploading' | 'uploaded' | 'failed';
  detectedDomains: DomainDetectionResult[];
  selectedDomain: 'auto' | 'manual' | 'none';
  manualDomainId: string | null;
  documentId?: string;
  error?: string;
}

interface Domain {
  domain_id: string;
  domain_name: string;
  ddc_code: string;
}

export function UploadPageV2() {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [availableDomains, setAvailableDomains] = useState<Domain[]>([]);
  const [namespace, setNamespace] = useState('default');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load available domains on mount
  useState(() => {
    const loadDomains = async () => {
      try {
        const response = await fetch('/api/v1/admin/domains');
        if (response.ok) {
          const data = await response.json();
          setAvailableDomains(data.domains || []);
        }
      } catch (err) {
        console.error('Failed to load domains:', err);
      }
    };
    loadDomains();
  });

  const handleFilesSelected = async (selectedFiles: FileList | null) => {
    if (!selectedFiles || selectedFiles.length === 0) return;

    const newFiles: UploadFile[] = Array.from(selectedFiles).map((f) => ({
      file: f,
      status: 'detecting',
      detectedDomains: [],
      selectedDomain: 'auto',
      manualDomainId: null,
    }));

    setFiles((prev) => [...prev, ...newFiles]);

    // Detect domain for each file
    for (const uploadFile of newFiles) {
      try {
        const result = await detectDomain(uploadFile.file);

        setFiles((prev) =>
          prev.map((f) =>
            f.file.name === uploadFile.file.name
              ? {
                  ...f,
                  status: 'detected',
                  detectedDomains: result.domains,
                }
              : f
          )
        );
      } catch (error) {
        console.error(`Failed to detect domain for ${uploadFile.file.name}:`, error);
        setFiles((prev) =>
          prev.map((f) =>
            f.file.name === uploadFile.file.name
              ? {
                  ...f,
                  status: 'failed',
                  error: 'Domain detection failed',
                }
              : f
          )
        );
      }
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFilesSelected(e.target.files);
  };

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const updateDomainSelection = (
    index: number,
    selection: 'auto' | 'manual' | 'none',
    manualId?: string
  ) => {
    setFiles((prev) =>
      prev.map((f, i) =>
        i === index
          ? {
              ...f,
              selectedDomain: selection,
              manualDomainId: selection === 'manual' ? manualId || null : null,
            }
          : f
      )
    );
  };

  const handleUploadAll = async () => {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file.status === 'uploaded') continue;

      setFiles((prev) =>
        prev.map((f, idx) => (idx === i ? { ...f, status: 'uploading' } : f))
      );

      try {
        const domainId =
          file.selectedDomain === 'auto'
            ? file.detectedDomains[0]?.domain_id
            : file.selectedDomain === 'manual'
              ? file.manualDomainId
              : undefined;

        const result = await uploadDocument(file.file, namespace, domainId ?? undefined);

        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === i
              ? {
                  ...f,
                  status: 'uploaded',
                  documentId: result.document_id,
                }
              : f
          )
        );
      } catch (error) {
        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === i
              ? {
                  ...f,
                  status: 'failed',
                  error: error instanceof Error ? error.message : 'Upload failed',
                }
              : f
          )
        );
      }
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const getStatusIcon = (status: UploadFile['status']) => {
    switch (status) {
      case 'detecting':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'detected':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'uploading':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'uploaded':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'failed':
        return <AlertTriangle className="w-5 h-5 text-red-500" />;
      default:
        return <FileText className="w-5 h-5 text-gray-400" />;
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="upload-page-v2">
      {/* Back Link */}
      <Link
        to="/admin"
        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 mb-4"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 19l-7-7m0 0l7-7m-7 7h18"
          />
        </svg>
        Back to Admin
      </Link>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Document Upload</h1>
        <p className="text-gray-600 mt-1">
          Upload documents with automatic domain detection powered by AI
        </p>
      </div>

      {/* Namespace Input */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Namespace
        </label>
        <input
          type="text"
          value={namespace}
          onChange={(e) => setNamespace(e.target.value)}
          placeholder="default"
          className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* File Dropzone */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.docx,.md"
          onChange={handleFileInputChange}
          className="hidden"
          id="file-input-v2"
          data-testid="file-input"
        />
        <label
          htmlFor="file-input-v2"
          className="flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-lg p-12 cursor-pointer hover:border-blue-500 transition-colors"
        >
          <Upload className="w-12 h-12 text-gray-400 mb-4" />
          <span className="text-lg font-medium text-gray-700 mb-2">
            Choose files or drag and drop
          </span>
          <span className="text-sm text-gray-500">
            PDF, DOCX, TXT, MD supported
          </span>
        </label>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Files ({files.length})
            </h2>
          </div>
          <div className="divide-y divide-gray-200">
            {files.map((file, idx) => (
              <div
                key={idx}
                className="p-6 hover:bg-gray-50"
                data-testid={`file-item-${idx}`}
              >
                <div className="flex items-start gap-4">
                  {/* Status Icon */}
                  <div className="flex-shrink-0 mt-1">
                    {getStatusIcon(file.status)}
                  </div>

                  {/* File Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium text-gray-900 truncate">
                        {file.file.name}
                      </div>
                      <button
                        onClick={() => handleRemoveFile(idx)}
                        className="text-gray-400 hover:text-red-600"
                        data-testid={`remove-file-${idx}`}
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                    <div className="text-sm text-gray-500 mb-3">
                      {formatBytes(file.file.size)}
                    </div>

                    {/* Domain Selection */}
                    {file.status === 'detected' && (
                      <div className="space-y-2">
                        {/* Auto-detected option */}
                        {file.detectedDomains.length > 0 && (
                          <label className="flex items-start gap-2 cursor-pointer">
                            <input
                              type="radio"
                              name={`domain-selection-${idx}`}
                              checked={file.selectedDomain === 'auto'}
                              onChange={() => updateDomainSelection(idx, 'auto')}
                              className="mt-1 w-4 h-4 text-blue-600"
                            />
                            <div className="flex-1">
                              <div className="font-medium text-gray-900">
                                Use detected: {file.detectedDomains[0].domain_name}
                              </div>
                              <div className="text-sm text-gray-600">
                                Confidence:{' '}
                                {(file.detectedDomains[0].confidence * 100).toFixed(1)}%
                                {file.detectedDomains[0].confidence >= 0.85 && (
                                  <span className="ml-2 text-green-600">(Recommended)</span>
                                )}
                              </div>
                            </div>
                          </label>
                        )}

                        {/* Manual selection option */}
                        <label className="flex items-start gap-2 cursor-pointer">
                          <input
                            type="radio"
                            name={`domain-selection-${idx}`}
                            checked={file.selectedDomain === 'manual'}
                            onChange={() => updateDomainSelection(idx, 'manual')}
                            className="mt-1 w-4 h-4 text-blue-600"
                          />
                          <div className="flex-1">
                            <div className="font-medium text-gray-900">
                              Select manually
                            </div>
                            {file.selectedDomain === 'manual' && (
                              <select
                                value={file.manualDomainId || ''}
                                onChange={(e) =>
                                  updateDomainSelection(idx, 'manual', e.target.value)
                                }
                                className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                data-testid={`manual-domain-select-${idx}`}
                              >
                                <option value="">-- Select domain --</option>
                                {availableDomains.map((d) => (
                                  <option key={d.domain_id} value={d.domain_id}>
                                    {d.domain_name} ({d.ddc_code})
                                  </option>
                                ))}
                              </select>
                            )}
                          </div>
                        </label>

                        {/* No domain option */}
                        <label className="flex items-start gap-2 cursor-pointer">
                          <input
                            type="radio"
                            name={`domain-selection-${idx}`}
                            checked={file.selectedDomain === 'none'}
                            onChange={() => updateDomainSelection(idx, 'none')}
                            className="mt-1 w-4 h-4 text-blue-600"
                          />
                          <div className="flex-1">
                            <div className="font-medium text-gray-900">No domain</div>
                            <div className="text-sm text-gray-600">
                              Upload without domain classification
                            </div>
                          </div>
                        </label>
                      </div>
                    )}

                    {/* Error Message */}
                    {file.error && (
                      <div className="mt-2 text-sm text-red-600">{file.error}</div>
                    )}

                    {/* Upload Success */}
                    {file.status === 'uploaded' && file.documentId && (
                      <div className="mt-2 text-sm text-green-600">
                        Uploaded successfully! ID: {file.documentId}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
            <button
              onClick={() => setFiles([])}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Clear All
            </button>
            <button
              onClick={handleUploadAll}
              disabled={
                files.length === 0 ||
                files.some((f) => f.status === 'uploading' || f.status === 'detecting')
              }
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              data-testid="upload-button"
            >
              Upload {files.filter((f) => f.status !== 'uploaded').length} file(s)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
